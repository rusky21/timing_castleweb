import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from app.core.redis import get_redis_client

# In-memory fallback if Redis is not running: {ip: (count, reset_timestamp)}
_in_memory_store: Dict[str, Tuple[int, float]] = {}


async def check_rate_limit(
    request: Request,
    key_prefix: str = "ratelimit",
    max_requests: int = 3,
    window_seconds: int = 600
):
    """
    Проверяет лимит запросов с IP-адреса.
    По умолчанию: не более 3 запросов за 10 минут.
    Работает через Redis, а при его отсутствии — через in-memory словарь.
    """
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")

    redis = await get_redis_client()
    key = f"{key_prefix}:{ip}"

    if redis:
        try:
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, window_seconds)

            if current > max_requests:
                ttl = await redis.ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Слишком много запросов. Попробуйте снова через {max(1, ttl)} секунд."
                )
            return
        except HTTPException:
            raise
        except Exception:
            # If Redis command fails, fall back to in-memory
            pass

    # In-memory fallback
    now = time.time()
    if ip in _in_memory_store:
        count, reset_time = _in_memory_store[ip]
        if now < reset_time:
            if count >= max_requests:
                retry_after = int(reset_time - now)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Слишком много запросов. Попробуйте снова через {max(1, retry_after)} секунд."
                )
            _in_memory_store[ip] = (count + 1, reset_time)
        else:
            _in_memory_store[ip] = (1, now + window_seconds)
    else:
        _in_memory_store[ip] = (1, now + window_seconds)
