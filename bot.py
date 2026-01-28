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

# STABLE MODELS LIST (Lightweight & Fast)
MODELS = [
    "https://api-inference.huggingface.co/models/google/gemma-1.1-2b-it",
    "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct",
    "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-0.5B-Instruct"
]

app = Flask(__name__)

# =====================
# INTELLIGENT AI HANDLER
# =====================
def ask_ai(user_text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # Prompt engineering for short, human-like replies
    payload = {
        "inputs": f"<|user|>\n{user_text}\n<|assistant|>\n",
        "parameters": {
            "max_new_tokens": 200, 
            "return_full_text": False,
            "temperature": 0.7
        }
    }

    # Debug: Check if Token exists
    if not HF_TOKEN:
        return "⚠️ Error: HF_TOKEN is missing in Render Settings."

    errors_log = []

    for model_url in MODELS:
        try:
            print(f"Connecting to: {model_url}...")
            # Increased timeout to 35s for cold starts
            response = requests.post(model_url, headers=headers, json=payload, timeout=35)
            
            # 1. SUCCESS
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and "generated_text" in data[0]:
                    return data[0]["generated_text"].strip()
                elif isinstance(data, dict) and "generated_text" in data:
                    return data["generated_text"].strip()
                else:
                    return str(data)

            # 2. INVALID TOKEN (Critical Fix)
            elif response.status_code == 401:
                return "❌ Error 401: Your HuggingFace Token is invalid. Please create a new 'WRITE' token."

            # 3. MODEL LOADING (Wait & Retry)
            elif response.status_code == 503:
                print("Model loading... waiting 20s.")
                time.sleep(20)
                # Retry once
                response = requests.post(model_url, headers=headers, json=payload, timeout=35)
                if response.status_code == 200:
                     return response.json()[0]["generated_text"].strip()
                else:
                    errors_log.append(f"{model_url.split('/')[-1]}: Still loading (503)")

            # 4. OTHER ERRORS
            else:
                errors_log.append(f"{model_url.split('/')[-1]}: Error {response.status_code}")
                
        except Exception as e:
            errors_log.append(f"{model_url.split('/')[-1]}: Connection Failed")

    # If all fail, return the debug log so we can see WHY
    return f"⚠️ All AI models failed.\nDebug Log:\n" + "\n".join(errors_log)

# =====================
# TELEGRAM WEBHOOK
# =====================
@app.route("/", methods=["POST"])
def telegram():
    try:
        data = request.get_json(force=True)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            if text:
                # Send "Typing..." action
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                # Get Response
                reply = ask_ai(text)
                
                # Send Response
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reply})
                
        return "ok", 200
    except Exception as e:
        print(f"Webhook Error: {e}")
        return "error", 200

# MANUAL RESET URL
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={RENDER_URL}"
    response = requests.get(url)
    return f"Webhook Status: {response.text}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
