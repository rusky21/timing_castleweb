import os
import logging
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import FLOrder, FLOrderInteraction, FLCategorySync, utc_now
from app.services.fl.constants import FL_CATEGORIES, CATEGORY_BY_ID
from app.services.fl.fl_worker import fl_worker
from app.services.connection_manager import ws_manager
from app.core.security import decode_session_token

logger = logging.getLogger("fl_api")

def require_fl_access(request: Request):
    """
    Разрешает доступ к бирже FL.ru только:
    1) Запросам с валидным секретом X-Internal-Secret (Telegram-бот студии)
    2) Авторизованным пользователям с ролью 'admin'
    """
    internal_secret = request.headers.get("X-Internal-Secret") or request.query_params.get("internal_secret")
    expected_secret = os.environ.get("INTERNAL_API_SECRET", "castleweb-internal-demo-secret")
    if internal_secret and internal_secret == expected_secret:
        return {"role": "admin", "sub": "internal_service"}

    user_data = getattr(request.state, "user", None)
    if not user_data:
        token = request.cookies.get("access_token")
        if token:
            user_data = decode_session_token(token)

    role = (user_data.get("role") or "").lower() if user_data else ""
    if not user_data or role not in ("admin", "superuser", "root"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к бирже фриланса и заказам разрешен только администраторам"
        )
    return user_data

router = APIRouter(prefix="/api/fl", tags=["Биржа FL.ru"], dependencies=[Depends(require_fl_access)])

class InteractionUpdate(BaseModel):
    is_favorite: Optional[bool] = None
    is_hidden: Optional[bool] = None
    is_read: Optional[bool] = None
    notes: Optional[str] = None

@router.get("/categories", summary="Получить список категорий биржи FL.ru")
async def get_categories():
    return FL_CATEGORIES

@router.get("/orders", summary="Получить список заказов FL.ru с фильтрами")
async def get_orders(
    category_id: Optional[str] = Query(None, description="ID категории FL"),
    min_price: Optional[int] = Query(None, ge=0, description="Минимальный бюджет в рублях"),
    is_favorite: Optional[bool] = Query(None, description="Только избранные"),
    is_hidden: Optional[bool] = Query(False, description="Показывать скрытые"),
    search: Optional[str] = Query(None, description="Поиск по ключевым словам"),
    is_pro_only: Optional[bool] = Query(None, description="Фильтр только для PRO"),
    is_urgent: Optional[bool] = Query(None, description="Фильтр только срочных"),
    allow_negotiable: Optional[bool] = Query(True, description="Включать проекты по договоренности"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    query = select(FLOrder).options(selectinload(FLOrder.interaction))

    # Скрытые / не скрытые
    if is_hidden is not None:
        if not is_hidden:
            # Исключаем скрытые: либо нет записи в interaction, либо is_hidden == False
            query = query.outerjoin(FLOrder.interaction).where(
                or_(FLOrderInteraction.is_hidden == False, FLOrderInteraction.is_hidden == None)
            )
        else:
            query = query.join(FLOrder.interaction).where(FLOrderInteraction.is_hidden == True)

    # Избранные
    if is_favorite is not None:
        if is_favorite:
            query = query.join(FLOrder.interaction).where(FLOrderInteraction.is_favorite == True)
        else:
            query = query.outerjoin(FLOrder.interaction).where(
                or_(FLOrderInteraction.is_favorite == False, FLOrderInteraction.is_favorite == None)
            )

    # Категория
    if category_id and category_id != "all":
        query = query.where(FLOrder.category_id == category_id)

    # PRO и Срочность
    if is_pro_only is not None:
        query = query.where(FLOrder.is_pro_only == is_pro_only)
    if is_urgent is not None:
        query = query.where(FLOrder.is_urgent == is_urgent)

    # Минимальная цена и по договоренности
    if not allow_negotiable:
        query = query.where(FLOrder.is_negotiable == False)

    if min_price and min_price > 0:
        if allow_negotiable:
            query = query.where(
                or_(
                    FLOrder.price_rub >= min_price,
                    FLOrder.is_negotiable == True
                )
            )
        else:
            query = query.where(FLOrder.price_rub >= min_price)

    # Поиск по заголовку и описанию
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                FLOrder.title.ilike(term),
                FLOrder.description.ilike(term)
            )
        )

    # Подсчет total
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Сортировка: самые свежие сверху
    query = query.order_by(FLOrder.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    res = await db.execute(query)
    orders = res.scalars().all()

    return {
        "items": [o.to_dict() for o in orders],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.post("/orders/{order_id}/interaction", summary="Обновить статус заказа (прочитано / избранное / скрыть)")
async def update_order_interaction(
    order_id: int,
    payload: InteractionUpdate,
    db: AsyncSession = Depends(get_db)
):
    order = await db.get(FLOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    interaction = await db.get(FLOrderInteraction, order_id)
    if not interaction:
        interaction = FLOrderInteraction(
            order_id=order_id,
            is_favorite=payload.is_favorite if payload.is_favorite is not None else False,
            is_hidden=payload.is_hidden if payload.is_hidden is not None else False,
            is_read=payload.is_read if payload.is_read is not None else False,
            notes=payload.notes,
            updated_at=utc_now()
        )
        db.add(interaction)
    else:
        if payload.is_favorite is not None:
            interaction.is_favorite = payload.is_favorite
        if payload.is_hidden is not None:
            interaction.is_hidden = payload.is_hidden
        if payload.is_read is not None:
            interaction.is_read = payload.is_read
        if payload.notes is not None:
            interaction.notes = payload.notes
        interaction.updated_at = utc_now()

    await db.commit()

    # Оповещаем десктоп по WebSocket о смене статуса
    await ws_manager.broadcast_all({
        "type": "FL_ORDER_INTERACTION_UPDATED",
        "data": {
            "order_id": order_id,
            "is_favorite": interaction.is_favorite,
            "is_hidden": interaction.is_hidden,
            "is_read": interaction.is_read
        }
    })

    return {
        "order_id": order_id,
        "is_favorite": interaction.is_favorite,
        "is_hidden": interaction.is_hidden,
        "is_read": interaction.is_read
    }

@router.post("/poll", summary="Принудительно запустить шаг проверки ленты FL.ru")
async def trigger_poll():
    import asyncio
    asyncio.create_task(fl_worker.poll_cycle())
    return {"status": "ok", "message": "Опрос FL.ru запущен в фоне"}

@router.get("/stats", summary="Сводка по заказам FL.ru")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(FLOrder.id)))).scalar_one() or 0
    favorites = (await db.execute(
        select(func.count(FLOrderInteraction.order_id)).where(FLOrderInteraction.is_favorite == True)
    )).scalar_one() or 0

    syncs_res = await db.execute(select(FLCategorySync).order_by(FLCategorySync.synced_at.desc()).limit(1))
    last_sync = syncs_res.scalar_one_or_none()

    return {
        "total_orders": total,
        "favorite_orders": favorites,
        "last_synced_at": last_sync.synced_at.isoformat() if last_sync else None
    }

@router.get("/worker/status", summary="Статус фонового воркера FL.ru")
async def get_worker_status():
    return {
        "is_running": fl_worker.is_running,
        "poll_interval_min": fl_worker.poll_interval_min,
        "poll_interval_max": fl_worker.poll_interval_max,
        "next_poll_in": round(fl_worker.next_poll_in, 1),
        "last_poll_at": fl_worker.last_poll_at.isoformat() if fl_worker.last_poll_at else None,
    }
