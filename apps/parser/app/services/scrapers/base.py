import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Awaitable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# ==========================================
# 1. СУЩЕСТВУЮЩИЕ МОДЕЛИ ДЛЯ ЯНДЕКС КАРТ / 2ГИС
# ==========================================

class ScrapedOrgItem(BaseModel):
    """Сырая спарсенная карточка организации из геосервиса"""
    source: str  # 'yandex' | '2gis'
    external_id: str
    name: str
    category: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    rating: float = 0.0
    reviews_count: int = 0
    phones: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    telegram: Optional[str] = None
    socials: List[str] = Field(default_factory=list)
    card_url: Optional[str] = None


class BaseScraper(ABC):
    """Базовый абстрактный класс скрейпера геосервиса"""

    @abstractmethod
    async def scrape(
        self,
        niche: str,
        city: str,
        limit: int,
        on_item_scraped: Callable[[ScrapedOrgItem], Awaitable[None]],
        on_status: Callable[[str], Awaitable[None]],
        on_captcha: Callable[[str], Awaitable[None]],
        is_cancelled: Callable[[], bool],
    ) -> List[ScrapedOrgItem]:
        """
        Запуск скрейпинга геосервиса (Яндекс Карты / 2ГИС)
        """
        pass


# ==========================================
# 2. НОВЫЕ МОДЕЛИ ДЛЯ БИРЖ ФРИЛАНСА
# ==========================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class NormalizedOrder:
    composite_id: str            # Уникальный ключ: f"{platform}_{external_id}"
    platform: str                # 'fl', 'kwork', 'freelancer', 'freelancehunt', 'freelanceru', 'workspace', 'upwork', etc.
    external_id: str             # Исходный ID на бирже
    title: str                   # Название задачи
    url: str                     # Ссылка на заказ
    price_info: str = "Договорная"  # Форматированная строка цены
    price_rub: Optional[int] = None # Нормализованная цена в рублях (для фильтров)
    currency: str = "RUB"        # "RUB", "USD", "EUR", "UAH", etc.
    is_free: bool = True         # True = бесплатный отклик / базовый доступ
    response_type_label: str = "✨ Бесплатный отклик" # Бейдж для Telegram и Web
    description: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=utc_now)
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    def to_fl_order_dict(self) -> Dict[str, Any]:
        """Приводит к совместимой со старой схемой FLOrder структуре для API и БД"""
        safe_int_id = None
        try:
            safe_int_id = int(self.external_id)
        except (ValueError, TypeError):
            # Детерминированный 32-bit ID на основе MD5 для устойчивости между перезапусками процесса
            hash_hex = hashlib.md5(f"{self.platform}_{self.external_id}".encode("utf-8")).hexdigest()
            safe_int_id = int(hash_hex[:8], 16) % 2147483647

        return {
            "id": safe_int_id,
            "platform": self.platform,
            "composite_id": self.composite_id,
            "external_id": str(self.external_id),
            "title": self.title,
            "description": self.description,
            "price_raw": self.price_info,
            "price_rub": self.price_rub,
            "is_negotiable": self.price_rub is None or self.price_rub == 0,
            "category_id": self.category_id or self.platform,
            "category_name": self.category_name or self.platform.upper(),
            "url": self.url,
            "is_pro_only": not self.is_free,
            "is_urgent": False,
            "is_free": self.is_free,
            "response_type_label": self.response_type_label,
            "published_at": self.published_at or self.created_at,
            "created_at": self.created_at,
        }


class BaseFetcher(ABC):
    """Абстрактный класс сборщика для любой биржи фриланса"""
    platform_name: str
    display_name: str
    is_enabled: bool = True

    @abstractmethod
    async def fetch_orders(self) -> List[NormalizedOrder]:
        """Возвращает список свежих нормализованных заказов с площадки"""
        pass
