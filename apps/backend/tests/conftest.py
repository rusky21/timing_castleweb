import asyncio
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    """
    ASGITransport не запускает lifespan приложения, поэтому create_all из app.main
    в тестах не срабатывает и чистая БД в CI остаётся без таблиц.
    Создаём таблицы и наполняем кейсы из data/cases.json до первого теста.
    """
    from app.core.database import engine
    from seed_cases import seed_data

    async def _setup():
        await seed_data()
        # Соединения пула привязаны к этому event loop, тесты откроют свои
        await engine.dispose()

    asyncio.run(_setup())
    yield
