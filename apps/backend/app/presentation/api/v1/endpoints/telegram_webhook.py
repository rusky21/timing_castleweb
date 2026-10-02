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
from app.infrastructure.db.models import Lead, Blacklist, Case
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

                await answer_callback_query(cb_id, f"⚡ Вы взяли заявку #{lead.id} в работу!")
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

                await answer_callback_query(cb_id, f"✅ Отмечено: связались по заявке #{lead.id}!")
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

                await answer_callback_query(cb_id, f"🚫 Заявка #{lead.id} отправлена в СПАМ. IP заблокирован.")
                if message_id and chat_id:
                    await TelegramBotService.update_message(chat_id, message_id, lead)

        elif data.startswith("lead_del_prompt:"):
            lead_id = int(data.split(":")[1])
            res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = res.scalar_one_or_none()
            if not lead:
                await answer_callback_query(cb_id, f"⚠️ Заявка #{lead_id} уже не найдена в базе")
                return {"ok": True}

            confirm_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": f"💥 Да, удалить #{lead_id} из БД", "callback_data": f"lead_del_confirm:{lead_id}"},
                        {"text": "❌ Отмена", "callback_data": f"lead_del_cancel:{lead_id}"}
                    ]
                ]
            }
            await answer_callback_query(cb_id, f"Подтвердите удаление заявки #{lead_id}")
            if message_id and chat_id:
                await TelegramBotService.edit_message_reply_markup(chat_id, message_id, confirm_keyboard)

        elif data.startswith("lead_del_cancel:"):
            lead_id = int(data.split(":")[1])
            res = await db.execute(select(Lead).where(Lead.id == lead_id))
            lead = res.scalar_one_or_none()
            await answer_callback_query(cb_id, "Удаление отменено")
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
                    f"🗑 <b>ЗАЯВКА #{lead_id} УДАЛЕНА ИЗ БАЗЫ ДАННЫХ</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 <b>Клиент:</b> {html.escape(lead_name)}\n"
                    f"💬 <b>Контакт:</b> <code>{html.escape(lead_contact)}</code>\n"
                    f"🛠 <b>Удалил:</b> {user_display}\n"
                    f"📌 <b>Статус:</b> Запись полностью стёрта из PostgreSQL"
                )
                del_keyboard = {"inline_keyboard": [[{"text": "🗑 Запись удалена из базы", "callback_data": "noop"}]]}
                await answer_callback_query(cb_id, f"🗑 Заявка #{lead_id} удалена из БД!")
                if message_id and chat_id:
                    await TelegramBotService.edit_message_text(chat_id, message_id, deleted_text, del_keyboard)
            else:
                await answer_callback_query(cb_id, f"⚠️ Заявка #{lead_id} уже была удалена ранее.")

        elif data == "client_cases":
            res = await db.execute(select(Case).where(Case.is_published.is_(True)).order_by(Case.sort_order.asc()).limit(5))
            cases = res.scalars().all()
            if not cases:
                await answer_callback_query(cb_id, "Портфолио наполняется...")
            else:
                await answer_callback_query(cb_id, "Загрузка кейсов...")
                lines = ["🏰 <b>ПОРТФОЛИО СТУДИИ CASTLEWEB:</b>\n━━━━━━━━━━━━━━━━━━━━"]
                for c in cases:
                    cat_val = c.category.value if hasattr(c.category, "value") else str(c.category)
                    link_html = f' — <a href="{html.escape(c.live_url)}">Смотреть</a>' if c.live_url else ""
                    lines.append(f"🚀 <b>{html.escape(c.title)}</b> [{cat_val.upper()}]\n{html.escape(c.short_description)}{link_html}")
                lines.append("━━━━━━━━━━━━━━━━━━━━\n🌐 Все кейсы: https://castleweb.ru")
                if chat_id:
                    await send_reply_message(chat_id, "\n\n".join(lines))

        elif data == "noop":
            await answer_callback_query(cb_id, "Информация зафиксирована")

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
                    f"💬 <b>Ответ инженера CASTLEWEB:</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{html.escape(text)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"<i>Вы можете отправить ответ или файлы прямо в этот чат.</i>"
                )
                try:
                    await send_reply_message(client_tg_id, client_msg)
                    await send_reply_message(chat_id, "✅ <b>Ответ успешно отправлен клиенту в личные сообщения бота!</b>")
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
                f"📊 <b>СТАТИСТИКА СТУДИИ CASTLEWEB</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📥 Всего заявок: <b>{total_leads}</b>\n"
                f"🟡 В ожидании: <b>{pending}</b>\n"
                f"⚡ В работе: <b>{in_progress}</b>\n"
                f"✅ Успешно связались: <b>{contacted}</b>\n"
                f"🚫 Спам: <b>{spam}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            await send_reply_message(chat_id, stats_msg)
            return {"ok": True}

        elif text.startswith("/leads"):
            recent_leads = (await db.execute(select(Lead).order_by(Lead.id.desc()).limit(5))).scalars().all()
            if not recent_leads:
                await send_reply_message(chat_id, "Заявок пока нет.")
            else:
                lines = ["📋 <b>ПОСЛЕДНИЕ 5 ЗАЯВОК:</b>\n━━━━━━━━━━━━━━━━━━━━"]
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
                    await send_reply_message(chat_id, f"⚠️ <b>Заявка #{lead_id} не найдена в базе данных.</b>")
                else:
                    lead_name = lead.name
                    lead_contact = lead.contact
                    msg_id_card = lead.telegram_message_id
                    await db.delete(lead)
                    await db.commit()

                    del_info = (
                        f"🗑 <b>Заявка #{lead_id} успешно удалена из базы!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 <b>Клиент:</b> {html.escape(lead_name)}\n"
                        f"💬 <b>Контакт:</b> <code>{html.escape(lead_contact)}</code>\n"
                        f"🛠 <b>Удалил:</b> {user_display}"
                    )
                    await send_reply_message(chat_id, del_info)

                    # Обновляем карточку заявки, если сообщение сохранено
                    if msg_id_card and settings.TELEGRAM_CHAT_ID:
                        try:
                            card_text = (
                                f"🗑 <b>ЗАЯВКА #{lead_id} УДАЛЕНА ИЗ БАЗЫ ДАННЫХ</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"👤 <b>Клиент:</b> {html.escape(lead_name)}\n"
                                f"💬 <b>Контакт:</b> <code>{html.escape(lead_contact)}</code>\n"
                                f"🛠 <b>Удалил:</b> {user_display}\n"
                                f"📌 <b>Статус:</b> Запись полностью стёрта из PostgreSQL"
                            )
                            card_kb = {"inline_keyboard": [[{"text": "🗑 Запись стёрта", "callback_data": "noop"}]]}
                            await TelegramBotService.edit_message_text(settings.TELEGRAM_CHAT_ID, msg_id_card, card_text, card_kb)
                        except Exception:
                            pass
            else:
                await send_reply_message(chat_id, "ℹ️ Использование: <code>/del &lt;ID заявки&gt;</code> (например: <code>/del 15</code>)")
            return {"ok": True}

        elif text.startswith("/find ") or text.startswith("/search "):
            parts = text.split(maxsplit=1)
            q = parts[1].strip() if len(parts) > 1 else ""
            if not q:
                await send_reply_message(chat_id, "ℹ️ Использование: <code>/find &lt;имя, телефон, @тег или текст&gt;</code>")
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
                    await send_reply_message(chat_id, f"🔍 По запросу <code>{html.escape(q)}</code> заявок не найдено.")
                else:
                    lines = [f"🔍 <b>НАЙДЕНО ЗАЯВОК: {len(found)}</b>\n━━━━━━━━━━━━━━━━━━━━"]
                    for l in found:
                        st = l.status.value if hasattr(l.status, "value") else str(l.status)
                        lines.append(
                            f"#{l.id} | <b>{html.escape(l.name)}</b> (<code>{html.escape(l.contact)}</code>)\n"
                            f"📌 Статус: <i>{st}</i> | Бюджет: {html.escape(l.budget or 'Не указан')}\n"
                            f"📝 <i>{html.escape(l.task_description[:80])}...</i>"
                        )
                    await send_reply_message(chat_id, "\n\n".join(lines))
            return {"ok": True}

        elif text.startswith("/server") or text.startswith("/sys"):
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
                        uptime_str = f"{d} дн. {h} ч. {m} мин." if d > 0 else f"{h} ч. {m} мин."
            except Exception:
                pass

            # 5. Database ping & latency
            db_status = "🔴 Offline"
            try:
                t0 = time.perf_counter()
                await db.execute(sql_text("SELECT 1"))
                lat = (time.perf_counter() - t0) * 1000
                db_status = f"🟢 Operational ({lat:.1f} ms)"
            except Exception as e:
                db_status = f"🔴 Ошибка: {str(e)[:30]}"

            # 6. Redis ping & latency
            redis_status = "🟡 Not connected"
            try:
                redis_client = await get_redis_client()
                if redis_client:
                    t0 = time.perf_counter()
                    await redis_client.ping()
                    lat = (time.perf_counter() - t0) * 1000
                    redis_status = f"🟢 Operational ({lat:.1f} ms)"
            except Exception:
                pass

            server_report = (
                f"🖥 <b>СОСТОЯНИЕ СЕРВЕРА CASTLEWEB</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ <b>CPU Load Avg:</b> {load_str} (1/5/15 мин)\n"
                f"🧠 <b>RAM ОЗУ:</b> {ram_str}\n"
                f"💾 <b>SSD Диск (/):</b> {disk_str}\n"
                f"⏱ <b>Uptime хоста:</b> {uptime_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🗄 <b>PostgreSQL:</b> {db_status}\n"
                f"⚡ <b>Redis Cache:</b> {redis_status}\n"
                f"🤖 <b>Telegram Webhook:</b> 🟢 Active\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            await send_reply_message(chat_id, server_report)
            return {"ok": True}

        elif text.startswith("/cases") or text.startswith("/portfolio"):
            res = await db.execute(select(Case).where(Case.is_published.is_(True)).order_by(Case.sort_order.asc()).limit(5))
            cases = res.scalars().all()
            if not cases:
                await send_reply_message(chat_id, "📁 Портфолио пока пусто.")
            else:
                lines = ["🏰 <b>ПОРТФОЛИО СТУДИИ CASTLEWEB:</b>\n━━━━━━━━━━━━━━━━━━━━"]
                for c in cases:
                    cat_val = c.category.value if hasattr(c.category, "value") else str(c.category)
                    link_html = f' — <a href="{html.escape(c.live_url)}">Смотреть проект</a>' if c.live_url else ""
                    lines.append(f"🚀 <b>{html.escape(c.title)}</b> [{cat_val.upper()}]\n{html.escape(c.short_description)}{link_html}")
                lines.append("━━━━━━━━━━━━━━━━━━━━\n🌐 Все кейсы на сайте: https://castleweb.ru")
                await send_reply_message(chat_id, "\n\n".join(lines))
            return {"ok": True}

        elif text.startswith("/status"):
            parts = text.split(maxsplit=1)
            if len(parts) > 1 and parts[1].strip().isdigit():
                lead_id = int(parts[1].strip())
                res = await db.execute(select(Lead).where(Lead.id == lead_id))
                lead = res.scalar_one_or_none()
                if not lead:
                    await send_reply_message(chat_id, f"⚠️ Заявка #{lead_id} не найдена в базе данных.")
                else:
                    st_desc = {
                        LeadStatus.PENDING: "🟡 Заявка принята и ожидает назначения инженера",
                        LeadStatus.DELIVERED: "🟡 В очереди дежурного инженера",
                        LeadStatus.IN_PROGRESS: f"⚡ В работе (назначен: {lead.handled_by or 'Архитектор'})",
                        LeadStatus.CONTACTED: f"✅ Инженер связался с вами ({lead.handled_by or 'Сеньор-разработчик'})",
                        LeadStatus.SPAM: "🚫 Отклонена",
                        LeadStatus.ARCHIVED: "📁 В архиве"
                    }.get(lead.status, str(lead.status.value))

                    lead_card_msg = (
                        f"📋 <b>СТАТУС ЗАЯВКИ #{lead.id}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 <b>Клиент:</b> {html.escape(lead.name)}\n"
                        f"💬 <b>Контакт:</b> <code>{html.escape(lead.contact)}</code>\n"
                        f"💰 <b>Бюджет:</b> {html.escape(lead.budget or 'Не указан')}\n"
                        f"📌 <b>Статус:</b> {st_desc}\n"
                        f"⏱ <b>Создана:</b> {lead.created_at.strftime('%d.%m.%Y %H:%M') if lead.created_at else '—'}"
                    )
                    await send_reply_message(chat_id, lead_card_msg)
            else:
                await send_reply_message(chat_id, "ℹ️ Использование: <code>/status &lt;ID заявки&gt;</code> (например: <code>/status 12</code>)")
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
            caption = f"📊 <b>Выгрузка лидов CASTLEWEB</b>\nВсего записей: {len(leads)}"

            sent = await TelegramBotService.send_document(chat_id, filename, csv_bytes, caption=caption)
            if not sent:
                await send_reply_message(chat_id, "⚠️ Не удалось отправить файл. Проверьте права бота.")
            return {"ok": True}

        elif text.startswith("/help"):
            help_msg = (
                f"🛠 <b>КОМАНДЫ CASTLEWEB BOT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• <code>/stats</code> — Сводка по всем заявкам\n"
                f"• <code>/leads</code> — Список последних 5 заявок\n"
                f"• <code>/find &lt;запрос&gt;</code> — Поиск заявки по имени или контакту\n"
                f"• <code>/del &lt;ID&gt;</code> — Удалить заявку из базы данных\n"
                f"• <code>/status &lt;ID&gt;</code> — Проверить статус заявки по номеру\n"
                f"• <code>/server</code> — Телеметрия сервера (CPU, RAM, SSD, DB, Redis)\n"
                f"• <code>/cases</code> — Список кейсов портфолио\n"
                f"• <code>/export</code> — Экспорт базы лидов в CSV (Excel)\n"
                f"• <code>/help</code> — Справка"
            )
            await send_reply_message(chat_id, help_msg)
            return {"ok": True}


        # Б. ЛИЧНЫЕ СООБЩЕНИЯ ОТ КЛИЕНТА (chat_type == "private")
        if chat_type == "private":
            # 1. Приветствие на /start
            if text.startswith("/start"):
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
                                f"🏰 Ваша заявка <b>#{lead.id}</b> уже принята дежурным инженером CASTLEWEB!\n\n"
                                f"Вы можете отправить прямо сюда любые дополнительные файлы, схемы, "
                                f"ссылки на макеты в Figma или вопросы. Мы сразу их увидим и ответим вам здесь в течение <b>15 минут</b>."
                            )
                            buttons = {
                                "inline_keyboard": [
                                    [{"text": "🌐 Открыть сайт castleweb.ru", "url": "https://castleweb.ru"}]
                                ]
                            }
                            await send_reply_message(chat_id, welcome_lead, reply_markup=buttons)

                            # Уведомляем группу инженеров
                            if settings.TELEGRAM_CHAT_ID:
                                client_handle = f"@{username}" if username else f"ID: <code>{from_id}</code>"
                                notify_eng = (
                                    f"🔔 <b>Клиент по заявке #{lead.id} подключился к боту в Telegram!</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 <b>Клиент:</b> {html.escape(lead.name)}\n"
                                    f"💬 <b>Контакт:</b> {client_handle}"
                                )
                                direct_btn = [{"text": "💬 Написать клиенту", "url": f"https://t.me/{username}"}] if username else []
                                reply_markup = {"inline_keyboard": [direct_btn]} if direct_btn else None
                                await send_reply_message(settings.TELEGRAM_CHAT_ID, notify_eng, reply_markup=reply_markup)
                            return {"ok": True}
                    except ValueError:
                        pass

                # Общее приветствие нового пользователя
                general_welcome = (
                    f"👋 <b>Здравствуйте, {html.escape(first_name)}!</b>\n\n"
                    f"Добро пожаловать в <b>CASTLEWEB Studio</b> 🏰\n\n"
                    f"Мы проектируем и разрабатываем надежные веб-сервисы, высоконагруженные SaaS-платформы "
                    f"и интерактивные сайты «под ключ» напрямую с сеньор-инженерами — без лишних менеджеров.\n\n"
                    f"💬 <b>Как мы можем вам помочь?</b>\n"
                    f"Опишите вашу задачу прямо в этом диалоге или оставьте заявку на нашем сайте. "
                    f"Дежурный инженер ответит вам в течение <b>15 минут</b>."
                )
                welcome_buttons = {
                    "inline_keyboard": [
                        [{"text": "💼 Портфолио проектов", "callback_data": "client_cases"}],
                        [{"text": "📊 Калькулятор сметы", "url": "https://castleweb.ru/#calculator"}],
                        [{"text": "🌐 Открыть сайт castleweb.ru", "url": "https://castleweb.ru"}]
                    ]
                }
                await send_reply_message(chat_id, general_welcome, reply_markup=welcome_buttons)
                return {"ok": True}

            # 2. Любое сообщение / вопрос / фото / документ от клиента в ЛС
            has_media = bool(msg.get("document") or msg.get("photo") or msg.get("voice"))
            user_msg_text = text if text else ("📎 [Вложенный файл / документ / фото]" if has_media else "👋 [Обращение]")

            # 2.1. Автоответ клиенту
            client_reply = (
                f"✅ <b>Спасибо за обращение!</b>\n\n"
                f"🏰 Дежурный инженер CASTLEWEB уже получил ваше сообщение и ответит вам прямо в этом чате в течение <b>15 минут</b>.\n\n"
                f"Если у вас есть дополнительные материалы (ТЗ, макеты, ссылки) — можете отправить их сюда следующим сообщением."
            )
            await send_reply_message(chat_id, client_reply)

            # 2.2. Мгновенная пересылка и оповещение в закрытый чат инженеров
            if settings.TELEGRAM_CHAT_ID:
                direct_url = f"https://t.me/{username}" if username else f"tg://user?id={from_id}"
                reply_btn_text = f"💬 Ответить @{username}" if username else "💬 Открыть диалог с клиентом"
                media_note = "\n📎 <i>Клиент также прикрепил файл/медиа</i>" if has_media else ""

                eng_alert = (
                    f"📩 <b>НОВОЕ СООБЩЕНИЕ В ЛИЧКУ БОТА</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 <b>Клиент:</b> {html.escape(user_display)}\n"
                    f"💬 <b>Username:</b> {f'@{username}' if username else 'Не задан'}\n"
                    f"🆔 <b>Telegram ID:</b> <code>{from_id}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📝 <b>Сообщение:</b>\n"
                    f"<blockquote>{html.escape(user_msg_text)}</blockquote>"
                    f"{media_note}"
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
