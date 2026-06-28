from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from groq import Groq
import json
import os
import base64
import fitz
from datetime import datetime

app = Flask(__name__, static_folder='static')

# Secret key for session security
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret-key")

# Your credentials
SECRET_PASSWORD = os.environ.get("SECRET_PASSWORD", "changeme")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Set up Groq client
client = Groq(api_key=GROQ_API_KEY)

# Knowledge file
KNOWLEDGE_FILE = "my_knowledge.txt"

# ─── Load knowledge ───
def load_knowledge():
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r") as f:
            return f.read()
    return "No knowledge loaded yet."

# ─── Save knowledge ───
def save_knowledge(new_info):
    existing = load_knowledge()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    updated = existing + f"\n\n[Learned on {timestamp}]\n{new_info}"
    with open(KNOWLEDGE_FILE, "w") as f:
        f.write(updated)
    return updated

# ─── Build system instruction ───
def build_system_instruction():
    knowledge = load_knowledge()
    return f"""
You are an AI clone of [your name].

Here is everything you know about yourself:
{knowledge}

Important rules:
- Always answer as if you ARE this person
- Use their personality tone and language style
- Draw from their knowledge and experience
- Never say you are an AI unless directly asked

Memory rules:
- If the user says "remember", "save", "learn"
  or "add to knowledge" extract the key information
  and reply with exactly:
  SAVE_KNOWLEDGE: [the information to save]
- Otherwise just chat normally
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
    image_data = data.get("image", None)
    pdf_text = data.get("pdf_text", None)

    if not user_message and not image_data and not pdf_text:
        return jsonify({"error": "No input provided"}), 400

    try:
        # ─── Handle image ───
        if image_data:
            image_bytes = base64.b64decode(image_data["data"])
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_data['type']};base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": user_message if user_message else "What is in this image? Describe it in detail."
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            ai_reply = response.choices[0].message.content
            chat_history.append({"role": "user", "content": f"[Sent an image] {user_message}"})
            chat_history.append({"role": "assistant", "content": ai_reply})
            return jsonify({"reply": ai_reply})

        # ─── Handle PDF ───
        if pdf_text:
            full_message = f"""
The user has shared a PDF document. Here is the content:

{pdf_text[:4000]}

User question: {user_message if user_message else 'Please summarise this document.'}
"""
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": build_system_instruction()},
                    {"role": "user", "content": full_message}
                ],
                max_tokens=1000
            )

            ai_reply = response.choices[0].message.content
            chat_history.append({"role": "user", "content": f"[Sent a PDF] {user_message}"})
            chat_history.append({"role": "assistant", "content": ai_reply})
            return jsonify({"reply": ai_reply})

        # ─── Handle normal text chat ───
        chat_history.append({
            "role": "user",
            "content": user_message
        })

        recent_history = chat_history[-20:]

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": build_system_instruction()}
            ] + recent_history,
            max_tokens=1000
        )

        ai_reply = response.choices[0].message.content

        # ─── Check if AI wants to save knowledge ───
        if ai_reply.startswith("SAVE_KNOWLEDGE:"):
            new_info = ai_reply.replace("SAVE_KNOWLEDGE:", "").strip()
            save_knowledge(new_info)
            ai_reply = f"✅ Got it! I have saved this to my knowledge:\n\n'{new_info}'\n\nI will remember this forever!"

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
