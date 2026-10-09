import asyncio
import re
import random
import urllib.parse
import json
import logging
from typing import List, Optional, Callable, Awaitable, Set
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.config import CAPTCHA_TIMEOUT_SECONDS
from app.services.scrapers.base import BaseScraper, ScrapedOrgItem

logger = logging.getLogger("yandex_scraper")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

class YandexScraper(BaseScraper):
    """
    Высокоскоростной и надежный скрейпер Яндекс.Карт:
    1. Извлекает полные данные (сайты, телефоны, рейтинги) из state-view и AJAX ответов API поиска.
    2. Обходит виртуализацию DOM и антифрод (SmartCaptcha).
    3. Поддерживает динамический стриминг лидов во время скролла.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._captcha_resolved_event = asyncio.Event()

    def signal_captcha_resolved(self):
        """Вызывается через API, когда пользователь нажал 'Капча пройдена'"""
        self._captcha_resolved_event.set()

    def _normalize_phone(self, raw: str) -> Optional[str]:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 11 and digits[0] in ("7", "8"):
            return f"+7{digits[1:]}"
        elif len(digits) == 10:
            return f"+7{digits}"
        return raw if raw else None

    def _clean_website(self, raw_url: str) -> Optional[str]:
        if not raw_url:
            return None
        raw_url = raw_url.strip()
        if any(ign in raw_url for ign in ("yandex.ru/maps", "javascript:")):
            return None
        try:
            parsed = urllib.parse.urlparse(raw_url)
            # Удаляем мусорные рекламные UTM и трекинг-метки
            tracking_params = {"yclid", "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "_openstat", "fbclid"}
            qs = urllib.parse.parse_qs(parsed.query)
            clean_qs = {k: v for k, v in qs.items() if k not in tracking_params}
            new_query = urllib.parse.urlencode(clean_qs, doseq=True)
            clean_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, ""))
            return clean_url
        except Exception:
            return raw_url

    def _parse_business_item(self, raw: dict) -> Optional[ScrapedOrgItem]:
        # Проверяем, что это организация, а не подборка/баннер
        item_type = raw.get("type")
        if item_type and item_type not in ("business", "topObject"):
            return None

        external_id = str(raw.get("id") or raw.get("analyticsId") or "")
        if not external_id:
            return None

        name = (raw.get("title") or raw.get("shortTitle") or "").strip()
        if not name or len(name) < 2:
            return None

        # Адрес
        address = raw.get("fullAddress") or raw.get("address") or raw.get("additionalAddress")

        # Рубрика / Категория
        category = None
        cats = raw.get("categories") or []
        if cats and isinstance(cats, list) and len(cats) > 0:
            first_cat = cats[0]
            category = first_cat.get("name") if isinstance(first_cat, dict) else str(first_cat)

        # Рейтинг и количество отзывов
        rating_data = raw.get("ratingData") or {}
        rating = float(rating_data.get("ratingValue") or rating_data.get("rating") or 0.0)
        reviews_count = int(rating_data.get("reviewCount") or rating_data.get("reviewsCount") or 0)

        # Сайт организации, Telegram и соцсети
        website = None
        telegram = None
        socials = []

        all_candidate_urls = []
        for u in (raw.get("urls") or []):
            if isinstance(u, str):
                all_candidate_urls.append(u)
            elif isinstance(u, dict) and u.get("value"):
                all_candidate_urls.append(u["value"])

        for ab in (raw.get("actionButtons") or []):
            if isinstance(ab, dict):
                v = ab.get("value") or ab.get("url") or ""
                if v:
                    all_candidate_urls.append(v)

        for sl in (raw.get("socialLinks") or raw.get("links") or []):
            if isinstance(sl, str):
                all_candidate_urls.append(sl)
            elif isinstance(sl, dict) and (sl.get("href") or sl.get("url")):
                all_candidate_urls.append(sl.get("href") or sl.get("url"))

        for cu in all_candidate_urls:
            cu_str = str(cu).strip()
            if not cu_str:
                continue
            if "t.me/" in cu_str or "telegram.me/" in cu_str:
                clean_tg = cu_str if cu_str.startswith("http") else f"https://{cu_str}"
                if not telegram:
                    telegram = clean_tg
                if clean_tg not in socials:
                    socials.append(clean_tg)
            elif any(s in cu_str.lower() for s in ("vk.com", "wa.me", "whatsapp.com", "viber")):
                if cu_str not in socials:
                    socials.append(cu_str)
            elif not website and not any(ign in cu_str.lower() for ign in ("yandex", "google", "vk.com", "t.me")):
                cleaned = self._clean_website(cu_str)
                if cleaned:
                    website = cleaned

        # Телефоны
        phones = []
        for p in raw.get("phones") or []:
            p_val = p.get("value") or p.get("number") or ""
            cl = self._normalize_phone(p_val)
            if cl and cl not in phones:
                phones.append(cl)

        # Ссылка на карточку в Яндекс.Картах
        card_url = f"https://yandex.ru/maps/org/{external_id}/"
        seoname = raw.get("seoname")
        if seoname:
            card_url = f"https://yandex.ru/maps/org/{seoname}/{external_id}/"

        return ScrapedOrgItem(
            source="yandex",
            external_id=external_id,
            name=name,
            category=category,
            address=address,
            rating=rating,
            reviews_count=reviews_count,
            phones=phones,
            website=website,
            telegram=telegram,
            socials=socials,
            card_url=card_url
        )

    async def _check_and_handle_captcha(
        self,
        page: Page,
        on_captcha: Callable[[str], Awaitable[None]],
        on_status: Callable[[str], Awaitable[None]]
    ):
        """Детектор капчи Яндекс (SmartCaptcha / Робот)"""
        captcha_selectors = [
            ".SmartCaptcha",
            "iframe[src*='captcha']",
            "form[action*='captcha']",
            ".checkbox__box",
            "#captcha-container"
        ]

        is_captcha = False
        for sel in captcha_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    is_captcha = True
                    break
            except Exception:
                pass

        if is_captcha:
            await on_captcha("Яндекс запросил проверку на робота (SmartCaptcha). Окно открыто, пройдите капчу!")
            self._captcha_resolved_event.clear()

            wait_time = 0
            while wait_time < CAPTCHA_TIMEOUT_SECONDS:
                await asyncio.sleep(2)
                wait_time += 2

                still_captcha = False
                for sel in captcha_selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible():
                            still_captcha = True
                            break
                    except Exception:
                        pass

                if not still_captcha or self._captcha_resolved_event.is_set():
                    await on_status("Капча успешно пройдена! Продолжаем сбор...")
                    await asyncio.sleep(2)
                    break

    async def scrape(
        self,
        niche: str,
        city: str,
        limit: int,
        on_item_scraped: Callable[[ScrapedOrgItem], Awaitable[None]],
        on_status: Callable[[str], Awaitable[None]],
        on_captcha: Callable[[str], Awaitable[None]],
        is_cancelled: Callable[[], bool],
    ) -> List[ScrapedOrgItem]:
        results: List[ScrapedOrgItem] = []
        seen_ids: Set[str] = set()

        search_query = f"{niche} {city}".strip()
        encoded_query = urllib.parse.quote(search_query)
        start_url = f"https://yandex.ru/maps/?text={encoded_query}"

        await on_status(f"Запуск браузера и открытие Яндекс.Карт: «{search_query}»...")

        playwright_obj = None
        browser = None
        context = None

        try:
            playwright_obj = await async_playwright().start()

            browser = await playwright_obj.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                ]
            )

            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1366, "height": 850},
                locale="ru-RU",
            )

            page = await context.new_page()
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = { runtime: {} };
            """)

            # 1. Перехватчик ответов AJAX поиска (подгрузка при скролле)
            async def handle_response(resp):
                if "maps/api/search" in resp.url and len(results) < limit and not is_cancelled():
                    try:
                        data = await resp.json()
                        def walk_and_extract(obj):
                            if isinstance(obj, dict):
                                if "items" in obj and isinstance(obj["items"], list):
                                    for raw_it in obj["items"]:
                                        if len(results) >= limit or is_cancelled():
                                            break
                                        item = self._parse_business_item(raw_it)
                                        if item and item.external_id not in seen_ids:
                                            seen_ids.add(item.external_id)
                                            results.append(item)
                                            asyncio.create_task(on_item_scraped(item))
                                for v in obj.values():
                                    walk_and_extract(v)
                        walk_and_extract(data)
                    except Exception:
                        pass

            page.on("response", handle_response)

            # Открываем поиск
            await page.goto(start_url, timeout=35000, wait_until="domcontentloaded")
            await asyncio.sleep(2.5)

            # Проверяем капчу на старте
            await self._check_and_handle_captcha(page, on_captcha, on_status)

            if is_cancelled():
                return results

            # 2. Извлечение первичных 25 элементов из скрипта начального состояния
            script_el = await page.query_selector("script.state-view, script[class*='state-view']")
            if script_el:
                try:
                    txt = await script_el.inner_text()
                    data = json.loads(txt)
                    for s in data.get("stack", []):
                        for raw_it in s.get("results", {}).get("items", []):
                            if len(results) >= limit or is_cancelled():
                                break
                            item = self._parse_business_item(raw_it)
                            if item and item.external_id not in seen_ids:
                                seen_ids.add(item.external_id)
                                results.append(item)
                                await on_item_scraped(item)
                except Exception as e:
                    logger.warning(f"Error reading initial state-view: {e}")

            # 3. Цикл плавного скроллинга выдачи
            no_new_cards_counter = 0
            max_stuck_attempts = 8

            while len(results) < limit and not is_cancelled():
                # Проверяем капчу во время работы
                await self._check_and_handle_captcha(page, on_captcha, on_status)

                prev_count = len(results)

                # Скроллим контейнер вниз для подгрузки следующей порции организаций
                try:
                    scroll_script = """
                        () => {
                            const scrollable = document.querySelector('.scroll__container') || 
                                               document.querySelector('div[class*="search-list-view"]') ||
                                               document.querySelector('div[role="region"]');
                            if (scrollable) {
                                scrollable.scrollTop += 1800;
                                return true;
                            }
                            window.scrollBy(0, 1000);
                            return false;
                        }
                    """
                    await page.evaluate(scroll_script)
                    pause = random.uniform(1.8, 2.8)
                    await asyncio.sleep(pause)
                except Exception:
                    break

                # Если количество не изменилось, увеличиваем счетчик отсутствия новых карточек
                if len(results) == prev_count:
                    no_new_cards_counter += 1
                else:
                    no_new_cards_counter = 0

                # Детектор конца выдачи
                if no_new_cards_counter >= max_stuck_attempts:
                    await on_status("Достигнут конец выдачи Яндекс.Карт.")
                    break

        except Exception as e:
            logger.exception(f"Error during Yandex Maps scrape: {e}")
            await on_status(f"Ошибка во время парсинга Яндекс.Карт: {e}")
        finally:
            # Гарантированное закрытие контекста и браузера
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright_obj:
                try:
                    await playwright_obj.stop()
                except Exception:
                    pass

        await on_status(f"Яндекс.Карты: собрано {len(results)} организаций")
        return results
