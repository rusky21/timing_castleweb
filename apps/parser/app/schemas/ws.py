from typing import Optional, Literal, Any
from pydantic import BaseModel, Field

class WSEvent(BaseModel):
    """Базовое событие WebSocket"""
    type: Literal["PROGRESS", "AUDIT_STATUS", "NEW_LEAD", "CAPTCHA_REQUIRED", "COMPLETED", "ERROR", "STOPPED"]
    data: Any

class WSProgressData(BaseModel):
    found: int
    limit: int
    percent: int

class WSAuditStatusData(BaseModel):
    domain: str
    step: str  # e.g., "CHECKING_SSL", "CHECKING_VIEWPORT", "EXTRACTING_CONTACTS"
    message: str

class WSCaptchaData(BaseModel):
    service: str  # 'yandex' | '2gis'
    message: str
    hint: str = "Пройдите капчу в открытом окне браузера и нажмите 'Готово' в интерфейсе"
