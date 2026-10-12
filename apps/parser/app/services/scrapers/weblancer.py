import re
import logging
from typing import List
from selectolax.lexbor import LexborHTMLParser
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("weblancer_fetcher")


class WeblancerFetcher(BaseFetcher):
    platform_name = "weblancer"
    display_name = "Weblancer"

    def __init__(self, client: StealthClient | None = None):
        self.client = client or StealthClient()
        self.url = "https://www.weblancer.net/jobs/"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            resp = await self.client.get(self.url, timeout=15, use_stealth=True)
            if resp.status_code != 200:
                logger.warning(f"Weblancer: HTTP {resp.status_code}")
                return orders

            tree = LexborHTMLParser(resp.text)
            links = tree.css("a[href*='/jobs/']")

            seen_ids = set()
            for a in links:
                href = a.attributes.get("href") or ""
                m_id = re.search(r'/jobs/[^/]+-(\d+)/', href)
                if not m_id:
                    continue

                order_id = m_id.group(1)
                if order_id in seen_ids:
                    continue
                seen_ids.add(order_id)

                title = a.text(strip=True)
                if not title or len(title) < 4:
                    continue

                parent = a.parent
                for _ in range(3):
                    if parent and parent.parent:
                        parent = parent.parent

                cost_str = "Договорная ($)"
                price_rub = None
                if parent:
                    cost_el = parent.css_first(".amount, .price, .val")
                    if cost_el:
                        raw_cost = cost_el.text(strip=True)
                        if any(c.isdigit() for c in raw_cost):
                            cost_str = raw_cost
                            digits = "".join(c for c in raw_cost if c.isdigit())
                            if digits:
                                price_rub = int(int(digits) * 95)

                full_url = f"https://www.weblancer.net{href}" if href.startswith("/") else href

                order = NormalizedOrder(
                    composite_id=f"weblancer_{order_id}",
                    platform="weblancer",
                    external_id=order_id,
                    title=title.strip(),
                    description="",
                    url=full_url,
                    price_info=cost_str,
                    price_rub=price_rub,
                    currency="USD",
                    is_free=True,
                    response_type_label="✨ Бесплатная заявка по тарифу",
                    category_name="Weblancer",
                    created_at=utc_now()
                )
                orders.append(order)

            logger.info(f"WeblancerFetcher: получено {len(orders)} заказов")
        except Exception as e:
            logger.error(f"WeblancerFetcher error: {e}")

        return orders
