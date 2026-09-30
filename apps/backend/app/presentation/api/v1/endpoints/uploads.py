import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.presentation.schemas.upload import PresignedUrlRequest, PresignedUrlResponse
from app.infrastructure.storage.r2_storage import generate_presigned_upload, UPLOADS_DIR

router = APIRouter()

ALLOWED_EXTENSIONS = {
    ".pdf", ".zip", ".rar", ".7z", ".png", ".jpg", ".jpeg",
    ".docx", ".doc", ".fig", ".txt", ".csv", ".xlsx"
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
    Локальный эндпоинт загрузки файлов (fallback, если в .env не заданы ключи Cloudflare R2).
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый формат файла '{ext}'."
        )

    save_path = UPLOADS_DIR / (file.filename or "upload.bin")
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "url": f"/uploads/{file.filename}"
    }
