from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import DATABASE_URL

# SQLite aiosqlite engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=10000;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """Dependency для получения асинхронной сессии БД в FastAPI эндпоинтах"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

from sqlalchemy import text

async def init_db():
    """Инициализация таблиц базы данных при старте приложения"""
    async with engine.begin() as conn:
        from app.db import models  # noqa
        await conn.run_sync(Base.metadata.create_all)

        # Безопасная миграция для существующих БД
        migrations = [
            "ALTER TABLE organizations ADD COLUMN telegram VARCHAR(255)",
            "ALTER TABLE organizations ADD COLUMN has_telegram BOOLEAN DEFAULT 0",
            "ALTER TABLE telegram_user_settings ADD COLUMN fl_keywords TEXT DEFAULT '[]'",
            "ALTER TABLE telegram_user_settings ADD COLUMN fl_allow_negotiable BOOLEAN DEFAULT 1",
            "ALTER TABLE telegram_user_settings ADD COLUMN fl_hide_pro BOOLEAN DEFAULT 0",
            "ALTER TABLE telegram_user_settings ADD COLUMN fl_urgent_only BOOLEAN DEFAULT 0",
            "ALTER TABLE telegram_user_settings ADD COLUMN maps_source_filter VARCHAR(50) DEFAULT 'all'",
            "ALTER TABLE telegram_user_settings ADD COLUMN maps_only_without_site BOOLEAN DEFAULT 0",
            "ALTER TABLE telegram_user_settings ADD COLUMN maps_only_without_ssl BOOLEAN DEFAULT 0",
            "ALTER TABLE telegram_user_settings ADD COLUMN notify_sound BOOLEAN DEFAULT 1",
            "ALTER TABLE telegram_user_settings ADD COLUMN notify_captcha BOOLEAN DEFAULT 1",
            "ALTER TABLE telegram_user_settings ADD COLUMN fl_live_mode BOOLEAN DEFAULT 1",
            "ALTER TABLE fl_orders ADD COLUMN is_free BOOLEAN DEFAULT 1",
            "ALTER TABLE users ADD COLUMN demo_searches_left INTEGER DEFAULT 5",
            "ALTER TABLE users ADD COLUMN max_companies_per_search INTEGER DEFAULT 5",
            "ALTER TABLE users ADD COLUMN last_search_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN tg_user_id VARCHAR(100)",
            "ALTER TABLE search_campaigns ADD COLUMN user_id INTEGER",
        ]
        for mig in migrations:
            try:
                await conn.execute(text(mig))
            except Exception:
                pass

    # Автоматическое создание начального администратора при первом запуске
    try:
        import os
        import logging
        from sqlalchemy import select, func
        from app.db.models import User
        from app.core.security import hash_password

        db_logger = logging.getLogger("leadhunter.db")
        async with async_session_factory() as session:
            result = await session.execute(select(func.count(User.id)))
            users_count = result.scalar_one()
            if users_count == 0:
                admin_email = os.environ.get("INITIAL_ADMIN_EMAIL", "admin@lead.pro").strip().lower()
                admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD", "AdminPass123!_ChangeMe")
                admin = User(
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    role="admin",
                    is_active=True
                )
                session.add(admin)
                await session.commit()
                db_logger.info(f"🔑 Успешно создан начальный администратор в базе данных: {admin_email}")
    except Exception as e:
        import logging
        logging.getLogger("leadhunter.db").warning(f"Проверка/создание пользователя: {e}")
