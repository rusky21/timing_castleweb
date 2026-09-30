import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

redis_pool: Optional[aioredis.Redis] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    """
    Возвращает асинхронный клиент Redis.
    Если Redis недоступен локально — возвращает None (graceful fallback).
    """
    global redis_pool
    if redis_pool is None:
        try:
            redis_pool = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            # Ping check
            await redis_pool.ping()
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable at {settings.REDIS_URL}. Fallback to in-memory mode: {e}")
            redis_pool = None

    return redis_pool


async def close_redis_pool():
    global redis_pool
    if redis_pool is not None:
        await redis_pool.close()
        redis_pool = None
