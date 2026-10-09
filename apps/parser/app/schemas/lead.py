from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class PitchDetail(BaseModel):
    """Скрипт звонка и оффер для менеджера"""
    pain: Optional[str] = Field(None, description="Боль клиента (почему теряет заявки)")
    solution: Optional[str] = Field(None, description="Предлагаемое решение проблемы")
    opening_phrase: Optional[str] = Field(None, description="Готовая первая фраза для холодного звонка")
    full_text: Optional[str] = Field(None, description="Полный текст оффера")

class LeadItem(BaseModel):
    """Строка таблицы лидов (соответствует дизайну дашборда)"""
    id: int
    campaign_id: int
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    rating: float = 0.0
    reviews_count: int = 0
    
    # Контакты
    primary_phone: Optional[str] = None
    all_phones: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    all_emails: List[str] = Field(default_factory=list)
    telegram: Optional[str] = None
    socials: List[Dict[str, str]] = Field(default_factory=list)
    
    # Сайты и ссылки
    website: Optional[str] = None
    final_url: Optional[str] = None
    card_url: Optional[str] = None
    source: str = "yandex"
    
    # Диагностика и статус-бейдж
    status_badge: str = Field(..., description="NO_SSL | NOT_RESPONSIVE | NO_ANALYTICS | HTTPS_OK | NO_WEBSITE | SITE_DOWN")
    lead_score: int = Field(..., ge=0, le=100, description="Индекс горячести лида от 0 до 100")
    
    # Флаги аудита
    has_ssl: bool = False
    is_adaptive: bool = False
    has_analytics: bool = False
    detected_cms: Optional[str] = None
    last_updated_year: Optional[int] = None
    
    # Питч
    pitch: Optional[PitchDetail] = None

class LeadFilterParams(BaseModel):
    """Параметры фильтрации лидов"""
    campaign_id: Optional[int] = None
    badge: Optional[str] = None  # NO_SSL, NOT_RESPONSIVE, NO_ANALYTICS, NO_WEBSITE, HTTPS_OK
    search: Optional[str] = None
    min_score: Optional[int] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)

class LeadListResponse(BaseModel):
    """Ответ со списком лидов и пагинацией"""
    total: int
    page: int
    page_size: int
    items: List[LeadItem]
