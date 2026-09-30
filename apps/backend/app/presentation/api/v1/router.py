from fastapi import APIRouter
from app.presentation.api.v1.endpoints import health, status, cases, leads, telegram_webhook, uploads

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(status.router, tags=["Status"])
api_v1_router.include_router(cases.router, prefix="/cases", tags=["Cases"])
api_v1_router.include_router(leads.router, prefix="/leads", tags=["Leads"])
api_v1_router.include_router(telegram_webhook.router, prefix="/telegram", tags=["Telegram CRM"])
api_v1_router.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
