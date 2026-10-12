import logging
from typing import List
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.services.fl.fl_fetcher import FLFetcher

logger = logging.getLogger("fl_scraper_adapter")


class FLScraperFetcher(BaseFetcher):
    platform_name = "fl"
    display_name = "FL.ru"

    def __init__(self, fetcher: FLFetcher | None = None):
        self.fetcher = fetcher or FLFetcher()

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            # Получаем все свежие проекты с FL.ru (и бесплатные, и платные)
            projects = await self.fetcher.fetch_projects(only_free=False)
            for p in projects:
                p_id = str(p.get("id"))
                if not p_id:
                    continue

                is_free = bool(p.get("is_free", True))
                label = "✨ Бесплатный отклик" if is_free else "💼 Платный отклик (пакет)"

                order = NormalizedOrder(
                    composite_id=f"fl_{p_id}",
                    platform="fl",
                    external_id=p_id,
                    title=p.get("title") or "Заказ FL.ru",
                    description=p.get("description") or "",
                    url=p.get("url") or f"https://www.fl.ru/projects/{p_id}/",
                    price_info=p.get("price_raw") or "Договорная",
                    price_rub=p.get("price_rub"),
                    currency="RUB",
                    is_free=is_free,
                    response_type_label=label,
                    category_id=p.get("category_id"),
                    category_name=p.get("category_name") or "FL.ru",
                    created_at=utc_now(),
                    raw_payload=p
                )
                orders.append(order)

            logger.info(f"FLScraperFetcher: получено {len(orders)} заказов с FL.ru")
        except Exception as e:
            logger.error(f"FLScraperFetcher error: {e}", exc_info=True)

        return orders
