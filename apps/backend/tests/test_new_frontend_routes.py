import asyncio
import os
import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.main import app

@pytest.mark.asyncio
async def test_frontend_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Main index
        r_root = await ac.get("/")
        assert r_root.status_code == 200
        assert "Castleweb Studio" in r_root.text
        print("Root /: OK (200)")

        # 2. /cases
        r_cases = await ac.get("/cases")
        assert r_cases.status_code == 200
        assert "cases" in r_cases.text.lower()
        print("Route /cases: OK (200)")

        # 3. /case-aria
        r_aria = await ac.get("/case-aria")
        assert r_aria.status_code == 200
        assert "ARIA" in r_aria.text
        print("Route /case-aria: OK (200)")

        # 4. /assets/lenis.min.js
        r_lenis = await ac.get("/assets/lenis.min.js")
        assert r_lenis.status_code == 200
        print("Asset /assets/lenis.min.js: OK (200)")

        # 5. Lead form submission
        lead_payload = {
            "name": "Тестовый Заказчик",
            "contact": "@castleweb_test",
            "task_description": "[Направление: Веб-сервисы & SaaS]\nТестовая заявка с обновленного сайта",
            "budget": None,
            "hp_website": None
        }
        r_lead = await ac.post("/api/v1/leads", json=lead_payload)
        assert r_lead.status_code in (201, 200), f"Lead submission failed: {r_lead.status_code} {r_lead.text}"
        data = r_lead.json()
        assert data.get("name") == "Тестовый Заказчик"
        print(f"Lead API /api/v1/leads: OK ({r_lead.status_code}, lead_id={data.get('id')})")

if __name__ == "__main__":
    asyncio.run(test_frontend_routes())
