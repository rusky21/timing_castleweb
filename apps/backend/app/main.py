from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.core.database import engine, Base
from app.presentation.api.v1.router import api_v1_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist in dev environment
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"🚀 {settings.APP_NAME} started on {settings.APP_HOST}:{settings.APP_PORT} (Env: {settings.APP_ENV})")

    # Background: recover and process any pending leads in queue
    import asyncio
    from app.infrastructure.queue.worker import process_pending_leads
    asyncio.create_task(process_pending_leads())

    # Background: auto-register Telegram webhook if configured
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN not in ("your_bot_token_here", ""):
        async def _register_telegram_webhook():
            await asyncio.sleep(2.0)
            try:
                import httpx
                from app.infrastructure.telegram.bot_service import build_telegram_api_url
                domain = getattr(settings, "DOMAIN_NAME", None) or "castleweb.ru"
                webhook_url = f"https://{domain}/api/v1/telegram/webhook"
                url = build_telegram_api_url("setWebhook")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json={
                        "url": webhook_url,
                        "allowed_updates": ["message", "callback_query"]
                    })
                    data = resp.json()
                    if data.get("ok"):
                        print(f"🤖 Telegram Webhook registered: {webhook_url}")
                    else:
                        print(f"⚠️ Telegram Webhook registration notice: {data}")
            except Exception as e:
                print(f"⚠️ Telegram Webhook registration check failed: {e}")

        asyncio.create_task(_register_telegram_webhook())

    yield
    # Shutdown
    await engine.dispose()
    print("🛑 Database engine connection closed.")



app = FastAPI(
    title=settings.APP_NAME,
    description="High-performance backend API for CASTLEWEB Studio",
    version="1.0.0",
    docs_url="/docs" if (settings.DEBUG or settings.ENABLE_DOCS) else None,
    redoc_url="/redoc" if (settings.DEBUG or settings.ENABLE_DOCS) else None,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # In production, do not leak raw error trace
    error_msg = str(exc) if settings.DEBUG else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"detail": error_msg}
    )


from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.infrastructure.storage.r2_storage import UPLOADS_DIR

# Include API v1 Routes
app.include_router(api_v1_router)

# Mount local uploads directory for static file serving
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

    @app.get("/", summary="Frontend SPA Root")
    async def serve_spa_root():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        target = FRONTEND_DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/", summary="Root Index")
    async def root():
        return {
            "studio": "CASTLEWEB",
            "service": "Backend API",
            "version": "1.0.0",
            "docs": "/docs" if settings.DEBUG else "disabled"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
