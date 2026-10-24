import os
import shutil
import time
import re
import logging
import html
import httpx
import secrets
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
KNOWN_ADMIN_CHATS: set[str] = {"1878543896"}


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
                logger.warning(f"Telegram sendMessage returned not ok for {chat_id}: {data}")
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
                    fb_resp = await client.post(url, json=payload)
                    if not fb_resp.json().get("ok"):
                        logger.error(f"Fallback plain-text sendMessage also failed: {fb_resp.json()}")
            else:
                logger.info(f"✅ Telegram message delivered to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send reply to chat {chat_id}: {e}", exc_info=True)


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
    configured_url = (getattr(settings, "PARSER_INTERNAL_URL", "") or os.environ.get("PARSER_INTERNAL_URL", "")).strip()
    raw_urls = [
        "http://leadhunter:8000",
        configured_url,
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    internal_urls = []
    for u in raw_urls:
        if u and u.rstrip("/") not in internal_urls:
            internal_urls.append(u.rstrip("/"))

    configured_secret = (getattr(settings, "INTERNAL_API_SECRET", "") or os.environ.get("INTERNAL_API_SECRET", "")).strip()
    secrets_to_try = [s for s in dict.fromkeys([configured_secret, "castleweb-internal-demo-secret"]) if s]

    last_error = None
    for secret in secrets_to_try:
        payload = {
            "tg_user_id": str(tg_user_id),
            "tg_username": username or "",
            "secret_key": secret
        }
        for base_url in internal_urls:
            url = f"{base_url}/api/internal/create-demo-user"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url, json=payload, headers={"X-Internal-Secret": secret})
                    if resp.status_code == 200:
                        return resp.json()
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)

    raise RuntimeError(f"Parser API unavailable: {last_error}")


async def request_parser_paid_access(tg_user_id: str | int, plan: str, username: str | None = None) -> dict:
    """
    Обращается к внутреннему API LeadHunter Pro для активации/продления коммерческой подписки:
    - 1m: 2 000 ₽ (30 дней)
    - 3m: 5 000 ₽ (90 дней)
    - 1y: 10 000 ₽ (365 дней)
    - lifetime: 50 000 ₽ (бессрочно)
    Суточный лимит: 100 компаний/день.
    """
    configured_url = (getattr(settings, "PARSER_INTERNAL_URL", "") or os.environ.get("PARSER_INTERNAL_URL", "")).strip()
    raw_urls = [
        "http://leadhunter:8000",
        configured_url,
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    internal_urls = []
    for u in raw_urls:
        if u and u.rstrip("/") not in internal_urls:
            internal_urls.append(u.rstrip("/"))

    configured_secret = (getattr(settings, "INTERNAL_API_SECRET", "") or os.environ.get("INTERNAL_API_SECRET", "")).strip()
    secrets_to_try = [s for s in dict.fromkeys([configured_secret, "castleweb-internal-demo-secret"]) if s]

    last_error = None
    for secret in secrets_to_try:
        payload = {
            "tg_user_id": str(tg_user_id),
            "plan": plan,
            "tg_username": username or "",
            "secret_key": secret
        }
        for base_url in internal_urls:
            url = f"{base_url}/api/internal/grant-paid-access"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url, json=payload, headers={"X-Internal-Secret": secret})
                    if resp.status_code == 200:
                        return resp.json()
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)

    raise RuntimeError(f"Parser API unavailable: {last_error}")


async def request_parser_user_cabinet(tg_user_id: str | int) -> dict:
    """
    Запрашивает актуальное состояние ЛК пользователя из сервиса LeadHunter:
    - тариф подписки
    - дату окончания
    - текущий суточный расход (из 100 компаний)
    - логин и статус
    """
    configured_url = (getattr(settings, "PARSER_INTERNAL_URL", "") or os.environ.get("PARSER_INTERNAL_URL", "")).strip()
    raw_urls = [
        "http://leadhunter:8000",
        configured_url,
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    internal_urls = []
    for u in raw_urls:
        if u and u.rstrip("/") not in internal_urls:
            internal_urls.append(u.rstrip("/"))

    configured_secret = (getattr(settings, "INTERNAL_API_SECRET", "") or os.environ.get("INTERNAL_API_SECRET", "")).strip()
    secrets_to_try = [s for s in dict.fromkeys([configured_secret, "castleweb-internal-demo-secret"]) if s]

    last_error = None
    for secret in secrets_to_try:
        params = {"tg_user_id": str(tg_user_id)}
        for base_url in internal_urls:
            url = f"{base_url}/api/internal/user-cabinet"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url, params=params, headers={"X-Internal-Secret": secret})
                    if resp.status_code == 200:
                        return resp.json()
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)

    raise RuntimeError(f"Parser API unavailable: {last_error}")


async def request_parser_reset_password(tg_user_id: str | int) -> dict:
    """
    Запрашивает генерацию нового пароля для пользователя в LeadHunter.
    """
    configured_url = (getattr(settings, "PARSER_INTERNAL_URL", "") or os.environ.get("PARSER_INTERNAL_URL", "")).strip()
    raw_urls = [
        "http://leadhunter:8000",
        configured_url,
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    internal_urls = []
    for u in raw_urls:
        if u and u.rstrip("/") not in internal_urls:
            internal_urls.append(u.rstrip("/"))

    configured_secret = (getattr(settings, "INTERNAL_API_SECRET", "") or os.environ.get("INTERNAL_API_SECRET", "")).strip()
    secrets_to_try = [s for s in dict.fromkeys([configured_secret, "castleweb-internal-demo-secret"]) if s]

    last_error = None
    for secret in secrets_to_try:
        payload = {"tg_user_id": str(tg_user_id)}
        for base_url in internal_urls:
            url = f"{base_url}/api/internal/reset-password"
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url, json=payload, headers={"X-Internal-Secret": secret})
                    if resp.status_code == 200:
                        return resp.json()
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)

    raise RuntimeError(f"Parser API unavailable: {last_error}")


async def request_parser_clear_history(tg_user_id: str | int, clear_all: bool = False) -> dict:
    """
    Запрашивает очистку истории поисковых кампаний и лидов в LeadHunter.
    """
    configured_url = (getattr(settings, "PARSER_INTERNAL_URL", "") or os.environ.get("PARSER_INTERNAL_URL", "")).strip()
    raw_urls = [
        "http://leadhunter:8000",
        configured_url,
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    internal_urls = []
    for u in raw_urls:
        if u and u.rstrip("/") not in internal_urls:
            internal_urls.append(u.rstrip("/"))

    configured_secret = (getattr(settings, "INTERNAL_API_SECRET", "") or os.environ.get("INTERNAL_API_SECRET", "")).strip()
    secrets_to_try = [s for s in dict.fromkeys([configured_secret, "castleweb-internal-demo-secret"]) if s]

    last_error = None
    for secret in secrets_to_try:
        payload = {"tg_user_id": str(tg_user_id), "clear_all": clear_all}
        for base_url in internal_urls:
            url = f"{base_url}/api/internal/clear-user-history"
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(url, json=payload, headers={"X-Internal-Secret": secret})
                    if resp.status_code == 200:
                        return resp.json()
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)

    raise RuntimeError(f"Parser API unavailable: {last_error}")



async def request_parser_cleanup_db() -> dict:
    """
    Запрашивает очистку базы данных SQLite, сброс WAL и VACUUM в LeadHunter.
    """
    configured_url = (getattr(settings, "PARSER_INTERNAL_URL", "") or os.environ.get("PARSER_INTERNAL_URL", "")).strip()
    raw_urls = [
        "http://leadhunter:8000",
        configured_url,
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]
    internal_urls = []
    for u in raw_urls:
        if u and u.rstrip("/") not in internal_urls:
            internal_urls.append(u.rstrip("/"))

    configured_secret = (getattr(settings, "INTERNAL_API_SECRET", "") or os.environ.get("INTERNAL_API_SECRET", "")).strip()
    secrets_to_try = [s for s in dict.fromkeys([configured_secret, "castleweb-internal-demo-secret"]) if s]

    last_error = None
    for secret in secrets_to_try:
        for base_url in internal_urls:
            url = f"{base_url}/api/settings/cleanup"
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, headers={"X-Internal-Secret": secret})
                    if resp.status_code == 200:
                        return resp.json()
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)

    raise RuntimeError(f"Parser API unavailable: {last_error}")


def format_user_cabinet(res: dict, parser_public_url: str, new_pass: str | None = None) -> tuple[str, dict]:
    """
    Формирует красивый интерфейс Личного Кабинета подписчика LeadHunter в Telegram:
    - тариф и статус подписки
    - срок действия
    - использованный дневной лимит из 100 компаний
    - ссылку на сайт и учетные данные
    - акцент на то, что лиды приходят ТОЛЬКО в браузере
    """
    st = res.get("status")
    if st == "not_found":
        text = (
            "👤 <b>Личный кабинет LeadHunter</b>\n\n"
            "У вас пока нет зарегистрированного аккаунта в парсере Яндекс.Карт.\n\n"
            "Вы можете получить бесплатный демо-доступ (5 запросов) или оформить коммерческую подписку "
            "со 100 компаниями в день, выгрузкой в Excel и контактами (телефоны, Telegram, сайты)."
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🔑 Получить демо-доступ", "callback_data": "get_demo_access"}],
                [{"text": "💳 Оформить подписку", "callback_data": "buy_parser_menu"}],
                [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
            ]
        }
        return text, kb

    is_paid = bool(res.get("is_paid")) or res.get("role") == "paid"
    is_admin = bool(res.get("is_admin")) or res.get("role") in ("admin", "superuser", "root")
    plan_title = res.get("plan_title", "Тариф не указан")
    until_human = res.get("subscription_until_human", "—")
    daily_parsed = res.get("daily_companies_parsed", 0)
    daily_limit = res.get("daily_limit", 100)
    daily_rem = res.get("daily_remaining", max(0, daily_limit - daily_parsed))
    is_expired = res.get("is_expired", False)
    email = res.get("email", "—")

    if is_admin:
        badge = "👑 <b>Администратор студии</b> (Безлимитный доступ)"
        limit_line = "⚡️ <b>Лимит:</b> Без ограничений"
    elif is_paid:
        if is_expired:
            badge = "⚠️ <b>Подписка истекла</b> (требуется продление)"
        else:
            badge = f"💎 <b>Платная подписка: {plan_title}</b>"
        limit_line = (
            f"📊 <b>Расход сегодня:</b> <code>{daily_parsed}</code> из <code>{daily_limit}</code> компаний\n"
            f"⚡️ <b>Осталось на сегодня:</b> <b>{daily_rem}</b> компаний\n"
            f"🔄 <i>(Лимит автоматически обновляется каждый день в 00:00 UTC)</i>"
        )
    else:
        badge = "🧪 <b>Демо-режим</b> (Тестовый период)"
        demo_left = res.get("demo_searches_left", 0)
        limit_line = f"📊 <b>Осталось демо-поисков:</b> <b>{demo_left} из 5</b> (до 5 компаний за раз)"

    pass_block = f"\n🔑 <b>Ваш новый пароль:</b> <code>{new_pass}</code>\n" if new_pass else ""

    text = (
        f"👤 <b>ЛИЧНЫЙ КАБИНЕТ LEADHUNTER</b>\n\n"
        f"Статус: {badge}\n"
        f"📅 <b>Срок действия:</b> {until_human}\n\n"
        f"{limit_line}\n\n"
        f"🌐 <b>Адрес веб-панели:</b> <a href=\"{parser_public_url}\">{parser_public_url}</a>\n"
        f"👤 <b>Логин для входа:</b> <code>{email}</code>"
        f"{pass_block}\n"
        f"💡 <i>Лиды отображаются только в веб-интерфейсе в браузере (уведомления в Telegram отключены, чтобы не спамить чат).</i>"
    )

    kb = {
        "inline_keyboard": [
            [{"text": "🚀 Войти в веб-панель LeadHunter", "url": parser_public_url}],
            [
                {"text": "🔄 Обновить данные", "callback_data": "client_cabinet"},
                {"text": "🔑 Сбросить пароль", "callback_data": "cabinet_reset_password"}
            ],
            [{"text": "🗑 Очистить историю поисков", "callback_data": "cabinet_clear_history"}],
            [{"text": "💳 Продлить / Сменить тариф", "callback_data": "buy_parser_menu"}],
            [{"text": "💬 Поддержка менеджера (@kupidon996)", "url": "https://t.me/kupidon996"}],
            [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
        ]
    }
    return text, kb


def get_buy_parser_menu() -> tuple[str, dict]:
    """
    Формирует текст и кнопки тарифов платного доступа к парсеру LeadHunter.
    """
    text = (
        "💳 <b>Тарифы на доступ к парсеру Яндекс.Карт (LeadHunter)</b>\n\n"
        "⚡️ <b>Что входит в коммерческую версию:</b>\n"
        "• Сбор любых категорий и городов по всей РФ и СНГ\n"
        "• Контакты: прямые телефоны, сайты, Telegram, WhatsApp\n"
        "• Автоматический Tech & SEO аудит и выявление критических дефектов\n"
        "• Выгрузка всех собранных баз в Excel (.xlsx) и CSV\n"
        "• Дневной лимит: <b>100 спарсенных компаний в день</b> (обновляется ежедневно в 00:00 UTC)\n\n"
        "💰 <b>Стоимость подписки:</b>\n"
        "• <b>1 месяц</b> — 2 000 ₽\n"
        "• <b>3 месяца</b> — 5 000 ₽ <i>(скидка ~17%)</i>\n"
        "• <b>1 год</b> — 10 000 ₽ <i>(скидка ~58%)</i>\n"
        "• <b>Бессрочно</b> — 50 000 ₽ <i>(вечный доступ навсегда)</i>\n\n"
        "Нажмите <b>«📩 Оставить заявку на покупку»</b> — наш менеджер свяжется с вами в Telegram "
        "для согласования оплаты (СБП, карта или счет). Сразу после оплаты доступ активируется в 1 клик!"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "📩 Оставить заявку на покупку", "callback_data": "buy_parser_request"}],
            [{"text": "💬 Написать менеджеру (@kupidon996)", "url": "https://t.me/kupidon996"}],
            [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
        ]
    }
    return text, kb


def get_manager_grant_keyboard(client_tg_id: str | int) -> dict:
    """
    Формирует инлайн-клавиатуру для менеджеров в Telegram-группе для мгновенной выдачи доступа.
    """
    return {
        "inline_keyboard": [
            [
                {"text": "1 мес (2 000 ₽)", "callback_data": f"grant_sub:{client_tg_id}:1m"},
                {"text": "3 мес (5 000 ₽)", "callback_data": f"grant_sub:{client_tg_id}:3m"}
            ],
            [
                {"text": "1 год (10 000 ₽)", "callback_data": f"grant_sub:{client_tg_id}:1y"},
                {"text": "Бессрочно (50 000 ₽)", "callback_data": f"grant_sub:{client_tg_id}:lifetime"}
            ],
            [
                {"text": "❌ Отклонить заявку", "callback_data": f"decline_sub:{client_tg_id}"}
            ]
        ]
    }


def format_demo_access_response(res: dict, parser_public_url: str) -> tuple[str, dict]:
    """
    Формирует текст и клавиатуру в зависимости от статуса демо-доступа:
    - 'paid': активный платный аккаунт (перенаправляет в ЛК);
    - 'created': выдан впервые (5 запросов);
    - 'already_active': напоминание данных существующего аккаунта (тест выдается только 1 раз);
    - 'exhausted': 5 запросов полностью исчерпаны (тест завершен, связь с разработчиком).
    """
    status = res.get("status")

    if status == "paid":
        return format_user_cabinet(res, parser_public_url)

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
            "Чтобы приобрести полноценную версию парсера (100 организаций в день, сбор любых ниш, экспорт в Excel, контакты и аудит сайтов):\n"
            "• 1 месяц — 2 000 ₽\n"
            "• 3 месяца — 5 000 ₽\n"
            "• 1 год — 10 000 ₽\n"
            "• Бессрочно — 50 000 ₽"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "💳 Купить доступ к парсеру", "callback_data": "buy_parser_menu"}],
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
                [{"text": "💳 Купить полный доступ (100 орг/день)", "callback_data": "buy_parser_menu"}],
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
            [{"text": "💳 Купить постоянный доступ", "callback_data": "buy_parser_menu"}],
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
            [{"text": "👤 Личный кабинет LeadHunter", "callback_data": "client_cabinet"}],
            [{"text": "🔑 Демо-доступ к парсеру", "callback_data": "get_demo_access"}],
            [{"text": "💳 Купить доступ к парсеру (от 2к)", "callback_data": "buy_parser_menu"}],
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
    expected_secret = (settings.TELEGRAM_WEBHOOK_SECRET or "").strip().strip("'\"")
    if expected_secret:
        incoming_token = (request.headers.get("x-telegram-bot-api-secret-token", "") or "").strip().strip("'\"")
        if not incoming_token or not secrets.compare_digest(incoming_token, expected_secret):
            logger.warning(f"Webhook rejected: invalid or missing secret token from {request.client.host if request.client else 'unknown'}")
            return {"ok": False}

    update = await request.json()
    logger.info(f"📩 Telegram webhook update received: keys={list(update.keys())}")

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

        elif data == "client_cabinet":
            await answer_callback_query(cb_id, "Загрузка Личного кабинета...")
            domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
            parser_public_url = os.environ.get("PARSER_PUBLIC_URL", f"https://leads.{domain}").rstrip("/")
            try:
                res = await request_parser_user_cabinet(user.get("id", ""))
                cab_text, cab_kb = format_user_cabinet(res, parser_public_url)
                if message_id and chat_id:
                    try:
                        await TelegramBotService.edit_message_text(chat_id, message_id, cab_text, cab_kb)
                    except Exception:
                        await send_reply_message(chat_id, cab_text, cab_kb)
                else:
                    await send_reply_message(chat_id, cab_text, cab_kb)
            except Exception as e:
                logger.error(f"Error loading user cabinet: {e}")
                err_text = "⚠️ Не удалось связаться с сервером парсера. Попробуйте через минуту или напишите @kupidon996"
                await send_reply_message(chat_id, err_text)

        elif data == "cabinet_reset_password":
            await answer_callback_query(cb_id, "Генерация нового пароля...")
            domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
            parser_public_url = os.environ.get("PARSER_PUBLIC_URL", f"https://leads.{domain}").rstrip("/")
            try:
                reset_res = await request_parser_reset_password(user.get("id", ""))
                new_pass = reset_res.get("new_password")
                cab_res = await request_parser_user_cabinet(user.get("id", ""))
                cab_text, cab_kb = format_user_cabinet(cab_res, parser_public_url, new_pass=new_pass)
                if message_id and chat_id:
                    try:
                        await TelegramBotService.edit_message_text(chat_id, message_id, cab_text, cab_kb)
                    except Exception:
                        await send_reply_message(chat_id, cab_text, cab_kb)
                else:
                    await send_reply_message(chat_id, cab_text, cab_kb)
            except Exception as e:
                logger.error(f"Error resetting password: {e}")
                await answer_callback_query(cb_id, "⚠️ Ошибка сброса пароля", show_alert=True)

        elif data == "cabinet_clear_history":
            confirm_text = (
                "⚠️ <b>Очистить историю поисков?</b>\n\n"
                "Все ваши поисковые кампании, собранные контакты компаний и результаты аудитов "
                "будут удалены из веб-панели LeadHunter.\n\n"
                "Вы уверены, что хотите продолжить?"
            )
            confirm_kb = {
                "inline_keyboard": [
                    [{"text": "✅ Да, очистить историю", "callback_data": "confirm_clear_history"}],
                    [{"text": "❌ Отмена", "callback_data": "client_cabinet"}]
                ]
            }
            if message_id and chat_id:
                try:
                    await TelegramBotService.edit_message_text(chat_id, message_id, confirm_text, confirm_kb)
                except Exception:
                    await send_reply_message(chat_id, confirm_text, confirm_kb)
            else:
                await send_reply_message(chat_id, confirm_text, confirm_kb)

        elif data == "confirm_clear_history":
            await answer_callback_query(cb_id, "Очищаем историю...")
            try:
                res = await request_parser_clear_history(user.get("id", ""))
                del_count = res.get("deleted_count", 0)
                await answer_callback_query(cb_id, f"✅ История очищена! Удалено: {del_count} кампаний", show_alert=True)

                domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
                parser_public_url = os.environ.get("PARSER_PUBLIC_URL", f"https://leads.{domain}").rstrip("/")
                cab_res = await request_parser_user_cabinet(user.get("id", ""))
                cab_text, cab_kb = format_user_cabinet(cab_res, parser_public_url)
                if message_id and chat_id:
                    try:
                        await TelegramBotService.edit_message_text(chat_id, message_id, cab_text, cab_kb)
                    except Exception:
                        await send_reply_message(chat_id, cab_text, cab_kb)
            except Exception as e:
                logger.error(f"Error confirming clear history: {e}")
                await answer_callback_query(cb_id, "⚠️ Ошибка при очистке истории", show_alert=True)

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
            res = await db.execute(select(Case).where(Case.is_published.is_(True)).order_by(Case.sort_order.asc()).limit(5))
            cases = res.scalars().all()
            lines = ["💼 <b>Избранные проекты CASTLEWEB:</b>\n"]
            if cases:
                for i, c in enumerate(cases, 1):
                    lines.append(f"<b>[{i:02d}] {html.escape(c.title)}</b>\n{html.escape(c.short_description)}")
            else:
                lines.append("<b>[01] Onyx OS — Шелл для ПК-клуба</b>\nСпециализированная операционная оболочка (шелл) и лаунчер для ПК-клубов и сим-рейсинга на Unreal/DirectX.")
                lines.append("<b>[02] Skog Chalet & Hytte Control</b>\nПремиальный сервис загородного отдыха: мобильный кабинет гостя, программа лояльности и умная сводка бронирований.")
                lines.append("<b>[03] LeadHunter — Парсер Яндекс.Карт</b>\nАвтономный сервис парсинга организаций: телефоны, сайты, адреса, Telegram с экспортом в Excel.")
            lines.append("\n💡 <i>Вы можете протестировать демо-версию парсера прямо сейчас!</i>")
            cases_text = "\n\n".join(lines)
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

        elif data == "buy_parser_menu":
            await answer_callback_query(cb_id, "Тарифы парсера")
            tariffs_text, tariffs_kb = get_buy_parser_menu()
            if message_id and chat_id:
                try:
                    await TelegramBotService.edit_message_text(chat_id, message_id, tariffs_text, tariffs_kb)
                except Exception:
                    await send_reply_message(chat_id, tariffs_text, tariffs_kb)
            else:
                await send_reply_message(chat_id, tariffs_text, tariffs_kb)

        elif data == "buy_parser_request":
            await answer_callback_query(cb_id, "Заявка отправлена!")
            confirm_text = (
                "✅ <b>Ваша заявка принята!</b>\n\n"
                "Наш менеджер уже получил уведомление и свяжется с вами в Telegram "
                "в течение нескольких минут для предоставления реквизитов (СБП, карта или счет).\n\n"
                "После подтверждения оплаты доступ к веб-панели парсера активируется автоматически, "
                "и бот пришлет вам персональный логин и пароль."
            )
            confirm_kb = {
                "inline_keyboard": [
                    [{"text": "💬 Написать менеджеру сейчас", "url": "https://t.me/kupidon996"}],
                    [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
                ]
            }
            if message_id and chat_id:
                try:
                    await TelegramBotService.edit_message_text(chat_id, message_id, confirm_text, confirm_kb)
                except Exception:
                    await send_reply_message(chat_id, confirm_text, confirm_kb)
            else:
                await send_reply_message(chat_id, confirm_text, confirm_kb)

            if settings.TELEGRAM_CHAT_ID:
                client_id = user.get("id")
                alert_text = (
                    "💳 <b>НОВАЯ ЗАЯВКА НА ПОКУПКУ ПАРСЕРА КАРТ</b>\n\n"
                    f"👤 <b>Клиент:</b> {user_display}\n"
                    f"🆔 <b>Telegram ID:</b> <code>{client_id}</code>\n"
                    f"🔗 <b>Профиль:</b> tg://user?id={client_id}\n\n"
                    "💰 <b>Тарифы (суточный лимит 100 компаний):</b>\n"
                    "• 1 мес — 2 000 ₽ | 3 мес — 5 000 ₽\n"
                    "• 1 год — 10 000 ₽ | Бессрочно — 50 000 ₽\n\n"
                    "👉 Свяжитесь с клиентом в ЛС, передайте реквизиты и нажмите нужную кнопку для выдачи доступа:"
                )
                mgr_kb = get_manager_grant_keyboard(client_id)
                await send_reply_message(settings.TELEGRAM_CHAT_ID, alert_text, reply_markup=mgr_kb)

        elif data.startswith("grant_sub:"):
            parts = data.split(":")
            if len(parts) >= 3:
                target_client_id = parts[1]
                target_plan = parts[2]
                try:
                    res = await request_parser_paid_access(target_client_id, target_plan)
                    domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
                    parser_public_url = os.environ.get("PARSER_PUBLIC_URL", f"https://leads.{domain}").rstrip("/")

                    plan_title = res.get("plan_title", target_plan)
                    until_human = res.get("subscription_until_human", "Бессрочно")

                    await answer_callback_query(cb_id, f"✅ Выдано: {plan_title}!")

                    # Обновляем карточку в группе менеджеров
                    updated_group_msg = (
                        f"✅ <b>ДОСТУП К ПАРСЕРУ ВЫДАН: {plan_title}</b>\n\n"
                        f"👤 <b>Клиент:</b> <a href=\"tg://user?id={target_client_id}\">Клиент #{target_client_id}</a> (ID: <code>{target_client_id}</code>)\n"
                        f"🔑 <b>Логин в веб-панели:</b> <code>{res.get('email')}</code>\n"
                        f"📅 <b>Срок действия:</b> {until_human}\n"
                        f"⚡️ <b>Суточный лимит:</b> 100 компаний в день\n"
                        f"👨‍💼 <b>Выдал менеджер:</b> {user_display}"
                    )
                    done_kb = {"inline_keyboard": [[{"text": f"✅ Активировано: {plan_title}", "callback_data": "noop"}]]}
                    if message_id and chat_id:
                        await TelegramBotService.edit_message_text(chat_id, message_id, updated_group_msg, done_kb)

                    # Отправляем сообщение клиенту в личный чат Telegram
                    client_notification = (
                        "🎉 <b>Оплата подтверждена! Доступ к парсеру LeadHunter активирован</b>\n\n"
                        f"Тариф: <b>{plan_title}</b>\n"
                        f"Срок действия: <b>{until_human}</b>\n"
                        f"Дневной лимит: <b>100 спарсенных организаций в день</b> (обновляется каждые сутки в полночь)\n\n"
                        f"🌐 <b>Адрес панели:</b> <a href=\"{parser_public_url}\">{parser_public_url}</a>\n"
                        f"👤 <b>Логин:</b> <code>{res.get('email')}</code>\n"
                        f"🔑 <b>Пароль:</b> <code>{res.get('password')}</code>\n\n"
                        "📱 <i>Управлять аккаунтом, смотреть суточный остаток и сбрасывать пароль можно в Личном кабинете прямо в боте (команда /lk).</i>\n"
                        "💡 <i>Спарсенные компании и контакты выводятся только в веб-интерфейсе в браузере.</i>"
                    )
                    client_kb = {
                        "inline_keyboard": [
                            [{"text": "🚀 Войти в панель LeadHunter", "url": parser_public_url}],
                            [{"text": "👤 Личный кабинет", "callback_data": "client_cabinet"}],
                            [{"text": "💬 Поддержка (@kupidon996)", "url": "https://t.me/kupidon996"}],
                            [{"text": "🔙 Главное меню", "callback_data": "client_menu"}]
                        ]
                    }
                    await send_reply_message(int(target_client_id), client_notification, reply_markup=client_kb)
                except Exception as ex:
                    logger.error(f"Error granting subscription: {ex}")
                    await answer_callback_query(cb_id, f"⚠️ Ошибка: {str(ex)[:50]}", show_alert=True)

        elif data.startswith("decline_sub:"):
            parts = data.split(":")
            if len(parts) >= 2:
                target_client_id = parts[1]
                await answer_callback_query(cb_id, "Заявка отклонена")
                decline_msg = (
                    f"❌ <b>Заявка на покупку для ID {target_client_id} отклонена</b>\n"
                    f"👨‍💼 <b>Менеджер:</b> {user_display}"
                )
                del_kb = {"inline_keyboard": [[{"text": "❌ Заявка отклонена", "callback_data": "noop"}]]}
                if message_id and chat_id:
                    await TelegramBotService.edit_message_text(chat_id, message_id, decline_msg, del_kb)


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

        # Регистрация администраторов студии для персональных уведомлений
        clean_user = (username or "").lower().lstrip("@")
        if clean_user in ("kupidon996", "ya_emildjan", "castleweb_admin", "admin") or str(from_id) == "1878543896":
            if from_id:
                KNOWN_ADMIN_CHATS.add(str(from_id))
            if chat_id and chat_type == "private":
                KNOWN_ADMIN_CHATS.add(str(chat_id))
            try:
                redis = await get_redis_client()
                if redis:
                    if from_id:
                        await redis.sadd("castleweb:admin_chats", str(from_id))
                    if chat_id and chat_type == "private":
                        await redis.sadd("castleweb:admin_chats", str(chat_id))
            except Exception:
                pass

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

        elif text.startswith("/fl") or text.startswith("/kwork") or text.startswith("/workspace") or text.startswith("/freelance") or text.startswith("/orders"):
            target_plat = None
            if text.startswith("/fl"):
                target_plat = "fl"
                plat_header = "биржи FL.ru (бесплатный отклик)"
            elif text.startswith("/kwork"):
                target_plat = "kwork"
                plat_header = "биржи Kwork"
            elif text.startswith("/workspace"):
                target_plat = "workspace"
                plat_header = "биржи Workspace (Тендеры)"
            else:
                plat_header = "бирж фриланса"

            if chat_id:
                KNOWN_ADMIN_CHATS.add(str(chat_id))
            if from_id:
                KNOWN_ADMIN_CHATS.add(str(from_id))
            try:
                redis = await get_redis_client()
                if redis:
                    if chat_id:
                        await redis.sadd("castleweb:admin_chats", str(chat_id))
                    if from_id:
                        await redis.sadd("castleweb:admin_chats", str(from_id))
            except Exception:
                pass

            internal_urls = [
                "http://leadhunter:8000",
                getattr(settings, "PARSER_INTERNAL_URL", "") or os.environ.get("PARSER_INTERNAL_URL", "").strip(),
            ]
            secret = getattr(settings, "INTERNAL_API_SECRET", "") or os.environ.get("INTERNAL_API_SECRET", "castleweb-internal-demo-secret")
            headers = {"X-Internal-Secret": secret}

            last_error = None
            found_resp = None

            query_params = ["page=1", "page_size=5"]
            if target_plat:
                query_params.append(f"platform={target_plat}")
                if target_plat == "fl":
                    query_params.append("is_free=true")
            qs = "&".join(query_params)

            for base_url in filter(None, internal_urls):
                b_url = base_url.rstrip("/")
                try:
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                        # Запускаем шаг опроса в фоне
                        try:
                            await client.post(f"{b_url}/api/fl/poll", headers=headers)
                        except Exception:
                            pass

                        # 1. Запрос заказов с заголовком X-Internal-Secret
                        resp = await client.get(f"{b_url}/api/fl/orders?{qs}", headers=headers)

                        # 2. Если парсер вернул 401 (старый контейнер без X-Internal-Secret) — мгновенная авторизация через /login
                        if resp.status_code == 401:
                            login_resp = await client.post(
                                f"{b_url}/login",
                                data={"email": "admin@lead.pro", "password": "AdminPass123!_ChangeMe"}
                            )
                            if login_resp.status_code in (200, 303):
                                resp = await client.get(f"{b_url}/api/fl/orders?{qs}")

                        if resp.status_code == 200:
                            found_resp = resp.json()
                            break
                        else:
                            last_error = f"код {resp.status_code}"
                except Exception as ex:
                    last_error = str(ex)

            if found_resp is not None:
                items = found_resp.get("items", [])
                if not items:
                    await send_reply_message(chat_id, f"ℹ️ На {plat_header} пока нет сохраненных подходящих заказов. Опрос запущен в фоне, новые заказы скоро появятся!")
                else:
                    msg_lines = [f"⚡️ <b>Свежие заказы с {plat_header}:</b>\n"]
                    for ord_item in items:
                        p = ord_item.get("price_raw") or "По договоренности"
                        t = ord_item.get("title", "")
                        u = ord_item.get("url", "https://www.fl.ru/projects/")
                        cat = ord_item.get("category_name", "Разработка")
                        plat = (ord_item.get("platform") or "fl").upper()
                        msg_lines.append(f"📌 <a href=\"{u}\"><b>{html.escape(t)}</b></a>\n💰 <b>{html.escape(str(p))}</b> | 🏷 <b>[{plat}]</b> 📁 <i>{html.escape(str(cat))}</i>\n")
                    msg_lines.append("🟢 <i>Авто-мониторинг активен (15-20 сек). Все новые заказы автоматически приходят сюда.</i>")
                    await send_reply_message(chat_id, "\n".join(msg_lines))
            else:
                await send_reply_message(chat_id, f"⚠️ Не удалось связаться с парсером ({last_error or 'ошибка соединения'}).")
            return {"ok": True}

        elif text.startswith("/cases") or text.startswith("/portfolio"):
            domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
            res = await db.execute(select(Case).where(Case.is_published.is_(True)).order_by(Case.sort_order.asc()).limit(5))
            cases = res.scalars().all()
            lines = ["💼 <b>Избранные проекты CASTLEWEB:</b>\n"]
            if cases:
                for i, c in enumerate(cases, 1):
                    lines.append(f"<b>[{i:02d}] {html.escape(c.title)}</b>\n{html.escape(c.short_description)}")
            else:
                lines.append("<b>[01] Onyx OS — Шелл для ПК-клуба</b>\nСпециализированная операционная оболочка (шелл) и лаунчер для ПК-клубов и сим-рейсинга на Unreal/DirectX.")
                lines.append("<b>[02] Skog Chalet & Hytte Control</b>\nПремиальный сервис загородного отдыха: мобильный кабинет гостя, программа лояльности и умная сводка бронирований.")
                lines.append("<b>[03] LeadHunter — Парсер Яндекс.Карт</b>\nАвтономный сервис парсинга организаций: телефоны, сайты, адреса, Telegram с экспортом в Excel.")
            lines.append(f"\n🌐 <a href=\"https://{domain}/cases.html\">Все кейсы на сайте castleweb.ru/cases.html</a>")
            cases_kb = {
                "inline_keyboard": [
                    [{"text": "🔑 Получить демо LeadHunter", "callback_data": "get_demo_access"}],
                    [{"text": "🌐 Все кейсы на сайте", "url": f"https://{domain}/cases.html"}]
                ]
            }
            await send_reply_message(chat_id, "\n\n".join(lines), reply_markup=cases_kb)
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

        elif text.startswith("/id") or text.startswith("/whoami"):
            await send_reply_message(
                chat_id,
                f"🆔 <b>Ваш Telegram ID:</b> <code>{from_id}</code>\n"
                f"👤 <b>Username:</b> @{username or 'не задан'}\n"
                f"💬 <b>Chat ID:</b> <code>{chat_id}</code>"
            )
            return {"ok": True}

        elif text.startswith("/admin"):
            clean_user = (username or "").lower().lstrip("@")
            is_adm = (
                clean_user in ("kupidon996", "ya_emildjan", "castleweb_admin", "admin")
                or str(from_id) in ("1878543896", str(settings.TELEGRAM_CHAT_ID))
                or str(chat_id) == str(settings.TELEGRAM_CHAT_ID)
            )
            if not is_adm:
                await send_reply_message(chat_id, "⛔️ Доступ ограничен. Команда доступна только администраторам студии.")
                return {"ok": True}

            domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
            parser_public_url = os.environ.get("PARSER_PUBLIC_URL", f"https://leads.{domain}").rstrip("/")
            admin_msg = (
                f"👑 <b>Панель управления CASTLEWEB STUDIO</b>\n\n"
                f"Вы авторизованы как администратор ({user_display}).\n\n"
                f"🛠 <b>Быстрые команды CRM:</b>\n"
                f"• /stats — сводка и конверсия заявок\n"
                f"• /leads — список последних 5 заявок\n"
                f"• /export — скачать базу заявок в CSV\n"
                f"• /server — диагностика сервера и контейнеров\n\n"
                f"🗺 <b>Парсер Яндекс.Карт и FL.ru:</b>\n"
                f"Для входа в веб-панель нажмите кнопку ниже или отправьте команду /demo"
            )
            admin_kb = {
                "inline_keyboard": [
                    [{"text": "🚀 Войти в панель LeadHunter", "callback_data": "get_demo_access"}],
                    [{"text": "📊 Статистика заявок", "callback_data": "server_stats"}],
                    [{"text": "🖥 Состояние сервера", "callback_data": "server_refresh"}]
                ]
            }
            await send_reply_message(chat_id, admin_msg, reply_markup=admin_kb)
            return {"ok": True}

        elif text.startswith("/help"):
            help_msg = (
                f"🛠 <b>Доступные команды бота:</b>\n\n"
                f"<b>💼 Биржи фриланса и заказы:</b>\n"
                f"• /fl — свежие заказы с биржи FL.ru (бесплатный отклик)\n"
                f"• /kwork — свежие заказы с Kwork (Разработка & Дизайн)\n"
                f"• /workspace — тендеры с биржи Workspace\n"
                f"• /orders (или /freelance) — свежие заказы со всех бирж\n\n"
                f"<b>📊 Заявки и клиенты (CastleWeb Studio):</b>\n"
                f"• /stats — статистика заявок и конверсии\n"
                f"• /leads — последние входящие заявки\n"
                f"• /find &lt;запрос&gt; — поиск клиента по имени/телефону/задаче\n"
                f"• /del &lt;id&gt; — удалить заявку\n"
                f"• /status &lt;id&gt; — статус заявки\n"
                f"• /export — выгрузка базы лидов в CSV\n\n"
                f"<b>🖥 Сервер и управление:</b>\n"
                f"• /server (или /sys) — состояние сервера (CPU, RAM, диск, аптайм)\n"
                f"• /admin — админ-панель и вход в LeadHunter\n"
                f"• /lk — Личный кабинет LeadHunter (тариф, лимиты, сброс пароля)\n"
                f"• /clear_history — очистить историю своих поисков в LeadHunter\n                • /cleanup_db (или /vacuum) — освободить память и сжать SQLite БД\n"
                f"• /cases — портфолио и кейсы студии\n"
                f"• /id — узнать свой Telegram ID и права"
            )
            await send_reply_message(chat_id, help_msg)
            return {"ok": True}


        # Б. Интерактивные команды для всех типов чатов (/lk, /clear_history, /demo, /start, /menu)
        # Команда очистки истории поиска (/clear_history или /clear)
        if text.startswith("/clear_history") or text.startswith("/clear"):
            parts = text.split()
            clear_all = len(parts) > 1 and parts[1].lower() in ("all", "global", "все")
            try:
                res = await request_parser_clear_history(from_id, clear_all=clear_all)
                del_count = res.get("deleted_count", 0)
                await send_reply_message(
                    chat_id,
                    f"🗑 <b>История поисков очищена!</b>\n\n"
                    f"Успешно удалено кампаний и отчетов: <b>{del_count}</b>.\n"
                    f"Веб-панель LeadHunter теперь чистая."
                )
            except Exception as e:
                logger.error(f"Error clearing history via command: {e}")
                await send_reply_message(chat_id, "⚠️ Не удалось очистить историю. Убедитесь, что у вас есть зарегистрированный аккаунт в LeadHunter.")
            return {"ok": True}

        # Команда очистки БД парсера и дискового пространства (/cleanup_db или /vacuum)
        if text.startswith("/cleanup_db") or text.startswith("/vacuum"):
            if not is_admin:
                await send_reply_message(chat_id, "🚫 Команда доступна только администраторам студии.")
                return {"ok": True}
            await send_reply_message(chat_id, "🧹 Запуск оптимизации SQLite, сброса WAL и очистки диска LeadHunter...")
            try:
                res = await request_parser_cleanup_db()
                freed = res.get("freed_mb", 0.0)
                orders_del = res.get("orders_deleted", 0)
                camps_del = res.get("campaigns_deleted", 0)
                files_del = res.get("screenshots_deleted", 0) + res.get("exports_deleted", 0)
                dur = res.get("duration_sec", 0)
                msg = (
                    f"✅ <b>Очистка базы данных LeadHunter завершена!</b>\n\n"
                    f"• Удалено старых заказов: <b>{orders_del}</b>\n"
                    f"• Удалено старых кампаний: <b>{camps_del}</b>\n"
                    f"• Удалено временных файлов: <b>{files_del}</b>\n"
                    f"• Размер БД до: <b>{res.get('db_size_before_mb', 0)} MB</b>\n"
                    f"• Размер БД после: <b>{res.get('db_size_after_mb', 0)} MB</b>\n"
                    f"• <b>Освобождено памяти на диске: {freed} MB</b>\n"
                    f"• Время выполнения: <i>{dur}с</i>"
                )
                await send_reply_message(chat_id, msg)
            except Exception as e:
                logger.error(f"Error in /cleanup_db: {e}")
                await send_reply_message(chat_id, f"⚠️ Ошибка очистки БД: {e}")
            return {"ok": True}

        # 0. Личный кабинет подписчика / пользователя LeadHunter (/lk, /cabinet, /profile)
        if text.startswith("/lk") or text.startswith("/cabinet") or text.startswith("/profile"):
            domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
            parser_public_url = os.environ.get("PARSER_PUBLIC_URL", f"https://leads.{domain}").rstrip("/")
            try:
                res = await request_parser_user_cabinet(from_id)
                cab_text, cab_kb = format_user_cabinet(res, parser_public_url)
                await send_reply_message(chat_id, cab_text, reply_markup=cab_kb)
            except Exception as e:
                logger.error(f"Error loading user cabinet via command: {e}")
                await send_reply_message(chat_id, "⚠️ Сервер парсера временно недоступен. Попробуйте через минуту.")
            return {"ok": True}

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

        # В. Произвольные сообщения от клиентов в ЛС (автоответчик + пересылка инженерам)
        if chat_type == "private" and not text.startswith("/"):
            has_media = bool(msg.get("document") or msg.get("photo") or msg.get("voice"))
            user_msg_text = text if text else ("📎 [Вложенный файл]" if has_media else "👋 [Обращение]")

            # 1. Автоответ клиенту
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


_RECENT_BROADCAST_FL_ORDERS = set()

@router.post("/fl-order", summary="Broadcast new FL.ru project to studio chat and admins")
async def broadcast_fl_order(request: Request):
    """
    Принимает свежий заказ от парсера FL.ru и мгновенно оповещает администраторов студии
    в закрытый командный чат и в личные сообщения.
    """
    try:
        order_data = await request.json()
    except Exception:
        return {"ok": False, "error": "Invalid JSON"}

    order_id = order_data.get("id")
    if order_id and order_id in _RECENT_BROADCAST_FL_ORDERS:
        return {"ok": True, "skipped": "already_broadcast"}
    title = order_data.get("title", "Заказ на FL.ru")
    desc = order_data.get("description", "")
    price = order_data.get("price_raw") or "По договоренности"
    cat_name = order_data.get("category_name", "Все категории")
    url = order_data.get("url", "https://www.fl.ru/projects/")
    is_pro = order_data.get("is_pro_only", False)
    is_free = order_data.get("is_free", True)
    is_urgent = order_data.get("is_urgent", False)
    if not is_free or is_pro:
        return {"ok": True, "skipped": "paid_or_pro_order"}

    platform = (order_data.get("platform") or "fl").lower()
    icon = "🟠" if platform == "fl" else "💼"
    tag = f"#{platform.upper()}"

    badges = []
    label = order_data.get("response_type_label")
    if label:
        badges.append(f"<b>{html.escape(label)}</b>")
    elif is_free:
        badges.append("✨ <b>Бесплатный отклик</b>")
    else:
        badges.append("💼 <b>Платный отклик (пакет)</b>")

    if is_pro:
        badges.append("👑 <b>Только PRO</b>")
    if is_urgent:
        badges.append("🔥 <b>Срочно</b>")
    badge_str = f" ({' | '.join(badges)})" if badges else ""

    short_desc = desc[:300].rsplit(" ", 1)[0] + "..." if len(desc) > 300 else (desc or "Без описания")

    from datetime import datetime, timezone, timedelta
    msk_tz = timezone(timedelta(hours=3))
    msk_time = datetime.now(msk_tz).strftime("%H:%M:%S")

    pub_str = order_data.get("published_at")
    pub_info = ""
    if pub_str:
        try:
            pub_dt = datetime.fromisoformat(pub_str)
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            age_sec = (now_utc - pub_dt).total_seconds()
            if age_sec > 12 * 3600:
                logger.info(f"broadcast_fl_order: Заказ #{order_id} старше 12 часов ({age_sec:.0f}s), пропуск рассылки.")
                return {"ok": True, "skipped": "too_old"}
            pub_info = f" <i>(на бирже: {pub_dt.astimezone(msk_tz).strftime('%H:%M')})</i>"
        except Exception:
            pass

    price_str = str(price).strip()
    if price_str and price_str not in ("Договорная", "По договоренности"):
        price_text = f"💰 <b>{html.escape(price_str)}</b>"
    else:
        price_text = "🤝 <b>По договоренности</b>"

    time_info = f"⚡️ <i>В эфире с: {msk_time} МСК</i>{pub_info}"

    msg = (
        f"{icon} {tag} | <b>{html.escape(title)}</b>{badge_str}\n"
        f"🏷 <i>{html.escape(str(cat_name))}</i>\n"
        f"{time_info}\n\n"
        f"{price_text}\n\n"
        f"📝 <b>Описание:</b>\n{html.escape(short_desc)}\n"
    )

    kb = {
        "inline_keyboard": [
            [{"text": "🔗 Открыть проект на FL.ru", "url": url}]
        ]
    }

    # 1. Отправляем в командный чат студии
    if settings.TELEGRAM_CHAT_ID:
        await send_reply_message(settings.TELEGRAM_CHAT_ID, msg, reply_markup=kb)

    # 2. Отправляем всем авторизованным администраторам напрямую (с подгрузкой из Redis)
    admin_targets = set(KNOWN_ADMIN_CHATS)
    admin_targets.add("1878543896")
    try:
        redis = await get_redis_client()
        if redis:
            cached_chats = await redis.smembers("castleweb:admin_chats")
            for c in cached_chats:
                c_str = c.decode("utf-8") if isinstance(c, bytes) else str(c)
                admin_targets.add(c_str)
                KNOWN_ADMIN_CHATS.add(c_str)
    except Exception:
        pass

    for aid in admin_targets:
        if str(aid) != str(settings.TELEGRAM_CHAT_ID):
            await send_reply_message(aid, msg, reply_markup=kb)

    if order_id:
        _RECENT_BROADCAST_FL_ORDERS.add(order_id)
        if len(_RECENT_BROADCAST_FL_ORDERS) > 2000:
            _RECENT_BROADCAST_FL_ORDERS.clear()

    return {"ok": True, "order_id": order_id}
