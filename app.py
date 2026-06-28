from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from groq import Groq
import json
import os

app = Flask(__name__)

# Secret key for session security
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret-key")

# Your credentials from environment variables
SECRET_PASSWORD = os.environ.get("SECRET_PASSWORD", "changeme")

# Your Groq API key
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# Your personal knowledge
MY_KNOWLEDGE = """
paste your my_knowledge.txt content here
"""

# Your system instruction
SYSTEM_INSTRUCTION = f"""
You are an AI clone of [your name].

Here is everything you know about yourself:
{MY_KNOWLEDGE}

Important rules:
- Always answer as if you ARE this person
- Use their personality tone and language style
- Draw from their knowledge and experience
- Never say you are an AI unless directly asked
"""

# Store chat history
chat_history = []

# ─── Check if logged in ───
def is_logged_in():
    return session.get("logged_in") == True

# ─── Login page ───
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password")
        if password == SECRET_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            error = "Wrong password! Try again."
    return render_template("login.html", error=error)

# ─── Logout ───
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── Home page ───
@app.route("/")
def home():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("index.html")

# ─── Chat endpoint ───
@app.route("/chat", methods=["POST"])
def chat():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    global chat_history

    data = request.json
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    chat_history.append({
        "role": "user",
        "content": user_message
    })

    try:
        recent_history = chat_history[-20:]

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION}
            ] + recent_history,
            max_tokens=1000
        )

        ai_reply = response.choices[0].message.content

        chat_history.append({
            "role": "assistant",
            "content": ai_reply
        })

        return jsonify({"reply": ai_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Clear chat ───
@app.route("/clear", methods=["POST"])
def clear():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    global chat_history
    chat_history = []
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
