import html
from typing import Dict, Any

def format_fl_order_message(order) -> str:
    """Форматирование карточки заказа с FL.ru для Telegram"""
    title = html.escape(order.title or "Без заголовка")
    cat_name = html.escape(order.category_name or "Общая категория")
    desc = html.escape(order.description or "Без описания")
    if len(desc) > 300:
        desc = desc[:300].rsplit(" ", 1)[0] + "..."

    # Бейджи
    badges = []
    if order.is_pro_only:
        badges.append("👑 <b>Только для PRO</b>")
    if order.is_urgent:
        badges.append("🔥 <b>Срочно</b>")
    badge_str = f" ({' | '.join(badges)})" if badges else ""

    # Цена
    if order.is_negotiable or not order.price_rub:
        price_text = "🤝 <b>По договоренности</b>"
    else:
        price_text = f"💰 <b>{order.price_rub:,} ₽</b>".replace(",", " ")

    msg = (
        f"💼 <b>{title}</b>{badge_str}\n"
        f"🏷 <i>{cat_name}</i>\n\n"
        f"{price_text}\n\n"
        f"📝 <b>Описание:</b>\n{desc}\n"
    )
    return msg

def format_lead_message(lead: Dict[str, Any]) -> str:
    """Форматирование карточки организации (Яндекс / 2ГИС) для Telegram"""
    name = html.escape(lead.get("name") or "Без названия")
    category = html.escape(lead.get("category") or "Бизнес")
    address = html.escape(lead.get("address") or "Адрес не указан")
    rating = lead.get("rating", 0.0)
    reviews = lead.get("reviews_count", 0)

    # Телефон
    phone = lead.get("primary_phone") or (lead.get("phones", [None])[0] if lead.get("phones") else None)
    phone_str = f"📞 <code>{html.escape(phone)}</code>" if phone else "📞 <i>Телефон не найден</i>"

    # Telegram
    tg = lead.get("telegram")
    if tg:
        tg_clean = tg if tg.startswith("@") or "t.me" in tg else f"@{tg}"
        tg_str = f"✉️ <b>Telegram:</b> <code>{html.escape(tg_clean)}</code>"
    else:
        tg_str = "✉️ <i>Telegram не найден</i>"

    # Сайт
    website = lead.get("website") or lead.get("final_url")
    site_str = f"🌐 <b>Сайт:</b> {html.escape(website)}" if website else "🌐 <i>Сайт отсутствует</i>"

    # Бейдж аудита
    badge = lead.get("status_badge", "")
    badge_text = "✅ <b>Сайт в порядке</b>"
    if badge == "NO_WEBSITE":
        badge_text = "🔴 <b>Нет сайта (нужна разработка)</b>"
    elif badge == "NO_SSL":
        badge_text = "⚠️ <b>Опасный сайт (нет SSL-сертификата)</b>"
    elif badge == "NOT_RESPONSIVE":
        badge_text = "📱 <b>Нет мобильной адаптации</b>"
    elif badge == "NO_ANALYTICS":
        badge_text = "📉 <b>Нет веб-аналитики (Я.Метрики)</b>"
    elif badge == "SITE_DOWN":
        badge_text = "⛔️ <b>Сайт недоступен (ошибка)</b>"

    # Питч
    pitch = lead.get("pitch") or {}
    opening_phrase = pitch.get("opening_phrase") or lead.get("pitch_opening_phrase")
    pitch_str = ""
    if opening_phrase:
        pitch_str = f"\n🎯 <b>Скрипт звонка:</b>\n<i>«{html.escape(opening_phrase)}»</i>\n"

    score = lead.get("lead_score", 50)
    source_icon = "📍 2ГИС" if lead.get("source") == "2gis" else "🗺 Яндекс.Карты"

    msg = (
        f"🏢 <b>{name}</b> ({source_icon})\n"
        f"🏷 <i>{category}</i>\n"
        f"📍 {address}\n"
        f"⭐️ Рейтинг: <b>{rating}</b> ({reviews} отз.) | Score: <b>{score}/100</b>\n\n"
        f"{phone_str}\n"
        f"{tg_str}\n"
        f"{site_str}\n\n"
        f"Статус аудита: {badge_text}\n"
        f"{pitch_str}"
    )
    return msg

def format_campaign_status(campaign_dict: Dict[str, Any]) -> str:
    """Форматирование статуса поисковой кампании"""
    niche = html.escape(campaign_dict.get("niche", ""))
    city = html.escape(campaign_dict.get("city", ""))
    found = campaign_dict.get("found_count", 0)
    target = campaign_dict.get("target_limit", 50)
    status = campaign_dict.get("status", "UNKNOWN")

    status_icon = "▶️ Выполняется" if status == "RUNNING" else ("⏸ Пауза (Капча)" if status == "PAUSED_CAPTCHA" else "✅ Завершен")

    percent = int((found / target) * 100) if target > 0 else 0
    percent = min(percent, 100)
    bar_len = 10
    filled = int(bar_len * percent / 100)
    bar = "█" * filled + "░" * (bar_len - filled)

    msg = (
        f"📊 <b>Кампания: {niche} ({city})</b>\n"
        f"Статус: <b>{status_icon}</b>\n"
        f"Прогресс: <code>[{bar}] {percent}%</code>\n"
        f"Собрано: <b>{found}</b> из <b>{target}</b> организаций"
    )
    return msg

def format_profile_summary(settings) -> str:
    """Форматирование карточки полного профиля настроек и фильтров пользователя"""
    from app.services.fl.constants import CATEGORY_BY_ID

    fl_status = "🟢 Включены" if settings.fl_enabled else "🔴 Отключены"
    cat_ids = settings.fl_categories or []
    cat_names = [
        CATEGORY_BY_ID[str(cid)]["name"] if str(cid) in CATEGORY_BY_ID else f"ID {cid}"
        for cid in cat_ids
    ]
    cats_str = ", ".join(cat_names) if cat_names else "<i>Не выбраны (все)</i>"

    budget_str = f"от {settings.fl_min_price:,} ₽".replace(",", " ") if settings.fl_min_price else "Любой"
    neg_ok = "✅ Принимать" if getattr(settings, "fl_allow_negotiable", True) else "❌ Скрывать"
    pro_rule = "❌ Скрывать PRO" if getattr(settings, "fl_hide_pro", False) else "✅ Показывать любые"
    urgent_rule = "🔥 Только срочные" if getattr(settings, "fl_urgent_only", False) else "⬜️ Все заказы"

    kw_list = getattr(settings, "fl_keywords", []) or []
    kw_str = ", ".join([html.escape(k) for k in kw_list]) if kw_list else "<i>Не заданы (любые)</i>"

    nw_list = settings.fl_negative_words or []
    nw_str = ", ".join([html.escape(n) for n in nw_list]) if nw_list else "<i>Не заданы</i>"

    maps_status = "🟢 Включены" if settings.maps_enabled else "🔴 Отключены"
    tg_mode = "🟢 Только с Telegram" if settings.maps_only_with_telegram else "⚪️ Все организации (с ТГ и без)"

    src = getattr(settings, "maps_source_filter", "all") or "all"
    src_map = {"all": "🌐 Яндекс.Карты + 2ГИС", "yandex": "🗺 Только Яндекс.Карты", "2gis": "📍 Только 2ГИС"}
    src_str = src_map.get(src, "🌐 Все")

    no_site = "🔴 Только без сайта" if getattr(settings, "maps_only_without_site", False) else "⬜️ Все лиды"
    no_ssl = "⚠️ Только без SSL" if getattr(settings, "maps_only_without_ssl", False) else "⬜️ Все лиды"
    limit_val = getattr(settings, "default_limit", 50)

    sound = "🔊 Со звуком" if getattr(settings, "notify_sound", True) else "🔇 Без звука (Silent)"
    captcha = "🟢 Оповещать в ТГ" if getattr(settings, "notify_captcha", True) else "🔴 Отключено"

    msg = (
        f"📋 <b>ПОЛНЫЙ ПРОФИЛЬ НАСТРОЕК И ФИЛЬТРОВ</b>\n\n"
        f"💼 <b>Биржа FL.ru:</b>\n"
        f"• Уведомления: <b>{fl_status}</b>\n"
        f"• Категории: {cats_str}\n"
        f"• Мин. бюджет: <b>{budget_str}</b>\n"
        f"• По договоренности: <b>{neg_ok}</b>\n"
        f"• Заказы PRO: <b>{pro_rule}</b>\n"
        f"• Срочность: <b>{urgent_rule}</b>\n"
        f"• Ключевые слова (White-list): {kw_str}\n"
        f"• Стоп-слова (Stop-list): {nw_str}\n\n"
        f"🗺 <b>Карты и Лидогенерация:</b>\n"
        f"• Уведомления: <b>{maps_status}</b>\n"
        f"• Фильтр контактов: <b>{tg_mode}</b>\n"
        f"• Источник: <b>{src_str}</b>\n"
        f"• Фильтр сайтов: <b>{no_site}</b>\n"
        f"• Фильтр SSL: <b>{no_ssl}</b>\n"
        f"• Лимит сбора по умолчанию: <b>{limit_val} шт.</b>\n\n"
        f"🔔 <b>Общие параметры:</b>\n"
        f"• Звук: <b>{sound}</b>\n"
        f"• Капча: <b>{captcha}</b>"
    )
    return msg
