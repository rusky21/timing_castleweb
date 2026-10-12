import logging
from typing import List
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("freelancer_fetcher")


class FreelancerFetcher(BaseFetcher):
    platform_name = "freelancer"
    display_name = "Freelancer.com"

    def __init__(self, client: StealthClient | None = None):
        self.client = client or StealthClient()
        self.url = "https://www.freelancer.com/api/projects/0.1/projects/active"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            params = {
                "limit": 20,
                "compact": "true",
                "sort_field": "time_updated",
                "reverse_sort": "true"
            }
            resp = await self.client.get(self.url, params=params, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Freelancer.com: HTTP {resp.status_code}")
                return orders

            data = resp.json()
            projects = data.get("result", {}).get("projects", [])

            for p in projects:
                p_id = str(p.get("id"))
                if not p_id:
                    continue

                title = p.get("title") or "Untitled Project"
                desc = p.get("preview_description") or p.get("description") or ""
                seo_url = p.get("seo_url") or p_id
                url = f"https://www.freelancer.com/projects/{seo_url}"

                curr_code = p.get("currency", {}).get("code") or "USD"
                b = p.get("budget", {}) or {}
                b_min = b.get("minimum")
                b_max = b.get("maximum")

                price_str = "Договорная"
                price_rub = None
                if b_min and b_max:
                    price_str = f"{int(b_min)} - {int(b_max)} {curr_code}"
                elif b_min:
                    price_str = f"от {int(b_min)} {curr_code}"
                elif b_max:
                    price_str = f"до {int(b_max)} {curr_code}"

                # Примерный курс в рубли для фильтрации
                if b_min or b_max:
                    approx_val = int(b_max or b_min or 0)
                    rate = 95 if curr_code in ("USD", "EUR") else (120 if curr_code == "GBP" else 1.1)
                    price_rub = int(approx_val * rate)

                # Проверка специальных требований (NDA, Sealed, Urgent)
                is_free = True
                label = "✨ Стандартный отклик (1 бесплатный Bid)"
                if p.get("nda") or p.get("sealed"):
                    is_free = False
                    label = "💎 Требует NDA / Депозит"
                elif p.get("urgent"):
                    label = "⚡ Срочный проект (Urgent)"

                order = NormalizedOrder(
                    composite_id=f"freelancer_{p_id}",
                    platform="freelancer",
                    external_id=p_id,
                    title=title.strip(),
                    description=desc.strip(),
                    url=url,
                    price_info=price_str,
                    price_rub=price_rub,
                    currency=curr_code,
                    is_free=is_free,
                    response_type_label=label,
                    category_name="Freelancer.com Global",
                    created_at=utc_now(),
                    raw_payload=p
                )
                orders.append(order)

            logger.info(f"FreelancerFetcher: успешно получено {len(orders)} проектов")
        except Exception as e:
            logger.error(f"FreelancerFetcher error: {e}", exc_info=True)

        return orders
