import os
import shutil
import time
import re
import logging
import html
import httpx
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text as sql_text
from app.core.database import get_db
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.infrastructure.db.models import Lead, Blacklist, Case, DemoGrant
from app.domain.entities import LeadStatus
from app.infrastructure.telegram.bot_service import (
    TelegramBotService, build_telegram_api_url
)

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


async def answer_callback_query(callback_id: str, text: str):
    """
    Всплывающее уведомление в интерфейсе Telegram при нажатии кнопки.
    """
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN in ("your_bot_token_here", ""):
        return
    url = build_telegram_api_url("answerCallbackQuery")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(url, json={"callback_query_id": callback_id, "text": text})
    except Exception as e:
        logger.warning(f"Failed to answer callback query {callback_id}: {e}")


async def send_reply_message(chat_id: int | str, text: str, reply_markup: dict | None = None):
    """
    Отправляет текстовое сообщение в чат Telegram с поддержкой кнопок,
    автоматической миграцией supergroup и plain-text fallback.
    """
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN in ("your_bot_token_here", ""):
        return
    url = build_telegram_api_url("sendMessage")
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                # Handle supergroup migration
                migrate_to = data.get("parameters", {}).get("migrate_to_chat_id")
                if migrate_to:
                    logger.info(f"🔄 Supergroup migration detected in send_reply_message: {chat_id} -> {migrate_to}")
                    if str(chat_id) == str(settings.TELEGRAM_CHAT_ID):
                        settings.TELEGRAM_CHAT_ID = str(migrate_to)
                    payload["chat_id"] = migrate_to
                    resp = await client.post(url, json=payload)
                    data = resp.json()
                    if data.get("ok"):
                        return

                # Handle HTML parse error fallback
                err_desc = data.get("description", "")
                if any(k in err_desc.lower() for k in ("parse", "tag", "entity", "link")):
                    clean_text = re.sub(r"<[^>]+>", "", text)
                    payload["text"] = clean_text
                    payload["parse_mode"] = None
                    await client.post(url, json=payload)
    except Exception as e:
        logger.warning(f"Failed to send reply to chat {chat_id}: {e}")


@router.api_route("/test", methods=["GET", "POST"], summary="Send Test Notification to Telegram")
async def send_test_telegram():
    """
    Диагностический эндпоинт: отправляет тестовое сообщение в Telegram-чат с текущими настройками.
    Автоматически распознает миграцию группы в супергруппу и обновляет chat_id.
    """
    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
    chat_id = (getattr(settings, "TELEGRAM_CHAT_ID", "") or "").strip()
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "(не задан или некорректный)"

    if not token or token in ("your_bot_token_here", ""):
        return {
            "ok": False,
            "error": "TELEGRAM_BOT_TOKEN не задан в .env на сервере (или содержит плейсхолдер)",
            "token_preview": masked_token
        }
    if not chat_id or chat_id in ("your_team_chat_id_here", ""):
        return {
            "ok": False,
            "error": "TELEGRAM_CHAT_ID не задан в .env на сервере (или содержит плейсхолдер)",
            "token_preview": masked_token,
            "chat_id": chat_id
        }

    url = build_telegram_api_url("sendMessage")
    payload = {
        "chat_id": chat_id,
        "text": "🏰 <b>CASTLEWEB</b>: Проверка интеграции бэкенда с Telegram прошла успешно! 🚀\nБот активен и готов принимать заявки с сайта.",
        "parse_mode": "HTML"
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                migrate_to = data.get("parameters", {}).get("migrate_to_chat_id")
                if migrate_to:
                    old_id = chat_id
                    settings.TELEGRAM_CHAT_ID = str(migrate_to)
                    payload["chat_id"] = migrate_to
                    retry_resp = await client.post(url, json=payload)
                    retry_data = retry_resp.json()
                    return {
                        "ok": retry_data.get("ok", False),
                        "chat_id": str(migrate_to),
                        "migrated_from": old_id,
                        "migrated_to": str(migrate_to),
                        "message_id": retry_data.get("result", {}).get("message_id"),
                        "error": retry_data.get("description"),
                        "token_preview": masked_token
                    }
                return {
                    "ok": False,
                    "chat_id": chat_id,
                    "error": data.get("description"),
                    "parameters": data.get("parameters"),
                    "token_preview": masked_token,
                    "status_code": resp.status_code
                }
            return {
                "ok": True,
                "chat_id": chat_id,
                "message_id": data["result"]["message_id"],
                "token_preview": masked_token
            }
    except Exception as e:
        return {"ok": False, "chat_id": chat_id, "token_preview": masked_token, "error": str(e)}


@router.api_route("/setup-webhook", methods=["GET", "POST"], summary="Register Webhook with Telegram")
async def setup_webhook(drop_pending_updates: bool = False):
    """
    Регистрирует адрес https://{DOMAIN_NAME}/api/v1/telegram/webhook в Telegram Bot API.
    """
    try:
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN in ("your_bot_token_here", ""):
            return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not configured"}

        domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
        webhook_url = f"https://{domain}/api/v1/telegram/webhook"
        url = build_telegram_api_url("setWebhook")
        payload = {
            "url": webhook_url,
            "drop_pending_updates": drop_pending_updates,
            "allowed_updates": ["message", "callback_query"]
        }
        if settings.TELEGRAM_WEBHOOK_SECRET:
            payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            return {
                "ok": data.get("ok", False),
                "webhook_url": webhook_url,
                "telegram_response": data
            }
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/webhook-info", summary="Get Current Webhook Status from Telegram")
async def get_webhook_info():
    """
    Возвращает диагностическую информацию о текущем вебхуке из Telegram Bot API.
    """
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN in ("your_bot_token_here", ""):
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not configured"}

    url = build_telegram_api_url("getWebhookInfo")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def get_server_status_card(db: AsyncSession) -> tuple[str, dict]:
    """
    Формирует интерактивную карточку телеметрии сервера
    с инлайн-кнопками для мгновенного обновления.
    """
    # 1. CPU Load
    load_str = "0.08, 0.12, 0.09"
    if hasattr(os, "getloadavg"):
        try:
            l1, l5, l15 = os.getloadavg()
            load_str = f"{l1:.2f}, {l5:.2f}, {l15:.2f}"
        except Exception:
            pass

    # 2. RAM
    ram_str = "N/A"
    try:
        if os.path.exists("/proc/meminfo"):
            mem = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    p = line.split(":")
                    if len(p) == 2:
                        v = p[1].strip().split()[0]
                        if v.isdigit():
                            mem[p[0].strip()] = int(v) * 1024
            tot = mem.get("MemTotal", 0)
            free = mem.get("MemAvailable", mem.get("MemFree", 0))
            used = tot - free
            if tot > 0:
                pct = round((used / tot) * 100, 1)
                ram_str = f"{round(used/(1024**3), 1)} GB / {round(tot/(1024**3), 1)} GB ({pct}%)"
    except Exception:
        pass

    # 3. Disk (/)
    disk_str = "N/A"
    try:
        du_path = "/" if os.name != "nt" else "C:\\"
        du = shutil.disk_usage(du_path)
        pct = round((du.used / du.total) * 100, 1)
        disk_str = f"{round(du.used/(1024**3), 1)} GB / {round(du.total/(1024**3), 1)} GB ({pct}%)"
    except Exception:
        pass

    # 4. Uptime
    uptime_str = "Активен"
    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime") as f:
                sec = float(f.readline().split()[0])
                d = int(sec // 86400)
                h = int((sec % 86400) // 3600)
                m = int((sec % 3600) // 60)
                uptime_str = f"{d}д {h}ч {m}м" if d > 0 else f"{h}ч {m}м"
    except Exception:
        pass

    # 5. Database ping & latency
    db_status = "🔴 Offline"
    try:
        t0 = time.perf_counter()
        await db.execute(sql_text("SELECT 1"))
        lat = (time.perf_counter() - t0) * 1000
        db_status = f"🟢 OK ({lat:.1f} ms)"
    except Exception as e:
        db_status = f"🔴 Ошибка ({str(e)[:25]})"

    # 6. Redis ping & latency
    redis_status = "🟡 N/A"
    try:
        redis_client = await get_redis_client()
        if redis_client:
            t0 = time.perf_counter()
            await redis_client.ping()
            lat = (time.perf_counter() - t0) * 1000
            redis_status = f"🟢 OK ({lat:.1f} ms)"
    except Exception:
        pass

    now_str = time.strftime("%H:%M:%S UTC")
    server_report = (
        f"🏰 <b>CASTLEWEB • Мониторинг сервера</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 <b>Статус:</b> В штатном режиме\n\n"
        f"⚙️ <b>Ресурсы хоста:</b>\n"
        f"• CPU Load: <code>{load_str}</code>\n"
        f"• RAM: <code>{ram_str}</code>\n"
        f"• SSD (/): <code>{disk_str}</code>\n"
        f"• Uptime: <code>{uptime_str}</code>\n\n"
        f"🛡️ <b>Инфраструктура:</b>\n"
        f"• PostgreSQL: {db_status}\n"
        f"• Redis: {redis_status}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <i>Обновлено: {now_str}</i>"
    )

    kb = {
        "inline_keyboard": [
            [
                {"text": "🔄 Обновить метрики", "callback_data": "server_refresh"},
                {"text": "📊 Статистика лидов", "callback_data": "server_stats"}
            ]
        ]
    }
    return server_report, kb


async def request_parser_demo_access(tg_user_id: str | int, username: str | None = None) -> dict:
    """
    Обращается к внутреннему API LeadHunter Pro для создания или обновления временного демо-аккаунта.
    """
    internal_urls = [
        getattr(settings, "PARSER_INTERNAL_URL", "") or os.environ.get("PARSER_INTERNAL_URL", "").strip(),
        "http://leadhunter:8000",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    secret = getattr(settings, "INTERNAL_API_SECRET", "") or os.environ.get("INTERNAL_API_SECRET", "castleweb-internal-demo-secret")
    payload = {
        "tg_user_id": str(tg_user_id),
        "tg_username": username or "",
        "secret_key": secret
    }

    last_error = None
    for base_url in filter(None, internal_urls):
        url = f"{base_url.rstrip('/')}/api/internal/create-demo-user"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.post(url, json=payload, headers={"X-Internal-Secret": secret})
                if resp.status_code == 200:
                    return resp.json()
                last_error = f"HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            last_error = str(e)

    raise RuntimeError(f"Parser API unavailable: {last_error}")


def format_demo_access_response(res: dict, parser_public_url: str) -> tuple[str, dict]:
    """
    Формирует текст и клавиатуру в зависимости от статуса демо-доступа:
    - 'created': выдан впервые (5 запросов);
    - 'already_active': напоминание данных существующего аккаунта (тест выдается только 1 раз);
    - 'exhausted': 5 запросов полностью исчерпаны (тест завершен, связь с разработчиком).
    """
    status = res.get("status")

    if status == "admin":
        text = (
            "👑 <b>Панель Администратора LeadHunter Pro</b>\n\n"
            "Вы авторизованы как <b>Администратор / Разработчик</b> студии.\n\n"
            f"🌐 <b>Адрес веб-панели:</b> <a href=\"{parser_public_url}\">{parser_public_url}</a>\n"
            f"👤 <b>Логин:</b> <code>{res['email']}</code>\n"
            f"🔑 <b>Пароль:</b> <code>{res['password']}</code>\n\n"
            "⚡️ <b>Ваши безграничные права:</b>\n"
            "• Безлимитный сбор организаций по Яндекс.Картам\n"
            "• Без таймеров и ограничений по количеству\n"
            "• Мониторинг заказов FL.ru и глубокий аудит сайтов\n"
            "• Экспорт всей базы в Excel (.xlsx) / CSV\n\n"
            "💡 <i>Нажмите на логин или пароль, чтобы скопировать.</i>"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🚀 Войти в панель администратора", "url": parser_public_url}],
                [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
            ]
        }
        return text, kb

    if status == "exhausted":
        text = (
            "⛔️ <b>Тестовый период уже завершён</b>\n\n"
            "Вы уже использовали все 5 запросов к парсеру Яндекс.Карт.\n"
            "Тестовый режим предоставляется строго <b>один раз</b> для каждого пользователя.\n\n"
            "Чтобы приобрести полноценную версию парсера без ограничений "
            "(любые города, безлимитный сбор, выгрузка прямых телефонов, сайтов, Telegram и экспорт в Excel), напишите нам:\n"
            "👉 <b>@kupidon996</b>"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "💬 Написать разработчику (@kupidon996)", "url": "https://t.me/kupidon996"}],
                [{"text": "💼 Посмотреть кейсы студии", "callback_data": "client_cases"}],
                [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
            ]
        }
        return text, kb

    if status == "already_active":
        searches_left = res.get("demo_searches_left", 0)
        text = (
            "ℹ️ <b>Вы уже получали тестовый доступ ранее!</b>\n\n"
            "Тестовый режим предоставляется строго <b>один раз</b> на пользователя (повторный тестовый период не выдаётся).\n\n"
            f"Ваши данные для входа в панель парсера:\n"
            f"🌐 <b>Адрес панели:</b> <a href=\"{parser_public_url}\">{parser_public_url}</a>\n"
            f"👤 <b>Логин:</b> <code>{res['email']}</code>\n"
            f"🔑 <b>Пароль:</b> <code>{res['password']}</code>\n\n"
            f"⚙️ <b>Параметры вашего аккаунта:</b>\n"
            f"• Доступный модуль: <b>Яндекс.Карты</b>\n"
            f"• Осталось поисков: <b>{searches_left} из 5</b>\n"
            f"• Организаций за раз: <b>до {res.get('max_companies_per_search', 5)}</b>\n"
            f"• Интервал между поисками: <b>{res.get('cooldown_minutes', 15)} минут</b>\n\n"
            f"💡 <i>Нажмите на логин или пароль, чтобы скопировать.</i>"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🚀 Войти в панель LeadHunter", "url": parser_public_url}],
                [{"text": "💬 Вопрос по парсеру (@kupidon996)", "url": "https://t.me/kupidon996"}],
                [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
            ]
        }
        return text, kb

    # status == "created" (первая выдача)
    text = (
        "🎯 <b>Демо-доступ к парсеру Яндекс.Карт активирован!</b>\n\n"
        f"🌐 <b>Адрес панели:</b> <a href=\"{parser_public_url}\">{parser_public_url}</a>\n"
        f"👤 <b>Логин:</b> <code>{res['email']}</code>\n"
        f"🔑 <b>Пароль:</b> <code>{res['password']}</code>\n\n"
        "⚙️ <b>Параметры демо-режима:</b>\n"
        "• Доступный модуль: <b>Яндекс.Карт</b>\n"
        f"• Поисковых запросов: <b>{res.get('demo_searches_left', 5)} из 5</b>\n"
        f"• Организаций за раз: <b>до {res.get('max_companies_per_search', 5)}</b>\n"
        f"• Интервал между поисками: <b>{res.get('cooldown_minutes', 15)} минут</b>\n\n"
        "⚠️ <i>Обратите внимание: тестовый доступ предоставляется строго один раз на пользователя.</i>\n\n"
        "💡 <i>Нажмите на логин или пароль, чтобы скопировать в буфер обмена.</i>"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "🚀 Войти в панель LeadHunter", "url": parser_public_url}],
            [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
        ]
    }
    return text, kb


def get_client_main_menu(name: str = "Гость") -> tuple[str, dict]:
    """
    Формирует интерактивное меню Telegram-бота студии для клиентов.
    """
    text = (
        f"👋 <b>Здравствуйте, {html.escape(name)}!</b>\n\n"
        f"🏰 <b>CASTLEWEB Studio</b> — проектируем надежный бэкенд и собираем живой, отзывчивый фронтенд без посредников.\n\n"
        f"Выберите действие в интерактивном меню ниже:"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "🔑 Демо-доступ к парсеру LeadHunter", "callback_data": "get_demo_access"}],
            [{"text": "💼 Портфолио и кейсы", "callback_data": "client_cases"}],
            [{"text": "📊 Калькулятор сметы", "url": "https://castleweb.ru/#calculator"}],
            [{"text": "🌐 Официальный сайт", "url": "https://castleweb.ru"}]
        ]
    }
    return text, kb


@router.post("/webhook", summary="Telegram Bot Webhook Handler (Headless CRM)")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Обрабатывает события от Telegram Bot:
    - Нажатия inline-кнопок (Взять в работу, Связался, Спам/Бан)
    - Команды инженеров: /stats, /leads
    - Сообщения и документы от пользователей (автоответчик + пересылка инженерам)
    """
    # Verify secret token to prevent forged webhook updates
    if settings.TELEGRAM_WEBHOOK_SECRET:
        incoming_token = request.headers.get("x-telegram-bot-api-secret-token", "")
        if incoming_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning(f"Webhook rejected: invalid secret token from {request.client.host if request.client else 'unknown'}")
            return {"ok": False}

    update = await request.json()

    # 1. Обработка нажатий инлайн-кнопок (Callback Query)
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb["id"]
        data = cb.get("data", "")
        message = cb.get("message", {})
        message_id = message.get("message_id")
        chat_id = message.get("chat", {}).get("id")
        user = cb.get("from", {})
        username = user.get("username")
        user_display = f"@{username}" if username else user.get("first_name", "Инженер")

        if data.startswith("lead_take:"):
            lead_id = int(data.split(":")[1])
            res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = res.scalar_one_or_none()
            if lead:
                lead.status = LeadStatus.IN_PROGRESS
                lead.handled_by = user_display
                await db.commit()
                await db.refresh(lead)

                await answer_callback_query(cb_id, f"⚡ Заявка #{lead.id} в работе")
                if message_id and chat_id:
                    await TelegramBotService.update_message(chat_id, message_id, lead)

        elif data.startswith("lead_contacted:"):
            lead_id = int(data.split(":")[1])
            res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = res.scalar_one_or_none()
            if lead:
                lead.status = LeadStatus.CONTACTED
                lead.handled_by = user_display
                await db.commit()
                await db.refresh(lead)

                await answer_callback_query(cb_id, f"✅ Связались по #{lead.id}")
                if message_id and chat_id:
                    await TelegramBotService.update_message(chat_id, message_id, lead)

        elif data.startswith("lead_spam:"):
            lead_id = int(data.split(":")[1])
            res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = res.scalar_one_or_none()
            if lead:
                lead.status = LeadStatus.SPAM

                if lead.ip_address:
                    existing_ip = (await db.execute(select(Blacklist).where(Blacklist.ip_address == lead.ip_address))).scalar_one_or_none()
                    if not existing_ip:
                        db.add(Blacklist(ip_address=lead.ip_address, reason=f"Spam lead #{lead.id}"))

                if lead.contact:
                    existing_contact = (await db.execute(select(Blacklist).where(Blacklist.contact == lead.contact))).scalar_one_or_none()
                    if not existing_contact:
                        db.add(Blacklist(contact=lead.contact, reason=f"Spam lead #{lead.id}"))

                redis = await get_redis_client()
                if redis and lead.ip_address:
                    await redis.set(f"blacklist:{lead.ip_address}", "1", ex=86400 * 30)

                await db.commit()
                await db.refresh(lead)

                await answer_callback_query(cb_id, f"🚫 Заявка #{lead.id} в спаме (IP заблокирован)")
                if message_id and chat_id:
                    await TelegramBotService.update_message(chat_id, message_id, lead)

        elif data.startswith("lead_del_prompt:"):
            lead_id = int(data.split(":")[1])
            res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = res.scalar_one_or_none()
            if not lead:
                await answer_callback_query(cb_id, f"⚠️ Заявка #{lead_id} не найдена")
                return {"ok": True}

            confirm_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": f"💥 Да, удалить #{lead_id}", "callback_data": f"lead_del_confirm:{lead_id}"},
                        {"text": "Отмена", "callback_data": f"lead_del_cancel:{lead_id}"}
                    ]
                ]
            }
            await answer_callback_query(cb_id, f"Удалить заявку #{lead_id}?")
            if message_id and chat_id:
                await TelegramBotService.edit_message_reply_markup(chat_id, message_id, confirm_keyboard)

        elif data.startswith("lead_del_cancel:"):
            lead_id = int(data.split(":")[1])
            res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = res.scalar_one_or_none()
            await answer_callback_query(cb_id, "Отменено")
            if lead and message_id and chat_id:
                await TelegramBotService.update_message(chat_id, message_id, lead)

        elif data.startswith("lead_del_confirm:"):
            lead_id = int(data.split(":")[1])
            res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = res.scalar_one_or_none()
            if lead:
                lead_name = lead.name
                lead_contact = lead.contact
                await db.delete(lead)
                await db.commit()

                deleted_text = (
                    f"🗑 <b>Заявка #{lead_id} удалена из базы</b>\n"
                    f"Клиент: {html.escape(lead_name)} (<code>{html.escape(lead_contact)}</code>)\n"
                    f"Удалил: {user_display}"
                )
                del_keyboard = {"inline_keyboard": [[{"text": "🗑 Запись удалена", "callback_data": "noop"}]]}
                await answer_callback_query(cb_id, f"🗑 Заявка #{lead_id} удалена")
                if message_id and chat_id:
                    await TelegramBotService.edit_message_text(chat_id, message_id, deleted_text, del_keyboard)
            else:
                await answer_callback_query(cb_id, f"⚠️ Заявка #{lead_id} уже удалена")

        elif data == "client_cases":
            res = await db.execute(select(Case).where(Case.is_published.is_(True)).order_by(Case.sort_order.asc()).limit(5))
            cases = res.scalars().all()
            if not cases:
                await answer_callback_query(cb_id, "Портфолио наполняется...")
            else:
                await answer_callback_query(cb_id, "Загрузка...")
                lines = ["💼 <b>Кейсы CASTLEWEB:</b>"]
                for c in cases:
                    cat_val = c.category.value if hasattr(c.category, "value") else str(c.category)
                    link_html = f' — <a href="{html.escape(c.live_url)}">ссылка</a>' if c.live_url else ""
                    lines.append(f"• <b>{html.escape(c.title)}</b> [{cat_val.upper()}]{link_html}\n{html.escape(c.short_description)}")
                lines.append("\n🌐 castleweb.ru")
                if chat_id:
                    await send_reply_message(chat_id, "\n\n".join(lines))

        elif data == "server_refresh":
            report, kb = await get_server_status_card(db)
            await answer_callback_query(cb_id, "Метрики обновлены ⚡")
            if message_id and chat_id:
                try:
                    await TelegramBotService.edit_message_text(chat_id, message_id, report, kb)
                except Exception:
                    pass

        elif data == "server_stats":
            total_leads = (await db.execute(select(func.count(Lead.id)))).scalar() or 0
            pending = (await db.execute(select(func.count(Lead.id)).where(Lead.status.in_([LeadStatus.PENDING, LeadStatus.DELIVERED])))).scalar() or 0
            in_progress = (await db.execute(select(func.count(Lead.id)).where(Lead.status == LeadStatus.IN_PROGRESS))).scalar() or 0
            contacted = (await db.execute(select(func.count(Lead.id)).where(Lead.status == LeadStatus.CONTACTED))).scalar() or 0
            spam = (await db.execute(select(func.count(Lead.id)).where(Lead.status == LeadStatus.SPAM))).scalar() or 0

            stats_msg = (
                f"📊 <b>Статистика заявок</b>\n"
                f"• Всего: <b>{total_leads}</b>\n"
                f"• В ожидании: <b>{pending}</b>\n"
                f"• В работе: <b>{in_progress}</b>\n"
                f"• Связались: <b>{contacted}</b>\n"
                f"• Спам: <b>{spam}</b>"
            )
            kb = {
                "inline_keyboard": [
                    [
                        {"text": "🖥 Сервер", "callback_data": "server_refresh"}
                    ]
                ]
            }
            await answer_callback_query(cb_id, "Статистика лидов")
            if message_id and chat_id:
                try:
                    await TelegramBotService.edit_message_text(chat_id, message_id, stats_msg, kb)
                except Exception:
                    pass

        elif data == "noop":
            await answer_callback_query(cb_id, "OK")

        elif data == "get_demo_access":
            await answer_callback_query(cb_id, "Проверяем доступ к парсеру...")
            domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
            parser_public_url = os.environ.get("PARSER_PUBLIC_URL", f"https://leads.{domain}").rstrip("/")
            try:
                res = await request_parser_demo_access(user.get("id", ""), user.get("username", ""))
                demo_text, demo_kb = format_demo_access_response(res, parser_public_url)

                # Фиксируем в БД CRM выдачу, если аккаунт создан впервые
                if res.get("status") == "created":
                    try:
                        grant_check = await db.execute(select(DemoGrant).where(DemoGrant.tg_user_id == str(user.get("id", ""))))
                        if not grant_check.scalar_one_or_none():
                            db.add(DemoGrant(
                                tg_user_id=str(user.get("id", "")),
                                tg_username=user.get("username", ""),
                                first_name=user.get("first_name", ""),
                                email=res.get("email", "")
                            ))
                            await db.commit()
                    except Exception as ge:
                        logger.warning(f"Failed to record DemoGrant: {ge}")

                if message_id and chat_id:
                    try:
                        await TelegramBotService.edit_message_text(chat_id, message_id, demo_text, demo_kb)
                    except Exception:
                        await send_reply_message(chat_id, demo_text, demo_kb)
                else:
                    await send_reply_message(chat_id, demo_text, demo_kb)

                if settings.TELEGRAM_CHAT_ID:
                    st = res.get("status")
                    if st == "created":
                        alert = f"🔔 Клиент {user_display} (ID: <code>{user.get('id')}</code>) впервые активировал демо к парсеру ({res.get('email')})."
                    elif st == "exhausted":
                        alert = f"⚠️ Клиент {user_display} (ID: <code>{user.get('id')}</code>) повторно запросил демо, но его лимит исчерпан."
                    else:
                        alert = f"ℹ️ Клиент {user_display} (ID: <code>{user.get('id')}</code>) запросил данные своего демо-доступа повторно."
                    await send_reply_message(settings.TELEGRAM_CHAT_ID, alert)
            except Exception as e:
                logger.error(f"Error creating demo user: {e}")
                err_text = (
                    "⚠️ Сервер парсера сейчас перезагружается или временно недоступен.\n"
                    "Пожалуйста, повторите попытку через пару минут или напишите дежурному разработчику: @kupidon996"
                )
                await send_reply_message(chat_id, err_text)

        elif data == "client_cases":
            await answer_callback_query(cb_id, "Кейсы CASTLEWEB")
            domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
            cases_text = (
                f"💼 <b>Избранные проекты CASTLEWEB:</b>\n\n"
                f"1. <b>Onyx OS</b> — специализированный шелл для ПК-клуба и сим-рейсинга на Unreal/DirectX.\n"
                f"2. <b>Skog Chalet & Hytte Control</b> — мобильный кабинет гостя и система бронирования загородных шале.\n"
                f"3. <b>LeadHunter</b> — автономный сервис парсинга организаций из Яндекс.Карт (телефоны, сайты, адреса, Telegram).\n\n"
                f"Вы можете протестировать демо-версию парсера прямо сейчас!"
            )
            cases_kb = {
                "inline_keyboard": [
                    [{"text": "🔑 Получить демо LeadHunter", "callback_data": "get_demo_access"}],
                    [{"text": "🌐 Все кейсы на сайте", "url": f"https://{domain}/cases.html"}],
                    [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
                ]
            }
            if message_id and chat_id:
                try:
                    await TelegramBotService.edit_message_text(chat_id, message_id, cases_text, cases_kb)
                except Exception:
                    await send_reply_message(chat_id, cases_text, cases_kb)
            else:
                await send_reply_message(chat_id, cases_text, cases_kb)

        elif data == "client_menu":
            await answer_callback_query(cb_id, "Меню")
            menu_text, menu_kb = get_client_main_menu(user.get("first_name", "Клиент"))
            if message_id and chat_id:
                try:
                    await TelegramBotService.edit_message_text(chat_id, message_id, menu_text, menu_kb)
                except Exception:
                    await send_reply_message(chat_id, menu_text, menu_kb)
            else:
                await send_reply_message(chat_id, menu_text, menu_kb)

        return {"ok": True}

    # 2. Обработка входящих сообщений (Команды и Умный автоответчик)
    if "message" in update:
        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        chat_type = chat.get("type", "private")
        user = msg.get("from", {})
        from_id = user.get("id")
        username = user.get("username")
        first_name = user.get("first_name", "Клиент")
        last_name = user.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        user_display = f"{full_name} (@{username})" if username else full_name

        text = msg.get("text", "") or msg.get("caption", "")
        text = text.strip()

        # А.1. ДВУСТОРОННИЙ МОСТ ОБЩЕНИЯ С КЛИЕНТОМ (Two-Way Bridge)
        # Если инженер в командном чате делает Reply на сообщение или уведомление клиента
        reply_to = msg.get("reply_to_message")
        if reply_to and text and not text.startswith("/"):
            client_tg_id = None
            forward_from = reply_to.get("forward_from")
            if forward_from and forward_from.get("id"):
                client_tg_id = forward_from["id"]
            else:
                reply_text = reply_to.get("text", "") or reply_to.get("caption", "")
                m = re.search(r"Telegram ID:\s*<code>(\d+)</code>", reply_text, re.IGNORECASE)
                if not m:
                    m = re.search(r"ID:\s*<code>(\d+)</code>", reply_text, re.IGNORECASE)
                if m:
                    client_tg_id = int(m.group(1))

            if client_tg_id and str(client_tg_id) != str(chat_id):
                client_msg = (
                    f"💬 <b>CASTLEWEB:</b>\n"
                    f"{html.escape(text)}"
                )
                try:
                    await send_reply_message(client_tg_id, client_msg)
                    await send_reply_message(chat_id, "✅ Ответ отправлен клиенту.")
                    return {"ok": True}
                except Exception as e:
                    logger.warning(f"Failed to bridge engineer reply to client {client_tg_id}: {e}")

        # А.2. Команды для инженеров (/stats, /leads, /del, /find, /server, /cases, /status, /export, /help)
        if text.startswith("/stats"):
            total_leads = (await db.execute(select(func.count(Lead.id)))).scalar() or 0
            pending = (await db.execute(select(func.count(Lead.id)).where(Lead.status.in_([LeadStatus.PENDING, LeadStatus.DELIVERED])))).scalar() or 0
            in_progress = (await db.execute(select(func.count(Lead.id)).where(Lead.status == LeadStatus.IN_PROGRESS))).scalar() or 0
            contacted = (await db.execute(select(func.count(Lead.id)).where(Lead.status == LeadStatus.CONTACTED))).scalar() or 0
            spam = (await db.execute(select(func.count(Lead.id)).where(Lead.status == LeadStatus.SPAM))).scalar() or 0

            stats_msg = (
                f"📊 <b>Статистика заявок</b>\n"
                f"• Всего: <b>{total_leads}</b>\n"
                f"• В ожидании: <b>{pending}</b>\n"
                f"• В работе: <b>{in_progress}</b>\n"
                f"• Связались: <b>{contacted}</b>\n"
                f"• Спам: <b>{spam}</b>"
            )
            await send_reply_message(chat_id, stats_msg)
            return {"ok": True}

        elif text.startswith("/leads"):
            recent_leads = (await db.execute(select(Lead).order_by(Lead.id.desc()).limit(5))).scalars().all()
            if not recent_leads:
                await send_reply_message(chat_id, "Заявок пока нет.")
            else:
                lines = ["📋 <b>Последние заявки:</b>"]
                for l in recent_leads:
                    status_str = l.status.value if hasattr(l.status, "value") else str(l.status)
                    lines.append(f"#{l.id} | {html.escape(l.name)} (<code>{html.escape(l.contact)}</code>) — <i>{status_str}</i>")
                await send_reply_message(chat_id, "\n".join(lines))
            return {"ok": True}

        elif text.startswith("/del") or text.startswith("/delete"):
            parts = text.split()
            if len(parts) > 1 and parts[1].isdigit():
                lead_id = int(parts[1])
                res = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = res.scalar_one_or_none()
                if not lead:
                    await send_reply_message(chat_id, f"⚠️ Заявка #{lead_id} не найдена.")
                else:
                    lead_name = lead.name
                    lead_contact = lead.contact
                    msg_id_card = lead.telegram_message_id
                    await db.delete(lead)
                    await db.commit()

                    del_info = f"🗑 Заявка #{lead_id} ({html.escape(lead_name)}) удалена из базы."
                    await send_reply_message(chat_id, del_info)

                    # Обновляем карточку заявки, если сообщение сохранено
                    if msg_id_card and settings.TELEGRAM_CHAT_ID:
                        try:
                            card_text = f"🗑 <b>Заявка #{lead_id} удалена</b> (удалил {user_display})"
                            card_kb = {"inline_keyboard": [[{"text": "🗑 Удалено", "callback_data": "noop"}]]}
                            await TelegramBotService.edit_message_text(settings.TELEGRAM_CHAT_ID, msg_id_card, card_text, card_kb)
                        except Exception:
                            pass
            else:
                await send_reply_message(chat_id, "Использование: <code>/del &lt;ID&gt;</code>")
            return {"ok": True}

        elif text.startswith("/find ") or text.startswith("/search "):
            parts = text.split(maxsplit=1)
            q = parts[1].strip() if len(parts) > 1 else ""
            if not q:
                await send_reply_message(chat_id, "Использование: <code>/find &lt;запрос&gt;</code>")
            else:
                pattern = f"%{q}%"
                res = await db.execute(
                    select(Lead).where(
                        (Lead.name.ilike(pattern)) |
                        (Lead.contact.ilike(pattern)) |
                        (Lead.task_description.ilike(pattern))
                    ).order_by(Lead.id.desc()).limit(5)
                )
                found = res.scalars().all()
                if not found:
                    await send_reply_message(chat_id, f"По запросу «{html.escape(q)}» ничего не найдено.")
                else:
                    lines = [f"🔍 <b>Найдено ({len(found)}):</b>"]
                    for l in found:
                        st = l.status.value if hasattr(l.status, "value") else str(l.status)
                        lines.append(
                            f"#{l.id} | <b>{html.escape(l.name)}</b> (<code>{html.escape(l.contact)}</code>) — <i>{st}</i>\n"
                            f"<i>{html.escape(l.task_description[:70])}...</i>"
                        )
                    await send_reply_message(chat_id, "\n\n".join(lines))
            return {"ok": True}

        elif text.startswith("/server") or text.startswith("/sys") or text.startswith("/monitor"):
            server_report, kb = await get_server_status_card(db)
            await send_reply_message(chat_id, server_report, kb)
            return {"ok": True}

        elif text.startswith("/cases") or text.startswith("/portfolio"):
            res = await db.execute(select(Case).where(Case.is_published.is_(True)).order_by(Case.sort_order.asc()).limit(5))
            cases = res.scalars().all()
            if not cases:
                await send_reply_message(chat_id, "Портфолио пока пусто.")
            else:
                lines = ["💼 <b>Кейсы CASTLEWEB:</b>"]
                for c in cases:
                    cat_val = c.category.value if hasattr(c.category, "value") else str(c.category)
                    link_html = f' — <a href="{html.escape(c.live_url)}">ссылка</a>' if c.live_url else ""
                    lines.append(f"• <b>{html.escape(c.title)}</b> [{cat_val.upper()}]{link_html}\n{html.escape(c.short_description)}")
                lines.append("\n🌐 castleweb.ru")
                await send_reply_message(chat_id, "\n\n".join(lines))
            return {"ok": True}

        elif text.startswith("/status"):
            parts = text.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip().isdigit():
                lead_id = int(parts[1].strip())
                res = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = res.scalar_one_or_none()
                if not lead:
                    await send_reply_message(chat_id, f"⚠️ Заявка #{lead_id} не найдена.")
                else:
                    st_desc = {
                        LeadStatus.PENDING: "Ожидает инженера",
                        LeadStatus.DELIVERED: "В очереди",
                        LeadStatus.IN_PROGRESS: f"В работе ({lead.handled_by or 'Архитектор'})",
                        LeadStatus.CONTACTED: f"Связались ({lead.handled_by or 'Инженер'})",
                        LeadStatus.SPAM: "Отклонена",
                        LeadStatus.ARCHIVED: "Архив"
                    }.get(lead.status, str(lead.status.value))

                    lead_card_msg = (
                        f"📋 <b>Заявка #{lead.id}</b>\n"
                        f"Клиент: {html.escape(lead.name)}\n"
                        f"Статус: <b>{st_desc}</b>\n"
                        f"Бюджет: {html.escape(lead.budget or 'Не указан')}\n"
                        f"Создана: {lead.created_at.strftime('%d.%m.%Y %H:%M') if lead.created_at else '—'}"
                    )
                    await send_reply_message(chat_id, lead_card_msg)
            else:
                await send_reply_message(chat_id, "Использование: <code>/status &lt;ID&gt;</code>")
            return {"ok": True}

        elif text.startswith("/export"):
            import csv
            import io
            from datetime import datetime

            leads_res = await db.execute(select(Lead).order_by(Lead.id.desc()).limit(500))
            leads = leads_res.scalars().all()
            if not leads:
                await send_reply_message(chat_id, "Заявок для выгрузки пока нет.")
                return {"ok": True}

            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["ID", "Имя", "Контакт", "Бюджет", "Статус", "Город", "Страна", "IP", "Дата создания", "ТЗ / Описание", "Вложение"])
            for l in leads:
                writer.writerow([
                    l.id,
                    l.name,
                    l.contact,
                    l.budget or "",
                    l.status.value if hasattr(l.status, "value") else str(l.status),
                    l.geo_city or "",
                    l.geo_country or "",
                    l.ip_address or "",
                    l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else "",
                    (l.task_description or "").replace("\n", " "),
                    l.attachment_url or ""
                ])

            csv_bytes = csv_buffer.getvalue().encode("utf-8-sig")
            now_str = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"castleweb_leads_{now_str}.csv"
            caption = f"📊 <b>Выгрузка заявок</b> ({len(leads)} записей)"

            sent = await TelegramBotService.send_document(chat_id, filename, csv_bytes, caption=caption)
            if not sent:
                await send_reply_message(chat_id, "⚠️ Не удалось отправить файл. Проверьте права бота.")
            return {"ok": True}

        elif text.startswith("/help"):
            help_msg = (
                f"🛠 <b>Команды:</b>\n"
                f"/stats — статистика заявок\n"
                f"/leads — последние заявки\n"
                f"/find &lt;запрос&gt; — поиск по базе\n"
                f"/del &lt;id&gt; — удалить заявку\n"
                f"/status &lt;id&gt; — статус заявки\n"
                f"/server — состояние сервера\n"
                f"/cases — портфолио\n"
                f"/export — выгрузка в CSV"
            )
            await send_reply_message(chat_id, help_msg)
            return {"ok": True}


        # Б. ЛИЧНЫЕ СООБЩЕНИЯ ОТ КЛИЕНТА (chat_type == "private")
        if chat_type == "private":
            # 1. Прямая команда /demo
            if text.startswith("/demo") or (text.startswith("/start") and "demo" in text.lower()):
                domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
                parser_public_url = os.environ.get("PARSER_PUBLIC_URL", f"https://leads.{domain}").rstrip("/")
                try:
                    res = await request_parser_demo_access(from_id, username)
                    demo_text, demo_kb = format_demo_access_response(res, parser_public_url)

                    # Фиксируем в БД CRM выдачу, если аккаунт создан впервые
                    if res.get("status") == "created":
                        try:
                            grant_check = await db.execute(select(DemoGrant).where(DemoGrant.tg_user_id == str(from_id)))
                            if not grant_check.scalar_one_or_none():
                                db.add(DemoGrant(
                                    tg_user_id=str(from_id),
                                    tg_username=username,
                                    first_name=first_name,
                                    email=res.get("email", "")
                                ))
                                await db.commit()
                        except Exception as ge:
                            logger.warning(f"Failed to record DemoGrant: {ge}")

                    await send_reply_message(chat_id, demo_text, reply_markup=demo_kb)

                    if settings.TELEGRAM_CHAT_ID:
                        st = res.get("status")
                        if st == "created":
                            alert = f"🔔 Клиент {user_display} (ID: <code>{from_id}</code>) впервые активировал демо к парсеру ({res.get('email')})."
                        elif st == "exhausted":
                            alert = f"⚠️ Клиент {user_display} (ID: <code>{from_id}</code>) повторно запросил демо, но его лимит исчерпан."
                        else:
                            alert = f"ℹ️ Клиент {user_display} (ID: <code>{from_id}</code>) запросил данные своего демо-доступа повторно."
                        await send_reply_message(settings.TELEGRAM_CHAT_ID, alert)
                except Exception as e:
                    logger.error(f"Error creating demo user via /demo: {e}")
                    err_text = (
                        "⚠️ Сервер парсера сейчас перезагружается или временно недоступен.\n"
                        "Пожалуйста, повторите попытку через минуту или напишите дежурному разработчику: @kupidon996"
                    )
                    await send_reply_message(chat_id, err_text)
                return {"ok": True}

            # 2. Приветствие и главное меню (/start или /menu)
            if text.startswith("/start") or text.startswith("/menu"):
                parts = text.split(maxsplit=1)
                start_payload = parts[1] if len(parts) > 1 else ""

                if start_payload.startswith("lead_") or start_payload.isdigit():
                    lead_id_str = start_payload.replace("lead_", "")
                    try:
                        lead_id = int(lead_id_str)
                        res = await db.execute(select(Lead).where(Lead.id == lead_id))
                        lead = res.scalar_one_or_none()
                        if lead:
                            welcome_lead = (
                                f"👋 <b>Здравствуйте, {html.escape(lead.name)}!</b>\n\n"
                                f"Заявка <b>#{lead.id}</b> принята в работу.\n"
                                f"Сюда можно присылать любые файлы, ссылки и вопросы — дежурный инженер ответит в течение 15 минут."
                            )
                            buttons = {
                                "inline_keyboard": [
                                    [{"text": "🌐 Сайт castleweb.ru", "url": "https://castleweb.ru"}]
                                ]
                            }
                            await send_reply_message(chat_id, welcome_lead, reply_markup=buttons)

                            # Уведомляем группу инженеров
                            if settings.TELEGRAM_CHAT_ID:
                                client_handle = f"@{username}" if username else f"ID: <code>{from_id}</code>"
                                notify_eng = f"🔔 Клиент по заявке #{lead.id} ({html.escape(lead.name)}) открыл диалог с ботом ({client_handle})."
                                direct_btn = [{"text": "💬 Написать клиенту", "url": f"https://t.me/{username}"}] if username else []
                                reply_markup = {"inline_keyboard": [direct_btn]} if direct_btn else None
                                await send_reply_message(settings.TELEGRAM_CHAT_ID, notify_eng, reply_markup=reply_markup)
                            return {"ok": True}
                    except ValueError:
                        pass

                # Общее главное меню для клиента
                menu_text, menu_kb = get_client_main_menu(first_name)
                await send_reply_message(chat_id, menu_text, reply_markup=menu_kb)
                return {"ok": True}

            # 2. Любое сообщение / вопрос / фото / документ от клиента в ЛС
            has_media = bool(msg.get("document") or msg.get("photo") or msg.get("voice"))
            user_msg_text = text if text else ("📎 [Вложенный файл]" if has_media else "👋 [Обращение]")

            # 2.1. Автоответ клиенту
            client_reply = (
                f"✅ <b>Сообщение принято.</b>\n"
                f"Дежурный инженер ответит вам в этом чате в течение 15 минут."
            )
            await send_reply_message(chat_id, client_reply)

            # 2.2. Мгновенная пересылка и оповещение в закрытый чат инженеров
            if settings.TELEGRAM_CHAT_ID:
                direct_url = f"https://t.me/{username}" if username else f"tg://user?id={from_id}"
                reply_btn_text = f"💬 @{username}" if username else "💬 Клиент"
                media_note = "\n📎 <i>[Прикреплен файл/медиа]</i>" if has_media else ""

                eng_alert = (
                    f"📩 <b>Сообщение от клиента</b>\n"
                    f"👤 {html.escape(user_display)} (ID: <code>{from_id}</code>)\n\n"
                    f"<blockquote>{html.escape(user_msg_text)}</blockquote>"
                    f"{media_note}\n\n"
                    f"<i>Ответьте Reply на это сообщение, чтобы написать клиенту.</i>"
                )
                eng_buttons = {
                    "inline_keyboard": [
                        [{"text": reply_btn_text, "url": direct_url}]
                    ]
                }
                await send_reply_message(settings.TELEGRAM_CHAT_ID, eng_alert, reply_markup=eng_buttons)

                # Также пересылаем исходное медиа/сообщение инженерам
                try:
                    forward_url = build_telegram_api_url("forwardMessage")
                    async with httpx.AsyncClient(timeout=6.0) as client:
                        await client.post(forward_url, json={
                            "chat_id": settings.TELEGRAM_CHAT_ID,
                            "from_chat_id": chat_id,
                            "message_id": msg.get("message_id")
                        })
                except Exception as fwd_err:
                    logger.warning(f"Could not forward message to team chat: {fwd_err}")

            return {"ok": True}

    return {"ok": True}


@router.get("/bot-info", summary="Get Telegram Bot Public Info")
async def get_bot_info():
    """
    Возвращает юзернейм и статус бота для фронтенда.
    """
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN in ("your_bot_token_here", ""):
        return {"ok": False, "username": None}
    url = build_telegram_api_url("getMe")
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            data = resp.json()
            if data.get("ok"):
                return {"ok": True, "username": data["result"].get("username")}
    except Exception:
        pass
    return {"ok": False, "username": None}
