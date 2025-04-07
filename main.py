import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import openai
import aiohttp

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = 75729723
PROMPT = "Give this car a body kit"

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Словари для лимитов и рефералов
user_limits = {}
user_referrals = {}

# Установка API ключа OpenAI
openai.api_key = OPENAI_API_KEY

async def generate_image_from_photo(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        response = openai.images.create_variation(
            image=image_file,
            n=1,
            size="512x512"
        )
    return response.data[0].url

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # Лимиты
    if user_id != ADMIN_ID:
        user_limits.setdefault(user_id, 2)
        if user_limits[user_id] <= 0:
            await update.message.reply_text(
                "❌ Лимит генераций исчерпан. Пригласи друга по своей ссылке, чтобы получить ещё 1 генерацию."
            )
            return
        user_limits[user_id] -= 1

    # Скачивание фото
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = f"/tmp/{photo.file_id}.jpg"
    await file.download_to_drive(file_path)

    # Генерация
    try:
        result_url = await generate_image_from_photo(file_path)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=result_url)
    except Exception as e:
        logger.error("Ошибка генерации: %s", e)
        await update.message.reply_text("⚠️ Ошибка генерации тюнинга.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user_id:
                user_limits[referrer_id] = user_limits.get(referrer_id, 2) + 1
                user_referrals.setdefault(referrer_id, []).append(user_id)
        except Exception:
            pass
    await update.message.reply_text(
        "🚗 Отправь мне фото машины, и я наложу на неё тюнинг!\n\n"
        f"🔗 Твоя реферальная ссылка:\nhttps://t.me/{context.bot.username}?start={user_id}"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    stats = "\n".join(
        [f"👤 {uid} — {lim} генераций, 👥 {len(user_referrals.get(uid, []))} рефералов"
         for uid, lim in user_limits.items()]
    )
    await update.message.reply_text(f"📊 Статистика:\n{stats if stats else 'Нет данных'}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()