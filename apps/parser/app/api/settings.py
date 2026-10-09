import logging
from typing import Optional, List, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import TelegramUser, TelegramUserSettings
from app.services.telegram.bot_service import tg_bot_service

logger = logging.getLogger("settings_api")
router = APIRouter(prefix="/api/settings", tags=["Настройки и фильтрация"])

class SettingsUpdateSchema(BaseModel):
    fl_enabled: Optional[bool] = None
    fl_categories: Optional[List[str]] = None
    fl_min_price: Optional[int] = None
    fl_allow_negotiable: Optional[bool] = None
    fl_hide_pro: Optional[bool] = None
    fl_urgent_only: Optional[bool] = None
    fl_keywords: Optional[List[str]] = None
    fl_negative_words: Optional[List[str]] = None
    maps_enabled: Optional[bool] = None
    maps_only_with_telegram: Optional[bool] = None
    maps_source_filter: Optional[str] = None
    maps_only_without_site: Optional[bool] = None
    maps_only_without_ssl: Optional[bool] = None
    notify_sound: Optional[bool] = None
    notify_captcha: Optional[bool] = None
    default_limit: Optional[int] = None

@router.get("", summary="Получить текущие настройки системы и фильтров")
async def get_settings(db: AsyncSession = Depends(get_db)):
    # Получаем первую активную запись настроек (или создаем дефолтную)
    stmt = select(TelegramUserSettings).limit(1)
    res = await db.execute(stmt)
    settings = res.scalar_one_or_none()

    if not settings:
        return {
            "fl_enabled": True,
            "fl_categories": ["2", "5", "7"],
            "fl_min_price": 0,
            "fl_allow_negotiable": True,
            "fl_hide_pro": False,
            "fl_urgent_only": False,
            "fl_keywords": [],
            "fl_negative_words": [],
            "maps_enabled": True,
            "maps_only_with_telegram": True,
            "maps_source_filter": "all",
            "maps_only_without_site": False,
            "maps_only_without_ssl": False,
            "notify_sound": True,
            "notify_captcha": True,
            "default_limit": 50,
            "bot_is_running": tg_bot_service.is_running
        }

    return {
        "fl_enabled": settings.fl_enabled,
        "fl_categories": settings.fl_categories or [],
        "fl_min_price": settings.fl_min_price,
        "fl_allow_negotiable": getattr(settings, "fl_allow_negotiable", True),
        "fl_hide_pro": getattr(settings, "fl_hide_pro", False),
        "fl_urgent_only": getattr(settings, "fl_urgent_only", False),
        "fl_keywords": getattr(settings, "fl_keywords", []) or [],
        "fl_negative_words": settings.fl_negative_words or [],
        "maps_enabled": settings.maps_enabled,
        "maps_only_with_telegram": settings.maps_only_with_telegram,
        "maps_source_filter": getattr(settings, "maps_source_filter", "all") or "all",
        "maps_only_without_site": getattr(settings, "maps_only_without_site", False),
        "maps_only_without_ssl": getattr(settings, "maps_only_without_ssl", False),
        "notify_sound": getattr(settings, "notify_sound", True),
        "notify_captcha": getattr(settings, "notify_captcha", True),
        "default_limit": getattr(settings, "default_limit", 50),
        "bot_is_running": tg_bot_service.is_running
    }

@router.post("", summary="Обновить настройки фильтров")
async def update_settings(payload: SettingsUpdateSchema, db: AsyncSession = Depends(get_db)):
    stmt = select(TelegramUserSettings)
    res = await db.execute(stmt)
    all_settings = res.scalars().all()

    if not all_settings:
        raise HTTPException(status_code=404, detail="Настройки пользователя еще не созданы (запустите бота /start)")

    data = payload.model_dump(exclude_unset=True)
    for s in all_settings:
        for k, v in data.items():
            if hasattr(s, k):
                setattr(s, k, v)

    await db.commit()
    return {"status": "ok", "updated_fields": list(data.keys())}

@router.post("/reset", summary="Сбросить все настройки к стандартным значениям")
async def reset_settings(db: AsyncSession = Depends(get_db)):
    stmt = select(TelegramUserSettings)
    res = await db.execute(stmt)
    all_settings = res.scalars().all()

    defaults = {
        "fl_enabled": True,
        "fl_categories": ["2", "5", "7"],
        "fl_min_price": 0,
        "fl_allow_negotiable": True,
        "fl_hide_pro": False,
        "fl_urgent_only": False,
        "fl_keywords": [],
        "fl_negative_words": [],
        "maps_enabled": True,
        "maps_only_with_telegram": True,
        "maps_source_filter": "all",
        "maps_only_without_site": False,
        "maps_only_without_ssl": False,
        "notify_sound": True,
        "notify_captcha": True,
        "default_limit": 50,
    }

    for s in all_settings:
        for k, v in defaults.items():
            if hasattr(s, k):
                setattr(s, k, v)

    await db.commit()
    return {"status": "ok", "message": "Настройки сброшены к стандартным"}

@router.get("/status", summary="Статус Telegram-бота и подписчиков")
async def get_bot_status(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TelegramUser).where(TelegramUser.is_active == True))
    users = res.scalars().all()
    return {
        "is_running": tg_bot_service.is_running,
        "active_users_count": len(users),
        "users": [{"chat_id": u.chat_id, "username": u.username, "full_name": u.full_name} for u in users]
    }
