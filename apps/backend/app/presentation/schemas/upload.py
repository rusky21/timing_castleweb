from typing import Optional
from pydantic import BaseModel, Field


class PresignedUrlRequest(BaseModel):
    filename: str = Field(..., min_length=3, max_length=200, description="Имя загружаемого файла (например, tz_fintech.pdf)")
    content_type: str = Field(..., description="MIME-тип (например, application/pdf, image/png)")
    file_size_bytes: Optional[int] = Field(None, le=52428800, description="Размер файла в байтах (максимум 50 МБ)")


class PresignedUrlResponse(BaseModel):
    upload_url: str = Field(..., description="URL для прямой загрузки файла (PUT запрос)")
    public_url: str = Field(..., description="Публичный постоянный URL загруженного файла для сохранения в заявке")
    storage_type: str = Field(..., description="'cloudflare_r2' или 'local'")
    expires_in_seconds: int = 600
