from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import SearchCampaign, Organization
from app.schemas.report import ReportListItem, ReportDetailResponse, ReportSummary
from app.schemas.lead import LeadItem, PitchDetail

router = APIRouter(prefix="/api/reports", tags=["Отчёты (История поисков)"])

@router.get("", response_model=List[ReportListItem], summary="Получить историю всех поисковых кампаний")
async def get_reports(db: AsyncSession = Depends(get_db)):
    """
    Возвращает список всех когда-либо запущенных поисков для вкладки «Отчёты»:
    дата, ниша, город, источник карт, сколько лидов собрано, статус и сводка по проблемам.
    """
    stmt = (
        select(SearchCampaign)
        .options(selectinload(SearchCampaign.organizations).selectinload(Organization.audit))
        .order_by(SearchCampaign.created_at.desc())
    )
    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    items = []
    for c in campaigns:
        summary_dict = c.to_summary_dict()
        items.append(ReportListItem(
            id=c.id,
            created_at=c.created_at,
            finished_at=c.finished_at,
            niche=c.niche,
            city=c.city,
            source=c.source,
            requested_limit=c.target_limit,
            found_count=c.found_count,
            status=c.status,
            summary=ReportSummary(**summary_dict["summary"])
        ))

    return items

@router.get("/{campaign_id}", response_model=ReportDetailResponse, summary="Детальный просмотр отчета по кампании")
async def get_report_detail(campaign_id: int, db: AsyncSession = Depends(get_db)):
    """
    Возвращает полную сводку по кампании и список всех ее лидов.
    """
    stmt = (
        select(SearchCampaign)
        .where(SearchCampaign.id == campaign_id)
        .options(selectinload(SearchCampaign.organizations).selectinload(Organization.audit))
    )
    result = await db.execute(stmt)
    c = result.scalar_one_or_none()

    if not c:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    leads = []
    for org in c.organizations:
        audit = org.audit

        all_phones = list(org.phones or [])
        if audit and audit.extra_phones:
            for ep in audit.extra_phones:
                if ep not in all_phones:
                    all_phones.append(ep)

        primary_phone = all_phones[0] if all_phones else None
        email = audit.extra_emails[0] if (audit and audit.extra_emails) else None
        telegram = None
        if audit and audit.extra_socials:
            telegram = next((s for s in audit.extra_socials if "t.me" in s), None)

        pitch_detail = None
        if audit and audit.pitch_full_text:
            pitch_detail = PitchDetail(
                pain=audit.pitch_pain,
                solution=audit.pitch_solution,
                opening_phrase=audit.pitch_opening_phrase,
                full_text=audit.pitch_full_text
            )

        leads.append(LeadItem(
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

    summary_dict = c.to_summary_dict()
    camp_item = ReportListItem(
        id=c.id,
        created_at=c.created_at,
        finished_at=c.finished_at,
        niche=c.niche,
        city=c.city,
        source=c.source,
        requested_limit=c.target_limit,
        found_count=c.found_count,
        status=c.status,
        summary=ReportSummary(**summary_dict["summary"])
    )

    return ReportDetailResponse(
        campaign=camp_item,
        leads=leads
    )

@router.delete("/{campaign_id}", summary="Удалить кампанию и связанные лиды")
async def delete_report(campaign_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(SearchCampaign).where(SearchCampaign.id == campaign_id)
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    await db.delete(c)
    await db.commit()
    return {"success": True, "message": f"Кампания {campaign_id} удалена"}
