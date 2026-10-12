import logging
from typing import Optional
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.db.database import async_session_factory
from app.db.models import (
    TelegramUser, TelegramUserSettings, FLOrder, FLOrderInteraction,
    Organization, AuditResult, SearchCampaign, utc_now
)
from app.services.fl.constants import FL_CATEGORIES, CATEGORY_BY_ID
from app.services.telegram.keyboards import (
    main_menu_keyboard, maps_menu_keyboard, leads_filter_keyboard,
    fl_menu_keyboard, fl_categories_keyboard, settings_menu_keyboard,
    fl_settings_keyboard, maps_settings_keyboard, notifications_settings_keyboard,
    fl_budget_presets_keyboard, fl_words_keyboard, maps_limit_presets_keyboard,
    order_inline_keyboard, lead_inline_keyboard
)
from app.services.telegram.formatters import (
    format_fl_order_message, format_lead_message, format_campaign_status, format_profile_summary
)

logger = logging.getLogger("tg_handlers")
router = Router()

class SearchCampaignStates(StatesGroup):
    waiting_for_niche = State()
    waiting_for_city = State()
    waiting_for_limit = State()

class BudgetState(StatesGroup):
    waiting_for_budget = State()

class KeywordsState(StatesGroup):
    waiting_for_words = State()

class NegativeWordsState(StatesGroup):
    waiting_for_words = State()

async def get_or_create_user(chat_id: int, username: str = None, full_name: str = None) -> TelegramUserSettings:
    """Получает или создает пользователя и его настройки в БД"""
    async with async_session_factory() as db:
        user = await db.get(TelegramUser, chat_id)
        if not user:
            user = TelegramUser(
                chat_id=chat_id,
                username=username,
                full_name=full_name,
                is_active=True,
                created_at=utc_now()
            )
            db.add(user)
            await db.flush()

            settings = TelegramUserSettings(
                chat_id=chat_id,
                fl_enabled=True,
                fl_categories=["2", "5", "7"],  # По умолчанию: боты, веб, софт
                fl_min_price=0,
                fl_negative_words=[],
                fl_keywords=[],
                fl_allow_negotiable=True,
                fl_hide_pro=False,
                fl_urgent_only=False,
                maps_enabled=True,
                maps_only_with_telegram=True,
                maps_source_filter="all",
                maps_only_without_site=False,
                maps_only_without_ssl=False,
                notify_sound=True,
                notify_captcha=True,
                default_limit=50
            )
            db.add(settings)
            await db.commit()
            return settings
        else:
            settings = await db.get(TelegramUserSettings, chat_id)
            if not settings:
                settings = TelegramUserSettings(
                    chat_id=chat_id,
                    fl_enabled=True,
                    fl_categories=["2", "5", "7"],
                    fl_min_price=0,
                    fl_negative_words=[],
                    fl_keywords=[],
                    fl_allow_negotiable=True,
                    fl_hide_pro=False,
                    fl_urgent_only=False,
                    maps_enabled=True,
                    maps_only_with_telegram=True,
                    maps_source_filter="all",
                    maps_only_without_site=False,
                    maps_only_without_ssl=False,
                    notify_sound=True,
                    notify_captcha=True,
                    default_limit=50
                )
                db.add(settings)
                await db.commit()
            return settings

# --- КОМАНДЫ И ГЛАВНОЕ МЕНЮ ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    settings = await get_or_create_user(
        chat_id=message.chat.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    welcome_text = (
        f"👋 <b>Добро пожаловать, {message.from_user.first_name}!</b>\n\n"
        f"🎯 <b>LeadHunter Pro + FL.ru Monitor</b> — единый центр лидогенерации и заказов.\n\n"
        f"• <b>Мониторинг FL.ru:</b> получение заказов по выбранным категориям без спама.\n"
        f"• <b>Сбор лидов по картам:</b> Яндекс.Карты и 2ГИС с глубоким аудитом сайтов.\n"
        f"• <b>Фильтр Telegram:</b> возможность получать <u>только компании с прямым ТГ-контактом</u>.\n\n"
        f"Выберите нужный раздел в меню ниже ⬇️"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu_keyboard())

@router.message(F.text == "🗺 Поиск по картам")
async def menu_maps(message: Message):
    text = (
        "🗺 <b>Управление поиском по картам (Яндекс.Карты + 2ГИС)</b>\n\n"
        "Здесь вы можете запустить фоновый сбор организаций с автоматическим аудитом "
        "их сайтов (проверка SSL, адаптивности, аналитики, CMS) и генерацией готовых скриптов звонков."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=maps_menu_keyboard())

@router.message(F.text == "🏢 Лиды (Яндекс / 2ГИС)")
async def menu_leads(message: Message):
    settings = await get_or_create_user(message.chat.id)
    only_tg = settings.maps_only_with_telegram
    mode_descr = "Включен режим <b>«Только с Telegram»</b>. Организации без найденного TG скрываются." if only_tg else "Включен режим <b>«Все организации»</b> (с TG и без него)."

    text = (
        f"🏢 <b>База лидов с геосервисов</b>\n\n"
        f"{mode_descr}\n\n"
        f"Вы можете переключать режим фильтрации нажатием на кнопку ниже."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=leads_filter_keyboard(only_tg))

@router.message(Command("live"))
async def cmd_live(message: Message):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, message.chat.id)
        if not settings:
            settings = TelegramUserSettings(chat_id=message.chat.id, fl_live_mode=True)
            db.add(settings)
        else:
            settings.fl_live_mode = not getattr(settings, "fl_live_mode", True)
        await db.commit()
        val = settings.fl_live_mode

    status_str = "🟢 ВКЛЮЧЕН (опрос ленты каждые 15-20 сек)" if val else "🔴 ОТКЛЮЧЕН (на паузе)"
    text = (
        f"⚡ <b>Live-режим FL.ru:</b> {status_str}\n\n"
        f"Вы можете быстро переключать его кнопкой ниже:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=fl_menu_keyboard(val))

@router.message(Command("fl"))
async def cmd_fl(message: Message):
    async with async_session_factory() as db:
        stmt = (
            select(FLOrder)
            .options(selectinload(FLOrder.interaction))
            .order_by(FLOrder.id.desc())
            .limit(5)
        )
        res = await db.execute(stmt)
        orders = res.scalars().all()

    if not orders:
        await message.answer("Заказы еще не загружены воркером. Подождите 15-20 секунд...")
        return

    await message.answer("⚡️ <b>Свежие заказы с биржи FL.ru:</b>", parse_mode="HTML")
    for ord_obj in orders:
        msg = format_fl_order_message(ord_obj)
        is_fav = ord_obj.interaction.is_favorite if ord_obj.interaction else False
        kb = order_inline_keyboard(order_id=ord_obj.id, url=ord_obj.url, is_favorite=is_fav)
        try:
            await message.answer(msg, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            logger.warning(f"Ошибка отправки заказа {ord_obj.id}: {e}")

@router.message(F.text == "💼 Заказы с FL.ru")
async def menu_fl(message: Message):
    settings = await get_or_create_user(message.chat.id)
    cats_count = len(settings.fl_categories or [])
    min_price_str = f"{settings.fl_min_price:,} ₽".replace(",", " ") if settings.fl_min_price else "Любой"
    live_status = "🟢 ВКЛ (каждые 15-20с)" if getattr(settings, "fl_live_mode", True) else "🔴 ВЫКЛ"

    text = (
        f"💼 <b>Лента заказов биржи FL.ru</b>\n\n"
        f"• Live-мониторинг: <b>{live_status}</b>\n"
        f"• Активных категорий: <b>{cats_count}</b>\n"
        f"• Минимальный бюджет: <b>{min_price_str}</b>\n"
        f"• Заказы «По договоренности»: <b>доставляются всегда</b>\n\n"
        f"Переключайте Live-режим или выберите действие ниже ⬇️"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=fl_menu_keyboard(getattr(settings, "fl_live_mode", True)))

@router.message(F.text == "⚙️ Настройки и фильтры")
async def menu_settings(message: Message):
    settings = await get_or_create_user(message.chat.id)
    text = "⚙️ <b>Персональные настройки уведомлений и фильтров:</b>"
    await message.answer(text, parse_mode="HTML", reply_markup=settings_menu_keyboard(settings))

@router.callback_query(F.data == "to_main_menu")
async def cb_to_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await call.answer()

# --- ФИЛЬТР TELEGRAM И ПРОСМОТР ЛИДОВ ---

@router.callback_query(F.data == "toggle_tg_filter")
async def cb_toggle_tg_filter(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if not settings:
            settings = TelegramUserSettings(chat_id=call.message.chat.id, maps_only_with_telegram=True)
            db.add(settings)
        else:
            settings.maps_only_with_telegram = not settings.maps_only_with_telegram
        await db.commit()
        new_val = settings.maps_only_with_telegram

    status_word = "ТОЛЬКО С TELEGRAM ✅" if new_val else "ВСЕ ОРГАНИЗАЦИИ (с ТГ и без) 🌐"
    await call.answer(f"Режим переключен: {status_word}")

    try:
        await call.message.edit_reply_markup(reply_markup=leads_filter_keyboard(new_val))
    except Exception:
        pass

@router.callback_query(F.data.in_(["show_leads_page_0", "maps_recent_leads"]))
async def cb_show_leads(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    only_tg = settings.maps_only_with_telegram

    async with async_session_factory() as db:
        stmt = select(Organization).options(selectinload(Organization.audit))
        if only_tg:
            stmt = stmt.where(Organization.has_telegram == True)
        stmt = stmt.order_by(Organization.id.desc()).limit(5)
        res = await db.execute(stmt)
        orgs = res.scalars().all()

    if not orgs:
        empty_text = "Лиды с Telegram пока не найдены." if only_tg else "База лидов пуста. Запустите сбор через раздел «Поиск по картам»."
        try:
            await call.message.answer(empty_text)
        except Exception:
            pass
        await call.answer()
        return

    await call.answer("Загружаю карточки...")
    for org in orgs:
        audit = org.audit
        lead_dict = {
            "id": org.id,
            "name": org.name,
            "category": org.category,
            "address": org.address,
            "rating": org.rating,
            "reviews_count": org.reviews_count,
            "phones": org.phones,
            "primary_phone": (org.phones[0] if org.phones else None),
            "website": org.website,
            "final_url": audit.final_url if audit else org.website,
            "card_url": org.card_url,
            "source": org.source,
            "telegram": org.telegram or (next((s for s in audit.extra_socials if "t.me" in s), None) if audit and audit.extra_socials else None),
            "status_badge": audit.status_badge if audit else "NO_WEBSITE",
            "lead_score": audit.lead_score if audit else 50,
            "pitch_opening_phrase": audit.pitch_opening_phrase if audit else None
        }

        msg_text = format_lead_message(lead_dict)
        kb = lead_inline_keyboard(
            org_id=org.id,
            telegram=lead_dict["telegram"],
            primary_phone=lead_dict["primary_phone"],
            card_url=org.card_url,
            website=lead_dict["website"]
        )
        try:
            await call.message.answer(msg_text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            logger.warning(f"Ошибка отправки карточки организации {org.id}: {e}")

@router.callback_query(F.data == "leads_stats")
async def cb_leads_stats(call: CallbackQuery):
    async with async_session_factory() as db:
        total = (await db.execute(select(func.count(Organization.id)))).scalar_one() or 0
        with_tg = (await db.execute(select(func.count(Organization.id)).where(Organization.has_telegram == True))).scalar_one() or 0
        total_campaigns = (await db.execute(select(func.count(SearchCampaign.id)))).scalar_one() or 0

    text = (
        f"📊 <b>Сводка по базе организаций:</b>\n\n"
        f"• Всего собрано организаций: <b>{total}</b>\n"
        f"• Организаций с Telegram: <b>{with_tg}</b> ({(with_tg / total * 100):.1f}%)\n"
        f"• Проведено поисковых кампаний: <b>{total_campaigns}</b>"
    )
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()

# --- КАТЕГОРИИ И ЗАКАЗЫ FL.RU ---

@router.callback_query(F.data == "to_fl_menu")
async def cb_to_fl_menu(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    text = "💼 <b>Лента заказов биржи FL.ru</b>"
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=fl_menu_keyboard(getattr(settings, "fl_live_mode", True)))
    await call.answer()

@router.callback_query(F.data == "toggle_fl_live")
async def cb_toggle_fl_live(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if not settings:
            settings = TelegramUserSettings(chat_id=call.message.chat.id, fl_live_mode=True)
            db.add(settings)
        else:
            settings.fl_live_mode = not getattr(settings, "fl_live_mode", True)
        await db.commit()
        val = settings.fl_live_mode

    if val:
        alert_text = "⚡ Live-мониторинг FL.ru ВКЛЮЧЕН!\nСвежие заказы с проверкой каждые 15-20 сек будут мгновенно приходить в этот чат."
    else:
        alert_text = "⏸ Live-мониторинг FL.ru ОТКЛЮЧЕН.\nАвто-уведомления на паузе. Вы можете просматривать заказы вручную по кнопке «🆕 Свежие заказы»."

    await call.answer(alert_text, show_alert=True)

    try:
        if "Детальные настройки" in (call.message.text or "") or "Фильтры" in (call.message.text or ""):
            await call.message.edit_reply_markup(reply_markup=fl_settings_keyboard(settings))
        else:
            await call.message.edit_reply_markup(reply_markup=fl_menu_keyboard(val))
    except Exception:
        pass

@router.callback_query(F.data == "fl_recent_orders")
async def cb_fl_recent(call: CallbackQuery):
    async with async_session_factory() as db:
        stmt = (
            select(FLOrder)
            .options(selectinload(FLOrder.interaction))
            .order_by(FLOrder.id.desc())
            .limit(5)
        )
        res = await db.execute(stmt)
        orders = res.scalars().all()

    if not orders:
        await call.message.answer("Заказы еще не загружены воркером. Подождите 30 секунд...")
        await call.answer()
        return

    await call.answer("Отправляю свежие заказы...")
    for ord_obj in orders:
        msg = format_fl_order_message(ord_obj)
        is_fav = ord_obj.interaction.is_favorite if ord_obj.interaction else False
        kb = order_inline_keyboard(order_id=ord_obj.id, url=ord_obj.url, is_favorite=is_fav)
        try:
            await call.message.answer(msg, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            logger.warning(f"Ошибка отправки заказа {ord_obj.id}: {e}")

@router.callback_query(F.data == "fl_favorite_orders")
async def cb_fl_favs(call: CallbackQuery):
    async with async_session_factory() as db:
        stmt = (
            select(FLOrder)
            .join(FLOrderInteraction)
            .where(FLOrderInteraction.is_favorite == True)
            .options(selectinload(FLOrder.interaction))
            .order_by(FLOrder.id.desc())
            .limit(10)
        )
        res = await db.execute(stmt)
        orders = res.scalars().all()

    if not orders:
        await call.message.answer("В избранном пока нет заказов. Нажмите ⭐️ на карточке любого заказа, чтобы сохранить.")
        await call.answer()
        return

    await call.answer("Загружаю избранное...")
    for ord_obj in orders:
        msg = format_fl_order_message(ord_obj)
        kb = order_inline_keyboard(order_id=ord_obj.id, url=ord_obj.url, is_favorite=True)
        try:
            await call.message.answer(msg, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            logger.warning(f"Ошибка отправки избранного {ord_obj.id}: {e}")

@router.callback_query(F.data.startswith("fl_fav_"))
async def cb_toggle_fav(call: CallbackQuery):
    order_id = int(call.data.replace("fl_fav_", ""))
    async with async_session_factory() as db:
        inter = await db.get(FLOrderInteraction, order_id)
        if not inter:
            inter = FLOrderInteraction(order_id=order_id, is_favorite=True, updated_at=utc_now())
            db.add(inter)
            is_fav = True
        else:
            inter.is_favorite = not inter.is_favorite
            inter.updated_at = utc_now()
            is_fav = inter.is_favorite
        await db.commit()

        ord_obj = await db.get(FLOrder, order_id)
        url = ord_obj.url if ord_obj else "https://www.fl.ru"

    alert_text = "⭐️ Заказ добавлен в избранное!" if is_fav else "Удалено из избранного."
    await call.answer(alert_text)
    try:
        await call.message.edit_reply_markup(reply_markup=order_inline_keyboard(order_id, url, is_favorite=is_fav))
    except Exception:
        pass

@router.callback_query(F.data.startswith("fl_hide_"))
async def cb_hide_order(call: CallbackQuery):
    order_id = int(call.data.replace("fl_hide_", ""))
    async with async_session_factory() as db:
        inter = await db.get(FLOrderInteraction, order_id)
        if not inter:
            inter = FLOrderInteraction(order_id=order_id, is_hidden=True, updated_at=utc_now())
            db.add(inter)
        else:
            inter.is_hidden = True
            inter.updated_at = utc_now()
        await db.commit()

    await call.answer("Заказ скрыт.")
    try:
        await call.message.delete()
    except Exception:
        pass

@router.callback_query(F.data == "fl_settings_cats")
async def cb_fl_cats(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    text = (
        "🏷 <b>Выберите ниши/категории на FL.ru для мониторинга:</b>\n\n"
        "Нажимайте на нужные пункты, чтобы включить (✅) или отключить (⬜️) получение заказов."
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=fl_categories_keyboard(settings.fl_categories))
    await call.answer()

@router.callback_query(F.data.startswith("fl_cat_toggle_"))
async def cb_toggle_cat(call: CallbackQuery):
    cat_id = call.data.replace("fl_cat_toggle_", "")
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        cats = list(settings.fl_categories or [])
        if cat_id in cats:
            cats.remove(cat_id)
        else:
            cats.append(cat_id)
        settings.fl_categories = cats
        await db.commit()

    await call.answer()
    try:
        await call.message.edit_reply_markup(reply_markup=fl_categories_keyboard(cats))
    except Exception:
        pass

@router.callback_query(F.data == "fl_cat_select_all")
async def cb_cat_select_all(call: CallbackQuery):
    all_ids = [str(c["id"]) for c in FL_CATEGORIES]
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        settings.fl_categories = all_ids
        await db.commit()
    await call.answer("Выбраны все категории")
    try:
        await call.message.edit_reply_markup(reply_markup=fl_categories_keyboard(all_ids))
    except Exception:
        pass

@router.callback_query(F.data == "fl_cat_clear_all")
async def cb_cat_clear_all(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        settings.fl_categories = []
        await db.commit()
    await call.answer("Категории очищены")
    try:
        await call.message.edit_reply_markup(reply_markup=fl_categories_keyboard([]))
    except Exception:
        pass

# --- РАСШИРЕННЫЕ НАСТРОЙКИ И ФИЛЬТРЫ ---

@router.callback_query(F.data == "menu_settings")
async def cb_menu_settings(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    text = (
        "⚙️ <b>Центр настроек и расширенной фильтрации</b>\n\n"
        "Выберите раздел для детальной настройки параметров сбора, фильтрации и оповещений:"
    )
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=settings_menu_keyboard(settings))
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=settings_menu_keyboard(settings))
    await call.answer()

# 1. FL.ru Настройки
@router.callback_query(F.data == "settings_fl_menu")
async def cb_settings_fl(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    text = (
        "💼 <b>Детальные настройки биржи FL.ru</b>\n\n"
        "Настройте фильтрацию проектов по категориям, бюджету, типу (PRO/срочные) и ключевым словам:"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=fl_settings_keyboard(settings))
    await call.answer()

@router.callback_query(F.data == "toggle_notif_fl")
async def cb_toggle_notif_fl(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.fl_enabled = not settings.fl_enabled
            await db.commit()
            val = settings.fl_enabled
    st_text = "включены 🟢" if val else "отключены 🔴"
    await call.answer(f"Уведомления FL {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=fl_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "toggle_fl_negotiable")
async def cb_toggle_fl_negotiable(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.fl_allow_negotiable = not getattr(settings, "fl_allow_negotiable", True)
            await db.commit()
            val = settings.fl_allow_negotiable
    st_text = "разрешены ✅" if val else "скрыты ❌"
    await call.answer(f"Проекты 'По договоренности': {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=fl_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "toggle_fl_hide_pro")
async def cb_toggle_fl_hide_pro(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.fl_hide_pro = not getattr(settings, "fl_hide_pro", False)
            await db.commit()
            val = settings.fl_hide_pro
    st_text = "скрываются ❌" if val else "отображаются ✅"
    await call.answer(f"Заказы Только для PRO: {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=fl_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "toggle_fl_urgent")
async def cb_toggle_fl_urgent(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.fl_urgent_only = not getattr(settings, "fl_urgent_only", False)
            await db.commit()
            val = settings.fl_urgent_only
    st_text = "включен (только срочные) 🔥" if val else "выключен (все заказы) ⬜️"
    await call.answer(f"Фильтр срочности: {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=fl_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data.in_(["fl_budget_menu", "fl_settings_budget", "set_min_budget"]))
async def cb_fl_budget_menu(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    text = (
        f"💵 <b>Минимальный бюджет заказа FL.ru</b>\n\n"
        f"Текущий порог: <b>{settings.fl_min_price:,} ₽</b>\n\n"
        f"Выберите готовый пресет бюджета или введите сумму вручную:"
    ).replace(",", " ")
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=fl_budget_presets_keyboard(settings.fl_min_price))
    await call.answer()

@router.callback_query(F.data.startswith("set_fl_budget_"))
async def cb_set_fl_budget_preset(call: CallbackQuery):
    budget_val = int(call.data.replace("set_fl_budget_", ""))
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.fl_min_price = budget_val
            await db.commit()
    await call.answer(f"Минимальный бюджет: {budget_val:,} ₽".replace(",", " "))
    text = (
        "💼 <b>Детальные настройки биржи FL.ru</b>\n\n"
        "Настройки успешно обновлены."
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=fl_settings_keyboard(settings))

@router.callback_query(F.data == "input_fl_budget_manual")
async def cb_input_fl_budget_manual(call: CallbackQuery, state: FSMContext):
    await state.set_state(BudgetState.waiting_for_budget)
    await call.message.answer(
        "✏️ Введите <b>минимальный бюджет в рублях</b> целым числом (например: <code>15000</code> или <code>0</code> для любого):",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(BudgetState.waiting_for_budget)
async def state_budget_input(message: Message, state: FSMContext):
    text_val = message.text.replace(" ", "").replace("₽", "").strip()
    try:
        val = int(text_val)
        val = max(0, val)
    except ValueError:
        val = 0
    await state.clear()
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, message.chat.id)
        if settings:
            settings.fl_min_price = val
            await db.commit()

    await message.answer(
        f"✅ Минимальный бюджет сохранен: <b>{val:,} ₽</b>".replace(",", " "),
        parse_mode="HTML",
        reply_markup=fl_settings_keyboard(settings)
    )

# Ключевые слова (White-list)
@router.callback_query(F.data == "fl_keywords_menu")
async def cb_fl_keywords_menu(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    words = getattr(settings, "fl_keywords", []) or []
    words_str = "\n".join([f"• <code>{w}</code>" for w in words]) if words else "<i>Список пуст (доставляются все заказы ленты)</i>"
    text = (
        f"🔍 <b>Ключевые слова (White-list)</b>\n\n"
        f"Если заданы, вам будут приходить <u>только те заказы</u>, в названии или описании которых есть хотя бы одно из этих слов:\n\n"
        f"{words_str}"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=fl_words_keyboard("keywords", len(words)))
    await call.answer()

@router.callback_query(F.data == "add_words_keywords")
async def cb_add_words_keywords(call: CallbackQuery, state: FSMContext):
    await state.set_state(KeywordsState.waiting_for_words)
    await call.message.answer(
        "➕ Введите <b>ключевые слова</b> через запятую\n(например: <code>парсер, бот, python, react</code>):",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(KeywordsState.waiting_for_words)
async def state_keywords_input(message: Message, state: FSMContext):
    raw = message.text.replace("\n", ",")
    new_words = [w.strip() for w in raw.split(",") if w.strip()]
    await state.clear()
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, message.chat.id)
        if settings:
            current = list(getattr(settings, "fl_keywords", []) or [])
            for nw in new_words:
                if nw.lower() not in [c.lower() for c in current]:
                    current.append(nw)
            settings.fl_keywords = current
            await db.commit()

    await message.answer(
        f"✅ Добавлено слов: {len(new_words)}. Всего в белом списке: {len(current)}.",
        reply_markup=fl_settings_keyboard(settings)
    )

@router.callback_query(F.data == "clear_words_keywords")
async def cb_clear_words_keywords(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.fl_keywords = []
            await db.commit()
    await call.answer("Ключевые слова очищены")
    await cb_fl_keywords_menu(call)

# Стоп-слова (Stop-list / Negative)
@router.callback_query(F.data == "fl_negwords_menu")
async def cb_fl_negwords_menu(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    words = settings.fl_negative_words or []
    words_str = "\n".join([f"• <code>{w}</code>" for w in words]) if words else "<i>Список пуст (минус-слова не фильтруются)</i>"
    text = (
        f"🚫 <b>Стоп-слова (Минус-слова)</b>\n\n"
        f"Заказы, содержащие любое из этих слов, будут <u>автоматически отсеиваться</u>:\n\n"
        f"{words_str}"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=fl_words_keyboard("negative", len(words)))
    await call.answer()

@router.callback_query(F.data == "add_words_negative")
async def cb_add_words_negative(call: CallbackQuery, state: FSMContext):
    await state.set_state(NegativeWordsState.waiting_for_words)
    await call.message.answer(
        "➕ Введите <b>стоп-слова</b> через запятую\n(например: <code>1С, битрикс, диплом, wordpress</code>):",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(NegativeWordsState.waiting_for_words)
async def state_negwords_input(message: Message, state: FSMContext):
    raw = message.text.replace("\n", ",")
    new_words = [w.strip() for w in raw.split(",") if w.strip()]
    await state.clear()
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, message.chat.id)
        if settings:
            current = list(settings.fl_negative_words or [])
            for nw in new_words:
                if nw.lower() not in [c.lower() for c in current]:
                    current.append(nw)
            settings.fl_negative_words = current
            await db.commit()

    await message.answer(
        f"✅ Добавлено стоп-слов: {len(new_words)}. Всего в черном списке: {len(current)}.",
        reply_markup=fl_settings_keyboard(settings)
    )

@router.callback_query(F.data == "clear_words_negative")
async def cb_clear_words_negative(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.fl_negative_words = []
            await db.commit()
    await call.answer("Стоп-слова очищены")
    await cb_fl_negwords_menu(call)

# 2. Настройки Карт и Лидогенерации
@router.callback_query(F.data == "settings_maps_menu")
async def cb_settings_maps(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    text = (
        "🗺 <b>Детальные настройки поиска по картам и лидов</b>\n\n"
        "Настройте фильтрацию контактов Telegram, источника, сайтов и лимитов сбора:"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=maps_settings_keyboard(settings))
    await call.answer()

@router.callback_query(F.data == "toggle_notif_maps")
async def cb_toggle_notif_maps(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.maps_enabled = not settings.maps_enabled
            await db.commit()
            val = settings.maps_enabled
    st_text = "включены 🟢" if val else "отключены 🔴"
    await call.answer(f"Уведомления карт {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=maps_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "toggle_maps_tg_filter")
async def cb_toggle_maps_tg_filter_settings(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.maps_only_with_telegram = not settings.maps_only_with_telegram
            await db.commit()
            val = settings.maps_only_with_telegram
    st_text = "ТОЛЬКО С TELEGRAM 🟢" if val else "ВСЕ ОРГАНИЗАЦИИ ⚪️"
    await call.answer(f"Режим контактов: {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=maps_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "cycle_maps_source")
async def cb_cycle_maps_source(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            cur = getattr(settings, "maps_source_filter", "all") or "all"
            cycle_map = {"all": "yandex", "yandex": "2gis", "2gis": "all"}
            settings.maps_source_filter = cycle_map.get(cur, "all")
            await db.commit()
            new_src = settings.maps_source_filter
    labels = {"all": "Все сервисы (Яндекс + 2ГИС)", "yandex": "Только Яндекс.Карты", "2gis": "Только 2ГИС"}
    await call.answer(f"Источник: {labels.get(new_src, new_src)}")
    try:
        await call.message.edit_reply_markup(reply_markup=maps_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "toggle_maps_no_site")
async def cb_toggle_maps_no_site(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.maps_only_without_site = not getattr(settings, "maps_only_without_site", False)
            await db.commit()
            val = settings.maps_only_without_site
    st_text = "включен (только без сайта) 🔴" if val else "выключен (все) ⬜️"
    await call.answer(f"Фильтр отсутствия сайта: {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=maps_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "toggle_maps_no_ssl")
async def cb_toggle_maps_no_ssl(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.maps_only_without_ssl = not getattr(settings, "maps_only_without_ssl", False)
            await db.commit()
            val = settings.maps_only_without_ssl
    st_text = "включен (только без SSL) ⚠️" if val else "выключен (все) ⬜️"
    await call.answer(f"Фильтр отсутствия SSL: {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=maps_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "maps_limit_menu")
async def cb_maps_limit_menu(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    cur_limit = getattr(settings, "default_limit", 50)
    text = (
        f"📊 <b>Лимит сбора организаций по умолчанию</b>\n\n"
        f"Текущее значение: <b>{cur_limit} шт.</b>\n"
        f"Выберите лимит для новых поисковых кампаний:"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=maps_limit_presets_keyboard(cur_limit))
    await call.answer()

@router.callback_query(F.data.startswith("set_maps_limit_"))
async def cb_set_maps_limit_preset(call: CallbackQuery):
    limit_val = int(call.data.replace("set_maps_limit_", ""))
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.default_limit = limit_val
            await db.commit()
    await call.answer(f"Лимит сбора установлен: {limit_val} шт.")
    text = (
        "🗺 <b>Детальные настройки поиска по картам и лидов</b>\n\n"
        "Настройки успешно обновлены."
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=maps_settings_keyboard(settings))

# 3. Настройки Звука и Оповещений
@router.callback_query(F.data == "settings_notif_menu")
async def cb_settings_notif(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    text = (
        "🔔 <b>Настройки звука и сервисных оповещений</b>\n\n"
        "Настройте звук доставки сообщений (тихий режим / обычный) и оповещения при обнаружении капчи:"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=notifications_settings_keyboard(settings))
    await call.answer()

@router.callback_query(F.data == "toggle_notify_sound")
async def cb_toggle_notify_sound(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.notify_sound = not getattr(settings, "notify_sound", True)
            await db.commit()
            val = settings.notify_sound
    st_text = "СО ЗВУКОМ 🔊" if val else "БЕЗ ЗВУКА (Тихий режим) 🔇"
    await call.answer(f"Режим доставки: {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=notifications_settings_keyboard(settings))
    except Exception:
        pass

@router.callback_query(F.data == "toggle_notify_captcha")
async def cb_toggle_notify_captcha(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.notify_captcha = not getattr(settings, "notify_captcha", True)
            await db.commit()
            val = settings.notify_captcha
    st_text = "включены 🟢" if val else "отключены 🔴"
    await call.answer(f"Оповещения о капче {st_text}")
    try:
        await call.message.edit_reply_markup(reply_markup=notifications_settings_keyboard(settings))
    except Exception:
        pass

# 4. Профиль и Сводка
@router.callback_query(F.data == "settings_profile_summary")
async def cb_settings_profile_summary(call: CallbackQuery):
    settings = await get_or_create_user(call.message.chat.id)
    text = format_profile_summary(settings)
    await call.message.answer(text, parse_mode="HTML", reply_markup=settings_menu_keyboard(settings))
    await call.answer()

# 5. Сброс настроек к дефолтным
@router.callback_query(F.data == "settings_reset_defaults")
async def cb_settings_reset_defaults(call: CallbackQuery):
    async with async_session_factory() as db:
        settings = await db.get(TelegramUserSettings, call.message.chat.id)
        if settings:
            settings.fl_enabled = True
            settings.fl_categories = ["2", "5", "7"]
            settings.fl_min_price = 0
            settings.fl_allow_negotiable = True
            settings.fl_hide_pro = False
            settings.fl_urgent_only = False
            settings.fl_keywords = []
            settings.fl_negative_words = []
            settings.maps_enabled = True
            settings.maps_only_with_telegram = True
            settings.maps_source_filter = "all"
            settings.maps_only_without_site = False
            settings.maps_only_without_ssl = False
            settings.notify_sound = True
            settings.notify_captcha = True
            settings.default_limit = 50
            await db.commit()

    await call.answer("✅ Настройки сброшены к стандартным!", show_alert=True)
    text = (
        "⚙️ <b>Центр настроек и расширенной фильтрации</b>\n\n"
        "Все параметры возвращены к исходным значениям по умолчанию."
    )
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=settings_menu_keyboard(settings))
    except Exception:
        pass

# --- УПРАВЛЕНИЕ ПОИСКОМ ПО КАРТАМ ---

@router.callback_query(F.data == "maps_status")
async def cb_maps_status(call: CallbackQuery):
    async with async_session_factory() as db:
        stmt = select(SearchCampaign).order_by(SearchCampaign.id.desc()).limit(1)
        res = await db.execute(stmt)
        campaign = res.scalar_one_or_none()

    if not campaign:
        await call.message.answer("Поисковые кампании еще не запускались.")
    else:
        text = format_campaign_status(campaign.to_summary_dict())
        await call.message.answer(text, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "maps_start")
async def cb_maps_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(SearchCampaignStates.waiting_for_niche)
    await call.message.answer(
        "📝 Введите <b>нишу / сферу бизнеса</b> для поиска (например: <code>Стоматологии</code> или <code>Автосервисы</code>):",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(SearchCampaignStates.waiting_for_niche)
async def state_niche(message: Message, state: FSMContext):
    await state.update_data(niche=message.text.strip())
    await state.set_state(SearchCampaignStates.waiting_for_city)
    await message.answer("📍 Введите <b>город</b> для сбора (например: <code>Казань</code> или <code>Москва</code>):", parse_mode="HTML")

@router.message(SearchCampaignStates.waiting_for_city)
async def state_city(message: Message, state: FSMContext):
    settings = await get_or_create_user(message.chat.id)
    def_limit = getattr(settings, "default_limit", 50)
    await state.update_data(city=message.text.strip(), default_limit=def_limit)
    await state.set_state(SearchCampaignStates.waiting_for_limit)
    await message.answer(f"🔢 Введите <b>лимит организаций</b> (от 10 до 100, по умолчанию {def_limit}):", parse_mode="HTML")

@router.message(SearchCampaignStates.waiting_for_limit)
async def state_limit(message: Message, state: FSMContext):
    data = await state.get_data()
    niche = data.get("niche", "Бизнес")
    city = data.get("city", "Москва")
    def_limit = data.get("default_limit", 50)
    try:
        limit = int(message.text.strip())
        limit = max(10, min(100, limit))
    except ValueError:
        limit = def_limit

    await state.clear()

    settings = await get_or_create_user(message.chat.id)
    source = getattr(settings, "maps_source_filter", "all") or "all"

    # Запускаем через TaskManager
    from app.services.task_manager import TaskManager
    from app.api.search import task_manager

    # Создаем запись кампании
    async with async_session_factory() as db:
        camp = SearchCampaign(
            niche=niche,
            city=city,
            source=source,
            target_limit=limit,
            status="PENDING"
        )
        db.add(camp)
        await db.commit()
        await db.refresh(camp)
        camp_id = camp.id

    task_manager.start_campaign(
        campaign_id=camp_id,
        niche=niche,
        city=city,
        source=source,
        limit=limit
    )

    src_labels = {"all": "Яндекс.Карты + 2ГИС", "yandex": "Яндекс.Карты", "2gis": "2ГИС"}
    src_text = src_labels.get(source, "Яндекс.Карты + 2ГИС")

    await message.answer(
        f"🚀 <b>Сбор лидов успешно запущен!</b>\n\n"
        f"• Ниша: <b>{niche}</b>\n"
        f"• Город: <b>{city}</b>\n"
        f"• Лимит: <b>{limit}</b>\n"
        f"• Источники: <b>{src_text}</b>\n\n"
        f"Новые найденные лиды будут поступать сюда в соответствии с вашими настройками.",
        parse_mode="HTML",
        reply_markup=maps_menu_keyboard()
    )

@router.callback_query(F.data == "maps_stop")
async def cb_maps_stop(call: CallbackQuery):
    from app.api.search import task_manager
    async with async_session_factory() as db:
        stmt = select(SearchCampaign).where(SearchCampaign.status.in_(["RUNNING", "PAUSED_CAPTCHA"])).order_by(SearchCampaign.id.desc()).limit(1)
        res = await db.execute(stmt)
        active_camp = res.scalar_one_or_none()

    if active_camp:
        task_manager.stop_campaign(active_camp.id)
        await call.message.answer(f"⏹ Кампания #{active_camp.id} ({active_camp.niche}) остановлена.")
    else:
        await call.message.answer("Сейчас нет активных запущенных кампаний.")
    await call.answer()

@router.callback_query(F.data.startswith("resolve_captcha_"))
async def cb_resolve_captcha(call: CallbackQuery):
    campaign_id = int(call.data.replace("resolve_captcha_", ""))
    from app.api.search import task_manager
    task_manager.signal_captcha_resolved(campaign_id)
    await call.answer("Сигнал о прохождении капчи передан в браузер!", show_alert=True)
    await call.message.edit_text("✅ Сигнал о решении капчи отправлен. Сбор возобновляется...")
