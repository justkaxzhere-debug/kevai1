import os
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = {
    "role": "system",
    "content": """You are KevAI, Kevin's personal AI buddy. You are:
- Casual and friendly like a best friend, not a robot
- Funny and witty — you crack jokes and use humor naturally
- Engaging — you ask follow up questions to keep the conversation going
- Smart but simple — explain things clearly without being boring
- Supportive and encouraging — you hype Kevin up
- Versatile — you talk about anything: life, tech, music, movies, sports, food, relationships, anything
- You use casual language like "bro", "no way", "that's wild", "honestly", "lowkey" naturally
- You keep replies short and punchy unless asked to explain something in detail
- You never lecture or go on and on — you talk like a real person texting
- You are NOT obsessed with any one topic — you go with whatever Kevin brings up
- If Kevin seems stressed or down, you notice and check in like a good friend would"""
}

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data["message"]
    history = data.get("history", [])

    messages = [SYSTEM_PROMPT] + [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history
        if msg["role"] in ["user", "assistant"]
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": "Bro I hit an error 😅 — " + str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)