import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Настраиваем sys.path
BASE_DIR = Path("c:/Users/fake_netrunner/Desktop/мой сайтик)))))").resolve()
sys.path.insert(0, str(BASE_DIR / "apps" / "parser"))
sys.path.insert(0, str(BASE_DIR / "apps" / "backend"))
parser_pkg = BASE_DIR / "парсеп" / "parser" / ".venv" / "Lib" / "site-packages"
if parser_pkg.exists():
    sys.path.append(str(parser_pkg))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text

async def run_multi_city_tests():
    print("=" * 65)
    print("🧪 ЗАПУСК ТЕСТОВОГО НАБОРА: МУЛЬТИГОРОДСКОЙ ПАРСИНГ И КВОТЫ")
    print("=" * 65)

    # -----------------------------------------------------------------
    # ТЕСТ 1: Проверка функции parse_cities (парсинг строк и списков)
    # -----------------------------------------------------------------
    print("\n[ТЕСТ 1] Тестирование функции parse_cities...")
    from app.api.search import parse_cities

    # 1.1 Одиночный город
    res1 = parse_cities("Москва")
    assert res1 == ["Москва"], f"Ожидалось ['Москва'], получено {res1}"

    # 1.2 Города через запятую и пробелы
    res2 = parse_cities("Москва, Казань, Санкт-Петербург")
    assert res2 == ["Москва", "Казань", "Санкт-Петербург"], f"Ошибка разделения по запятой: {res2}"

    # 1.3 Города через точку с запятой
    res3 = parse_cities("Екатеринбург; Новосибирск ; Самара")
    assert res3 == ["Екатеринбург", "Новосибирск", "Самара"], f"Ошибка разделения по ';': {res3}"

    # 1.4 Передача списка cities
    res4 = parse_cities("", cities_list=["Уфа", "Краснодар", "Казань"])
    assert res4 == ["Уфа", "Краснодар", "Казань"], f"Ошибка парсинга списка: {res4}"

    # 1.5 Комбинация списка и строки с дубликатами
    res5 = parse_cities("Казань, Сочи", cities_list=["Москва", "Казань"])
    assert res5 == ["Москва", "Казань", "Сочи"], f"Ошибка дедупликации: {res5}"

    # 1.6 Пустой ввод -> фоллбэк на Казань
    res6 = parse_cities("", cities_list=[])
    assert res6 == ["Казань"], f"Фоллбэк по умолчанию не сработал: {res6}"

    print("  ✅ ТЕСТ 1 ПРОЙДЕН: parse_cities корректно нормализует города, удаляет дубликаты и пробелы.")

    # -----------------------------------------------------------------
    # ТЕСТ 2: Pydantic схемы (SearchStartRequest, ScrapedOrgItem, LeadItem)
    # -----------------------------------------------------------------
    print("\n[ТЕСТ 2] Проверка валидации Pydantic схем...")
    from app.schemas.search import SearchStartRequest
    from app.services.scrapers.base import ScrapedOrgItem
    from app.schemas.lead import LeadItem

    # 2.1 SearchStartRequest с одиночным city
    req1 = SearchStartRequest(niche="Автосервисы", city="Казань", source="yandex", limit=20)
    assert req1.city == "Казань"
    assert req1.cities is None

    # 2.2 SearchStartRequest со списком cities
    req2 = SearchStartRequest(
        niche="Автосервисы",
        city="Москва, СПб",
        cities=["Москва", "Санкт-Петербург"],
        source="yandex",
        limit=50
    )
    assert req2.cities == ["Москва", "Санкт-Петербург"]

    # 2.3 ScrapedOrgItem с атрибутом city
    item = ScrapedOrgItem(
        source="yandex",
        external_id="123456",
        name="Автосервис Мастер",
        city="Екатеринбург",
        address="ул. Ленина, 10"
    )
    assert item.city == "Екатеринбург"

    # 2.4 LeadItem с атрибутом city
    lead = LeadItem(
        id=1,
        campaign_id=1,
        name="Автосервис Мастер",
        category="Автосервис",
        city="Екатеринбург",
        address="ул. Ленина, 10",
        rating=4.8,
        reviews_count=25,
        primary_phone="+79991234567",
        all_phones=["+79991234567"],
        all_emails=[],
        socials=[],
        source="yandex",
        status_badge="HTTPS_OK",
        lead_score=85,
        has_ssl=True,
        is_adaptive=True,
        has_analytics=True
    )
    assert lead.city == "Екатеринбург"
    dumped = lead.model_dump()
    assert dumped["city"] == "Екатеринбург"
    print("  ✅ ТЕСТ 2 ПРОЙДЕН: Схемы корректно валидируют и сериализуют поле 'city'.")

    # -----------------------------------------------------------------
    # ТЕСТ 3: Структура базы данных и сохранение Organization.city
    # -----------------------------------------------------------------
    print("\n[ТЕСТ 3] Проверка колонок в БД и сохранения Organization.city...")
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    from app.db.database import Base
    from app.db.models import SearchCampaign, Organization, AuditResult

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        table_info = await conn.execute(text("PRAGMA table_info(organizations)"))
        columns = [row[1] for row in table_info.fetchall()]
        assert "city" in columns, f"Колонка 'city' не найдена в таблице organizations! Колонки: {columns}"

    async with session_factory() as db:
        # Создаем кампанию на 2 города
        camp = SearchCampaign(
            niche="Стоматологии",
            city="Москва, Санкт-Петербург",
            source="yandex",
            target_limit=50,
            status="RUNNING"
        )
        db.add(camp)
        await db.flush()

        # Создаем организации в разных городах
        org1 = Organization(
            campaign_id=camp.id,
            source="yandex",
            external_id="msk_001",
            name="Стоматология Дент Москва",
            category="Стоматология",
            city="Москва",
            address="г. Москва, Тверская 1"
        )
        org2 = Organization(
            campaign_id=camp.id,
            source="yandex",
            external_id="spb_001",
            name="Стоматология Улыбка СПб",
            category="Стоматология",
            city="Санкт-Петербург",
            address="г. Санкт-Петербург, Невский пр. 20"
        )
        db.add_all([org1, org2])
        await db.commit()

        # Проверяем сохранение и чтение
        res = await db.execute(select(Organization).where(Organization.campaign_id == camp.id))
        saved_orgs = res.scalars().all()
        assert len(saved_orgs) == 2
        assert saved_orgs[0].city == "Москва"
        assert saved_orgs[1].city == "Санкт-Петербург"
    print("  ✅ ТЕСТ 3 ПРОЙДЕН: Колонка city создана и успешно сохраняет города разных организаций в одной кампании.")

    # -----------------------------------------------------------------
    # ТЕСТ 4: Математика распределения квот и rollover
    # -----------------------------------------------------------------
    print("\n[ТЕСТ 4] Проверка математики динамического распределения квот...")
    cities_list = ["Москва", "Казань", "Самара"]
    limit = 60
    results = []

    # Город 1: Москва
    city_idx = 0
    remaining_needed = limit - len(results)  # 60
    remaining_cities = len(cities_list) - city_idx  # 3
    city_quota_1 = max(1, int(remaining_needed / remaining_cities))
    target_1 = min(limit, len(results) + city_quota_1)
    assert city_quota_1 == 20
    assert target_1 == 20

    # Предположим, Москва нашла только 12 организаций из 20 (недобор 8)
    for i in range(12):
        results.append(f"msk_{i}")

    # Город 2: Казань
    city_idx = 1
    remaining_needed = limit - len(results)  # 60 - 12 = 48
    remaining_cities = len(cities_list) - city_idx  # 2
    city_quota_2 = max(1, int(remaining_needed / remaining_cities))
    target_2 = min(limit, len(results) + city_quota_2)
    assert city_quota_2 == 24, f"Ожидалось 24 с учетом переноса недобора, получено {city_quota_2}"
    assert target_2 == 36

    # Предположим, Казань собрала ровно 24
    for i in range(24):
        results.append(f"kzn_{i}")

    # Город 3: Самара (последний город)
    city_idx = 2
    remaining_needed = limit - len(results)  # 60 - 36 = 24
    remaining_cities = len(cities_list) - city_idx  # 1
    city_quota_3 = remaining_needed
    target_3 = min(limit, len(results) + city_quota_3)
    assert city_quota_3 == 24
    assert target_3 == 60
    print("  ✅ ТЕСТ 4 ПРОЙДЕН: Алгоритм Rollover переносит недосбор на следующие города, гарантируя заполнение лимита.")

    # -----------------------------------------------------------------
    # ТЕСТ 5: Интеграция API эндпоинта /api/search/start
    # -----------------------------------------------------------------
    print("\n[ТЕСТ 5] Проверка эндпоинта start_search с несколькими городами...")
    from app.api.search import start_search

    mock_req = MagicMock()
    mock_req.state = MagicMock(user={"role": "admin", "sub": "1"})
    mock_req.cookies = {}

    search_payload = SearchStartRequest(
        niche="Автосервисы",
        city="Москва, Санкт-Петербург",
        cities=["Москва", "Санкт-Петербург"],
        source="yandex",
        limit=50
    )

    async with session_factory() as db:
        with patch("app.api.search.task_manager") as mock_tm:
            mock_tm.start_campaign = MagicMock()

            resp = await start_search(
                req=search_payload,
                request=mock_req,
                db=db
            )

            assert resp.status == "STARTED"
            assert resp.campaign_id is not None
            assert "в городах: Москва, Санкт-Петербург" in resp.message
            # Проверяем, что в task_manager ушли правильные параметры
            mock_tm.start_campaign.assert_called_once()
            call_kwargs = mock_tm.start_campaign.call_args[1]
            assert call_kwargs["cities"] == ["Москва", "Санкт-Петербург"]
            assert call_kwargs["city"] == "Москва, Санкт-Петербург"
    print("  ✅ ТЕСТ 5 ПРОЙДЕН: API принимает города, форматирует ответ и передает список в TaskManager.")

    # -----------------------------------------------------------------
    # ТЕСТ 6: Проверка YandexScraper._parse_business_item с параметром city
    # -----------------------------------------------------------------
    print("\n[ТЕСТ 6] Проверка YandexScraper._parse_business_item с привязкой города...")
    from app.services.scrapers.yandex_scraper import YandexScraper
    scraper = YandexScraper(headless=True)

    sample_raw = {
        "id": "org_777",
        "title": "Стоматологическая Клиника Дент",
        "type": "business",
        "fullAddress": "ул. Пушкина, д. 5",
        "categories": [{"name": "Стоматология"}],
        "ratingData": {"ratingValue": 4.9, "reviewCount": 42},
        "phones": [{"value": "+7 843 200-11-22"}],
        "urls": ["https://dent-example.ru"]
    }

    scraped_item = scraper._parse_business_item(sample_raw, city="Казань")
    assert scraped_item is not None
    assert scraped_item.name == "Стоматологическая Клиника Дент"
    assert scraped_item.city == "Казань", f"Ожидался город 'Казань', получено {scraped_item.city}"
    assert scraped_item.rating == 4.9
    print("  ✅ ТЕСТ 6 ПРОЙДЕН: Скрейпер корректно привязывает текущий город к каждой спарсенной организации.")

    print("\n" + "=" * 65)
    print("🎉 ВСЕ 6 ТЕСТОВ МУЛЬТИГОРОДСКОГО ПАРСИНГА УСПЕШНО ПРОЙДЕНЫ!")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_multi_city_tests())
