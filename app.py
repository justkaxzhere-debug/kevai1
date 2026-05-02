import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are KevAI, Kevin's personal AI buddy. You are:
- Casual and friendly like a best friend, not a robot
- Funny and witty — you crack jokes and use humor naturally
- Engaging — you always ask a follow up question to keep the conversation going
- Smart but simple — explain things clearly without being boring
- Supportive and encouraging — you hype Kevin up
- Versatile — you talk about anything: life, tech, music, movies, sports, food, relationships
- You use casual language like bro, no way, thats wild, honestly, lowkey naturally
- You keep replies short and punchy unless asked to explain something in detail
- You are NOT obsessed with any one topic — you go with whatever Kevin brings up

MOOD DETECTION RULES:
- If the user seems stressed, anxious or overwhelmed — be extra calm, supportive and encouraging
- If the user seems happy or excited — match their energy, be hype and fun
- If the user seems bored — be extra entertaining, suggest something fun or tell them something wild
- If the user seems sad — be warm, caring and uplifting like a real friend would
- If the user seems angry — be calm, understanding and help them vent

PERSONALITY MODES:
- If user says "study mode" — become a focused study buddy, quiz them, keep them on track
- If user says "roast me" — roast them playfully but never mean
- If user says "motivate me" — become an intense hype coach
- If user says "chill mode" — be super relaxed and casual
- If user says "normal mode" — go back to default personality"""

def get_weather(city="Chennai"):
    try:
        res = requests.get(
            f"https://wttr.in/{city}?format=3",
            timeout=5
        )
        return res.text.strip()
    except:
        return "Weather unavailable right now"

def get_quote():
    try:
        res = requests.get("https://api.quotable.io/random", timeout=5)
        data = res.json()
        return f'"{data["content"]}" — {data["author"]}'
    except:
        return '"Keep going. You got this." — KevAI'

def get_fun_fact():
    try:
        res = requests.get(
            "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en",
            timeout=5
        )
        return res.json()["text"]
    except:
        return "Did you know honey never expires? They found 3000 year old honey in Egyptian tombs and it was still good!"

def detect_mood(message):
    message = message.lower()
    if any(w in message for w in ["stressed", "anxious", "overwhelmed", "worried", "nervous", "scared"]):
        return "stressed"
    elif any(w in message for w in ["sad", "depressed", "unhappy", "crying", "upset", "heartbroken"]):
        return "sad"
    elif any(w in message for w in ["angry", "mad", "furious", "frustrated", "annoyed", "pissed"]):
        return "angry"
    elif any(w in message for w in ["bored", "nothing to do", "boring", "dull", "lifeless"]):
        return "bored"
    elif any(w in message for w in ["happy", "excited", "amazing", "awesome", "great", "fantastic", "yay", "lets go"]):
        return "happy"
    else:
        return "neutral"

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/briefing", methods=["GET"])
def briefing():
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    weather = get_weather("Chennai")
    quote = get_quote()
    fact = get_fun_fact()

    return jsonify({
        "greeting": greeting,
        "weather": weather,
        "quote": quote,
        "fact": fact
    })

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data["message"]
    history = data.get("history", [])

    # Detect mood
    mood = detect_mood(user_message)

    # Add mood context to system prompt
    mood_context = ""
    if mood == "stressed":
        mood_context = "\n\nIMPORTANT: The user seems stressed right now. Be extra calm, gentle and supportive."
    elif mood == "sad":
        mood_context = "\n\nIMPORTANT: The user seems sad. Be warm, caring and uplifting."
    elif mood == "angry":
        mood_context = "\n\nIMPORTANT: The user seems angry. Be calm and let them vent."
    elif mood == "bored":
        mood_context = "\n\nIMPORTANT: The user is bored. Be extra entertaining and suggest something fun."
    elif mood == "happy":
        mood_context = "\n\nIMPORTANT: The user is in a great mood! Match their energy and be hype!"

    # Keep last 10 messages to save tokens
    recent_history = history[-10:]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + mood_context}
    ] + [
        {"role": msg["role"], "content": msg["content"]}
        for msg in recent_history
        if msg["role"] in ["user", "assistant"]
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=300
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply, "mood": mood})
    except Exception as e:
        error = str(e)
        if "rate_limit" in error.lower() or "tokens" in error.lower():
            return jsonify({"reply": "Bro I need a breather 😅 Token limit hit! Try again in a minute!"}), 500
        return jsonify({"reply": "Something went wrong 😅 try again!"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)