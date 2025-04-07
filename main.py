import os
import logging
import json
import openai
from telegram import Update, InputFile
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes

# Константы
ADMIN_ID = 75729723
GENERATION_LIMIT = 2
USER_DATA_FILE = "user_data.json"

# Настройки логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Функции
def load_user_data():
    if not os.path.exists(USER_DATA_FILE):
        return {}
    with open(USER_DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def increment_generation(user_id):
    user_data = load_user_data()
    user_id = str(user_id)
    if user_id not in user_data:
        user_data[user_id] = {"generations": 0, "referrals": []}
    user_data[user_id]["generations"] += 1
    save_user_data(user_data)

def can_generate(user_id):
    user_data = load_user_data()
    user_id = str(user_id)
    if user_id not in user_data:
        return True
    return user_data[user_id]["generations"] < GENERATION_LIMIT + len(user_data[user_id].get("referrals", []))

async def generate_tuning_image(image_path: str) -> str:
    response = openai.images.edit(
        image=open(image_path, "rb"),
        mask=None,
        prompt="Add a stylish tuning to this car",
        n=1,
        size="1024x1024",
        response_format="url"
    )
    image_url = response['data'][0]['url']
    return image_url

# Хендлеры
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отправь фото машины — я добавлю тюнинг! 🚗🔥")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    user_data = load_user_data()
    text = "\n".join([f"{uid}: {info['generations']} генераций, {len(info.get('referrals', []))} рефералов" for uid, info in user_data.items()])
    await update.message.reply_text("👑 Админка:\n" + text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not can_generate(user_id):
        await update.message.reply_text("⛔ Превышен лимит генераций. Пригласи друзей, чтобы получить больше!")
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"user_{user_id}_input.jpg"
    await file.download_to_drive(file_path)

    await update.message.reply_text("⚙️ Генерирую тюнинг...")

    try:
        result_url = await generate_tuning_image(file_path)
        await update.message.reply_photo(photo=result_url, caption="🚘 Вот твоя машина с тюнингом!")
        increment_generation(user_id)
    except Exception as e:
        logger.exception("Ошибка генерации:")
        await update.message.reply_text("❌ Не удалось сгенерировать изображение. Попробуй позже.")

    os.remove(file_path)

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if context.args:
        ref = context.args[0]
        if ref != user_id:
            data = load_user_data()
            if ref in data and user_id not in data[ref].get("referrals", []):
                data[ref].setdefault("referrals", []).append(user_id)
                save_user_data(data)
                await update.message.reply_text("✅ Реферал засчитан!")
    else:
        await update.message.reply_text(f"🔗 Твоя реферальная ссылка: https://t.me/{context.bot.username}?start={user_id}")

# Запуск бота
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("ref", referral))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()

if __name__ == "__main__":
    main()