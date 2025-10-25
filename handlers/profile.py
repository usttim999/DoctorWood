import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from database import upsert_user, add_plant, list_plants, get_plant, delete_plant

# Этап диалога
ADD_NAME = range(1)

OPENFARM_URL = "https://openfarm.cc/api/v1/crops?filter="


async def my_plants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список растений пользователя"""
    user = update.effective_user
    user_id = upsert_user(
        chat_id=update.effective_chat.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    plants = list_plants(user_id)
    if not plants:
        text = "У вас пока нет растений. Добавьте первое с помощью кнопки ниже."
        keyboard = [[InlineKeyboardButton("➕ Добавить растение", callback_data="add_plant")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = "*Мои растения:*\n\n"
    keyboard = []
    for p in plants:
        pid, name, type_, photo, freq, last_watered, created = p
        text += f"• {name}\n"
        keyboard.append([InlineKeyboardButton(f"❌ Удалить {name}", callback_data=f"delete_{pid}")])

    keyboard.append([InlineKeyboardButton("➕ Добавить растение", callback_data="add_plant")])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def my_plants_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Добавить растение'"""
    query = update.callback_query
    await query.answer()
    if query.data == "add_plant":
        await query.message.reply_text("Введите название растения (например: «Фикус»):")
        return ADD_NAME
    return ConversationHandler.END


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем растение только по названию и показываем рекомендации"""
    plant_name = update.message.text.strip()

    user = update.effective_user
    user_id = upsert_user(
        chat_id=update.effective_chat.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    plant_id = add_plant(user_id=user_id, name=plant_name)

    # Получаем рекомендации из OpenFarm
    care_text = await fetch_openfarm_care(plant_name)

    text = f"*Карточка растения*\nНазвание: {plant_name}\n\n{care_text}"
    await update.message.reply_text(text, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


# Словарь для перевода популярных русских названий в английские
NAME_MAP = {
    "фикус": "ficus",
    "монстера": "monstera",
    "суккулент": "succulent",
    "орхидея": "orchid",
    "алое": "aloe",
    "кактус": "cactus",
}

async def fetch_openfarm_care(plant_name: str) -> str:
    """Запрос к OpenFarm API для получения рекомендаций"""
    try:
        # если название на русском — подставляем английский аналог
        query = NAME_MAP.get(plant_name.lower(), plant_name)

        response = requests.get(OPENFARM_URL + query, timeout=15)
        if not response.ok:
            return f"⚠️ Ошибка OpenFarm API ({response.status_code})"

        # проверяем, что ответ действительно JSON
        if "application/json" not in response.headers.get("Content-Type", ""):
            return "ℹ️ OpenFarm вернул неожиданный ответ. Попробуйте ввести название на английском."

        data = response.json()
        crops = data.get("data", [])
        if not crops:
            return "ℹ️ Рекомендации по уходу пока не найдены. Попробуйте ввести название на английском."

        crop = crops[0]
        attr = crop.get("attributes", {})

        text = ""
        if attr.get("description"):
            text += f"📖 {attr['description']}\n\n"
        if attr.get("sun_requirements"):
            text += f"☀️ Свет: {attr['sun_requirements']}\n"
        if attr.get("sowing_method"):
            text += f"🌱 Посев: {attr['sowing_method']}\n"

        return text or "ℹ️ Рекомендации по уходу пока не найдены."
    except Exception as e:
        return f"⚠️ Ошибка при обращении к OpenFarm: {e}"



async def send_plant_card(update_or_message, plant_id: int):
    """Показать карточку растения"""
    msg = update_or_message.message if hasattr(update_or_message, "message") else update_or_message
    plant = get_plant(plant_id)
    if not plant:
        await msg.reply_text("Не удалось найти растение.")
        return

    pid, user_id, name, type_, photo, freq, last_watered, created = plant
    care_text = await fetch_openfarm_care(name)

    text = f"*Карточка растения*\nНазвание: {name}\nДобавлено: {created.split('T')[0]}\n\n{care_text}"

    keyboard = [
        [InlineKeyboardButton("🔍 Диагностика по фото", callback_data=f"diag_photo_{pid}")],
        [InlineKeyboardButton("🛎 Настроить напоминания", callback_data=f"reminders_{pid}")],
        [InlineKeyboardButton("📜 История ухода", callback_data=f"history_{pid}")],
        [InlineKeyboardButton("❌ Удалить растение", callback_data=f"delete_{pid}")],
    ]

    if photo:
        await msg.reply_photo(photo=photo, caption=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def delete_plant_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление растения"""
    query = update.callback_query
    await query.answer()
    if query.data.startswith("delete_"):
        plant_id = int(query.data.split("_")[1])
        delete_plant(plant_id)
        await query.edit_message_text("✅ Растение удалено.\nОбновите список командой /myplants")


def build_profile_conversation():
    """Диалог добавления растения (только название)"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(my_plants_cb, pattern="^add_plant$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
