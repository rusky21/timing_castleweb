import re
import json
import logging
from typing import List
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("kwork_fetcher")


class KworkFetcher(BaseFetcher):
    platform_name = "kwork"
    display_name = "Kwork"

    def __init__(self, client: StealthClient | None = None):
        self.client = client or StealthClient()
        # Категории: 11 = Разработка и IT, 15 = Дизайн
        self.url = "https://kwork.ru/projects?c=11&c=15"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            resp = await self.client.get(self.url, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Kwork: HTTP {resp.status_code}")
                return orders

            m = re.search(r'window\.stateData\s*=\s*({.*?});\s*window\.', resp.text, re.DOTALL)
            if not m:
                logger.warning("Kwork: stateData не найден в HTML")
                return orders

            state = json.loads(m.group(1))
            wants = state.get("wants", [])

            # Построение карты категорий Kwork
            cat_map = {}
            for p_id, c in state.get("categories", {}).items():
                if isinstance(c, dict):
                    p_name = c.get("name") or ""
                    cat_map[str(p_id)] = p_name
                    for sub in c.get("cats", []):
                        s_id = str(sub.get("id") or sub.get("CATID") or "")
                        s_name = sub.get("name") or ""
                        cat_map[s_id] = f"{p_name} / {s_name}" if p_name else s_name

            for w in wants:
                w_id = str(w.get("id"))
                if not w_id:
                    continue

                title = w.get("name") or w.get("title") or "Без названия"
                desc = w.get("description") or ""
                price_limit = w.get("priceLimit") or w.get("possiblePriceLimit")
                
                price_rub = None
                price_str = "Договорная"
                if price_limit:
                    try:
                        price_rub = int(float(price_limit))
                        price_str = f"{price_rub:,} ₽".replace(",", " ")
                    except (ValueError, TypeError):
                        pass

                # Статус отклика на Kwork: только доступные для всех (без закрытых фильтров заказчика)
                kworks_filters = w.get("kworks_filters") or []
                if kworks_filters:
                    # Заказ закрыт фильтрами заказчика (требуется рейтинг/отзывы, не доступен всем)
                    continue

                is_free = True
                label = "✨ Базовый отклик (коннекты)"

                cid = str(w.get("category_id") or "")
                cat_name = cat_map.get(cid) or "Разработка и IT"

                order = NormalizedOrder(
                    composite_id=f"kwork_{w_id}",
                    platform="kwork",
                    external_id=w_id,
                    title=title.strip(),
                    description=desc.strip(),
                    url=f"https://kwork.ru/projects/{w_id}",
                    price_info=price_str,
                    price_rub=price_rub,
                    currency="RUB",
                    is_free=is_free,
                    response_type_label=label,
                    category_name=cat_name,
                    created_at=utc_now(),
                    raw_payload=w
                )
                orders.append(order)

            logger.info(f"KworkFetcher: успешно спарсено {len(orders)} проектов")
        except Exception as e:
            logger.error(f"KworkFetcher error: {e}", exc_info=True)

        return orders
