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
from handlers.start import start, help_command

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
    ["🌱 Мои растения", "🔍 Диагностика"],
    ["📚 Рекомендации", "🌍 Поиск растений"],
    ["👨‍🌾 Чат с агрономом"]
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "🌿 *Добро пожаловать в DoctorWood!*\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Доступные команды:*\n"
        "/start - главное меню\n"
        "/myplants - мои растения\n"
        "/diagnose - диагностика по фото\n"
        "/recommendations - рекомендации по уходу\n",
        parse_mode="Markdown",
    )


async def diagnose_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📷 Пришлите фото растения для диагностики",
        reply_markup=ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True),
    )


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    if text == "🌱 Мои растения":
        await my_plants(update, context)

    elif text == "🔍 Диагностика":
        await update.message.reply_text(
            "Выберите тип диагностики:\n"
            "• 📷 Пришлите фото для диагностики по фото\n"
            "• 📝 Опишите симптомы текстом",
            reply_markup=ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True),
        )

    elif text == "📚 Рекомендации":
        await get_recommendations(update, context)

    elif text == "🌍 Поиск растений":
        await update.message.reply_text(
            "Введите название растения для поиска в базе Trefle:",
            reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True),
        )
        # Запускаем диалог Trefle
        from handlers.trefle import trefle_start
        await trefle_start(update, context)

    elif text == "👨‍🌾 Чат с агрономом":
        await update.message.reply_text(
            "👨‍🌾 *Чат с агрономом*\n\n"
            "Эта функция находится в разработке 🛠️\n\n"
            "Скоро вы сможете:\n"
            "• 💬 Задавать вопросы профессиональным агрономам\n"
            "• 📸 Получать консультации по вашим растениям\n"
            "• 🌿 Получать персональные рекомендации\n\n"
            "А пока используйте автоматическую диагностику растений! 🔍",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
        )

    elif text == "⬅️ Назад":
        await start(update, context)


def main():
    # Инициализация БД
    init_db()

    # Создание приложения с более надёжными настройками
    app = Application.builder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myplants", my_plants))
    app.add_handler(CommandHandler("recommendations", get_recommendations))
    app.add_handler(CommandHandler("diagnose", diagnose_command))

    # Диалог добавления растения
    app.add_handler(build_profile_conversation())

    # Trefle поиск
    app.add_handler(build_trefle_conversation())

    # Диагностика по фото
    app.add_handler(MessageHandler(filters.PHOTO, diagnose_photo))

    # Callback для удаления растения
    app.add_handler(CallbackQueryHandler(delete_plant_cb, pattern="^delete_"))

    # Обработка кнопок меню
    app.add_handler(
        MessageHandler(
            filters.Regex(
                "^(🌱 Мои растения|🔍 Диагностика|📚 Рекомендации|🌍 Поиск растений|👨‍🌾 Чат с агрономом|⬅️ Назад)$"
            ),
            handle_menu,
        )
    )

    # Обработка симптомов (только текст, не команды)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symptoms))

    # Убедись, что старый бот остановлен!
    logging.info("🔄 Останавливаем старые процессы...")

    logging.info("✅ Бот запускается...")

    # Запуск с обработкой конфликтов
    try:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True  # Важно! Игнорирует старые сообщения
        )
    except Exception as e:
        logging.error(f"❌ Ошибка запуска: {e}")
        # При конфликте ждём и перезапускаем
        import time
        time.sleep(10)
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()