from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_plants_needing_watering, mark_watered


async def send_manual_reminder(bot, chat_id, plant_name, plant_id):
    """Ручная отправка напоминания"""
    message = (
        f"💧 *Пора полить растение!*\n\n"
        f"Растение *{plant_name}* ждет полива.\n\n"
        f"После полива нажмите кнопку ниже 👇"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Полил(а)", callback_data=f"watered_{plant_id}")]
    ]

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_watered_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки 'Полил(а)'"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("watered_"):
        plant_id = int(query.data.split("_")[1])
        mark_watered(plant_id)

        await query.edit_message_text(
            "✅ *Отлично! Растение полито.*\n\n"
            "Напоминание сброшено.",
            parse_mode="Markdown"
        )


async def check_reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручная проверка напоминаний (/check_reminders)"""
    plants = get_plants_needing_watering()

    if not plants:
        await update.message.reply_text("✅ Все растения политы вовремя!")
        return

    bot = context.bot
    reminder_count = 0

    for plant in plants:
        plant_id, name, interval, last_watered, chat_id = plant
        try:
            await send_manual_reminder(bot, chat_id, name, plant_id)
            reminder_count += 1
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания для {name}: {e}")

    await update.message.reply_text(f"📨 Отправлено {reminder_count} напоминаний")