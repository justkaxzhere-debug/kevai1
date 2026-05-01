import os
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
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>KevAI</title>
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap");
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
      font-family: "Inter", sans-serif;
      background: #0a0a0f;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      overflow: hidden;
    }
    .bg-glow {
      position: fixed;
      width: 400px; height: 400px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(108,63,197,0.15), transparent 70%);
      top: -100px; left: 50%;
      transform: translateX(-50%);
      pointer-events: none;
    }
    .container {
      width: 420px; height: 700px;
      background: rgba(20,20,30,0.95);
      border-radius: 24px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid rgba(108,63,197,0.3);
      box-shadow: 0 0 40px rgba(108,63,197,0.15);
      position: relative;
      z-index: 1;
    }
    .header {
      background: linear-gradient(135deg, #6c3fc5, #4a2d8a);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .avatar-wrap { position: relative; }
    .avatar {
      width: 46px; height: 46px;
      border-radius: 50%;
      background: rgba(255,255,255,0.15);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      border: 2px solid rgba(255,255,255,0.3);
    }
    .status-dot {
      width: 10px; height: 10px;
      background: #4ade80;
      border-radius: 50%;
      position: absolute;
      bottom: 1px; right: 1px;
      border: 2px solid #4a2d8a;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.2); opacity: 0.8; }
    }
    .header-text { flex: 1; }
    .header-text h1 { color: white; font-size: 16px; font-weight: 600; }
    .header-text p { color: rgba(255,255,255,0.7); font-size: 11px; margin-top: 2px; }
    .header-actions { display: flex; gap: 8px; }
    .icon-btn {
      background: rgba(255,255,255,0.15);
      border: none;
      color: white;
      width: 32px; height: 32px;
      border-radius: 50%;
      cursor: pointer;
      font-size: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s;
    }
    .icon-btn:hover { background: rgba(255,255,255,0.25); }
    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      scroll-behavior: smooth;
    }
    .messages::-webkit-scrollbar { width: 3px; }
    .messages::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
    .msg-row {
      display: flex;
      align-items: flex-end;
      gap: 8px;
      animation: fadeUp 0.3s ease;
    }
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .msg-row.user { flex-direction: row-reverse; }
    .msg-avatar {
      width: 30px; height: 30px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      flex-shrink: 0;
      background: rgba(108,63,197,0.3);
    }
    .msg-row.user .msg-avatar { background: rgba(108,63,197,0.5); }
    .msg-content { display: flex; flex-direction: column; gap: 4px; max-width: 75%; }
    .msg-row.user .msg-content { align-items: flex-end; }
    .message {
      padding: 10px 14px;
      border-radius: 18px;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
    }
    .user-msg {
      background: linear-gradient(135deg, #6c3fc5, #8b5cf6);
      color: white;
      border-bottom-right-radius: 4px;
    }
    .ai-msg {
      background: rgba(255,255,255,0.07);
      color: #e8e8f0;
      border-bottom-left-radius: 4px;
      border: 1px solid rgba(255,255,255,0.08);
    }
    .msg-time {
      font-size: 10px;
      color: #555;
      padding: 0 4px;
    }
    .typing-row {
      display: flex;
      align-items: flex-end;
      gap: 8px;
      animation: fadeUp 0.3s ease;
    }
    .typing-bubble {
      background: rgba(255,255,255,0.07);
      border: 1px solid rgba(255,255,255,0.08);
      padding: 12px 16px;
      border-radius: 18px;
      border-bottom-left-radius: 4px;
      display: flex;
      gap: 5px;
      align-items: center;
    }
    .dot {
      width: 7px; height: 7px;
      background: #6c3fc5;
      border-radius: 50%;
      animation: bounce 1.2s infinite;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }
    .suggestions {
      display: flex;
      gap: 8px;
      padding: 0 16px 8px;
      overflow-x: auto;
      flex-shrink: 0;
    }
    .suggestions::-webkit-scrollbar { display: none; }
    .suggestion-chip {
      background: rgba(108,63,197,0.15);
      border: 1px solid rgba(108,63,197,0.3);
      color: #a78bfa;
      padding: 6px 14px;
      border-radius: 99px;
      font-size: 12px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
      flex-shrink: 0;
    }
    .suggestion-chip:hover {
      background: rgba(108,63,197,0.3);
      color: white;
    }
    .input-area {
      padding: 12px 16px 16px;
      border-top: 1px solid rgba(255,255,255,0.06);
      display: flex;
      gap: 10px;
      align-items: center;
    }
    input {
      flex: 1;
      padding: 12px 16px;
      border-radius: 99px;
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(255,255,255,0.05);
      color: white;
      font-size: 14px;
      outline: none;
      font-family: "Inter", sans-serif;
      transition: border 0.2s;
    }
    input::placeholder { color: #555; }
    input:focus { border-color: rgba(108,63,197,0.6); background: rgba(108,63,197,0.05); }
    .send-btn {
      width: 44px; height: 44px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6c3fc5, #8b5cf6);
      border: none;
      color: white;
      font-size: 18px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s, opacity 0.2s;
      flex-shrink: 0;
    }
    .send-btn:hover { transform: scale(1.05); }
    .send-btn:active { transform: scale(0.95); }
    .empty-state {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      color: #444;
      font-size: 13px;
    }
    .empty-state .big-emoji { font-size: 40px; margin-bottom: 8px; }
  </style>
</head>
<body>
<div class="bg-glow"></div>
<div class="container">
  <div class="header">
    <div class="avatar-wrap">
      <div class="avatar">🤖</div>
      <div class="status-dot"></div>
    </div>
    <div class="header-text">
      <h1>KevAI</h1>
      <p>Your personal AI buddy — always online</p>
    </div>
    <div class="header-actions">
      <button class="icon-btn" onclick="clearChat()" title="Clear chat">🗑️</button>
    </div>
  </div>

  <div class="messages" id="messages">
    <div class="empty-state" id="empty-state">
      <div class="big-emoji">👋</div>
      <div style="color:#777; font-weight:500;">Hey Kevin! Start a convo</div>
      <div style="color:#444; font-size:12px;">I am always here bro</div>
    </div>
  </div>

  <div class="suggestions" id="suggestions">
    <div class="suggestion-chip" onclick="sendSuggestion(this)">What should I do today?</div>
    <div class="suggestion-chip" onclick="sendSuggestion(this)">Tell me something wild</div>
    <div class="suggestion-chip" onclick="sendSuggestion(this)">Roast me a little 😂</div>
    <div class="suggestion-chip" onclick="sendSuggestion(this)">Motivate me bro</div>
    <div class="suggestion-chip" onclick="sendSuggestion(this)">I am bored, help</div>
  </div>

  <div class="input-area">
    <input type="text" id="input" placeholder="Say something..." onkeydown="if(event.key===\'Enter\') sendMessage()"/>
    <button class="send-btn" onclick="sendMessage()">➤</button>
  </div>
</div>

<script>
  const messagesEl = document.getElementById("messages");
  const emptyState = document.getElementById("empty-state");
  const suggestionsEl = document.getElementById("suggestions");

  function getTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function removeEmpty() {
    if (emptyState) emptyState.remove();
    suggestionsEl.style.display = "none";
  }

  function addMessage(role, text) {
    removeEmpty();
    const row = document.createElement("div");
    row.className = "msg-row" + (role === "user" ? " user" : "");
    row.innerHTML = role === "user"
      ? `<div class="msg-avatar">👤</div>
         <div class="msg-content">
           <div class="message user-msg">${text}</div>
           <div class="msg-time">${getTime()}</div>
         </div>`
      : `<div class="msg-avatar">🤖</div>
         <div class="msg-content">
           <div class="message ai-msg">${text}</div>
           <div class="msg-time">${getTime()}</div>
         </div>`;
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function showTyping() {
    const row = document.createElement("div");
    row.className = "typing-row";
    row.id = "typing";
    row.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="typing-bubble">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>`;
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById("typing");
    if (t) t.remove();
  }

  async function sendMessage() {
    const input = document.getElementById("input");
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMessage("user", text);
    showTyping();
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      removeTyping();
      addMessage("ai", data.reply);
    } catch(e) {
      removeTyping();
      addMessage("ai", "Bro something went wrong on my end 😅 try again!");
    }
  }

  function sendSuggestion(el) {
    document.getElementById("input").value = el.textContent;
    sendMessage();
  }

  async function clearChat() {
    await fetch("/clear", { method: "POST" });
    messagesEl.innerHTML = `
      <div class="empty-state" id="empty-state">
        <div class="big-emoji">👋</div>
        <div style="color:#777; font-weight:500;">Fresh start! What is on your mind?</div>
      </div>`;
    suggestionsEl.style.display = "flex";
  }

  async function loadHistory() {
    const res = await fetch("/history");
    const data = await res.json();
    if (data.history && data.history.length > 0) {
      data.history.forEach(msg => {
        if (msg.role !== "system") {
          addMessage(msg.role === "user" ? "user" : "ai", msg.content);
        }
      });
    }
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