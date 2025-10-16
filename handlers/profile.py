from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from database import init_db, upsert_user, add_plant, list_plants, get_plant, delete_plant

# Этапы диалога для добавления растения
ADD_NAME, ADD_TYPE, ADD_PHOTO, ADD_WATER_FREQ = range(4)


async def my_plants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = upsert_user(
        chat_id=update.effective_chat.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
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
        text += f"• {name} ({type_ or 'тип не указан'})\n"
        # для каждого растения добавляем кнопку удаления
        keyboard.append([InlineKeyboardButton(f"❌ Удалить {name}", callback_data=f"delete_{pid}")])

    # внизу кнопка добавления
    keyboard.append([InlineKeyboardButton("➕ Добавить растение", callback_data="add_plant")])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def my_plants_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_plant":
        await query.message.reply_text("Введите название растения (например: «Фикус Бенджамина»):")
        return ADD_NAME

    return ConversationHandler.END


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["plant_name"] = update.message.text.strip()
    await update.message.reply_text("Укажите тип/вид растения (например: «фикус», «монстера», «суккулент»). Если не знаете — напишите «пропустить».")
    return ADD_TYPE


async def add_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["plant_type"] = None if text.lower() == "пропустить" else text
    await update.message.reply_text("Отправьте фото растения или напишите «пропустить».")
    return ADD_PHOTO


async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file_id = None
    if update.message.photo:
        # Берём крупное фото
        photo = update.message.photo[-1]
        photo_file_id = photo.file_id

    context.user_data["photo_file_id"] = photo_file_id
    await update.message.reply_text("Как часто поливать? Укажите число дней (например: 7). Если не уверены — напишите «пропустить».")
    return ADD_WATER_FREQ


async def add_water_freq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    watering_every_days = None
    if text != "пропустить":
        try:
            watering_every_days = int(text)
        except ValueError:
            await update.message.reply_text("Пожалуйста, укажите число (например: 7) или напишите «пропустить».")
            return ADD_WATER_FREQ

    # Сохраняем в БД
    user = update.effective_user
    user_id = upsert_user(
        chat_id=update.effective_chat.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    plant_id = add_plant(
        user_id=user_id,
        name=context.user_data.get("plant_name"),
        type_=context.user_data.get("plant_type"),
        photo_file_id=context.user_data.get("photo_file_id"),
        watering_every_days=watering_every_days
    )

    # Показать карточку растения
    await send_plant_card(update, plant_id)
    context.user_data.clear()
    return ConversationHandler.END


async def send_plant_card(update_or_message, plant_id: int):
    # update_or_message может быть Update или Message
    msg = update_or_message.message if hasattr(update_or_message, "message") else update_or_message

    plant = get_plant(plant_id)
    if not plant:
        await msg.reply_text("Не удалось найти растение.")
        return

    pid, user_id, name, type_, photo, freq, last_watered, created = plant
    text = (
        f"*Карточка растения*\n"
        f"Название: {name}\n"
        f"Тип: {type_ or 'не указан'}\n"
        f"Полив: каждые {freq or 'N/A'} дней\n"
        f"Последний полив: {last_watered or 'нет данных'}\n"
        f"Добавлено: {created.split('T')[0]}"
    )

    keyboard = [
        [InlineKeyboardButton("🔍 Диагностика по фото", callback_data=f"diag_photo_{pid}")],
        [InlineKeyboardButton("🛎 Настроить напоминания", callback_data=f"reminders_{pid}")],
        [InlineKeyboardButton("📜 История ухода", callback_data=f"history_{pid}")],
    ]

    if photo:
        await msg.reply_photo(photo=photo, caption=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


def build_profile_conversation():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(my_plants_cb, pattern="^add_plant$")
        ],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_type)],
            ADD_PHOTO: [MessageHandler((filters.PHOTO | (filters.TEXT & ~filters.COMMAND)), add_photo)],
            ADD_WATER_FREQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_water_freq)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
async def send_plant_card(update_or_message, plant_id: int):
    msg = update_or_message.message if hasattr(update_or_message, "message") else update_or_message

    plant = get_plant(plant_id)
    if not plant:
        await msg.reply_text("Не удалось найти растение.")
        return

    pid, user_id, name, type_, photo, freq, last_watered, created = plant
    text = (
        f"*Карточка растения*\n"
        f"Название: {name}\n"
        f"Тип: {type_ or 'не указан'}\n"
        f"Полив: каждые {freq or 'N/A'} дней\n"
        f"Последний полив: {last_watered or 'нет данных'}\n"
        f"Добавлено: {created.split('T')[0]}"
    )

    keyboard = [
        [InlineKeyboardButton("🔍 Диагностика по фото", callback_data=f"diag_photo_{pid}")],
        [InlineKeyboardButton("🛎 Настроить напоминания", callback_data=f"reminders_{pid}")],
        [InlineKeyboardButton("📜 История ухода", callback_data=f"history_{pid}")],
        [InlineKeyboardButton("❌ Удалить растение", callback_data=f"delete_{pid}")]
    ]

    if photo:
        await msg.reply_photo(photo=photo, caption=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def delete_plant_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("delete_"):
        plant_id = int(query.data.split("_")[1])
        delete_plant(plant_id)
        await query.edit_message_text("✅ Растение удалено.\nОбновите список командой /myplants")