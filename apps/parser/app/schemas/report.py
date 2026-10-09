from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.lead import LeadItem

class ReportSummary(BaseModel):
    """Сводная статистика проблем по кампании"""
    no_site: int = 0
    no_ssl: int = 0
    not_responsive: int = 0
    no_analytics: int = 0

class ReportListItem(BaseModel):
    """Строка в таблице отчетов (когда был какой поиск)"""
    id: int
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    niche: str
    city: str
    source: str
    requested_limit: int
    found_count: int
    status: str
    summary: ReportSummary

class ReportDetailResponse(BaseModel):
    """Детальный отчет по конкретной кампании с лидами"""
    campaign: ReportListItem
    leads: List[LeadItem]
