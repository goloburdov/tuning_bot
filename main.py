import os
import json
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import openai

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

USER_DATA_FILE = "user_data.json"

logging.basicConfig(level=logging.INFO)

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def start(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()

    if user_id not in user_data:
        user_data[user_id] = {"generations_left": 2, "referrals": []}

    if context.args:
        ref_id = context.args[0]
        if ref_id != user_id and ref_id not in user_data[user_id]["referrals"]:
            if ref_id not in user_data:
                user_data[ref_id] = {"generations_left": 2, "referrals": []}
            user_data[ref_id]["generations_left"] += 1
            user_data[ref_id]["referrals"].append(user_id)

    save_user_data(user_data)

    update.message.reply_text("Привет! Отправь фото машины — я сгенерирую тюнинг 🚗🔥")

def ref(update: Update, context: CallbackContext):
    bot_username = context.bot.username
    user_id = str(update.message.from_user.id)
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    update.message.reply_text(f"Пригласи друга этой ссылкой и получи +1 генерацию:\n{ref_link}")

def handle_photo(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()

    if user_id not in user_data:
        user_data[user_id] = {"generations_left": 2, "referrals": []}

    if user_data[user_id]["generations_left"] <= 0:
        update.message.reply_text("У тебя закончились генерации 😢 Пригласи друга или купи ещё.")
        return

    user_data[user_id]["generations_left"] -= 1
    save_user_data(user_data)

    update.message.reply_text("Фото получено. Генерирую тюнинг... 🔧")

    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt="A custom car bodykit, futuristic design, widebody, carbon fiber, aggressive style",
            n=1,
            size="1024x1024"
        )
        image_url = response['data'][0]['url']
        update.message.reply_photo(image_url, caption=f"Вот твой обвес! Осталось генераций: {user_data[user_id]['generations_left']}")
    except Exception as e:
        logging.error(f"Ошибка генерации: {e}")
        update.message.reply_text("Произошла ошибка. Попробуй позже.")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ref", ref))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()