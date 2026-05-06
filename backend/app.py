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
    response = send_from_directory(app.static_folder, filename)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are Pi, a warm and encouraging tech helper for kids and beginners. "
    "Your job is to make technology feel easy, fun, and stress-free.\n\n"
    "How you communicate:\n"
    "- Keep responses SHORT. 2 to 4 sentences max. If more is needed, break it into a follow-up.\n"
    "- Use simple, everyday words. If you must use a tech term, explain it in one short phrase right away.\n"
    "- Use fun real-world comparisons to explain things (e.g., 'A variable is like a labeled box').\n"
    "- Sound like a friendly, patient older sibling — warm, casual, and never overwhelming.\n"
    "- Never make anyone feel bad for not knowing something.\n\n"
    "Rules you must follow:\n"
    "1. NEVER give direct answers to coding problems. Give a small hint or ask one guiding question instead.\n"
    "2. Always give one small step at a time. Never dump a lot of information at once.\n"
    "3. Celebrate effort — every question is a great question.\n"
    "4. At the end of your response, suggest one of these two things — pick whichever fits best:\n"
    "   - Suggest a STUDY PLAN when the user is asking about a broad topic, wants to learn something new, "
    "is just getting started, or wants to understand a subject more deeply. "
    "Example: 'Want me to build you a study plan so you can learn [topic] step by step?'\n"
    "   - Suggest FLASHCARDS only when you just explained one specific, small concept and the user clearly "
    "already has some understanding of the topic. "
    "Example: 'Want me to make flashcards on this so you can review later?'\n"
    "   When in doubt, suggest a STUDY PLAN — it helps more. "
    "Only suggest one thing per response. Keep it one short, casual sentence.\n"
    "5. NEVER use markdown formatting. No **, *, or # symbols. Plain sentences only."
)


def _extract_intent(message, history=None):
    """Single Gemini call to classify user intent.
    Returns dict with 'type' of 'flashcard', 'study_plan', or 'chat',
    plus 'topic' and 'count' where relevant."""
    context = ""
    if history:
        recent = history[-6:]
        context = "Recent conversation:\n"
        for entry in recent:
            role = "User" if entry["role"] == "user" else "Assistant"
            context += f"{role}: {entry['content']}\n"
        context += "\n"

    prompt = (
        "Classify the intent of the following user message into exactly one of three types: "
        "\"flashcard\" (user wants flashcards generated), "
        "\"study_plan\" (user wants a study plan generated), or "
        "\"chat\" (everything else).\n"
        "Use the conversation context to resolve vague references like 'it', 'that topic', 'this', etc.\n"
        "Return ONLY valid JSON with no extra text, markdown, or code fences.\n"
        "Fields:\n"
        "  \"type\": one of \"flashcard\", \"study_plan\", or \"chat\"\n"
        "  \"topic\": the fully resolved subject as a string, or null if type is \"chat\"\n"
        "  \"count\": number of flashcards as an integer (default 5, max 15, only for flashcard type), or null\n\n"
        f"{context}Message: \"{message}\""
    )
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        text = response.text.strip()
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            return {"type": "chat"}
        data = json.loads(json_match.group(0))
        intent_type = data.get("type", "chat")
        if intent_type not in ("flashcard", "study_plan", "chat"):
            intent_type = "chat"
        topic = data.get("topic")
        count = int(data.get("count") or 5)
        count = min(max(count, 1), 15)
        return {"type": intent_type, "topic": topic, "count": count}
    except Exception as e:
        print(f"[intent classification error] {e}")
        return {"type": "chat"}


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


def _build_study_plan(topic):
    """Call Gemini and return a list of study plan topic strings."""
    prompt = (
        f"Generate a study plan for learning \"{topic}\".\n"
        "Return ONLY a valid JSON array of 6 to 8 short topic strings with no extra text, markdown, or code fences.\n"
        "Each string should be a specific topic or skill to learn (under 8 words each).\n"
        "Example: [\"Introduction to Python\", \"Variables and Data Types\", \"Loops and Conditionals\"]"
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = response.text.strip()
    json_match = re.search(r'\[[\s\S]*\]', text)
    if not json_match:
        raise ValueError(f"No JSON array found in Gemini response: {text[:200]}")
    topics = json.loads(json_match.group(0))
    if not isinstance(topics, list):
        return []
    return [str(t).strip() for t in topics if t]


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

    # Single intent classification call
    intent = _extract_intent(user_message, history)

    if intent["type"] == "flashcard" and intent.get("topic"):
        try:
            cards = _build_flashcards(intent["topic"], intent["count"])
            reply = (
                f"Done! I've generated {len(cards)} flashcards on \"{intent['topic']}\" "
                "and added them to your collection."
            )
            return jsonify({"response": reply, "flashcards": cards})
        except Exception as e:
            print(f"[flashcard generation error] {e}")

    elif intent["type"] == "study_plan" and intent.get("topic"):
        try:
            topics = _build_study_plan(intent["topic"])
            reply = (
                f"Done! I've created a study plan for \"{intent['topic']}\" "
                f"with {len(topics)} topics. Head over to your Study Tools page to start!"
            )
            return jsonify({"response": reply, "study_plan": topics})
        except Exception as e:
            print(f"[study plan generation error] {e}")

    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    response = client.models.generate_content(model=MODEL, contents=contents)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', response.text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'#{1,6}\s*', '', text)

    return jsonify({"response": text})


if __name__ == "__main__":
    app.run(debug=True)
