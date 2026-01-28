import os
import requests
from flask import Flask, request

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
RENDER_EXTERNAL_URL = os.environ["RENDER_EXTERNAL_URL"]

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

app = Flask(__name__)

# =====================
# SEND MESSAGE
# =====================
def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload, timeout=10)

# =====================
# WEBHOOK
# =====================
@app.route("/", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        send_message(chat_id, f"Bot working ✅\nYou said: {text}")

    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Bot running"

# =====================
# SET WEBHOOK
# =====================
if __name__ == "__main__":
    webhook_url = f"{RENDER_EXTERNAL_URL}/"
    requests.get(
        f"{TELEGRAM_API}/setWebhook",
        params={"url": webhook_url},
        timeout=10
    )

    app.run(host="0.0.0.0", port=10000)
