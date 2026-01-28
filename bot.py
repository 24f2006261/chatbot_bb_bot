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

# NEW 2026 URLS (Router API)
# We use "router.huggingface.co" instead of "api-inference" to fix Error 410
MODELS = [
    "https://router.huggingface.co/hf-inference/models/microsoft/Phi-3-mini-4k-instruct",
    "https://router.huggingface.co/hf-inference/models/Qwen/Qwen2.5-0.5B-Instruct",
    "https://router.huggingface.co/hf-inference/models/google/gemma-1.1-2b-it"
]

app = Flask(__name__)

# =====================
# AI LOGIC
# =====================
def ask_ai(user_text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Simple prompt for fast replies
    payload = {
        "inputs": f"<|user|>\n{user_text}\n<|assistant|>\n",
        "parameters": {
            "max_new_tokens": 200, 
            "return_full_text": False
        }
    }

    errors_log = []

    for model_url in MODELS:
        try:
            print(f"Connecting to: {model_url}...")
            # Timeout 30s to allow waking up
            response = requests.post(model_url, headers=headers, json=payload, timeout=30)
            
            # 1. SUCCESS
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and "generated_text" in data[0]:
                    return data[0]["generated_text"].strip()
                elif isinstance(data, dict) and "generated_text" in data:
                    return data["generated_text"].strip()
                else:
                    return str(data)

            # 2. MODEL LOADING (503) -> Wait & Retry
            elif response.status_code == 503:
                print("Model napping... waiting 20s.")
                time.sleep(20)
                # Retry once
                response = requests.post(model_url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                     return response.json()[0]["generated_text"].strip()

            # 3. AUTH ERROR (401)
            elif response.status_code == 401:
                return "❌ Error: Invalid Token. Please generate a new 'Write' token on Hugging Face."

            else:
                errors_log.append(f"{model_url}: Error {response.status_code}")
                
        except Exception as e:
            errors_log.append(f"{model_url}: Failed ({str(e)})")

    return f"⚠️ Connection failed. Debug Info:\n" + "\n".join(errors_log)

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

# RESET URL
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={RENDER_URL}"
    return requests.get(url).text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
