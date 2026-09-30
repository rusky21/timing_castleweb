from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.domain.entities import LeadStatus


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Имя клиента")
    contact: str = Field(..., min_length=3, max_length=200, description="Telegram / Почта / Телефон")
    task_description: str = Field(..., min_length=5, max_length=5000, description="Описание задачи")
    budget: Optional[str] = Field(None, max_length=100, description="Ориентировочный бюджет")
    attachment_url: Optional[str] = Field(None, max_length=500, description="Ссылка на ТЗ / макет в Cloudflare R2")
    
    # Anti-Spam
    hp_website: Optional[str] = Field(None, description="Honeypot скрытое поле для отлова ботов")
    turnstile_token: Optional[str] = Field(None, description="Токен проверки Cloudflare Turnstile")


class LeadResponse(BaseModel):
    id: int
    name: str
    contact: str
    task_description: str
    budget: Optional[str] = None
    attachment_url: Optional[str] = None
    status: LeadStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadStatusUpdate(BaseModel):
    status: LeadStatus
    handled_by: Optional[str] = None
