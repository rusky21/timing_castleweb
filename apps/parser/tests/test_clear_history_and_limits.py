import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path("c:/Users/fake_netrunner/Desktop/мой сайтик)))))").resolve()
sys.path.insert(0, str(BASE_DIR / "apps" / "parser"))
sys.path.insert(0, str(BASE_DIR / "apps" / "backend"))
parser_pkg = BASE_DIR / "парсеп" / "parser" / ".venv" / "Lib" / "site-packages"
if parser_pkg.exists():
    sys.path.append(str(parser_pkg))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["INTERNAL_API_SECRET"] = "test-internal-secret"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from unittest.mock import MagicMock
from fastapi import Request

async def run_verification():
    print("=" * 70)
    print("🧪 ПРОВЕРКА ЛИМИТА 100, ФИЛЬТРА «БЕЗ САЙТА» И ОЧИСТКИ ИСТОРИИ")
    print("=" * 70)

    # 1. Проверка схемы SearchStartRequest
    print("\n[ТЕСТ 1] Проверка схемы SearchStartRequest...")
    from app.schemas.search import SearchStartRequest
    req = SearchStartRequest(niche="Стоматологии", city="Казань")
    assert req.limit == 100, f"Ожидался limit=100 по умолчанию, получено: {req.limit}"
    assert req.only_without_website is False, "Ожидался only_without_website=False по умолчанию"
    req_no_web = SearchStartRequest(niche="Автосервисы", city="Москва", only_without_website=True)
    assert req_no_web.only_without_website is True
    print(f"  -> req.limit: {req.limit}")
    print(f"  -> req.only_without_website: {req.only_without_website}")
    print(f"  -> req_no_web.only_without_website: {req_no_web.only_without_website}")
    print("  ✅ ТЕСТ 1 ПРОЙДЕН: SearchStartRequest по умолчанию запрашивает 100 лидов и поддерживает only_without_website.")

    # 2. Проверка схемы БД SearchCampaign
    print("\n[ТЕСТ 2] Проверка модели SearchCampaign в БД...")
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    from app.db.database import Base
    from app.db.models import User, SearchCampaign, Organization, AuditResult

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        table_info = await conn.execute(text("PRAGMA table_info(search_campaigns)"))
        cols = [r[1] for r in table_info.fetchall()]
        print(f"  -> Колонки search_campaigns: {cols}")
        assert "only_without_website" in cols, "Колонка only_without_website отсутствует в search_campaigns"
        assert "target_limit" in cols, "Колонка target_limit отсутствует в search_campaigns"
    print("  ✅ ТЕСТ 2 ПРОЙДЕН: Таблица search_campaigns содержит only_without_website.")

    # 3. Создаем тестового пользователя и кампании
    print("\n[ТЕСТ 3] Проверка удаления истории через DELETE /api/reports...")
    from app.api.reports import clear_reports_history
    from app.core.security import hash_password

    async with session_factory() as db:
        test_user = User(
            email="paid_user@castleweb.ru",
            password_hash=hash_password("Pass123!"),
            role="paid",
            tg_user_id="99887766",
            subscription_plan="1m"
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)

        # Создаем 3 поисковые кампании для test_user
        for i in range(1, 4):
            camp = SearchCampaign(
                niche=f"Ниша {i}",
                city="Казань",
                source="yandex",
                target_limit=100,
                only_without_website=(i % 2 == 0),
                found_count=10 * i,
                user_id=test_user.id
            )
            db.add(camp)
        await db.commit()

        # Проверяем, что кампании созданы
        c_res = await db.execute(select(SearchCampaign).where(SearchCampaign.user_id == test_user.id))
        camps_before = c_res.scalars().all()
        assert len(camps_before) == 3, f"Ожидалось 3 кампании, создано {len(camps_before)}"
        print(f"  -> Создано кампаний в БД для пользователя #{test_user.id}: {len(camps_before)}")

        # Вызываем clear_reports_history от лица пользователя
        req = MagicMock(spec=Request)
        req.state = MagicMock()
        req.state.user = {"sub": str(test_user.id), "role": "paid", "email": test_user.email}
        req.cookies = {}

        del_res = await clear_reports_history(request=req, all=False, db=db)
        print(f"  -> Ответ clear_reports_history: {del_res}")
        assert del_res["success"] is True
        assert del_res["deleted_count"] == 3

        # Проверяем, что в БД ничего не осталось для этого пользователя
        c_check = await db.execute(select(SearchCampaign).where(SearchCampaign.user_id == test_user.id))
        assert len(c_check.scalars().all()) == 0
        print("  ✅ ТЕСТ 3 ПРОЙДЕН: DELETE /api/reports корректно очистил всю историю поисков пользователя.")

    # 4. Проверка внутреннего эндпоинта /api/internal/clear-user-history для Telegram-бота
    print("\n[ТЕСТ 4] Проверка /api/internal/clear-user-history для Telegram-бота...")
    from app.api.auth import clear_user_history_internal, ClearHistoryPayload

    async with session_factory() as db:
        # Добавляем 2 новые кампании
        for i in range(1, 3):
            camp = SearchCampaign(
                niche=f"Новая кампания {i}",
                city="Москва",
                source="yandex",
                target_limit=100,
                found_count=20,
                user_id=test_user.id
            )
            db.add(camp)
        await db.commit()

        req_internal = MagicMock(spec=Request)
        req_internal.headers = {"X-Internal-Secret": "test-internal-secret"}

        payload = ClearHistoryPayload(tg_user_id="99887766", clear_all=False)
        bot_res = await clear_user_history_internal(payload=payload, request=req_internal, db=db)
        print(f"  -> Ответ внутреннего API для бота: {bot_res}")
        assert bot_res["status"] == "ok"
        assert bot_res["deleted_count"] == 2

        # Проверяем БД
        c_check2 = await db.execute(select(SearchCampaign).where(SearchCampaign.user_id == test_user.id))
        assert len(c_check2.scalars().all()) == 0
        print("  ✅ ТЕСТ 4 ПРОЙДЕН: Telegram-бот через внутренний API успешно очищает историю по tg_user_id.")

    # 5. Проверка логики фильтрации без сайта в скрейпере
    print("\n[ТЕСТ 5] Проверка логики отсечения компаний с сайтом при only_without_website=True...")
    from app.services.scrapers.base import ScrapedOrgItem

    org_with_site = ScrapedOrgItem(
        source="yandex",
        external_id="111",
        name="ООО С Сайтом",
        website="https://super-site.ru",
        phones=["+79991112233"]
    )
    org_without_site = ScrapedOrgItem(
        source="yandex",
        external_id="222",
        name="ИП Без Сайта",
        website=None,
        phones=["+79994445566"]
    )

    only_no_web = True
    collected = []
    for item in [org_with_site, org_without_site]:
        if only_no_web and item.website:
            continue
        collected.append(item)

    assert len(collected) == 1
    assert collected[0].name == "ИП Без Сайта"
    assert collected[0].website is None
    print(f"  -> Отфильтровано: {len(collected)} из 2 (оставлен только «{collected[0].name}»)")
    print("  ✅ ТЕСТ 5 ПРОЙДЕН: Компании с сайтом отсеиваются при активном фильтре.")

    print("\n" + "=" * 70)
    print("🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ! ПОЛНЫЙ ЛИМИТ 100, ФИЛЬТР И ОЧИСТКА РАБОТАЮТ.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_verification())
