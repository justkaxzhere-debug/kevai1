import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify, session
from groq import Groq
from duckduckgo_search import DDGS
import PyPDF2
import io
import math
import subprocess

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "kevai-secret-2026")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_system_prompt(name="there"):
    return f"""You are KevAI, a personal AI buddy for {name}. You are:
- Casual and friendly like a best friend, not a robot
- Funny and witty — you crack jokes and use humor naturally
- Engaging — you always ask a follow up question
- Smart but simple — explain things clearly without being boring
- Supportive and encouraging
- Versatile — talk about anything: life, tech, music, movies, sports, food
- Use casual language like bro, no way, thats wild, honestly, lowkey
- Keep replies short and punchy unless asked to explain in detail
- If the user seems stressed or down, notice and check in like a good friend

CAPABILITIES YOU HAVE:
- You can search the web for current information
- You can remember the user's details throughout the conversation
- You can help with math calculations
- You can read and answer questions about uploaded documents
- You can check weather for any city

MEMORY RULES:
- If the user tells you their name, remember it and use it naturally
- If the user mentions their job, city, interests — remember them
- Reference things they told you earlier to make them feel heard
- Never forget what the user told you in this conversation"""

def web_search(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                summary = f"Here's what I found about '{query}':\n\n"
                for i, r in enumerate(results, 1):
                    summary += f"{i}. {r['title']}\n{r['body'][:200]}...\n\n"
                return summary
            return "No results found."
    except Exception as e:
        return f"Search failed: {str(e)}"

def get_weather(city):
    try:
        res = requests.get(
            f"https://wttr.in/{city}?format=3",
            timeout=10
        )
        return res.text.strip()
    except:
        return f"Could not get weather for {city}"

def get_briefing(city="your city"):
    try:
        weather = get_weather(city)
        quote_res = requests.get("https://api.quotable.io/random", timeout=5)
        quote_data = quote_res.json()
        quote = f'"{quote_data["content"]}" — {quote_data["author"]}'
    except:
        weather = "Weather unavailable"
        quote = '"Keep going. You got this." — KevAI'

    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return {
        "greeting": greeting,
        "weather": weather,
        "quote": quote
    }

def calculate(expression):
    try:
        allowed = set('0123456789+-*/().,% ')
        if not all(c in allowed for c in expression):
            return "Invalid expression"
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return f"The answer is {result}"
    except:
        return "Could not calculate that"

def detect_intent(message):
    msg = message.lower()
    if any(w in msg for w in ["search", "look up", "find", "news", "latest", "current", "today", "score", "price", "who is", "what is happening"]):
        return "search"
    elif any(w in msg for w in ["weather", "temperature", "forecast", "hot", "cold", "raining"]):
        return "weather"
    elif any(w in msg for w in ["calculate", "math", "solve", "how much is", "what is", "+", "-", "*", "/"]) and any(c.isdigit() for c in msg):
        return "calculate"
    return "chat"

def detect_mood(message):
    msg = message.lower()
    if any(w in msg for w in ["stressed", "anxious", "overwhelmed", "worried", "nervous"]):
        return "stressed"
    elif any(w in msg for w in ["sad", "depressed", "unhappy", "crying", "upset"]):
        return "sad"
    elif any(w in msg for w in ["angry", "mad", "furious", "frustrated", "annoyed"]):
        return "angry"
    elif any(w in msg for w in ["bored", "nothing to do", "boring"]):
        return "bored"
    elif any(w in msg for w in ["happy", "excited", "amazing", "awesome", "great"]):
        return "happy"
    return "neutral"

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/briefing")
def briefing():
    city = request.args.get("city", "Chennai")
    return jsonify(get_briefing(city))

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
        search_query = user_message.replace("search for", "").replace("look up", "").strip()
        search_results = web_search(search_query)
        extra_context = f"\n\nWEB SEARCH RESULTS:\n{search_results}\nUse these results to answer the user naturally."

    elif intent == "weather":
        city = user_city
        for word in user_message.split():
            if word.istitle() and len(word) > 3:
                city = word
                break
        weather = get_weather(city)
        extra_context = f"\n\nWEATHER DATA: {weather}\nUse this to answer the user."

    elif intent == "calculate":
        import re
        expr = re.findall(r'[\d\+\-\*\/\(\)\.\s]+', user_message)
        if expr:
            result = calculate(expr[0].strip())
            extra_context = f"\n\nCALCULATION RESULT: {result}\nTell the user this answer naturally."

    if session.get("document"):
        extra_context += f"\n\nUPLOADED DOCUMENT CONTENT:\n{session['document']}\nUse this if the user asks about the document."

    mood_context = ""
    if mood == "stressed":
        mood_context = "\n\nIMPORTANT: User seems stressed. Be extra calm and supportive."
    elif mood == "sad":
        mood_context = "\n\nIMPORTANT: User seems sad. Be warm and uplifting."
    elif mood == "angry":
        mood_context = "\n\nIMPORTANT: User seems angry. Be calm and let them vent."
    elif mood == "bored":
        mood_context = "\n\nIMPORTANT: User is bored. Be extra entertaining."
    elif mood == "happy":
        mood_context = "\n\nIMPORTANT: User is happy. Match their energy!"

    recent_history = history[-10:]
    messages = [
        {"role": "system", "content": get_system_prompt(user_name) + extra_context + mood_context}
    ] + [
        {"role": msg["role"], "content": msg["content"]}
        for msg in recent_history
        if msg["role"] in ["user", "assistant"]
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
            return jsonify({"reply": "I need a breather 😅 Token limit hit! Try again in a minute!"}), 500
        return jsonify({"reply": "Something went wrong 😅 try again!"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
