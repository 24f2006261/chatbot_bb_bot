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
HF_API = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"

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
def ask_ai(text):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }
    response = requests.post(
        HF_API,
        headers=headers,
        json={"inputs": text},
        timeout=30
    )

    if response.status_code != 200:
        return "AI is busy right now."

    data = response.json()
    if isinstance(data, list) and "generated_text" in data[0]:
        return data[0]["generated_text"]

    return "AI had nothing to say."

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
