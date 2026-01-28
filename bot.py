import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

app = Flask(__name__)
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is working.")

tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

@app.route("/", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Bot running"

if __name__ == "__main__":
    tg_app.initialize()
    tg_app.bot.set_webhook(
        url=os.environ["RENDER_EXTERNAL_URL"]
    )
    app.run(host="0.0.0.0", port=10000)
