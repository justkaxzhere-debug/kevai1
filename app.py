import os
from flask import Flask, request, jsonify, send_from_directory
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
chat_history = [
    {
        "role": "system",
        "content": "Your name is Kevin's AI. You are a helpful, funny and friendly assistant who loves Pokemon. You speak casually like a friend, use simple language, and always stay enthusiastic and encouraging."
    }
]

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    chat_history.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=chat_history
    )

    reply = response.choices[0].message.content
    chat_history.append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)