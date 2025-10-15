import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Загружаем .env (локально работает, на Render просто проигнорируется, если файла нет)
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Получаем токен
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logging.error("❌ BOT_TOKEN не установлен! Проверь .env или переменные окружения")
    exit(1)


# --- Обработчики команд ---
async def start(update, context):
    welcome_text = """
🌿 *Добро пожаловать в бот для диагностики растений!*

Я помогу вам:
• 🔍 Диагностировать проблемы растений по симптомам
• 💊 Получить рекомендации по лечению
• 🛡️ Узнать о методах профилактики

*Доступные команды:*
/start - Начать работу
/diagnose - Диагностировать проблему
/recommendations - Получить общие рекомендации
/help - Помощь

Опишите симптомы вашего растения, и я помогу определить проблему!
    """
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update, context):
    help_text = """
*Как пользоваться ботом:*
1. Используйте /diagnose для начала диагностики
2. Опишите симптомы вашего растения
3. Я проанализирую симптомы и дам рекомендации
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def diagnose(update, context):
    from handlers.diagnosis import diagnose_plant
    await diagnose_plant(update, context)


async def recommendations(update, context):
    from handlers.recommendations import get_recommendations
    await get_recommendations(update, context)


async def handle_symptoms(update, context):
    from handlers.diagnosis import handle_symptoms as hs
    await hs(update, context)


# --- Основная функция ---
def main():
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("diagnose", diagnose))
    application.add_handler(CommandHandler("recommendations", recommendations))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symptoms))

    logging.info("✅ Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()
