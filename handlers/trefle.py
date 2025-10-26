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
    """Запуск поиска растений"""
    if not TREFLE_API_KEY:
        await update.message.reply_text(
            "❌ API ключ Trefle не настроен. Функция поиска временно недоступна."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🔍 *Поиск растений*\n\n"
        "Введите название растения на русском или английском:\n\n"
        "*Примеры:*\n"
        "• Роза\n"
        "• Ficus\n"
        "• Орхидея\n"
        "• Sunflower",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True),
    )
    return ASK_NAME


async def trefle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск растения в Trefle API"""
    query = update.message.text.strip()

    if query == "⬅️ Назад":
        from handlers.start import MAIN_KEYBOARD
        await update.message.reply_text(
            "↩️ Возврат в главное меню",
            reply_markup=ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
        )
        return ConversationHandler.END

    # Показываем, что идёт поиск
    searching_msg = await update.message.reply_text("🔍 Ищем информацию о растении...")

    try:
        url = f"{TREFLE_URL}?q={query}&token={TREFLE_API_KEY}"
        response = requests.get(url, timeout=15)

        if not response.ok:
            await searching_msg.edit_text(f"❌ Ошибка при поиске (код {response.status_code})")
            return ConversationHandler.END

        data = response.json().get("data", [])
        if not data:
            await searching_msg.edit_text(
                f"🌱 *Растение не найдено*\n\n"
                f"Попробуйте:\n"
                f"• Ввести название на английском\n"
                f"• Проверить правильность написания\n"
                f"• Использовать научное название",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

        plant = data[0]
        await searching_msg.delete()  # Удаляем сообщение о поиске

        # Формируем красивый ответ
        common_name = plant.get('common_name')
        scientific_name = plant.get('scientific_name')
        family = plant.get('family_common_name')
        genus = plant.get('genus')
        image_url = plant.get('image_url')

        text = "🌿 *Информация о растении*\n\n"

        if common_name:
            text += f"*Название:* {common_name}\n"
        else:
            text += f"*Название:* {query.title()}\n"

        if scientific_name:
            text += f"*Научное название:* {scientific_name}\n"

        if family:
            text += f"*Семейство:* {family}\n"

        if genus:
            text += f"*Род:* {genus}\n"

        # Добавляем разделитель
        text += "\n" + "─" * 30 + "\n\n"

        # Основная информация
        if plant.get('observations'):
            text += f"📊 *Наблюдения:* {plant['observations']}\n"

        if plant.get('vegetable'):
            text += "🥬 *Тип:* Овощное растение\n"
        else:
            text += "🌺 *Тип:* Декоративное растение\n"

        if plant.get('edible'):
            text += "🍽️ *Съедобность:* Съедобное\n"
        else:
            text += "⚠️ *Съедобность:* Не съедобное\n"

        # Клавиатура для дополнительных действий
        keyboard = [["🔍 Найти другое растение", "⬅️ Назад"]]

        if image_url:
            # Отправляем фото с описанием
            await update.message.reply_photo(
                photo=image_url,
                caption=text,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )

    except requests.exceptions.Timeout:
        await searching_msg.edit_text(
            "⏰ *Таймаут запроса*\n\n"
            "Поиск занял слишком много времени. Попробуйте позже.",
            parse_mode="Markdown"
        )
    except requests.exceptions.ConnectionError:
        await searching_msg.edit_text(
            "🌐 *Ошибка соединения*\n\n"
            "Проверьте подключение к интернету и попробуйте снова.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await searching_msg.edit_text(
            f"❌ *Ошибка поиска*\n\n"
            f"Техническая информация: {str(e)}",
            parse_mode="Markdown"
        )

    return ConversationHandler.END


async def handle_trefle_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий после поиска"""
    text = update.message.text

    if text == "🔍 Найти другое растение":
        return await trefle_start(update, context)
    elif text == "⬅️ Назад":
        from handlers.start import MAIN_KEYBOARD
        await update.message.reply_text(
            "↩️ Возврат в главное меню",
            reply_markup=ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
        )
        return ConversationHandler.END

    return ConversationHandler.END


def build_trefle_conversation():
    """Диалог для кнопки 🌍 Поиск растений"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🌍 Поиск растений$"), trefle_start)],
        states={
            ASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trefle_search),
                MessageHandler(filters.Regex("^(🔍 Найти другое растение|⬅️ Назад)$"), handle_trefle_actions)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    )