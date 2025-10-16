import logging
import os
# Опциональная загрузка .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from database import init_db
from handlers.profile import my_plants, build_profile_conversation, delete_plant_cb
from handlers.diagnosis import handle_symptoms as diagnose_text
from handlers.recommendations import get_recommendations
from handlers.diagnose_photo import diagnose_photo

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен!")
    exit(1)


# Главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🌱 Мои растения", "📚 База знаний"],
        ["🔍 Диагностика", "🛎 Напоминания"],
        ["👨‍🌾 Чат с экспертом"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    text = (
        "🌿 *Добро пожаловать!*\n\n"
        "Выберите действие кнопками ниже 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


# Обработка кнопок меню
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🌱 Мои растения":
        await my_plants(update, context)
    elif text == "📚 База знаний":
        await update.message.reply_text("База знаний пока в разработке 📖")
    elif text == "🔍 Диагностика":
        await update.message.reply_text("Пришлите фото растения для диагностики 🖼️")
    elif text == "🛎 Напоминания":
        await update.message.reply_text("Напоминания пока в разработке ⏰")
    elif text == "👨‍🌾 Чат с экспертом":
        await update.message.reply_text("Функция платных консультаций пока в разработке 💬")


# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Команды:*\n"
        "/start — главное меню\n"
        "/myplants — список ваших растений, добавить новое\n"
        "/recommendations — общие рекомендации по уходу\n",
        parse_mode="Markdown"
    )


def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myplants", my_plants))
    app.add_handler(CommandHandler("recommendations", get_recommendations))

    # Диалог добавления растения
    app.add_handler(build_profile_conversation())

    # Диагностика по тексту
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, diagnose_text))

    # Диагностика по фото
    app.add_handler(MessageHandler(filters.PHOTO, diagnose_photo))

    # Callback для удаления растения
    app.add_handler(CallbackQueryHandler(delete_plant_cb, pattern="^delete_"))

    # Обработка кнопок меню
    app.add_handler(MessageHandler(
        filters.Regex("^(🌱 Мои растения|📚 База знаний|🔍 Диагностика|🛎 Напоминания|👨‍🌾 Чат с экспертом)$"),
        handle_menu
    ))

    logging.info("✅ Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
