import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update, context):
    """Обработчик команды /start"""
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
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update, context):
    """Обработчик команды /help"""
    help_text = """
*Как пользоваться ботом:*
1. Используйте /diagnose для начала диагностики
2. Опишите симптомы вашего растения
3. Я проанализирую симптомы и дам рекомендации
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def handle_symptoms(update, context):
    """Обработка описания симптомов"""
    from config import PLANT_DISEASES

    user_text = update.message.text.lower()

    # Поиск совпадений в базе знаний
    found_diseases = []

    for disease, info in PLANT_DISEASES.items():
        for symptom in info['symptoms']:
            if symptom in user_text:
                found_diseases.append((disease, info))
                break

    if found_diseases:
        response = "🔍 *Результаты диагностики:*\n\n"

        for disease_name, disease_info in found_diseases:
            response += f"*{disease_name.upper()}*\n"
            response += f"*Возможные причины:* {', '.join(disease_info['causes'])}\n"
            response += f"*Лечение:* {disease_info['treatment']}\n"
            response += f"*Профилактика:* {disease_info['prevention']}\n\n"
    else:
        response = "❌ Не удалось определить проблему. Опишите симптомы подробнее."

    await update.message.reply_text(response, parse_mode='Markdown')


def main():
    """Запуск бота"""
    token = os.getenv('BOT_TOKEN')

    if not token:
        logging.error("BOT_TOKEN не установлен!")
        return

    # Создаем приложение
    application = Application.builder().token(token).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("diagnose", start))  # Временно используем start
    application.add_handler(CommandHandler("recommendations", help_command))  # Временно
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symptoms))

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()