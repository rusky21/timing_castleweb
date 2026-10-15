import re
import logging
from typing import List
from selectolax.lexbor import LexborHTMLParser
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("freelanceru_fetcher")


class FreelanceruFetcher(BaseFetcher):
    platform_name = "freelanceru"
    display_name = "Freelance.ru"

    def __init__(self, client: StealthClient | None = None):
        self.client = client or StealthClient()
        self.url = "https://freelance.ru/task"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            resp = await self.client.get(self.url, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Freelance.ru: HTTP {resp.status_code}")
                return orders

            tree = LexborHTMLParser(resp.text)
            links = tree.css("a[href*='/task/view/']")

            seen_ids = set()

            for a in links:
                href = a.attributes.get("href") or ""
                m_id = re.search(r'/task/view/(\d+)', href)
                if not m_id:
                    continue

                order_id = m_id.group(1)
                if order_id in seen_ids:
                    continue
                seen_ids.add(order_id)

                title = a.text(strip=True)
                if not title or len(title) < 3:
                    continue

                # Находим родительский блок проекта
                parent = a.parent
                for _ in range(4):
                    if parent and parent.parent and getattr(parent.parent, "tag", "") not in ("body", "html", "[document]"):
                        parent = parent.parent

                cost_str = "Договорная"
                price_rub = None
                is_pro = False
                desc = ""

                if parent:
                    # Поиск стоимости
                    cost_el = parent.css_first(".cost, .price, .val, .budget, .amount")
                    if cost_el:
                        raw_cost = cost_el.text(strip=True)
                        if raw_cost and any(c.isdigit() for c in raw_cost):
                            cost_str = raw_cost
                            digits = "".join(c for c in raw_cost if c.isdigit())
                            if digits:
                                price_rub = int(digits)

                    # Поиск описания
                    desc_el = parent.css_first(".description, .descr, .text, p")
                    if desc_el:
                        desc = desc_el.text(strip=True)

                    # Проверка PRO-статуса
                    html_snippet = (parent.html or "").lower()
                    if "pro" in html_snippet and ("badge" in html_snippet or "label" in html_snippet or "pro-icon" in html_snippet):
                        is_pro = True

                # Строгий фильтр: только бесплатные отклики и доступные для всех (без PRO)
                if is_pro:
                    continue

                is_free = True
                label = "✨ Бесплатный отклик"

                full_url = f"https://freelance.ru/task/view/{order_id}" if not href.startswith("http") else href

                order = NormalizedOrder(
                    composite_id=f"freelanceru_{order_id}",
                    platform="freelanceru",
                    external_id=order_id,
                    title=title.strip(),
                    description=desc.strip(),
                    url=full_url,
                    price_info=cost_str,
                    price_rub=price_rub,
                    currency="RUB",
                    is_free=is_free,
                    response_type_label=label,
                    category_name="Freelance.ru",
                    created_at=utc_now()
                )
                orders.append(order)

            logger.info(f"FreelanceruFetcher: успешно собрано {len(orders)} заказов")
        except Exception as e:
            logger.error(f"FreelanceruFetcher error: {e}", exc_info=True)

        return orders
