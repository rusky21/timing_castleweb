import httpx
import logging
import secrets
import re
from fastapi import HTTPException, Request
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
COMPROMISED_INTERNAL_SECRETS = frozenset({
    "castleweb-internal-demo-secret",
    "castleweb_internal_secret_123",
})


def get_required_internal_secret() -> str:
    """Возвращает безопасный межсервисный секрет или останавливает операцию."""
    configured = (settings.INTERNAL_API_SECRET or "").strip()
    if not configured or configured in COMPROMISED_INTERNAL_SECRETS:
        raise RuntimeError("INTERNAL_API_SECRET is missing or uses a compromised legacy value")
    return configured


def is_valid_internal_secret(provided: str | None) -> bool:
    try:
        configured = get_required_internal_secret()
    except RuntimeError:
        return False
    candidate = (provided or "").strip()
    return bool(candidate and secrets.compare_digest(candidate, configured))


def get_required_webhook_secret() -> str:
    secret = (settings.TELEGRAM_WEBHOOK_SECRET or "").strip()
    if secret == "super-secret-telegram-webhook-token" or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", secret):
        raise RuntimeError("TELEGRAM_WEBHOOK_SECRET must be explicitly configured with a unique value")
    return secret


def require_internal_request(request: Request):
    if not is_valid_internal_secret(request.headers.get("x-internal-secret")):
        raise HTTPException(status_code=403, detail="Forbidden")


async def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    """
    Проверяет токен Cloudflare Turnstile через официальный API Cloudflare.
    Если проверка отключена в .env (CLOUDFLARE_TURNSTILE_ENABLED=False) — возвращает True.
    """
    if not settings.CLOUDFLARE_TURNSTILE_ENABLED:
        return True

    if not token:
        logger.warning("Turnstile verification failed: missing token")
        return False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            payload = {
                "secret": settings.CLOUDFLARE_TURNSTILE_SECRET_KEY,
                "response": token
            }
            if remote_ip:
                payload["remoteip"] = remote_ip

            response = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            data = response.json()
            success = data.get("success", False)
            if not success:
                logger.warning(f"Turnstile token validation failed: {data.get('error-codes')}")
            return success
    except Exception as e:
        logger.error(f"Error connecting to Turnstile API: {e}")
        # In case of network outage to Cloudflare, pass or fail depending on policy (here: reject on fail)
        return False
