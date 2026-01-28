import os
import asyncio
from flask import Flask, request

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

# =====================
# ENV VARIABLES
# =====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

# =====================
# FLASK APP
# =====================
app = Flask(__name__)

# =====================
# TELEGRAM APP
# =====================
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# =====================
# TELEGRAM HANDLER
# =====================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Bot is working ✅")

tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# =====================
# WEBHOOK (SYNC — IMPORTANT)
# =====================
@app.route("/", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put(update)   # ✅ correct way
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Bot running"

# =====================
# MAIN
# =====================
if __name__ == "__main__":

    async def setup():
        await tg_app.initialize()
        await tg_app.bot.set_webhook(
            url=RENDER_EXTERNAL_URL
        )

    asyncio.run(setup())

    app.run(host="0.0.0.0", port=10000)
