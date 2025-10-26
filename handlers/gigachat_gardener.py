import os
import requests
import uuid
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

# Конфигурация GigaChat
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")

# Состояния диалога
CHATTING_WITH_GARDENER = range(1)

# Кэш для токенов
access_token_cache = None
token_expires_at = 0


async def get_gigachat_token():
    """Получение токена доступа GigaChat"""
    global access_token_cache, token_expires_at

    # Если токен еще действителен (30 минут), возвращаем его
    current_time = int(time.time())
    if access_token_cache and token_expires_at > current_time:
        return access_token_cache

    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {GIGACHAT_CREDENTIALS}'
    }

    payload = {
        'scope': 'GIGACHAT_API_PERS'
    }

    try:
        # Отключаем проверку SSL для GigaChat API
        response = requests.post(url, headers=headers, data=payload, timeout=10, verify=False)
        response.raise_for_status()

        data = response.json()
        access_token_cache = data['access_token']
        token_expires_at = data['expires_at'] // 1000  # Конвертируем из мс в секунды

        print(f"✅ Токен GigaChat получен, действителен до: {time.ctime(token_expires_at)}")
        return access_token_cache

    except Exception as e:
        print(f"❌ Ошибка получения токена GigaChat: {e}")
        return None


async def get_gigachat_response(question: str) -> str:
    """Получение ответа от GigaChat"""
    token = await get_gigachat_token()
    if not token:
        return "❌ *Ошибка подключения к AI-консультанту*\n\nПопробуйте позже или используйте другие функции бота."

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    # Промпт для садовода
    system_prompt = """Ты опытный садовод-консультант с 20-летним стажем. Твоя специализация - комнатные растения, садоводство и уход за растениями.

Отвечай профессионально, но доступно для новичков. Используй эмодзи для наглядности. Разбивай ответ на логические блоки.

Твои ответы должны быть:
- Практичными и полезными
- С конкретными рекомендациями
- С учетом российских условий
- Доброжелательными и поддерживающими

Если не знаешь точного ответа, дай общие рекомендации по диагностике проблемы."""

    data = {
        "model": "GigaChat",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        # Отключаем проверку SSL для GigaChat API
        response = requests.post(url, headers=headers, json=data, timeout=30, verify=False)
        response.raise_for_status()

        result = response.json()
        answer = result['choices'][0]['message']['content']

        return answer

    except requests.exceptions.Timeout:
        return "⏰ *Время ожидания истекло*\n\nAI-консультант не успел обработать запрос. Попробуйте задать вопрос короче или повторите позже."

    except requests.exceptions.RequestException as e:
        return f"❌ *Ошибка связи с AI-консультантом*\n\nТехническая информация: {str(e)}"

    except Exception as e:
        return f"❌ *Произошла непредвиденная ошибка*\n\nПопробуйте переформулировать вопрос или обратиться позже."


async def start_gardener_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало чата с AI-садоводом"""
    if not GIGACHAT_CREDENTIALS:
        await update.message.reply_text(
            "❌ *AI-консультант временно недоступен*\n\n"
            "Ведутся технические работы. Используйте другие функции бота:\n"
            "• 🔍 Диагностика по фото\n"
            "• 📚 Рекомендации по уходу\n"
            "• 🌍 Поиск в базе растений",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    # Проверяем доступность GigaChat
    token = await get_gigachat_token()
    if not token:
        await update.message.reply_text(
            "❌ *AI-консультант временно недоступен*\n\n"
            "Не удалось подключиться к сервису. Попробуйте позже.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👨‍🌾 *Добро пожаловать в чат с AI-садоводом!*\n\n"
        "Я - ваш виртуальный консультант по растениям. Задавайте любые вопросы:\n\n"
        "*Примеры вопросов:*\n"
        "• Почему желтеют листья у моего фикуса?\n"
        "• Как правильно пересадить орхидею?\n"
        "• Какие удобрения выбрать для роз?\n"
        "• Что делать если на листьях появились пятна?\n"
        "• Как ухаживать за суккулентами зимой?\n\n"
        "Задайте ваш вопрос о растениях 👇",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Выйти из чата"]], resize_keyboard=True)
    )
    return CHATTING_WITH_GARDENER


async def handle_gardener_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка вопросов к AI-садоводу"""
    user_question = update.message.text

    if user_question == "⬅️ Выйти из чата":
        return await end_gardener_chat(update, context)

    # Показываем, что бот "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Получаем ответ от GigaChat
    response = await get_gigachat_response(user_question)

    # Отправляем ответ пользователю
    await update.message.reply_text(
        response,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Выйти из чата"]], resize_keyboard=True)
    )

    return CHATTING_WITH_GARDENER


async def end_gardener_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение чата"""
    from handlers.start import MAIN_KEYBOARD

    await update.message.reply_text(
        "👨‍🌾 *Был рад помочь!*\n\n"
        "Возвращайтесь с любыми вопросами о ваших растениях! 🌿\n"
        "Также можете использовать другие функции бота:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
    )
    return ConversationHandler.END


def build_gardener_conversation():
    """Диалог чата с AI-садоводом"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^👨‍🌾 Чат с агрономом$"), start_gardener_chat)],
        states={
            CHATTING_WITH_GARDENER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gardener_question)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^(⬅️ Выйти из чата)$"), end_gardener_chat)],
        allow_reentry=True,
        per_message=False
    )