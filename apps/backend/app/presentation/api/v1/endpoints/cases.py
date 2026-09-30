import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.redis import get_redis_client
from app.infrastructure.db.models import Case, Tag
from app.domain.entities import CaseCategory
from app.presentation.schemas.case import CaseListItem, CaseDetail

router = APIRouter()
logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600  # 1 час кэша


@router.get("", response_model=List[CaseListItem], summary="Get Portfolio Cases List (with Redis Cache)")
async def get_cases(
    category: Optional[CaseCategory] = Query(None, description="Фильтр по направлению: saas, landing, ecommerce, api"),
    tag: Optional[str] = Query(None, description="Фильтр по тегу технологии (например, FastAPI, React)"),
    db: AsyncSession = Depends(get_db)
):
    cat_str = category.value if category else "all"
    tag_str = tag.strip().lower() if tag else "all"
    cache_key = f"cache:cases:list:{cat_str}:{tag_str}"

    redis = await get_redis_client()
    if redis:
        try:
            cached_data = await redis.get(cache_key)
            if cached_data:
                logger.info(f"⚡ Serving cases list from Redis cache ({cache_key})")
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    # Database query
    query = select(Case).where(Case.is_published.is_(True))

    if category:
        query = query.where(Case.category == category)

    if tag:
        query = query.join(Case.tags).where(Tag.name.ilike(tag))

    query = query.order_by(Case.sort_order.asc(), Case.created_at.desc())

    result = await db.execute(query)
    cases = result.scalars().all()

    # Convert to Pydantic models for response & cache
    cases_items = [CaseListItem.model_validate(c) for c in cases]
    serialized_json = json.dumps([c.model_dump(mode="json") for c in cases_items])

    if redis:
        try:
            await redis.set(cache_key, serialized_json, ex=CACHE_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    return cases_items


@router.get("/{slug}", response_model=CaseDetail, summary="Get Case Technical Breakdown by Slug (with Redis Cache)")
async def get_case_detail(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"cache:cases:detail:{slug.strip().lower()}"

    redis = await get_redis_client()
    if redis:
        try:
            cached_detail = await redis.get(cache_key)
            if cached_detail:
                logger.info(f"⚡ Serving case '{slug}' from Redis cache")
                return json.loads(cached_detail)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    query = select(Case).where(Case.slug == slug, Case.is_published.is_(True))
    result = await db.execute(query)
    case_item = result.scalar_one_or_none()

    if not case_item:
        raise HTTPException(status_code=404, detail="Case not found")

    detail_dto = CaseDetail.model_validate(case_item)

    if redis:
        try:
            await redis.set(cache_key, json.dumps(detail_dto.model_dump(mode="json")), ex=CACHE_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    return detail_dto
