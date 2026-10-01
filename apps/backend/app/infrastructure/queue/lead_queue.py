import asyncio
import logging
from typing import Callable, Coroutine, Any
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# Queue channel name in Redis
LEAD_QUEUE_KEY = "queue:leads:process"


async def push_lead_to_queue(lead_id: int):
    """
    Ставит ID лида в очередь обработки и немедленно инициирует фоновую отправку в Telegram.
    """
    redis = await get_redis_client()
    if redis:
        try:
            await redis.rpush(LEAD_QUEUE_KEY, str(lead_id))
            logger.info(f"📥 Lead #{lead_id} pushed to Redis queue '{LEAD_QUEUE_KEY}'")
        except Exception as e:
            logger.warning(f"Failed to push to Redis queue: {e}")

    # Немедленно запускаем фоновую обработку заявки (GeoIP + Telegram отправка)
    from app.infrastructure.queue.worker import process_single_lead
    asyncio.create_task(process_single_lead(lead_id))
    logger.info(f"🚀 Lead #{lead_id} dispatched to async background worker")

