import os
import re
import uuid
import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.presentation.schemas.upload import PresignedUrlRequest, PresignedUrlResponse
from app.infrastructure.storage.r2_storage import generate_presigned_upload, _resolve_uploads_dir
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    # Documents
    ".pdf", ".docx", ".doc", ".txt", ".csv", ".xlsx", ".xls", ".odt", ".rtf", ".pptx", ".ppt",
    # Images & Graphics
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".heic", ".heif",
    # Archives & Project Files
    ".zip", ".rar", ".7z", ".tar", ".gz", ".fig"
}


@router.post("/presigned-url", response_model=PresignedUrlResponse, summary="Get Presigned URL for File Upload (Cloudflare R2)")
async def get_presigned_url(payload: PresignedUrlRequest):
    """
    Генерирует ссылку для загрузки файла напрямую в Cloudflare R2 (или локальное хранилище).
    Браузер отправляет PUT запрос на upload_url, минуя сервер, а в форму заявки передает public_url.
    """
    ext = Path(payload.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый формат файла '{ext}'. Разрешены: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    upload_url, public_url, storage_type = generate_presigned_upload(
        filename=payload.filename,
        content_type=payload.content_type,
        expires_in=600
    )

    return PresignedUrlResponse(
        upload_url=upload_url,
        public_url=public_url,
        storage_type=storage_type,
        expires_in_seconds=600
    )


@router.post("/file", summary="Local Direct Upload Fallback")
async def upload_local_file(file: UploadFile = File(...)):
    """
    Локальный эндпоинт загрузки файлов (фото, документов, ТЗ, архивов).
    Сохраняет файл в доступную директорию с уникальным безопасным именем.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл не был передан."
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый формат файла '{ext}'. Разрешены форматы: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Sanitize stem (preserve alphanumeric and hyphens, limit length)
    raw_stem = Path(file.filename).stem
    clean_stem = re.sub(r"[^\w\-]", "_", raw_stem)[:40]
    safe_filename = f"{uuid.uuid4().hex[:10]}_{clean_stem}{ext}"

    # Dynamically resolve writable uploads directory
    target_dir = _resolve_uploads_dir()
    save_path = target_dir / safe_filename

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Set read permissions for web server
        try:
            os.chmod(save_path, 0o664)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error saving uploaded file {safe_filename} to {save_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось сохранить файл на сервере: {e}"
        )

    relative_url = f"/uploads/{safe_filename}"
    domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
    public_url = f"https://{domain}{relative_url}"

    logger.info(f"File uploaded successfully: {file.filename} -> {relative_url}")

    return {
        "status": "uploaded",
        "filename": safe_filename,
        "original_name": file.filename,
        "url": relative_url,
        "public_url": public_url
    }
