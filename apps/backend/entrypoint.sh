#!/bin/sh
set -e

echo "⏳ Waiting for PostgreSQL database connection..."
python -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def wait_db():
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url or 'sqlite' in db_url:
        return
    engine = create_async_engine(db_url, pool_pre_ping=True)
    for i in range(30):
        try:
            async with engine.connect() as conn:
                await conn.execute(text('SELECT 1'))
            print('✅ PostgreSQL is ready!')
            await engine.dispose()
            return
        except Exception:
            await asyncio.sleep(1)
    print('⚠️ Warning: DB timeout, proceeding anyway...')

asyncio.run(wait_db())
"

echo "🔄 Running database migrations (Alembic)..."
alembic upgrade head

echo "🌱 Ensuring portfolio cases are seeded..."
python scripts/seed_cases.py

echo "🚀 Starting Production ASGI Server (Uvicorn)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips="*"
