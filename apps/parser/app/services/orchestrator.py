import asyncio
import random
import logging
from typing import List, Dict, Set
from datetime import datetime
from sqlalchemy import select

from app.db.database import async_session_factory
from app.db.models import FLOrder, FLOrderInteraction, utc_now
from app.services.scrapers.base import BaseFetcher, NormalizedOrder
from app.services.scrapers.fl import FLScraperFetcher
from app.services.scrapers.kwork import KworkFetcher
from app.services.scrapers.freelancer import FreelancerFetcher
from app.services.scrapers.freelancehunt import FreelancehuntFetcher
from app.services.scrapers.freelanceru import FreelanceruFetcher
from app.services.scrapers.workspace import WorkspaceFetcher
from app.services.scrapers.upwork import UpworkFetcher
from app.services.scrapers.weblancer import WeblancerFetcher
from app.services.scrapers.peopleperhour import PeoplePerHourFetcher
from app.services.scrapers.contra import ContraFetcher
from app.services.telegram.dispatcher import telegram_dispatcher
from app.services.connection_manager import ws_manager

logger = logging.getLogger("orchestrator")


class MultiPlatformOrchestrator:
    """
    Главный диспетчер комбайна сбора заказов со всех бирж.
    Опрашивает источники параллельно, сохраняет новые заказы в SQLite
    и отправляет уведомления в Telegram строго администраторам студии.
    """

    def __init__(self, interval_seconds: int = 40):
        self.interval = interval_seconds
        self.is_running = False
        self._task: asyncio.Task | None = None
        self._initialized_platforms: Set[str] = set()

        # Реестр всех активных сборщиков
        self.fetchers: List[BaseFetcher] = [
            FLScraperFetcher(),
            KworkFetcher(),
            FreelancerFetcher(),
            FreelancehuntFetcher(),
            FreelanceruFetcher(),
            WorkspaceFetcher(),
            UpworkFetcher(),
            WeblancerFetcher(),
            PeoplePerHourFetcher(),
            ContraFetcher()
        ]

    async def start(self):
        """Запуск бесконечного цикла комбайна в фоне"""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"🚀 MultiPlatformOrchestrator запущен! Подключено площадок: {len(self.fetchers)}")

    async def stop(self):
        """Остановка комбайна"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("MultiPlatformOrchestrator остановлен")

    async def _run_loop(self):
        while self.is_running:
            try:
                await self.poll_all_platforms()
            except Exception as e:
                logger.error(f"Ошибка в цикле Orchestrator: {e}", exc_info=True)

            # Человекоподобный тайминг (Gaussian Jitter)
            jitter = random.uniform(-6.0, 10.0)
            sleep_duration = max(20.0, self.interval + jitter)
            await asyncio.sleep(sleep_duration)

    async def poll_all_platforms(self):
        """Параллельный опрос всех подключенных сборщиков с изоляцией ошибок"""
        tasks = [self._poll_fetcher(f) for f in self.fetchers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for fetcher, res in zip(self.fetchers, results):
            if isinstance(res, Exception):
                logger.warning(f"Ошибка при сборе с {fetcher.display_name}: {res}")

    async def _poll_fetcher(self, fetcher: BaseFetcher):
        try:
            fresh_orders: List[NormalizedOrder] = await fetcher.fetch_orders()
            if not fresh_orders:
                return

            is_cold_start = fetcher.platform_name not in self._initialized_platforms
            saved_count = 0
            new_for_notify: List[FLOrder] = []

            async with async_session_factory() as db:
                for order in fresh_orders:
                    # Проверяем наличие по composite_id или по id
                    safe_data = order.to_fl_order_dict()
                    safe_id = safe_data["id"]

                    stmt = select(FLOrder).where(
                        (FLOrder.composite_id == order.composite_id) |
                        ((FLOrder.id == safe_id) & (FLOrder.platform == order.platform))
                    )
                    existing = (await db.execute(stmt)).scalar_one_or_none()
                    if existing:
                        continue

                    # Создаем запись в БД
                    new_db_order = FLOrder(
                        id=safe_id,
                        platform=order.platform,
                        composite_id=order.composite_id,
                        response_type_label=order.response_type_label,
                        title=order.title,
                        description=order.description,
                        price_raw=order.price_info,
                        price_rub=order.price_rub,
                        is_negotiable=safe_data["is_negotiable"],
                        category_id=order.category_id or order.platform,
                        category_name=order.category_name or fetcher.display_name,
                        url=order.url,
                        is_pro_only=not order.is_free,
                        is_urgent=False,
                        is_free=order.is_free,
                        published_at=order.published_at or order.created_at,
                        created_at=order.created_at
                    )
                    db.add(new_db_order)

                    # Создаем или привязываем статус взаимодействия
                    existing_interaction = await db.get(FLOrderInteraction, safe_id)
                    if not existing_interaction:
                        interaction = FLOrderInteraction(
                            order_id=safe_id,
                            is_favorite=False,
                            is_hidden=False,
                            is_read=False,
                            updated_at=utc_now()
                        )
                        new_db_order.interaction = interaction
                        db.add(interaction)
                    else:
                        new_db_order.interaction = existing_interaction

                    saved_count += 1
                    new_for_notify.append(new_db_order)

                if saved_count > 0:
                    await db.commit()
                    logger.info(f"[{fetcher.display_name}] Сохранено новых заказов: {saved_count}")

            # Мгновенная доставка через WebSocket (десктоп и веб)
            for db_order in new_for_notify:
                try:
                    await ws_manager.broadcast_all({
                        "type": "NEW_FL_ORDER",
                        "data": db_order.to_dict()
                    })
                except Exception as ws_err:
                    logger.debug(f"WS push error: {ws_err}")

            # Отправка в Telegram через единый диспетчер
            if new_for_notify:
                # Защита от спама при холодном старте: берем не более 3 свежих
                notify_list = new_for_notify[:3] if is_cold_start else new_for_notify
                for db_order in notify_list:
                    try:
                        # Диспетчер строго проверяет is_admin_sub!
                        await telegram_dispatcher.dispatch_fl_order(db_order)
                    except Exception as ex:
                        logger.warning(f"Ошибка отправки заказа #{db_order.id} в Telegram: {ex}")

            self._initialized_platforms.add(fetcher.platform_name)

        except Exception as e:
            logger.error(f"Сбой сбора {fetcher.display_name}: {e}", exc_info=True)


# Глобальный инстанс оркестратора
orchestrator = MultiPlatformOrchestrator()
