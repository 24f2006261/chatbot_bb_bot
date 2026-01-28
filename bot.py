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
# ENV
# =====================
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
RENDER_EXTERNAL_URL = os.environ["RENDER_EXTERNAL_URL"]

# =====================
# FLASK
# =====================
app = Flask(__name__)

# =====================
# TELEGRAM APP
# =====================
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# =====================
# HANDLER
# =====================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Hello! Bot is working ✅")

tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# =====================
# ASYNC LOOP (IMPORTANT)
# =====================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def telegram_startup():
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.bot.set_webhook(RENDER_EXTERNAL_URL)

loop.run_until_complete(telegram_startup())

# =====================
# WEBHOOK (SYNC, SAFE)
# =====================
@app.route("/", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    asyncio.run_coroutine_threadsafe(
        tg_app.process_update(update),
        loop
    )
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "Bot running"

# =====================
# MAIN
# =====================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
