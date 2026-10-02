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
    Гарантирует валидный абсолютный URL даже при непредвиденных значениях в .env.
    """
    base_url = (getattr(settings, "TELEGRAM_API_BASE_URL", "") or "").strip().rstrip("/")
    if not base_url or not (base_url.startswith("http://") or base_url.startswith("https://")):
        base_url = "https://api.telegram.org/bot"

    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()

    if base_url.endswith("/bot"):
        return f"{base_url}{token}/{method}"
    return f"{base_url}/bot{token}/{method}"


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
    InlineKeyboardButton url ДОЛЖЕН начинаться с http://, https:// или tg://.
    mailto: недопустим в InlineKeyboardButton и вызывает 400 Bad Request: BUTTON_URL_INVALID.
    """
    buttons = []

    # Кнопка связи с клиентом
    contact = (lead.contact or "").strip()
    if contact.startswith("@"):
        tg_username = contact.lstrip("@")
        direct_url = f"https://t.me/{tg_username}"
        buttons.append([{"text": f"💬 Написать @{tg_username}", "url": direct_url}])
    elif contact.startswith("http://") or contact.startswith("https://") or contact.startswith("tg://"):
        buttons.append([{"text": "💬 Открыть контакт", "url": contact}])
    elif "t.me/" in contact:
        url = contact if contact.startswith("http") else f"https://{contact}"
        buttons.append([{"text": "💬 Написать в Telegram", "url": url}])
    elif contact.startswith("+") and contact[1:].isdigit():
        clean_phone = contact.lstrip("+")
        buttons.append([{"text": "📱 WhatsApp", "url": f"https://wa.me/{clean_phone}"}])

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

    # Кнопка удаления записи для быстрого клининга / тестов
    buttons.append([
        {"text": "🗑 Удалить запись", "callback_data": f"lead_del_prompt:{lead.id}"}
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
        bot_token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        chat_id = (getattr(settings, "TELEGRAM_CHAT_ID", "") or "").strip()

        if not bot_token or bot_token in ("your_bot_token_here", ""):
            logger.info(f"ℹ️ Telegram Bot Token not configured (placeholder). Skipping sending Lead #{lead.id}.")
            return None

        if not chat_id or chat_id in ("your_team_chat_id_here", ""):
            logger.error(f"❌ Telegram Chat ID not configured in settings. Skipping sending Lead #{lead.id}.")
            return None

        url = build_telegram_api_url("sendMessage")
        current_chat_id = chat_id
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
                        logger.warning(f"Telegram API returned error (HTTP {resp.status_code}): {err_desc} (Attempt {attempt})")

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

                        # Fallback for HTML formatting / entity / link parsing errors or keyboard errors
                        if any(k in err_desc.lower() for k in ("parse", "tag", "entity", "link", "url", "button", "markup", "can't parse")):
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
                            # Safe fallback: callback buttons only, avoiding any invalid URLs
                            safe_keyboard = {
                                "inline_keyboard": [
                                    [
                                        {"text": "⚡ Взять в работу", "callback_data": f"lead_take:{lead.id}"},
                                        {"text": "🚫 В бан / Спам", "callback_data": f"lead_spam:{lead.id}"}
                                    ]
                                ]
                            }
                            plain_payload = {
                                **payload,
                                "text": plain_text,
                                "parse_mode": None,
                                "reply_markup": safe_keyboard
                            }
                            retry_resp = await client.post(url, json=plain_payload)
                            retry_data = retry_resp.json()
                            if retry_data.get("ok"):
                                msg_id = retry_data["result"]["message_id"]
                                logger.info(f"📢 Plain-text fallback sent for Lead #{lead.id}, message_id: {msg_id}")
                                return msg_id
                            else:
                                logger.warning(f"Plain-text fallback also failed: {retry_data.get('description')}")
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
        bot_token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not bot_token or bot_token in ("your_bot_token_here", ""):
            return True

        clean_chat = (str(chat_id) or "").strip()
        url = build_telegram_api_url("editMessageText")
        payload = {
            "chat_id": clean_chat,
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

    @staticmethod
    async def edit_message_text(
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Редактирует текст сообщения и опционально обновляет инлайн-кнопки.
        """
        bot_token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not bot_token or bot_token in ("your_bot_token_here", ""):
            return True

        clean_chat = (str(chat_id) or "").strip()
        url = build_telegram_api_url("editMessageText")
        payload = {
            "chat_id": clean_chat,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

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
            logger.warning(f"Failed to edit Telegram message text #{message_id}: {e}")
            return False

    @staticmethod
    async def edit_message_reply_markup(
        chat_id: int | str,
        message_id: int,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Редактирует только инлайн-кнопки сообщения (например, для подтверждения удаления).
        """
        bot_token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not bot_token or bot_token in ("your_bot_token_here", ""):
            return True

        clean_chat = (str(chat_id) or "").strip()
        url = build_telegram_api_url("editMessageReplyMarkup")
        payload = {
            "chat_id": clean_chat,
            "message_id": message_id,
            "reply_markup": reply_markup or {"inline_keyboard": []}
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
            logger.warning(f"Failed to edit Telegram reply markup #{message_id}: {e}")
            return False

    @staticmethod
    async def delete_message(chat_id: int | str, message_id: int) -> bool:
        """
        Удаляет сообщение из чата Telegram.
        """
        bot_token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not bot_token or bot_token in ("your_bot_token_here", ""):
            return True

        clean_chat = (str(chat_id) or "").strip()
        url = build_telegram_api_url("deleteMessage")
        payload = {"chat_id": clean_chat, "message_id": message_id}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload)
                return bool(resp.json().get("ok"))
        except Exception as e:
            logger.warning(f"Failed to delete Telegram message #{message_id}: {e}")
            return False

    @staticmethod
    async def send_raw_message(text: str, reply_markup: Optional[Dict[str, Any]] = None, chat_id: Optional[str | int] = None) -> bool:
        """
        Отправляет произвольное текстовое сообщение в чат инженеров (или указанный chat_id).
        """
        bot_token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        target_chat = (str(chat_id or getattr(settings, "TELEGRAM_CHAT_ID", "") or "")).strip()
        if not bot_token or not target_chat or target_chat in ("your_team_chat_id_here", ""):
            return False

        url = build_telegram_api_url("sendMessage")
        payload = {
            "chat_id": target_chat,
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
                    migrate_to = data.get("parameters", {}).get("migrate_to_chat_id")
                    if migrate_to:
                        if str(target_chat) == str(settings.TELEGRAM_CHAT_ID):
                            settings.TELEGRAM_CHAT_ID = str(migrate_to)
                        payload["chat_id"] = migrate_to
                        resp = await client.post(url, json=payload)
                        data = resp.json()
                return bool(data.get("ok"))
        except Exception as e:
            logger.warning(f"Failed to send raw Telegram message: {e}")
            return False

    @staticmethod
    async def send_document(chat_id: str | int, filename: str, content: bytes, caption: Optional[str] = None) -> bool:
        """
        Отправляет файл (например, CSV выгрузку) в чат Telegram.
        """
        bot_token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        clean_chat = (str(chat_id) or "").strip()
        if not bot_token or not clean_chat or clean_chat in ("your_team_chat_id_here", ""):
            return False

        url = build_telegram_api_url("sendDocument")
        try:
            files = {"document": (filename, content, "text/csv")}
            data = {"chat_id": clean_chat}
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, data=data, files=files)
                return bool(resp.json().get("ok"))
        except Exception as e:
            logger.warning(f"Failed to send document to Telegram chat {clean_chat}: {e}")
            return False

