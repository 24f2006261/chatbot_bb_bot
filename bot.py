import os
import requests
import time
from flask import Flask, request

# =====================
# CONFIG
# =====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# LIST OF MODELS TO TRY (If one fails, it tries the next)
MODELS = [
    "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct",
    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
]

app = Flask(__name__)

# =====================
# MEMORY STORAGE
# =====================
user_histories = {} 

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def update_history(user_id, role, content):
    if user_id not in user_histories:
        user_histories[user_id] = []
    user_histories[user_id].append({"role": role, "content": content})
    # Keep last 6 messages (Phi-3 has smaller context, keeps it fast)
    if len(user_histories[user_id]) > 6:
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
# AI ENGINE (ROBUST)
# =====================
def query_huggingface(url, payload):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        return response
    except:
        return None

def ask_ai(user_id, user_text):
    # 1. Prepare Prompt (Phi-3 Format)
    history = get_history(user_id)
    prompt = "<|system|>\nYou are a helpful assistant for studies and life. Be concise.<|end|>\n"
    
    for msg in history:
        prompt += f"<|{msg['role']}|>\n{msg['content']}<|end|>\n"
    
    prompt += f"<|user|>\n{user_text}<|end|>\n<|assistant|>\n"

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 300,
            "return_full_text": False
        }
    }

    # 2. Try Models in Order
    for model_url in MODELS:
        print(f"Trying model: {model_url}...")
        response = query_huggingface(model_url, payload)
        
        # If connection failed entirely, try next model
        if response is None:
            continue

        # If model is loading (503), wait and retry ONCE
        if response.status_code == 503:
            time.sleep(15)
            response = query_huggingface(model_url, payload)
        
        # If Success
        if response and response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and "generated_text" in data[0]:
                bot_reply = data[0]["generated_text"].strip()
                update_history(user_id, "user", user_text)
                update_history(user_id, "assistant", bot_reply)
                return bot_reply
        
        # If 410 (Gone) or 401 (Unauthorized), loop to NEXT model
        print(f"Model failed with {response.status_code}. Switching...")

    return "All AI brains are asleep right now. Try again in 5 mins? 😴"

# =====================
# ROUTES
# =====================
@app.route("/", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(force=True)
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            if "text" in data["message"]:
                user_text = data["message"]["text"]
                user_id = data["message"]["from"]["id"]
                
                # Typing action
                requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                ai_reply = ask_ai(user_id, user_text)
                send_message(chat_id, ai_reply)
        return "ok", 200
    except Exception as e:
        print(e)
        return "error", 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    s = requests.get(f"{TELEGRAM_API}/setWebhook?url={RENDER_EXTERNAL_URL}")
    return f"Webhook Status: {s.text}", s.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
