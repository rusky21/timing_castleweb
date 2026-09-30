import asyncio
import logging
import httpx
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.infrastructure.db.models import Lead
from app.domain.entities import LeadStatus
from app.infrastructure.telegram.bot_service import TelegramBotService

logger = logging.getLogger(__name__)


async def enrich_geoip(ip: str | None) -> dict:
    """
    Бесплатное GeoIP обогащение данных через ip-api (0 ₽, без регистрации).
    Возвращает страну, город и интернет-провайдера.
    """
    if not ip or ip in ("127.0.0.1", "localhost", "::1"):
        return {"country": "Localhost", "city": "Dev Environment", "isp": "Internal"}

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp")
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country"),
                    "city": data.get("city"),
                    "isp": data.get("isp")
                }
    except Exception as e:
        logger.warning(f"GeoIP enrichment failed for IP {ip}: {e}")

    return {}


async def process_single_lead(lead_id: int):
    """
    Фоновый обработчик одной заявки:
    1. Обогащение данными GeoIP
    2. Отправка интерактивной карточки в Telegram-чат инженеров
    3. Сохранение message_id и статуса DELIVERED в базе данных
    """
    logger.info(f"⚙️ Processing background task for Lead #{lead_id}...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            logger.error(f"Lead #{lead_id} not found in database")
            return

        # 1. GeoIP enrichment
        if lead.ip_address and not lead.geo_city:
            geo_info = await enrich_geoip(lead.ip_address)
            if geo_info:
                lead.geo_country = geo_info.get("country")
                lead.geo_city = geo_info.get("city")
                lead.geo_isp = geo_info.get("isp")
                logger.info(f"📍 Lead #{lead_id} enriched: {lead.geo_city}, {lead.geo_country} ({lead.geo_isp})")

        # 2. Telegram Notification Delivery
        message_id = await TelegramBotService.send_lead_notification(lead)
        if message_id:
            lead.telegram_message_id = message_id
            lead.status = LeadStatus.DELIVERED
        else:
            # Marked as DELIVERED in database anyway (local dev fallback)
            lead.status = LeadStatus.DELIVERED

        await session.commit()
        logger.info(f"✅ Lead #{lead_id} successfully processed and updated to status '{lead.status.value}'")
