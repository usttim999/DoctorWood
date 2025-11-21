import os
import requests
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from deep_translator import GoogleTranslator

# Импортируем функцию назад
from handlers.start import back_to_main

# Настройка логгера для Trefle
logger = logging.getLogger(__name__)

# API ключ берём из .env
TREFLE_API_KEY = os.getenv("TREFLE_API_KEY")
TREFLE_BASE_URL = "https://trefle.io/api/v1"

# Состояния диалога
ASK_NAME, AFTER_SEARCH = range(2)

# Словарь для перевода месяцев
MONTHS_TRANSLATION = {
    'january': 'Январь', 'february': 'Февраль', 'march': 'Март',
    'april': 'Апрель', 'may': 'Май', 'june': 'Июнь',
    'july': 'Июль', 'august': 'Август', 'september': 'Сентябрь',
    'october': 'Октябрь', 'november': 'Ноябрь', 'december': 'Декабрь'
}


def detect_language(plant_name):
    """Определяем язык введенного названия"""
    cyrillic_chars = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    if any(char in cyrillic_chars for char in plant_name.lower()):
        return 'russian'
    else:
        return 'latin'


def translate_to_latin(russian_name):
    """Перевод русского названия на латынь"""
    try:
        latin_name = GoogleTranslator(source='ru', target='la').translate(russian_name)
        return latin_name
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return None


def get_light_description(light_level):
    """Описание уровня освещения"""
    if light_level is None:
        return None

    light_map = {
        0: "❌ Без света (<= 10 lux)",
        1: "💡 Очень слабое",
        2: "💡 Слабое",
        3: "💡 Слабое",
        4: "🔆 Умеренное",
        5: "🔆 Умеренное",
        6: "☀️ Яркое",
        7: "☀️ Яркое",
        8: "☀️ Очень яркое",
        9: "🔥 Интенсивное",
        10: "🔥 Очень интенсивное (>= 100,000 lux)"
    }
    return light_map.get(light_level, f"Уровень {light_level}/10")


def get_toxicity_description(toxicity):
    """Описание токсичности"""
    if not toxicity:
        return None

    toxicity_map = {
        'none': "✅ Безопасно",
        'low': "⚠️ Низкая токсичность",
        'medium': "⚠️ Средняя токсичность",
        'high': "☠️ Высокая токсичность"
    }
    return toxicity_map.get(toxicity, toxicity)


def get_care_difficulty(plant_data):
    """Определяем сложность ухода на основе данных"""
    score = 0
    growth = plant_data.get('growth', {})

    # Анализируем требования
    if growth.get('ph_minimum') and growth.get('ph_maximum'):
        score += 1

    if growth.get('minimum_temperature') and growth.get('maximum_temperature'):
        score += 1

    if growth.get('soil_humidity') is not None:
        score += 1

    if score == 0:
        return "🟢 Легкий уход"
    elif score == 1:
        return "🟡 Средняя сложность"
    else:
        return "🔴 Сложный уход"


def get_available_care_data(plant_data):
    """Собираем ВСЮ доступную информацию о растении"""
    growth = plant_data.get('growth', {})
    specs = plant_data.get('specifications', {})
    foliage = plant_data.get('foliage', {})
    flower = plant_data.get('flower', {})
    fruit = plant_data.get('fruit_or_seed', {})

    care_info = []

    # 💧 ВОДНЫЙ РЕЖИМ
    water_section = []
    soil_humidity = growth.get('soil_humidity')
    if soil_humidity is not None:
        if soil_humidity >= 7:
            water_section.append("💧 Обильный полив")
        elif soil_humidity >= 4:
            water_section.append("💧 Умеренный полив")
        else:
            water_section.append("💧 Редкий полив")

    min_precip = growth.get('minimum_precipitation', {}).get('mm')
    max_precip = growth.get('maximum_precipitation', {}).get('mm')
    if min_precip and max_precip:
        water_section.append(f"🌧️ Осадки: {min_precip}-{max_precip} мм/год")

    if water_section:
        care_info.append("💧 *Водный режим:*\n" + "\n".join(f"• {item}" for item in water_section))

    # ☀️ ОСВЕЩЕНИЕ И ТЕМПЕРАТУРА
    light_temp_section = []

    # Освещение
    light_level = growth.get('light')
    if light_level is not None:
        light_desc = get_light_description(light_level)
        if light_desc:
            light_temp_section.append(f"☀️ Освещение: {light_desc}")

    # Температура
    min_temp = growth.get('minimum_temperature', {}).get('deg_c')
    max_temp = growth.get('maximum_temperature', {}).get('deg_c')
    if min_temp and max_temp:
        light_temp_section.append(f"🌡️ Температура: {min_temp}°C - {max_temp}°C")
    elif min_temp:
        light_temp_section.append(f"🌡️ Мин. температура: {min_temp}°C")
    elif max_temp:
        light_temp_section.append(f"🌡️ Макс. температура: {max_temp}°C")

    if light_temp_section:
        care_info.append("🌡️ *Условия содержания:*\n" + "\n".join(f"• {item}" for item in light_temp_section))

    # 🧪 ПОЧВА
    soil_section = []

    # pH
    ph_min = growth.get('ph_minimum')
    ph_max = growth.get('ph_maximum')
    if ph_min and ph_max:
        soil_section.append(f"🧪 pH почвы: {ph_min} - {ph_max}")
    elif ph_min:
        soil_section.append(f"🧪 Мин. pH: {ph_min}")
    elif ph_max:
        soil_section.append(f"🧪 Макс. pH: {ph_max}")

    # Текстура почвы
    soil_texture = growth.get('soil_texture')
    if soil_texture is not None:
        texture_map = {0: "Глинистая", 5: "Суглинистая", 10: "Скалистая"}
        soil_section.append(f"🏺 Текстура: {texture_map.get(soil_texture, f'Уровень {soil_texture}/10')}")

    # Питательность почвы
    soil_nutrients = growth.get('soil_nutriments')
    if soil_nutrients is not None:
        nutrient_map = {0: "Бедная", 5: "Средняя", 10: "Очень питательная"}
        soil_section.append(f"📊 Питательность: {nutrient_map.get(soil_nutrients, f'Уровень {soil_nutrients}/10')}")

    if soil_section:
        care_info.append("🏺 *Почва:*\n" + "\n".join(f"• {item}" for item in soil_section))

    # 🌿 ХАРАКТЕРИСТИКИ РАСТЕНИЯ
    characteristics_section = []

    # Высота
    avg_height = specs.get('average_height', {}).get('cm')
    max_height = specs.get('maximum_height', {}).get('cm')
    if avg_height and max_height:
        characteristics_section.append(f"📏 Высота: {avg_height}-{max_height} см")
    elif avg_height:
        characteristics_section.append(f"📏 Средняя высота: {avg_height} см")
    elif max_height:
        characteristics_section.append(f"📏 Макс. высота: {max_height} см")

    # Форма роста
    growth_form = specs.get('growth_form')
    if growth_form:
        characteristics_section.append(f"🌿 Форма: {growth_form}")

    growth_habit = specs.get('growth_habit')
    if growth_habit:
        characteristics_section.append(f"🎋 Габитус: {growth_habit}")

    # Текстура листьев
    foliage_texture = foliage.get('texture')
    if foliage_texture:
        texture_map = {'fine': "Мелкая", 'medium': "Средняя", 'coarse': "Крупная"}
        characteristics_section.append(f"🍃 Текстура листьев: {texture_map.get(foliage_texture, foliage_texture)}")

    if characteristics_section:
        care_info.append("🌿 *Характеристики:*\n" + "\n".join(f"• {item}" for item in characteristics_section))

    # 🌸 ЦВЕТЕНИЕ И ПЛОДОНОШЕНИЕ
    reproduction_section = []

    # Цветение
    bloom_months = growth.get('bloom_months', [])
    if bloom_months:
        translated_months = [MONTHS_TRANSLATION.get(month.lower(), month) for month in bloom_months]
        reproduction_section.append(f"🌸 Цветение: {', '.join(translated_months)}")

    # Плодоношение
    fruit_months = growth.get('fruit_months', [])
    if fruit_months:
        translated_months = [MONTHS_TRANSLATION.get(month.lower(), month) for month in fruit_months]
        reproduction_section.append(f"🍓 Плодоношение: {', '.join(translated_months)}")

    # Цвет цветов
    flower_color = flower.get('color', [])
    if flower_color:
        reproduction_section.append(f"🎨 Цвет цветов: {', '.join(flower_color)}")

    if reproduction_section:
        care_info.append("🌸 *Размножение:*\n" + "\n".join(f"• {item}" for item in reproduction_section))

    # ⚠️ БЕЗОПАСНОСТЬ
    safety_section = []

    # Токсичность
    toxicity = specs.get('toxicity')
    if toxicity:
        toxicity_desc = get_toxicity_description(toxicity)
        if toxicity_desc:
            safety_section.append(f"⚠️ Токсичность: {toxicity_desc}")

    # Съедобность
    edible = plant_data.get('edible')
    if edible is not None:
        safety_section.append("🍽️ Съедобность: " + ("✅ Съедобное" if edible else "❌ Не съедобное"))

    if safety_section:
        care_info.append("⚠️ *Безопасность:*\n" + "\n".join(f"• {item}" for item in safety_section))

    return care_info


async def trefle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск поиска растений"""
    if not TREFLE_API_KEY:
        await update.message.reply_text(
            "❌ API ключ Trefle не настроен. Функция поиска временно недоступна."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🔍 *Умный поиск растений*\n\n"
        "Введите название растения на русском или латыни:\n\n"
        "*Примеры:*\n"
        "• Роза (автоматически переведётся на латынь)\n"
        "• Rosa (поиск на латыни)\n"
        "• Ficus benjamina\n"
        "• Орхидея",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True),
    )
    return ASK_NAME


async def trefle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Умный поиск растения в Trefle API с авто-переводом"""
    query = update.message.text.strip()

    if query == "⬅️ Назад":
        return await back_to_main(update, context)

    # Показываем, что идёт поиск
    searching_msg = await update.message.reply_text("🔍 Ищем информацию о растении...")

    try:
        # Определяем язык и переводим при необходимости
        language = detect_language(query)

        if language == 'russian':
            latin_query = translate_to_latin(query)
            search_query = latin_query if latin_query else query
            logger.info(f"🔤 ОТЛАДКА: Перевод '{query}' -> '{latin_query}'")
        else:
            search_query = query

        context.user_data['original_query'] = query
        context.user_data['search_query'] = search_query

        # Поиск в Trefle
        url = f"{TREFLE_BASE_URL}/plants/search"
        params = {
            'q': search_query,
            'token': TREFLE_API_KEY
        }

        logger.info(f"🔍 ОТЛАДКА: Поисковый запрос: {search_query}")
        response = requests.get(url, params=params, timeout=15)

        if not response.ok:
            await searching_msg.edit_text(f"❌ Ошибка при поиске (код {response.status_code})")
            return ASK_NAME

        data = response.json().get("data", [])
        logger.info(f"📊 ОТЛАДКА: Найдено результатов: {len(data)}")

        if not data:
            await searching_msg.edit_text(
                f"🌱 *Растение не найдено*\n\n"
                f"*Ваш запрос:* {query}\n"
                f"*Поисковый запрос:* {search_query}\n\n"
                f"Попробуйте:\n"
                f"• Ввести научное название на латыни\n"
                f"• Проверить правильность написания\n"
                f"• Использовать английское название",
                parse_mode="Markdown"
            )
            return ASK_NAME

        plant = data[0]
        await searching_msg.delete()

        # Получаем детальную информацию о растении
        plant_id = plant.get('id')
        if plant_id:
            detail_url = f"{TREFLE_BASE_URL}/species/{plant_id}"
            detail_params = {'token': TREFLE_API_KEY}
            detail_response = requests.get(detail_url, params=detail_params, timeout=10)
            if detail_response.ok:
                plant_detail = detail_response.json().get('data', {})
                logger.info(f"🔍 ОТЛАДКА: Детальная информация получена: {bool(plant_detail)}")
                plant.update(plant_detail)

        # Формируем улучшенный ответ
        common_name = plant.get('common_name')
        scientific_name = plant.get('scientific_name')
        family = plant.get('family_common_name') or plant.get('family')
        genus = plant.get('genus')
        image_url = plant.get('image_url')

        text = "🌿 *Детальная информация о растении*\n\n"

        # Информация о запросе
        if language == 'russian':
            text += f"*Ваш запрос:* {query}\n"
            if search_query != query:
                text += f"*Перевод на латынь:* {search_query}\n"
        else:
            text += f"*Ваш запрос:* {query}\n"

        text += f"*Научное название:* {scientific_name}\n"

        if common_name and common_name != 'None':
            text += f"*Общепринятое название:* {common_name}\n"

        if family:
            text += f"*Семейство:* {family}\n"

        if genus:
            text += f"*Род:* {genus}\n"

        # Сложность ухода
        text += f"*Сложность ухода:* {get_care_difficulty(plant)}\n\n"

        # Основная информация
        if plant.get('observations'):
            observations = plant['observations']
            # Обрезаем слишком длинное описание
            if len(observations) > 300:
                observations = observations[:300] + "..."
            text += f"📊 *Описание:* {observations}\n\n"

        # Получаем ВСЮ доступную информацию о уходе
        care_info = get_available_care_data(plant)

        if care_info:
            text += "💡 *Рекомендации по уходу*\n\n"
            text += "\n\n".join(care_info)
        else:
            text += "ℹ️ *Информация об уходе:*\n"
            text += "Детальная информация об уходе отсутствует в базе данных.\n"
            text += "Рекомендуется использовать общие рекомендации для данного семейства растений.\n\n"

        # Клавиатура для дополнительных действий
        keyboard = [["🔍 Найти другое растение", "⬅️ Назад"]]

        if image_url:
            try:
                # Если текст слишком длинный, разбиваем на части
                if len(text) > 1000:
                    # Отправляем фото с кратким описанием
                    short_text = text[:800] + "\n\n... (продолжение в следующем сообщении)"
                    await update.message.reply_photo(
                        photo=image_url,
                        caption=short_text,
                        parse_mode="Markdown",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
                    # Отправляем оставшийся текст
                    if len(text) > 800:
                        remaining_text = text[800:]
                        await update.message.reply_text(
                            remaining_text,
                            parse_mode="Markdown"
                        )
                else:
                    await update.message.reply_photo(
                        photo=image_url,
                        caption=text,
                        parse_mode="Markdown",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                await update.message.reply_text(
                    text + f"\n\n*Изображение:* {image_url}",
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
        else:
            # Если текст слишком длинный, разбиваем на части
            if len(text) > 4000:
                parts = [text[i:i + 4000] for i in range(0, len(text), 4000)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        # Последняя часть с клавиатурой
                        await update.message.reply_text(
                            part,
                            parse_mode="Markdown",
                            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        )
                    else:
                        await update.message.reply_text(part, parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )

        return AFTER_SEARCH

    except requests.exceptions.Timeout:
        await searching_msg.edit_text(
            "⏰ *Таймаут запроса*\n\n"
            "Поиск занял слишком много времени. Попробуйте позже.",
            parse_mode="Markdown"
        )
        return ASK_NAME
    except requests.exceptions.ConnectionError:
        await searching_msg.edit_text(
            "🌐 *Ошибка соединения*\n\n"
            "Проверьте подключение к интернету и попробуйте снова.",
            parse_mode="Markdown"
        )
        return ASK_NAME
    except Exception as e:
        await searching_msg.edit_text(
            f"❌ *Ошибка поиска*\n\n"
            f"Техническая информация: {str(e)}",
            parse_mode="Markdown"
        )
        return ASK_NAME


async def handle_after_search_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий после поиска"""
    text = update.message.text

    if text == "🔍 Найти другое растение":
        await update.message.reply_text(
            "🔍 *Умный поиск растений*\n\n"
            "Введите название растения на русском или латыни:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True),
        )
        return ASK_NAME
    elif text == "⬅️ Назад":
        return await back_to_main(update, context)

    return AFTER_SEARCH


def build_trefle_conversation():
    """Диалог для кнопки 🌍 Поиск растений"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🌍 Поиск растений$"), trefle_start)],
        states={
            ASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trefle_search),
            ],
            AFTER_SEARCH: [
                MessageHandler(filters.Regex("^(🔍 Найти другое растение|⬅️ Назад)$"), handle_after_search_actions),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^⬅️ Назад$"), back_to_main),
        ],
        allow_reentry=True,
    )