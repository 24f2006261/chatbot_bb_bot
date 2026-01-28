import os
import requests
import time
from flask import Flask, request

# =====================
# CONFIG
# =====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")

# LIST OF NON-GATED (PUBLIC) MODELS
# These models do not require "Agree to Terms" so they won't give Error 410.
MODELS = [
    "https://api-inference.huggingface.co/models/TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-0.5B-Instruct",
    "https://api-inference.huggingface.co/models/facebook/blenderbot-400M-distill"
]

app = Flask(__name__)

# =====================
# AI LOGIC
# =====================
def ask_ai(user_text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # We use a simple structure that works for all models
    payload = {
        "inputs": f"User: {user_text}\nAssistant:",
        "parameters": {"max_new_tokens": 250, "return_full_text": False}
    }

    # Loop through the list until one works
    for model_url in MODELS:
        try:
            print(f"Trying {model_url}...")
            response = requests.post(model_url, headers=headers, json=payload, timeout=20)
            
            # SUCCESS (200)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and "generated_text" in data[0]:
                    return data[0]["generated_text"].strip()
                elif isinstance(data, dict) and "generated_text" in data:
                     return data["generated_text"].strip()
                else:
                    return str(data)

            # MODEL LOADING (503) -> Wait 20s and Retry
            elif response.status_code == 503:
                time.sleep(20)
                response = requests.post(model_url, headers=headers, json=payload, timeout=20)
                if response.status_code == 200:
                    return response.json()[0]["generated_text"].strip()

            # IF 410/404 (Model Gone) -> JUST SKIP TO NEXT
            print(f"Model failed with error {response.status_code}. Switching to next...")
            continue
                
        except Exception as e:
            print(f"Connection error: {e}")
            continue

    return "System Rebooting... Wait 30 seconds and try again."

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
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                reply = ask_ai(text)
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                
        return "ok", 200
    except:
        return "error", 200

# SET WEBHOOK
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={RENDER_URL}"
    return requests.get(url).text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
