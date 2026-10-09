import asyncio
import re
import urllib.parse
import json
import logging
from typing import List, Optional, Callable, Awaitable, Set
import httpx
from playwright.async_api import async_playwright, Page

from app.config import CAPTCHA_TIMEOUT_SECONDS
from app.services.scrapers.base import BaseScraper, ScrapedOrgItem

logger = logging.getLogger("twogis_scraper")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
DEFAULT_2GIS_KEYS = ["rurbbn3446", "ruedfc3902", "rubnre2444"]

class TwoGisScraper(BaseScraper):
    """
    Гибридный скрейпер 2ГИС:
    - Пробует высокоскоростной API каталог
    - При блокировке ключей / IP переключается на Playwright с обработкой капчи (/museum)
    - Извлекает организации с телефонами, сайтами и адресами
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.api_key = DEFAULT_2GIS_KEYS[0]
        self._captcha_resolved_event = asyncio.Event()

    def signal_captcha_resolved(self):
        """Вызывается через API при подтверждении пользователем прохождения капчи"""
        self._captcha_resolved_event.set()

    def _normalize_phone(self, raw: str) -> Optional[str]:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 11 and digits[0] in ("7", "8"):
            return f"+7{digits[1:]}"
        elif len(digits) == 10:
            return f"+7{digits}"
        return raw if raw else None

    async def _check_and_handle_captcha(
        self,
        page: Page,
        on_captcha: Callable[[str], Awaitable[None]],
        on_status: Callable[[str], Awaitable[None]]
    ) -> bool:
        """Проверка и ожидание решения капчи 2ГИС (/museum или g-recaptcha)"""
        is_captcha = False
        try:
            curr_url = page.url
            if "museum" in curr_url or "captcha" in curr_url:
                is_captcha = True
            else:
                el = await page.query_selector("form[action*='form'], .g-recaptcha, iframe[src*='recaptcha']")
                if el and await el.is_visible():
                    is_captcha = True
        except Exception:
            pass

        if is_captcha:
            await on_captcha("2ГИС запросил подтверждение (капча / музей). Окно открыто, пройдите капчу!")
            self._captcha_resolved_event.clear()

            wait_time = 0
            while wait_time < CAPTCHA_TIMEOUT_SECONDS:
                await asyncio.sleep(2)
                wait_time += 2

                # Проверяем, ушел ли браузер со страницы капчи
                curr_url = page.url
                if ("museum" not in curr_url and "captcha" not in curr_url) or self._captcha_resolved_event.is_set():
                    await on_status("Капча 2ГИС успешно пройдена! Продолжаем сбор...")
                    await asyncio.sleep(2)
                    return True
            return False

        return True

    async def _scrape_via_browser(
        self,
        niche: str,
        city: str,
        limit: int,
        results: List[ScrapedOrgItem],
        seen_ids: Set[str],
        on_item_scraped: Callable[[ScrapedOrgItem], Awaitable[None]],
        on_status: Callable[[str], Awaitable[None]],
        on_captcha: Callable[[str], Awaitable[None]],
        is_cancelled: Callable[[], bool],
    ):
        """Резервный сбор через браузер Playwright при недоступности API ключей"""
        await on_status(f"Запуск браузерного сбора 2ГИС: «{niche} {city}»...")

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
                ]
            )
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1366, "height": 850},
                locale="ru-RU"
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

            # Перехват сетевых JSON ответов 2ГИС
            async def handle_response(resp):
                url = resp.url
                if ("items" in url or "search" in url or "byid" in url or "firm" in url or "profile" in url) and len(results) < limit and not is_cancelled():
                    try:
                        ct = resp.headers.get("content-type", "")
                        if "json" in ct:
                            data = await resp.json()
                            items = data.get("result", {}).get("items", [])
                            if not items and "item" in data.get("result", {}):
                                single = data["result"]["item"]
                                if isinstance(single, dict):
                                    items = [single]
                            for it in items:
                                if len(results) >= limit or is_cancelled():
                                    break
                                it_id = str(it.get("id", ""))
                                if not it_id:
                                    continue
                                parsed = self._parse_api_item(it)
                                if not parsed:
                                    continue
                                if it_id not in seen_ids:
                                    seen_ids.add(it_id)
                                    results.append(parsed)
                                    asyncio.create_task(on_item_scraped(parsed))
                                else:
                                    # Если организация уже в списке, но пришел более детальный профиль (с телефонами/сайтом) — обновляем!
                                    for ex in results:
                                        if ex.external_id == it_id or (ex.card_url and it_id in ex.card_url):
                                            if not ex.phones and parsed.phones:
                                                ex.phones = parsed.phones
                                            if not ex.website and parsed.website:
                                                ex.website = parsed.website
                                            if not ex.address and parsed.address:
                                                ex.address = parsed.address
                                            break
                    except Exception:
                        pass

            page.on("response", handle_response)

            search_url = f"https://2gis.ru/search/{urllib.parse.quote(f'{niche} {city}')}"
            await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Проверяем капчу
            captcha_ok = await self._check_and_handle_captcha(page, on_captcha, on_status)
            if not captcha_ok or is_cancelled():
                return

            # Парсинг и дообогащение карточек из DOM
            no_new_counter = 0
            while len(results) < limit and not is_cancelled():
                prev_len = len(results)

                # Ищем ссылки на фирмы в левой панели
                firm_links = await page.query_selector_all("a[href*='/firm/']")
                for fl in firm_links:
                    if len(results) >= limit or is_cancelled():
                        break
                    try:
                        href = await fl.get_attribute("href") or ""
                        match = re.search(r"/firm/(\d+)", href)
                        firm_id = match.group(1) if match else None

                        # Находим уже спарсенную организацию (если она пришла из сети)
                        target_item = None
                        if firm_id:
                            for res in results:
                                if res.external_id == firm_id or (res.card_url and firm_id in res.card_url):
                                    target_item = res
                                    break

                        # Если у организации уже есть телефон И сайт — не тратим время на клик
                        if target_item and target_item.phones and target_item.website:
                            continue

                        # Кликаем по карточке, чтобы 2ГИС открыл правый сайдбар с контактами
                        try:
                            await fl.click(timeout=1500)
                            await asyncio.sleep(0.4)
                            # Проверяем кнопку "Показать контакты" / "Показать телефон"
                            show_btn = await page.query_selector("button:has-text('Показать контакты'), button:has-text('Показать телефон'), button:has-text('Контакты')")
                            if show_btn and await show_btn.is_visible():
                                await show_btn.click(timeout=800)
                                await asyncio.sleep(0.2)
                        except Exception:
                            pass

                        # Извлекаем контакты из открывшейся боковой панели
                        extracted_phones = []
                        tel_links = await page.query_selector_all("a[href^='tel:']")
                        for tl in tel_links:
                            thref = await tl.get_attribute("href") or ""
                            clean_p = self._normalize_phone(thref.replace("tel:", ""))
                            if clean_p and clean_p not in extracted_phones:
                                extracted_phones.append(clean_p)

                        # Если телефонов нет по ссылкам tel:, ищем в тексте правого сайдбара
                        if not extracted_phones:
                            sidebar_text = await page.evaluate("""() => {
                                const panels = document.querySelectorAll('div[class*=\"sidebar\"], div[class*=\"card\"], div[class*=\"profile\"]');
                                let text = '';
                                panels.forEach(p => text += ' ' + p.innerText);
                                return text;
                            }""")
                            raw_phones = re.findall(r"(?:\+7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}", sidebar_text or "")
                            for p in raw_phones:
                                cl = self._normalize_phone(p)
                                if cl and cl not in extracted_phones:
                                    extracted_phones.append(cl)

                        # Извлекаем сайт
                        extracted_website = None
                        site_links = await page.query_selector_all("a[href*='2gis.ru/away'], a[class*='contact'][href^='http'], a[target='_blank'][href^='http']")
                        for sl in site_links:
                            shref = await sl.get_attribute("href") or ""
                            if "2gis.ru/away" in shref or "to=" in shref:
                                parsed_to = urllib.parse.parse_qs(urllib.parse.urlparse(shref).query).get("to", [""])[0]
                                if parsed_to and "google" not in parsed_to and "2gis" not in parsed_to:
                                    extracted_website = parsed_to
                                    break
                            elif shref.startswith("http") and not any(ign in shref for ign in ("2gis.ru", "google.com", "yandex.ru", "vk.com/away")):
                                extracted_website = shref
                                break

                        # Извлекаем адрес из сайдбара
                        extracted_address = None
                        addr_el = await page.query_selector("a[href*='/geo/'], div[class*='address']")
                        if addr_el:
                            extracted_address = (await addr_el.inner_text() or "").strip()

                        # Обновляем существующий объект
                        if target_item:
                            if extracted_phones and not target_item.phones:
                                target_item.phones = extracted_phones
                            if extracted_website and not target_item.website:
                                target_item.website = extracted_website
                            if extracted_address and not target_item.address:
                                target_item.address = extracted_address
                            continue

                        # Иначе создаем новый объект
                        name_text = (await fl.inner_text()).strip().split("\n")[0].strip()
                        if not name_text or len(name_text) < 2:
                            continue

                        card_id = firm_id or str(hash(name_text))
                        if card_id in seen_ids:
                            continue

                        new_org = ScrapedOrgItem(
                            source="2gis",
                            external_id=card_id,
                            name=name_text,
                            category=niche,
                            address=extracted_address,
                            rating=0.0,
                            reviews_count=0,
                            phones=extracted_phones,
                            website=extracted_website,
                            card_url=f"https://2gis.ru/firm/{card_id}" if firm_id else href
                        )
                        seen_ids.add(card_id)
                        results.append(new_org)
                        await on_item_scraped(new_org)
                    except Exception as item_err:
                        logger.debug(f"Error extracting 2GIS card details: {item_err}")
                        continue

                # Скроллим список выдачи
                await page.evaluate("""() => {
                    const scrollable = document.querySelector('div[class*=\"scroll\"], div[class*=\"list\"]');
                    if (scrollable) scrollable.scrollTop += 1500;
                    else window.scrollBy(0, 800);
                }""")
                await asyncio.sleep(2.0)

                if len(results) == prev_len:
                    no_new_counter += 1
                else:
                    no_new_counter = 0

                if no_new_counter >= 5:
                    break

        except Exception as e:
            logger.warning(f"2GIS browser scrape error: {e}")
        finally:
            if context:
                try: await context.close()
                except Exception: pass
            if browser:
                try: await browser.close()
                except Exception: pass
            if playwright_obj:
                try: await playwright_obj.stop()
                except Exception: pass

    def _parse_api_item(self, item: dict) -> Optional[ScrapedOrgItem]:
        item_id = str(item.get("id", ""))
        name = item.get("name", "").strip()
        if not item_id or not name:
            return None

        # Рубрика
        rubrics = item.get("rubrics", [])
        category = rubrics[0].get("name") if rubrics and isinstance(rubrics[0], dict) else None
        if not category and "name_ex" in item and isinstance(item["name_ex"], dict):
            category = item["name_ex"].get("extension")

        # Адрес (проверяем все возможные варианты структуры 2ГИС)
        address = (
            item.get("address_name")
            or item.get("full_address_name")
            or (item.get("address") if isinstance(item.get("address"), str) else None)
            or (item.get("address", {}).get("building_name") if isinstance(item.get("address"), dict) else None)
            or (item.get("address", {}).get("name") if isinstance(item.get("address"), dict) else None)
            or item.get("address_comment")
            or item.get("caption")
            or item.get("subtitle")
        )
        if not address and "adm_div" in item and isinstance(item["adm_div"], list):
            parts = [d.get("name") for d in item["adm_div"] if isinstance(d, dict) and d.get("name")]
            if parts:
                address = ", ".join(parts)

        # Рейтинг и отзывы
        reviews = item.get("reviews", {})
        rating = 0.0
        reviews_count = 0
        if isinstance(reviews, dict):
            rating = float(reviews.get("general_rating", 0.0) or 0.0)
            reviews_count = int(reviews.get("general_review_count", 0) or 0)
        elif "rating" in item and isinstance(item["rating"], dict):
            rating = float(item["rating"].get("rating", 0.0) or 0.0)
            reviews_count = int(item["rating"].get("review_count", 0) or 0)

        # Контакты
        phones = []
        website = None
        telegram = None
        socials = []

        contact_groups = item.get("contact_groups", []) or (item.get("org", {}).get("contact_groups", []) if isinstance(item.get("org"), dict) else [])
        for cg in (contact_groups or []):
            if not isinstance(cg, dict):
                continue
            for contact in cg.get("contacts", []):
                if not isinstance(contact, dict):
                    continue
                c_type = str(contact.get("type", "")).lower()
                text_or_val = str(contact.get("url") or contact.get("text") or contact.get("value") or "").strip()
                
                if c_type in ("phone", "contacts") and not any(m in text_or_val.lower() for m in ("t.me", "vk.com", "wa.me")):
                    clean_p = self._normalize_phone(text_or_val)
                    if clean_p and clean_p not in phones:
                        phones.append(clean_p)
                elif c_type in ("website", "url", "site"):
                    if not website and not any(ign in text_or_val.lower() for ign in ("t.me", "telegram", "vk.com", "wa.me", "viber")):
                        website = text_or_val

                # Детекция Telegram
                if "t.me/" in text_or_val or "telegram.me/" in text_or_val or c_type in ("telegram", "tg"):
                    clean_tg = text_or_val
                    if not clean_tg.startswith("http"):
                        clean_tg = f"https://t.me/{clean_tg.lstrip('@')}"
                    if not telegram:
                        telegram = clean_tg
                    if clean_tg not in socials:
                        socials.append(clean_tg)
                elif any(soc in text_or_val.lower() for soc in ("vk.com", "wa.me", "whatsapp.com", "viber", "instagram")):
                    if text_or_val not in socials:
                        socials.append(text_or_val)

        # Дополнительный поиск ссылок на сайты в item
        if not website:
            for lk in (item.get("links", []) or []):
                if isinstance(lk, dict):
                    url_val = lk.get("url") or lk.get("href") or ""
                    if "t.me/" in url_val and not telegram:
                        telegram = url_val
                        socials.append(url_val)
                    elif url_val and not any(ign in url_val for ign in ("2gis.ru", "google", "vk.com", "t.me")):
                        website = url_val
                        break
        if not website and "external_content" in item and isinstance(item["external_content"], list):
            for ec in item["external_content"]:
                if isinstance(ec, dict) and ec.get("url"):
                    eurl = ec["url"]
                    if "t.me/" in eurl and not telegram:
                        telegram = eurl
                        socials.append(eurl)
                    elif not any(ign in eurl for ign in ("2gis.ru", "google", "vk.com", "t.me")):
                        website = eurl
                        break

        return ScrapedOrgItem(
            source="2gis",
            external_id=item_id,
            name=name,
            category=category,
            address=address,
            rating=rating,
            reviews_count=reviews_count,
            phones=phones,
            website=website,
            telegram=telegram,
            socials=socials,
            card_url=f"https://2gis.ru/firm/{item_id}"
        )

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
        seen_ids = set()

        search_query = f"{niche} {city}".strip()
        await on_status(f"Поиск в 2ГИС: «{search_query}»...")

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Origin": "https://2gis.ru",
            "Referer": "https://2gis.ru/",
        }

        # 1. Попытка собрать через быстрый API
        api_blocked = False
        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                params = {
                    "q": search_query,
                    "page": 1,
                    "page_size": min(limit, 50),
                    "key": self.api_key,
                    "fields": "items.point,items.adm_div,items.contact_groups,items.flags,items.schedule,items.name_ex,items.rubrics,items.reviews,items.external_content,items.org",
                    "locale": "ru_RU",
                }
                resp = await client.get("https://catalog.api.2gis.com/3.0/items", params=params)
                if resp.status_code != 200 or "apiKeyIsBlocked" in resp.text or "forbidden" in resp.text:
                    api_blocked = True
                else:
                    data = resp.json()
                    items = data.get("result", {}).get("items", [])
                    for it in items:
                        if len(results) >= limit or is_cancelled():
                            break
                        parsed = self._parse_api_item(it)
                        if parsed and parsed.external_id not in seen_ids:
                            seen_ids.add(parsed.external_id)
                            results.append(parsed)
                            await on_item_scraped(parsed)
        except Exception:
            api_blocked = True

        # 2. Если API заблокирован, переключаемся на браузерный сбор
        if api_blocked and len(results) < limit and not is_cancelled():
            await on_status("2ГИС API требует валидации, переход на браузерный сбор 2ГИС...")
            await self._scrape_via_browser(
                niche=niche,
                city=city,
                limit=limit,
                results=results,
                seen_ids=seen_ids,
                on_item_scraped=on_item_scraped,
                on_status=on_status,
                on_captcha=on_captcha,
                is_cancelled=is_cancelled
            )

        await on_status(f"2ГИС: собрано {len(results)} организаций")
        return results
