import logging
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def main():
    """Запуск бота"""
    token = os.getenv('BOT_TOKEN')

    if not token:
        logging.error("BOT_TOKEN не установлен!")
        return

    # Создаем updater и dispatcher
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    # Регистрируем обработчики
    from handlers.start import start, help_command
    from handlers.diagnosis import diagnose_plant, handle_symptoms
    from handlers.recommendations import get_recommendations

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("diagnose", diagnose_plant))
    dispatcher.add_handler(CommandHandler("recommendations", get_recommendations))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_symptoms))

    # Запускаем бота
    print("Бот запущен...")
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()