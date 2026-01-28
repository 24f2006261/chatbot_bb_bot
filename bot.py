import os
import requests
from flask import Flask, request

# =====================
# ENV
# =====================
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
HF_TOKEN = os.environ["HF_TOKEN"]
RENDER_EXTERNAL_URL = os.environ["RENDER_EXTERNAL_URL"]

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
HF_API = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"



app = Flask(__name__)

# =====================
# SEND TELEGRAM MESSAGE
# =====================
def send_message(chat_id, text):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=15
    )

# =====================
# ASK AI
# =====================
def ask_ai(user_text):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": f"""
You are a helpful, intelligent AI assistant.
Explain things clearly and naturally like a modern AI.
Be friendly, concise, and practical.
Do not mention models, servers, or errors.

User: {user_text}
Assistant:
""",
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.7,
            "top_p": 0.9,
            "repetition_penalty": 1.1
        }
    }

    response = requests.post(
        HF_API,
        headers=headers,
        json=payload,
        timeout=90
    )

    # HF cold start
    if response.status_code == 503:
        return "Hmm… give me a second, thinking about this 🤔"

    if response.status_code != 200:
        return "Let me rephrase that… can you ask again?"

    data = response.json()

    if isinstance(data, list) and "generated_text" in data[0]:
        text = data[0]["generated_text"]
        return text.split("Assistant:")[-1].strip()

    return "Alright, tell me a bit more 🙂"

# =====================
# WEBHOOK
# =====================
@app.route("/", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]

        ai_reply = ask_ai(user_text)
        send_message(chat_id, ai_reply)

    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "AI bot running"

# =====================
# SET WEBHOOK
# =====================
if __name__ == "__main__":
    requests.get(
        f"{TELEGRAM_API}/setWebhook",
        params={"url": RENDER_EXTERNAL_URL},
        timeout=10
    )
    app.run(host="0.0.0.0", port=10000)
