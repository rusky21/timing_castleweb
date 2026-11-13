"""No external services or application lifespan are used by these tests."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from app.presentation.api.v1.endpoints import telegram_webhook as endpoint


@pytest.mark.asyncio
async def test_service_routes_require_internal_auth():
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    app = FastAPI()
    app.include_router(endpoint.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method, path in (("GET", "/test"), ("POST", "/test"), ("GET", "/setup-webhook"),
                             ("POST", "/setup-webhook"), ("GET", "/webhook-info"), ("POST", "/fl-order")):
            response = await client.request(method, path)
            assert response.status_code == 403, path
        with patch.object(endpoint.settings, "TELEGRAM_BOT_TOKEN", ""):
            response = await client.get("/webhook-info", headers={"X-Internal-Secret": endpoint.settings.INTERNAL_API_SECRET})
            assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("configured,incoming", [("", ""), ("super-secret-telegram-webhook-token", "super-secret-telegram-webhook-token"), ("unique-test-token", ""), ("unique-test-token", "wrong")])
async def test_webhook_rejects_before_parsing(configured, incoming):
    request = SimpleNamespace(headers={"x-telegram-bot-api-secret-token": incoming},
                              json=AsyncMock(return_value={}), client=None)
    with patch.object(endpoint.settings, "TELEGRAM_WEBHOOK_SECRET", configured):
        with pytest.raises(HTTPException) as caught:
            await endpoint.telegram_webhook(request, db=AsyncMock())
    assert caught.value.status_code in (403, 503)
    request.json.assert_not_awaited()


@pytest.mark.asyncio
async def test_webhook_accepts_valid_telegram_header():
    request = SimpleNamespace(headers={"x-telegram-bot-api-secret-token": "unique-test-token"},
                              json=AsyncMock(return_value={}), client=None)
    with patch.object(endpoint.settings, "TELEGRAM_WEBHOOK_SECRET", "unique-test-token"):
        result = await endpoint.telegram_webhook(request, db=AsyncMock())
    assert result == {"ok": True}
    request.json.assert_awaited_once()
