from telegram import Update
from telegram.ext import ContextTypes
from config import PLANT_DISEASES


async def diagnose_plant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диагностики"""
    text = """
🔍 *Диагностика проблем растений*

Опишите симптомы, которые вы заметили у вашего растения
    """
    await update.message.reply_text(text, parse_mode='Markdown')


async def handle_symptoms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания симптомов"""
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
