
import os
import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from openai import OpenAI

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ADMIN_ID = 75729723
GENERATIONS_LIMIT = 2

USER_DATA_FILE = "user_data.json"


def load_user_data():
    if not os.path.exists(USER_DATA_FILE):
        return {}
    with open(USER_DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}


def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_user_data()
    if str(user.id) not in data:
        data[str(user.id)] = {"gen_count": 0, "referrals": []}
        if context.args:
            ref = context.args[0]
            if ref != str(user.id) and ref in data:
                data[ref]["referrals"].append(str(user.id))
                data[ref]["gen_count"] += 1
    save_user_data(data)
    await update.message.reply_text(f"Привет, {user.first_name}! Пришли фото машины и получишь её тюнинг")


async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_user_data()
    user_data = data.get(str(user.id), {"gen_count": 0})
    if user_data["gen_count"] >= GENERATIONS_LIMIT:
        await update.message.reply_text("Лимит генераций исчерпан.")
        return

    await update.message.reply_text("Генерация...")

    # Пример генерации
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Сгенерируй описание кастомного тюнинга авто."}]
    )

    result = response.choices[0].message.content
    await update.message.reply_text(result)

    user_data["gen_count"] += 1
    data[str(user.id)] = user_data
    save_user_data(data)


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return await update.message.reply_text("Нет доступа.")
    data = load_user_data()
    text = f"👤 Пользователи: {len(data)}\n"
    for uid, info in data.items():
        text += f"ID: {uid}, Генераций: {info.get('gen_count', 0)}, Рефералов: {len(info.get('referrals', []))}\n"
    await update.message.reply_text(text[:4000])


def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CommandHandler("admin", admin))
    app.run_polling()


if __name__ == "__main__":
    main()
