"""
Словари для перевода болезней растений и рекомендаций по лечению
Будем пополнять по мере обнаружения новых терминов от API
"""

# Основной словарь перевода болезней
DISEASE_TRANSLATIONS = {
    'senescence': 'естественное старение листьев',
    'powdery mildew': 'мучнистая роса',
    'leaf spot': 'пятнистость листьев',
    'rust': 'ржавчина',
    'blight': 'фитофтороз',
    'wilting': 'увядание',
    'chlorosis': 'хлороз',
    'necrosis': 'некроз',
    'mosaic virus': 'мозаичный вирус',
    'root rot': 'корневая гниль',
    'aphids': 'тля',
    'spider mites': 'паутинный клещ',
    'scale insects': 'щитовка',
    'mealybugs': 'мучнистый червец',
    'overwatering': 'перелив',
    'underwatering': 'недостаточный полив',
    'nutrient deficiency': 'недостаток питательных веществ',
    'sunburn': 'солнечный ожог',
    'frost damage': 'повреждение морозом',
    'drought stress': 'засуха',
    'healthy': 'здоровое растение',
    'leaf curl': 'скручивание листьев',
    'yellowing': 'пожелтение листьев',
    'brown spots': 'коричневые пятна',
    'whiteflies': 'белокрылка',
    'thrips': 'трипсы',
    'dead plant': 'умершее растение'
}

# Детальные описания болезней
DISEASE_DESCRIPTIONS = {
    'senescence': 'Естественный процесс старения листьев. Нижние листья желтеют и отмирают - это нормально для роста растения.',
    'powdery mildew': 'Белый мучнистый налёт на листьях, вызванный грибком. Часто возникает при высокой влажности и плохой вентиляции.',
    'leaf spot': 'Коричневые или чёрные пятна на листьях. Может быть вызвано грибками, бактериями или неправильным уходом.',
    'rust': 'Оранжевые или рыжие пятна-пустулы на нижней стороне листьев. Грибковое заболевание.',
    'overwatering': 'Избыточный полив приводит к загниванию корней. Листья желтеют, становятся вялыми.',
    'yellowing': 'Пожелтение листьев может быть вызвано различными причинами: недостаток света, питательных веществ или проблемы с поливом.'
}

# Рекомендации по лечению
TREATMENT_RECOMMENDATIONS = {
    'senescence': '• Удаляйте старые пожелтевшие листья\n• Продолжайте обычный уход\n• Это естественный процесс роста',
    'powdery mildew': '• Удалите поражённые листья\n• Обработайте фунгицидом\n• Улучшите вентиляцию\n• Сократите полив',
    'leaf spot': '• Удалите больные листья\n• Обработайте медьсодержащим препаратом\n• Избегайте попадания воды на листья',
    'overwatering': '• Дайте почве просохнуть\n• Убедитесь в наличии дренажа\n• Отрегулируйте режим полива',
    'yellowing': '• Проверьте влажность почвы\n• Убедитесь в достаточном освещении\n• Внесите комплексное удобрение'
}

# Словарь для растений
PLANT_TRANSLATIONS = {
    'oryza sativa': 'Рис посевной',
    'ficus benjamina': 'Фикус Бенджамина',
    'monstera deliciosa': 'Монстера деликатесная',
    'phalaenopsis': 'Фаленопсис (Орхидея)',
    'rosa': 'Роза',
    'chlorophytum comosum': 'Хлорофитум',
    'sansevieria': 'Сансевиерия (Щучий хвост)',
    'epipremnum aureum': 'Эпипремнум (Сциндапсус)',
    'crassula ovata': 'Крассула (Денежное дерево)',
    'aloe vera': 'Алоэ вера'
}
WATERING_GUIDE = {
    'фикус': 'Умеренный полив, когда верхний слой почвы подсохнет',
    'монстера': 'Обильный полив, но давайте почве просыхать',
    'орхидея': 'Умеренный полив методом погружения',
    'кактус': 'Редкий полив, зимой почти не поливать',
    'суккулент': 'Умеренный полив, давайте почве полностью просохнуть'
}

def add_new_disease(english_name: str, russian_name: str, description: str = "", treatment: str = ""):
    """Функция для добавления новых болезней в словарь"""
    DISEASE_TRANSLATIONS[english_name.lower()] = russian_name
    if description:
        DISEASE_DESCRIPTIONS[english_name.lower()] = description
    if treatment:
        TREATMENT_RECOMMENDATIONS[english_name.lower()] = treatment
    print(f"✅ Добавлена болезнь: {english_name} -> {russian_name}")

def add_new_plant(latin_name: str, russian_name: str):
    """Функция для добавления новых растений в словарь"""
    PLANT_TRANSLATIONS[latin_name.lower()] = russian_name
    print(f"✅ Добавлено растение: {latin_name} -> {russian_name}")

def get_unknown_diseases(disease_names: list) -> list:
    """Получить список болезней, которых нет в словаре"""
    return [disease for disease in disease_names if disease.lower() not in DISEASE_TRANSLATIONS]