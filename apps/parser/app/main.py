import sys
import os
import json
import asyncio
import urllib.parse

if sys.platform == "win32" and sys.version_info < (3, 14):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.db.database import init_db, async_session_factory
from app.db.models import SearchCampaign
from app.core.access import get_active_session_user, is_privileged_user
from app.api.auth import router as auth_router
from app.core.security import decode_session_token, get_safe_redirect_url, is_valid_internal_secret
from app.api.search import router as search_router
from app.api.leads import router as leads_router
from app.api.reports import router as reports_router
from app.api.export import router as export_router
from app.api.geo import router as geo_router
from app.api.fl import router as fl_router
from app.api.settings import router as settings_router
from app.api.outreach import router as outreach_router
from app.api.websocket import ws_manager
from app.services.fl.fl_worker import fl_worker
from app.services.orchestrator import orchestrator
from app.services.telegram.bot_service import tg_bot_service
from app.services.telegram.outreach_bot_service import outreach_bot_service
from app.services.outreach import session_manager, followup_worker
from app.services.cleanup_service import cleanup_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("leadhunter")

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.security import get_required_signing_key
    get_required_signing_key()
    # Старт: автоматическая инициализация базы данных SQLite
    logger.info("Initializing SQLite database...")
    await init_db()
    logger.info("Database initialized successfully.")

    # Скрытие старых нерелевантных заказов по стоп-категориям
    try:
        from app.services.filters import hide_existing_excluded_orders
        hidden_count = await hide_existing_excluded_orders()
        logger.info(f"Очистка стоп-категорий в БД: скрыто {hidden_count} нерелевантных заказов.")
    except Exception as e:
        logger.warning(f"Не удалось скрыть нерелевантные заказы при старте: {e}")

    # Запуск фонового парсера FL.ru и мультиплатформенного комбайна
    fl_worker.start()
    await orchestrator.start()
    cleanup_service.start()

    # Запуск основного Telegram-бота (Парсинг, FL.ru, уведомления по картам)
    await tg_bot_service.start()

    # Запуск отдельного бота AI SDR & Outreach (CastleWeb автоответчик и тесты)
    await outreach_bot_service.start()

    # Запуск пула MTProto аккаунтов и воркера Follow-Up
    try:
        await session_manager.start_all_active_accounts()
        followup_worker.start()
    except Exception as e:
        logger.warning(f"Инициализация служб outreach: {e}")

    yield

    # Остановка
    logger.info("Application shutting down...")
    followup_worker.stop()
    try:
        await session_manager.disconnect_all()
    except Exception:
        pass
    cleanup_service.stop()
    fl_worker.stop()
    await orchestrator.stop()
    await outreach_bot_service.stop()
    await tg_bot_service.stop()
    logger.info("Application shutdown complete.")



app = FastAPI(
    title="LeadHunter & Audit API",
    description="Асинхронный бэкенд парсинга Яндекс.Карт и 2ГИС, глубокого аудита сайтов и генерации офферов",
    version="1.0.0",
    lifespan=lifespan
)

# Доверенные прокси (Nginx & Cloudflare) для корректной работы X-Forwarded-Proto и редиректов
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=["*"]
)

# Настройка CORS для локальной разработки и взаимодействия
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth_router)
app.include_router(search_router)
app.include_router(leads_router)
app.include_router(reports_router)
app.include_router(export_router)
app.include_router(geo_router)
app.include_router(fl_router)
app.include_router(settings_router)
app.include_router(outreach_router)

# Middleware защиты маршрутов (Guard)
@app.middleware("http")
async def auth_guard_middleware(request: Request, call_next):
    path = request.url.path

    # Публичные маршруты и статические ресурсы, доступные без авторизации
    public_exact = {
        "/login", "/logout", "/health", "/favicon.ico",
        "/mini-cat.png", "/bg-video.mp4", "/favicon.svg", "/avatar.png"
    }
    public_prefixes = ("/assets", "/docs", "/openapi.json", "/redoc", "/api/internal/")
    static_extensions = (".png", ".jpg", ".jpeg", ".svg", ".ico", ".mp4", ".webp", ".woff2", ".woff", ".css", ".js")

    if path in public_exact or any(path.startswith(prefix) for prefix in public_prefixes) or any(path.endswith(ext) for ext in static_extensions):
        return await call_next(request)

    # Межсервисная авторизация (Backend студии <-> LeadHunter)
    internal_secret = (request.headers.get("X-Internal-Secret") or "").strip()
    if is_valid_internal_secret(internal_secret):
        return await call_next(request)

    # Проверка сессии из Cookie
    token = request.cookies.get("access_token")
    async with async_session_factory() as db:
        current_user = await get_active_session_user(token, db)
        user_payload = ({"sub": str(current_user.id), "email": current_user.email,
                         "role": current_user.role} if current_user else None)

    if not user_payload:
        # Для REST API возвращаем 401
        if path.startswith("/api/"):
            response = Response(
                status_code=401,
                content='{"detail":"Unauthorized"}',
                media_type="application/json"
            )
            response.delete_cookie("access_token", path="/")
            return response

        # Для веб-страниц — редирект на /login с сохранением returnUrl
        return_url = request.url.path
        if request.url.query:
            return_url += f"?{request.url.query}"
        safe_return = get_safe_redirect_url(return_url, default="/")
        response = RedirectResponse(f"/login?returnUrl={urllib.parse.quote(safe_return, safe='/?&=#')}", status_code=303)
        response.delete_cookie("access_token", path="/")
        return response

    request.state.user = user_payload
    return await call_next(request)

def stream_guard(token: str | None, campaign_id: int | None = None):
    """Recheck current rights and JWT expiry before every delivery/heartbeat."""
    async def check(global_event: bool = False) -> bool:
        async with async_session_factory() as db:
            user = await get_active_session_user(token, db)
            if user is None:
                return False
            if campaign_id is None:
                return is_privileged_user(user)
            campaign = await db.get(SearchCampaign, campaign_id)
            if campaign is None or (not is_privileged_user(user) and campaign.user_id != user.id):
                return False
            return not global_event or is_privileged_user(user)
    return check


async def receive_stream(websocket: WebSocket, check):
    while True:
        try:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
        except asyncio.TimeoutError:
            data = None
        if not await check():
            await websocket.close(code=4403)
            return
        if data == "ping":
            await websocket.send_text("pong")


# Глобальный WebSocket для всех событий (FL заказы, смена статусов)
@app.websocket("/ws/events")
async def websocket_global_endpoint(websocket: WebSocket):
    async with async_session_factory() as db:
        user = await get_active_session_user(websocket.cookies.get("access_token"), db)
        if user is None:
            await websocket.close(code=4401)
            return
        if not is_privileged_user(user):
            await websocket.close(code=4403)
            return

    check = stream_guard(websocket.cookies.get("access_token"))
    await ws_manager.connect_global(websocket, check=check)
    try:
        await receive_stream(websocket, check)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Global WebSocket error: {e}")
    finally:
        ws_manager.disconnect_global(websocket)

# WebSocket для стриминга прогресса конкретной кампании
@app.websocket("/ws/{campaign_id}")
async def websocket_endpoint(websocket: WebSocket, campaign_id: int):
    # Проверяем актуальные права до accept; соединение с БД не держим весь стрим.
    async with async_session_factory() as db:
        user = await get_active_session_user(websocket.cookies.get("access_token"), db)
        if user is None:
            await websocket.close(code=4401)
            return
        campaign = await db.get(SearchCampaign, campaign_id) if 0 < campaign_id <= 9223372036854775807 else None
        if campaign is None or (not is_privileged_user(user) and campaign.user_id != user.id):
            await websocket.close(code=4403)
            return

    check = stream_guard(websocket.cookies.get("access_token"), campaign_id)
    await ws_manager.connect(campaign_id, websocket, receive_global=is_privileged_user(user), check=check)
    try:
        await receive_stream(websocket, check)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
    finally:
        ws_manager.disconnect(campaign_id, websocket)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "LeadHunter API"}

# Раздача фронтенда из собранной папки фронт/dist
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

_candidates = [
    Path(__file__).resolve().parent.parent / "фронт" / "dist",
    Path(__file__).resolve().parent.parent / "frontend" / "dist",
    Path(__file__).resolve().parent.parent / "dist",
]
FRONTEND_DIST = next((d for d in _candidates if d.exists()), _candidates[0])

if FRONTEND_DIST.exists():
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str, request: Request):
        # Исключаем API и Swagger роуты
        if full_path.startswith(("api", "docs", "openapi.json", "ws")):
            raise HTTPException(status_code=404, detail="Not found")

        dist_root = FRONTEND_DIST.resolve()
        file_candidate = (FRONTEND_DIST / full_path).resolve()
        if not file_candidate.is_relative_to(dist_root):
            raise HTTPException(status_code=403, detail="Access denied")

        if full_path and file_candidate.is_file():
            return FileResponse(file_candidate)

        index_file = FRONTEND_DIST / "index.html"
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="Frontend index.html not found")

        user_payload = getattr(request.state, "user", None)
        if not user_payload:
            token = request.cookies.get("access_token")
            if token:
                user_payload = decode_session_token(token)

        try:
            content = index_file.read_text(encoding="utf-8")
            if user_payload:
                role = (user_payload.get("role") or "user").lower()
                user_json = json.dumps({
                    "id": user_payload.get("sub"),
                    "email": user_payload.get("email"),
                    "role": role,
                    "is_admin": role in ("admin", "superuser", "root"),
                    "is_paid": role == "paid",
                    "daily_limit": 100 if role == "paid" else (999999 if role in ("admin", "superuser", "root") else 5)
                })
                # Защита от Stored XSS через </script> в данных пользователя
                safe_user_json = user_json.replace("<", "\\u003c").replace(">", "\\u003e")
                injection = f'<script>window.__CURRENT_USER__ = {safe_user_json};</script>'
                content = content.replace("<head>", f"<head>{injection}", 1)
            return HTMLResponse(content)
        except Exception:
            return FileResponse(index_file)
else:
    @app.get("/")
    async def fallback_no_frontend():
        return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>LeadHunter Pro — API Backend</title>
            <style>
                body { background: #0B0F19; color: #f1f5f9; font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
                .card { background: #131B2E; border: 1px solid #1E293B; border-radius: 16px; padding: 40px; max-width: 600px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
                h1 { color: #38BDF8; font-size: 24px; margin-bottom: 12px; }
                p { color: #94A3B8; font-size: 15px; line-height: 1.6; }
                a.btn { display: inline-block; background: #2563EB; color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; margin-top: 16px; transition: background 0.2s; }
                a.btn:hover { background: #1D4ED8; }
                code { background: #0F172A; padding: 4px 8px; border-radius: 6px; color: #38BDF8; font-size: 13px; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🎯 LeadHunter Pro — Бэкенд запущен</h1>
                <p>Бэкенд-сервер и API работают в штатном режиме.<br>Статический бандл фронтенда еще не был собран.</p>
                <a class="btn" href="/docs">Открыть Swagger API документацию</a>
                <p style="margin-top: 24px; font-size: 13px;">Для сборки веб-интерфейса выполните в терминале:<br><code>cd фронт && npm install && npm run build</code></p>
            </div>
        </body>
        </html>
        """)


