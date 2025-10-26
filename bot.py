import logging
import os
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

from database import (
    init_db,
    get_plants_needing_watering,
    mark_watered
)
from handlers.profile import (
    my_plants,
    build_profile_conversation,
    delete_plant_cb,
    setup_reminders_cb,
    handle_interval_selection,
    handle_custom_interval,
    SET_WATERING_INTERVAL
)
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


async def check_watering_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Проверка растений, которые нужно полить"""
    plants_to_water = get_plants_needing_watering()

    for plant in plants_to_water:
        plant_id, plant_name, interval, last_watered, chat_id = plant
        message = (
            f"💧 *Напоминание о поливе*\n\n"
            f"Растение *{plant_name}* пора полить!\n"
            f"Последний полив: {last_watered.split('T')[0]}\n"
            f"Интервал: каждые {interval} дней\n\n"
            f"После полива нажмите кнопку ниже 👇"
        )

        keyboard = [
            [InlineKeyboardButton("✅ Полил(а)", callback_data=f"watered_{plant_id}")],
            [InlineKeyboardButton("🌱 Мои растения", callback_data="show_plants")]
        ]

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logging.error(f"Не удалось отправить напоминание: {e}")


async def handle_watered_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отметки о поливе"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("watered_"):
        plant_id = int(query.data.split("_")[1])
        mark_watered(plant_id)

        await query.edit_message_text(
            "✅ *Отлично!* Растение полито.\n\n"
            "Следующее напоминание придёт согласно установленному графику.",
            parse_mode="Markdown"
        )


def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Настройка JobQueue для напоминаний
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            check_watering_reminders,
            interval=3600,  # Проверка каждый час
            first=10
        )

    # Обработчики напоминаний
    app.add_handler(CallbackQueryHandler(handle_watered_callback, pattern="^watered_"))

    # ConversationHandler для напоминаний
    reminder_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(setup_reminders_cb, pattern="^reminders_")],
        states={
            SET_WATERING_INTERVAL: [
                CallbackQueryHandler(handle_interval_selection, pattern="^interval_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_interval)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_message=False
    )
    app.add_handler(reminder_conv)

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

    # Обработка симптомов
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symptoms))

    logging.info("✅ Бот запускается...")

    try:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logging.error(f"❌ Ошибка запуска: {e}")
        import time
        time.sleep(10)
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()