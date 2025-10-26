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
        text = "🌱 *У вас пока нет растений*\n\nДобавьте первое растение с помощью кнопки ниже 👇"
        keyboard = [[InlineKeyboardButton("➕ Добавить растение", callback_data="add_plant")]]
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = "🌿 *Мои растения:*\n\n"
    keyboard = []
    for p in plants:
        pid, name, type_, photo, freq, last_watered, created = p
        text += f"• **{name}**\n"
        keyboard.append([InlineKeyboardButton(f"🗑️ Удалить {name}", callback_data=f"delete_{pid}")])

    keyboard.append([InlineKeyboardButton("➕ Добавить растение", callback_data="add_plant")])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def my_plants_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Добавить растение'"""
    query = update.callback_query
    await query.answer()
    if query.data == "add_plant":
        await query.message.reply_text(
            "🌱 *Добавление растения*\n\nВведите название растения:\n\n*Примеры:*\n• Фикус\n• Монстера\n• Орхидея\n• Кактус",
            parse_mode="Markdown"
        )
        return ADD_NAME
    return ConversationHandler.END


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем растение только по названию"""
    plant_name = update.message.text.strip()

    user = update.effective_user
    user_id = upsert_user(
        chat_id=update.effective_chat.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )
    plant_id = add_plant(user_id=user_id, name=plant_name)

    # Базовая информация по популярным растениям
    care_text = get_basic_care_info(plant_name)

    text = f"🌿 *Растение добавлено!*\n\n*Название:* {plant_name}\n\n{care_text}"
    await update.message.reply_text(text, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


def get_basic_care_info(plant_name: str) -> str:
    """Базовая информация по уходу за популярными растениями"""
    plant_name_lower = plant_name.lower()

    care_info = {
        "фикус": "💧 *Полив:* умеренный, когда верхний слой почвы подсохнет\n☀️ *Свет:* яркий рассеянный\n🌡️ *Температура:* 18-25°C\n🌿 *Уход:* регулярное опрыскивание",
        "монстера": "💧 *Полив:* обильный, но давайте почве просыхать\n☀️ *Свет:* полутень или рассеянный свет\n🌡️ *Температура:* 20-25°C\n🌿 *Уход:* опрыскивание, поддержка для роста",
        "орхидея": "💧 *Полив:* умеренный, методом погружения\n☀️ *Свет:* яркий рассеянный, без прямого солнца\n🌡️ *Температура:* 18-25°C\n🌿 *Уход:* специальный субстрат для орхидей",
        "кактус": "💧 *Полив:* редкий, зимой почти не поливать\n☀️ *Свет:* максимально яркий\n🌡️ *Температура:* 20-30°C летом, 10-15°C зимой\n🌿 *Уход:* хорошо дренированная почва",
        "суккулент": "💧 *Полив:* умеренный, давайте почве полностью просохнуть\n☀️ *Свет:* яркий прямой\n🌡️ *Температура:* 18-25°C\n🌿 *Уход:* песчаная почва, хороший дренаж",
        "алое": "💧 *Полив:* умеренный, зимой реже\n☀️ *Свет:* яркий рассеянный\n🌡️ *Температура:* 18-25°C\n🌿 *Уход:* не требует частого ухода",
    }

    # Поиск совпадения
    for key, info in care_info.items():
        if key in plant_name_lower:
            return info

    # Общая информация для неизвестных растений
    return "💡 *Общие рекомендации:*\n• Полив: когда верхний слой почвы подсох\n• Свет: яркий рассеянный\n• Температура: 18-25°C\n• Удобрения: весной и летом\n\nДля точной диагностики используйте функцию 🔍 Диагностика"


async def send_plant_card(update_or_message, plant_id: int):
    """Показать карточку растения"""
    msg = update_or_message.message if hasattr(update_or_message, "message") else update_or_message
    plant = get_plant(plant_id)
    if not plant:
        await msg.reply_text("❌ Не удалось найти растение.")
        return

    pid, user_id, name, type_, photo, freq, last_watered, created = plant
    care_text = get_basic_care_info(name)

    text = f"🌿 *Карточка растения*\n\n*Название:* {name}\n*Добавлено:* {created.split('T')[0]}\n\n{care_text}"

    keyboard = [
        [InlineKeyboardButton("🔍 Диагностика по фото", callback_data=f"diag_photo_{pid}")],
        [InlineKeyboardButton("💧 Отметить полив", callback_data=f"water_{pid}")],
        [InlineKeyboardButton("📝 Добавить заметку", callback_data=f"note_{pid}")],
        [InlineKeyboardButton("🗑️ Удалить растение", callback_data=f"delete_{pid}")],
    ]

    if photo:
        await msg.reply_photo(
            photo=photo,
            caption=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await msg.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def delete_plant_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление растения"""
    query = update.callback_query
    await query.answer()
    if query.data.startswith("delete_"):
        plant_id = int(query.data.split("_")[1])
        delete_plant(plant_id)
        await query.edit_message_text("✅ *Растение удалено*\n\nОбновите список командой /myplants",
                                      parse_mode="Markdown")


def build_profile_conversation():
    """Диалог добавления растения"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(my_plants_cb, pattern="^add_plant$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
