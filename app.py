from flask import Flask, request, jsonify, render_template
from groq import Groq
import json
import os

app = Flask(__name__)

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

# Store chat history in memory
chat_history = []

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    global chat_history
    
    data = request.json
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    # Add user message to history
    chat_history.append({
        "role": "user",
        "content": user_message
    })
    
    try:
        # Keep last 20 messages only
        recent_history = chat_history[-20:]
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION}
            ] + recent_history,
            max_tokens=1000
        )
        
        ai_reply = response.choices[0].message.content
        
        # Add AI reply to history
        chat_history.append({
            "role": "assistant",
            "content": ai_reply
        })
        
        return jsonify({"reply": ai_reply})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clear", methods=["POST"])
def clear():
    global chat_history
    chat_history = []
    return jsonify({"status": "cleared"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
