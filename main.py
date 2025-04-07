import os
import json
import logging
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler
)
from dotenv import load_dotenv
from flask import Flask

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # замени на свой Telegram ID

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Webhook (для Render)
app = Flask(__name__)
telegram_app = ApplicationBuilder().token(TOKEN).build()

# Хранилище
DATA_FILE = "user_data.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)


def load_data():
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    data = load_data()

    ref = context.args[0] if context.args else None
    if user_id not in data:
        data[user_id] = {"gens": 2, "ref_by": ref, "refers": []}
        if ref and ref in data:
            data[ref]["gens"] += 1
            data[ref]["refers"].append(user_id)
    save_data(data)

    await update.message.reply_text(
        f"Привет, {user.first_name}! У тебя {data[user_id]['gens']} бесплатных генераций.\n"
        f"Приглашай друзей и получай больше!"
    )


async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if data.get(user_id, {}).get("gens", 0) <= 0:
        await update.message.reply_text("У тебя закончились генерации 😢")
        return

    data[user_id]["gens"] -= 1
    save_data(data)

    await update.message.reply_text("🔧 Генерирую тюнинг... (тут будет фото или ссылка)")
    # Здесь вставь вызов модели генерации

    await update.message.reply_text(f"У тебя осталось {data[user_id]['gens']} генераций.")


async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    await update.message.reply_text(
        f"Твоя реферальная ссылка:\nhttps://t.me/{context.bot.username}?start={user_id}"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        await update.message.reply_text("Нет данных о тебе.")
        return

    await update.message.reply_text(
        f"🔢 Генераций: {data[user_id]['gens']}\n👥 Приглашено: {len(data[user_id].get('refers', []))}"
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return await update.message.reply_text("Ты не админ 😎")

    data = load_data()
    total_users = len(data)
    total_gens = sum([user.get("gens", 0) for user in data.values()])
    await update.message.reply_text(
        f"👑 Админ-панель:\nВсего пользователей: {total_users}\nСуммарно генераций: {total_gens}"
    )


# Flask вебхуки
@app.route('/')
def index():
    return "Бот работает!"

@app.route(f'/{TOKEN}', methods=["POST"])
def webhook():
    from flask import request
    telegram_app.update_queue.put_nowait(Update.de_json(request.get_json(force=True), telegram_app.bot))
    return "ok"


# Хендлеры
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("gen", generate))
telegram_app.add_handler(CommandHandler("generate", generate))
telegram_app.add_handler(CommandHandler("ref", refer))
telegram_app.add_handler(CommandHandler("stats", stats))
telegram_app.add_handler(CommandHandler("admin", admin))