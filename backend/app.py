import os
import json
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Serve frontend files from the code/ directory
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '..', 'code'))
CORS(app)


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'firstPage.html')


@app.route('/<path:filename>')
def serve_frontend(filename):
    return send_from_directory(app.static_folder, filename)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are Pi, a warm, patient, and encouraging tech helper who loves making technology easy and fun to learn. "
    "You talk to people of all ages and backgrounds — from young kids to adults who are brand new to technology. "
    "Your job is to make everyone feel welcome, capable, and excited about learning.\n\n"
    "Topics you can help with: programming, computers, the internet, apps, games, cybersecurity, "
    "websites, databases, algorithms, and anything else tech-related.\n\n"
    "How you communicate:\n"
    "- Always use simple, everyday language. Avoid jargon — if you must use a technical word, explain it right away "
    "in plain terms (e.g., 'A variable is like a labeled box that holds information').\n"
    "- Use relatable real-world analogies and comparisons to explain tricky concepts.\n"
    "- Keep your tone warm, fun, and encouraging — like a patient friend who loves helping.\n"
    "- Never make anyone feel bad for not knowing something. Normalize not knowing — it's how we all learn!\n"
    "- Match your vocabulary and complexity to how the person is talking. "
    "If they sound young or are using simple words, keep it extra simple and friendly. "
    "If they seem more advanced, you can be more detailed.\n\n"
    "Rules you must follow:\n"
    "1. NEVER give direct answers to technical problems or coding challenges.\n"
    "2. Instead, give hints, explain the relevant concept or method, and ask guiding questions "
    "that lead the student toward the solution on their own.\n"
    "3. When helpful, suggest free beginner-friendly resources like freeCodeCamp, CS50, Khan Academy, "
    "Scratch, or Code.org for younger learners — or MDN Web Docs, GeeksforGeeks, and The Odin Project for older ones.\n"
    "4. Always break things into small, easy steps. Never overwhelm with too much at once.\n"
    "5. Celebrate every question and every effort — no question is too small or too silly.\n"
    "6. When a user asks about or discusses a topic, end your response with a short, friendly suggestion "
    "to generate flashcards on it. For example: 'Want me to make some flashcards on [topic] so you can practice later?' "
    "Keep the suggestion light and natural.\n"
    "7. NEVER use markdown formatting in your responses. Do not use ** for bold, * for italic, # for headers, "
    "or any other markdown symbols. Write in plain, natural sentences only."
)


def _extract_flashcard_intent(message, history=None):
    """Use Gemini to classify if the message is requesting flashcard generation.
    Returns (topic, count) if it is, else None."""
    context = ""
    if history:
        recent = history[-6:]  # last 3 exchanges
        context = "Recent conversation:\n"
        for entry in recent:
            role = "User" if entry["role"] == "user" else "Assistant"
            context += f"{role}: {entry['content']}\n"
        context += "\n"

    prompt = (
        "Determine if the following user message is requesting flashcard generation. "
        "Use the conversation context to resolve any vague references like 'it', 'that topic', 'this', etc.\n"
        "Return ONLY valid JSON with no extra text, markdown, or code fences.\n"
        "Fields:\n"
        "  \"is_request\": true if the user wants flashcards generated, false otherwise\n"
        "  \"topic\": the fully resolved subject for the flashcards as a string, or null if not a request\n"
        "  \"count\": number of flashcards requested as an integer (default 5, max 15), or null\n\n"
        f"{context}Message: \"{message}\""
    )
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        text = response.text.strip()
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            return None
        data = json.loads(json_match.group(0))
        if not data.get("is_request"):
            return None
        topic = data.get("topic")
        count = int(data.get("count") or 5)
        count = min(max(count, 1), 15)
        return (topic, count) if topic and len(str(topic)) > 1 else None
    except Exception as e:
        print(f"[flashcard intent classification error] {e}")
        return None


def _build_flashcards(topic, count):
    """Call Gemini and return a list of flashcard dicts."""
    prompt = (
        f"Generate {count} flashcards about the tech topic: \"{topic}\".\n"
        "Return ONLY a valid JSON array with no extra text, markdown, or code fences.\n"
        "Each element must have these exact fields:\n"
        "  \"title\": short descriptive title\n"
        "  \"front\": a clear question or concept prompt\n"
        "  \"back\": a concise, accurate answer or explanation\n"
        "Example: [{\"title\":\"...\",\"front\":\"...\",\"back\":\"...\"}]"
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = response.text.strip()

    # Extract JSON array from anywhere in the response (handles extra text and code fences)
    json_match = re.search(r'\[[\s\S]*\]', text)
    if not json_match:
        raise ValueError(f"No JSON array found in Gemini response: {text[:200]}")
    cards = json.loads(json_match.group(0))
    if not isinstance(cards, list):
        return []

    # Assign a single shared tag for the batch based on the generation topic
    tag = topic.strip().title()
    for card in cards:
        card['tags'] = [tag]
    return cards


@app.route("/api/welcome-questions", methods=["GET"])
def welcome_questions():
    prompt = (
        "Generate 4 short, fun, beginner-friendly example questions that someone of any age — "
        "including a child or someone new to technology — might ask a tech helper chatbot. "
        "The questions should be simple, curious, and cover a variety of topics like the internet, "
        "coding, devices, games, safety online, or how technology works in everyday life. "
        "Return ONLY a valid JSON array of 4 strings with no extra text, markdown, or code fences.\n"
        "Example: [\"What is the internet?\", \"How do video games get made?\"]"
    )
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        text = response.text.strip()
        json_match = re.search(r'\[[\s\S]*\]', text)
        if not json_match:
            raise ValueError("No JSON array found")
        questions = json.loads(json_match.group(0))
        if not isinstance(questions, list) or len(questions) < 4:
            raise ValueError("Invalid response format")
        return jsonify({"questions": questions[:4]})
    except Exception as e:
        print(f"[welcome questions error] {e}")
        return jsonify({"error": "Failed to generate questions"}), 500


@app.route("/api/generate-flashcards", methods=["POST"])
def generate_flashcards():
    data = request.get_json()
    if not data or "topic" not in data:
        return jsonify({"error": "Missing 'topic' field"}), 400

    topic = data["topic"]
    count = data.get("count", 5)

    try:
        cards = _build_flashcards(topic, count)
    except Exception:
        return jsonify({"error": "Failed to generate flashcards"}), 500

    if not cards:
        return jsonify({"error": "Unexpected response format"}), 500

    return jsonify({"flashcards": cards})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = data["message"]
    history = data.get("history", [])

    contents = [
        types.Content(role="user", parts=[types.Part(text=SYSTEM_PROMPT)]),
        types.Content(role="model", parts=[types.Part(text="Understood! I'm Pi, your tech study assistant. I'll guide you with hints and explanations without giving direct answers. How can I help you today?")]),
    ]

    for entry in history:
        role = "user" if entry["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=entry["content"])]))

    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    # Detect flashcard generation intent
    intent = _extract_flashcard_intent(user_message, history)
    if intent:
        topic, count = intent
        try:
            cards = _build_flashcards(topic, count)
            reply = (
                f"Done! I've generated {len(cards)} flashcards on \"{topic}\" "
                "and added them to your collection."
            )
            return jsonify({"response": reply, "flashcards": cards})
        except Exception as e:
            print(f"[flashcard generation error] {e}")
            # Fall through to regular chat response

    response = client.models.generate_content(model=MODEL, contents=contents)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', response.text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'#{1,6}\s*', '', text)

    return jsonify({"response": text})


if __name__ == "__main__":
    app.run(debug=True)
