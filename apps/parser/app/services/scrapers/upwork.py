import os
import re
import logging
import xml.etree.ElementTree as ET
from typing import List
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("upwork_fetcher")


class UpworkFetcher(BaseFetcher):
    platform_name = "upwork"
    display_name = "Upwork Global"

    def __init__(self, client: StealthClient | None = None):
        # Для Upwork приоритетно берем специальный резидентский прокси из UPWORK_PROXY_URL
        upwork_proxy = os.environ.get("UPWORK_PROXY_URL") or os.environ.get("SCRAPER_PROXY_URL") or None
        self.client = client or StealthClient(proxy=upwork_proxy)
        # Поисковый RSS-поток по популярным IT/Web категориям
        self.url = "https://www.upwork.com/ab/feed/jobs/rss?q=web+development&sort=recency"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            resp = await self.client.get(self.url, timeout=15, use_stealth=True)
            if resp.status_code == 403:
                logger.warning("Upwork: получен HTTP 403 (требуется резидентский прокси в UPWORK_PROXY_URL в .env)")
                return orders

            if resp.status_code != 200:
                logger.warning(f"Upwork: HTTP {resp.status_code}")
                return orders

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")

            for it in items:
                link = it.findtext("link") or ""
                guid = it.findtext("guid") or link
                # ID извлекаем из guid или url (например ~01abc...)
                m_id = re.search(r'(~[0-9a-zA-Z]+)', guid)
                order_id = m_id.group(1) if m_id else guid.split("/")[-1]
                if not order_id:
                    continue

                title = it.findtext("title") or "Upwork Project"
                desc_raw = it.findtext("description") or ""

                # Извлекаем бюджет:
                # <b>Budget</b>: $500 или <b>Hourly Range</b>: $30.00-$50.00
                price_str = "Договорная ($)"
                price_rub = None

                m_budget = re.search(r'Budget:\s*\$([0-9,]+)', desc_raw, re.IGNORECASE)
                m_hourly = re.search(r'Hourly Range:\s*(\$[0-9.-]+)', desc_raw, re.IGNORECASE)

                if m_budget:
                    b_val = m_budget.group(1).replace(",", "")
                    price_str = f"${b_val}"
                    try:
                        price_rub = int(int(b_val) * 95)
                    except ValueError:
                        pass
                elif m_hourly:
                    price_str = f"{m_hourly.group(1)} / hr"

                # Очищаем HTML
                clean_desc = re.sub(r'<[^>]+>', ' ', desc_raw).strip()

                order = NormalizedOrder(
                    composite_id=f"upwork_{order_id}",
                    platform="upwork",
                    external_id=order_id,
                    title=title.strip(),
                    description=clean_desc,
                    url=link,
                    price_info=price_str,
                    price_rub=price_rub,
                    currency="USD",
                    is_free=False,  # На Upwork все отклики требуют Connects
                    response_type_label="💎 Требуется Connects (4–16)",
                    category_name="Upwork International",
                    created_at=utc_now()
                )
                orders.append(order)

            logger.info(f"UpworkFetcher: успешно получено {len(orders)} заказов")
        except Exception as e:
            logger.error(f"UpworkFetcher error: {e}")

        return orders
