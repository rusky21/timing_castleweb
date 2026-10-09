import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, update, delete

from app.config import (
    ADMIN_TELEGRAM_IDS, MANAGER_TELEGRAM_CHAT_ID,
    OUTREACH_COMPANY_NAME, OUTREACH_DAILY_LIMIT,
    OUTREACH_WORK_HOURS_START, OUTREACH_WORK_HOURS_END
)
from app.db.database import async_session_factory
from app.db.models import (
    OutreachAccount, OutreachDialog, OutreachMessage,
    OutreachBlacklist, OutreachCampaign, OutreachPrompt,
    DialogStatus, OutreachAccountStatus, utc_now
)
from app.services.deepseek.client import deepseek_client
from app.services.outreach import (
    screenshot_service, pitch_generator, session_manager,
    intent_classifier, dialog_engine, followup_worker,
    get_prompt, set_prompt, reset_prompt_to_default
)
from app.core.env_editor import ENV_META, get_env_value, set_env_value

logger = logging.getLogger("admin_bot")
admin_router = Router(name="outreach_admin")


# ====================================================================
# FSM Состояния для пошаговых сценариев
# ====================================================================

class AdminStates(StatesGroup):
    # Тестовый аутрич
    test_waiting_username = State()
    test_waiting_url = State()
    test_waiting_company = State()
    test_confirm = State()
    test_sim_custom = State()

    # Добавление аккаунта
    acc_add_phone = State()
    acc_add_proxy = State()
    acc_add_code = State()
    acc_add_2fa = State()

    # Создание кампании
    camp_city = State()
    camp_niche = State()
    camp_limit = State()

    # Редактирование промпта
    prompt_select = State()
    prompt_edit_text = State()

    # Песочница
    sandbox_active = State()

    # Ручной ответ в диалог
    dialog_manual_reply = State()

    # Черный список
    bl_add = State()

    # Настройки .env
    env_edit_key = State()
    env_edit_value = State()


# ====================================================================
# Middleware / Проверка прав администратора
# ====================================================================

def is_admin(user_id: int) -> bool:
    if not ADMIN_TELEGRAM_IDS:
        # Если список админов пуст — разрешаем первому обратившемуся для удобства настройки
        return True
    return user_id in ADMIN_TELEGRAM_IDS


@admin_router.message.outer_middleware
async def admin_auth_middleware(handler, event: Message, data: dict):
    if not is_admin(event.from_user.id):
        # Неавторизованный пользователь игнорируется
        return
    return await handler(event, data)


@admin_router.callback_query.outer_middleware
async def admin_auth_cb_middleware(handler, event: CallbackQuery, data: dict):
    if not is_admin(event.from_user.id):
        await event.answer("⛔ Доступ ограничен.", show_alert=True)
        return
    return await handler(event, data)


# ====================================================================
# Главное меню (/menu, /start, /outreach)
# ====================================================================

def get_main_menu_keyboard(is_paused: bool = False) -> InlineKeyboardMarkup:
    pause_text = "▶️ Возобновить всё" if is_paused else "⏸ Пауза (Kill Switch)"
    pause_cb = "outreach_resume_all" if is_paused else "outreach_pause_all"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Аналитика", callback_data="menu_stats"),
            InlineKeyboardButton(text="👥 Аккаунты", callback_data="menu_accounts"),
        ],
        [
            InlineKeyboardButton(text="💬 Диалоги", callback_data="menu_dialogs"),
            InlineKeyboardButton(text="🧪 Тестовый аутрич", callback_data="menu_test"),
        ],
        [
            InlineKeyboardButton(text="🎯 Кампании", callback_data="menu_campaigns"),
            InlineKeyboardButton(text="📝 Промпты", callback_data="menu_prompts"),
        ],
        [
            InlineKeyboardButton(text="🚫 Черный список", callback_data="menu_blacklist"),
            InlineKeyboardButton(text="🧠 Песочница", callback_data="menu_sandbox"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки .env", callback_data="menu_settings"),
            InlineKeyboardButton(text="🏥 Здоровье системы", callback_data="menu_health"),
        ],
        [
            InlineKeyboardButton(text=pause_text, callback_data=pause_cb),
        ]
    ])



@admin_router.message(Command("menu", "outreach"))
@admin_router.message(Command("start"), F.text.contains("outreach"))
async def cmd_main_menu(message: Message, state: FSMContext):
    await state.clear()
    async with async_session_factory() as session:
        acc_total = (await session.execute(select(func.count(OutreachAccount.id)))).scalar_one()
        acc_active = (await session.execute(
            select(func.count(OutreachAccount.id)).where(OutreachAccount.status == OutreachAccountStatus.ACTIVE)
        )).scalar_one()
        sent_today = (await session.execute(select(func.coalesce(func.sum(OutreachAccount.sent_today), 0)))).scalar_one()
        active_dialogs = (await session.execute(
            select(func.count(OutreachDialog.id)).where(OutreachDialog.status.in_([DialogStatus.PITCH_SENT, DialogStatus.QUALIFYING, DialogStatus.REPLIED]))
        )).scalar_one()
        needs_human = (await session.execute(
            select(func.count(OutreachDialog.id)).where(OutreachDialog.status == DialogStatus.NEEDS_HUMAN)
        )).scalar_one()

    is_paused = followup_worker.is_paused
    status_emoji = "⏸ На паузе" if is_paused else "🟢 Активна"

    text = (
        f"🏠 <b>ПАНЕЛЬ УПРАВЛЕНИЯ AI SDR ({OUTREACH_COMPANY_NAME})</b>\n\n"
        f"<b>Статус системы:</b> {status_emoji}\n"
        f"<b>Аккаунтов в пуле:</b> {acc_active}/{acc_total}\n"
        f"<b>Отправлено сегодня:</b> {sent_today}\n"
        f"<b>Активных диалогов:</b> {active_dialogs}\n"
        f"<b>Ожидают менеджера (P0):</b> <b>{needs_human}</b> 🔥\n\n"
        f"<i>Выберите нужный раздел для управления:</i>"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(is_paused), parse_mode="HTML")


@admin_router.callback_query(F.data == "menu_main")
async def cb_main_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    is_paused = followup_worker.is_paused
    status_emoji = "⏸ На паузе" if is_paused else "🟢 Активна"

    async with async_session_factory() as session:
        acc_total = (await session.execute(select(func.count(OutreachAccount.id)))).scalar_one()
        acc_active = (await session.execute(
            select(func.count(OutreachAccount.id)).where(OutreachAccount.status == OutreachAccountStatus.ACTIVE)
        )).scalar_one()
        sent_today = (await session.execute(select(func.coalesce(func.sum(OutreachAccount.sent_today), 0)))).scalar_one()
        active_dialogs = (await session.execute(
            select(func.count(OutreachDialog.id)).where(OutreachDialog.status.in_([DialogStatus.PITCH_SENT, DialogStatus.QUALIFYING, DialogStatus.REPLIED]))
        )).scalar_one()
        needs_human = (await session.execute(
            select(func.count(OutreachDialog.id)).where(OutreachDialog.status == DialogStatus.NEEDS_HUMAN)
        )).scalar_one()

    text = (
        f"🏠 <b>ПАНЕЛЬ УПРАВЛЕНИЯ AI SDR ({OUTREACH_COMPANY_NAME})</b>\n\n"
        f"<b>Статус системы:</b> {status_emoji}\n"
        f"<b>Аккаунтов в пуле:</b> {acc_active}/{acc_total}\n"
        f"<b>Отправлено сегодня:</b> {sent_today}\n"
        f"<b>Активных диалогов:</b> {active_dialogs}\n"
        f"<b>Ожидают менеджера (P0):</b> <b>{needs_human}</b> 🔥"
    )
    try:
        await call.message.edit_text(text, reply_markup=get_main_menu_keyboard(is_paused), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=get_main_menu_keyboard(is_paused), parse_mode="HTML")
    await call.answer()


# ====================================================================
# 1. Управление аккаунтами (/accounts, /account_add)
# ====================================================================

@admin_router.message(Command("accounts"))
@admin_router.callback_query(F.data == "menu_accounts")
async def show_accounts_list(event: Message | CallbackQuery):
    message = event if isinstance(event, Message) else event.message
    async with async_session_factory() as session:
        accounts = (await session.execute(select(OutreachAccount).order_by(OutreachAccount.id.asc()))).scalars().all()

    if not accounts:
        text = "👥 <b>Рабочие аккаунты MTProto</b>\n\nВ базе пока нет добавленных аккаунтов."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="acc_add_start")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")]
        ])
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await event.answer()
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    text = f"👥 <b>Рабочие аккаунты MTProto ({len(accounts)}):</b>\n\n"
    buttons = []

    for a in accounts:
        st_emoji = "🟢" if a.status == OutreachAccountStatus.ACTIVE else "🟡" if a.status == OutreachAccountStatus.WARMUP else "🔴"
        prem = "⭐ Premium" if a.is_premium else ""
        text += (
            f"📱 <b>Аккаунт #{a.id}:</b> <code>{a.phone}</code> {prem}\n"
            f"├ Статус: {st_emoji} {a.status}\n"
            f"├ Отправлено сегодня: <b>{a.sent_today}/{a.daily_limit}</b>\n"
            f"├ Прокси: {a.proxy_url or 'Прямое подключение'}\n"
            f"└ Прогрев: Этап {a.warmup_stage}/4\n\n"
        )
        buttons.append([
            InlineKeyboardButton(text=f"🔍 SpamBot #{a.id}", callback_data=f"acc_spambot_{a.id}"),
            InlineKeyboardButton(text=f"⏸/▶️ #{a.id}", callback_data=f"acc_toggle_{a.id}"),
            InlineKeyboardButton(text=f"🗑 Удалить #{a.id}", callback_data=f"acc_del_{a.id}")
        ])

    buttons.append([InlineKeyboardButton(text="➕ Добавить новый аккаунт", callback_data="acc_add_start")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("acc_spambot_"))
async def cb_account_spambot(call: CallbackQuery):
    acc_id = int(call.data.replace("acc_spambot_", ""))
    await call.answer("Проверяем @SpamBot...", show_alert=False)
    res = await session_manager.check_spambot(acc_id)
    if res.get("ok"):
        reply = res.get("bot_reply", "").strip() or "Ограничений нет."
        status_txt = "🟢 Чист (ACTIVE)" if res.get("is_clean") else "🔴 Есть ограничения (SPAMBLOCKED)"
        await call.message.answer(
            f"🔍 <b>Результат проверки @SpamBot для аккаунта #{acc_id}:</b>\n\n"
            f"Статус: {status_txt}\n\n"
            f"<i>Ответ бота:</i>\n«{reply}»",
            parse_mode="HTML"
        )
    else:
        await call.message.answer(f"⚠️ Ошибка проверки SpamBot: {res.get('message')}")


@admin_router.callback_query(F.data.startswith("acc_toggle_"))
async def cb_account_toggle(call: CallbackQuery):
    acc_id = int(call.data.replace("acc_toggle_", ""))
    async with async_session_factory() as session:
        acc = (await session.execute(select(OutreachAccount).where(OutreachAccount.id == acc_id))).scalar_one_or_none()
        if acc:
            new_status = OutreachAccountStatus.DISABLED if acc.status == OutreachAccountStatus.ACTIVE else OutreachAccountStatus.ACTIVE
            acc.status = new_status
            await session.commit()
            await call.answer(f"Статус изменен на {new_status}", show_alert=True)
            await show_accounts_list(call)


@admin_router.callback_query(F.data.startswith("acc_del_"))
async def cb_account_delete(call: CallbackQuery):
    acc_id = int(call.data.replace("acc_del_", ""))
    async with async_session_factory() as session:
        await session.execute(delete(OutreachAccount).where(OutreachAccount.id == acc_id))
        await session.commit()
    await call.answer(f"Аккаунт #{acc_id} удален.", show_alert=True)
    await show_accounts_list(call)


# Пошаговое добавление аккаунта (FSM)
@admin_router.message(Command("account_add"))
@admin_router.callback_query(F.data == "acc_add_start")
async def start_add_account(event: Message | CallbackQuery, state: FSMContext):
    message = event if isinstance(event, Message) else event.message
    await state.set_state(AdminStates.acc_add_phone)
    text = (
        "➕ <b>Добавление рабочего MTProto-аккаунта</b>\n\n"
        "Отправьте номер телефона в международном формате (например, <code>+79991234567</code>):"
    )
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, parse_mode="HTML")
        except Exception:
            pass
        await event.answer()
    else:
        await message.answer(text, parse_mode="HTML")


@admin_router.message(AdminStates.acc_add_phone)
async def process_acc_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(AdminStates.acc_add_proxy)
    await message.answer(
        "🔌 <b>Настройка прокси</b>\n\n"
        "Отправьте строку прокси (например, <code>socks5://user:pass@host:port</code>)\n"
        "или отправьте <code>-</code> (прочерк), если прокси не требуется (или включен системный VPN):",
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.acc_add_proxy)
async def process_acc_proxy(message: Message, state: FSMContext):
    proxy_str = message.text.strip()
    proxy_url = None if proxy_str in ("-", "нет", "no") else proxy_str
    if proxy_url and "workers.dev" in proxy_url:
        await message.answer(
            "ℹ️ <b>Cloudflare Worker уже активен для Telegram Bot API!</b>\n\n"
            "Но для авторизации аккаунта <b>Userbot (Telethon)</b> требуется прямое TCP-подключение к серверам Telegram MTProto (воркер Cloudflare является HTTP-прокси, а не SOCKS5 TCP туннелем).\n\n"
            "• Включите <b>системный VPN</b> на 1 минуту и отправьте <code>-</code> (прочерк), либо\n"
            "• Укажите SOCKS5 прокси (например: <code>socks5://127.0.0.1:10808</code>).\n\n"
            "💡 <i>Вы также можете протестировать работу ИИ прямо сейчас без аккаунта: нажмите /test и выберите «Запустить интерактивную симуляцию»!</i>",
            parse_mode="HTML"
        )
        return

    await state.update_data(proxy_url=proxy_url)

    data = await state.get_data()
    phone = data["phone"]

    msg_wait = await message.answer("⏳ Подключаемся к Telegram и запрашиваем код подтверждения...")
    ok, hash_or_err, clean_phone = await session_manager.request_login_code(phone, proxy_url)

    if not ok:
        err_msg = hash_or_err
        if "timeout" in err_msg.lower() or "connection" in err_msg.lower():
            err_msg = (
                "Таймаут соединения с серверами Telegram MTProto.\n\n"
                "💡 <i>В РФ прямое подключение к IP Telegram блокируется провайдерами без VPN/прокси.</i>\n"
                "• Включите <b>VPN</b> на компьютере, либо\n"
                "• Укажите SOCKS5 прокси при добавлении аккаунта (например: <code>socks5://127.0.0.1:10808</code> или мобильный прокси)."
            )
        await msg_wait.edit_text(
            f"❌ <b>Ошибка отправки кода:</b>\n{err_msg}\n\nПопробуйте снова с /account_add",
            parse_mode="HTML"
        )
        await state.clear()
        return

    await state.update_data(phone_code_hash=hash_or_err, phone=clean_phone)
    await state.set_state(AdminStates.acc_add_code)
    await msg_wait.edit_text(
        f"📩 <b>Код подтверждения отправлен на номер {clean_phone}</b>\n\n"
        f"Введите полученный 5-значный код из Telegram (можно через пробел: <code>1 2 3 4 5</code>).\n\n"
        f"⚠️ <b>ВНИМАНИЕ (Анти-фишинг защита Telegram):</b>\n"
        f"Если вы привязываете <b>тот же самый аккаунт</b>, с которого сейчас пишете боту — <b>НЕ отправляйте код в этот чат</b>! "
        f"Telegram перехватит его и заблокирует вход с системным сообщением <i>«Вход заблокирован, поскольку ранее Вы сообщили этот код со своего аккаунта»</i>.\n\n"
        f"💡 <b>Для безопасной привязки своего аккаунта:</b>\n"
        f"Запустите на компьютере утилиту: <code>login_account.bat</code> (или команду <code>python login_account.py</code>).\n"
        f"<i>(Через бота привязывайте только сторонние рабочие аккаунты, с которых вы не ведете этот диалог)</i>",
        parse_mode="HTML"
    )


@admin_router.message(AdminStates.acc_add_code)
async def process_acc_code(message: Message, state: FSMContext):
    code = message.text.strip().replace(" ", "")
    data = await state.get_data()
    phone = data["phone"]
    phone_code_hash = data["phone_code_hash"]
    proxy_url = data.get("proxy_url")

    ok, res_str, acc_id = await session_manager.complete_login_with_code(
        phone=phone, code=code, phone_code_hash=phone_code_hash, proxy_url=proxy_url
    )

    if not ok and res_str == "NEEDS_2FA":
        await state.update_data(code=code)
        await state.set_state(AdminStates.acc_add_2fa)
        await message.answer("🔐 На аккаунте установлен пароль двухфакторной аутентификации (2FA).\nВведите пароль:")
        return

    if ok:
        await message.answer(f"🎉 <b>Успех!</b> Аккаунт #{acc_id} успешно авторизован и сохранен в пуле!", parse_mode="HTML")
        await state.clear()
        await show_accounts_list(message)
    else:
        err_hint = ""
        if "code" in res_str.lower() or "invalid" in res_str.lower() or "expired" in res_str.lower():
            err_hint = (
                "\n\n💡 <i>Если Telegram прислал уведомление «Вход заблокирован, так как вы сообщили этот код со своего аккаунта» — "
                "используйте прямой консольный вход: запустите <code>login_account.bat</code> на ПК.</i>"
            )
        await message.answer(f"❌ {res_str}{err_hint}\n\nПопробуйте заново: /account_add", parse_mode="HTML")
        await state.clear()


@admin_router.message(AdminStates.acc_add_2fa)
async def process_acc_2fa(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    phone = data["phone"]
    code = data["code"]
    phone_code_hash = data["phone_code_hash"]
    proxy_url = data.get("proxy_url")

    ok, res_str, acc_id = await session_manager.complete_login_with_code(
        phone=phone, code=code, phone_code_hash=phone_code_hash, password_2fa=password, proxy_url=proxy_url
    )
    if ok:
        await message.answer(f"🎉 <b>Успех!</b> Аккаунт #{acc_id} успешно авторизован и сохранен в пуле!", parse_mode="HTML")
        await state.clear()
        await show_accounts_list(message)
    else:
        await message.answer(f"❌ Ошибка 2FA: {res_str}")
        await state.clear()


# ====================================================================
# 2. Сквозной ручной тест (/test @username https://site.com)
# ====================================================================

@admin_router.message(Command("test"))
@admin_router.callback_query(F.data == "menu_test")
async def cmd_test_outreach(event: Message | CallbackQuery, state: FSMContext):
    message = event if isinstance(event, Message) else event.message
    # Проверка формата /test @username url [company]
    if isinstance(event, Message):
        parts = message.text.strip().split(maxsplit=3)
        if len(parts) >= 3:
            username = parts[1]
            url = parts[2]
            company = parts[3] if len(parts) > 3 else "Тестовая компания"
            await run_test_pipeline(message, username, url, company, state)
            return

    await state.set_state(AdminStates.test_waiting_username)
    text = (
        "🧪 <b>ТЕСТОВЫЙ АУТРИЧ (EXPRESS-RUN)</b>\n\n"
        "Шаг 1 из 3: Отправьте <b>@username</b> или телефон получателя:"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text, parse_mode="HTML")


@admin_router.message(AdminStates.test_waiting_username)
async def process_test_user(message: Message, state: FSMContext):
    user_str = message.text.strip()
    await state.update_data(username=user_str)
    await state.set_state(AdminStates.test_waiting_url)
    await message.answer("Шаг 2 из 3: Отправьте <b>URL сайта</b> (например, <code>https://example.com</code>):", parse_mode="HTML")


@admin_router.message(AdminStates.test_waiting_url)
async def process_test_url(message: Message, state: FSMContext):
    url = message.text.strip()
    await state.update_data(url=url)
    await state.set_state(AdminStates.test_waiting_company)
    await message.answer("Шаг 3 из 3: Название компании (например, <code>Автосервис Профи</code>):", parse_mode="HTML")


@admin_router.message(AdminStates.test_waiting_company)
async def process_test_company(message: Message, state: FSMContext):
    company = message.text.strip()
    data = await state.get_data()
    await run_test_pipeline(message, data["username"], data["url"], company, state)


async def run_test_pipeline(message: Message, username: str, url: str, company: str, state: FSMContext):
    wait_msg = await message.answer(
        "⏳ <b>Запуск пайплайна тестирования...</b>\n"
        "1. Эмуляция экрана iPhone 13 и захват пруфа...\n"
        "2. Анализ дефекта и генерация питча CastleWeb...",
        parse_mode="HTML"
    )

    # 1. Скриншот через Playwright
    screenshot_path = await screenshot_service.capture_mobile_defect(url)

    # 2. Генерация первого питча через DeepSeek (или fallback)
    pitch_text, issue_summary = await pitch_generator.generate(
        company_name=company,
        city="Москва",
        website_url=url,
        audit_data={"pitch_pain": "Сдвиг кнопки заявки", "is_adaptive": False}
    )

    # Выбор рабочего аккаунта
    account = await session_manager.pick_best_account()
    acc_info = f"#{account.id} ({account.phone})" if account else "❌ Нет активных аккаунтов в пуле"

    await state.update_data(
        target_username=username,
        target_url=url,
        company=company,
        pitch_text=pitch_text,
        screenshot_path=screenshot_path,
        account_id=account.id if account else None
    )
    await state.set_state(AdminStates.test_confirm)

    card_text = (
        f"🧪 <b>ПРЕВЬЮ ТЕСТОВОГО АУТРИЧА</b>\n\n"
        f"👤 <b>Получатель:</b> <code>{username}</code>\n"
        f"🌐 <b>Сайт:</b> {url}\n"
        f"🏢 <b>Компания:</b> {company}\n"
        f"📱 <b>Рабочий аккаунт:</b> {acc_info}\n\n"
        f"💬 <b>Текст питча (CastleWeb):</b>\n"
        f"<i>«{pitch_text}»</i>\n\n"
        f"🖼 <b>Скриншот дефекта:</b> {'Готов к отправке ✅' if screenshot_path else 'Не удалось сделать ⚠️'}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отправить через аккаунт", callback_data="test_send_now")],
        [InlineKeyboardButton(text="🧪 Запустить симуляцию диалога", callback_data="test_sim_start")],
        [InlineKeyboardButton(text="🔄 Перегенерировать питч", callback_data="test_regen")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_main")]
    ])

    try:
        await wait_msg.delete()
    except Exception:
        pass

    # Текстовое превью гарантированно и мгновенно доставляется через Cloudflare Worker
    await message.answer(card_text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data == "test_regen", AdminStates.test_confirm)
async def cb_test_regen(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    company = data.get("company", "Тестовая компания")
    url = data.get("target_url", "https://example.com")
    username = data.get("target_username", "@test")
    await call.answer("Генерируем новый вариант питча...", show_alert=False)
    pitch_text, _ = await pitch_generator.generate(
        company_name=company,
        city="Москва",
        website_url=url,
        audit_data={"pitch_pain": "Сдвиг верстки формы заявки", "is_adaptive": False}
    )
    await state.update_data(pitch_text=pitch_text)

    acc_id = data.get("account_id")
    acc_info = f"#{acc_id}" if acc_id else "❌ Нет активных аккаунтов в пуле"
    card_text = (
        f"🧪 <b>ПРЕВЬЮ ТЕСТОВОГО АУТРИЧА (ОБНОВЛЕНО)</b>\n\n"
        f"👤 <b>Получатель:</b> <code>{username}</code>\n"
        f"🌐 <b>Сайт:</b> {url}\n"
        f"🏢 <b>Компания:</b> {company}\n"
        f"📱 <b>Рабочий аккаунт:</b> {acc_info}\n\n"
        f"💬 <b>Новый текст питча (CastleWeb):</b>\n"
        f"<i>«{pitch_text}»</i>\n\n"
        f"🖼 <b>Скриншот дефекта:</b> {'Готов к отправке ✅' if data.get('screenshot_path') else 'Не удалось сделать ⚠️'}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Отправить через аккаунт", callback_data="test_send_now")],
        [InlineKeyboardButton(text="🧪 Запустить симуляцию диалога", callback_data="test_sim_start")],
        [InlineKeyboardButton(text="🔄 Еще вариант", callback_data="test_regen")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_main")]
    ])
    try:
        await call.message.edit_text(card_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await call.message.answer(card_text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data == "test_send_now", AdminStates.test_confirm)
async def cb_test_send(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    acc_id = data.get("account_id")
    target = data.get("target_username")
    pitch_text = data.get("pitch_text")
    screenshot_path = data.get("screenshot_path")
    company = data.get("company")
    url = data.get("target_url")

    if not acc_id:
        kb_no_acc = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧪 Запустить демо-симуляцию диалога", callback_data="test_sim_start")],
            [InlineKeyboardButton(text="➕ Подключить аккаунт сейчас", callback_data="acc_add_start")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")]
        ])
        await call.message.answer(
            "⚠️ <b>В пуле нет подключенных Userbot-аккаунтов!</b>\n\n"
            "Вы можете:\n"
            "1. <b>Запустить интерактивную симуляцию</b> прямо сейчас (без аккаунта) — проверить реакцию ИИ DeepSeek на любые ответы клиента!\n"
            "2. Либо подключить реальный Telegram-аккаунт через «➕ Подключить аккаунт».",
            reply_markup=kb_no_acc,
            parse_mode="HTML"
        )
        await call.answer()
        return

    await call.answer("Отправляем через Userbot...", show_alert=False)

    try:
        # Отправка через MTProto
        msg_id = await session_manager.send_message_safe(
            account_id=acc_id,
            recipient=target,
            text=pitch_text,
            simulate_typing=True
        )

        # Сохранение диалога в БД как тестового
        async with async_session_factory() as session:
            dialog = OutreachDialog(
                account_id=acc_id,
                client_tg_username=target.lstrip("@"),
                company_name=company,
                website_url=url,
                pitch_text=pitch_text,
                defect_screenshot_path=screenshot_path,
                pitch_sent_at=utc_now(),
                status=DialogStatus.PITCH_SENT,
                is_test=True
            )
            session.add(dialog)
            await session.commit()
            await session.refresh(dialog)

            session.add(OutreachMessage(
                dialog_id=dialog.id,
                sender_type="bot",
                message_text=pitch_text,
                tg_message_id=msg_id
            ))
            await session.commit()
            dialog_id = dialog.id

        await call.message.answer(
            f"✅ <b>Сообщение успешно доставлено!</b>\n\n"
            f"Диалог #{dialog_id} создан и отслеживается системой.\n"
            f"Когда клиент ответит, вы получите live-уведомление прямо сюда!",
            parse_mode="HTML"
        )
        await state.clear()

    except Exception as e:
        await call.message.answer(f"❌ Ошибка отправки через MTProto: {e}")


# ====================================================================
# Интерактивная симуляция диалога (Без MTProto-аккаунта)
# ====================================================================

SIM_PRESETS = {
    "price": "Сколько будет стоить исправить и какие сроки?",
    "proof": "Скиньте скриншот, где именно проблема? С компьютера все работает.",
    "lead": "Да, давайте обсудим. Перезвоните мне +7 999 123-45-67, я директор.",
    "cases": "А какие сайты вы делали? Покажите примеры работ или кейсы.",
    "bot": "Вы робот или живой человек? Откуда у вас этот контакт вообще?",
    "stop": "Нам это не интересно, у нас свой разработчик, не пишите больше.",
}


def get_sim_keyboard(dialog_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 «Сколько стоит?»", callback_data=f"sim_act_{dialog_id}_price"),
            InlineKeyboardButton(text="🖼 «Скиньте скриншот»", callback_data=f"sim_act_{dialog_id}_proof"),
        ],
        [
            InlineKeyboardButton(text="📞 «Мой номер: +79991234567»", callback_data=f"sim_act_{dialog_id}_lead"),
            InlineKeyboardButton(text="💼 «Покажите кейсы»", callback_data=f"sim_act_{dialog_id}_cases"),
        ],
        [
            InlineKeyboardButton(text="🤖 «Вы робот?»", callback_data=f"sim_act_{dialog_id}_bot"),
            InlineKeyboardButton(text="🚫 «Не интересно»", callback_data=f"sim_act_{dialog_id}_stop"),
        ],
        [
            InlineKeyboardButton(text="✏️ Написать свой ответ (произвольный текст)", callback_data=f"sim_custom_{dialog_id}"),
        ],
        [
            InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")
        ]
    ])


async def show_simulation_dialog(message: Message, dialog_id: int, company: str, url: str, pitch_text: str):
    text = (
        f"🧪 <b>ИНТЕРАКТИВНАЯ СИМУЛЯЦИЯ ДИАЛОГА #{dialog_id}</b>\n\n"
        f"🏢 <b>Компания:</b> {company}\n"
        f"🌐 <b>Сайт:</b> {url}\n\n"
        f"🤖 <b>Отправленный питч (CastleWeb):</b>\n"
        f"<i>«{pitch_text}»</i>\n\n"
        f"💡 <i>Выберите ответ клиента ниже или отправьте произвольное сообщение:</i>"
    )
    try:
        await message.edit_text(text, reply_markup=get_sim_keyboard(dialog_id), parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=get_sim_keyboard(dialog_id), parse_mode="HTML")


@admin_router.callback_query(F.data == "test_sim_start")
async def cb_test_sim_start(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    company = data.get("company") or "Тестовая компания"
    url = data.get("target_url") or "https://example.com"
    username = data.get("target_username") or "test_client"
    pitch_text = data.get("pitch_text") or "Здравствуйте! Заметил, что на сайте с мобильного съехала форма заявки. Подсказать где именно?"
    screenshot_path = data.get("screenshot_path")
    acc_id = data.get("account_id")

    async with async_session_factory() as session:
        dialog = OutreachDialog(
            account_id=acc_id,
            client_tg_username=username.lstrip("@"),
            company_name=company,
            website_url=url,
            pitch_text=pitch_text,
            defect_screenshot_path=screenshot_path,
            pitch_sent_at=utc_now(),
            status=DialogStatus.PITCH_SENT,
            is_test=True
        )
        session.add(dialog)
        await session.commit()
        await session.refresh(dialog)

        session.add(OutreachMessage(
            dialog_id=dialog.id,
            sender_type="bot",
            message_text=pitch_text,
            tg_message_id=None
        ))
        await session.commit()
        dialog_id = dialog.id

    await state.clear()
    await call.answer("Запуск симуляции...", show_alert=False)
    await show_simulation_dialog(call.message, dialog_id, company, url, pitch_text)


@admin_router.callback_query(F.data.startswith("sim_act_"))
async def cb_sim_action(call: CallbackQuery):
    parts = call.data.split("_")
    dialog_id = int(parts[2])
    action_key = parts[3]
    incoming_text = SIM_PRESETS.get(action_key, "Здравствуйте")

    await call.answer("DeepSeek анализирует интент и готовит ответ...", show_alert=False)

    res = await dialog_engine.process_simulated_reply(dialog_id, incoming_text)
    intent = res.get("intent", "UNKNOWN")
    confidence = res.get("confidence", 0.8)
    bot_reply = res.get("bot_reply")
    is_p0 = res.get("p0_triggered", False)

    status_badge = "🔥 <b>[P0 ЭСКАЛАЦИЯ МЕНЕДЖЕРУ!]</b>" if is_p0 else f"🧠 Интент: <code>{intent}</code> ({confidence:.0%})"

    result_text = (
        f"🧪 <b>СИМУЛЯЦИЯ ДИАЛОГА #{dialog_id}</b>\n\n"
        f"👤 <b>Клиент ответил:</b>\n"
        f"«{incoming_text}»\n\n"
        f"{status_badge}\n\n"
    )

    if is_p0:
        result_text += (
            f"⚡ <b>ИИ остановил автоответы!</b> Диалог переведен в статус <code>NEEDS_HUMAN</code>.\n"
            f"Менеджер получил мгновенный звуковой P0-алерт с кнопкой «Забрать в работу»."
        )
    elif bot_reply:
        result_text += (
            f"🤖 <b>Ответ CastleWeb (ИИ):</b>\n"
            f"<i>«{bot_reply}»</i>\n\n"
            f"Статус диалога: <code>{res.get('status')}</code>"
        )
    else:
        result_text += f"<i>Сообщение зафиксировано. Диалог в статусе {res.get('status')}</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Отправить еще ответ клиента", callback_data=f"sim_continue_{dialog_id}")],
        [InlineKeyboardButton(text="👁 Открыть диалог в CRM", callback_data=f"dlg_view_{dialog_id}")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")]
    ])

    await call.message.answer(result_text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("sim_custom_"))
async def cb_sim_custom(call: CallbackQuery, state: FSMContext):
    dialog_id = int(call.data.replace("sim_custom_", ""))
    await state.update_data(sim_dialog_id=dialog_id)
    await state.set_state(AdminStates.test_sim_custom)
    await call.message.answer(
        f"✍️ <b>Произвольный ответ клиента для диалога #{dialog_id}</b>\n\n"
        f"Напишите любое сообщение от лица клиента (возражение, каверзный вопрос, мат, попытку сбить цену):\n\n"
        f"<i>ИИ DeepSeek в реальном времени классифицирует интент и сформулирует ответ по стандартам CastleWeb.</i>",
        parse_mode="HTML"
    )
    await call.answer()


@admin_router.message(AdminStates.test_sim_custom)
async def process_sim_custom_text(message: Message, state: FSMContext):
    data = await state.get_data()
    dialog_id = data.get("sim_dialog_id")
    incoming_text = message.text.strip()
    await state.clear()

    wait_msg = await message.answer("🧠 <i>DeepSeek анализирует сообщение...</i>", parse_mode="HTML")

    res = await dialog_engine.process_simulated_reply(dialog_id, incoming_text)
    try:
        await wait_msg.delete()
    except Exception:
        pass

    intent = res.get("intent", "UNKNOWN")
    confidence = res.get("confidence", 0.8)
    bot_reply = res.get("bot_reply")
    is_p0 = res.get("p0_triggered", False)

    status_badge = "🔥 <b>[P0 ЭСКАЛАЦИЯ МЕНЕДЖЕРУ!]</b>" if is_p0 else f"🧠 Интент: <code>{intent}</code> ({confidence:.0%})"

    result_text = (
        f"🧪 <b>СИМУЛЯЦИЯ ДИАЛОГА #{dialog_id}</b>\n\n"
        f"👤 <b>Клиент написал:</b>\n«{incoming_text}»\n\n"
        f"{status_badge}\n\n"
    )

    if is_p0:
        result_text += (
            f"⚡ <b>ИИ остановил автоответы!</b> Диалог переведен в статус <code>NEEDS_HUMAN</code>.\n"
            f"Лид передан в чат менеджеров для закрытия сделки."
        )
    elif bot_reply:
        result_text += (
            f"🤖 <b>Ответ CastleWeb (ИИ):</b>\n<i>«{bot_reply}»</i>\n\n"
            f"Статус диалога: <code>{res.get('status')}</code>"
        )
    else:
        result_text += f"<i>Сообщение зафиксировано. Диалог в статусе {res.get('status')}</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Отправить еще ответ клиента", callback_data=f"sim_continue_{dialog_id}")],
        [InlineKeyboardButton(text="👁 Открыть диалог в CRM", callback_data=f"dlg_view_{dialog_id}")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")]
    ])

    await message.answer(result_text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("sim_continue_"))
async def cb_sim_continue(call: CallbackQuery):
    dialog_id = int(call.data.replace("sim_continue_", ""))
    async with async_session_factory() as session:
        dialog = (await session.execute(
            select(OutreachDialog).where(OutreachDialog.id == dialog_id)
        )).scalar_one_or_none()

    if dialog:
        await show_simulation_dialog(
            call.message, dialog_id,
            dialog.company_name or "Компания",
            dialog.website_url or "Сайт",
            dialog.pitch_text
        )
    else:
        await call.answer("Диалог не найден", show_alert=True)


# ====================================================================
# 3. Мониторинг диалогов (/dialogs)
# ====================================================================

@admin_router.message(Command("dialogs"))
@admin_router.callback_query(F.data == "menu_dialogs")
async def show_dialogs_list(event: Message | CallbackQuery):
    message = event if isinstance(event, Message) else event.message
    async with async_session_factory() as session:
        dialogs = (await session.execute(
            select(OutreachDialog).order_by(OutreachDialog.updated_at.desc()).limit(10)
        )).scalars().all()

    if not dialogs:
        text = "💬 <b>Диалоги аутрича</b>\n\nАктивных диалогов пока нет."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")]])
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await event.answer()
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        return

    text = f"💬 <b>Последние диалоги ({len(dialogs)}):</b>\n\n"
    buttons = []

    for d in dialogs:
        st_badge = "🔥 ЖДЕТ ЧЕЛОВЕКА" if d.status == DialogStatus.NEEDS_HUMAN else d.status
        user = f"@{d.client_tg_username}" if d.client_tg_username else f"ID {d.client_tg_id}"
        comp = d.company_name or "Компания"
        text += (
            f"<b>Диалог #{d.id}:</b> {comp} ({user})\n"
            f"├ Статус: <b>{st_badge}</b>\n"
            f"├ ИИ: {'🛑 Заблокирован' if d.ai_locked else '🤖 Автоответ'}\n"
            f"└ Интент: {d.last_intent or 'Нет'}\n\n"
        )
        buttons.append([
            InlineKeyboardButton(text=f"👁 Чат #{d.id}", callback_data=f"dlg_view_{d.id}"),
            InlineKeyboardButton(text=f"🛑 Забрать #{d.id}", callback_data=f"dlg_takeover_{d.id}")
        ])

    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("dlg_view_"))
async def cb_view_dialog(call: CallbackQuery):
    dlg_id = int(call.data.replace("dlg_view_", ""))
    async with async_session_factory() as session:
        dlg = (await session.execute(select(OutreachDialog).where(OutreachDialog.id == dlg_id))).scalar_one_or_none()
        if not dlg:
            await call.answer("Диалог не найден", show_alert=True)
            return

        msgs = (await session.execute(
            select(OutreachMessage).where(OutreachMessage.dialog_id == dlg_id).order_by(OutreachMessage.sent_at.asc())
        )).scalars().all()

    user_link = f"https://t.me/{dlg.client_tg_username}" if dlg.client_tg_username else f"tg://user?id={dlg.client_tg_id}"
    history_lines = ""
    for m in msgs[-8:]:
        prefix = "🤖 Бот" if m.sender_type == "bot" else "👤 Клиент" if m.sender_type == "client" else "👨‍💼 Менеджер"
        history_lines += f"<b>{prefix}:</b> {m.message_text}\n\n"

    text = (
        f"💬 <b>КАРТОЧКА ДИАЛОГА #{dlg.id}</b>\n\n"
        f"🏢 <b>Компания:</b> {dlg.company_name or '—'}\n"
        f"👤 <b>Контакт:</b> <a href='{user_link}'>@{dlg.client_tg_username or dlg.client_tg_id}</a>\n"
        f"🌐 <b>Сайт:</b> {dlg.website_url or '—'}\n"
        f"📌 <b>Статус:</b> {dlg.status}\n"
        f"🤖 <b>Режим ИИ:</b> {'🛑 Отключен (ЧЕЛОВЕК)' if dlg.ai_locked else '🟢 Активен'}\n\n"
        f"📜 <b>История переписки:</b>\n{history_lines or 'Нет сообщений'}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛑 Забрать диалог", callback_data=f"dlg_takeover_{dlg.id}"),
            InlineKeyboardButton(text="💬 Написать клиенту", callback_data=f"dlg_reply_{dlg.id}")
        ],
        [
            InlineKeyboardButton(text="🖼 Отправить скриншот", callback_data=f"dlg_send_screen_{dlg.id}"),
            InlineKeyboardButton(text="🚫 В черный список", callback_data=f"dlg_bl_{dlg.id}")
        ],
        [InlineKeyboardButton(text="🔙 К списку диалогов", callback_data="menu_dialogs")]
    ])

    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    await call.answer()


@admin_router.callback_query(F.data.startswith("dlg_takeover_"))
async def cb_dialog_takeover(call: CallbackQuery):
    dlg_id = int(call.data.replace("dlg_takeover_", ""))
    async with async_session_factory() as session:
        await session.execute(
            update(OutreachDialog)
            .where(OutreachDialog.id == dlg_id)
            .values(ai_locked=True, status=DialogStatus.NEEDS_HUMAN)
        )
        await session.commit()
    await call.answer("🛑 ИИ заблокирован! Диалог передан вам.", show_alert=True)
    await cb_view_dialog(call)


@admin_router.callback_query(F.data.startswith("dlg_reply_"))
async def cb_start_manual_reply(call: CallbackQuery, state: FSMContext):
    dlg_id = int(call.data.replace("dlg_reply_", ""))
    await state.update_data(reply_dialog_id=dlg_id)
    await state.set_state(AdminStates.dialog_manual_reply)
    await call.message.answer(
        f"✍️ <b>Отправка ответа в диалог #{dlg_id}</b>\n\n"
        f"Напишите текст сообщения. Оно будет отправлено клиенту прямо от имени рабочего Telegram-аккаунта:",
        parse_mode="HTML"
    )
    await call.answer()


@admin_router.message(AdminStates.dialog_manual_reply)
async def process_manual_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    dlg_id = data.get("reply_dialog_id")
    reply_text = message.text.strip()

    async with async_session_factory() as session:
        dlg = (await session.execute(select(OutreachDialog).where(OutreachDialog.id == dlg_id))).scalar_one_or_none()
        if not dlg or not dlg.account_id:
            await message.answer("Диалог не найден или у него нет привязанного аккаунта.")
            await state.clear()
            return

        try:
            recipient = dlg.client_tg_username or dlg.client_tg_id
            msg_id = await session_manager.send_message_safe(
                account_id=dlg.account_id,
                recipient=recipient,
                text=reply_text,
                simulate_typing=True
            )
            session.add(OutreachMessage(
                dialog_id=dlg.id,
                sender_type="manager",
                message_text=reply_text,
                tg_message_id=msg_id
            ))
            dlg.ai_locked = True
            await session.commit()

            await message.answer(f"✅ Сообщение отправлено в диалог #{dlg.id}!")
            await state.clear()
        except Exception as e:
            await message.answer(f"❌ Ошибка отправки: {e}")


# ====================================================================
# 4. Редактор промптов (/prompts)
# ====================================================================

@admin_router.message(Command("prompts"))
@admin_router.callback_query(F.data == "menu_prompts")
async def show_prompts_menu(event: Message | CallbackQuery):
    message = event if isinstance(event, Message) else event.message
    text = (
        "📝 <b>УПРАВЛЕНИЕ ПРОМПТАМИ DEEPSEEK</b>\n\n"
        "Вы можете просматривать и изменять промпты системы в реальном времени "
        "без перезапуска сервера:\n\n"
        "1. <b>PITCH</b> — генератор первого сообщения аудита\n"
        "2. <b>CLASSIFIER</b> — классификатор 12 сценариев\n"
        "3. <b>DIALOG_REPLY</b> — автоответы с брендингом CastleWeb\n"
        "4. <b>FOLLOWUP_1</b> — напоминание через 48 часов\n"
        "5. <b>FOLLOWUP_2</b> — Break-up касание через 72-96ч\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 PITCH", callback_data="prompt_view_PITCH"), InlineKeyboardButton(text="👁 CLASSIFIER", callback_data="prompt_view_CLASSIFIER")],
        [InlineKeyboardButton(text="👁 DIALOG_REPLY", callback_data="prompt_view_DIALOG_REPLY")],
        [InlineKeyboardButton(text="👁 FOLLOWUP 1", callback_data="prompt_view_FOLLOWUP_1"), InlineKeyboardButton(text="👁 FOLLOWUP 2", callback_data="prompt_view_FOLLOWUP_2")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")]
    ])
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("prompt_view_"))
async def cb_view_prompt(call: CallbackQuery):
    key = call.data.replace("prompt_view_", "")
    async with async_session_factory() as session:
        prompt_text = await get_prompt(key, session)

    text = (
        f"📝 <b>Промпт [{key}]:</b>\n\n"
        f"<code>{prompt_text[:3500]}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"prompt_edit_{key}")],
        [InlineKeyboardButton(text="🔄 Сброс к дефолту", callback_data=f"prompt_reset_{key}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_prompts")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@admin_router.callback_query(F.data.startswith("prompt_reset_"))
async def cb_reset_prompt(call: CallbackQuery):
    key = call.data.replace("prompt_reset_", "")
    async with async_session_factory() as session:
        await reset_prompt_to_default(key, session)
    await call.answer(f"Промпт {key} сброшен к стандарту!", show_alert=True)
    await cb_view_prompt(call)


@admin_router.callback_query(F.data.startswith("prompt_edit_"))
async def cb_edit_prompt_start(call: CallbackQuery, state: FSMContext):
    key = call.data.replace("prompt_edit_", "")
    await state.update_data(editing_prompt_key=key)
    await state.set_state(AdminStates.prompt_edit_text)
    await call.message.answer(
        f"✏️ <b>Редактирование промпта [{key}]</b>\n\n"
        f"Отправьте новый полный текст промпта в ответном сообщении:",
        parse_mode="HTML"
    )
    await call.answer()


@admin_router.message(AdminStates.prompt_edit_text)
async def process_prompt_new_text(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("editing_prompt_key")
    new_text = message.text.strip()

    async with async_session_factory() as session:
        await set_prompt(key, new_text, session)

    await message.answer(f"✅ Промпт <b>[{key}]</b> успешно обновлен и вступил в силу!", parse_mode="HTML")
    await state.clear()


# ====================================================================
# 5. Песочница классификатора (/sandbox)
# ====================================================================

@admin_router.message(Command("sandbox"))
@admin_router.callback_query(F.data == "menu_sandbox")
async def start_sandbox(event: Message | CallbackQuery, state: FSMContext):
    message = event if isinstance(event, Message) else event.message
    await state.set_state(AdminStates.sandbox_active)
    text = (
        "🧠 <b>РЕЖИМ ПЕСОЧНИЦЫ (SANDBOX) АКТИВИРОВАН</b>\n\n"
        "Пишите сюда любые реплики клиентов (например: <i>«Вы кто?», «Сколько стоит поправить?», «Скиньте скриншот», «Ты бот?»</i>).\n\n"
        "Система прогонит фразу через классификатор и покажет определенный интент и ответ без реальной отправки.\n\n"
        "Для выхода отправьте: /sandbox_exit или /menu"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text, parse_mode="HTML")


@admin_router.message(Command("sandbox_exit"), AdminStates.sandbox_active)
async def exit_sandbox(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Песочница отключена. Возврат в главное меню: /menu")


@admin_router.message(AdminStates.sandbox_active)
async def process_sandbox_query(message: Message):
    incoming = message.text.strip()
    if incoming.startswith("/"):
        return

    res = await intent_classifier.classify(incoming, [])
    intent = res.get("intent")
    conf = res.get("confidence", 0.0)
    req_human = res.get("requires_human", False)
    phone = res.get("extracted_phone")

    action = "🔥 HUMAN TAKEOVER (Передача менеджеру P0)" if req_human else "🤖 Автоматический ответ CastleWeb"
    if intent == "REJECT_HARD":
        action = "Вежливый уход + Blacklist"
    elif intent == "REQUEST_PROOF":
        action = "Отправка Playwright скриншота + вопрос"

    text = (
        f"🧠 <b>Анализ реплики:</b>\n"
        f"«{incoming}»\n\n"
        f"┌ <b>Интент:</b> <code>{intent}</code> ({conf:.0%})\n"
        f"├ <b>Нужен человек:</b> {'Да 🚨' if req_human else 'Нет'}\n"
        f"├ <b>Найден телефон:</b> {phone or '—'}\n"
        f"├ <b>Действие:</b> {action}\n"
        f"└ <b>Предлагаемый ответ:</b>\n<i>«{res.get('recommended_response') or '—'}»</i>"
    )
    await message.answer(text, parse_mode="HTML")


# ====================================================================
# 6. Аналитика и статистика (/stats)
# ====================================================================

@admin_router.message(Command("stats"))
@admin_router.callback_query(F.data == "menu_stats")
async def show_stats(event: Message | CallbackQuery):
    message = event if isinstance(event, Message) else event.message
    async with async_session_factory() as session:
        total_dialogs = (await session.execute(select(func.count(OutreachDialog.id)))).scalar_one()
        replied = (await session.execute(
            select(func.count(OutreachDialog.id)).where(OutreachDialog.last_client_reply_at.is_not(None))
        )).scalar_one()
        hot_leads = (await session.execute(
            select(func.count(OutreachDialog.id)).where(OutreachDialog.status == DialogStatus.NEEDS_HUMAN)
        )).scalar_one()
        rejected = (await session.execute(
            select(func.count(OutreachDialog.id)).where(OutreachDialog.status == DialogStatus.CLOSED_REJECTED)
        )).scalar_one()
        sent_today = (await session.execute(select(func.coalesce(func.sum(OutreachAccount.sent_today), 0)))).scalar_one()

    reply_cr = (replied / total_dialogs * 100) if total_dialogs > 0 else 0.0
    lead_cr = (hot_leads / total_dialogs * 100) if total_dialogs > 0 else 0.0

    today_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    text = (
        f"📊 <b>АНАЛИТИКА AI SDR ({today_str})</b>\n\n"
        f"📤 <b>Всего диалогов создано:</b> {total_dialogs}\n"
        f"📨 <b>Ответили клиенты:</b> {replied} (<b>CR в ответ: {reply_cr:.1f}%</b>)\n"
        f"🔥 <b>Горячих лидов (P0):</b> {hot_leads} (<b>CR в лид: {lead_cr:.1f}%</b>)\n"
        f"❌ <b>Отказов/Спам:</b> {rejected}\n"
        f"⚡ <b>Отправок сегодня:</b> {sent_today}\n"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")]])
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ====================================================================
# 7. Здоровье системы и Kill Switch (/health, /pause, /resume)
# ====================================================================

@admin_router.message(Command("health"))
@admin_router.callback_query(F.data == "menu_health")
async def show_health(event: Message | CallbackQuery):
    message = event if isinstance(event, Message) else event.message
    # Пинг DeepSeek API
    ds_ok, ds_lat, ds_msg = await deepseek_client.ping()
    ds_status = f"🟢 OK ({ds_lat}ms)" if ds_ok else f"🔴 Сбой: {ds_msg}"

    # Статус сессий
    active_sessions = len(session_manager.clients)
    fu_status = "⏸ На паузе" if followup_worker.is_paused else "🟢 Работает"

    async with async_session_factory() as session:
        total_dialogs = (await session.execute(select(func.count(OutreachDialog.id)))).scalar_one()

    text = (
        f"🏥 <b>СОСТОЯНИЕ СИСТЕМЫ AI OUTREACH</b>\n\n"
        f"🧠 <b>DeepSeek API:</b> {ds_status}\n"
        f"📱 <b>MTProto сессий онлайн:</b> {active_sessions}\n"
        f"🗄 <b>База данных:</b> 🟢 OK ({total_dialogs} диалогов)\n"
        f"⏰ <b>Follow-up воркер:</b> {fu_status}\n"
        f"🕐 <b>Серверное время:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")]])
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@admin_router.message(Command("pause"))
@admin_router.callback_query(F.data == "outreach_pause_all")
async def cb_pause_all(event: Message | CallbackQuery):
    followup_worker.pause()
    text = "🛑 <b>KILL SWITCH АКТИВИРОВАН: Все рассылки и автоответы приостановлены!</b>"
    if isinstance(event, CallbackQuery):
        await event.answer("Все рассылки остановлены!", show_alert=True)
        await cb_main_menu(event, None)
    else:
        await event.answer(text, parse_mode="HTML")


@admin_router.message(Command("resume"))
@admin_router.callback_query(F.data == "outreach_resume_all")
async def cb_resume_all(event: Message | CallbackQuery):
    followup_worker.resume()
    if isinstance(event, CallbackQuery):
        await event.answer("Рассылки возобновлены!", show_alert=True)
        await cb_main_menu(event, None)
    else:
        await event.answer("▶️ Все процессы возобновлены.", parse_mode="HTML")


# ====================================================================
# 8. Черный список (/blacklist)
# ====================================================================

@admin_router.message(Command("blacklist"))
@admin_router.callback_query(F.data == "menu_blacklist")
async def show_blacklist(event: Message | CallbackQuery):
    message = event if isinstance(event, Message) else event.message
    async with async_session_factory() as session:
        bl_items = (await session.execute(
            select(OutreachBlacklist).order_by(OutreachBlacklist.added_at.desc()).limit(15)
        )).scalars().all()

    text = f"🚫 <b>Черный список (всего {len(bl_items)}):</b>\n\n"
    for b in bl_items:
        text += f"• <code>{b.identifier}</code> ({b.reason or 'Отказ'})\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить в стоп-лист", callback_data="bl_add_start")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="menu_main")]
    ])
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text or "Список пуст.", reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text or "Список пуст.", reply_markup=kb, parse_mode="HTML")


# ====================================================================
# 9. Интеграция Live-зеркалирования и P0 Handoff в Telegram
# ====================================================================

def get_active_outreach_bot() -> Optional[Bot]:
    from app.services.telegram.outreach_bot_service import outreach_bot_service
    if outreach_bot_service.bot:
        return outreach_bot_service.bot
    from app.services.telegram.bot_service import tg_bot_service
    return tg_bot_service.bot


async def live_mirror_handler(dialog: OutreachDialog, incoming_text: str, intent_info: dict, bot_reply: Optional[str] = None):
    """
    Отправляет уведомление о новом сообщении администраторам через бот AI SDR.
    """
    bot = get_active_outreach_bot()
    if not bot or not ADMIN_TELEGRAM_IDS:
        return

    intent = intent_info.get("intent", "OTHER")
    conf = intent_info.get("confidence", 0.8)
    user_str = f"@{dialog.client_tg_username}" if dialog.client_tg_username else f"ID {dialog.client_tg_id}"

    text = (
        f"🔔 <b>НОВЫЙ ОТВЕТ В ДИАЛОГЕ #{dialog.id}</b>\n\n"
        f"🏢 <b>Компания:</b> {dialog.company_name or 'Организация'}\n"
        f"👤 <b>Контакт:</b> {user_str}\n\n"
        f"💬 <b>Клиент написал:</b>\n"
        f"«{incoming_text}»\n\n"
        f"🧠 <b>Интент:</b> <code>{intent}</code> ({conf:.0%})\n"
    )
    if bot_reply:
        text += f"🤖 <b>Отправлен автоответ:</b>\n<i>«{bot_reply}»</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👁 Открыть диалог", callback_data=f"dlg_view_{dialog.id}"),
            InlineKeyboardButton(text="🛑 Забрать себе", callback_data=f"dlg_takeover_{dialog.id}")
        ]
    ])

    for admin_id in ADMIN_TELEGRAM_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Не удалось отправить mirror админу {admin_id}: {e}")


async def manager_p0_alert_handler(dialog: OutreachDialog, incoming_text: str, intent_info: dict):
    """
    P0 Эскалация: Мгновенное оповещение о горячем лиде в чат менеджеров.
    """
    bot = get_active_outreach_bot()
    if not bot:
        return

    chat_id = MANAGER_TELEGRAM_CHAT_ID or next(iter(ADMIN_TELEGRAM_IDS), None)
    if not chat_id:
        return

    user_link = f"tg://resolve?domain={dialog.client_tg_username}" if dialog.client_tg_username else f"tg://user?id={dialog.client_tg_id}"
    phone = intent_info.get("extracted_phone") or dialog.client_phone or "Не указан"

    text = (
        f"🔥 <b>[P0] ГОРЯЧИЙ ЛИД ЖДЕТ В TELEGRAM!</b>\n\n"
        f"🏢 <b>Организация:</b> {dialog.company_name or '—'}\n"
        f"👤 <b>Контакт:</b> @{dialog.client_tg_username or dialog.client_tg_id}\n"
        f"🌐 <b>Сайт:</b> {dialog.website_url or '—'}\n"
        f"📞 <b>Телефон:</b> {phone}\n\n"
        f"💬 <b>Сообщение клиента:</b>\n"
        f"«{incoming_text}»\n\n"
        f"⚠️ <b>Статус:</b> ИИ заблокирован! Лид ждет ответа эксперта CastleWeb.\n\n"
        f"👉 <a href='{user_link}'><b>ОТКРЫТЬ ЧАТ В 1 КЛИК</b></a>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Забрал лид в работу", callback_data=f"dlg_takeover_{dialog.id}")],
        [InlineKeyboardButton(text="🖼 Отправить скриншот", callback_data=f"dlg_send_screen_{dialog.id}")],
    ])

    try:
        await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не удалось отправить P0 алерт в чат {chat_id}: {e}")



# Регистрируем коллбеки в dialog_engine
dialog_engine.register_admin_mirror(live_mirror_handler)
dialog_engine.register_manager_alert(manager_p0_alert_handler)


# ====================================================================
# 10. Управление конфигурацией (.env) (/settings, /env)
# ====================================================================

@admin_router.message(Command("settings", "env"))
@admin_router.callback_query(F.data == "menu_settings")
async def show_env_settings(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    message = event if isinstance(event, Message) else event.message

    text = "⚙️ <b>КОНФИГУРАЦИЯ СИСТЕМЫ (.env)</b>\n\n"
    buttons = []

    for key, meta in ENV_META.items():
        val = get_env_value(key, meta["default"])
        if meta["secret"] and val:
            display_val = val[:6] + "..." + val[-4:] if len(val) > 10 else "******"
        elif not val:
            display_val = "<i>[не задано]</i>"
        else:
            display_val = f"<code>{val}</code>"

        text += f"• <b>{meta['title']}</b> ({key}):\n  └ {display_val}\n\n"
        buttons.append([InlineKeyboardButton(text=f"✏️ {meta['title']}", callback_data=f"env_edit_{key}")])

    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu_main")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("env_edit_"))
async def cb_env_edit_key(call: CallbackQuery, state: FSMContext):
    key = call.data.replace("env_edit_", "")
    meta = ENV_META.get(key, {"title": key, "desc": "", "default": ""})
    curr = get_env_value(key, meta.get("default", ""))

    await state.update_data(editing_env_key=key)
    await state.set_state(AdminStates.env_edit_value)

    text = (
        f"✏️ <b>Изменение параметра: {meta['title']}</b>\n"
        f"Ключ: <code>{key}</code>\n"
        f"Описание: <i>{meta['desc']}</i>\n\n"
        f"Текущее значение: <code>{curr or '[не задано]'}</code>\n\n"
        f"Отправьте новое значение в ответном сообщении (или <code>-</code> чтобы очистить):"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_settings")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@admin_router.message(AdminStates.env_edit_value)
async def process_env_edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("editing_env_key")
    if not key:
        await state.clear()
        return

    new_val = message.text.strip()
    if new_val == "-":
        new_val = ""

    set_env_value(key, new_val)

    # Мгновенное применение в рантайме
    if key == "DEEPSEEK_API_KEY":
        deepseek_client.set_api_key(new_val)

    meta = ENV_META.get(key, {"title": key})
    await message.answer(
        f"✅ <b>Параметр успешно обновлен!</b>\n\n"
        f"<b>{meta['title']}</b> (<code>{key}</code>) = <code>{new_val or '[очищено]'}</code>\n\n"
        f"Изменение сохранено в <code>.env</code> и мгновенно активно в системе.",
        parse_mode="HTML"
    )
    await state.clear()
