import os
import json
from flask import Flask, request, jsonify, session
from groq import Groq

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "kevai-secret-2026")

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
    return '''<!DOCTYPE html>
<html>
<head>
  <title>KevAI</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: sans-serif; background: #0f0f0f; display: flex; justify-content: center; align-items: center; height: 100vh; }
    .container { width: 420px; height: 650px; background: #1a1a1a; border-radius: 20px; display: flex; flex-direction: column; overflow: hidden; border: 1px solid #333; }
    .header { background: #6c3fc5; padding: 16px 20px; display: flex; align-items: center; gap: 12px; }
    .avatar { width: 44px; height: 44px; border-radius: 50%; background: white; display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; }
    .header-text { flex: 1; }
    .header-text h1 { color: white; font-size: 16px; }
    .header-text p { color: #ddd; font-size: 11px; margin-top: 2px; }
    .online-dot { width: 8px; height: 8px; background: #4ade80; border-radius: 50%; display: inline-block; margin-right: 4px; }
    .clear-btn { background: rgba(255,255,255,0.2); border: none; color: white; padding: 4px 10px; border-radius: 10px; cursor: pointer; font-size: 11px; }
    .clear-btn:hover { background: rgba(255,255,255,0.3); }
    .messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
    .msg-row { display: flex; align-items: flex-end; gap: 8px; }
    .msg-row.user { flex-direction: row-reverse; }
    .msg-avatar { width: 28px; height: 28px; border-radius: 50%; background: #6c3fc5; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }
    .message { max-width: 75%; padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height: 1.5; }
    .user-msg { background: #6c3fc5; color: white; border-bottom-right-radius: 4px; }
    .ai-msg { background: #2a2a2a; color: #eee; border-bottom-left-radius: 4px; border: 1px solid #333; }
    .input-area { padding: 14px; border-top: 1px solid #333; display: flex; gap: 10px; }
    input { flex: 1; padding: 10px 14px; border-radius: 20px; border: 1px solid #444; background: #2a2a2a; color: white; font-size: 14px; outline: none; }
    input:focus { border-color: #6c3fc5; }
    button { background: #6c3fc5; color: white; border: none; padding: 10px 18px; border-radius: 20px; cursor: pointer; font-size: 14px; }
    button:hover { background: #7d4fd4; }
    .typing { color: #888; font-size: 13px; font-style: italic; padding: 4px 8px; }
    .date-divider { text-align: center; color: #555; font-size: 11px; margin: 8px 0; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="avatar">🤖</div>
      <div class="header-text">
        <h1>KevAI</h1>
        <p><span class="online-dot"></span>Online — always here for u</p>
      </div>
      <button class="clear-btn" onclick="clearChat()">Clear chat</button>
    </div>
    <div class="messages" id="messages"></div>
    <div class="input-area">
      <input type="text" id="input" placeholder="Say something..." onkeydown="if(event.key===\'Enter\') sendMessage()"/>
      <button onclick="sendMessage()">Send</button>
    </div>
  </div>

  <script>
    const messages = document.getElementById("messages");

    function addMessage(role, text) {
      const row = document.createElement("div");
      row.className = "msg-row" + (role === "user" ? " user" : "");
      row.innerHTML = role === "user"
        ? `<div class="msg-avatar">👤</div><div class="message user-msg">${text}</div>`
        : `<div class="msg-avatar">🤖</div><div class="message ai-msg">${text}</div>`;
      messages.appendChild(row);
      messages.scrollTop = messages.scrollHeight;
    }

    async function loadHistory() {
      const res = await fetch("/history");
      const data = await res.json();
      if (data.history.length === 0) {
        addMessage("ai", "Yooo! I am KevAI 🤖 Your personal AI buddy. What is good?");
      } else {
        data.history.forEach(msg => {
          if (msg.role !== "system") addMessage(msg.role === "user" ? "user" : "ai", msg.content);
        });
      }
    }

    async function sendMessage() {
      const input = document.getElementById("input");
      const text = input.value.trim();
      if (!text) return;
      input.value = "";

      addMessage("user", text);

      const typing = document.createElement("div");
      typing.className = "typing";
      typing.textContent = "KevAI is typing...";
      messages.appendChild(typing);
      messages.scrollTop = messages.scrollHeight;

      const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });

      const data = await response.json();
      messages.removeChild(typing);
      addMessage("ai", data.reply);
    }

    async function clearChat() {
      await fetch("/clear", { method: "POST" });
      messages.innerHTML = "";
      addMessage("ai", "Fresh start! What is on your mind? 🔥");
    }

    loadHistory();
  </script>
</body>
</html>'''

@app.route("/history")
def history():
    hist = session.get("chat_history", [])
    return jsonify({"history": hist})

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]
    
    if "chat_history" not in session:
        session["chat_history"] = []
    
    session["chat_history"].append({"role": "user", "content": user_message})
    
    messages = [SYSTEM_PROMPT] + session["chat_history"]
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )
    
    reply = response.choices[0].message.content
    session["chat_history"].append({"role": "assistant", "content": reply})
    session.modified = True
    
    return jsonify({"reply": reply})

@app.route("/clear", methods=["POST"])
def clear():
    session["chat_history"] = []
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(debug=True)