from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from app.services.fl.constants import FL_CATEGORIES

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    kb = [
        [
            KeyboardButton(text="🗺 Поиск по картам"),
            KeyboardButton(text="🏢 Лиды (Яндекс / 2ГИС)")
        ],
        [
            KeyboardButton(text="💼 Заказы с FL.ru"),
            KeyboardButton(text="⚙️ Настройки и фильтры")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def maps_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления парсером карт"""
    buttons = [
        [
            InlineKeyboardButton(text="▶️ Запустить сбор лидов", callback_data="maps_start"),
            InlineKeyboardButton(text="⏹ Остановить сбор", callback_data="maps_stop")
        ],
        [
            InlineKeyboardButton(text="📊 Статус текущего сбора", callback_data="maps_status"),
            InlineKeyboardButton(text="🏢 Показать свежие лиды", callback_data="maps_recent_leads")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def leads_filter_keyboard(only_tg: bool) -> InlineKeyboardMarkup:
    """Клавиатура с переключателем (тумблером) фильтра по Telegram"""
    toggle_text = "🟢 Режим: ТОЛЬКО С TELEGRAM" if only_tg else "⚪️ Режим: ВСЕ КОМПАНИИ (С ТГ и без)"
    buttons = [
        [
            InlineKeyboardButton(text=toggle_text, callback_data="toggle_tg_filter")
        ],
        [
            InlineKeyboardButton(text="📥 Показать последние 5 лидов", callback_data="show_leads_page_0"),
            InlineKeyboardButton(text="📊 Сводка", callback_data="leads_stats")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def fl_menu_keyboard(fl_live_mode: bool = True) -> InlineKeyboardMarkup:
    """Меню биржи FL.ru с тумблером Live-режима"""
    live_text = "⚡ Live-мониторинг: 🟢 ВКЛ (15-20с)" if fl_live_mode else "⚡ Live-мониторинг: 🔴 ВЫКЛ"
    buttons = [
        [
            InlineKeyboardButton(text=live_text, callback_data="toggle_fl_live")
        ],
        [
            InlineKeyboardButton(text="🆕 Свежие заказы ленты", callback_data="fl_recent_orders"),
            InlineKeyboardButton(text="⭐️ Избранные заказы", callback_data="fl_favorite_orders")
        ],
        [
            InlineKeyboardButton(text="🏷 Настройка категорий/ниш", callback_data="fl_settings_cats"),
            InlineKeyboardButton(text="💰 Мин. бюджет / Стоп-слова", callback_data="fl_settings_budget")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def fl_categories_keyboard(selected_cats: list) -> InlineKeyboardMarkup:
    """Клавиатура с чекбоксами для выбора категорий FL.ru"""
    buttons = []
    selected_set = set(str(c) for c in (selected_cats or []))

    for cat in FL_CATEGORIES:
        cid = str(cat["id"])
        is_sel = cid in selected_set
        icon = "✅" if is_sel else "⬜️"
        label = f"{icon} {cat['name']}"
        buttons.append([
            InlineKeyboardButton(text=label, callback_data=f"fl_cat_toggle_{cid}")
        ])

    buttons.append([
        InlineKeyboardButton(text="✅ Выбрать все", callback_data="fl_cat_select_all"),
        InlineKeyboardButton(text="❌ Снять все", callback_data="fl_cat_clear_all")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Сохранить и назад", callback_data="to_fl_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def settings_menu_keyboard(settings) -> InlineKeyboardMarkup:
    """Главная панель настроек и фильтров"""
    buttons = [
        [
            InlineKeyboardButton(text="💼 Фильтры биржи FL.ru", callback_data="settings_fl_menu"),
            InlineKeyboardButton(text="🗺 Фильтры Карт и Лидов", callback_data="settings_maps_menu")
        ],
        [
            InlineKeyboardButton(text="🔔 Звук и Оповещения", callback_data="settings_notif_menu"),
            InlineKeyboardButton(text="📋 Мой профиль и фильтры", callback_data="settings_profile_summary")
        ],
        [
            InlineKeyboardButton(text="🔄 Сбросить настройки к стандартным", callback_data="settings_reset_defaults")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="to_main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def fl_settings_keyboard(settings) -> InlineKeyboardMarkup:
    """Подменю детальной настройки биржи FL.ru с тумблером Live-режима"""
    live_label = "🟢 ВКЛ (15-20с)" if getattr(settings, "fl_live_mode", True) else "🔴 ВЫКЛ"
    fl_notif = "🟢 Вкл" if settings.fl_enabled else "🔴 Выкл"
    cats_count = len(settings.fl_categories or [])
    budget_label = f"{settings.fl_min_price:,} ₽".replace(",", " ") if settings.fl_min_price else "Любой"
    neg_label = "✅ Принимать" if getattr(settings, "fl_allow_negotiable", True) else "❌ Скрывать"
    pro_label = "❌ Скрывать" if getattr(settings, "fl_hide_pro", False) else "✅ Показывать"
    urgent_label = "🔥 Только срочные" if getattr(settings, "fl_urgent_only", False) else "⬜️ Все заказы"
    kw_count = len(getattr(settings, "fl_keywords", []) or [])
    nw_count = len(settings.fl_negative_words or [])

    buttons = [
        [
            InlineKeyboardButton(text=f"⚡ Live-мониторинг: {live_label}", callback_data="toggle_fl_live")
        ],
        [
            InlineKeyboardButton(text=f"🔔 Уведомления FL: {fl_notif}", callback_data="toggle_notif_fl"),
            InlineKeyboardButton(text=f"🏷 Категории ({cats_count})", callback_data="fl_settings_cats")
        ],
        [
            InlineKeyboardButton(text=f"💵 Мин. бюджет: {budget_label}", callback_data="fl_budget_menu"),
            InlineKeyboardButton(text=f"🤝 По договор.: {neg_label}", callback_data="toggle_fl_negotiable")
        ],
        [
            InlineKeyboardButton(text=f"👑 Заказы PRO: {pro_label}", callback_data="toggle_fl_hide_pro"),
            InlineKeyboardButton(text=f"⚡ Срочность: {urgent_label}", callback_data="toggle_fl_urgent")
        ],
        [
            InlineKeyboardButton(text=f"🔍 Ключевые слова ({kw_count})", callback_data="fl_keywords_menu"),
            InlineKeyboardButton(text=f"🚫 Стоп-слова ({nw_count})", callback_data="fl_negwords_menu")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="menu_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def maps_settings_keyboard(settings) -> InlineKeyboardMarkup:
    """Подменю детальной настройки Карт и Лидогенерации"""
    maps_notif = "🟢 Вкл" if settings.maps_enabled else "🔴 Выкл"
    tg_icon = "🟢 Только с TG" if settings.maps_only_with_telegram else "⚪️ Все лиды"
    
    src = getattr(settings, "maps_source_filter", "all") or "all"
    src_labels = {"all": "🌐 Все сервисы", "yandex": "🗺 Только Яндекс", "2gis": "📍 Только 2ГИС"}
    src_title = src_labels.get(src, "🌐 Все")

    no_site = "🔴 Только без сайта" if getattr(settings, "maps_only_without_site", False) else "⬜️ Все"
    no_ssl = "⚠️ Только без SSL" if getattr(settings, "maps_only_without_ssl", False) else "⬜️ Все"
    limit_val = getattr(settings, "default_limit", 50)

    buttons = [
        [
            InlineKeyboardButton(text=f"🔔 Уведомления карт: {maps_notif}", callback_data="toggle_notif_maps"),
            InlineKeyboardButton(text=f"📱 Telegram: {tg_icon}", callback_data="toggle_maps_tg_filter")
        ],
        [
            InlineKeyboardButton(text=f"📍 Источник: {src_title}", callback_data="cycle_maps_source"),
            InlineKeyboardButton(text=f"📊 Лимит по умолч.: {limit_val}", callback_data="maps_limit_menu")
        ],
        [
            InlineKeyboardButton(text=f"🌐 Без сайта: {no_site}", callback_data="toggle_maps_no_site"),
            InlineKeyboardButton(text=f"🔒 Без SSL: {no_ssl}", callback_data="toggle_maps_no_ssl")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="menu_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def notifications_settings_keyboard(settings) -> InlineKeyboardMarkup:
    """Подменю звука и сервисных уведомлений"""
    sound = "🔊 Со звуком" if getattr(settings, "notify_sound", True) else "🔇 Без звука (Silent)"
    captcha = "🟢 Включены" if getattr(settings, "notify_captcha", True) else "🔴 Отключены"

    buttons = [
        [
            InlineKeyboardButton(text=f"Режим звука: {sound}", callback_data="toggle_notify_sound")
        ],
        [
            InlineKeyboardButton(text=f"Оповещения о капче: {captcha}", callback_data="toggle_notify_captcha")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="menu_settings")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def fl_budget_presets_keyboard(current_budget: int) -> InlineKeyboardMarkup:
    """Пресеты выбора минимального бюджета для биржи FL.ru"""
    presets = [0, 1000, 3000, 5000, 10000, 25000, 50000]
    rows = []
    current_row = []
    for p in presets:
        mark = "✓ " if p == current_budget else ""
        label = f"{mark}Любой (0 ₽)" if p == 0 else f"{mark}{p:,} ₽".replace(",", " ")
        current_row.append(InlineKeyboardButton(text=label, callback_data=f"set_fl_budget_{p}"))
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    rows.append([InlineKeyboardButton(text="✏️ Ввести бюджет вручную", callback_data="input_fl_budget_manual")])
    rows.append([InlineKeyboardButton(text="🔙 Назад в настройки FL", callback_data="settings_fl_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fl_words_keyboard(word_type: str, count: int) -> InlineKeyboardMarkup:
    """Управление ключевыми словами (белыми) или стоп-словами (минус)"""
    title_word = "ключевые" if word_type == "keywords" else "стоп"
    buttons = [
        [
            InlineKeyboardButton(text=f"➕ Добавить {title_word}-слова", callback_data=f"add_words_{word_type}")
        ],
        [
            InlineKeyboardButton(text=f"🗑 Очистить весь список ({count})", callback_data=f"clear_words_{word_type}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в настройки FL", callback_data="settings_fl_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def maps_limit_presets_keyboard(current_limit: int) -> InlineKeyboardMarkup:
    """Пресеты лимита сбора организаций для карт"""
    limits = [10, 25, 50, 100]
    row = []
    for lim in limits:
        mark = "✓ " if lim == current_limit else ""
        row.append(InlineKeyboardButton(text=f"{mark}{lim} шт.", callback_data=f"set_maps_limit_{lim}"))

    buttons = [
        row,
        [InlineKeyboardButton(text="🔙 Назад в настройки Карт", callback_data="settings_maps_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def order_inline_keyboard(order_id: int, url: str, is_favorite: bool = False) -> InlineKeyboardMarkup:
    """Инлайн-кнопки под карточкой заказа FL.ru"""
    fav_text = "🌟 В избранном" if is_favorite else "⭐️ В избранное"
    buttons = [
        [
            InlineKeyboardButton(text="🔗 Открыть на FL.ru", url=url)
        ],
        [
            InlineKeyboardButton(text=fav_text, callback_data=f"fl_fav_{order_id}"),
            InlineKeyboardButton(text="🚫 Скрыть", callback_data=f"fl_hide_{order_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def lead_inline_keyboard(
    org_id: int,
    telegram: str = None,
    primary_phone: str = None,
    card_url: str = None,
    website: str = None
) -> InlineKeyboardMarkup:
    """Инлайн-кнопки под карточкой организации с карт"""
    buttons = []
    top_row = []

    if telegram:
        tg_link = telegram if telegram.startswith("http") else f"https://t.me/{telegram.lstrip('@')}"
        top_row.append(InlineKeyboardButton(text="✉️ Написать в Telegram", url=tg_link))

    if website:
        site_link = website if website.startswith("http") else f"https://{website}"
        top_row.append(InlineKeyboardButton(text="🌐 Сайт", url=site_link))

    if top_row:
        buttons.append(top_row)

    second_row = []
    if card_url:
        second_row.append(InlineKeyboardButton(text="🗺 На карте", url=card_url))

    if second_row:
        buttons.append(second_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def captcha_resolved_keyboard(campaign_id: int) -> InlineKeyboardMarkup:
    """Кнопка подтверждения решения капчи"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Я решил капчу в окне браузера", callback_data=f"resolve_captcha_{campaign_id}")
    ]])
