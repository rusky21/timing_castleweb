from typing import Optional, Literal
from pydantic import BaseModel, Field

class SearchStartRequest(BaseModel):
    """Параметры запуска поиска с главной формы"""
    niche: str = Field(..., min_length=2, description="Ниша поиска (например, 'Стоматология', 'Автосервис')")
    city: str = Field(..., min_length=2, description="Город поиска (например, 'Казань', 'Москва')")
    source: Literal["yandex", "2gis", "all"] = Field(default="all", description="Источник сбора карт")
    limit: int = Field(default=50, ge=1, le=500, description="Лимит количества собираемых лидов")

class SearchStartResponse(BaseModel):
    """Ответ на запуск задачи сбора"""
    campaign_id: int
    task_id: str
    status: str
    message: str

class SearchStopRequest(BaseModel):
    """Запрос принудительной остановки задачи"""
    campaign_id: int

class SearchStopResponse(BaseModel):
    success: bool
    message: str

class CaptchaResolvedRequest(BaseModel):
    """Сигнал о прохождении капчи пользователем"""
    campaign_id: int
