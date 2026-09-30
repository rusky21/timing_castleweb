import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()
START_TIME = time.time()


@router.get("/health", summary="Basic Health Check")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    uptime_seconds = int(time.time() - START_TIME)

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "uptime_seconds": uptime_seconds
    }
