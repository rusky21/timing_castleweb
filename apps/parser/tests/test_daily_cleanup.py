import asyncio
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path("c:/Users/fake_netrunner/Desktop/мой сайтик)))))").resolve()
sys.path.insert(0, str(BASE_DIR / "apps" / "parser"))
parser_pkg = BASE_DIR / "парсеп" / "parser" / ".venv" / "Lib" / "site-packages"
if parser_pkg.exists():
    sys.path.append(str(parser_pkg))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.db.database import Base
from app.db.models import (
    FLOrder, FLOrderInteraction, FLOrderDelivery,
    SearchCampaign, Organization, AuditResult, utc_now
)
from app.services.cleanup_service import DatabaseCleanupService


async def run_verification():
    print("=" * 70)
    print("🧪 ПРОВЕРКА АВТОМАТИЧЕСКОЙ 24-ЧАСОВОЙ ОЧИСТКИ БД И ОСВОБОЖДЕНИЯ ДИСКА")
    print("=" * 70)

    # 1. Настройка тестовой БД в памяти
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    test_session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Переопределяем зависимости в инстансе сервиса для теста
    cleanup = DatabaseCleanupService(
        interval_hours=24,
        retention_days_orders=7,
        retention_days_campaigns=14,
        retention_days_screenshots=7,
        retention_days_exports=3
    )

    now = utc_now()
    ten_days_ago = now - timedelta(days=10)
    two_days_ago = now - timedelta(days=2)
    twenty_days_ago = now - timedelta(days=20)

    print("\n[ТЕСТ 1] Создание тестовых данных в базе...")
    async with test_session_factory() as db:
        # А. Свежие заказы (< 7 дней) — должны остаться
        for i in range(1, 4):
            o = FLOrder(
                id=100 + i,
                title=f"Свежий заказ {i}",
                url=f"https://fl.ru/projects/{100 + i}",
                created_at=two_days_ago
            )
            db.add(o)

        # Б. Старые нерелевантные заказы (10 дней назад, НЕ избранные) — ДОЛЖНЫ УДАЛИТЬСЯ
        for i in range(1, 6):
            o = FLOrder(
                id=200 + i,
                title=f"Старый заказ {i}",
                url=f"https://fl.ru/projects/{200 + i}",
                created_at=ten_days_ago
            )
            db.add(o)
            inter = FLOrderInteraction(order_id=200 + i, is_favorite=False)
            db.add(inter)
            deliv = FLOrderDelivery(order_id=200 + i, chat_id=12345, is_sent=True)
            db.add(deliv)

        # В. Старые заказы (10 дней назад), но ДОБАВЛЕННЫЕ В ИЗБРАННОЕ — ДОЛЖНЫ СОХРАНИТЬСЯ
        for i in range(1, 3):
            o = FLOrder(
                id=300 + i,
                title=f"Избранный старый заказ {i}",
                url=f"https://fl.ru/projects/{300 + i}",
                created_at=ten_days_ago
            )
            db.add(o)
            inter = FLOrderInteraction(order_id=300 + i, is_favorite=True)
            db.add(inter)

        # Г. Поисковые кампании:
        # - Свежая кампания (2 дня) -> сохраняется
        c_fresh = SearchCampaign(id=1, niche="Авто", city="Москва", status="COMPLETED", created_at=two_days_ago)
        # - Старая кампания (20 дней), но еще в процессе (RUNNING) -> сохраняется (Safety Guard!)
        c_running = SearchCampaign(id=2, niche="Юристы", city="Казань", status="RUNNING", created_at=twenty_days_ago)
        # - Старые завершенные кампании (20 дней) -> ДОЛЖНЫ УДАЛИТЬСЯ
        c_old_1 = SearchCampaign(id=3, niche="Кафе", city="СПб", status="COMPLETED", created_at=twenty_days_ago)
        c_old_2 = SearchCampaign(id=4, niche="Отели", city="Сочи", status="FAILED", created_at=twenty_days_ago)

        db.add_all([c_fresh, c_running, c_old_1, c_old_2])
        await db.commit()

    print("  -> Данные успешно созданы в SQLite.")

    # 2. Создание тестовых временных файлов
    print("\n[ТЕСТ 2] Подготовка тестовых файлов скриншотов и экспорта на диске...")
    from app.config import SCREENSHOTS_DIR, EXPORTS_DIR

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    old_screenshot = SCREENSHOTS_DIR / "test_old_proof.jpg"
    new_screenshot = SCREENSHOTS_DIR / "test_new_proof.jpg"
    old_screenshot.write_bytes(b"old_image_data")
    new_screenshot.write_bytes(b"new_image_data")

    # Искусственно состариваем дату модификации файла
    old_mtime = time.time() - (10 * 86400)  # 10 дней назад
    os.utime(old_screenshot, (old_mtime, old_mtime))

    old_export = EXPORTS_DIR / "test_old_export.xlsx"
    new_export = EXPORTS_DIR / "test_new_export.xlsx"
    old_export.write_bytes(b"old_excel_data")
    new_export.write_bytes(b"new_excel_data")
    old_export_mtime = time.time() - (5 * 86400)  # 5 дней назад
    os.utime(old_export, (old_export_mtime, old_export_mtime))

    assert old_screenshot.exists()
    assert new_screenshot.exists()
    assert old_export.exists()
    assert new_export.exists()
    print("  ✅ Тестовые файлы созданы.")

    # 3. Запуск логики очистки
    print("\n[ТЕСТ 3] Запуск цикла очистки run_cleanup...")
    # Патчим сессию и движок на тестовые
    import app.services.cleanup_service as cs_mod
    cs_mod.async_session_factory = test_session_factory
    cs_mod.engine = test_engine

    stats = await cleanup.run_cleanup()
    print(f"  -> Результат очистки: {stats}")

    assert stats["success"] is True
    assert stats["orders_deleted"] == 5, f"Ожидалось удаление 5 заказов, удалено: {stats['orders_deleted']}"
    assert stats["campaigns_deleted"] == 2, f"Ожидалось удаление 2 кампаний, удалено: {stats['campaigns_deleted']}"
    assert stats["screenshots_deleted"] >= 1, "Старый скриншот должен быть удален"
    assert stats["exports_deleted"] >= 1, "Старый экспорт должен быть удален"
    print("  ✅ ТЕСТ 3 ПРОЙДЕН: Статистика удаления полностью совпадает.")

    # 4. Проверка состояния базы после очистки
    print("\n[ТЕСТ 4] Проверка целостности и сохранности избранного в БД...")
    async with test_session_factory() as db:
        remaining_orders = (await db.execute(select(FLOrder))).scalars().all()
        rem_ids = {o.id for o in remaining_orders}
        print(f"  -> Оставшиеся заказы в БД: {rem_ids}")

        # Свежие заказы на месте
        assert 101 in rem_ids and 102 in rem_ids and 103 in rem_ids, "Свежие заказы должны остаться!"
        # Избранные старые заказы на месте!
        assert 301 in rem_ids and 302 in rem_ids, "Избранные старые заказы ДОЛЖНЫ СОХРАНЯТЬСЯ!"
        # Старые не-избранные удалены!
        for i in range(1, 6):
            assert (200 + i) not in rem_ids, f"Старый заказ {200 + i} должен быть удален!"

        # Кампании
        remaining_camps = (await db.execute(select(SearchCampaign))).scalars().all()
        camp_ids = {c.id for c in remaining_camps}
        print(f"  -> Оставшиеся кампании: {camp_ids}")
        assert 1 in camp_ids, "Свежая кампания #1 должна остаться"
        assert 2 in camp_ids, "Кампания #2 в статусе RUNNING должна остаться"
        assert 3 not in camp_ids and 4 not in camp_ids, "Старые кампании #3 и #4 должны быть удалены"

    print("  ✅ ТЕСТ 4 ПРОЙДЕН: Избранные заказы и активные кампании защищены от удаления.")

    # 5. Проверка файлов на диске
    print("\n[ТЕСТ 5] Проверка файлов на диске...")
    assert not old_screenshot.exists(), "Старый скриншот должен быть удален"
    assert new_screenshot.exists(), "Свежий скриншот должен остаться"
    assert not old_export.exists(), "Старый экспорт должен быть удален"
    assert new_export.exists(), "Свежий экспорт должен остаться"

    # Удаляем созданные свежие тестовые файлы
    new_screenshot.unlink(missing_ok=True)
    new_export.unlink(missing_ok=True)
    print("  ✅ ТЕСТ 5 ПРОЙДЕН: Файловая система очищена по таймлайнам.")

    # 6. Проверка get_status()
    print("\n[ТЕСТ 6] Проверка API статуса get_status()...")
    status_info = cleanup.get_status()
    print(f"  -> Статус сервиса: {status_info}")
    assert status_info["last_cleanup_at"] is not None
    assert "current_db_size_mb" in status_info
    assert status_info["last_stats"]["orders_deleted"] == 5
    print("  ✅ ТЕСТ 6 ПРОЙДЕН: get_status() возвращает полную телеметрию.")

    print("\n" + "=" * 70)
    print("🎉 ВСЕ ТЕСТЫ 24-ЧАСОВОЙ ОЧИСТКИ БД УСПЕШНО ПРОЙДЕНЫ!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_verification())
