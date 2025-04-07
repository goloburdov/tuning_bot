import os
import json
import logging
from uuid import uuid4
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

USER_DATA_FILE = "user_data.json"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

WEBHOOK_PATH = f"/{TELEGRAM_BOT_TOKEN}"
RENDER_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
WEBHOOK_URL = f"https://{RENDER_HOSTNAME}{WEBHOOK_PATH}" if RENDER_HOSTNAME else None

user_data = {}

# ========== Загрузка/сохранение данных ==========
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_user_data():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f, indent=4)

# ========== Основная логика ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    ref = context.args[0] if context.args else None
    if user_id not in user_data:
        user_data[user_id] = {"generations": 2, "ref": ref, "invited": []}
        if ref and ref in user_data:
            user_data[ref]["generations"] += 1
            user_data[ref]["invited"].append(user_id)
        save_user_data()
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! У тебя {user_data[user_id]['generations']} генераций.\n"
        f"Твоя реф-ссылка: https://t.me/{context.bot.username}?start={user_id}"
    )

async def handle_image_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = user_data.get(user_id)
    if not user or user["generations"] <= 0:
        await update.message.reply_text("У тебя закончились генерации. Пригласи друга, чтобы получить больше!")
        return

    prompt = update.message.text
    await update.message.reply_text("Генерирую изображение...")

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.images.generate(prompt=prompt, model="dall-e-3", n=1, size="1024x1024")
    image_url = response.data[0].url

    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)

    user["generations"] -= 1
    save_user_data()

# ========== FastAPI часть ==========
app = FastAPI()

@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, Bot(token=TELEGRAM_BOT_TOKEN))
    await app.telegram_app.update_queue.put(update)
    return "ok"

@app.get("/admin")
async def admin(request: Request):
    token = request.query_params.get("token")
    if token != ADMIN_PASSWORD:
        return JSONResponse({"error": "Unauthorized"}, status_code=403)
    return user_data

# ========== Запуск ==========
if __name__ == "__main__":
    import uvicorn
    import asyncio

    async def main():
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        app.telegram_app = application

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_image_prompt))

        user_data.update(load_user_data())

        if WEBHOOK_URL:
            await application.bot.set_webhook(WEBHOOK_URL)
        else:
            await application.initialize()
            await application.start()
            await application.updater.start_polling()

        config = {"host": "0.0.0.0", "port": int(os.getenv("PORT", 8000)), "log_level": "info"}
        await uvicorn.run(app, **config)

    asyncio.run(main())