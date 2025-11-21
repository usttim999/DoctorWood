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
    return light_map.get(light_level, "Не указано")


def get_toxicity_description(toxicity):
    """Описание токсичности"""
    toxicity_map = {
        'none': "✅ Безопасно",
        'low': "⚠️ Низкая токсичность",
        'medium': "⚠️ Средняя токсичность",
        'high': "☠️ Высокая токсичность"
    }
    return toxicity_map.get(toxicity, "Не указано")


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


def get_seasonal_advice(plant_data):
    """Сезонные рекомендации на основе данных"""
    growth = plant_data.get('growth', {})
    bloom_months = growth.get('bloom_months', [])
    growth_months = growth.get('growth_months', [])
    fruit_months = growth.get('fruit_months', [])

    advice = "*🌱 Сезонные рекомендации:*\n"

    if bloom_months:
        translated_months = [MONTHS_TRANSLATION.get(month.lower(), month) for month in bloom_months]
        advice += f"• Цветение: {', '.join(translated_months)}\n"

    if growth_months:
        translated_months = [MONTHS_TRANSLATION.get(month.lower(), month) for month in growth_months]
        advice += f"• Активный рост: {', '.join(translated_months)}\n"

    if fruit_months:
        translated_months = [MONTHS_TRANSLATION.get(month.lower(), month) for month in fruit_months]
        advice += f"• Плодоношение: {', '.join(translated_months)}\n"

    return advice


def get_care_recommendations(plant_data):
    """Рекомендации по уходу на основе данных Trefle"""
    growth = plant_data.get('growth', {})
    specs = plant_data.get('specifications', {})

    recommendations = "*💡 Рекомендации по уходу:*\n"

    # Полив на основе влажности почвы
    soil_humidity = growth.get('soil_humidity')
    if soil_humidity is not None:
        if soil_humidity >= 7:
            recommendations += "• 💧 Обильный полив (почва всегда влажная)\n"
        elif soil_humidity >= 4:
            recommendations += "• 💧 Умеренный полив (давайте почве подсыхать)\n"
        else:
            recommendations += "• 💧 Редкий полив (устойчиво к засухе)\n"

    # Температура
    min_temp = growth.get('minimum_temperature', {}).get('deg_c')
    max_temp = growth.get('maximum_temperature', {}).get('deg_c')
    if min_temp and max_temp:
        recommendations += f"• 🌡️ Температура: {min_temp}°C - {max_temp}°C\n"

    # Освещение
    light_level = growth.get('light')
    if light_level is not None:
        recommendations += f"• ☀️ Освещение: {get_light_description(light_level)}\n"

    # pH почвы
    ph_min = growth.get('ph_minimum')
    ph_max = growth.get('ph_maximum')
    if ph_min and ph_max:
        recommendations += f"• 🧪 pH почвы: {ph_min} - {ph_max}\n"

    return recommendations


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

        # 🔍 ОТЛАДОЧНАЯ ИНФОРМАЦИЯ - выведем что пришло от Trefle
        logger.info("=== ДАННЫЕ ОТ TREFLE ===")
        logger.info(f"Common name: {plant.get('common_name')}")
        logger.info(f"Scientific name: {plant.get('scientific_name')}")
        logger.info(f"Family: {plant.get('family')}")
        logger.info(f"Observations: {plant.get('observations', '')[:100]}...")

        growth_data = plant.get('growth', {})
        logger.info(f"Growth data exists: {bool(growth_data)}")
        if growth_data:
            logger.info(f"Light: {growth_data.get('light')}")
            logger.info(f"PH min/max: {growth_data.get('ph_minimum')}-{growth_data.get('ph_maximum')}")
            logger.info(f"Bloom months: {growth_data.get('bloom_months')}")
            logger.info(f"Soil humidity: {growth_data.get('soil_humidity')}")
            logger.info(f"Growth months: {growth_data.get('growth_months')}")
            logger.info(f"Fruit months: {growth_data.get('fruit_months')}")
            logger.info(f"Min temp: {growth_data.get('minimum_temperature')}")
            logger.info(f"Max temp: {growth_data.get('maximum_temperature')}")

        specifications = plant.get('specifications', {})
        logger.info(f"Specifications exists: {bool(specifications)}")
        if specifications:
            logger.info(f"Toxicity: {specifications.get('toxicity')}")
            logger.info(f"Average height: {specifications.get('average_height')}")
            logger.info(f"Growth form: {specifications.get('growth_form')}")
            logger.info(f"Growth habit: {specifications.get('growth_habit')}")
        logger.info("========================")

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

                # Проверяем детальные данные
                growth_detail = plant.get('growth', {})
                if growth_detail:
                    logger.info(f"🔍 ОТЛАДКА: Детальный light: {growth_detail.get('light')}")
                    logger.info(f"🔍 ОТЛАДКА: Детальный bloom months: {growth_detail.get('bloom_months')}")
                    logger.info(f"🔍 ОТЛАДКА: Детальный soil humidity: {growth_detail.get('soil_humidity')}")
            else:
                logger.error(f"❌ ОТЛАДКА: Ошибка получения детальной информации: {detail_response.status_code}")

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
            text += f"📊 *Описание:* {plant['observations'][:200]}...\n\n"

        # Токсичность
        toxicity = plant.get('specifications', {}).get('toxicity')
        if toxicity:
            text += f"*Токсичность:* {get_toxicity_description(toxicity)}\n"

        # Съедобность
        if plant.get('edible'):
            text += "🍽️ *Съедобность:* Съедобное\n"
        else:
            text += "⚠️ *Съедобность:* Не съедобное\n"

        # Добавляем рекомендации по уходу
        care_recs = get_care_recommendations(plant)
        logger.info(f"🔍 ОТЛАДКА: Рекомендации по уходу: {care_recs}")
        text += "\n" + care_recs

        # Добавляем сезонные рекомендации
        seasonal_advice = get_seasonal_advice(plant)
        logger.info(f"🔍 ОТЛАДКА: Сезонные рекомендации: {seasonal_advice}")
        if "Сезонные рекомендации" in seasonal_advice:
            text += "\n" + seasonal_advice

        # Клавиатура для дополнительных действий
        keyboard = [["🔍 Найти другое растение", "⬅️ Назад"]]

        if image_url:
            try:
                await update.message.reply_photo(
                    photo=image_url,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
            except:
                await update.message.reply_text(
                    text + f"\n\n*Изображение:* {image_url}",
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
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
