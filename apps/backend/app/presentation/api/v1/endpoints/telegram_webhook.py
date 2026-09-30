import logging
import httpx
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.infrastructure.db.models import Lead, Blacklist
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


async def send_reply_message(chat_id: int | str, text: str):
    """
    Отправляет текстовое сообщение в чат Telegram.
    """
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN in ("your_bot_token_here", ""):
        return
    url = build_telegram_api_url("sendMessage")
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception as e:
        logger.warning(f"Failed to send reply to chat {chat_id}: {e}")


@router.post("/webhook", summary="Telegram Bot Webhook Handler (Headless CRM)")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Обрабатывает события от Telegram Bot:
    - Нажатия inline-кнопок (Взять в работу, Связался, Спам/Бан)
    - Команды инженеров: /stats, /leads
    """
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

                # Добавляем IP в черный список, если еще нет
                if lead.ip_address:
                    existing_ip = (await db.execute(select(Blacklist).where(Blacklist.ip_address == lead.ip_address))).scalar_one_or_none()
                    if not existing_ip:
                        db.add(Blacklist(ip_address=lead.ip_address, reason=f"Spam lead #{lead.id}"))

                # Добавляем контакт в черный список, если еще нет
                if lead.contact:
                    existing_contact = (await db.execute(select(Blacklist).where(Blacklist.contact == lead.contact))).scalar_one_or_none()
                    if not existing_contact:
                        db.add(Blacklist(contact=lead.contact, reason=f"Spam lead #{lead.id}"))

                # Блокировка в Redis
                redis = await get_redis_client()
                if redis and lead.ip_address:
                    await redis.set(f"blacklist:{lead.ip_address}", "1", ex=86400 * 30)

                await db.commit()
                await db.refresh(lead)

                await answer_callback_query(cb_id, f"🚫 Заявка #{lead.id} отправлена в СПАМ. IP заблокирован.")
                if message_id and chat_id:
                    await TelegramBotService.update_message(chat_id, message_id, lead)

        elif data == "noop":
            await answer_callback_query(cb_id, "Информация зафиксирована")

        return {"ok": True}

    # 2. Обработка команд (/stats, /leads)
    if "message" in update and "text" in update["message"]:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "").strip()

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

        elif text.startswith("/leads"):
            recent_leads = (await db.execute(select(Lead).order_by(Lead.id.desc()).limit(5))).scalars().all()
            if not recent_leads:
                await send_reply_message(chat_id, "Заявок пока нет.")
            else:
                lines = ["📋 <b>ПОСЛЕДНИЕ 5 ЗАЯВОК:</b>\n━━━━━━━━━━━━━━━━━━━━"]
                for l in recent_leads:
                    lines.append(f"#{l.id} | {l.name} ({l.contact}) — <i>{l.status.value}</i>")
                await send_reply_message(chat_id, "\n".join(lines))

    return {"ok": True}
