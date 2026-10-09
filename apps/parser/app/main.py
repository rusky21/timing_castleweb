import sys
import os
import json
import asyncio

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

from app.db.database import init_db
from app.api.auth import router as auth_router
from app.core.security import decode_session_token
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
from app.services.telegram.bot_service import tg_bot_service
from app.services.telegram.outreach_bot_service import outreach_bot_service
from app.services.outreach import session_manager, followup_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("leadhunter")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Старт: автоматическая инициализация базы данных SQLite
    logger.info("Initializing SQLite database...")
    await init_db()
    logger.info("Database initialized successfully.")

    # Запуск фонового парсера FL.ru
    fl_worker.start()

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
    fl_worker.stop()
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
    internal_secret = request.headers.get("X-Internal-Secret") or request.query_params.get("internal_secret")
    expected_secret = os.environ.get("INTERNAL_API_SECRET", "castleweb-internal-demo-secret")
    if internal_secret and internal_secret == expected_secret:
        return await call_next(request)

    # Проверка сессии из Cookie
    token = request.cookies.get("access_token")
    user_payload = decode_session_token(token) if token else None

    if not user_payload:
        # Для REST API возвращаем 401
        if path.startswith("/api/"):
            return Response(
                status_code=401,
                content='{"detail":"Unauthorized"}',
                media_type="application/json"
            )

        # Для веб-страниц — редирект на /login с сохранением returnUrl
        return_url = request.url.path
        if request.url.query:
            return_url += f"?{request.url.query}"
        return RedirectResponse(f"/login?returnUrl={return_url}", status_code=303)

    request.state.user = user_payload
    return await call_next(request)

# Глобальный WebSocket для всех событий (FL заказы, смена статусов)
@app.websocket("/ws/events")
async def websocket_global_endpoint(websocket: WebSocket):
    # Проверка сессии по Cookie при handshake
    token = websocket.cookies.get("access_token")
    if not token or not decode_session_token(token):
        await websocket.close(code=4401)
        return

    await ws_manager.connect_global(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect_global(websocket)
    except Exception as e:
        logger.warning(f"Global WebSocket error: {e}")
        ws_manager.disconnect_global(websocket)

# WebSocket для стриминга прогресса конкретной кампании
@app.websocket("/ws/{campaign_id}")
async def websocket_endpoint(websocket: WebSocket, campaign_id: int):
    # Проверка сессии по Cookie при handshake
    token = websocket.cookies.get("access_token")
    if not token or not decode_session_token(token):
        await websocket.close(code=4401)
        return

    await ws_manager.connect(campaign_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(campaign_id, websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
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
        file_candidate = FRONTEND_DIST / full_path
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
                    "is_admin": role in ("admin", "superuser", "root")
                })
                injection = f'<script>window.__CURRENT_USER__ = {user_json};</script>'
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


