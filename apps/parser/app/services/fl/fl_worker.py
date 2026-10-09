import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import List, Set, Optional
from sqlalchemy import select, insert

from app.db.database import async_session_factory
from app.db.models import FLOrder, FLCategorySync, FLOrderInteraction, TelegramUserSettings, utc_now
from app.services.fl.fl_fetcher import FLFetcher
from app.services.fl.constants import CATEGORY_BY_ID, FL_CATEGORIES
from app.services.connection_manager import ws_manager

logger = logging.getLogger("fl_worker")

class FLWorker:
    """
    Фоновый воркер опроса биржи FL.ru:
    - Скоростной безопасный опрос ленты каждые 15-20 сек (без риска бана IP)
    - Главная лента FL.ru (содержит 100% свежих заказов) + Round-Robin по рубрикам
    - Защита от спама старыми заказами при первом старте категории (per-category sync)
    - Дедупликация через SQLite
    - Мгновенный пуш в десктоп/веб через WebSocket + Live Ticks
    - Передача новых релевантных заказов в Telegram-диспетчер
    """

    def __init__(self, poll_interval_min: float = 15.0, poll_interval_max: float = 20.0):
        self.poll_interval_min = poll_interval_min
        self.poll_interval_max = poll_interval_max
        self._task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self.fetcher = FLFetcher()
        self.last_poll_at: Optional[datetime] = None
        self.next_poll_in: float = 18.0
        self._category_index: int = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("FLWorker запущен в live-режиме (15-20 сек).")

    def stop(self):
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("FLWorker остановлен.")

    async def _get_active_categories(self) -> List[str]:
        """Получает список всех категорий, на которые подписаны пользователи или десктоп"""
        category_ids: Set[str] = set()

        # Категории по умолчанию для десктопа
        default_cats = {"2", "5", "7"}
        category_ids.update(default_cats)

        # Категории из настроек пользователей Telegram
        try:
            async with async_session_factory() as db:
                res = await db.execute(
                    select(TelegramUserSettings.fl_categories).where(TelegramUserSettings.fl_enabled == True)
                )
                for (cats,) in res.all():
                    if isinstance(cats, list):
                        for c in cats:
                            if str(c).strip():
                                category_ids.add(str(c).strip())
        except Exception as e:
            logger.error(f"Ошибка получения категорий из настроек: {e}")

        return list(category_ids)

    async def _run_loop(self):
        logger.info(f"FLWorker: запущен live-цикл с интервалом {self.poll_interval_min}-{self.poll_interval_max} сек.")
        while self._is_running:
            try:
                # Оповещаем WebSocket клиентов о начале проверки
                await ws_manager.broadcast_all({
                    "type": "FL_POLL_TICK",
                    "data": {
                        "status": "polling",
                        "next_poll_in": 0,
                        "last_poll_at": self.last_poll_at.isoformat() if self.last_poll_at else None,
                    }
                })

                total_new = await self.poll_cycle()
                self.last_poll_at = utc_now()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"FLWorker непредвиденная ошибка в цикле: {e}", exc_info=True)

            # Случайный джиттер 15-20 сек для имитации естественного поведения человека
            sleep_time = random.uniform(self.poll_interval_min, self.poll_interval_max)
            self.next_poll_in = sleep_time

            # Оповещаем WebSocket клиентов о времени до следующего опроса
            try:
                await ws_manager.broadcast_all({
                    "type": "FL_POLL_TICK",
                    "data": {
                        "status": "idle",
                        "next_poll_in": round(sleep_time, 1),
                        "last_poll_at": self.last_poll_at.isoformat() if self.last_poll_at else None,
                    }
                })
            except Exception:
                pass

            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break

    async def poll_cycle(self, force: bool = False) -> int:
        """
        Один безопасный шаг опроса FL.ru:
        1. Всегда опрашиваем общую ленту /projects/ (содержит ВСЕ свежие заказы сайта)
        2. Дополнительно опрашиваем 1 конкретную категорию по очереди (round-robin)
        Это дает максимум 2 запроса за цикл (4-6 запросов в минуту) — IP НИКОГДА не заблокируют!
        """
        categories = await self._get_active_categories()
        targets = [None] # Главная лента всегда первая

        if categories:
            chosen_cat = categories[self._category_index % len(categories)]
            self._category_index += 1
            targets.append(chosen_cat)

        from app.services.telegram.dispatcher import tg_dispatcher

        total_saved = 0
        for i, cat_id in enumerate(targets):
            if not self._is_running and not force:
                break

            cat_name = CATEGORY_BY_ID.get(cat_id, {}).get("name", "Все категории" if not cat_id else f"Категория {cat_id}")
            sync_key = str(cat_id or "all")

            # 1. Проверяем, опрашивалась ли эта категория ранее
            is_first_sync = False
            async with async_session_factory() as db:
                sync_record = await db.get(FLCategorySync, sync_key)
                if not sync_record:
                    is_first_sync = True
                    db.add(FLCategorySync(
                        category_id=sync_key,
                        category_name=cat_name,
                        synced_at=utc_now()
                    ))
                    await db.commit()

            # 2. Скачиваем проекты
            projects = await self.fetcher.fetch_projects(category_id=cat_id)
            if not projects:
                continue

            # 3. Сохранение и дедупликация в БД
            new_orders_saved = []
            async with async_session_factory() as db:
                for proj in projects:
                    proj_id = proj["id"]
                    existing = await db.get(FLOrder, proj_id)
                    if existing:
                        continue

                    order = FLOrder(
                        id=proj_id,
                        title=proj["title"],
                        description=proj["description"],
                        price_raw=proj["price_raw"],
                        price_rub=proj["price_rub"],
                        is_negotiable=proj["is_negotiable"],
                        category_id=str(proj.get("category_id") or cat_id or "all"),
                        category_name=proj.get("category_name") or cat_name,
                        url=proj["url"],
                        is_pro_only=proj["is_pro_only"],
                        is_urgent=proj["is_urgent"],
                        published_at=proj["published_at"],
                        created_at=utc_now()
                    )
                    db.add(order)
                    await db.flush()

                    interaction = FLOrderInteraction(
                        order_id=order.id,
                        is_favorite=False,
                        is_hidden=False,
                        is_read=False,
                        updated_at=utc_now()
                    )
                    order.interaction = interaction
                    db.add(interaction)
                    new_orders_saved.append(order)

                await db.commit()

            total_saved += len(new_orders_saved)

            # 4. Логика первого запуска vs Новые заказы
            if is_first_sync:
                logger.info(
                    f"FLWorker: [Первый запуск] Для «{cat_name}» сохранено {len(new_orders_saved)} исторических заказов без отправки в Telegram."
                )
            else:
                for order in new_orders_saved:
                    # А. Мгновенно отправляем в десктоп/веб через WebSocket
                    order_dict = order.to_dict()
                    await ws_manager.broadcast_all({
                        "type": "NEW_FL_ORDER",
                        "data": order_dict
                    })

                    # Б. Отправляем в Telegram подписчикам с фильтрацией
                    await tg_dispatcher.dispatch_fl_order(order)

            # Пауза 1.2 сек между запросами к разным категориям если их 2
            if i < len(targets) - 1:
                await asyncio.sleep(1.2)

        return total_saved

fl_worker = FLWorker()

