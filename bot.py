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
    ConversationHandler
)

from database import init_db
from handlers.profile import my_plants, build_profile_conversation, build_reminders_conversation, delete_plant_cb, setup_reminders_cb, \
    handle_interval_selection
from handlers.diagnosis import handle_symptoms
from handlers.recommendations import build_recommendations_conversation
from handlers.diagnose_photo import diagnose_photo
from handlers.trefle import build_trefle_conversation
from handlers.start import start, help_command, back_to_main
from handlers.gigachat_gardener import build_gardener_conversation
from handlers.reminders import handle_watered_callback, check_reminders_command, send_manual_reminder

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен!")
    exit(1)

MAIN_KEYBOARD = [
    ["🌱 Мои растения", "🔍 Диагностика"],
    ["📚 Рекомендации", "🌍 Поиск растений"],
    ["👨‍🌾 Чат с агрономом"]
]


async def check_watering_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Проверка напоминаний о поливе"""
    from database import get_plants_needing_watering
    plants = get_plants_needing_watering()

    print(f"🔍 Проверка напоминаний: найдено {len(plants)} растений")

    if not plants:
        print("ℹ️ Нет растений, требующих полива")
        return

    for plant in plants:
        plant_id, name, interval, last_watered, chat_id = plant
        print(f"💧 Растение нуждается в поливе: {name} (ID: {plant_id}, интервал: {interval} дней)")

        try:
            await send_manual_reminder(context.bot, chat_id, name, plant_id)
            print(f"✅ Напоминание отправлено для {name} в чат {chat_id}")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания для {name}: {e}")


async def test_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда для создания растения с интервалом 1 день"""
    from database import add_plant, set_watering_schedule, upsert_user
    import datetime

    user_id = upsert_user(
        chat_id=update.effective_chat.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        last_name=update.effective_user.last_name
    )

    plant_id = add_plant(user_id, "Тестовое растение", "тест")

    set_watering_schedule(plant_id, 1)

    from database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        old_date = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()
        cur.execute("UPDATE plants SET last_watered_at = ? WHERE id = ?", (old_date, plant_id))
        conn.commit()

    await update.message.reply_text(
        "✅ Тестовое растение создано с интервалом полива 1 день!\n"
        "Напоминание придет в течение 5 минут."
    )


def setup_handlers(application):
    """Настройка всех обработчиков"""

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myplants", my_plants))
    application.add_handler(CommandHandler("check_reminders", check_reminders_command))
    application.add_handler(CommandHandler("test_reminder", test_reminder))  # только для теста

    application.add_handler(MessageHandler(filters.Regex("^🌱 Мои растения$"), my_plants))
    application.add_handler(MessageHandler(filters.Regex("^🔍 Диагностика$"), diagnose_photo))

    from handlers.recommendations import build_recommendations_conversation
    application.add_handler(build_recommendations_conversation())

    application.add_handler(MessageHandler(filters.Regex("^⬅️ Назад$"), back_to_main))
    application.add_handler(MessageHandler(filters.Regex("^↩️ Назад$"), back_to_main))

    application.add_handler(MessageHandler(filters.PHOTO, diagnose_photo))

    application.add_handler(build_trefle_conversation())
    application.add_handler(build_gardener_conversation())
    application.add_handler(build_profile_conversation())
    application.add_handler(build_reminders_conversation())

    application.add_handler(CallbackQueryHandler(delete_plant_cb, pattern="^delete_"))
    application.add_handler(CallbackQueryHandler(setup_reminders_cb, pattern="^reminders_"))
    application.add_handler(CallbackQueryHandler(handle_watered_callback, pattern="^watered_"))
    application.add_handler(CallbackQueryHandler(handle_interval_selection, pattern="^interval_"))
    application.add_handler(CallbackQueryHandler(handle_interval_selection, pattern="^custom_interval$"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symptoms))


def create_application():
    """Создание и настройка приложения"""
    application = Application.builder().token(TOKEN).build()
    setup_handlers(application)

    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            check_watering_reminders,
            interval=300,
            first=10
        )
        print("🔔 Автоматические напоминания настроены")

    return application


def main():
    """Локальный запуск"""
    print("🔄 Инициализация БД...")
    init_db()
    print("✅ БД инициализирована")

    application = create_application()

    print("🤖 Бот запущен локально...")
    print("💧 Напоминания будут приходить каждые 5 минут")
    print("🔧 Для теста используйте /test_reminder")

    application.run_polling()


if __name__ == "__main__":
    main()