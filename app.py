import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq
from duckduckgo_search import DDGS
import PyPDF2
import io
import math
import base64
from PIL import Image
import io as io_module

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "kevai-secret-2026")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///kevai.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ===== MODELS =====
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(80), default="Chennai")
    theme = db.Column(db.String(20), default="dark")
    personality = db.Column(db.String(200), default="casual")
    ai_name = db.Column(db.String(50), default="KevAI")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship("Message", backref="user", lazy=True)
    conversations = db.relationship("Conversation", backref="user", lazy=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(100), default="New Chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_shared = db.Column(db.Boolean, default=False)
    share_code = db.Column(db.String(20), unique=True, nullable=True)
    messages = db.relationship("Message", backref="conversation", lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ===== AI HELPERS =====
def get_system_prompt(user):
    personality_map = {
        "casual": "casual and funny like a best friend",
        "professional": "professional, smart and concise like a business advisor",
        "coach": "motivating and intense like a life coach",
        "tutor": "patient and educational like a teacher",
        "sarcastic": "witty and playfully sarcastic like a funny friend"
    }
    style = personality_map.get(user.personality, "casual and friendly")
    return f"""You are {user.ai_name}, a personal AI buddy for {user.username}. 
You are {style}.
- Keep replies short and punchy unless asked to explain in detail
- Always ask a follow up question to keep conversation going
- Remember what the user tells you and reference it naturally
- If user seems stressed or down, be supportive like a real friend
- Never be robotic or boring"""

def web_search(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                summary = f"Search results for '{query}':\n\n"
                for i, r in enumerate(results, 1):
                    summary += f"{i}. {r['title']}\n{r['body'][:200]}...\n\n"
                return summary
        return "No results found."
    except Exception as e:
        return f"Search failed: {str(e)}"

def get_weather(city):
    try:
        geo = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1",
            timeout=8
        ).json()
        if not geo.get("results"):
            return f"Could not find {city}"
        r = geo["results"][0]
        lat, lon = r["latitude"], r["longitude"]
        w = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true",
            timeout=8
        ).json()["current_weather"]
        codes = {
            0:"☀️ Clear",1:"🌤️ Mainly clear",2:"⛅ Partly cloudy",
            3:"☁️ Overcast",45:"🌫️ Foggy",51:"🌦️ Drizzle",
            61:"🌧️ Light rain",63:"🌧️ Rain",65:"🌧️ Heavy rain",
            80:"🌦️ Showers",95:"⛈️ Thunderstorm"
        }
        condition = codes.get(w["weathercode"], "🌡️ Clear")
        return f"{city}: {condition}, {w['temperature']}°C, Wind {w['windspeed']} km/h"
    except:
        return f"{city}: Weather unavailable right now"

def detect_intent(message):
    msg = message.lower()
    if any(w in msg for w in ["generate image","create image","draw","paint","make an image","show me a picture","generate a picture","create a picture","imagine","visualize","make art"]):
        return "image"
    elif any(w in msg for w in ["search","look up","find","news","latest","current","today","score","price","who is","what is happening"]):
        return "search"
    elif any(w in msg for w in ["weather","temperature","forecast","hot","cold","raining"]):
        return "weather"
    elif any(w in msg for w in ["calculate","math","solve","how much is"]) and any(c.isdigit() for c in msg):
        return "calculate"
    return "chat"

def detect_mood(message):
    msg = message.lower()
    if any(w in msg for w in ["stressed","anxious","overwhelmed","worried"]):
        return "stressed"
    elif any(w in msg for w in ["sad","depressed","unhappy","crying","upset"]):
        return "sad"
    elif any(w in msg for w in ["angry","mad","furious","frustrated"]):
        return "angry"
    elif any(w in msg for w in ["bored","nothing to do","boring"]):
        return "bored"
    elif any(w in msg for w in ["happy","excited","amazing","awesome","great"]):
        return "happy"
    return "neutral"

def calculate(expression):
    try:
        allowed = set("0123456789+-*/().,% ")
        if not all(c in allowed for c in expression):
            return "Invalid expression"
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return f"The answer is {result}"
    except:
        return "Could not calculate that"

import random, string
def generate_share_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_image(prompt):
    try:
        hf_key = os.environ.get("HF_API_KEY")
        if not hf_key:
            return None, "No Hugging Face API key set"
        
        # Using Stable Diffusion XL — best free model
        response = requests.post(
            "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
            headers={"Authorization": f"Bearer {hf_key}"},
            json={"inputs": prompt},
            timeout=60
        )
        
        if response.status_code == 200:
            # Convert image bytes to base64
            img_data = base64.b64encode(response.content).decode("utf-8")
            return img_data, None
        elif response.status_code == 503:
            return None, "Model is loading, try again in 20 seconds"
        else:
            return None, f"Generation failed: {response.status_code}"
    except Exception as e:
        return None, str(e)

# ===== ROUTES =====
@app.route("/")
def home():
    return open("index.html").read()

@app.route("/auth")
def auth_page():
    return open("auth.html").read()

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 400
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 400
    user = User(
        username=data["username"],
        email=data["email"],
        password=generate_password_hash(data["password"]),
        city=data.get("city", "Chennai"),
        personality=data.get("personality", "casual"),
        ai_name=data.get("ai_name", "KevAI")
    )
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"success": True, "username": user.username})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()
    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401
    login_user(user)
    return jsonify({"success": True, "username": user.username})

@app.route("/logout")
def logout():
    logout_user()
    return jsonify({"success": True})

@app.route("/me")
@login_required
def me():
    return jsonify({
        "username": current_user.username,
        "city": current_user.city,
        "theme": current_user.theme,
        "personality": current_user.personality,
        "ai_name": current_user.ai_name
    })

@app.route("/update-profile", methods=["POST"])
@login_required
def update_profile():
    data = request.json
    if "city" in data: current_user.city = data["city"]
    if "theme" in data: current_user.theme = data["theme"]
    if "personality" in data: current_user.personality = data["personality"]
    if "ai_name" in data: current_user.ai_name = data["ai_name"]
    db.session.commit()
    return jsonify({"success": True})

@app.route("/conversations")
@login_required
def get_conversations():
    convos = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.created_at.desc()).all()
    return jsonify([{
        "id": c.id,
        "title": c.title,
        "created_at": c.created_at.strftime("%b %d"),
        "is_shared": c.is_shared,
        "share_code": c.share_code
    } for c in convos])

@app.route("/conversations/new", methods=["POST"])
@login_required
def new_conversation():
    convo = Conversation(user_id=current_user.id, title="New Chat")
    db.session.add(convo)
    db.session.commit()
    session["conversation_id"] = convo.id
    return jsonify({"id": convo.id})

@app.route("/conversations/<int:convo_id>")
@login_required
def load_conversation(convo_id):
    convo = Conversation.query.filter_by(id=convo_id, user_id=current_user.id).first()
    if not convo:
        return jsonify({"error": "Not found"}), 404
    session["conversation_id"] = convo_id
    messages = Message.query.filter_by(conversation_id=convo_id).order_by(Message.created_at).all()
    return jsonify([{"role": m.role, "content": m.content} for m in messages])

@app.route("/conversations/<int:convo_id>/share", methods=["POST"])
@login_required
def share_conversation(convo_id):
    convo = Conversation.query.filter_by(id=convo_id, user_id=current_user.id).first()
    if not convo:
        return jsonify({"error": "Not found"}), 404
    if not convo.share_code:
        convo.share_code = generate_share_code()
    convo.is_shared = True
    db.session.commit()
    return jsonify({"share_code": convo.share_code})

@app.route("/shared/<share_code>")
def view_shared(share_code):
    convo = Conversation.query.filter_by(share_code=share_code, is_shared=True).first()
    if not convo:
        return "Conversation not found", 404
    messages = Message.query.filter_by(conversation_id=convo.id).order_by(Message.created_at).all()
    html = f"""<!DOCTYPE html>
<html><head><title>Shared Chat</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<style>
  body {{ font-family: Inter, sans-serif; background:#0a0a0f; color:#eee; max-width:600px; margin:0 auto; padding:20px; }}
  h2 {{ color:#a78bfa; margin-bottom:20px; }}
  .msg {{ padding:10px 14px; border-radius:16px; margin:8px 0; max-width:80%; font-size:14px; line-height:1.5; }}
  .user {{ background:#6c3fc5; color:white; margin-left:auto; text-align:right; }}
  .assistant {{ background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); }}
  .label {{ font-size:11px; color:#888; margin:4px 8px; }}
</style></head><body>
<h2>💬 Shared Conversation</h2>"""
    for m in messages:
        if m.role != "system":
            html += f'<div class="label">{"You" if m.role=="user" else "AI"}</div>'
            html += f'<div class="msg {m.role}">{m.content}</div>'
    html += "</body></html>"
    return html

@app.route("/briefing")
def briefing():
    city = request.args.get("city", "Chennai")
    try:
        weather = get_weather(city)
        quote_res = requests.get("https://api.quotable.io/random", timeout=5)
        quote = f'"{quote_res.json()["content"]}" — {quote_res.json()["author"]}'
    except:
        weather = "Weather unavailable"
        quote = '"Keep going. You got this." — KevAI'
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    return jsonify({"greeting": greeting, "weather": weather, "quote": quote})

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files["file"]
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        session["document"] = text[:3000]
        return jsonify({"success": True, "pages": len(pdf_reader.pages)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    data = request.json
    user_message = data["message"]
    history = data.get("history", [])

    mood = detect_mood(user_message)
    intent = detect_intent(user_message)
    extra_context = ""

    if intent == "search":
        results = web_search(user_message)
        extra_context = f"\n\nWEB SEARCH RESULTS:\n{results}"
    elif intent == "weather":
        city = current_user.city
        extra_context = f"\n\nWEATHER: {get_weather(city)}"
    elif intent == "calculate":
        import re
        expr = re.findall(r"[\d\+\-\*\/\(\)\.\s]+", user_message)
        if expr:
            extra_context = f"\n\nCALCULATION: {calculate(expr[0].strip())}"

    if session.get("document"):
        extra_context += f"\n\nDOCUMENT:\n{session['document']}"

    mood_context = {
        "stressed": "\n\nUser seems stressed. Be extra calm and supportive.",
        "sad": "\n\nUser seems sad. Be warm and uplifting.",
        "angry": "\n\nUser seems angry. Be calm and let them vent.",
        "bored": "\n\nUser is bored. Be extra entertaining.",
        "happy": "\n\nUser is happy. Match their energy!"
    }.get(mood, "")

    recent_history = history[-10:]
    messages = [
        {"role": "system", "content": get_system_prompt(current_user) + extra_context + mood_context}
    ] + [
        {"role": m["role"], "content": m["content"]}
        for m in recent_history
        if m["role"] in ["user", "assistant"]
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=400
        )
        reply = response.choices[0].message.content

        # Save to database
        convo_id = session.get("conversation_id")
        if convo_id:
            db.session.add(Message(
                user_id=current_user.id,
                conversation_id=convo_id,
                role="user",
                content=user_message
            ))
            db.session.add(Message(
                user_id=current_user.id,
                conversation_id=convo_id,
                role="assistant",
                content=reply
            ))
            # Auto update conversation title
            convo = Conversation.query.get(convo_id)
            if convo and convo.title == "New Chat":
                convo.title = user_message[:40] + "..." if len(user_message) > 40 else user_message
            db.session.commit()

        return jsonify({"reply": reply, "mood": mood, "intent": intent})
    except Exception as e:
        error = str(e)
        if "rate_limit" in error.lower():
            return jsonify({"reply": "Token limit hit! Try again in a minute 😅"}), 500
        return jsonify({"reply": "Something went wrong 😅 try again!"}), 500

with app.app_context():
    db.create_all()

from flask import send_from_directory

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")

@app.route("/sw.js")
def service_worker():
    response = send_from_directory("static", "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
