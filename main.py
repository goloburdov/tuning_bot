import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import openai

# ✅ Получаем ключи из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Отправь мне фото машины, и я сгенерирую тюнинг-обвес 🎨")

def handle_photo(update: Update, context: CallbackContext):
    user = update.message.from_user
    photo_file = update.message.photo[-1].get_file()
    photo_path = f"{user.id}_photo.jpg"
    photo_file.download(photo_path)

    update.message.reply_text("Фото получено. Генерирую тюнинг-обвес... 🛠")

    try:
        # Заменим на простой ответ, потому что генерация картинки с openai.Image больше не поддерживается напрямую
        response = openai.images.generate(
            model="dall-e-3",
            prompt="A heavily customized car with an aggressive body kit, large wheels, neon underglow, carbon fiber details, futuristic design",
            n=1,
            size="1024x1024"
        )

        image_url = response['data'][0]['url']
        update.message.reply_photo(image_url, caption="Вот твой обвес!")

    except Exception as e:
        logging.error(f"Ошибка генерации: {e}")
        update.message.reply_text("Произошла ошибка при генерации. Попробуй позже.")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.photo, handle_photo))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()