import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

SECRET_KEY = os.environ.get("SECRET_KEY", "leadhunter-super-secret-production-key-change-me-in-env")
ALGORITHM = "HS256"
SESSION_LIFETIME_DAYS = int(os.environ.get("SESSION_LIFETIME_DAYS", "7"))

def hash_password(password: str) -> str:
    """Хеширование пароля через bcrypt с автоматической солью"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Безопасная сверка пароля с bcrypt-хешем из БД"""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_session_token(user_id: int, email: str, role: str = "admin") -> str:
    """Генерация подписанного JWT-токена для защищенной Cookie"""
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=SESSION_LIFETIME_DAYS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Декодирование и проверка подписи/срока действия JWT токена"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None
