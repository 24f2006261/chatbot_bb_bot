import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "PUT_YOUR_TELEGRAM_BOT_TOKEN_HERE"
HF_TOKEN = "PUT_YOUR_HUGGINGFACE_TOKEN_HERE"

MODEL_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    payload = {
        "inputs": f"Reply simply in short sentences. No technical language. {user_text}"
    }

    response = requests.post(MODEL_URL, headers=HEADERS, json=payload)
    data = response.json()

    try:
        reply = data[0]["generated_text"]
    except:
        reply = "I'm here 🙂 Ask something simple."

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
app.run_polling()
