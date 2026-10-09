from typing import List, Tuple
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import SearchCampaign, Organization
from app.schemas.report import ReportListItem, ReportDetailResponse, ReportSummary
from app.schemas.lead import LeadItem, PitchDetail
from app.core.security import decode_session_token

router = APIRouter(prefix="/api/reports", tags=["Отчёты (История поисков)"])

def get_user_access(request: Request) -> Tuple[bool, int | None]:
    user_payload = getattr(request.state, "user", None)
    if not user_payload:
        token = request.cookies.get("access_token")
        if token:
            user_payload = decode_session_token(token)

    role = (user_payload.get("role") or "").lower() if user_payload else ""
    is_admin = role in ("admin", "superuser", "root")
    uid = None
    if user_payload and user_payload.get("sub"):
        try:
            uid = int(user_payload.get("sub"))
        except (ValueError, TypeError):
            pass
    return is_admin, uid

@router.get("", response_model=List[ReportListItem], summary="Получить историю поисковых кампаний")
async def get_reports(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Возвращает список запущенных поисков для вкладки «Отчёты»:
    - Для администраторов: вся глобальная история студии.
    - Для тестовых/обычных пользователей: только их собственные поиски.
    """
    is_admin, uid = get_user_access(request)

    stmt = (
        select(SearchCampaign)
        .options(selectinload(SearchCampaign.organizations).selectinload(Organization.audit))
    )
    if not is_admin:
        if uid:
            stmt = stmt.where(SearchCampaign.user_id == uid)
        else:
            stmt = stmt.where(SearchCampaign.user_id == -1)

    stmt = stmt.order_by(SearchCampaign.created_at.desc())
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
async def get_report_detail(campaign_id: int, request: Request, db: AsyncSession = Depends(get_db)):
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

    is_admin, uid = get_user_access(request)
    if not is_admin and (c.user_id is None or c.user_id != uid):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="У вас нет доступа к этому отчету")

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
async def delete_report(campaign_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    stmt = select(SearchCampaign).where(SearchCampaign.id == campaign_id)
    res = await db.execute(stmt)
    c = res.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    is_admin, uid = get_user_access(request)
    if not is_admin and (c.user_id is None or c.user_id != uid):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для удаления этого отчета")

    await db.delete(c)
    await db.commit()
    return {"success": True, "message": f"Кампания {campaign_id} удалена"}
