import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import SearchCampaign, User
from app.schemas.search import (
    SearchStartRequest, SearchStartResponse, 
    SearchStopRequest, SearchStopResponse,
    CaptchaResolvedRequest
)
from app.services.task_manager import task_manager

router = APIRouter(prefix="/api/search", tags=["Поиск и сбор"])

@router.post("/start", response_model=SearchStartResponse, summary="Запустить сбор и аудит лидов")
async def start_search(
    req: SearchStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Запускает сбор лидов по нише и городу с выбранных геосервисов (Яндекс.Карты / 2ГИС).
    Создает поисковую кампанию и запускает фоновый воркер с отправкой событий через WebSocket.
    Для пользователей с ролью 'demo' действуют лимиты: 5 запросов, до 5 компаний, кулдаун 15 минут.
    """
    effective_limit = req.limit

    # Проверка демо-пользователя и его лимитов
    user_payload = getattr(request.state, "user", None)
    if user_payload and user_payload.get("sub"):
        try:
            uid = int(user_payload.get("sub"))
            u_res = await db.execute(select(User).where(User.id == uid))
            current_user = u_res.scalar_one_or_none()
            if current_user and current_user.role == "demo":
                # 1. Проверка оставшихся попыток
                if current_user.demo_searches_left <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Лимит демо-доступа исчерпан (0 из 5 запросов). Для получения полного доступа свяжитесь со студией CASTLEWEB."
                    )

                # 2. Проверка интервала 15 минут между поисками
                if current_user.last_search_at:
                    now = datetime.now(timezone.utc)
                    last_at = current_user.last_search_at
                    if last_at.tzinfo is None:
                        last_at = last_at.replace(tzinfo=timezone.utc)
                    elapsed = (now - last_at).total_seconds()
                    cooldown = 15 * 60  # 15 минут в секундах
                    if elapsed < cooldown:
                        rem_min = int((cooldown - elapsed + 59) // 60)
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"В демо-режиме действует интервал 15 минут между поисками. Подождите еще {rem_min} мин."
                        )

                # 3. Ограничение: максимум 5 компаний за один запуск
                effective_limit = min(req.limit, current_user.max_companies_per_search or 5)

                # 4. Списание попытки и фиксация времени
                current_user.demo_searches_left -= 1
                current_user.last_search_at = datetime.now(timezone.utc)
                await db.commit()
        except HTTPException:
            raise
        except Exception:
            pass

    # Создаем запись кампании
    campaign = SearchCampaign(
        niche=req.niche.strip(),
        city=req.city.strip(),
        source=req.source,
        target_limit=effective_limit,
        status="RUNNING"
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    task_id = str(uuid.uuid4())[:8]

    # Запускаем фоновую задачу
    task_manager.start_campaign(
        campaign_id=campaign.id,
        niche=campaign.niche,
        city=campaign.city,
        source=campaign.source,
        limit=campaign.target_limit
    )

    return SearchStartResponse(
        campaign_id=campaign.id,
        task_id=task_id,
        status="STARTED",
        message=f"Сбор запущен для «{campaign.niche}» в г. {campaign.city}. Подключитесь к WebSocket /ws/{campaign.id} для получения логов."
    )

@router.post("/stop", response_model=SearchStopResponse, summary="Принудительно остановить сбор")
async def stop_search(req: SearchStopRequest):
    """
    Останавливает запущенный процесс парсинга и закрывает браузер.
    """
    stopped = task_manager.stop_campaign(req.campaign_id)
    if not stopped:
        return SearchStopResponse(
            success=False,
            message="Задача не найдена или уже завершена."
        )
    return SearchStopResponse(
        success=True,
        message=f"Кампания {req.campaign_id} успешно остановлена."
    )

@router.post("/captcha/resolved", response_model=SearchStopResponse, summary="Подтвердить ручное прохождение капчи")
async def captcha_resolved(req: CaptchaResolvedRequest):
    """
    Вызывается фронтендом, когда пользователь решил капчу в открывшемся окне браузера.
    """
    task_manager.signal_captcha_resolved(req.campaign_id)
    return SearchStopResponse(
        success=True,
        message="Сигнал о решении капчи передан воркеру."
    )
