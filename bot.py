import os
import requests
import time
from flask import Flask, request

# =====================
# SETTINGS
# =====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

# We use "TinyLlama" because it is fast, free, and talks simply (not like a robot)
API_URL = "https://api-inference.huggingface.co/models/TinyLlama/TinyLlama-1.1B-Chat-v1.0"

app = Flask(__name__)

def ask_ai(user_text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # THIS PART MAKES IT HUMAN
    # We tell the AI: "You are a friend. Keep it short."
    prompt = f"""<|system|>
You are a helpful friend. You help with studies, diet, and life. 
Speak in simple, short text messages. No big words. Be kind.<|end|>
<|user|>
{user_text}<|end|>
<|assistant|>
"""
    
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 200, "return_full_text": False}
    }

    # Try 3 times to connect (in case server is busy)
    for i in range(3):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                return response.json()[0]["generated_text"].strip()
            time.sleep(2) # Wait 2 seconds and try again
        except:
            pass
            
    return "Network is slow... ask me again?"

# =====================
# WEBHOOK (The Bridge)
# =====================
@app.route("/", methods=["POST"])
def telegram():
    try:
        data = request.get_json(force=True)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            if text:
                # Show "typing..."
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                # Get Answer
                reply = ask_ai(text)
                
                # Send Answer
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                
        return "ok", 200
    except:
        return "error", 200

# Run this ONCE in browser: https://your-app.onrender.com/set_webhook
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={RENDER_URL}"
    return requests.get(url).text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
