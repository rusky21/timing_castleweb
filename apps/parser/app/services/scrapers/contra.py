import re
import logging
from typing import List
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("contra_fetcher")


class ContraFetcher(BaseFetcher):
    platform_name = "contra"
    display_name = "Contra Global"

    def __init__(self, client: StealthClient | None = None):
        self.client = client or StealthClient()
        self.url = "https://contra.com/hire"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            resp = await self.client.get(self.url, timeout=15, use_stealth=True)
            if resp.status_code != 200:
                logger.warning(f"Contra: HTTP {resp.status_code}")
                return orders

            # Contra — современное SPA. Извлекаем данные из Next.js __NEXT_DATA__
            m = re.search(r'<script id="__NEXT_DATA__" type="application/json">({.*?})</script>', resp.text)
            if m:
                import json
                try:
                    data = json.loads(m.group(1))
                    page_props = data.get("props", {}).get("pageProps", {})
                    # Если есть список проектов
                    items = page_props.get("projects") or page_props.get("opportunities") or []
                    for it in items:
                        c_id = str(it.get("id"))
                        title = it.get("title") or "Contra Project"
                        order = NormalizedOrder(
                            composite_id=f"contra_{c_id}",
                            platform="contra",
                            external_id=c_id,
                            title=title,
                            description=it.get("description", ""),
                            url=f"https://contra.com/opportunity/{c_id}",
                            price_info=it.get("rate", "Договорная ($)"),
                            currency="USD",
                            is_free=True,
                            response_type_label="✨ Бесплатный прямой отклик",
                            category_name="Contra Global",
                            created_at=utc_now()
                        )
                        orders.append(order)
                except Exception as ex:
                    logger.debug(f"Contra NEXT_DATA parse error: {ex}")

            logger.info(f"ContraFetcher: получено {len(orders)} проектов")
        except Exception as e:
            logger.error(f"ContraFetcher error: {e}")

        return orders
