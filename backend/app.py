import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)
CORS(app)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

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
    "7. Celebrate progress and effort, not just correct answers."
)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = data["message"]
    history = data.get("history", [])

    contents = [{"role": "user", "parts": [SYSTEM_PROMPT]}]
    contents.append({"role": "model", "parts": ["Understood! I'm Pi, your math study assistant. I'll guide you with hints and explanations without giving direct answers. How can I help you today?"]})

    for entry in history:
        role = "user" if entry["role"] == "user" else "model"
        contents.append({"role": role, "parts": [entry["content"]]})

    contents.append({"role": "user", "parts": [user_message]})

    response = model.generate_content(contents)

    return jsonify({"response": response.text})


if __name__ == "__main__":
    app.run(debug=True)
