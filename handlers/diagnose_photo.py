import os
import requests
import base64
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv
from handlers.disease_dictionary import (
    DISEASE_TRANSLATIONS,
    DISEASE_DESCRIPTIONS,
    TREATMENT_RECOMMENDATIONS,
    PLANT_TRANSLATIONS,
    get_unknown_diseases,
    add_new_disease
)

load_dotenv()

API_KEY = os.getenv("PLANT_API_KEY")


async def diagnose_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("📷 Отправьте фото растения для диагностики")
        return

    # Берём самое большое фото
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = "temp.jpg"
    await file.download_to_drive(file_path)

    try:
        # Читаем фото и кодируем в base64
        with open(file_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")

        url = "https://api.plant.id/v3/identification"
        headers = {
            "Api-Key": API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "images": [img_base64],
            "health": "all",
            "classification_level": "species"
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if not response.ok:
            await update.message.reply_text(
                f"⚠️ Ошибка API ({response.status_code}):\n{response.text}"
            )
            return

        result = response.json()
        text = ""

        # Проверяем, есть ли вообще растение
        is_plant = result.get("result", {}).get("is_plant", {}).get("binary")
        if is_plant is False:
            await update.message.reply_text("❌ На фото не распознано растение")
            return

        # Определение вида
        suggestions = result.get("result", {}).get("classification", {}).get("suggestions", [])
        if suggestions:
            best = suggestions[0]
            latin_name = best.get("name", "Неизвестно")
            # Пытаемся перевести название
            plant_name = PLANT_TRANSLATIONS.get(latin_name.lower(), latin_name)
            prob = round(best.get("probability", 0) * 100, 1)
            common = best.get("details", {}).get("common_names", [])
            if common:
                text += f"🌱 *Похоже, это:* {plant_name} ({', '.join(common)}) - {prob}%\n\n"
            else:
                text += f"🌱 *Похоже, это:* {plant_name} - {prob}%\n\n"
        else:
            text += "❓ Вид растения определить не удалось\n\n"

        # Диагностика здоровья
        disease_suggestions = result.get("result", {}).get("disease", {}).get("suggestions", [])
        if disease_suggestions:
            # Собираем все найденные болезни для логирования
            all_disease_names = [d.get("name", "") for d in disease_suggestions if d.get("name")]
            unknown_diseases = get_unknown_diseases(all_disease_names)

            if unknown_diseases:
                print(f"🚨 НЕИЗВЕСТНЫЕ БОЛЕЗНИ ДЛЯ СЛОВАРЯ: {unknown_diseases}")

            disease = disease_suggestions[0]
            d_name = disease.get("name", "Неизвестная болезнь")
            d_prob = round(disease.get("probability", 0) * 100, 1)

            # Перевод названия болезни
            translated_name = DISEASE_TRANSLATIONS.get(d_name.lower(), d_name)

            # Получение описания и лечения
            description = DISEASE_DESCRIPTIONS.get(d_name.lower(),
                                                   disease.get("details", {}).get("description", ""))
            treatment = TREATMENT_RECOMMENDATIONS.get(d_name.lower(),
                                                      disease.get("details", {}).get("treatment", {}))

            text += f"⚠️ *Обнаружена проблема:* {translated_name} ({d_prob}%)\n\n"

            if description:
                text += f"📋 *Описание:* {description}\n\n"

            if treatment:
                if isinstance(treatment, str):
                    text += f"💊 *Рекомендации:*\n{treatment}\n"
                else:
                    if treatment.get("biological"):
                        text += "🧪 *Биологическое лечение:* " + ", ".join(treatment["biological"]) + "\n"
                    if treatment.get("chemical"):
                        text += "💊 *Химическое лечение:* " + ", ".join(treatment["chemical"]) + "\n"
            else:
                text += "💡 *Общие рекомендации:*\n• Изолируйте растение\n• Удалите поражённые части\n• Отрегулируйте полив и освещение\n"

        else:
            text += "✅ *Растение выглядит здоровым!*\n\n💡 *Совет:* Продолжайте регулярный уход и осмотр"

        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка диагностики: {str(e)}")