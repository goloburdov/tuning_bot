import os
import json
import random
import logging
from uuid import uuid4
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import openai

# ENV переменные
openai.api_key = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_ID = 75729723

# Логирование
logging.basicConfig(level=logging.INFO)

# Сохранение/загрузка данных
DATA_FILE = "user_data.json"

def load_user_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

user_data = load_user_data()

# ===========================
# Обработка /start
# ===========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"generations": 2, "referrals": []}
        save_user_data(user_data)

    ref = context.args[0] if context.args else None
    if ref and ref != user_id and ref not in user_data[user_id]["referrals"]:
        if ref in user_data:
            user_data[ref]["generations"] += 1
            user_data[ref]["referrals"].append(user_id)
            save_user_data(user_data)
        await update.message.reply_text("Благодарим! Вы перешли по реферальной ссылке.")
    await update.message.reply_text("Пришли мне фото машины, и я добавлю тюнинг 🤖")

# ===========================
# Админка
# ===========================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Недоступно.")
        return

    stats = "\n".join([
        f"{uid}: {data['generations']} генераций, {len(data['referrals'])} рефералов"
        for uid, data in user_data.items()
    ])
    await update.message.reply_text(f"📊 Статистика:\n{stats}")

# ===========================
# Обработка фото
# ===========================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"generations": 2, "referrals": []}
        save_user_data(user_data)

    if user_data[user_id]["generations"] <= 0:
        await update.message.reply_text("У тебя закончились генерации. Пригласи друга, чтобы получить ещё.")
        return

    await update.message.reply_text("🔧 Обрабатываю фото, подожди немного...")

    # Получение фото
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"/tmp/{uuid4()}.png"
    await photo_file.download_to_drive(file_path)

    # Генерация с помощью OpenAI
    with open(file_path, "rb") as image_file:
        response = openai.images.create_variation(
            image=image_file,
            n=1,
            size="1024x1024"
        )

    image_url = response.data[0].url
    await update.message.reply_photo(image_url, caption="🚗 Вот твоя машина с тюнингом!")

    user_data[user_id]["generations"] -= 1
    save_user_data(user_data)

# ===========================
# Основной запуск
# ===========================
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()