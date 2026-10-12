import re
import logging
from typing import List
from selectolax.lexbor import LexborHTMLParser
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("peopleperhour_fetcher")


class PeoplePerHourFetcher(BaseFetcher):
    platform_name = "peopleperhour"
    display_name = "PeoplePerHour"

    def __init__(self, client: StealthClient | None = None):
        self.client = client or StealthClient()
        self.url = "https://www.peopleperhour.com/freelance-jobs"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            headers = {"Referer": "https://www.peopleperhour.com/"}
            resp = await self.client.get(self.url, headers=headers, timeout=15, use_stealth=True)
            if resp.status_code != 200:
                logger.warning(f"PeoplePerHour: HTTP {resp.status_code}")
                return orders

            tree = LexborHTMLParser(resp.text)
            links = tree.css("a[href*='/freelance-jobs/']")

            seen_ids = set()
            for a in links:
                href = a.attributes.get("href") or ""
                # ID извлекаем из слага или хеша ссылки
                parts = href.strip("/").split("/")
                if len(parts) < 2:
                    continue
                slug = parts[-1]
                if slug in seen_ids or slug == "freelance-jobs":
                    continue
                seen_ids.add(slug)

                title = a.text(strip=True)
                if not title or len(title) < 5:
                    continue

                full_url = f"https://www.peopleperhour.com{href}" if href.startswith("/") else href

                order = NormalizedOrder(
                    composite_id=f"pph_{slug[:40]}",
                    platform="peopleperhour",
                    external_id=slug[:40],
                    title=title.strip(),
                    description="",
                    url=full_url,
                    price_info="Договорная (£/$)",
                    price_rub=None,
                    currency="GBP",
                    is_free=True,
                    response_type_label="✨ Доступно по квоте откликов",
                    category_name="PeoplePerHour UK/Global",
                    created_at=utc_now()
                )
                orders.append(order)

            logger.info(f"PeoplePerHourFetcher: получено {len(orders)} проектов")
        except Exception as e:
            logger.error(f"PeoplePerHourFetcher error: {e}")

        return orders
