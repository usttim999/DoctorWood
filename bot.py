import logging
import os
from dotenv import load_dotenv
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
from handlers.diagnosis import handle_symptoms
from handlers.recommendations import get_recommendations
from handlers.diagnose_photo import diagnose_photo
from handlers.trefle import build_trefle_conversation

# Загружаем .env
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен!")
    exit(1)

# Главное меню
MAIN_KEYBOARD = [
    ["🌱 Мои растения", "📚 База знаний"],
    ["🔍 Диагностика", "🛎 Напоминания"],
    ["👨‍🌾 Чат с экспертом", "🌍 Trefle"],
]

BACK_KEYBOARD = [["⬅️ Назад"]]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "🌿 *Добро пожаловать!*\n\nВыберите действие кнопками ниже 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Команды:*\n"
        "/start — главное меню\n"
        "/myplants — список ваших растений\n"
        "/diagnose — диагностика по фото\n"
        "/recommendations — рекомендации по уходу\n",
        parse_mode="Markdown",
    )


async def diagnose_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Для диагностики пришлите фото вашего растения 🖼️",
        reply_markup=ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True),
    )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🌱 Мои растения":
        await my_plants(update, context)
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True),
        )

    elif text == "📚 База знаний":
        await update.message.reply_text(
            "📚 База знаний находится в разработке",
            reply_markup=ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True),
        )

    elif text == "🔍 Диагностика":
        await diagnose_command(update, context)

    elif text == "🛎 Напоминания":
        await update.message.reply_text(
            "🛎 Напоминания находятся в разработке",
            reply_markup=ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True),
        )

    elif text == "👨‍🌾 Чат с экспертом":
        await update.message.reply_text(
            "👨‍🌾 Чат с агрономом находится в разработке",
            reply_markup=ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True),
        )

    elif text == "⬅️ Назад":
        await start(update, context)

    elif text == "🌍 Trefle":
        await update.message.reply_text(
            "Введите название растения для поиска в базе Trefle.\n\n"
            "Например: `/trefle ficus`",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True),
        )


def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myplants", my_plants))
    app.add_handler(CommandHandler("recommendations", get_recommendations))
    app.add_handler(CommandHandler("diagnose", diagnose_command))

    # Диалог добавления растения
    app.add_handler(build_profile_conversation())

    # Диагностика по фото
    app.add_handler(MessageHandler(filters.PHOTO, diagnose_photo))

    # Callback для удаления растения
    app.add_handler(CallbackQueryHandler(delete_plant_cb, pattern="^delete_"))
    app.add_handler(build_trefle_conversation())

    # Обработка кнопок меню (включая Назад)
    app.add_handler(
        MessageHandler(
            filters.Regex(
                "^(🌱 Мои растения|📚 База знаний|🔍 Диагностика|🛎 Напоминания|👨‍🌾 Чат с экспертом|⬅️ Назад)$"
            ),
            handle_menu,
        )
    )

    # Обработка симптомов (только если это текст и не команда/кнопка)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symptoms))

    logging.info("✅ Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
