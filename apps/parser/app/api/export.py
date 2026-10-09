from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import SearchCampaign, Organization
from app.services.excel_exporter import ExcelExporter

router = APIRouter(prefix="/api/export", tags=["Экспорт"])

@router.get("/excel", summary="Экспорт отчета в Excel (.xlsx)")
async def export_excel(
    request: Request,
    campaign_id: int = Query(..., description="ID кампании для выгрузки"),
    db: AsyncSession = Depends(get_db)
):
    """
    Формирует и скачивает файл Excel с цветовой маркировкой статусов, кликабельными ссылками и скриптами звонков.
    """
    user = getattr(request.state, "user", None)
    if not user:
        from app.core.security import decode_session_token
        token = request.cookies.get("access_token")
        if token:
            user = decode_session_token(token)

    role = (user.get("role") or "").lower() if user else ""
    is_admin = role in ("admin", "superuser", "root")
    uid = None
    if user and user.get("sub"):
        try:
            uid = int(user.get("sub"))
        except (ValueError, TypeError):
            pass

    if user and user.get("role") == "demo":
        raise HTTPException(
            status_code=403,
            detail="Экспорт в Excel доступен только в полной версии программы. В тестовом режиме лиды доступны для просмотра в интерфейсе."
        )
    stmt = (
        select(SearchCampaign)
        .where(SearchCampaign.id == campaign_id)
        .options(selectinload(SearchCampaign.organizations).selectinload(Organization.audit))
    )
    res = await db.execute(stmt)
    campaign = res.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    if not is_admin and (campaign.user_id is None or campaign.user_id != uid):
        raise HTTPException(status_code=403, detail="У вас нет прав для выгрузки этого отчета")

    excel_stream = ExcelExporter.generate_campaign_excel(campaign, campaign.organizations)
    
    filename = f"leads_{campaign.niche}_{campaign.city}_{campaign.id}.xlsx"
    # Экранирование для кириллицы в заголовках HTTP
    from urllib.parse import quote
    encoded_filename = quote(filename)

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )
