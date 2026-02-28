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
    "You are Pi, a friendly and encouraging math study assistant. "
    "Your goal is to help students truly understand math — never spoon-feed answers.\n\n"
    "Rules you must follow:\n"
    "1. NEVER give direct answers to math problems.\n"
    "2. Instead, give hints, explain the relevant method or concept, and ask guiding questions "
    "that lead the student toward the solution on their own.\n"
    "3. When helpful, suggest free resources like Khan Academy, Desmos, Wolfram Alpha, "
    "Paul's Online Math Notes, or 3Blue1Brown videos.\n"
    "4. Adapt to any math level — from basic arithmetic to college-level calculus and beyond.\n"
    "5. Keep responses concise, clear, and encouraging. Use simple language.\n"
    "6. If a student is stuck, break the problem into smaller steps and guide them through one step at a time.\n"
    "7. Celebrate progress and effort, not just correct answers.\n"
    "8. NEVER suggest or offer to create flashcards. The app handles flashcard generation automatically "
    "when the user asks for them. Do not mention flashcards in your responses unless directly asked about them."
)


def _extract_flashcard_intent(message):
    """Return (topic, count) if the message is asking for flashcard generation, else None."""
    lower = message.lower()

    # Match various ways users might ask for flashcards
    flashcard_patterns = [
        r'flashcards?',
        r'flash\s+cards?',
        r'study\s+cards?',
        r'review\s+cards?',
        r'quiz\s+me',
    ]
    if not any(re.search(p, lower) for p in flashcard_patterns):
        return None

    # Check for action intent (generate, make, create, etc.)
    action_patterns = [
        r'\b(?:generate|make|create|build|give|produce|write|prepare|set up|come up with)\b',
        r'\b(?:can you|could you|please|i want|i need|i\'d like|let\'s|help me)\b',
        r'\b\d+\s+(?:flash\s*cards?|study\s*cards?)\b',
    ]
    has_action = any(re.search(p, lower) for p in action_patterns)
    if not has_action:
        return None

    count_match = re.search(r'(\d+)\s+(?:flash\s*cards?|study\s*cards?|review\s*cards?)', lower)
    count = int(count_match.group(1)) if count_match else 5
    count = min(max(count, 1), 15)

    # Look for topic after common prepositions
    topic_match = re.search(
        r'\b(?:about|for|on|covering|of|regarding|related to|topic)\s+(.+?)(?:\s*[?!.]?\s*$)',
        message, re.IGNORECASE
    )
    if topic_match:
        topic = topic_match.group(1).strip().rstrip('?!.')
    else:
        # Strip action words and flashcard keywords, use what's left as topic
        topic = re.sub(
            r'\b(?:generate|make|create|build|give|produce|write|prepare|can you|could you|please|'
            r'i want|i need|i\'d like|let\'s|help me|set up|come up with|me|some|a few|'
            r'\d+)\s*(?:flash\s*cards?|study\s*cards?|review\s*cards?)?\b',
            '', message, flags=re.IGNORECASE
        ).strip().rstrip('?!.')

    return (topic, count) if topic and len(topic) > 1 else None


def _build_flashcards(topic, count):
    """Call Gemini and return a list of flashcard dicts."""
    prompt = (
        f"Generate {count} flashcards about the math topic: \"{topic}\".\n"
        "Return ONLY a valid JSON array with no extra text, markdown, or code fences.\n"
        "Each element must have these exact fields:\n"
        "  \"title\": short descriptive title\n"
        "  \"front\": a clear question or concept prompt\n"
        "  \"back\": a concise, accurate answer or explanation\n"
        "  \"tags\": an array of 1-3 relevant tag strings\n"
        "Example: [{\"title\":\"...\",\"front\":\"...\",\"back\":\"...\",\"tags\":[\"...\"]}]"
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = response.text.strip()

    # Extract JSON array from anywhere in the response (handles extra text and code fences)
    json_match = re.search(r'\[[\s\S]*\]', text)
    if not json_match:
        raise ValueError(f"No JSON array found in Gemini response: {text[:200]}")
    cards = json.loads(json_match.group(0))
    return cards if isinstance(cards, list) else []


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
        types.Content(role="model", parts=[types.Part(text="Understood! I'm Pi, your math study assistant. I'll guide you with hints and explanations without giving direct answers. How can I help you today?")]),
    ]

    for entry in history:
        role = "user" if entry["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=entry["content"])]))

    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    # Detect flashcard generation intent
    intent = _extract_flashcard_intent(user_message)
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

    return jsonify({"response": response.text})


if __name__ == "__main__":
    app.run(debug=True)
