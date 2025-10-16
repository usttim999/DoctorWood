import logging
import os

# Опциональная загрузка .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram.ext import Application, CommandHandler, MessageHandler, filters,  CallbackQueryHandler
from database import init_db
from handlers.profile import my_plants, build_profile_conversation
from handlers.diagnosis import handle_symptoms as diagnose_text
from handlers.recommendations import get_recommendations
from handlers.profile import delete_plant_cb
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен!")
    exit(1)


async def start(update, context):
    text = (
        "🌿 *Добро пожаловать!*\n\n"
        "Выберите действие:\n"
        "• 🌱 Мои растения — /myplants\n"
        "• 📚 База знаний — /knowledge (скоро)\n"
        "• 🔍 Диагностика (текст) — просто опишите симптомы\n"
        "• 🛎 Напоминания — (скоро)\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update, context):
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

    # Диагностика по тексту — любые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, diagnose_text))
    app.add_handler(CallbackQueryHandler(delete_plant_cb, pattern="^delete_"))
    app.add_handler(CommandHandler("myplants", my_plants))
    app.add_handler(build_profile_conversation())
    app.add_handler(CallbackQueryHandler(delete_plant_cb, pattern="^delete_"))
    logging.info("✅ Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
