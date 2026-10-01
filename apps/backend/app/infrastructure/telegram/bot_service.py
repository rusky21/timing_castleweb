import asyncio
import logging
import html
from typing import Optional, Dict, Any
import httpx
from app.core.config import get_settings
from app.infrastructure.db.models import Lead
from app.domain.entities import LeadStatus

settings = get_settings()
logger = logging.getLogger(__name__)


def build_telegram_api_url(method: str) -> str:
    """
    Формирует URL к методу Telegram Bot API.
    Поддерживает как прямой доступ к api.telegram.org, так и Cloudflare Worker прокси.
    """
    base_url = settings.TELEGRAM_API_BASE_URL.rstrip("/")
    if base_url.endswith("/bot"):
        return f"{base_url}{settings.TELEGRAM_BOT_TOKEN}/{method}"
    return f"{base_url}/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def format_lead_html(lead: Lead) -> str:
    """
    Формирует интерактивную HTML-карточку заявки для закрытого чата инженеров.
    """
    status_emoji = {
        LeadStatus.PENDING: "🟡 Ожидает ответа",
        LeadStatus.DELIVERED: "🟡 В очереди",
        LeadStatus.IN_PROGRESS: f"⚡ В работе ({lead.handled_by or 'инженер'})",
        LeadStatus.CONTACTED: f"✅ Связались ({lead.handled_by or 'инженер'})",
        LeadStatus.SPAM: "🚫 Отклонен (СПАМ)",
        LeadStatus.ARCHIVED: "📁 В архиве"
    }.get(lead.status, str(lead.status.value))

    name_clean = html.escape(lead.name)
    contact_clean = html.escape(lead.contact)
    desc_clean = html.escape(lead.task_description)
    budget_clean = html.escape(lead.budget) if lead.budget else "Не указан"

    attachment_text = ""
    if lead.attachment_url:
        att_url = lead.attachment_url.strip()
        if att_url.startswith("/"):
            domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
            att_url = f"https://{domain}{att_url}"
        attachment_text = f'\n📎 <b>ТЗ / Вложение:</b> <a href="{html.escape(att_url)}">Открыть файл</a>'

    # GeoIP block
    geo_parts = []
    if lead.geo_city:
        geo_parts.append(lead.geo_city)
    if lead.geo_country:
        geo_parts.append(lead.geo_country)
    if lead.geo_isp:
        geo_parts.append(f"({lead.geo_isp})")
    geo_str = ", ".join(geo_parts) if geo_parts else "Локальная сеть / VPN"

    text = (
        f"🔥 <b>НОВАЯ ЗАЯВКА #{lead.id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Клиент:</b> {name_clean}\n"
        f"💬 <b>Контакт:</b> <code>{contact_clean}</code>\n"
        f"💰 <b>Бюджет:</b> {budget_clean}\n"
        f"📌 <b>Статус:</b> {status_emoji}\n"
        f"{attachment_text}\n"
        f"📝 <b>Суть задачи:</b>\n"
        f"<blockquote>{desc_clean}</blockquote>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Инфо о клиенте:</b> {html.escape(geo_str)}\n"
        f"🌐 <b>IP:</b> <code>{html.escape(lead.ip_address or 'unknown')}</code>"
    )
    return text


def build_lead_keyboard(lead: Lead) -> Dict[str, Any]:
    """
    Создает инлайн-кнопки для карточки заявки в Telegram.
    """
    buttons = []

    # Кнопка связи с клиентом
    contact = lead.contact.strip()
    if contact.startswith("@"):
        tg_username = contact.lstrip("@")
        direct_url = f"https://t.me/{tg_username}"
        buttons.append([{"text": f"💬 Написать @{tg_username}", "url": direct_url}])
    elif contact.startswith("http://") or contact.startswith("https://"):
        buttons.append([{"text": "💬 Открыть контакт", "url": contact}])
    elif "@" in contact:
        buttons.append([{"text": f"✉️ Написать на {contact}", "url": f"mailto:{contact}"}])

    # Кнопки смены статуса (Headless CRM)
    if lead.status in (LeadStatus.PENDING, LeadStatus.DELIVERED):
        buttons.append([
            {"text": "⚡ Взять в работу", "callback_data": f"lead_take:{lead.id}"},
            {"text": "🚫 В бан / Спам", "callback_data": f"lead_spam:{lead.id}"}
        ])
    elif lead.status == LeadStatus.IN_PROGRESS:
        buttons.append([
            {"text": f"⚡ В работе: {lead.handled_by or 'Инженер'}", "callback_data": "noop"},
            {"text": "✅ Связался", "callback_data": f"lead_contacted:{lead.id}"}
        ])
    elif lead.status == LeadStatus.CONTACTED:
        buttons.append([
            {"text": f"✅ Связался: {lead.handled_by or 'Инженер'}", "callback_data": "noop"}
        ])
    elif lead.status == LeadStatus.SPAM:
        buttons.append([
            {"text": "🚫 Отправлен в БАН", "callback_data": "noop"}
        ])

    return {"inline_keyboard": buttons}


class TelegramBotService:
    @staticmethod
    async def send_lead_notification(lead: Lead) -> Optional[int]:
        """
        Отправляет заявку в Telegram-чат инженеров с ретраями при сетевых сбоях,
        автоматической миграцией supergroup и plain-text fallback.
        Возвращает telegram message_id для последующего редактирования кнопок.
        """
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN in ("your_bot_token_here", ""):
            logger.info(f"ℹ️ Telegram Bot Token not configured (placeholder). Skipping sending Lead #{lead.id}.")
            return None

        if not settings.TELEGRAM_CHAT_ID or settings.TELEGRAM_CHAT_ID in ("your_team_chat_id_here", ""):
            logger.error(f"❌ Telegram Chat ID not configured in settings. Skipping sending Lead #{lead.id}.")
            return None

        url = build_telegram_api_url("sendMessage")
        current_chat_id = settings.TELEGRAM_CHAT_ID
        payload = {
            "chat_id": current_chat_id,
            "text": format_lead_html(lead),
            "parse_mode": "HTML",
            "reply_markup": build_lead_keyboard(lead),
            "disable_web_page_preview": True
        }

        # Up to 4 attempts with smart flood control handling
        for attempt in range(1, 5):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    data = resp.json()
                    if data.get("ok"):
                        message_id = data["result"]["message_id"]
                        logger.info(f"📢 Telegram message sent for Lead #{lead.id}, message_id: {message_id}")
                        return message_id
                    else:
                        err_desc = data.get('description', '')
                        logger.warning(f"Telegram API returned error: {err_desc} (Attempt {attempt})")

                        # Supergroup migration: auto-detect and update chat_id
                        migrate_to = data.get("parameters", {}).get("migrate_to_chat_id")
                        if migrate_to:
                            logger.info(f"🔄 Group was upgraded to supergroup! Updating chat_id from {current_chat_id} to {migrate_to}")
                            settings.TELEGRAM_CHAT_ID = str(migrate_to)
                            payload["chat_id"] = migrate_to
                            current_chat_id = str(migrate_to)
                            retry_resp = await client.post(url, json=payload)
                            retry_data = retry_resp.json()
                            if retry_data.get("ok"):
                                msg_id = retry_data["result"]["message_id"]
                                logger.info(f"📢 Telegram message sent to supergroup {migrate_to} for Lead #{lead.id}, message_id: {msg_id}")
                                return msg_id

                        # Telegram Flood Control: respect retry_after parameter
                        if "retry after" in err_desc.lower() or data.get("error_code") == 429:
                            wait_sec = data.get("parameters", {}).get("retry_after", 10)
                            logger.warning(f"⏳ Telegram rate limited: waiting {wait_sec}s before next attempt...")
                            await asyncio.sleep(wait_sec + 1)
                            continue

                        # Fallback for HTML formatting / entity / link parsing errors
                        if any(k in err_desc.lower() for k in ("parse", "tag", "entity", "link", "url")):
                            clean_att = lead.attachment_url or 'Нет'
                            if clean_att.startswith("/"):
                                domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
                                clean_att = f"https://{domain}{clean_att}"
                            plain_text = (
                                f"🔥 НОВАЯ ЗАЯВКА #{lead.id}\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"Клиент: {lead.name}\n"
                                f"Контакт: {lead.contact}\n"
                                f"Бюджет: {lead.budget or 'Не указан'}\n"
                                f"Суть задачи:\n{lead.task_description}\n"
                                f"Вложение: {clean_att}\n"
                                f"IP: {lead.ip_address or 'unknown'}"
                            )
                            plain_payload = {**payload, "text": plain_text, "parse_mode": None}
                            retry_resp = await client.post(url, json=plain_payload)
                            retry_data = retry_resp.json()
                            if retry_data.get("ok"):
                                msg_id = retry_data["result"]["message_id"]
                                logger.info(f"📢 Plain-text fallback sent for Lead #{lead.id}, message_id: {msg_id}")
                                return msg_id
            except Exception as e:
                logger.warning(f"Network error sending to Telegram (Attempt {attempt}/4): {e}")

            await asyncio.sleep(attempt * 2.0)

        logger.error(f"❌ Failed to deliver Lead #{lead.id} to Telegram after 4 attempts.")
        return None

    @staticmethod
    async def update_message(chat_id: int | str, message_id: int, lead: Lead) -> bool:
        """
        Редактирует сообщение в Telegram (обновляет статус и кнопки).
        """
        if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN in ("your_bot_token_here", ""):
            return True

        url = build_telegram_api_url("editMessageText")
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": format_lead_html(lead),
            "parse_mode": "HTML",
            "reply_markup": build_lead_keyboard(lead),
            "disable_web_page_preview": True
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                if not data.get("ok"):
                    migrate_to = data.get("parameters", {}).get("migrate_to_chat_id")
                    if migrate_to:
                        payload["chat_id"] = migrate_to
                        resp = await client.post(url, json=payload)
                        data = resp.json()
                return bool(data.get("ok"))
        except Exception as e:
            logger.warning(f"Failed to edit Telegram message #{message_id}: {e}")
            return False
