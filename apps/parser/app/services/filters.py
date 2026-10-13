"""
Централизованный фильтр исключения нерелевантных заказов и категорий для LeadHunter & бирж фриланса.

Исключаемые направления (по запросу):
1. Менеджер (найм менеджеров, продажи, маркетплейсы, аккаунты, вакансии)
2. Монтаж коротких видео роликов (Reels, Shorts, TikTok, нарезка)
3. Монтаж (видеомонтаж, аудиомонтаж, строительный монтаж, инженерный монтаж)
4. Отопление (котлы, радиаторы, отопительные системы, теплый пол, котельные)
5. SMM (ведение соцсетей, продвижение аккаунтов, сммщики, таргетинг инстаграм)
6. Создание аватара
7. Создание ИИ аватара (нейроаватары, цифровые аватары, HeyGen, D-ID, генерация)
8. Привлечение клиентов (лидогенерация, спам, холодный обзвон, инвайтинг)
9. Написать сценарии (сценаристы, сценарии для видео/Reels/Shorts/роликов)
"""
import os
import re
import logging
from typing import Tuple, List, Set, Optional
from sqlalchemy import select

logger = logging.getLogger("order_filters")

# Стоп-фразы и стоп-слова в названиях категорий/рубрик бирж
STOP_CATEGORIES_KEYWORDS = [
    # 1. Менеджер
    "менеджер", "менеджмент", "менеджеры", "управление проектами", "project management",
    "обзвоны и продажи", "персональный помощник",
    # 2 & 3. Монтаж / Монтаж коротких видео роликов
    "монтаж", "видеомонтаж", "монтаж видео", "монтаж роликов", "видеоролики",
    "видео и аудио", "видео/аудио", "аудио/видео", "обработка видео", "видеомонтажер",
    # 4. Отопление
    "отопление", "сантехника", "отопление и вентиляция", "инженерные системы",
    # 5. SMM
    "smm", "смм", "социальные сети", "продвижение в соцсетях", "smm-маркетинг", "соцсети",
    "продвижение маркетплейс",
    # 6 & 7. Создание аватара / Создание ИИ аватара
    "создание аватара", "создание ии аватара", "нейроаватары", "аватары",
    # 8. Привлечение клиентов
    "привлечение клиентов", "лидогенерация", "холодные звонки", "продажи и лидогенерация",
    # 9. Написать сценарии
    "сценарии", "сценаристы", "написание сценариев",
    # 10. Обучение / Репетиторство (нерелевантно)
    "репетитор", "обучение и консультации", "дипломные работы"
]

# Точные скомпилированные регулярные выражения для заголовков и описаний
STOP_PATTERNS = [
    # 1. Менеджер (найм, вакансии, управление, ведение переписки)
    (re.compile(r'\bменеджер(?:а|у|ом|е|ы|ов)?\b', re.IGNORECASE), "Менеджер"),
    (re.compile(r'\b(?:project|sales|account|community|traffic|lead)\s+manager\b', re.IGNORECASE), "Менеджер (Manager)"),
    (re.compile(r'\bменеджмент\b', re.IGNORECASE), "Менеджмент"),
    (re.compile(r'\b(?:вест[иь]|веден\w*|диалог\w*|переписк\w*|коммуникаци\w*|общени\w*)\s+(?:.*?\s+)?(?:партн[её]р\w*|клиент\w*|пользовател\w*|собеседник\w*)\b', re.IGNORECASE), "Менеджер (коммуникация/переписка)"),

    # 2 & 3. Монтаж / Монтаж коротких видео роликов
    (re.compile(r'\bмонтаж\w*\b', re.IGNORECASE), "Монтаж"),
    (re.compile(r'\bвидеомонтаж\w*\b', re.IGNORECASE), "Видеомонтаж"),
    (re.compile(r'\bмонтажер\w*\b', re.IGNORECASE), "Монтажер"),
    (re.compile(r'\bсмонтировать\b', re.IGNORECASE), "Монтаж"),
    (re.compile(r'\bкоротк(?:их|ие|ого|им)\s+(?:видео|ролик\w*)\b', re.IGNORECASE), "Монтаж коротких видео роликов"),
    (re.compile(r'\b(?:reels|shorts|рилс\w*|шортс\w*|тиктоки?|tiktok)\b', re.IGNORECASE), "Монтаж роликов (Reels/Shorts)"),
    (re.compile(r'\bнарезк(?:а|и|у|ой)\s+(?:видео|стрим\w*|ролик\w*)\b', re.IGNORECASE), "Монтаж (нарезка видео)"),

    # 4. Отопление
    (re.compile(r'\bотоплен(?:ие|ия|ию|ем|ии)\b', re.IGNORECASE), "Отопление"),
    (re.compile(r'\bкот(?:ел|ла|лу|лом|лы|лов)\b', re.IGNORECASE), "Отопление (котел)"),
    (re.compile(r'\bкотельн(?:ая|ой|ую|ые)\b', re.IGNORECASE), "Отопление (котельная)"),
    (re.compile(r'\bрадиатор(?:ы|ов|а)?\b', re.IGNORECASE), "Отопление (радиаторы)"),
    (re.compile(r'\bтепл(?:ый|ого|ые|ых)\s+пол\w*\b', re.IGNORECASE), "Отопление (теплый пол)"),
    (re.compile(r'\bтеплоснабжен\w*\b', re.IGNORECASE), "Отопление (теплоснабжение)"),

    # 5. SMM & Продвижение маркетплейсов
    (re.compile(r'\b(?:smm|смм)\b', re.IGNORECASE), "SMM"),
    (re.compile(r'\bведение\s+(?:соцсет\w*|социальных\s+сетей|инстаграм\w*|instagram|аккаунт\w*|паблик\w*|сообществ\w*)\b', re.IGNORECASE), "SMM (ведение соцсетей)"),
    (re.compile(r'\bпродвижени(?:е|я)\s+в\s+(?:соцсет\w*|социальных\s+сетях|инстаграм\w*|тг|телеграм\w*)\b', re.IGNORECASE), "SMM (продвижение)"),
    (re.compile(r'\bпродвижени\w*\s+(?:.*?\s+)?(?:маркетплейс\w*|wb|ozon|вайлдберриз|wildberries)\b', re.IGNORECASE), "SMM (продвижение маркетплейса)"),
    (re.compile(r'\b(?:маркетплейс\w*|wb|ozon|вайлдберриз|wildberries)\b.*?\bпродвижени\w*\b', re.IGNORECASE), "SMM (продвижение маркетплейса)"),
    (re.compile(r'\bсммщик\w*\b', re.IGNORECASE), "SMM (сммщик)"),

    # 6 & 7. Создание аватара / Создание ИИ аватара
    (re.compile(r'(?:создани(?:е|я)|создать|генераци(?:я|и)|сгенерировать)\s+(?:ии[-\s]*)?аватар\w*', re.IGNORECASE), "Создание (ИИ) аватара"),
    (re.compile(r'\b(?:ии|ai)[-\s]*аватар\w*\b', re.IGNORECASE), "Создание ИИ аватара"),
    (re.compile(r'\bнейроаватар\w*\b', re.IGNORECASE), "Создание ИИ аватара (нейроаватар)"),
    (re.compile(r'\bцифров(?:ой|ого|ые)\s+аватар\w*\b', re.IGNORECASE), "Создание аватара"),
    (re.compile(r'\bговорящ(?:ий|его|их)\s+аватар\w*\b', re.IGNORECASE), "Создание аватара (говорящий аватар)"),
    (re.compile(r'\b(?:heygen|synthesia|d-id)\b', re.IGNORECASE), "Создание ИИ аватара (сервисы)"),

    # 8. Привлечение клиентов & Лидогенерация
    (re.compile(r'(?:привлечени(?:е|я)|привлечь|поиск|найти|поток)\s+клиент\w*', re.IGNORECASE), "Привлечение клиентов"),
    (re.compile(r'\bлидогенераци\w*\b', re.IGNORECASE), "Привлечение клиентов (лидогенерация)"),
    (re.compile(r'\bхолодн(?:ые|ый|ого|ым)\s+(?:звонк\w*|обзвон\w*)\b', re.IGNORECASE), "Привлечение клиентов (холодные звонки)"),
    (re.compile(r'\b(?:первичн\w*|холодн\w*)\s+коммуникаци\w*', re.IGNORECASE), "Привлечение клиентов (коммуникация)"),
    (re.compile(r'\b(?:инвайтинг|рассылка\s+в\s+лс|спам[-\s]*рассылк\w*)\b', re.IGNORECASE), "Привлечение клиентов (спам/инвайтинг)"),

    # 9. Написать сценарии
    (re.compile(r'(?:написа\w*|состави\w*|разработ\w*)\s+(?:\w+\s+)?сценари\w*', re.IGNORECASE), "Написать сценарии"),
    (re.compile(r'\bсценари(?:й|и|ев|я|ям|ями|ем)\b.*?\b(?:reels|shorts|рилс\w*|шортс\w*|видео|ролик\w*|тикток\w*|фильм\w*|ютуб\w*|youtube|реклам\w*|квест\w*|подкаст\w*)\b', re.IGNORECASE), "Написать сценарии"),
    (re.compile(r'\b(?:reels|shorts|рилс\w*|шортс\w*|видео|ролик\w*|тикток\w*|фильм\w*|ютуб\w*|youtube|реклам\w*)\b.*?\bсценари(?:й|и|ев|я|ям|ями|ем)\b', re.IGNORECASE), "Написать сценарии"),
    (re.compile(r'\bсценарист\w*\b', re.IGNORECASE), "Сценарист / Написать сценарии"),

    # 10. Учеба / Репетиторство (нерелевантно)
    (re.compile(r'\b(?:репетитор\w*|диплом\w*|курсов\w*|контрольн\w*|домашк\w*|реферат\w*)\b', re.IGNORECASE), "Репетитор/Учеба"),
]

# Дополнительные стоп-слова из переменных окружения
extra_stops = os.getenv("ADDITIONAL_STOP_WORDS", "")
if extra_stops:
    for word in extra_stops.split(","):
        w = word.strip()
        if w:
            STOP_CATEGORIES_KEYWORDS.append(w.lower())
            STOP_PATTERNS.append((re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE), f"Стоп-слово: {w}"))


# ==============================================================================
# ПРОФИЛЬ КОМПЕТЕНЦИЙ CASTLEWEB STUDIO (castleweb.ru)
# ==============================================================================
CASTLEWEB_RELEVANT_CATEGORIES = [
    "разработка", "веб-программирование", "сайты «под ключ»", "сайты под ключ",
    "вёрстка", "верстка", "дизайн сайтов", "интерфейсы", "скрипты и боты",
    "мобильные приложения", "базы данных", "веб-дизайн", "разработка сайтов",
    "программирование", "тендеры", "it /", "разработка и it"
]

CASTLEWEB_RELEVANT_PATTERNS = [
    # 1. Веб-разработка & сайты
    re.compile(r'\b(?:сайт\w*|лендинг\w*|веб[-\s]*сервис\w*|веб[-\s]*платформ\w*|веб[-\s]*приложени\w*|портал\w*|интернет[-\s]*магазин\w*|landing\w*)\b', re.IGNORECASE),
    re.compile(r'\b(?:верстк\w*|сверстать\w*|html\w*|css\w*|frontend\w*|фронтенд\w*)\b', re.IGNORECASE),
    re.compile(r'\b(?:редизайн\w*|доработк\w*\s+(?:по\s+)?сайт\w*|перенос\s+сайт\w*|правк\w*\s+на\s+сайт\w*)\b', re.IGNORECASE),
    re.compile(r'\b(?:wordpress\w*|вордпресс\w*|tilda\w*|тильд\w*|битрикс\w*|bitrix\w*|opencart\w*|webflow\w*)\b', re.IGNORECASE),
    re.compile(r'\b(?:react\w*|vue\w*|next(?:\.js)?\b|nuxt(?:\.js)?\b|tailwind\w*|javascript\w*|typescript\w*)\b', re.IGNORECASE),
    
    # 2. Бэкенд, базы данных, API
    re.compile(r'\b(?:бэкенд\w*|backend\w*|api\b|fastapi\w*|django\w*|flask\w*|laravel\w*|node(?:\.js)?\b|php\b|python\w*|пайтон\w*|питон\w*)\b', re.IGNORECASE),
    re.compile(r'\b(?:баз[аеу]\s+данных|базами\s+данных|sql\w*|postgresql\w*|mysql\w*|sqlite\w*|mongodb\w*)\b', re.IGNORECASE),
    re.compile(r'\b(?:интеграци\w*\s+(?:api|сервис\w*|crm|платформ\w*)|микросервис\w*|личн\w*\s+кабинет\w*|crm\b)\b', re.IGNORECASE),
    
    # 3. Telegram боты & mini apps
    re.compile(r'\b(?:telegram|телеграм\w*|тг)\s+(?:бот\w*|mini\s*app\w*|мини[-\s]*апп\w*|web\s*app\w*|канал\w*|чат[-\s]*бот\w*)\b', re.IGNORECASE),
    re.compile(r'\b(?:бот\w*|bot\w*|чат[-\s]*бот\w*)\b', re.IGNORECASE),
    
    # 4. Парсеры & сбор данных
    re.compile(r'\b(?:парсер\w*|парсинг\w*|скрап\w*|сбор\w*\s+данных|выгрузк\w*\s+данных|скрипт\w*)\b', re.IGNORECASE),
    
    # 5. Дизайн & UI/UX
    re.compile(r'\b(?:дизайн\w*|веб[-\s]*дизайн\w*|ui[/_\s]*ux\w*|figma\w*|фигм\w*|макет\w*)\b', re.IGNORECASE),
    
    # 6. Софт & мобильные/десктоп приложения
    re.compile(r'\b(?:приложени\w*|app\w*|apk|арк|android\w*|ios\b|flutter\w*|desktop\w*|десктоп\w*|программ\w*|софт\w*)\b', re.IGNORECASE),
    
    # 7. Инфраструктура & хостинг
    re.compile(r'\b(?:хостинг\w*|домен\w*|ssl\b|nginx\b|docker\b|деплой\w*|сервер\w*)\b', re.IGNORECASE),
]


def is_relevant_to_castleweb(title: str, description: str = "", category_name: str = "") -> bool:
    """
    Проверяет, относится ли проект к компетенциям веб-студии CastleWeb:
    - Веб-разработка (сайты, лендинги, сервисы, CMS, frontend, backend)
    - Боты (Telegram боты, Mini Apps, чат-боты)
    - Парсеры (сбор данных, скрапинг, автоматизация)
    - Софт (приложения, скрипты, интеграции)
    - UI/UX Дизайн (Figma, прототипы, макеты)
    """
    cat_lower = (category_name or "").lower().strip()
    if cat_lower:
        for rel_cat in CASTLEWEB_RELEVANT_CATEGORIES:
            if rel_cat in cat_lower:
                return True

    full_text = f"{title or ''} {description or ''}"
    for pattern in CASTLEWEB_RELEVANT_PATTERNS:
        if pattern.search(full_text):
            return True

    return False


def is_order_excluded(title: str, description: str = "", category_name: str = "") -> Tuple[bool, str]:
    """
    Проверяет заказ на соответствие исключенным категориям или ключевым словам:
    1. Исключает стоп-категории и стоп-слова (менеджеры, SMM, видеомонтаж, отопление, репетиторы и др.)
    2. Требует обязательное соответствие компетенциям студии CastleWeb (веб, боты, софт, парсинг, дизайн).
    Возвращает (True, причина), если заказ нужно отфильтровать, иначе (False, "").
    """
    cat_lower = (category_name or "").lower().strip()
    title_raw = title or ""
    desc_raw = description or ""
    full_text = f"{title_raw} {desc_raw}"

    # 1. Проверка категории биржи на стоп-слова
    if cat_lower:
        for stop_cat in STOP_CATEGORIES_KEYWORDS:
            if stop_cat in cat_lower:
                return True, f"Стоп-категория: {category_name} ({stop_cat})"

    # 2. Проверка заголовка по стоп-паттернам (наивысший приоритет)
    for pattern, reason in STOP_PATTERNS:
        if pattern.search(title_raw):
            return True, f"{reason} в заголовке"

    # 3. Проверка описания по стоп-паттернам
    if desc_raw:
        for pattern, reason in STOP_PATTERNS:
            if pattern.search(full_text):
                return True, f"{reason} в описании"

    # 4. Проверка на соответствие профилю CastleWeb (веб-разработка, боты, софт, парсеры, дизайн)
    if not is_relevant_to_castleweb(title_raw, desc_raw, category_name):
        return True, "Не относится к профилю CastleWeb (веб, боты, софт, парсинг, дизайн)"

    return False, ""


async def hide_existing_excluded_orders() -> int:
    """
    Асинхронная служебная функция:
    Проверяет все существующие в базе данных SQLite заказы и помечает
    нерелевантные как is_hidden=True, чтобы они не засоряли интерфейс.
    """
    from app.db.database import async_session_factory
    from app.db.models import FLOrder, FLOrderInteraction, utc_now

    hidden_count = 0
    try:
        async with async_session_factory() as session:
            stmt = select(FLOrder)
            res = await session.execute(stmt)
            orders = res.scalars().all()

            for order in orders:
                excluded, _ = is_order_excluded(
                    title=order.title,
                    description=order.description or "",
                    category_name=order.category_name or ""
                )
                if excluded:
                    interaction = await session.get(FLOrderInteraction, order.id)
                    if not interaction:
                        interaction = FLOrderInteraction(
                            order_id=order.id,
                            is_favorite=False,
                            is_hidden=True,
                            is_read=True,
                            updated_at=utc_now()
                        )
                        session.add(interaction)
                        hidden_count += 1
                    elif not interaction.is_hidden:
                        interaction.is_hidden = True
                        interaction.updated_at = utc_now()
                        hidden_count += 1

            if hidden_count > 0:
                await session.commit()
                logger.info(f"🧹 Стоп-фильтр: скрыто {hidden_count} ранее сохраненных нерелевантных заказов в БД")
    except Exception as e:
        logger.warning(f"Ошибка при очистке старых заказов стоп-фильтром: {e}")

    return hidden_count
