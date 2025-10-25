from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
*Как пользоваться ботом:*

1. Используйте /diagnose для начала диагностики
2. Опишите симптомы вашего растения
3. Я проанализирую симптомы и дам рекомендации
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')
