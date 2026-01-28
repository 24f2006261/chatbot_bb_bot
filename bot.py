import os
import requests
import time
from flask import Flask, request

# =====================
# CONFIGURATION
# =====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

# "OLD RELIABLE" MODELS (These rarely give 410 or 503 errors)
# 1. BlenderBot (Facebook): Made for chat, very fast.
# 2. DialoGPT (Microsoft): Good conversationalist.
MODELS = [
    "https://api-inference.huggingface.co/models/facebook/blenderbot-400M-distill",
    "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
]

app = Flask(__name__)

# =====================
# AI LOGIC
# =====================
def ask_ai(user_text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Payload designed for Chat Models
    payload = {
        "inputs": user_text,
        "parameters": {
            "max_new_tokens": 100, # Keep it short for Blackberry
            "return_full_text": False
        }
    }

    errors_log = []

    for model_url in MODELS:
        try:
            print(f"Trying {model_url}...")
            response = requests.post(model_url, headers=headers, json=payload, timeout=25)
            
            # 1. SUCCESS
            if response.status_code == 200:
                data = response.json()
                
                # BlenderBot/DialoGPT return format is sometimes different
                if isinstance(data, list) and "generated_text" in data[0]:
                    return data[0]["generated_text"].strip()
                elif isinstance(data, dict) and "generated_text" in data:
                    return data["generated_text"].strip()
                else:
                    return str(data) # Fallback

            # 2. LOADING (503)
            elif response.status_code == 503:
                time.sleep(15)
                # Quick Retry
                response = requests.post(model_url, headers=headers, json=payload, timeout=25)
                if response.status_code == 200:
                     return response.json()[0]["generated_text"].strip()

            # 3. TOKEN ERROR (401)
            elif response.status_code == 401:
                return "❌ Error: Invalid Token. Check Render Settings."

            else:
                errors_log.append(f"Status {response.status_code}")
                continue
                
        except Exception as e:
            errors_log.append(str(e))
            continue

    # FALLBACK IF EVERYTHING FAILS
    # This ensures the bot ALWAYS replies, even if AI is broken.
    return "I'm having trouble connecting to my brain, but I'm online! 🤖"

# =====================
# WEBHOOK
# =====================
@app.route("/", methods=["POST"])
def telegram():
    try:
        data = request.get_json(force=True)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            if text:
                # Typing...
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                # Get Reply
                reply = ask_ai(text)
                
                # Send Reply
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                
        return "ok", 200
    except:
        return "error", 200

# RESET WEBHOOK
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={RENDER_URL}"
    return requests.get(url).text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
