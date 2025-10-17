import os
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# API ключ берём из .env
TREFLE_API_KEY = os.getenv("TREFLE_API_KEY")
TREFLE_URL = "https://trefle.io/api/v1/species/search"

# Состояния диалога
ASK_NAME = range(1)


async def trefle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запросить у пользователя название растения"""
    if not TREFLE_API_KEY:
        await update.message.reply_text(
            "❌ API ключ Trefle не найден. Добавьте TREFLE_API_KEY в .env"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🌍 Введите название растения для поиска в базе Trefle:",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True),
    )
    return ASK_NAME


async def trefle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск растения в Trefle API"""
    query = update.message.text.strip()
    if query == "⬅️ Назад":
        await update.message.reply_text("↩️ Возврат в главное меню.")
        return ConversationHandler.END

    url = f"{TREFLE_URL}?q={query}&token={TREFLE_API_KEY}"
    try:
        r = requests.get(url, timeout=15)
        if not r.ok:
            await update.message.reply_text(f"⚠️ Ошибка Trefle API ({r.status_code})")
            return ConversationHandler.END

        data = r.json().get("data", [])
        if not data:
            await update.message.reply_text("ℹ️ Растение не найдено.")
            return ConversationHandler.END

        plant = data[0]
        text = f"🌱 *{plant.get('common_name') or query.title()}*\n"
        text += f"🔬 Научное имя: {plant.get('scientific_name')}\n"
        if plant.get("family_common_name"):
            text += f"🌿 Семейство: {plant['family_common_name']}\n"
        if plant.get("image_url"):
            text += f"\nФото: {plant['image_url']}"

        await update.message.reply_text(
            text, parse_mode="Markdown", disable_web_page_preview=False
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при обращении к Trefle: {e}")

    return ConversationHandler.END


def build_trefle_conversation():
    """Диалог для кнопки 🌍 Trefle"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🌍 Trefle$"), trefle_start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, trefle_search)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
