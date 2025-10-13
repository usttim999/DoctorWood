import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def main():
    """Запуск бота"""
    # Для Render используем переменные окружения
    token = os.getenv('BOT_TOKEN')

    if not token:
        logging.error("BOT_TOKEN не установлен!")
        return

    application = Application.builder().token(token).build()

    # Регистрируем обработчики
    from handlers.start import start, help_command
    from handlers.diagnosis import diagnose_plant, handle_symptoms
    from handlers.recommendations import get_recommendations

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("diagnose", diagnose_plant))
    application.add_handler(CommandHandler("recommendations", get_recommendations))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symptoms))

    # Простой запуск через polling
    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()