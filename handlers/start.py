from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

# Главное меню
MAIN_KEYBOARD = [
    ["🌱 Мои растения", "🔍 Диагностика"],
    ["📚 Рекомендации", "🌍 Поиск растений"],
    ["👨‍🌾 Чат с агрономом"]
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    reply_markup = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

    welcome_text = """
🌿 *Добро пожаловать в DoctorWood!*

Я помогу вам:
• 🔍 Диагностировать проблемы растений
• 💊 Получить рекомендации по лечению  
• 🌱 Вести учёт ваших растений
• 👨‍🌾 Получить консультацию агронома

*Выберите действие кнопками ниже:* 👇
    """
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
*Как пользоваться ботом:*

• 🌱 *Мои растения* - добавьте растения для персонализированных советов
• 🔍 *Диагностика* - пришлите фото или опишите симптомы проблемы
• 📚 *Рекомендации* - общие советы по уходу
• 🌍 *Поиск растений* - найдите информацию о любом растении
• 👨‍🌾 *Чат с агрономом* - консультация специалиста

*Команды:*
/start - главное меню
/myplants - мои растения  
/diagnose - диагностика по фото
/recommendations - советы по уходу
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    reply_markup = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "↩️ *Возврат в главное меню*",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )