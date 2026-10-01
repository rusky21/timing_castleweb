import os
import uuid
import logging
from pathlib import Path
from typing import Tuple
from botocore.client import Config
import boto3
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Base upload directory from settings
def _resolve_uploads_dir() -> Path:
    """
    Определяет доступную для записи директорию загрузок:
    1. /app/uploads (Docker volume mount)
    2. settings.UPLOAD_DIR
    3. relative uploads folder
    """
    candidates = [
        Path("/app/uploads"),
        Path(settings.UPLOAD_DIR) if getattr(settings, "UPLOAD_DIR", None) else None,
        Path(__file__).resolve().parent.parent.parent.parent / "uploads"
    ]
    for c in candidates:
        if not c:
            continue
        try:
            c.mkdir(parents=True, exist_ok=True)
            test_file = c / ".perm_check"
            test_file.write_text("ok")
            test_file.unlink(missing_ok=True)
            return c
        except Exception:
            continue

    # Fallback to /tmp/uploads
    tmp = Path("/tmp/uploads")
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp

UPLOADS_DIR = _resolve_uploads_dir()


def get_r2_client():
    """
    Создает S3-совместимый клиент для Cloudflare R2 только если STORAGE_DRIVER == 'r2'.
    """
    if getattr(settings, "STORAGE_DRIVER", "local").lower() != "r2":
        return None

    if not (settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY):
        return None

    endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto"
    )


def generate_presigned_upload(
    filename: str,
    content_type: str,
    expires_in: int = 600
) -> Tuple[str, str, str]:
    """
    Генерирует ссылку для загрузки файла:
    - Если в .env настроен Cloudflare R2: возвращает Presigned PUT URL для прямой загрузки в бакет.
    - Если R2 не настроен: возвращает локальный эндпоинт загрузки для бесшовной локальной разработки.
    
    Возвращает кортеж: (upload_url, public_url, storage_type)
    """
    # Генерируем уникальное безопасное имя файла
    ext = Path(filename).suffix.lower()
    unique_key = f"leads/{uuid.uuid4().hex}{ext}"

    r2 = get_r2_client()

    if r2:
        try:
            # Генерация подписанной ссылки для прямого PUT в Cloudflare R2
            upload_url = r2.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": settings.R2_BUCKET_NAME,
                    "Key": unique_key,
                    "ContentType": content_type
                },
                ExpiresIn=expires_in
            )
            # Публичный URL
            if settings.R2_PUBLIC_DOMAIN:
                public_domain = settings.R2_PUBLIC_DOMAIN.rstrip('/')
                public_url = f"{public_domain}/{unique_key}"
            else:
                public_url = f"https://{settings.R2_BUCKET_NAME}.r2.dev/{unique_key}"

            logger.info(f"Generated Cloudflare R2 presigned URL for key '{unique_key}'")
            return upload_url, public_url, "cloudflare_r2"
        except Exception as e:
            logger.warning(f"Failed to generate R2 presigned URL: {e}. Falling back to local storage.")

    # Local fallback
    upload_url = "/api/v1/uploads/file"
    public_url = f"/uploads/{Path(unique_key).name}"
    return upload_url, public_url, "local"
