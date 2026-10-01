import asyncio
import io
import pytest
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.presentation.middlewares.rate_limit import _in_memory_store


@pytest.mark.asyncio
async def test_health_and_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"

        # 2. Live status
        res = await client.get("/api/v1/status")
        assert res.status_code == 200
        status_data = res.json()
        assert status_data["status"] == "operational"
        assert "latency_ms" in status_data
        assert "services" in status_data
        assert status_data["services"]["database"]["status"] == "operational"
        assert status_data["engineers_on_duty"] == 2


@pytest.mark.asyncio
async def test_cases_endpoints_and_cache():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # List cases (1st call: DB fetch + cache set)
        res = await client.get("/api/v1/cases")
        assert res.status_code == 200
        cases = res.json()
        assert len(cases) >= 3

        # List cases (2nd call: cached)
        res_cached = await client.get("/api/v1/cases")
        assert res_cached.status_code == 200
        assert len(res_cached.json()) == len(cases)

        # Filter by category
        saas_res = await client.get("/api/v1/cases?category=saas")
        assert saas_res.status_code == 200
        for c in saas_res.json():
            assert c["category"] == "saas"

        # Detail case
        detail_res = await client.get("/api/v1/cases/lead-hunter-saas")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data["slug"] == "lead-hunter-saas"
        assert "solution_fe" in detail_data
        assert "solution_be" in detail_data


@pytest.mark.asyncio
async def test_uploads_service():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Presigned URL generation for valid document
        req_payload = {
            "filename": "technical_specification.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 1024 * 500
        }
        res = await client.post("/api/v1/uploads/presigned-url", json=req_payload)
        assert res.status_code == 200
        data = res.json()
        assert "upload_url" in data
        assert "public_url" in data
        assert data["storage_type"] in ("cloudflare_r2", "local")

        # 2. Reject disallowed dangerous file extensions
        bad_payload = {
            "filename": "malware.exe",
            "content_type": "application/x-msdownload"
        }
        res_bad = await client.post("/api/v1/uploads/presigned-url", json=bad_payload)
        assert res_bad.status_code == 400
        assert "Недопустимый формат" in res_bad.json()["detail"]

        # 3. Local direct upload fallback
        dummy_file = io.BytesIO(b"Hello Castleweb Project Spec")
        files = {"file": ("brief.pdf", dummy_file, "application/pdf")}
        upload_res = await client.post("/api/v1/uploads/file", files=files)
        assert upload_res.status_code == 200
        assert upload_res.json()["status"] == "uploaded"


@pytest.mark.asyncio
async def test_leads_and_anti_spam():
    _in_memory_store.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        lead_payload = {
            "name": "Иван Смирнов",
            "contact": "@ivan_tech",
            "task_description": "Разработка API микросервисов для маркетплейса",
            "budget": "от 700 000 ₽"
        }
        headers = {"x-forwarded-for": "194.87.12.34"}
        res = await client.post("/api/v1/leads", json=lead_payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] > 0
        assert data["name"] == "Иван Смирнов"

        await asyncio.sleep(0.2)

        # Rate limit test (4th request from same IP is blocked)
        await client.post("/api/v1/leads", json=lead_payload, headers=headers)
        await client.post("/api/v1/leads", json=lead_payload, headers=headers)
        res4 = await client.post("/api/v1/leads", json=lead_payload, headers=headers)
        assert res4.status_code == 429

        # Honeypot
        bot_payload = {
            "name": "Bot Spammer",
            "contact": "spam@seo.com",
            "task_description": "Boost your rank now!",
            "hp_website": "http://evil-bot.com"
        }
        bot_res = await client.post("/api/v1/leads", json=bot_payload, headers={"x-forwarded-for": "100.200.50.4"})
        assert bot_res.status_code == 201
        assert bot_res.json()["status"] == "spam"


@pytest.mark.asyncio
async def test_telegram_crm_webhook():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        lead_payload = {
            "name": "Ольга Заказчица",
            "contact": "@olga_ceo",
            "task_description": "SaaS платформа аналитики продаж",
            "budget": "1 500 000 ₽"
        }
        create_res = await client.post(
            "/api/v1/leads",
            json=lead_payload,
            headers={"x-forwarded-for": "185.220.101.5"}
        )
        lead_id = create_res.json()["id"]

        # 1. Simulate Engineer clicking "Взять в работу"
        take_callback = {
            "callback_query": {
                "id": "cb_001",
                "from": {"id": 123456, "first_name": "Senior", "username": "senior_dev"},
                "message": {"message_id": 9999, "chat": {"id": -100987654321}},
                "data": f"lead_take:{lead_id}"
            }
        }
        cb_res = await client.post("/api/v1/telegram/webhook", json=take_callback)
        assert cb_res.status_code == 200
        assert cb_res.json()["ok"] is True

        # 2. Simulate Engineer clicking "Связался"
        contacted_callback = {
            "callback_query": {
                "id": "cb_002",
                "from": {"id": 123456, "first_name": "Senior", "username": "senior_dev"},
                "message": {"message_id": 9999, "chat": {"id": -100987654321}},
                "data": f"lead_contacted:{lead_id}"
            }
        }
        res_cont = await client.post("/api/v1/telegram/webhook", json=contacted_callback)
        assert res_cont.status_code == 200

        # 3. Simulate Engineer clicking "Спам / В бан"
        test_attacker_ip = f"222.111.1.{int(asyncio.get_event_loop().time() * 1000) % 250}"
        spam_lead_res = await client.post(
            "/api/v1/leads",
            json={"name": "Bad Guy", "contact": "bad@evil.com", "task_description": "Spam message"},
            headers={"x-forwarded-for": test_attacker_ip}
        )
        assert spam_lead_res.status_code == 201
        spam_lead_id = spam_lead_res.json()["id"]

        spam_callback = {
            "callback_query": {
                "id": "cb_003",
                "from": {"id": 123456, "first_name": "Senior", "username": "senior_dev"},
                "message": {"message_id": 9998, "chat": {"id": -100987654321}},
                "data": f"lead_spam:{spam_lead_id}"
            }
        }
        res_spam = await client.post("/api/v1/telegram/webhook", json=spam_callback)
        assert res_spam.status_code == 200

        # Verify that test_attacker_ip is now BLACKLISTED in database!
        blocked_attempt = await client.post(
            "/api/v1/leads",
            json={"name": "Attacker", "contact": "attack@mail.com", "task_description": "More spam"},
            headers={"x-forwarded-for": test_attacker_ip}
        )
        assert blocked_attempt.status_code == 403

        # 4. Test Telegram commands: /stats and /leads
        stats_cmd = {
            "message": {
                "message_id": 100,
                "chat": {"id": -100987654321},
                "text": "/stats"
            }
        }
        res_stats = await client.post("/api/v1/telegram/webhook", json=stats_cmd)
        assert res_stats.status_code == 200

        leads_cmd = {
            "message": {
                "message_id": 101,
                "chat": {"id": -100987654321},
                "text": "/leads"
            }
        }
        res_leads = await client.post("/api/v1/telegram/webhook", json=leads_cmd)
        assert res_leads.status_code == 200


@pytest.mark.asyncio
async def test_deduplication_and_webhook_secret():
    from app.core.config import get_settings
    settings = get_settings()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Test lead deduplication
        dedup_payload = {
            "name": "Дмитрий Повторный",
            "contact": "@dmitry_dedup",
            "task_description": "Разработка уникального личного кабинета под ключ",
            "budget": "от 500 000 ₽"
        }
        res1 = await client.post("/api/v1/leads", json=dedup_payload, headers={"x-forwarded-for": "178.62.200.1"})
        assert res1.status_code == 201
        lead_id_1 = res1.json()["id"]

        # Duplicate submit with identical contact & description within 5 minutes returns existing lead
        res2 = await client.post("/api/v1/leads", json=dedup_payload, headers={"x-forwarded-for": "178.62.200.2"})
        assert res2.status_code in (200, 201)
        lead_id_2 = res2.json()["id"]
        assert lead_id_1 == lead_id_2

        # 2. Test Telegram Webhook secret token check
        orig_secret = settings.TELEGRAM_WEBHOOK_SECRET
        try:
            settings.TELEGRAM_WEBHOOK_SECRET = "super_secret_test_token"

            # Rejected without header
            res_no_token = await client.post("/api/v1/telegram/webhook", json={"message": {"text": "/stats"}})
            assert res_no_token.json().get("ok") is False

            # Rejected with wrong token
            res_bad_token = await client.post(
                "/api/v1/telegram/webhook",
                json={"message": {"text": "/stats"}},
                headers={"x-telegram-bot-api-secret-token": "wrong_token"}
            )
            assert res_bad_token.json().get("ok") is False

            # Accepted with correct token
            res_good_token = await client.post(
                "/api/v1/telegram/webhook",
                json={"message": {"message_id": 200, "chat": {"id": -100987654321}, "text": "/export"}},
                headers={"x-telegram-bot-api-secret-token": "super_secret_test_token"}
            )
            assert res_good_token.status_code == 200
            assert res_good_token.json().get("ok") is True
        finally:
            settings.TELEGRAM_WEBHOOK_SECRET = orig_secret


if __name__ == "__main__":
    async def run_all():
        print("🧪 Running API verification tests...")
        await test_health_and_status()
        print("✅ /health and /status: PASS")
        await test_cases_endpoints_and_cache()
        print("✅ /cases list, filter, detail & cache: PASS")
        await test_uploads_service()
        print("✅ /uploads presigned URL & file handling: PASS")
        await test_leads_and_anti_spam()
        print("✅ /leads rate limiting & honeypot: PASS")
        await test_telegram_crm_webhook()
        print("✅ Telegram Headless CRM webhook & ban actions: PASS")
        await test_deduplication_and_webhook_secret()
        print("✅ Deduplication & Telegram webhook secret security: PASS")
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

    asyncio.run(run_all())

