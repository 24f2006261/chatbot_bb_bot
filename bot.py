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

# Zephyr 7B Beta (Free, Smart, Ungated - Works Instantly)
HF_API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"

app = Flask(__name__)

# =====================
# MEMORY
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
    if len(user_histories[user_id]) > 10:
        user_histories[user_id].pop(0)

# =====================
# SEND MSG
# =====================
def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=15
    )

# =====================
# AI ENGINE
# =====================
def ask_ai(user_id, user_text):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Prepare History
    history = get_history(user_id)
    
    # Zephyr Prompt Format
    prompt = "<|system|>\nYou are a helpful AI assistant for studies, diet, and life advice. Keep answers short and clear.<|endoftext|>\n"
    
    for msg in history:
        role = "user" if msg['role'] == "user" else "assistant"
        prompt += f"<|{role}|>\n{msg['content']}<|endoftext|>\n"
    
    prompt += f"<|user|>\n{user_text}<|endoftext|>\n<|assistant|>\n"

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 400,
            "temperature": 0.7,
            "top_p": 0.9,
            "return_full_text": False
        }
    }

    # 2. Call API with Retry (Fixes "Model Loading" errors)
    for attempt in range(3):
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=45)
            
            # If AI is waking up (503), wait 20s and try again
            if response.status_code == 503:
                time.sleep(20)
                continue
                
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and "generated_text" in data[0]:
                    bot_reply = data[0]["generated_text"].strip()
                    update_history(user_id, "user", user_text)
                    update_history(user_id, "assistant", bot_reply)
                    return bot_reply
            
            # If 410/400 error again, fail gracefully
            if response.status_code >= 400:
                return f"Error {response.status_code}. (AI servers are busy, try again in 1 min)"
                
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

    return "Thinking took too long... try again? 🧠"

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
                # Typing indicator
                requests.post(f"{TELEGRAM_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
                
                ai_reply = ask_ai(user_id, user_text)
                send_message(chat_id, ai_reply)
        return "ok", 200
    except:
        return "error", 500

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    s = requests.get(f"{TELEGRAM_API}/setWebhook?url={RENDER_EXTERNAL_URL}")
    if s.status_code == 200:
        return "Webhook Live! Check Telegram.", 200
    else:
        return f"Fail: {s.text}", 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
