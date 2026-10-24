import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from sqlalchemy import select, delete, text

from app.config import DATA_DIR, DB_PATH, SCREENSHOTS_DIR, EXPORTS_DIR
from app.db.database import async_session_factory, engine
from app.db.models import (
    FLOrder, FLOrderInteraction, FLOrderDelivery,
    SearchCampaign, utc_now
)

logger = logging.getLogger("cleanup_service")

STATE_FILE = DATA_DIR / "cleanup_state.json"


class DatabaseCleanupService:
    """
    Автономный сервис периодической очистки базы данных и дискового пространства.
    Запускается каждые 24 часа в фоне:
    1. Удаляет нерелевантные заказы бирж старше 7 дней (строго сохраняя избранные).
    2. Очищает каскадно записи доставки и взаимодействия.
    3. Удаляет старые завершенные поисковые кампании и лиды старше 14 дней.
    4. Удаляет временные скриншоты дефектов (>7 дней) и выгрузки Excel (>3 дней).
    5. Выполняет PRAGMA wal_checkpoint(TRUNCATE) и VACUUM для освобождения места на сервере.
    """

    def __init__(
        self,
        interval_hours: int = 24,
        retention_days_orders: int = 7,
        retention_days_campaigns: int = 14,
        retention_days_screenshots: int = 7,
        retention_days_exports: int = 3
    ):
        self.interval_seconds = int(os.environ.get("CLEANUP_INTERVAL_HOURS", interval_hours)) * 3600
        self.retention_days_orders = int(os.environ.get("RETENTION_DAYS_ORDERS", retention_days_orders))
        self.retention_days_campaigns = int(os.environ.get("RETENTION_DAYS_CAMPAIGNS", retention_days_campaigns))
        self.retention_days_screenshots = int(os.environ.get("RETENTION_DAYS_SCREENSHOTS", retention_days_screenshots))
        self.retention_days_exports = int(os.environ.get("RETENTION_DAYS_EXPORTS", retention_days_exports))

        self.last_cleanup_at: Optional[datetime] = None
        self.last_stats: Dict[str, Any] = {}
        self._is_running = False
        self._task: Optional[asyncio.Task] = None

        self._load_state()

    def _load_state(self):
        """Загружает дату и статус последней очистки из JSON-файла состояния"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    dt_str = data.get("last_cleanup_at")
                    if dt_str:
                        parsed_dt = datetime.fromisoformat(dt_str)
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        self.last_cleanup_at = parsed_dt
                    self.last_stats = data.get("last_stats", {})
            except Exception as e:
                logger.warning(f"Не удалось прочитать состояние очистки: {e}")

    def _save_state(self, stats: Dict[str, Any]):
        """Сохраняет дату и статистику последней очистки"""
        try:
            data = {
                "last_cleanup_at": self.last_cleanup_at.isoformat() if self.last_cleanup_at else None,
                "last_stats": stats
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Не удалось сохранить состояние очистки: {e}")

    def _get_storage_size_bytes(self) -> int:
        """Суммарный размер файлов БД SQLite, WAL и SHM на диске"""
        total = 0
        try:
            if DB_PATH.exists():
                total += DB_PATH.stat().st_size
            wal_file = Path(f"{DB_PATH}-wal")
            if wal_file.exists():
                total += wal_file.stat().st_size
            shm_file = Path(f"{DB_PATH}-shm")
            if shm_file.exists():
                total += shm_file.stat().st_size
        except Exception:
            pass
        return total

    async def run_cleanup(self) -> Dict[str, Any]:
        """
        Полный цикл очистки БД и дискового пространства.
        """
        logger.info("🧹 [CleanupService] Запуск плановой очистки базы данных и освобождения диска...")
        start_time = utc_now()
        size_before_bytes = self._get_storage_size_bytes()
        size_before_mb = round(size_before_bytes / (1024 * 1024), 2)

        orders_deleted = 0
        campaigns_deleted = 0
        screenshots_deleted = 0
        exports_deleted = 0

        # 1. Удаление старых заказов бирж (строго сохраняя избранные)
        try:
            cutoff_orders = utc_now() - timedelta(days=self.retention_days_orders)
            async with async_session_factory() as db:
                fav_subquery = select(FLOrderInteraction.order_id).where(FLOrderInteraction.is_favorite == True)
                
                del_stmt = (
                    delete(FLOrder)
                    .where(FLOrder.created_at < cutoff_orders)
                    .where(FLOrder.id.not_in(fav_subquery))
                )
                res = await db.execute(del_stmt)
                orders_deleted = res.rowcount or 0

                # Очистка возможных сиротских записей доставки и взаимодействий
                await db.execute(
                    delete(FLOrderDelivery).where(FLOrderDelivery.order_id.not_in(select(FLOrder.id)))
                )
                await db.execute(
                    delete(FLOrderInteraction).where(FLOrderInteraction.order_id.not_in(select(FLOrder.id)))
                )

                # 2. Удаление старых завершенных поисковых кампаний
                cutoff_campaigns = utc_now() - timedelta(days=self.retention_days_campaigns)
                camp_stmt = select(SearchCampaign).where(
                    SearchCampaign.created_at < cutoff_campaigns,
                    SearchCampaign.status.in_(["COMPLETED", "STOPPED", "FAILED"])
                )
                camp_res = await db.execute(camp_stmt)
                old_campaigns = camp_res.scalars().all()
                campaigns_deleted = len(old_campaigns)
                for camp in old_campaigns:
                    await db.delete(camp)

                await db.commit()
                logger.info(
                    f"🧹 [CleanupService] Удалено устаревших заказов: {orders_deleted}, "
                    f"удалено старых поисковых кампаний: {campaigns_deleted}"
                )
        except Exception as e:
            logger.error(f"Ошибка при удалении записей из SQLite: {e}", exc_info=True)

        # 3. Удаление устаревших скриншотов на диске
        try:
            now_ts = utc_now().timestamp()
            if SCREENSHOTS_DIR.exists():
                cutoff_ts = now_ts - (self.retention_days_screenshots * 86400)
                for p in SCREENSHOTS_DIR.glob("*.*"):
                    try:
                        if p.is_file() and p.stat().st_mtime < cutoff_ts:
                            p.unlink()
                            screenshots_deleted += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Ошибка при очистке папки скриншотов: {e}")

        # 4. Удаление старых Excel выгрузок на диске
        try:
            now_ts = utc_now().timestamp()
            if EXPORTS_DIR.exists():
                cutoff_ts = now_ts - (self.retention_days_exports * 86400)
                for p in EXPORTS_DIR.glob("*.*"):
                    try:
                        if p.is_file() and p.stat().st_mtime < cutoff_ts:
                            p.unlink()
                            exports_deleted += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Ошибка при очистке папки экспорта: {e}")

        # 5. Сброс WAL и VACUUM SQLite (освобождение дискового пространства OS)
        try:
            for vacuum_attempt in range(2):
                try:
                    async with engine.connect() as conn:
                        await conn.execution_options(isolation_level="AUTOCOMMIT")
                        await conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
                        await conn.execute(text("VACUUM;"))
                        await conn.execute(text("PRAGMA optimize;"))
                    break
                except Exception as vac_err:
                    if vacuum_attempt == 0:
                        await asyncio.sleep(2.0)
                    else:
                        logger.warning(f"Предупреждение при выполнении VACUUM: {vac_err}")
        except Exception as e:
            logger.warning(f"Ошибка при VACUUM SQLite: {e}")

        size_after_bytes = self._get_storage_size_bytes()
        size_after_mb = round(size_after_bytes / (1024 * 1024), 2)
        freed_mb = round(max(0.0, size_before_mb - size_after_mb), 2)

        self.last_cleanup_at = start_time
        stats = {
            "success": True,
            "cleaned_at": start_time.isoformat(),
            "orders_deleted": orders_deleted,
            "campaigns_deleted": campaigns_deleted,
            "screenshots_deleted": screenshots_deleted,
            "exports_deleted": exports_deleted,
            "db_size_before_mb": size_before_mb,
            "db_size_after_mb": size_after_mb,
            "freed_mb": freed_mb,
            "duration_sec": round((utc_now() - start_time).total_seconds(), 2)
        }

        self.last_stats = stats
        self._save_state(stats)

        logger.info(
            f"✅ [CleanupService] Очистка успешно завершена за {stats['duration_sec']}с. "
            f"Заказы: -{orders_deleted}, Кампании: -{campaigns_deleted}, "
            f"Файлы: -{screenshots_deleted + exports_deleted}. "
            f"Размер БД: {size_before_mb} MB -> {size_after_mb} MB (освобождено: {freed_mb} MB)."
        )
        return stats

    def start(self):
        """Запуск фонового воркера очистки БД"""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"🚀 DatabaseCleanupService запущен (интервал: {self.interval_seconds // 3600} ч).")

    def stop(self):
        """Остановка фонового воркера"""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("DatabaseCleanupService остановлен.")

    async def _run_loop(self):
        """Бесконечный фоновый цикл проверки интервала 24 часа"""
        # Первоначальная проверка при старте приложения:
        # если очистка никогда не запускалась или прошло >24 часов — запускаем через 30 секунд после старта
        try:
            await asyncio.sleep(15.0)
            now = utc_now()
            should_run_initial = (
                self.last_cleanup_at is None
                or (now - self.last_cleanup_at).total_seconds() >= self.interval_seconds
            )
            if should_run_initial and self._is_running:
                logger.info("🕒 [CleanupService] Прошло более 24 часов с последней очистки. Запуск...")
                await self.run_cleanup()
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning(f"Ошибка первоначального запуска очистки: {e}")

        # Основной цикл проверки каждый час
        while self._is_running:
            try:
                await asyncio.sleep(1800.0)  # Проверка каждые 30 минут
                now = utc_now()
                if self.last_cleanup_at is None or (now - self.last_cleanup_at).total_seconds() >= self.interval_seconds:
                    logger.info("🕒 [CleanupService] Наступило время плановой 24-часовой очистки БД.")
                    await self.run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Непредвиденная ошибка в цикле CleanupService: {e}", exc_info=True)
                await asyncio.sleep(60.0)

    def get_status(self) -> Dict[str, Any]:
        """Текущий статус службы очистки, дата последней операции и размер БД"""
        curr_bytes = self._get_storage_size_bytes()
        curr_mb = round(curr_bytes / (1024 * 1024), 2)
        next_run_in_sec = 0
        if self.last_cleanup_at:
            elapsed = (utc_now() - self.last_cleanup_at).total_seconds()
            next_run_in_sec = max(0, int(self.interval_seconds - elapsed))

        return {
            "is_running": self._is_running,
            "interval_hours": self.interval_seconds // 3600,
            "last_cleanup_at": self.last_cleanup_at.isoformat() if self.last_cleanup_at else None,
            "next_cleanup_in_seconds": next_run_in_sec,
            "current_db_size_mb": curr_mb,
            "last_stats": self.last_stats
        }


cleanup_service = DatabaseCleanupService()
