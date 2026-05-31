import os
import requests
import math
import re
import io
from datetime import datetime
from flask import Flask, request, jsonify, session, send_from_directory
from groq import Groq
from duckduckgo_search import DDGS
import PyPDF2

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "kevai-secret-2026")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ===== SYSTEM PROMPT =====
def get_system_prompt(name="there"):
    return f"""You are KevAI, a personal AI buddy for {name}. You are:
- Casual and funny like a best friend, not a robot
- Witty — you crack jokes and use humor naturally
- Engaging — you always ask a follow up question
- Smart but simple — explain things clearly without being boring
- Supportive and encouraging
- Versatile — talk about anything: life, tech, music, movies, sports, food
- Use casual language like bro, no way, thats wild, honestly, lowkey
- Keep replies short and punchy unless asked to explain in detail
- Never be robotic or boring
- You can search the web, check weather and do math"""

# ===== HELPERS =====
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
            return f"Could not find weather for {city}"
        r = geo["results"][0]
        lat, lon = r["latitude"], r["longitude"]
        w = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true",
            timeout=8
        ).json()["current_weather"]
        codes = {
            0:"☀️ Clear", 1:"🌤️ Mainly clear", 2:"⛅ Partly cloudy",
            3:"☁️ Overcast", 45:"🌫️ Foggy", 51:"🌦️ Drizzle",
            61:"🌧️ Light rain", 63:"🌧️ Rain", 65:"🌧️ Heavy rain",
            80:"🌦️ Showers", 95:"⛈️ Thunderstorm"
        }
        condition = codes.get(w["weathercode"], "🌡️ Clear")
        return f"{city}: {condition}, {w['temperature']}°C, Wind {w['windspeed']} km/h"
    except:
        return f"{city}: Weather unavailable right now"

def detect_intent(message):
    msg = message.lower()
    if any(w in msg for w in ["search", "look up", "find", "news", "latest",
                                "current", "today", "score", "price", "who is",
                                "what is happening"]):
        return "search"
    elif any(w in msg for w in ["weather", "temperature", "forecast", "hot", "cold", "raining"]):
        return "weather"
    elif any(w in msg for w in ["calculate", "math", "solve", "how much is"]) and any(c.isdigit() for c in msg):
        return "calculate"
    return "chat"

def detect_mood(message):
    msg = message.lower()
    if any(w in msg for w in ["stressed", "anxious", "overwhelmed", "worried"]):
        return "stressed"
    elif any(w in msg for w in ["sad", "depressed", "unhappy", "crying", "upset"]):
        return "sad"
    elif any(w in msg for w in ["angry", "mad", "furious", "frustrated"]):
        return "angry"
    elif any(w in msg for w in ["bored", "nothing to do", "boring"]):
        return "bored"
    elif any(w in msg for w in ["happy", "excited", "amazing", "awesome", "great"]):
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

# ===== ROUTES =====
@app.route("/")
def home():
    return open("index.html").read()

@app.route("/briefing")
def briefing():
    city = request.args.get("city", "Chennai")
    try:
        weather = get_weather(city)
        quote_res = requests.get("https://api.quotable.io/random", timeout=5)
        quote = f'"{quote_res.json()["content"]}" — {quote_res.json()["author"]}'
    except:
        weather = get_weather(city)
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
def chat():
    data = request.json
    user_message = data["message"]
    history = data.get("history", [])
    user_name = data.get("userName", "there")
    user_city = data.get("userCity", "Chennai")

    mood = detect_mood(user_message)
    intent = detect_intent(user_message)
    extra_context = ""

    if intent == "search":
        results = web_search(user_message)
        extra_context = f"\n\nWEB SEARCH RESULTS:\n{results}"
    elif intent == "weather":
        extra_context = f"\n\nWEATHER: {get_weather(user_city)}"
    elif intent == "calculate":
        expr = re.findall(r"[\d\+\-\*\/\(\)\.\s]+", user_message)
        if expr:
            extra_context = f"\n\nCALCULATION: {calculate(expr[0].strip())}"

    if session.get("document"):
        extra_context += f"\n\nDOCUMENT:\n{session['document']}"

    mood_context = {
        "stressed": "\n\nUser seems stressed. Be extra calm and supportive.",
        "sad":      "\n\nUser seems sad. Be warm and uplifting.",
        "angry":    "\n\nUser seems angry. Be calm and let them vent.",
        "bored":    "\n\nUser is bored. Be extra entertaining.",
        "happy":    "\n\nUser is happy. Match their energy!"
    }.get(mood, "")

    recent_history = history[-10:]
    messages = [
        {"role": "system", "content": get_system_prompt(user_name) + extra_context + mood_context}
    ] + [
        {"role": m["role"], "content": m["content"]}
        for m in recent_history if m["role"] in ["user", "assistant"]
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=400
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply, "mood": mood, "intent": intent})
    except Exception as e:
        error = str(e)
        if "rate_limit" in error.lower():
            return jsonify({"reply": "Token limit hit! Try again in a minute 😅"}), 500
        return jsonify({"reply": "Something went wrong 😅 try again!"}), 500

# ===== PWA ROUTES =====
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
   app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
