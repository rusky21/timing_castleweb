import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status

class CloudflareRateLimiter:
    """
    In-memory Rate Limiter со скользящим окном запросов,
    корректно считывающий реальный IP пользователя за Cloudflare Proxy.
    """
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, List[float]] = defaultdict(list)

    def get_real_client_ip(self, request: Request) -> str:
        """
        Извлекает реальный IP клиента с приоритетом заголовков Cloudflare.
        """
        # 1. Заголовок Cloudflare Proxy
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()

        # 2. X-Forwarded-For (первый IP в цепочке)
        x_forwarded = request.headers.get("x-forwarded-for")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()

        # 3. X-Real-IP
        x_real = request.headers.get("x-real-ip")
        if x_real:
            return x_real.strip()

        # 4. Fallback к прямому адресу клиента
        return request.client.host if request.client else "127.0.0.1"

    def check(self, request: Request) -> None:
        """
        Проверяет количество попыток с данного IP за окно времени.
        При превышении выбрасывает HTTP 429.
        """
        ip = self.get_real_client_ip(request)
        now = time.time()

        # Удаляем устаревшие метки времени
        self.attempts[ip] = [ts for ts in self.attempts[ip] if now - ts < self.window_seconds]

        if len(self.attempts[ip]) >= self.max_attempts:
            retry_after = int(self.window_seconds - (now - self.attempts[ip][0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много попыток входа с вашего IP ({ip}). Повторите через {max(1, retry_after)} сек.",
                headers={"Retry-After": str(max(1, retry_after))}
            )

        self.attempts[ip].append(now)

# Лимит для эндпоинта логина: 5 попыток в 60 секунд на один IP
login_limiter = CloudflareRateLimiter(max_attempts=5, window_seconds=60)
