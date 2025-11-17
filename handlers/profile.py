from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from database import (
    upsert_user,
    add_plant,
    list_plants,
    get_plant,
    delete_plant,
    set_watering_schedule,
    mark_watered
)

# Этапы диалога
ADD_NAME = range(1)
SET_WATERING_INTERVAL = range(2)


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
        text += f"• **{name}**"
        if freq:
            text += f" 💧 каждые {freq} дней"
        text += "\n"

        keyboard.append([
            InlineKeyboardButton(f"💧 Напоминания {name}", callback_data=f"reminders_{pid}"),
            InlineKeyboardButton(f"🗑️ Удалить {name}", callback_data=f"delete_{pid}")
        ])

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

    for key, info in care_info.items():
        if key in plant_name_lower:
            return info

    return "💡 *Общие рекомендации:*\n• Полив: когда верхний слой почвы подсох\n• Свет: яркий рассеянный\n• Температура: 18-25°C\n• Удобрения: весной и летом\n\nДля точной диагностики используйте функцию 🔍 Диагностика"


async def delete_plant_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление растения"""
    query = update.callback_query
    await query.answer()
    if query.data.startswith("delete_"):
        plant_id = int(query.data.split("_")[1])
        delete_plant(plant_id)
        await query.edit_message_text("✅ *Растение удалено*\n\nОбновите список командой /myplants",
                                      parse_mode="Markdown")


async def setup_reminders_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройка напоминаний о поливе"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("reminders_"):
        plant_id = int(query.data.split("_")[1])
        context.user_data['setup_plant_id'] = plant_id

        plant = get_plant(plant_id)
        if plant:
            pid, user_id, name, type_, photo, freq, last_watered, created = plant

            text = (
                f"🛎 *Настройка напоминаний для {name}*\n\n"
                f"Как часто нужно поливать это растение?\n"
                f"Выберите интервал или введите своё значение:"
            )

            keyboard = [
                [InlineKeyboardButton("💧 Каждый день", callback_data="interval_1")],
                [InlineKeyboardButton("💧 Каждые 3 дня", callback_data="interval_3")],
                [InlineKeyboardButton("💧 Раз в неделю", callback_data="interval_7")],
                [InlineKeyboardButton("💧 Раз в 2 недели", callback_data="interval_14")],
                [InlineKeyboardButton("📝 Ввести свой интервал", callback_data="custom_interval")]
            ]

            await query.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return SET_WATERING_INTERVAL


async def handle_interval_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора интервала полива"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("interval_"):
        interval = int(query.data.split("_")[1])
        plant_id = context.user_data.get('setup_plant_id')

        if plant_id:
            set_watering_schedule(plant_id, interval)
            plant = get_plant(plant_id)

            await query.message.reply_text(
                f"✅ *Напоминания настроены!*\n\n"
                f"Растение *{plant[2]}* будет напоминать о поливе каждые {interval} дней.\n\n"
                f"Бот пришлёт уведомление, когда придёт время полить растение.",
                parse_mode="Markdown"
            )

        context.user_data.clear()
        return ConversationHandler.END

    elif query.data == "custom_interval":
        await query.message.reply_text(
            "📝 Введите интервал полива в днях:\n\n"
            "*Пример:* 5 (полив каждые 5 дней)",
            parse_mode="Markdown"
        )
        return SET_WATERING_INTERVAL


async def handle_custom_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пользовательского интервала"""
    try:
        interval = int(update.message.text.strip())
        if interval < 1 or interval > 30:
            await update.message.reply_text("❌ Введите число от 1 до 30 дней")
            return SET_WATERING_INTERVAL

        plant_id = context.user_data.get('setup_plant_id')
        if plant_id:
            set_watering_schedule(plant_id, interval)
            plant = get_plant(plant_id)

            await update.message.reply_text(
                f"✅ *Напоминания настроены!*\n\n"
                f"Растение *{plant[2]}* будет напоминать о поливе каждые {interval} дней.",
                parse_mode="Markdown"
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число")
        return SET_WATERING_INTERVAL


def build_profile_conversation():
    """Диалог добавления растения и настройки напоминаний"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(my_plants_cb, pattern="^add_plant$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            SET_WATERING_INTERVAL: [
                CallbackQueryHandler(handle_interval_selection, pattern="^interval_"),
                CallbackQueryHandler(handle_interval_selection, pattern="^custom_interval$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_interval)
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        per_message=False
    )