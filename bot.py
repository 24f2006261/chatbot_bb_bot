import os
import requests
from flask import Flask, request

# =====================
# CONFIG
# =====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

# Using Microsoft Phi-3 (Smart & Fast)
API_URL = "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct"

app = Flask(__name__)

def ask_ai(user_text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Prompt for Phi-3 to be human-like
    prompt = f"<|user|>\n{user_text}\n<|assistant|>\n"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 150, 
            "return_full_text": False,
            "temperature": 0.7
        }
    }

    try:
        # We only wait 8 seconds. If it takes longer, we stop to prevent crashing.
        response = requests.post(API_URL, headers=headers, json=payload, timeout=8)
        
        # SUCCESS
        if response.status_code == 200:
            return response.json()[0]["generated_text"].strip()
            
        # MODEL LOADING (503)
        elif response.status_code == 503:
            return "😴 I am waking up from cold sleep (free server!). Please wait 20 seconds and ask again."
            
        # AUTH ERROR (401)
        elif response.status_code == 401:
            return "❌ Error: Invalid Token. Please update HF_TOKEN in Render."

        else:
            return f"Error {response.status_code}: Try again."

    except requests.exceptions.Timeout:
        # If it takes too long, we tell you instead of crashing
        return "⏱️ Waking up is taking time... Wait 20s and ask again!"
        
    except Exception as e:
        return f"Error: {str(e)}"

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
                # Typing action...
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                # Get Reply
                reply = ask_ai(text)
                
                # Send Reply
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                
        return "ok", 200
    except:
        return "error", 200

# Set Webhook URL
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={RENDER_URL}"
    return requests.get(url).text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
