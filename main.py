import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY
from openai import OpenAI
import sys

client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)

USER_DATA_PATH = "user_data.json"
if not os.path.exists(USER_DATA_PATH):
    with open(USER_DATA_PATH, "w") as f:
        json.dump({}, f)

STYLES = ["Спорт", "Дрифт", "VIP", "Урбан"]
DEFAULT_FREE_GENERATIONS = 2

def load_data():
    with open(USER_DATA_PATH, "r") as f:
        return json.load(f)

def save_data(data):
    with open(USER_DATA_PATH, "w") as f:
        json.dump(data, f)

def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    args = context.args

    data = load_data()

    if user_id not in data:
        data[user_id] = {
            "generations_left": DEFAULT_FREE_GENERATIONS
        }
        # Обрабатываем реферал
        if args:
            referrer_id = args[0]
            if referrer_id != user_id and referrer_id in data:
                data[referrer_id]["generations_left"] += 1
                data[user_id]["invited_by"] = referrer_id
                context.bot.send_message(chat_id=referrer_id, text="🎉 Тебе +1 генерация за приглашённого друга!")
        save_data(data)

    update.message.reply_text(
        "Привет! Пришли мне фото своей машины 🚗\n"
        f"Осталось генераций: {data[user_id]['generations_left']}"
    )

def handle_photo(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    data = load_data()

    if user_id not in data:
        update.message.reply_text("Сначала отправь /start")
        return

    if data[user_id].get("generations_left", 0) <= 0:
        update.message.reply_text("У тебя закончились генерации! Пригласи друга или купи через Telegram Stars ✨")
        return

    photo_file = update.message.photo[-1].get_file()
    photo_path = f"user_{user_id}.jpg"
    photo_file.download(photo_path)

    data[user_id]["photo"] = photo_path
    save_data(data)

    reply_markup = ReplyKeyboardMarkup([[s] for s in STYLES], one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Выбери стиль обвеса:", reply_markup=reply_markup)

def handle_style(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    selected_style = update.message.text

    data = load_data()

    if user_id not in data or "photo" not in data[user_id]:
        update.message.reply_text("Сначала пришли фото машины.")
        return

    if data[user_id].get("generations_left", 0) <= 0:
        update.message.reply_text("У тебя закончились генерации!")
        return

    photo_path = data[user_id]["photo"]
    update.message.reply_text("Генерирую обвес... ⏳")

    prompt = f"A realistic car with a custom {selected_style.lower()} body kit, wide fenders, aggressive tuning, dramatic lighting, parked on a street"

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        update.message.reply_photo(photo=image_url, caption=f"Вот твой обвес в стиле: {selected_style} 🤘")

        # Уменьшаем генерации
        data[user_id]["generations_left"] -= 1
        save_data(data)

    except Exception as e:
        logging.error(e)
        update.message.reply_text("Ошибка при генерации 😔")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start, pass_args=True))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_style))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()