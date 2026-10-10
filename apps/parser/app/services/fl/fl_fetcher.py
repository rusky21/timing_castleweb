import os
import re
import html
import time
import random
import email.utils
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx
try:
    from selectolax.lexbor import LexborHTMLParser as HTMLParser
except ImportError:
    from selectolax.parser import HTMLParser

from app.services.fl.constants import FL_CATEGORIES, CATEGORY_BY_ID

logger = logging.getLogger("fl_fetcher")

MONTHS_RU = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "май": 5,
    "июн": 6, "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12
}

# Реалистичный пул браузерных профилей для ротации
USER_AGENTS = [
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "brand": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        "platform": '"Windows"',
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
        "brand": '"Microsoft Edge";v="128", "Chromium";v="128", "Not=A?Brand";v="24"',
        "platform": '"Windows"',
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "brand": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        "platform": '"macOS"',
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "brand": None,
        "platform": '"Windows"',
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0",
        "brand": None,
        "platform": '"macOS"',
    }
]

class FLFetcher:
    """
    Модуль извлечения заказов с биржи FL.ru:
    1. Прямой высокоскоростной HTML-скрейпинг ленты с сохранением сессионных кук DDoS-Guard
    2. Правильная адресация разделов каталога по URL-слагам FL.ru
    3. Точный парсинг реального времени публикации с карточки
    4. Надежный fallback на RSS-фид только в случае жесткой блокировки
    """

    def __init__(self):
        self._html_cooldown_until: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None
        self._client_created_at: float = 0.0

    def _get_proxy(self) -> Optional[str]:
        """Получить URL прокси из окружения если задан"""
        return os.environ.get("FL_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None

    def _get_headers(self, referer: str = "https://www.fl.ru/") -> dict:
        """Генерирует заголовки реального браузера со случайным User-Agent"""
        profile = random.choice(USER_AGENTS)
        headers = {
            "User-Agent": profile["ua"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": referer,
            "Cache-Control": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        if profile.get("brand"):
            headers["Sec-Ch-Ua"] = profile["brand"]
            headers["Sec-Ch-Ua-Mobile"] = "?0"
            headers["Sec-Ch-Ua-Platform"] = profile["platform"]
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        """Возвращает или пересоздает долгоживущий AsyncClient с пулом соединений и сессионными куками"""
        now = time.time()
        if self._client is None or self._client.is_closed or (now - self._client_created_at > 3600):
            if self._client and not self._client.is_closed:
                try:
                    await self._client.aclose()
                except Exception:
                    pass

            headers = self._get_headers()
            proxy = self._get_proxy()
            self._client = httpx.AsyncClient(
                headers=headers,
                proxy=proxy,
                timeout=httpx.Timeout(15.0, connect=10.0),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10, keepalive_expiry=60.0)
            )
            self._client_created_at = now
        return self._client

    async def close(self):
        """Закрывает сессионный HTTP клиент"""
        if self._client and not self._client.is_closed:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

    def _parse_price(self, price_str: str) -> tuple[Optional[int], bool]:
        """
        Преобразует строку цены в (price_rub, is_negotiable)
        """
        if not price_str:
            return None, True

        raw_clean = html.unescape(price_str).replace("\xa0", " ").replace("&nbsp;", " ").strip()
        raw_lower = raw_clean.lower()

        if any(neg in raw_lower for neg in ("договор", "по согласованию", "не указана", "уточняйте", "соглас")):
            return None, True

        # Проверка диапазонов цен: '10 000 - 20 000 руб'
        range_match = re.search(r"(\d[\d\s]*)\s*[-—–]\s*(\d[\d\s]*)", raw_clean)
        if range_match:
            first_num = re.sub(r"\D", "", range_match.group(1))
            if first_num:
                val = int(first_num)
                if "$" in raw_clean or "usd" in raw_lower:
                    val = val * 92
                elif "€" in raw_clean or "eur" in raw_lower:
                    val = val * 100
                return val, False

        # Извлечение единого числа
        digits_only = re.sub(r"[^\d]", "", raw_clean)
        if not digits_only:
            return None, True

        try:
            val = int(digits_only)
            if "$" in raw_clean or "usd" in raw_lower:
                val = val * 92
            elif "€" in raw_clean or "eur" in raw_lower:
                val = val * 100
            return val, False
        except ValueError:
            return None, True

    def _extract_project_id(self, url: str) -> Optional[int]:
        """Извлекает числовой ID проекта из URL: /projects/12345/ или /vakansii/12345/"""
        match = re.search(r"/(?:projects|vakansii|konkurs)/(\d+)", url)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None

    def _parse_card_published_at(self, card) -> datetime:
        """
        Извлекает точное время публикации с карточки проекта на FL.ru:
        - 'только что' / 'менее минуты назад'
        - 'минуту назад' / '5 минут назад'
        - 'час назад' / '2 часа 16 минут назад'
        - 'сегодня в 12:30' / 'сегодня, 12:30'
        - 'вчера в 18:20' / 'вчера, 18:20'
        - '9 октября, 11:13' / '8 октября 12:14'
        Если дата не указана или нестандартная — возвращает текущее время (заказ с 1 страницы ленты).
        """
        now = datetime.now(timezone.utc)
        msk_tz = timezone(timedelta(hours=3))
        now_msk = datetime.now(msk_tz)

        # 1. Поиск элемента с датой: time, классы opacity, foot, mute
        dt_el = (
            card.css_first('time') or
            card.css_first('span.text-gray-opacity-4') or
            card.css_first('span[class*="opacity"]') or
            card.css_first('div[class*="opacity"]') or
            card.css_first('span.text-muted') or
            card.css_first('.b-post__foot span')
        )
        text = dt_el.text(strip=True).lower() if dt_el else ""

        # 2. Если селектор не сработал — сканируем компактные текстовые узлы (< 60 символов)
        if not text:
            for el in card.css('span') + card.css('small') + card.css('div'):
                t = el.text(strip=True).lower()
                if 2 < len(t) < 60 and any(w in t for w in ["назад", "сегодня", "вчера", "только что", "минут", "час"]):
                    text = t
                    break

        if not text:
            return now

        try:
            # 'только что', 'менее минуты назад', 'меньше минуты'
            if any(w in text for w in ["только что", "менее минуты", "меньше минуты", "прямо сейчас", "сейчас"]):
                return now

            # Относительное время: часы и минуты
            m_hour = re.search(r'(\d+)\s+час', text)
            m_min = re.search(r'(\d+)\s+мин', text)

            hours = int(m_hour.group(1)) if m_hour else (1 if "час назад" in text else 0)
            minutes = int(m_min.group(1)) if m_min else (1 if "минуту назад" in text else 0)

            if m_hour or m_min or "час назад" in text or "минуту назад" in text:
                return now - timedelta(hours=hours, minutes=minutes)

            # 'сегодня в 14:30' или 'сегодня, 14:30'
            m_today = re.search(r'сегодня(?:[\s,]+(?:в\s*)?(\d{1,2}):(\d{2}))?', text)
            if m_today:
                if m_today.group(1) and m_today.group(2):
                    h, m = int(m_today.group(1)), int(m_today.group(2))
                    dt_msk = now_msk.replace(hour=h, minute=m, second=0, microsecond=0)
                    return dt_msk.astimezone(timezone.utc)
                else:
                    return now - timedelta(minutes=15)

            # 'вчера в 18:20' или 'вчера, 18:20'
            m_yesterday = re.search(r'вчера(?:[\s,]+(?:в\s*)?(\d{1,2}):(\d{2}))?', text)
            if m_yesterday:
                h = int(m_yesterday.group(1)) if m_yesterday.group(1) else 12
                m = int(m_yesterday.group(2)) if m_yesterday.group(2) else 0
                dt_msk = (now_msk - timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)
                return dt_msk.astimezone(timezone.utc)

            # '9 октября, 11:13' или '8 октября 12:14'
            m_date = re.search(r'(\d{1,2})\s+([а-яё]+)(?:[,\s]+(?:в\s*)?(\d{1,2}):(\d{2}))?', text)
            if m_date:
                day = int(m_date.group(1))
                mon_str = m_date.group(2)[:3]
                month = MONTHS_RU.get(mon_str)
                if month:
                    h = int(m_date.group(3)) if m_date.group(3) else 12
                    m = int(m_date.group(4)) if m_date.group(4) else 0
                    year = now_msk.year
                    if month > now_msk.month:
                        year -= 1
                    dt_msk = datetime(year, month, day, h, m, 0, tzinfo=msk_tz)
                    return dt_msk.astimezone(timezone.utc)
        except Exception as e:
            logger.warning(f"FLFetcher: ошибка парсинга даты '{text}': {e}")

        return now


    def _detect_category_id(self, cat_text: str, title: str) -> str:
        """
        Интеллектуальное определение ID категории на основе рубрики FL или текста проекта
        """
        combined = f"{cat_text} {title}".lower()

        if any(k in combined for k in ["бот", "bot", "telegram", "тг", "парсер", "parser", "скрейп", "scrap"]):
            return "2"  # Боты, парсеры и скрипты
        if any(k in combined for k in ["сайт", "web", "веб", "yii", "wordpress", "wp", "bitrix", "битрикс", "лендинг", "frontend", "backend", "fullstack", "react", "vue", "html", "css", "landing"]):
            return "5"  # Веб-разработка
        if any(k in combined for k in ["python", "c++", "c#", "java", "golang", "rust", "системн", "desktop", "десктоп", "прилож", "ядро"]):
            return "7"  # Прикладное программирование
        if any(k in combined for k in ["ios", "android", "flutter", "react native", "мобильн", "mobile", "swift", "kotlin"]):
            return "3"  # Мобильные приложения
        if any(k in combined for k in ["дизайн", "ui", "ux", "figma", "баннер", "логотип", "иллюстрац", "вектор", "dwg", "макет", "инфографик"]):
            return "37" # UI/UX Дизайн
        if any(k in combined for k in ["1с", "1c", "crm", "amocrm", "bitrix24", "битрикс24", "erp", "склад"]):
            return "8"  # 1С, CRM
        if any(k in combined for k in ["seo", "geo", "smm", "реклам", "маркетинг", "трафик", "лидогенерац", "ads", "контекст", "яндекс", "google ads"]):
            return "14" # Маркетинг и SEO
        if any(k in combined for k in ["текст", "копирайт", "стать", "перевод", "рерайт", "контент"]):
            return "1"  # Тексты

        return "5" # По умолчанию веб-разработка

    async def fetch_projects(self, category_id: Optional[str] = None, only_free: bool = True) -> List[Dict[str, Any]]:
        """
        Основной метод получения свежих проектов:
        1. Официальный RSS-фид FL.ru — единственный надежный источник, где биржа открыто
           указывает бейдж «для всех» (бесплатный отклик). В HTML для анонимных посетителей
           этот статус скрыт. RSS также отдает 60 свежих проектов и не блокируется.
        2. Прямой HTML-скрейпинг ленты (включая вакансии и конкурсы, отклики на которые также бесплатны).
        3. Объединение и дедупликация по ID проекта со свежей сортировкой по published_at.
        """
        merged: Dict[int, Dict[str, Any]] = {}

        # 1. Приоритетный опрос через RSS (проекты с меткой «для всех»)
        try:
            rss_projects = await self._fetch_via_rss(category_id, only_free=only_free)
            for p in rss_projects:
                merged[p["id"]] = p
            if rss_projects:
                logger.info(f"FL RSS: собрано {len(rss_projects)} проектов (only_free={only_free})")
        except Exception as e:
            logger.warning(f"FL RSS fetch error ({e}), опрос продолжается...")

        # 2. Опрос HTML ленты (получение вакансий и конкурсов, а также свежих карточек)
        if time.time() >= self._html_cooldown_until:
            url = "https://www.fl.ru/projects/"
            if category_id and str(category_id) != "all":
                cat_info = CATEGORY_BY_ID.get(str(category_id))
                if cat_info and cat_info.get("url_path"):
                    url = f"https://www.fl.ru/projects/category/{cat_info['url_path']}/"
                elif cat_info and cat_info.get("slug"):
                    url = f"https://www.fl.ru/projects/category/{cat_info['slug']}/"

            try:
                html_projects = await self._fetch_via_html(url, category_id, only_free=only_free)
                for p in html_projects:
                    if p["id"] not in merged:
                        merged[p["id"]] = p
                if html_projects:
                    logger.info(f"FL HTML: собрано {len(html_projects)} проектов для {url}")
            except Exception as e:
                logger.warning(f"FL HTML fetch error: {e}")

        projects = list(merged.values())
        # Сортировка по published_at убыванию (самые свежие первыми)
        projects.sort(key=lambda x: x.get("published_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return projects

    async def _fetch_via_html(self, url: str, category_id: Optional[str], only_free: bool = True) -> List[Dict[str, Any]]:
        """Прямой разбор HTML ленты FL.ru с переиспользуемой сессией и защитой от блокировки"""
        client = await self._get_client()

        resp = await client.get(url, headers={"Referer": "https://www.fl.ru/"})
        if resp.status_code in (429, 403, 503):
            self._html_cooldown_until = time.time() + 15.0
            raise Exception(f"HTTP Status {resp.status_code} (включен защитный кулдаун 15с)")

        if resp.status_code != 200:
            raise Exception(f"HTTP Status {resp.status_code}")

        html_text = resp.text
        if "Just a moment..." in html_text or "cf-browser-verification" in html_text or "challenge-running" in html_text:
            self._html_cooldown_until = time.time() + 15.0
            raise Exception("Cloudflare challenge detected (включен защитный кулдаун 15с)")

        tree = HTMLParser(html_text)
        items = []

        # Контейнеры проектов на FL.ru
        cards = tree.css('div.b-post') or tree.css('div[id^="project-item-"]') or tree.css('article')

        for card in cards:
            # Ссылка и заголовок
            title_el = (
                card.css_first('h2 a') or
                card.css_first('.b-post__title a') or
                card.css_first('a[href*="/projects/"]') or
                card.css_first('a[href*="/vakansii/"]') or
                card.css_first('a[href*="/konkurs/"]')
            )
            if not title_el:
                continue

            href = title_el.attributes.get("href") or ""
            if not href.startswith("http"):
                href = f"https://www.fl.ru{href}"

            proj_id = self._extract_project_id(href)
            if not proj_id:
                continue

            raw_title = title_el.text(strip=True)
            title = html.unescape(raw_title)

            # Цена
            price_el = (
                card.css_first('.b-post__price') or
                card.css_first('div[class*="price"]') or
                card.css_first('span[class*="price"]') or
                card.css_first('.b-post__cost')
            )
            price_raw = html.unescape(price_el.text(strip=True)) if price_el else "По договоренности"
            price_rub, is_negotiable = self._parse_price(price_raw)

            # Описание
            desc_el = (
                card.css_first('.b-post__txt.text-5') or
                card.css_first('.b-post__body') or
                card.css_first('.b-post__txt') or
                card.css_first('p')
            )
            description = html.unescape(desc_el.text(strip=True)) if desc_el else ""

            # Бейджи: PRO, Срочно, Бесплатный отклик
            card_text = (card.text() or "").lower()
            card_classes = (card.attributes.get("class") or "").lower()
            is_pro = bool(
                card.css_first('.b-post__pro') or
                card.css_first('span[class*="pro"]') or
                "pro" in card_classes or
                "только для pro" in card_text
            )
            is_urgent = bool(
                card.css_first('.b-post__bold') or
                "срочно" in card_text
            )
            is_for_all = "для всех" in card_text
            is_vacancy = "ваканси" in card_text or "/vakansii/" in href.lower()
            is_contest = "конкурс" in card_text or "/konkurs/" in href.lower()
            is_free = bool((is_for_all or is_vacancy or is_contest) and not is_pro)

            if only_free and not is_free:
                continue

            # Рубрика
            matched_cat_id = category_id or self._detect_category_id("", title)
            cat_name = CATEGORY_BY_ID.get(matched_cat_id, {}).get("name", "Разработка")
            published_at = self._parse_card_published_at(card)

            items.append({
                "id": proj_id,
                "title": title,
                "description": description[:1000],
                "price_raw": price_raw,
                "price_rub": price_rub,
                "is_negotiable": is_negotiable,
                "category_id": matched_cat_id,
                "category_name": cat_name,
                "url": href,
                "is_pro_only": is_pro,
                "is_urgent": is_urgent,
                "is_free": is_free,
                "published_at": published_at
            })

        return items

    async def _fetch_via_rss(self, category_id: Optional[str] = None, only_free: bool = True) -> List[Dict[str, Any]]:
        """Разбор официального RSS-фида FL.ru с точным определением опции «для всех» (бесплатный отклик)"""
        rss_url = "https://www.fl.ru/rss/all.xml"
        if category_id and str(category_id).isdigit():
            rss_url = f"https://www.fl.ru/rss/all.xml?category={category_id}"

        client = await self._get_client()
        resp = await client.get(rss_url, headers=self._get_headers(rss_url))
        if resp.status_code != 200:
            raise Exception(f"RSS Status {resp.status_code}")

        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            return []

        items = []
        for it in channel.findall("item"):
            raw_title = html.unescape(it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            raw_desc = html.unescape(it.findtext("description") or "").strip()
            pub_date_str = it.findtext("pubDate")
            cat_raw = html.unescape(it.findtext("category") or "").strip()

            proj_id = self._extract_project_id(link)
            if not proj_id:
                continue

            raw_title_lower = raw_title.lower()
            raw_desc_lower = raw_desc.lower()
            cat_lower = cat_raw.lower()
            link_lower = link.lower()

            # Проверка бесплатности отклика по официальным правилам FL.ru:
            # 1. Заказ имеет опцию «для всех» в заголовке или описании
            # 2. Вакансии (отклики бесплатны для всех)
            # 3. Конкурсы (отклики бесплатны для всех)
            # 4. Не требует PRO-аккаунт
            is_for_all = ("для всех" in raw_title_lower) or ("для всех" in raw_desc_lower)
            is_vacancy = ("ваканси" in cat_lower) or ("/vakansii/" in link_lower)
            is_contest = ("конкурс" in cat_lower) or ("/konkurs/" in link_lower)

            is_pro = (
                "только для pro" in raw_desc_lower or
                "только pro" in raw_desc_lower or
                "только для pro" in raw_title_lower or
                "profi" in raw_title_lower
            )

            is_free = bool((is_for_all or is_vacancy or is_contest) and not is_pro)

            # Если включен фильтр "только бесплатные заказы" — отсекаем платные
            if only_free and not is_free:
                continue

            # Извлечение цены из заголовка: (Бюджет: 35 000 ₽, для всех) или [35 000 руб.]
            price_raw = "По договоренности"
            clean_title = raw_title
            price_match = re.search(r"[\(\[](?:Бюджет|Цена)?[:\s]*(.*?)[\)\]]\s*$", raw_title, re.IGNORECASE)
            if price_match:
                inside_bracket = price_match.group(1).strip()
                clean_title = raw_title[:price_match.start()].strip()
                if re.match(r"^для всех$", inside_bracket, re.IGNORECASE):
                    price_raw = "По договоренности"
                else:
                    price_raw = re.sub(r",?\s*для всех", "", inside_bracket, flags=re.IGNORECASE).strip()
                    if not price_raw:
                        price_raw = "По договоренности"

            # Очищаем возможные хвосты "(для всех)" в названии
            clean_title = re.sub(r"[\(\[]\s*для всех\s*[\)\]]", "", clean_title, flags=re.IGNORECASE).strip()

            price_rub, is_negotiable = self._parse_price(price_raw)

            # Очистка описания от HTML-тегов
            clean_desc = re.sub(r"<[^>]+>", " ", raw_desc)
            clean_desc = re.sub(r"\s+", " ", clean_desc).strip()

            is_urgent = "срочно" in clean_title.lower() or "срочно" in clean_desc.lower()

            # Точная дата публикации
            published_at = datetime.now(timezone.utc)
            if pub_date_str:
                try:
                    parsed_dt = email.utils.parsedate_to_datetime(pub_date_str)
                    if parsed_dt:
                        published_at = parsed_dt.astimezone(timezone.utc)
                except Exception:
                    pass

            # Определение категории
            matched_cat_id = category_id or self._detect_category_id(cat_raw, clean_title)
            matched_cat_name = cat_raw or CATEGORY_BY_ID.get(matched_cat_id, {}).get("name", "Разработка")

            items.append({
                "id": proj_id,
                "title": clean_title or raw_title,
                "description": clean_desc[:1000],
                "price_raw": price_raw,
                "price_rub": price_rub,
                "is_negotiable": is_negotiable,
                "category_id": matched_cat_id,
                "category_name": matched_cat_name,
                "url": link,
                "is_pro_only": is_pro,
                "is_urgent": is_urgent,
                "is_free": is_free,
                "published_at": published_at
            })

        return items

