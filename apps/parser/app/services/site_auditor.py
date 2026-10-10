import ipaddress
import re
import ssl
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
import httpx
try:
    from selectolax.lexbor import LexborHTMLParser as HTMLParser
except ImportError:
    from selectolax.parser import HTMLParser

from app.config import DEFAULT_TIMEOUT_CONNECT, DEFAULT_TIMEOUT_READ
from app.services.pitch_maker import PitchMaker

# Домены соцсетей и конструкторов визиток
SOCIAL_DOMAINS = {
    "vk.com", "vk.me", "m.vk.com",
    "t.me", "telegram.me",
    "taplink.cc", "taplink.ws",
    "instagram.com", "inst.me",
    "ok.ru", "m.ok.ru",
    "wa.me", "api.whatsapp.com"
}

# Черный список мусорных почт
EMAIL_BLACKLIST = {
    "wix.com", "tilda.cc", "sentry.io", "example.com", 
    "domain.com", "email.com", "placeholder.com", "mysite.ru"
}

# Регулярки для телефонов и email
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+7|8)[\s\-\(]*(\d{3})[\s\-\)]*(\d{3})[\s\-]*(\d{2})[\s\-]*(\d{2})")
COPYRIGHT_REGEX = re.compile(r"(?:©|&copy;|copyright|\(c\))\s*(?:20\d\d\s*[-—–]\s*)?(20\d\d)", re.IGNORECASE)
ALT_COPYRIGHT_REGEX = re.compile(r"(20\d\d)\s*(?:©|&copy;|copyright)", re.IGNORECASE)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

class SiteAuditor:
    """Высокоскоростной асинхронный аудитор сайтов с переиспользованием пула соединений"""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client
        self._insecure_client: Optional[httpx.AsyncClient] = None

    def _is_safe_host(self, host: str) -> bool:
        """Защита от SSRF: блокирует локальные, приватные и петлевые IP-адреса"""
        if not host:
            return False
        host_clean = host.split(":")[0].strip().lower()
        if host_clean in ("localhost", "0.0.0.0", "127.0.0.1", "::1", "metadata.google.internal"):
            return False
        try:
            ip = ipaddress.ip_address(host_clean)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass
        return True

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            timeout = httpx.Timeout(connect=DEFAULT_TIMEOUT_CONNECT, read=DEFAULT_TIMEOUT_READ, write=5.0, pool=5.0)
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                verify=True,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=40, keepalive_expiry=30.0)
            )
        return self._client

    async def _get_insecure_client(self) -> httpx.AsyncClient:
        if self._insecure_client is None or self._insecure_client.is_closed:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            timeout = httpx.Timeout(connect=DEFAULT_TIMEOUT_CONNECT, read=DEFAULT_TIMEOUT_READ, write=5.0, pool=5.0)
            self._insecure_client = httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                verify=False,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0)
            )
        return self._insecure_client

    def _safe_extract_text(self, resp: httpx.Response, max_bytes: int = 2 * 1024 * 1024) -> str:
        """Безопасное извлечение текста ответа с ограничением в 2 МБ для защиты от OOM"""
        try:
            content = resp.content[:max_bytes]
            encoding = resp.encoding or "utf-8"
            return content.decode(encoding, errors="ignore")
        except Exception:
            return ""

    async def close(self):
        if self._client and not self._client.is_closed:
            try: await self._client.aclose()
            except Exception: pass
        if self._insecure_client and not self._insecure_client.is_closed:
            try: await self._insecure_client.aclose()
            except Exception: pass

    def _is_social(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        return any(soc in netloc for soc in SOCIAL_DOMAINS)

    def _clean_phone(self, raw: str) -> Optional[str]:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 11 and digits[0] in ("7", "8"):
            return f"+7{digits[1:]}"
        elif len(digits) == 10:
            return f"+7{digits}"
        return None

    def _is_valid_email(self, email: str) -> bool:
        email = email.lower().strip()
        if any(email.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".css", ".js")):
            return False
        if ".." in email or email.startswith("wght@") or "@" not in email:
            return False
        parts = email.split("@")
        if len(parts) != 2:
            return False
        user, domain = parts
        if not user or not domain or domain in EMAIL_BLACKLIST:
            return False
        if "." not in domain:
            return False
        tld = domain.split(".")[-1]
        if not tld.isalpha() or len(tld) < 2 or len(tld) > 10:
            return False
        return 5 <= len(email) <= 50

    async def audit_url(
        self,
        url: Optional[str],
        org_name: str,
        category: str = "",
        city: str = ""
    ) -> Dict[str, Any]:
        """
        Главный метод аудита: проверяет доступность, SSL, адаптивность, аналитику, CMS, контакты.
        """
        if not url or not url.strip():
            # Сайта нет
            score, badge, pitch = PitchMaker.calculate_score_and_pitch(
                name=org_name,
                category=category,
                city=city,
                website="",
                status="NO_SITE",
                has_ssl=False,
                is_adaptive=False,
                has_analytics=False,
                detected_cms=None,
                last_updated_year=None
            )
            return {
                "status": "NO_SITE",
                "has_ssl": False,
                "is_adaptive": False,
                "has_analytics": False,
                "detected_cms": None,
                "last_updated_year": None,
                "final_url": None,
                "extra_phones": [],
                "extra_emails": [],
                "extra_socials": [],
                "status_badge": badge,
                "lead_score": score,
                "pitch": pitch
            }

        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Если исходно указана соцсеть
        if self._is_social(url):
            score, badge, pitch = PitchMaker.calculate_score_and_pitch(
                name=org_name,
                category=category,
                city=city,
                website=url,
                status="ONLY_SOCIAL",
                has_ssl=True,
                is_adaptive=True,
                has_analytics=False,
                detected_cms=None,
                last_updated_year=None
            )
            return {
                "status": "ONLY_SOCIAL",
                "has_ssl": True,
                "is_adaptive": True,
                "has_analytics": False,
                "detected_cms": None,
                "last_updated_year": None,
                "final_url": url,
                "extra_phones": [],
                "extra_emails": [],
                "extra_socials": [url],
                "status_badge": badge,
                "lead_score": score,
                "pitch": pitch
            }

        # Проверка безопасности хоста (SSRF защита)
        parsed_target = urlparse(url)
        if not self._is_safe_host(parsed_target.netloc):
            score, badge, pitch = PitchMaker.calculate_score_and_pitch(
                name=org_name, category=category, city=city, website=url,
                status="SITE_DOWN", has_ssl=False, is_adaptive=False,
                has_analytics=False, detected_cms=None, last_updated_year=None
            )
            return {
                "status": "SITE_DOWN", "has_ssl": False, "is_adaptive": False,
                "has_analytics": False, "detected_cms": None, "last_updated_year": None,
                "final_url": url, "extra_phones": [], "extra_emails": [], "extra_socials": [],
                "status_badge": badge, "lead_score": score, "pitch": pitch
            }

        client_secure = await self._get_client()
        client_insecure = await self._get_insecure_client()

        html_content = ""
        final_url = url
        has_ssl = False
        is_up = False

        # Фаза 1: строгий запрос по HTTPS (проверка валидности SSL)
        target_url = url
        if target_url.startswith("http://"):
            https_candidate = "https://" + target_url[7:]
            try:
                res = await client_secure.get(https_candidate)
                if res.status_code < 400:
                    has_ssl = True
                    target_url = str(res.url)
                    html_content = self._safe_extract_text(res)
                    final_url = str(res.url)
                    is_up = True
            except Exception:
                has_ssl = False

        if not is_up:
            try:
                res = await client_secure.get(target_url)
                if res.status_code < 400:
                    has_ssl = str(res.url).startswith("https://")
                    html_content = self._safe_extract_text(res)
                    final_url = str(res.url)
                    is_up = True
            except (ssl.SSLError, httpx.ConnectError, httpx.SecurityError):
                has_ssl = False
                try:
                    # Фаза 2: повторный запрос без верификации SSL для чтения контента
                    res = await client_insecure.get(target_url)
                    if res.status_code < 400:
                        html_content = self._safe_extract_text(res)
                        final_url = str(res.url)
                        is_up = True
                except Exception:
                    pass
            except Exception:
                pass

        # Если https не ответил, пробуем обычный http
        if not is_up and target_url.startswith("https://"):
            try:
                http_candidate = "http://" + target_url[8:]
                res = await client_insecure.get(http_candidate)
                if res.status_code < 400:
                    has_ssl = False
                    html_content = self._safe_extract_text(res)
                    final_url = str(res.url)
                    is_up = True
            except Exception:
                pass

        # Если сайт лежит или не ответил
        if not is_up or not html_content:
            score, badge, pitch = PitchMaker.calculate_score_and_pitch(
                name=org_name,
                category=category,
                city=city,
                website=url,
                status="SITE_DOWN",
                has_ssl=False,
                is_adaptive=False,
                has_analytics=False,
                detected_cms=None,
                last_updated_year=None
            )
            return {
                "status": "SITE_DOWN",
                "has_ssl": False,
                "is_adaptive": False,
                "has_analytics": False,
                "detected_cms": None,
                "last_updated_year": None,
                "final_url": final_url,
                "extra_phones": [],
                "extra_emails": [],
                "extra_socials": [],
                "status_badge": badge,
                "lead_score": score,
                "pitch": pitch
            }

        # Если после редиректов сайт перешел на соцсеть
        if self._is_social(final_url):
            score, badge, pitch = PitchMaker.calculate_score_and_pitch(
                name=org_name,
                category=category,
                city=city,
                website=final_url,
                status="ONLY_SOCIAL",
                has_ssl=True,
                is_adaptive=True,
                has_analytics=False,
                detected_cms=None,
                last_updated_year=None
            )
            return {
                "status": "ONLY_SOCIAL",
                "has_ssl": True,
                "is_adaptive": True,
                "has_analytics": False,
                "detected_cms": None,
                "last_updated_year": None,
                "final_url": final_url,
                "extra_phones": [],
                "extra_emails": [],
                "extra_socials": [final_url],
                "status_badge": badge,
                "lead_score": score,
                "pitch": pitch
            }

        # Парсим HTML через Selectolax
        parser = HTMLParser(html_content)

        # 1. Адаптивность: проверка <meta name="viewport"> с width=device-width
        is_adaptive = False
        viewport_meta = parser.css_first('meta[name="viewport"]') or parser.css_first('meta[name="Viewport"]')
        if viewport_meta:
            content_val = (viewport_meta.attributes.get("content") or "").lower()
            if "width=device-width" in content_val or "initial-scale=1" in content_val:
                is_adaptive = True

        # 2. Аналитика
        raw_text_lower = html_content.lower()
        has_analytics = any(marker in raw_text_lower for marker in [
            "mc.yandex.ru/metrika", "ym(", "yandex_metrika",
            "google-analytics.com", "gtag(", "ga(", "googletagmanager.com",
            "top-fwz1.mail.ru", "vk.com/rtrg"
        ])

        # 3. Детектор CMS
        detected_cms = None
        if "tilda-records" in raw_text_lower or "tilda.css" in raw_text_lower or "tilda.ws" in raw_text_lower:
            detected_cms = "Tilda"
        elif "wp-content" in raw_text_lower or "wp-includes" in raw_text_lower:
            detected_cms = "WordPress"
        elif "bitrix" in raw_text_lower or "/bitrix/" in raw_text_lower:
            detected_cms = "1C-Bitrix"
        elif "wix.com" in raw_text_lower or "parastorage.com" in raw_text_lower:
            detected_cms = "Wix"
        elif "insales.ru" in raw_text_lower:
            detected_cms = "InSales"
        elif "flexbe.ru" in raw_text_lower:
            detected_cms = "Flexbe"

        # 4. Копирайт / Год последнего обновления
        last_updated_year = None
        cp_match = COPYRIGHT_REGEX.search(html_content) or ALT_COPYRIGHT_REGEX.search(html_content)
        if cp_match:
            try:
                yr = int(cp_match.group(1))
                if 2000 <= yr <= 2030:
                    last_updated_year = yr
            except Exception:
                pass

        # 5. Сбор контактов (Email, телефоны, мессенджеры)
        extra_emails = set()
        extra_phones = set()
        extra_socials = set()

        # Поиск по ссылкам <a>
        for a in parser.css("a[href]"):
            href = (a.attributes.get("href") or "").strip()
            if not href:
                continue
            if href.startswith("mailto:"):
                raw_mail = href.replace("mailto:", "").split("?")[0].strip()
                if self._is_valid_email(raw_mail):
                    extra_emails.add(raw_mail)
            elif href.startswith("tel:"):
                clean = self._clean_phone(href.replace("tel:", ""))
                if clean:
                    extra_phones.add(clean)
            elif "t.me/" in href or "telegram.me/" in href:
                extra_socials.add(href)
            elif "wa.me/" in href or "whatsapp.com/" in href:
                extra_socials.add(href)
            elif "vk.com/" in href:
                extra_socials.add(href)

        # Текстовый поиск email (только если мало найдено)
        if len(extra_emails) < 3:
            for em in EMAIL_REGEX.findall(html_content):
                if self._is_valid_email(em):
                    extra_emails.add(em)

        score, badge, pitch = PitchMaker.calculate_score_and_pitch(
            name=org_name,
            category=category,
            city=city,
            website=final_url,
            status="OK",
            has_ssl=has_ssl,
            is_adaptive=is_adaptive,
            has_analytics=has_analytics,
            detected_cms=detected_cms,
            last_updated_year=last_updated_year
        )

        return {
            "status": "OK",
            "has_ssl": has_ssl,
            "is_adaptive": is_adaptive,
            "has_analytics": has_analytics,
            "detected_cms": detected_cms,
            "last_updated_year": last_updated_year,
            "final_url": final_url,
            "extra_phones": list(extra_phones)[:5],
            "extra_emails": list(extra_emails)[:5],
            "extra_socials": list(extra_socials)[:5],
            "status_badge": badge,
            "lead_score": score,
            "pitch": pitch
        }
