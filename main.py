
import os
import logging
import openai
import aiohttp
from PIL import Image
from io import BytesIO
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Настройки
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = 75729723
PROMPT = "Give this car a body kit"

openai.api_key = OPENAI_API_KEY

# Память пользователей
user_data = {}
referrals = {}

# Логгинг
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = "Привет! Отправь мне фото машины, и я добавлю тюнинг. У тебя 2 генерации бесплатно."
    ref = context.args[0] if context.args else None

    if user_id not in user_data:
        user_data[user_id] = 2 if user_id != ADMIN_ID else float('inf')
        if ref and ref.isdigit() and int(ref) != user_id:
            ref_id = int(ref)
            referrals.setdefault(ref_id, set()).add(user_id)
            user_data[ref_id] = user_data.get(ref_id, 0) + 1

    await update.message.reply_text(text)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    gen_left = user_data.get(user_id, 2 if user_id != ADMIN_ID else float('inf'))

    if gen_left <= 0 and user_id != ADMIN_ID:
        await update.message.reply_text("У тебя закончились генерации. Пригласи друга по ссылке:
"
                                        f"https://t.me/{context.bot.username}?start={user_id}")
        return

    photo_file = await update.message.photo[-1].get_file()
    async with aiohttp.ClientSession() as session:
        async with session.get(photo_file.file_path) as resp:
            img_bytes = await resp.read()

    try:
        img = Image.open(BytesIO(img_bytes)).convert("RGBA")
        if img.format != "PNG":
            png_io = BytesIO()
            img.save(png_io, format="PNG")
            png_io.seek(0)
        else:
            png_io = BytesIO(img_bytes)

        response = openai.images.create_variation(
            image=png_io,
            n=1,
            size="1024x1024"
        )
        result_url = response.data[0].url

        await update.message.reply_photo(photo=result_url)

        if user_id != ADMIN_ID:
            user_data[user_id] -= 1

    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        await update.message.reply_text("Произошла ошибка при генерации изображения. Попробуй ещё раз.")


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Нет доступа.")
        return

    total_users = len(user_data)
    top_refs = sorted(referrals.items(), key=lambda x: len(x[1]), reverse=True)
    ref_text = "\n".join([f"{uid}: {len(refs)} приглашений" for uid, refs in top_refs[:10]])

    await update.message.reply_text(f"Всего пользователей: {total_users}\n\nТоп по рефералам:\n{ref_text}")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
