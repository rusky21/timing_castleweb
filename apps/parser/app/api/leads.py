from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Organization, AuditResult
from app.schemas.lead import LeadListResponse, LeadItem, PitchDetail

router = APIRouter(prefix="/api/leads", tags=["Лиды и аудит"])

@router.get("", response_model=LeadListResponse, summary="Получить список найденных лидов с фильтрацией")
async def get_leads(
    campaign_id: Optional[int] = Query(None, description="ID поисковой кампании"),
    badge: Optional[str] = Query(None, description="Фильтр по бейджу: NO_SSL, NOT_RESPONSIVE, NO_ANALYTICS, HTTPS_OK, NO_WEBSITE"),
    search: Optional[str] = Query(None, description="Поиск по названию или телефону"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Минимальный Lead Score"),
    has_telegram: Optional[bool] = Query(None, description="Фильтр: только компании с Telegram (True)"),
    source: Optional[str] = Query(None, description="Фильтр по источнику: yandex, 2gis"),
    has_website: Optional[bool] = Query(None, description="Фильтр наличия сайта: True (только с сайтом), False (только без сайта)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    query = select(Organization).options(selectinload(Organization.audit))

    if campaign_id:
        query = query.where(Organization.campaign_id == campaign_id)

    if source and source != "all":
        query = query.where(Organization.source.ilike(f"%{source}%"))

    if has_website is not None:
        if has_website:
            query = query.where(Organization.website != None).where(Organization.website != "")
        else:
            query = query.where((Organization.website == None) | (Organization.website == ""))

    if has_telegram is not None:
        if has_telegram:
            query = query.where(Organization.has_telegram.is_(True))
        else:
            query = query.where((Organization.has_telegram.is_(False)) | (Organization.has_telegram.is_(None)))

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(Organization.name.ilike(search_term) | Organization.address.ilike(search_term))

    if badge or min_score:
        query = query.join(Organization.audit)
        if badge:
            query = query.where(AuditResult.status_badge == badge)
        if min_score is not None:
            query = query.where(AuditResult.lead_score >= min_score)

    # Подсчет общего количества
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Сортировка по умолчанию: сначала с наивысшим Lead Score
    query = query.order_by(Organization.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    orgs = result.scalars().all()

    items = []
    for org in orgs:
        audit = org.audit

        all_phones = list(org.phones or [])
        if audit and audit.extra_phones:
            for ep in audit.extra_phones:
                if ep not in all_phones:
                    all_phones.append(ep)

        primary_phone = all_phones[0] if all_phones else None
        email = audit.extra_emails[0] if (audit and audit.extra_emails) else None
        telegram = org.telegram
        if not telegram and audit and audit.extra_socials:
            telegram = next((s for s in audit.extra_socials if "t.me" in s), None)

        pitch_detail = None
        if audit and audit.pitch_full_text:
            pitch_detail = PitchDetail(
                pain=audit.pitch_pain,
                solution=audit.pitch_solution,
                opening_phrase=audit.pitch_opening_phrase,
                full_text=audit.pitch_full_text
            )

        items.append(LeadItem(
            id=org.id,
            campaign_id=org.campaign_id,
            name=org.name,
            category=org.category,
            address=org.address,
            rating=org.rating,
            reviews_count=org.reviews_count,
            primary_phone=primary_phone,
            all_phones=all_phones,
            email=email,
            all_emails=audit.extra_emails if audit else [],
            telegram=telegram,
            socials=[{"url": s} for s in (audit.extra_socials if audit else [])],
            website=org.website,
            final_url=audit.final_url if audit else org.website,
            card_url=org.card_url,
            source=org.source,
            status_badge=audit.status_badge if audit else "NO_WEBSITE",
            lead_score=audit.lead_score if audit else 50,
            has_ssl=audit.has_ssl if audit else False,
            is_adaptive=audit.is_adaptive if audit else False,
            has_analytics=audit.has_analytics if audit else False,
            detected_cms=audit.detected_cms if audit else None,
            last_updated_year=audit.last_updated_year if audit else None,
            pitch=pitch_detail
        ))

    return LeadListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )

@router.get("/{lead_id}/pitch", response_model=PitchDetail, summary="Получить подробный скрипт звонка для лида")
async def get_lead_pitch(lead_id: int, db: AsyncSession = Depends(get_db)):
    """
    Возвращает персонализированный питч для холодного звонка: боль, решение, стартовая фраза.
    """
    stmt = select(AuditResult).where(AuditResult.org_id == lead_id)
    res = await db.execute(stmt)
    audit = res.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Лид или результаты аудита не найдены")

    return PitchDetail(
        pain=audit.pitch_pain or "Технических проблем не зафиксировано.",
        solution=audit.pitch_solution or "Предложить контекстную рекламу или продвижение на картах.",
        opening_phrase=audit.pitch_opening_phrase or "Здравствуйте! Звоню предложить сотрудничество по привлечению клиентов.",
        full_text=audit.pitch_full_text or ""
    )
