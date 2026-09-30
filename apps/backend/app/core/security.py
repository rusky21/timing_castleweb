import httpx
import logging
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


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
