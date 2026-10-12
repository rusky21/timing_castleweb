import re
import logging
import xml.etree.ElementTree as ET
from typing import List
from app.services.scrapers.base import BaseFetcher, NormalizedOrder, utc_now
from app.core.stealth import StealthClient

logger = logging.getLogger("workspace_fetcher")


class WorkspaceFetcher(BaseFetcher):
    platform_name = "workspace"
    display_name = "Workspace (Тендеры)"

    def __init__(self, client: StealthClient | None = None):
        self.client = client or StealthClient()
        self.url = "https://workspace.ru/tenders/rss/"

    async def fetch_orders(self) -> List[NormalizedOrder]:
        orders: List[NormalizedOrder] = []
        try:
            resp = await self.client.get(self.url, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Workspace RSS: HTTP {resp.status_code}")
                return orders

            root = ET.fromstring(resp.content)
            items = root.findall(".//item")

            for it in items:
                link = it.findtext("link") or ""
                # ID извлекаем из конца URL, например -19019/
                m_id = re.search(r'-(\d+)/?$', link)
                if not m_id:
                    continue

                order_id = m_id.group(1)
                title = it.findtext("title") or "Тендер без названия"
                desc_html = it.findtext("description") or ""

                # Извлекаем бюджет из описания если есть
                # Формат: <b>Бюджет</b>: до 1 000 000 руб.<br/>
                price_str = "Договорная (Тендер)"
                price_rub = None

                m_budget = re.search(r'Бюджет</b>:\s*([^<]+)', desc_html, re.IGNORECASE)
                if m_budget:
                    raw_b = m_budget.group(1).strip()
                    price_str = raw_b
                    digits = "".join(c for c in raw_b if c.isdigit())
                    if digits:
                        price_rub = int(digits)

                # Очищаем HTML из описания
                clean_desc = re.sub(r'<[^>]+>', ' ', desc_html).strip()

                order = NormalizedOrder(
                    composite_id=f"workspace_{order_id}",
                    platform="workspace",
                    external_id=order_id,
                    title=title.strip(),
                    description=clean_desc,
                    url=link,
                    price_info=price_str,
                    price_rub=price_rub,
                    currency="RUB",
                    is_free=True,
                    response_type_label="🏢 Бесплатная подача (Тендер)",
                    category_name="Digital-тендеры",
                    created_at=utc_now()
                )
                orders.append(order)

            logger.info(f"WorkspaceFetcher: успешно получено {len(orders)} тендеров")
        except Exception as e:
            logger.error(f"WorkspaceFetcher error: {e}", exc_info=True)

        return orders
