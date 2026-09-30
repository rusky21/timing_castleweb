import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.core.config import get_settings

router = APIRouter()
START_TIME = time.time()
settings = get_settings()


@router.get("/status", summary="Live Engineering Status & Latency API")
async def live_status(db: AsyncSession = Depends(get_db)):
    """
    Публичный эндпоинт для фронтенд-виджета надежности студии.
    Отдает статус доступности БД, Redis, средний пинг и время непрерывной работы (Uptime).
    """
    # 1. Database latency check
    t0 = time.perf_counter()
    db_healthy = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_healthy = False
    db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 2. Redis latency check
    redis = await get_redis_client()
    redis_healthy = False
    redis_latency_ms = 0.0
    if redis:
        try:
            t_red = time.perf_counter()
            await redis.ping()
            redis_latency_ms = round((time.perf_counter() - t_red) * 1000, 2)
            redis_healthy = True
        except Exception:
            redis_healthy = False

    # 3. Uptime formatting
    uptime_sec = int(time.time() - START_TIME)
    days = uptime_sec // 86400
    hours = (uptime_sec % 86400) // 3600
    minutes = (uptime_sec % 3600) // 60

    uptime_human = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"

    overall_status = "operational" if db_healthy else "degraded"

    return {
        "status": overall_status,
        "latency_ms": db_latency_ms,
        "uptime": uptime_human,
        "services": {
            "api": "operational",
            "database": {
                "status": "operational" if db_healthy else "disconnected",
                "latency_ms": db_latency_ms
            },
            "redis_cache": {
                "status": "operational" if redis_healthy else "in_memory_fallback",
                "latency_ms": redis_latency_ms if redis_healthy else None
            },
            "telegram_bot": {
                "status": "connected" if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN != "your_bot_token_here" else "standby"
            }
        },
        "engineers_on_duty": 2,
        "version": "1.0.0"
    }
