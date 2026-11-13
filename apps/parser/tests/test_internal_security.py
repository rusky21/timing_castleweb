"""Регрессионные проверки критического контура внутреннего API.

Запуск: python apps/parser/tests/test_internal_security.py
"""

import asyncio
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARSER_DIR))
os.environ["INTERNAL_API_SECRET"] = "test-internal-secret-value"

from app.api.auth import (  # noqa: E402
    CreateDemoUserPayload,
    GrantPaidAccessPayload,
    ResetPasswordPayload,
    create_demo_user,
    grant_paid_access,
    reset_password_internal,
)
from app.core.security import hash_password, is_valid_internal_secret  # noqa: E402
from app.db.database import (  # noqa: E402
    Base,
    LEGACY_INITIAL_ADMIN_PASSWORD,
    ensure_secure_initial_admin,
)
from app.db.models import User  # noqa: E402


SAFE_SECRET = "test-internal-secret-value"
LEGACY_SECRETS = (
    "castleweb-internal-demo-secret",
    "castleweb_internal_secret_123",
)


class RequestStub:
    def __init__(self, secret: str | None = SAFE_SECRET):
        self.headers = {} if secret is None else {"X-Internal-Secret": secret}


@contextmanager
def preserved_environment(*names: str):
    original = {name: os.environ.get(name) for name in names}
    try:
        yield
    finally:
        for name, value in original.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


async def new_database():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def expect_http_status(awaitable, expected_status: int):
    try:
        await awaitable
    except HTTPException as exc:
        assert exc.status_code == expected_status, exc
        return
    raise AssertionError(f"Expected HTTP {expected_status}")


def test_secret_policy() -> None:
    with preserved_environment("INTERNAL_API_SECRET"):
        os.environ["INTERNAL_API_SECRET"] = SAFE_SECRET
        assert is_valid_internal_secret(SAFE_SECRET)
        assert not is_valid_internal_secret("wrong-secret")
        assert not is_valid_internal_secret(None)
        for legacy in LEGACY_SECRETS:
            assert not is_valid_internal_secret(legacy)
            os.environ["INTERNAL_API_SECRET"] = legacy
            assert not is_valid_internal_secret(legacy)

        os.environ.pop("INTERNAL_API_SECRET", None)
        assert not is_valid_internal_secret(SAFE_SECRET)


async def check_demo_provisioning_cannot_create_or_mutate_admin() -> None:
    os.environ["INTERNAL_API_SECRET"] = SAFE_SECRET
    engine, factory = await new_database()
    try:
        async with factory() as session:
            result = await create_demo_user(
                CreateDemoUserPayload(tg_user_id="1878543896", tg_username="admin"),
                RequestStub(),
                db=session,
            )
            created = (
                await session.execute(select(User).where(User.tg_user_id == "1878543896"))
            ).scalar_one()
            assert result["status"] == "created"
            assert created.role == "demo"

        async with factory() as session:
            admin_hash = hash_password("unique-admin-test-password")
            admin = User(
                email="security-admin@example.test",
                password_hash=admin_hash,
                role="admin",
                is_active=True,
                tg_user_id="admin-telegram-id",
            )
            session.add(admin)
            await session.commit()

            await expect_http_status(
                create_demo_user(
                    CreateDemoUserPayload(
                        tg_user_id="admin-telegram-id",
                        tg_username="admin",
                    ),
                    RequestStub(),
                    db=session,
                ),
                403,
            )
            await expect_http_status(
                grant_paid_access(
                    GrantPaidAccessPayload(tg_user_id="admin-telegram-id", plan="1m"),
                    RequestStub(),
                    db=session,
                ),
                403,
            )
            await expect_http_status(
                reset_password_internal(
                    ResetPasswordPayload(tg_user_id="admin-telegram-id"),
                    RequestStub(),
                    db=session,
                ),
                403,
            )
            await session.refresh(admin)
            assert admin.role == "admin"
            assert admin.password_hash == admin_hash
            assert admin.is_active is True

        async with factory() as session:
            payload_with_legacy_body_secret = CreateDemoUserPayload.model_validate({
                "tg_user_id": "body-secret-only",
                "secret_key": LEGACY_SECRETS[0],
            })
            await expect_http_status(
                create_demo_user(
                    payload_with_legacy_body_secret,
                    RequestStub(secret=None),
                    db=session,
                ),
                403,
            )
            missing = (
                await session.execute(select(User).where(User.tg_user_id == "body-secret-only"))
            ).scalar_one_or_none()
            assert missing is None
    finally:
        await engine.dispose()


def test_demo_provisioning_cannot_create_or_mutate_admin() -> None:
    asyncio.run(check_demo_provisioning_cannot_create_or_mutate_admin())


async def check_secure_admin_bootstrap() -> None:
    with preserved_environment("INITIAL_ADMIN_EMAIL", "INITIAL_ADMIN_PASSWORD"):
        os.environ.pop("INITIAL_ADMIN_EMAIL", None)
        os.environ.pop("INITIAL_ADMIN_PASSWORD", None)
        engine, factory = await new_database()
        try:
            async with factory() as session:
                assert await ensure_secure_initial_admin(session) is False
                assert (await session.execute(select(User))).scalars().all() == []
        finally:
            await engine.dispose()

        os.environ["INITIAL_ADMIN_EMAIL"] = "first-admin@example.test"
        os.environ["INITIAL_ADMIN_PASSWORD"] = "unique-bootstrap-password"
        engine, factory = await new_database()
        try:
            async with factory() as session:
                assert await ensure_secure_initial_admin(session) is True
                admin = (await session.execute(select(User))).scalar_one()
                assert admin.email == "first-admin@example.test"
                assert admin.role == "admin"
                assert admin.is_active is True
        finally:
            await engine.dispose()

        engine, factory = await new_database()
        try:
            async with factory() as session:
                legacy_admin = User(
                    email="legacy-admin@example.test",
                    password_hash=hash_password(LEGACY_INITIAL_ADMIN_PASSWORD),
                    role="admin",
                    is_active=True,
                )
                session.add(legacy_admin)
                await session.commit()
                assert await ensure_secure_initial_admin(session) is False
                await session.refresh(legacy_admin)
                assert legacy_admin.is_active is False
        finally:
            await engine.dispose()


def test_secure_admin_bootstrap() -> None:
    asyncio.run(check_secure_admin_bootstrap())


async def run_all_tests() -> None:
    test_secret_policy()
    await check_demo_provisioning_cannot_create_or_mutate_admin()
    await check_secure_admin_bootstrap()
    print("OK: internal API and admin bootstrap security regressions passed")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
