from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Awaitable
from pydantic import BaseModel, Field

class ScrapedOrgItem(BaseModel):
    """Сырая спарсенная карточка организации из геосервиса"""
    source: str  # 'yandex' | '2gis'
    external_id: str
    name: str
    category: Optional[str] = None
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
        Запуск скрейпинга:
        - on_item_scraped: коллбек при нахождении новой организации
        - on_status: коллбек обновления статуса для UI
        - on_captcha: коллбек при появлении капчи
        - is_cancelled: функция проверки отмены задачи
        """
        pass
