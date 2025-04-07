import os
import logging
import openai
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 75729723

logging.basicConfig(level=logging.INFO)

async def generate_tuning_image(prompt: str):
    response = await openai.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    return response.data[0].url

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        file_path = f"downloads/{update.message.photo[-1].file_id}.jpg"

        # Скачиваем фото
        async with aiohttp.ClientSession() as session:
            async with session.get(file.file_path) as resp:
                with open(file_path, "wb") as f:
                    f.write(await resp.read())

        prompt = "Add aggressive cyberpunk-style body kit tuning to the car in the photo"
        image_url = await generate_tuning_image(prompt)

        await update.message.reply_photo(photo=image_url, caption="Вот тюнингованная версия твоей тачки 😎")

    except Exception as e:
        logging.exception("Ошибка генерации:")
        await update.message.reply_text("Произошла ошибка при генерации. Попробуй позже.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь мне фото машины, и я покажу тебе её в тюнинге 🔥")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Добро пожаловать в админ-панель.")
    else:
        await update.message.reply_text("Доступ запрещён.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Запуск Webhook (используется на Render)
    port = int(os.environ.get("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/webhook"
    )

if __name__ == "__main__":
    main()