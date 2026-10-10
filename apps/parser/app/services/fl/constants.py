"""
Константы категорий биржи FL.ru для фильтрации и мониторинга
"""

FL_CATEGORIES = [
    {
        "id": "2",
        "slug": "razrabotka-botov-skriptov",
        "url_path": "programmirovanie",
        "name": "Боты, парсеры и скрипты",
        "description": "Telegram-боты, web-скрейпинг, автоматизация процессов"
    },
    {
        "id": "5",
        "slug": "veb-razrabotka",
        "url_path": "saity",
        "name": "Веб-разработка (Frontend / Backend)",
        "description": "Сайты под ключ, лендинги, веб-сервисы, FastAPI, Django, React, Node.js"
    },
    {
        "id": "7",
        "slug": "prikladnoe-programmirovanie",
        "url_path": "programmirovanie",
        "name": "Прикладное программирование (Python, C++, Java)",
        "description": "Десктоп-софт, системные утилиты, серверные скрипты"
    },
    {
        "id": "3",
        "slug": "mobilnye-prilozheniya",
        "url_path": "mobile",
        "name": "Мобильные приложения (iOS / Android / Flutter)",
        "description": "Разработка и доработка мобильных приложений"
    },
    {
        "id": "37",
        "slug": "dizajn-interfejsov-ui-ux",
        "url_path": "dizajn",
        "name": "UI/UX Дизайн и Веб-дизайн",
        "description": "Дизайн сайтов, интерфейсов, Figma, адаптивные макеты"
    },
    {
        "id": "8",
        "slug": "1c-crm-erp",
        "url_path": "avtomatizaciya-biznesa",
        "name": "1С, CRM и интеграции",
        "description": "Интеграции с Битрикс24, AmoCRM, 1С, складскими сервисами"
    },
    {
        "id": "14",
        "slug": "reklama-i-marketing",
        "url_path": "reklama-marketing",
        "name": "Маркетинг, SEO и Трафик",
        "description": "Контекстная реклама, таргетинг, продвижение сайтов"
    },
    {
        "id": "1",
        "slug": "teksty-kopirajting",
        "url_path": "teksty",
        "name": "Тексты, копирайтинг и переводы",
        "description": "Статьи, описания товаров, продающие тексты"
    }
]

CATEGORY_BY_ID = {c["id"]: c for c in FL_CATEGORIES}
CATEGORY_BY_NAME = {c["name"]: c for c in FL_CATEGORIES}

