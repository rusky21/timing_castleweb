import logging
from typing import List
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("freelancehunt_fetcher")


class FreelancehuntFetcher(BaseFetcher):
    platform_name = "freelancehunt"
    display_name = "Freelancehunt"

    def __init__(self, client: StealthClient | None = None):
        self.client = client or StealthClient()
        self.url = "https://api.freelancehunt.com/v2/projects"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            resp = await self.client.get(self.url, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Freelancehunt: HTTP {resp.status_code}")
                return orders

            data = resp.json()
            projects = data.get("data", [])

            for p in projects:
                p_id = str(p.get("id"))
                if not p_id:
                    continue

                attr = p.get("attributes", {})
                title = attr.get("name") or "Без названия"
                desc = attr.get("description") or ""
                url = attr.get("url") or f"https://freelancehunt.com/project/{p_id}.html"

                b = attr.get("budget") or {}
                amount = b.get("amount")
                currency = b.get("currency") or "UAH"

                price_str = "Договорная"
                price_rub = None
                if amount:
                    try:
                        val = int(amount)
                        price_str = f"{val:,} {currency}".replace(",", " ")
                        # Переводим в рубли для фильтрации
                        if currency == "USD":
                            price_rub = int(val * 95)
                        elif currency == "EUR":
                            price_rub = int(val * 103)
                        elif currency == "UAH":
                            price_rub = int(val * 2.3)
                        elif currency == "RUB":
                            price_rub = val
                    except (ValueError, TypeError):
                        pass

                is_plus = bool(attr.get("is_plus_only", False))
                is_free = not is_plus
                label = "✨ Бесплатный отклик (для всех)" if is_free else "💼 Только с аккаунтом Плюс (Платный)"

                order = NormalizedOrder(
                    composite_id=f"freelancehunt_{p_id}",
                    platform="freelancehunt",
                    external_id=p_id,
                    title=title.strip(),
                    description=desc.strip(),
                    url=url,
                    price_info=price_str,
                    price_rub=price_rub,
                    currency=currency,
                    is_free=is_free,
                    response_type_label=label,
                    category_name="Freelancehunt",
                    created_at=utc_now(),
                    raw_payload=p
                )
                orders.append(order)

            logger.info(f"FreelancehuntFetcher: получено {len(orders)} проектов")
        except Exception as e:
            logger.error(f"FreelancehuntFetcher error: {e}", exc_info=True)

        return orders
