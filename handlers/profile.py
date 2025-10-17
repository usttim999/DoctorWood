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

    # Простая карточка без OpenFarm
    text = f"*Карточка растения*\nНазвание: {plant_name}\nℹ️ Рекомендации пока не добавлены."
    await update.message.reply_text(text, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


async def send_plant_card(update_or_message, plant_id: int):
    """Показать карточку растения"""
    msg = update_or_message.message if hasattr(update_or_message, "message") else update_or_message
    plant = get_plant(plant_id)
    if not plant:
        await msg.reply_text("Не удалось найти растение.")
        return

    pid, user_id, name, type_, photo, freq, last_watered, created = plant
    text = f"*Карточка растения*\nНазвание: {name}\nДобавлено: {created.split('T')[0]}\nℹ️ Рекомендации пока не добавлены."

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
