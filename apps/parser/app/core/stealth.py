import os
import random
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("stealth_client")

# Проверяем доступность curl_cffi
try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    logger.warning("curl_cffi не установлен, StealthClient будет использовать aiohttp")

import aiohttp


class StealthResponse:
    def __init__(self, status_code: int, text: str, headers: Dict[str, str], raw_bytes: bytes = b""):
        self.status_code = status_code
        self.text = text
        self.headers = headers
        self.content = raw_bytes

    def json(self) -> Any:
        import json
        return json.loads(self.text)


class StealthClient:
    """
    Клиент для скрытного сбора данных с защищенных сайтов (Cloudflare, DDoS-Guard).
    Использует BoringSSL с точной эмуляцией отпечатка браузера Chrome (JA3/JA4).
    """

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }

    def __init__(self, proxy: Optional[str] = None, impersonate: str = "chrome124"):
        self.proxy = proxy or os.environ.get("SCRAPER_PROXY_URL") or None
        self.impersonate = impersonate

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 15,
        use_stealth: bool = True
    ) -> StealthResponse:
        merged_headers = {**self.DEFAULT_HEADERS, **(headers or {})}

        # Если доступен curl_cffi и требуется скрытность — отправляем запрос через BoringSSL
        if CURL_CFFI_AVAILABLE and use_stealth:
            try:
                async with CurlAsyncSession(impersonate=self.impersonate) as s:
                    kwargs = {
                        "headers": merged_headers,
                        "params": params,
                        "timeout": timeout,
                    }
                    if self.proxy:
                        kwargs["proxy"] = self.proxy

                    resp = await s.get(url, **kwargs)
                    return StealthResponse(
                        status_code=resp.status_code,
                        text=resp.text,
                        headers=dict(resp.headers),
                        raw_bytes=resp.content
                    )
            except Exception as e:
                logger.warning(f"curl_cffi запрос к {url} вызвал ошибку: {e}. Пробуем aiohttp фоллбэк.")

        # Фоллбэк на стандартный aiohttp
        async with aiohttp.ClientSession(headers=merged_headers) as session:
            async with session.get(url, params=params, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                text = await resp.text()
                raw = await resp.read()
                return StealthResponse(
                    status_code=resp.status,
                    text=text,
                    headers=dict(resp.headers),
                    raw_bytes=raw
                )

    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: int = 15,
        use_stealth: bool = True
    ) -> StealthResponse:
        merged_headers = {**self.DEFAULT_HEADERS, **(headers or {})}

        if CURL_CFFI_AVAILABLE and use_stealth:
            try:
                async with CurlAsyncSession(impersonate=self.impersonate) as s:
                    kwargs = {
                        "headers": merged_headers,
                        "json": json_data,
                        "timeout": timeout,
                    }
                    if self.proxy:
                        kwargs["proxy"] = self.proxy

                    resp = await s.post(url, **kwargs)
                    return StealthResponse(
                        status_code=resp.status_code,
                        text=resp.text,
                        headers=dict(resp.headers),
                        raw_bytes=resp.content
                    )
            except Exception as e:
                logger.warning(f"curl_cffi POST к {url} вызвал ошибку: {e}. Пробуем aiohttp фоллбэк.")

        async with aiohttp.ClientSession(headers=merged_headers) as session:
            async with session.post(url, json=json_data, proxy=self.proxy, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                text = await resp.text()
                raw = await resp.read()
                return StealthResponse(
                    status_code=resp.status,
                    text=text,
                    headers=dict(resp.headers),
                    raw_bytes=raw
                )
