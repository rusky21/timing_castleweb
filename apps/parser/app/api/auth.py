import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User
from app.core.security import verify_password, create_session_token, decode_session_token
from app.core.rate_limiter import login_limiter

router = APIRouter(tags=["Authentication"])

# Флаг Secure для Cookie: True для продакшна за Cloudflare (HTTPS)
# Позволяет отключить через COOKIE_SECURE=false при локальной отладке по HTTP
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() in ("true", "1", "yes")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, returnUrl: str = "/", error: Optional[str] = None):
    """Страница входа в систему LeadHunter Pro в стилистике основного интерфейса"""
    token = request.cookies.get("access_token")
    if token and decode_session_token(token):
        return RedirectResponse(url=returnUrl or "/", status_code=status.HTTP_303_SEE_OTHER)

    error_html = ""
    if error == "invalid_credentials":
        error_html = '''
        <div class="alert alert-error">
            <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <div>
                <div class="alert-title">Ошибка авторизации</div>
                <div class="alert-desc">Неверный логин или мастер-пароль</div>
            </div>
        </div>
        '''
    elif error == "inactive":
        error_html = '''
        <div class="alert alert-error">
            <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18.364 18.364A9 9 0 0 0 5.636 5.636m12.728 12.728A9 9 0 0 1 5.636 5.636m12.728 12.728L5.636 5.636"></path>
            </svg>
            <div>
                <div class="alert-title">Доступ заблокирован</div>
                <div class="alert-desc">Учетная запись деактивирована администратором</div>
            </div>
        </div>
        '''
    elif error == "session_expired":
        error_html = '''
        <div class="alert alert-warn">
            <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <div>
                <div class="alert-title">Сессия завершена</div>
                <div class="alert-desc">Срок действия токена истек. Войдите заново</div>
            </div>
        </div>
        '''

    html_content = f"""<!DOCTYPE html>
<html lang="ru" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LeadHunter Pro | Вход в систему</title>
    <link rel="icon" type="image/png" href="/mini-cat.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        ::selection {{
            background: rgba(255, 255, 255, 0.2);
            color: #ffffff;
        }}

        body {{
            background-color: #000000;
            color: #ededed;
            font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow-x: hidden;
            padding: 24px;
        }}

        /* Ambient Video Background */
        .bg-video {{
            position: fixed;
            inset: 0;
            width: 100vw;
            height: 100vh;
            object-fit: cover;
            object-position: center;
            z-index: 0;
            opacity: 0.32;
            filter: contrast(1.15) brightness(0.9);
            pointer-events: none;
        }}

        /* Dark Vignette Overlay */
        .bg-overlay {{
            position: fixed;
            inset: 0;
            z-index: 1;
            background: 
                radial-gradient(circle at 50% 35%, rgba(13, 17, 28, 0.55) 0%, rgba(0, 0, 0, 0.94) 80%),
                linear-gradient(180deg, rgba(0, 0, 0, 0.3) 0%, rgba(0, 0, 0, 0.85) 100%);
            pointer-events: none;
        }}

        /* Top Corner Status Bar */
        .top-bar {{
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 20;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 9999px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            color: #34d399;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }}

        .status-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 8px #10b981;
            animation: pulse-dot 2s infinite cubic-bezier(0.4, 0, 0.6, 1);
        }}

        @keyframes pulse-dot {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.4; transform: scale(0.85); }}
        }}

        /* Main Container */
        .auth-container {{
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 440px;
        }}

        /* Glassmorphic Card */
        .auth-card {{
            background: rgba(14, 14, 18, 0.82);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 
                0 30px 60px -15px rgba(0, 0, 0, 0.9),
                0 0 0 1px rgba(255, 255, 255, 0.04),
                0 0 50px rgba(56, 189, 248, 0.04);
            transition: border-color 0.3s ease;
        }}

        .auth-card:hover {{
            border-color: rgba(255, 255, 255, 0.16);
        }}

        /* Brand Header */
        .brand {{
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 24px;
        }}

        .logo-wrap {{
            width: 44px;
            height: 44px;
            background: #121215;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 3px;
            flex-shrink: 0;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
            transition: border-color 0.2s ease, transform 0.2s ease;
        }}

        .logo-wrap:hover {{
            border-color: rgba(255, 255, 255, 0.3);
            transform: scale(1.04);
        }}

        .logo-img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            filter: invert(100%);
        }}

        .brand-text {{
            display: flex;
            flex-direction: column;
        }}

        .brand-title {{
            font-size: 17px;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #ffffff;
            display: flex;
            align-items: baseline;
            gap: 6px;
        }}

        .brand-title .pro {{
            font-size: 12px;
            font-weight: 600;
            color: #38bdf8;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
        }}

        .brand-tagline {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #64748b;
            letter-spacing: 0.02em;
            margin-top: 2px;
        }}

        .title-block {{
            margin-bottom: 26px;
        }}

        h1 {{
            font-size: 22px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.025em;
            margin-bottom: 6px;
        }}

        p.description {{
            font-size: 13px;
            color: #94a3b8;
            line-height: 1.5;
        }}

        /* Alerts */
        .alert {{
            padding: 13px 15px;
            border-radius: 14px;
            font-size: 13px;
            margin-bottom: 22px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            line-height: 1.4;
            animation: fadeIn 0.25s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .alert-error {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.25);
            color: #fca5a5;
        }}

        .alert-warn {{
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.25);
            color: #fde047;
        }}

        .alert-icon {{
            width: 18px;
            height: 18px;
            flex-shrink: 0;
            margin-top: 1px;
        }}

        .alert-title {{
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 2px;
        }}

        .alert-desc {{
            font-size: 12px;
            opacity: 0.9;
        }}

        /* Form */
        form {{
            display: flex;
            flex-direction: column;
            gap: 18px;
        }}

        .form-group {{
            display: flex;
            flex-direction: column;
        }}

        label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #a1a1aa;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .input-wrapper {{
            position: relative;
            display: flex;
            align-items: center;
        }}

        .input-icon {{
            position: absolute;
            left: 14px;
            width: 17px;
            height: 17px;
            color: #71717a;
            pointer-events: none;
            transition: color 0.2s ease;
        }}

        input[type="email"],
        input[type="password"],
        input[type="text"] {{
            width: 100%;
            height: 48px;
            padding: 0 42px 0 42px;
            background: #101013;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 14px;
            color: #ffffff;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
            outline: none;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        input[type="email"]::placeholder,
        input[type="password"]::placeholder,
        input[type="text"]::placeholder {{
            color: #52525b;
            font-size: 13px;
        }}

        input:hover {{
            border-color: rgba(255, 255, 255, 0.2);
            background: #121216;
        }}

        input:focus {{
            border-color: rgba(255, 255, 255, 0.35);
            background: #141418;
            box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.08);
        }}

        input:focus + .input-icon,
        .input-wrapper:focus-within .input-icon {{
            color: #e4e4e7;
        }}

        .toggle-pwd-btn {{
            position: absolute;
            right: 12px;
            background: none;
            border: none;
            padding: 4px;
            color: #71717a;
            cursor: pointer;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.2s ease, background 0.2s ease;
        }}

        .toggle-pwd-btn:hover {{
            color: #e4e4e7;
            background: rgba(255, 255, 255, 0.06);
        }}

        .toggle-pwd-btn svg {{
            width: 16px;
            height: 16px;
        }}

        /* Submit Button */
        .btn-submit {{
            width: 100%;
            height: 50px;
            margin-top: 8px;
            background: #ffffff;
            color: #000000;
            border: none;
            border-radius: 14px;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: -0.01em;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 4px 20px rgba(255, 255, 255, 0.15);
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .btn-submit:hover {{
            background: #e5e5e5;
            box-shadow: 0 6px 24px rgba(255, 255, 255, 0.25);
            transform: translateY(-1px);
        }}

        .btn-submit:active {{
            transform: scale(0.98);
        }}

        .btn-submit svg.arrow-icon {{
            width: 16px;
            height: 16px;
            transition: transform 0.2s ease;
        }}

        .btn-submit:hover svg.arrow-icon {{
            transform: translateX(3px);
        }}

        .btn-submit:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}

        .spinner {{
            width: 16px;
            height: 16px;
            border: 2px solid rgba(0, 0, 0, 0.2);
            border-top-color: #000000;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }}

        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}

        /* Footer Meta Info */
        .card-footer {{
            margin-top: 28px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #52525b;
        }}

        .security-badge {{
            display: flex;
            align-items: center;
            gap: 5px;
            color: #71717a;
        }}

        .security-badge svg {{
            width: 12px;
            height: 12px;
            color: #38bdf8;
        }}

        @media (max-width: 480px) {{
            body {{
                padding: 16px;
            }}
            .auth-card {{
                padding: 28px 22px;
            }}
            .top-bar {{
                top: 16px;
                right: 16px;
            }}
        }}
    </style>
</head>
<body>
    <!-- Ambient Background Video -->
    <video class="bg-video" autoplay loop muted playsinline src="/bg-video.mp4" poster=""></video>
    <div class="bg-overlay"></div>

    <!-- Live System Badge in Top-Right -->
    <div class="top-bar">
        <div class="status-badge">
            <span class="status-dot"></span>
            <span>SYSTEM ONLINE</span>
        </div>
    </div>

    <!-- Centered Card Container -->
    <div class="auth-container">
        <div class="auth-card">
            <!-- Brand -->
            <div class="brand">
                <div class="logo-wrap">
                    <img src="/mini-cat.png" alt="LeadHunter Core" class="logo-img">
                </div>
                <div class="brand-text">
                    <div class="brand-title">LeadGen & Audit <span class="pro">PRO</span></div>
                    <div class="brand-tagline">// HIGH-PERFORMANCE SCRAPER & AUDIT</div>
                </div>
            </div>

            <!-- Title & Subtitle -->
            <div class="title-block">
                <h1>Вход в систему</h1>
                <p class="description">Авторизуйтесь для доступа к панели лидогенерации, картам и бирже FL.ru</p>
            </div>

            {error_html}

            <!-- Form -->
            <form method="POST" action="/login" id="loginForm">
                <input type="hidden" name="returnUrl" value="{returnUrl}">

                <div class="form-group">
                    <label for="email">
                        <span>Электронная почта</span>
                        <span style="color: #52525b;">AUTH ID</span>
                    </label>
                    <div class="input-wrapper">
                        <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect width="20" height="16" x="2" y="4" rx="2"></rect>
                            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"></path>
                        </svg>
                        <input 
                            type="email" 
                            id="email" 
                            name="email" 
                            required 
                            autocomplete="username" 
                            placeholder="admin@lead.pro" 
                            autofocus
                        >
                    </div>
                </div>

                <div class="form-group">
                    <label for="password">
                        <span>Пароль доступа</span>
                        <span style="color: #52525b;">SECURITY KEY</span>
                    </label>
                    <div class="input-wrapper">
                        <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect width="18" height="11" x="3" y="11" rx="2" ry="2"></rect>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        </svg>
                        <input 
                            type="password" 
                            id="password" 
                            name="password" 
                            required 
                            autocomplete="current-password" 
                            placeholder="••••••••••••"
                        >
                        <button type="button" class="toggle-pwd-btn" id="togglePwd" title="Показать пароль" aria-label="Показать пароль">
                            <svg id="eyeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                        </button>
                    </div>
                </div>

                <button type="submit" class="btn-submit" id="submitBtn">
                    <span>Войти в систему</span>
                    <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M5 12h14"></path>
                        <path d="m12 5 7 7-7 7"></path>
                    </svg>
                </button>
            </form>

            <div class="card-footer">
                <div class="security-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    </svg>
                    <span>TLS Encrypted Node</span>
                </div>
                <div>v2.4.0 PRO</div>
            </div>
        </div>
    </div>

    <script>
        // Toggle password visibility
        const toggleBtn = document.getElementById('togglePwd');
        const pwdInput = document.getElementById('password');
        const eyeIcon = document.getElementById('eyeIcon');

        toggleBtn.addEventListener('click', () => {{
            if (pwdInput.type === 'password') {{
                pwdInput.type = 'text';
                eyeIcon.innerHTML = `
                    <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"></path>
                    <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"></path>
                    <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"></path>
                    <line x1="2" y1="2" x2="22" y2="22"></line>
                `;
                toggleBtn.title = 'Скрыть пароль';
            }} else {{
                pwdInput.type = 'password';
                eyeIcon.innerHTML = `
                    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                `;
                toggleBtn.title = 'Показать пароль';
            }}
        }});

        // Button submit spinner state
        const form = document.getElementById('loginForm');
        const submitBtn = document.getElementById('submitBtn');

        form.addEventListener('submit', () => {{
            submitBtn.disabled = true;
            submitBtn.innerHTML = `
                <span class="spinner"></span>
                <span>Авторизация...</span>
            `;
        }});
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    returnUrl: str = Form("/"),
    db: AsyncSession = Depends(get_db)
):
    """Обработчик отправки формы входа"""
    # 1. Защита от брутфорса с учетом реального IP от Cloudflare
    login_limiter.check(request)

    # 2. Поиск пользователя в нашей БД
    clean_email = email.strip().lower()
    query = select(User).where(User.email == clean_email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Проверка пароля и статуса пользователя
    if not user or not verify_password(password, user.password_hash):
        if "application/json" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        return RedirectResponse(
            url=f"/login?error=invalid_credentials&returnUrl={returnUrl}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    if not user.is_active:
        if "application/json" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Учетная запись деактивирована"
            )
        return RedirectResponse(
            url=f"/login?error=inactive&returnUrl={returnUrl}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # 3. Фиксация времени последнего входа
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # 4. Выпуск JWT токена
    token = create_session_token(user.id, user.email, user.role)

    # 5. Установка защищенной HTTP-Only Cookie
    target_url = returnUrl if (returnUrl and not returnUrl.startswith("/login")) else "/"
    response = RedirectResponse(url=target_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=7 * 86400,
        path="/"
    )
    return response

@router.get("/logout")
@router.post("/logout")
async def logout():
    """Выход из аккаунта и очистка Cookie"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/")
    return response

@router.get("/api/auth/me")
async def get_current_user_info(request: Request):
    """Получение информации о текущем пользователе (для фронтенда)"""
    user_data = getattr(request.state, "user", None)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {
        "id": user_data.get("sub"),
        "email": user_data.get("email"),
        "role": user_data.get("role")
    }

# ====================================================================
# Управление пользователями (Доступно только администраторам)
# ====================================================================
from pydantic import BaseModel, Field
from app.core.security import hash_password

class UserCreateSchema(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    role: str = "admin"

class UserUpdateSchema(BaseModel):
    password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None
    role: Optional[str] = None

def require_admin(request: Request):
    user_data = getattr(request.state, "user", None)
    if not user_data or user_data.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права администратора")
    return user_data

@router.get("/api/users")
async def get_users_list(request: Request, db: AsyncSession = Depends(get_db)):
    """Получение списка всех пользователей системы"""
    require_admin(request)
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None
        }
        for u in users
    ]

@router.post("/api/users", status_code=status.HTTP_201_CREATED)
async def create_user_api(payload: UserCreateSchema, request: Request, db: AsyncSession = Depends(get_db)):
    """Создание нового пользователя"""
    require_admin(request)
    clean_email = payload.email.strip().lower()

    existing = (await db.execute(select(User).where(User.email == clean_email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует")

    new_user = User(
        email=clean_email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "status": "success",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "role": new_user.role,
            "is_active": new_user.is_active
        }
    }

@router.patch("/api/users/{user_id}")
async def update_user_api(user_id: int, payload: UserUpdateSchema, request: Request, db: AsyncSession = Depends(get_db)):
    """Обновление пароля или статуса пользователя"""
    require_admin(request)
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role

    await db.commit()
    return {"status": "updated", "id": user.id, "email": user.email}

@router.delete("/api/users/{user_id}")
async def delete_user_api(user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Удаление пользователя"""
    current_admin = require_admin(request)
    if str(user_id) == str(current_admin.get("sub")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя удалить собственную учетную запись")

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    await db.delete(user)
    await db.commit()
    return {"status": "deleted", "id": user_id}

# ====================================================================
# Внутренний эндпоинт для генерации демо-аккаунтов из Telegram-бота
# ====================================================================
import secrets
import string

class CreateDemoUserPayload(BaseModel):
    tg_user_id: str
    tg_username: Optional[str] = None
    secret_key: Optional[str] = None

@router.post("/api/internal/create-demo-user")
async def create_demo_user(
    payload: CreateDemoUserPayload,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Внутренний эндпоинт для Telegram-бота студии:
    Создает или возвращает временный демо-аккаунт на 5 запросов с кулдауном 15 минут.
    """
    secret = request.headers.get("X-Internal-Secret") or payload.secret_key
    expected_secret = os.environ.get("INTERNAL_API_SECRET", "castleweb-internal-demo-secret")
    if secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Invalid internal secret")

    clean_tg_id = str(payload.tg_user_id).strip()
    if not clean_tg_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tg_user_id is required")

    from app.config import ADMIN_TELEGRAM_IDS
    is_admin = False
    clean_username = (payload.tg_username or "").strip().lower().lstrip("@")
    clean_id_str = str(clean_tg_id).strip()
    try:
        clean_id_int = int(clean_id_str)
        is_admin = (
            (clean_id_int in ADMIN_TELEGRAM_IDS)
            or (clean_id_int == 1878543896)
            or (clean_username in ("kupidon996", "ya_emildjan", "castleweb_admin", "admin"))
        )
    except Exception:
        is_admin = (clean_username in ("kupidon996", "ya_emildjan", "castleweb_admin", "admin"))

    # Проверяем, существует ли уже аккаунт для данного Telegram ID
    query = select(User).where(User.tg_user_id == clean_tg_id)
    res = await db.execute(query)
    existing_user = res.scalar_one_or_none()

    if is_admin:
        new_password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        if existing_user:
            existing_user.role = "admin"
            existing_user.demo_searches_left = 999999
            existing_user.max_companies_per_search = 1000
            existing_user.is_active = True
            existing_user.password_hash = hash_password(new_password)
            await db.commit()
            return {
                "status": "admin",
                "email": existing_user.email,
                "password": new_password,
                "role": "admin",
                "demo_searches_left": 999999,
                "max_companies_per_search": 1000,
                "cooldown_minutes": 0,
                "message": "Безграничный доступ Администратора активирован"
            }
        else:
            suffix = clean_tg_id[-4:] if len(clean_tg_id) >= 4 else clean_tg_id
            email = f"admin_{suffix}@castleweb.ru"
            new_user = User(
                email=email,
                password_hash=hash_password(new_password),
                role="admin",
                is_active=True,
                tg_user_id=clean_tg_id,
                demo_searches_left=999999,
                max_companies_per_search=1000,
                created_at=datetime.now(timezone.utc)
            )
            db.add(new_user)
            await db.commit()
            return {
                "status": "admin",
                "email": email,
                "password": new_password,
                "role": "admin",
                "demo_searches_left": 999999,
                "max_companies_per_search": 1000,
                "cooldown_minutes": 0,
                "message": "Безграничный доступ Администратора активирован"
            }

    if existing_user:
        # Если попытки уже исчерпаны — тестовый режим повторно не выдается
        if existing_user.demo_searches_left <= 0:
            return {
                "status": "exhausted",
                "email": existing_user.email,
                "demo_searches_left": 0,
                "max_companies_per_search": existing_user.max_companies_per_search,
                "cooldown_minutes": 15,
                "message": "Тестовый доступ уже был использован (0 из 5 запросов). Тестовый режим выдаётся только 1 раз."
            }

        # Если попытки еще остались — напоминаем данные существующего аккаунта
        new_password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        existing_user.password_hash = hash_password(new_password)
        existing_user.is_active = True
        await db.commit()
        return {
            "status": "already_active",
            "email": existing_user.email,
            "password": new_password,
            "demo_searches_left": existing_user.demo_searches_left,
            "max_companies_per_search": existing_user.max_companies_per_search,
            "cooldown_minutes": 15,
            "message": "Вы уже получили демо-доступ ранее."
        }

    # Генерируем уникальный логин и пароль
    suffix = clean_tg_id[-4:] if len(clean_tg_id) >= 4 else clean_tg_id
    rand_chars = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    email = f"demo_{suffix}_{rand_chars}@castleweb.ru"
    password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

    new_user = User(
        email=email,
        password_hash=hash_password(password),
        role="demo",
        is_active=True,
        tg_user_id=clean_tg_id,
        demo_searches_left=5,
        max_companies_per_search=5,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "status": "created",
        "email": new_user.email,
        "password": password,
        "demo_searches_left": new_user.demo_searches_left,
        "max_companies_per_search": new_user.max_companies_per_search,
        "cooldown_minutes": 15
    }

