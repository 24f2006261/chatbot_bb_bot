import os
import requests
import json
from flask import Flask, request

# =====================
# ENV VARIABLES
# =====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Using Llama 3 8B (Smarter & Faster for logic/chat)
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"

app = Flask(__name__)

# =====================
# MEMORY (Simple RAM Storage)
# =====================
# Stores last 10 messages per user to maintain context
user_histories = {} 

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def update_history(user_id, role, content):
    if user_id not in user_histories:
        user_histories[user_id] = []
    # Append new message
    user_histories[user_id].append({"role": role, "content": content})
    # Keep only last 10 messages to save tokens/memory
    if len(user_histories[user_id]) > 10:
        user_histories[user_id].pop(0)

# =====================
# SEND MESSAGE
# =====================
def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=15
    )

# =====================
# AI LOGIC
# =====================
def ask_ai(user_id, user_text):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Retrieve History
    history = get_history(user_id)
    
    # 2. Build Prompt with System Context
    # We use a special format for Llama 3 to understand it's a chat
    messages = [
        {
            "role": "system", 
            "content": (
                "You are a smart, friendly AI companion. "
                "You help with diet planning, studies, and life decisions. "
                "Keep answers concise and readable for small screens. "
                "Be human-like, empathetic, and practical."
            )
        }
    ]
    
    # Add past conversation
    for msg in history:
        messages.append(msg)
    
    # Add current user message
    messages.append({"role": "user", "content": user_text})

    payload = {
        "inputs": str(messages), # HuggingFace sometimes needs raw string or specific formatting depending on endpoint
        # For HF Inference API standard, we often send the raw prompt string constructed manually for best results:
        # But let's try the structured way or fallback to prompt engineering below.
        "parameters": {
            "max_new_tokens": 400,
            "temperature": 0.7,
            "top_p": 0.9,
            "return_full_text": False
        }
    }

    # *Manual Prompt Construction for Llama 3 (More reliable on free tier)*
    # Llama 3 uses <|begin_of_text|><|start_header_id|>... format
    full_prompt = "<|begin_of_text|>"
    for m in messages:
        full_prompt += f"<|start_header_id|>{m['role']}<|end_header_id|>\n\n{m['content']}<|eot_id|>"
    full_prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    
    payload["inputs"] = full_prompt

    # 3. Call API
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        
        # Handle "Model Loading" (503 Error)
        if response.status_code == 503:
            return "Brains are warming up... wait 20s and try again! 🧠"
            
        if response.status_code != 200:
            return f"Error: {response.status_code}. Try again."

        data = response.json()
        
        if isinstance(data, list) and "generated_text" in data[0]:
            bot_reply = data[0]["generated_text"].replace(full_prompt, "").strip()
            
            # Save to memory
            update_history(user_id, "user", user_text)
            update_history(user_id, "assistant", bot_reply)
            
            return bot_reply
            
        return "I heard you, but I'm confused. Say again?"
        
    except Exception as e:
        print(e)
        return "Connection glitch. Try again."

# =====================
# ROUTES
# =====================
@app.route("/", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            user_id = data["message"]["from"]["id"]
            
            if "text" in data["message"]:
                user_text = data["message"]["text"]
                
                # Show "typing..." status (Optional UX improvement)
                requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                ai_reply = ask_ai(user_id, user_text)
                send_message(chat_id, ai_reply)
                
        return "ok", 200
    except Exception as e:
        print(f"Error: {e}")
        return "error", 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    # Call this URL manually once from your browser to fix the connection
    url = f"{RENDER_EXTERNAL_URL}"
    s = requests.get(f"{TELEGRAM_API}/setWebhook?url={url}")
    if s.status_code == 200:
        return "Webhook Set Successfully! Bot should work now.", 200
    else:
        return f"Webhook setup failed: {s.text}", 400

@app.route("/", methods=["GET"])
def index():
    return "Bot is Alive. Go to /set_webhook to connect Telegram."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
