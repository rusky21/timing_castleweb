"""HTTP/WebSocket authorization regressions, isolated from DB and integrations.

Run: python apps/parser/tests/test_access_boundaries.py
The production lifespan (workers/bots) is deliberately not started.
"""

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["SECRET_KEY"] = "isolated-access-boundary-test-signing-key"
os.environ["INTERNAL_API_SECRET"] = "isolated-access-boundary-test-internal-key"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["OUTREACH_BOT_TOKEN"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.websockets import WebSocketDisconnect

from app import main
from app.api import outreach, search
from app.core.security import create_session_token
from app.db.database import Base, get_db
from app.db.models import User, SearchCampaign, OutreachDialog, Organization, AuditResult


class AccessBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        cls.sessions = async_sessionmaker(cls.engine, expire_on_commit=False)

        async def seed():
            async with cls.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with cls.sessions() as db:
                for uid, role, active in (
                    (1, "demo", True), (2, "paid", True), (3, "admin", True),
                    (4, "superuser", True), (5, "root", True),
                    (6, "admin", False), (7, "paid", True), (8, "demo", False),
                ):
                    db.add(User(id=uid, email=f"user{uid}@example.test",
                                password_hash="unused", role=role, is_active=active))
                db.add_all([
                    SearchCampaign(id=101, user_id=1, niche="one", city="test", status="RUNNING"),
                    SearchCampaign(id=102, user_id=2, niche="two", city="test"),
                    SearchCampaign(id=103, user_id=None, niche="legacy", city="test"),
                    SearchCampaign(id=104, user_id=8, niche="disabled", city="test"),
                    OutreachDialog(id=1, account_id=1, client_tg_username="test_recipient", pitch_text="test"),
                ])
                await db.flush()
                for cid in (101, 102, 103):
                    db.add(Organization(id=cid, campaign_id=cid, source="test", external_id=str(cid), name="Test"))
                await db.flush()
                for cid in (101, 102, 103):
                    db.add(AuditResult(org_id=cid, pitch_full_text=f"private pitch {cid}"))
                await db.commit()
        asyncio.run(seed())

        async def override_db():
            async with cls.sessions() as db:
                yield db
        main.app.dependency_overrides[get_db] = override_db
        # Isolate direct WebSocket DB access as well as HTTP dependencies.
        cls.factory_patch = patch.object(main, "async_session_factory", cls.sessions, create=True)
        cls.factory_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.factory_patch.stop()
        main.app.dependency_overrides.clear()
        asyncio.run(cls.engine.dispose())

    def setUp(self):
        self.client = TestClient(main.app)  # No lifespan, no bot/network activity.

    def tearDown(self):
        self.client.close()

    def login(self, uid, role):
        self.client.cookies.set("access_token", create_session_token(uid, "test@example.test", role))

    def assert_ws_denied(self, path, code):
        with self.assertRaises(WebSocketDisconnect) as caught:
            with self.client.websocket_connect(path):
                self.fail("Unauthorized WebSocket accepted")
        self.assertEqual(caught.exception.code, code)

    def test_outreach_read_denied_to_non_admins(self):
        for uid, role, status in ((1, "demo", 403), (2, "paid", 403),
                                  (6, "admin", 401), (7, "admin", 403),
                                  (999, "admin", 401)):
            self.login(uid, role)
            for path in ("accounts", "dialogs", "dialogs/1", "blacklist", "stats", "settings"):
                with self.subTest(uid=uid, path=path):
                    self.assertEqual(self.client.get(f"/api/outreach/{path}").status_code, status)

    def test_outreach_write_denied_before_side_effects(self):
        self.login(1, "demo")
        with patch.object(outreach.session_manager, "send_message_safe", new_callable=AsyncMock, return_value=43) as send, \
             patch("app.core.env_editor.set_env_value") as write_env:
            self.assertEqual(self.client.post("/api/outreach/dialogs/1/message", json={"text": "blocked"}).status_code, 403)
            self.assertEqual(self.client.post("/api/outreach/settings", json={"key": "DEEPSEEK_API_KEY", "value": "blocked"}).status_code, 403)
            self.assertEqual(self.client.delete("/api/outreach/blacklist/1").status_code, 403)
            send.assert_not_awaited()
            write_env.assert_not_called()

    def test_every_outreach_route_is_guarded(self):
        # Valid bodies ensure that a missing role guard cannot hide behind 422.
        bodies = {"/test": {"username": "test", "website_url": "https://example.test"},
                  "/dialogs/{dialog_id}/message": {"text": "blocked"},
                  "/blacklist": {"identifier": "blocked"},
                  "/settings": {"key": "DEEPSEEK_API_KEY", "value": "blocked"}}
        self.login(2, "paid")
        with patch.object(outreach.deepseek_client, "ping", new_callable=AsyncMock, return_value=(True, 0, "test")), \
             patch.object(outreach.session_manager, "pick_best_account", new_callable=AsyncMock, return_value=None), \
             patch.object(outreach.session_manager, "send_message_safe", new_callable=AsyncMock), \
             patch("app.core.env_editor.set_env_value"):
            for route in outreach.router.routes:
                path = route.path.replace("{dialog_id}", "1").replace("{item_id}", "1")
                for method in route.methods:
                    with self.subTest(method=method, path=path):
                        suffix = route.path.removeprefix("/api/outreach")
                        kwargs = {"json": bodies[suffix]} if method == "POST" and suffix in bodies else {}
                        self.assertEqual(self.client.request(method, path, **kwargs).status_code, 403)

    def test_outreach_admin_and_role_aliases_still_work(self):
        for uid, role in ((3, "admin"), (4, "superuser"), (5, "root"), (3, "paid")):
            self.login(uid, role)
            self.assertEqual(self.client.get("/api/outreach/accounts").status_code, 200)
        self.login(3, "admin")
        with patch.object(outreach.session_manager, "send_message_safe", new_callable=AsyncMock, return_value=42) as send:
            response = self.client.post("/api/outreach/dialogs/1/message", json={"text": "authorized test"})
            self.assertEqual(response.status_code, 200, response.text)
            send.assert_awaited_once()

    def test_internal_header_alone_cannot_manage_outreach(self):
        response = self.client.get("/api/outreach/accounts", headers={"X-Internal-Secret": os.environ["INTERNAL_API_SECRET"]})
        self.assertEqual(response.status_code, 401)

    def test_outreach_missing_or_invalid_cookie_denied(self):
        self.assertEqual(self.client.get("/api/outreach/accounts").status_code, 401)
        self.client.cookies.set("access_token", "not-a-signed-token")
        self.assertEqual(self.client.get("/api/outreach/accounts").status_code, 401)

    def test_websocket_cross_user_unowned_and_missing_campaigns_denied(self):
        self.login(1, "demo")
        for path in ("/ws/102", "/ws/0102", "/ws/103", "/ws/999"):
            with self.subTest(path=path):
                self.assert_ws_denied(path, 4403)

    def test_websocket_invalid_disabled_deleted_and_stale_admin_denied(self):
        self.assert_ws_denied("/ws/101", 4401)
        for uid in ("invalid", "999999999999999999999999999999", "-1"):
            self.login(uid, "admin")
            self.assert_ws_denied("/ws/101", 4401)
        for uid, role, campaign, code in ((8, "demo", 104, 4401), (999, "admin", 101, 4401),
                                           (6, "admin", 101, 4401), (7, "admin", 101, 4403)):
            self.login(uid, role)
            with self.subTest(uid=uid):
                self.assert_ws_denied(f"/ws/{campaign}", code)

    def test_websocket_owner_and_admin_receive_campaign_events(self):
        for uid, role, campaign in ((1, "demo", 101), (2, "paid", 102),
                                     (3, "admin", 102), (4, "superuser", 103), (5, "root", 101)):
            self.login(uid, role)
            with self.client.websocket_connect(f"/ws/{campaign}") as ws:
                ws.send_text("ping")
                self.assertEqual(ws.receive_text(), "pong")
                event = {"type": "NEW_LEAD", "data": {"campaign_id": campaign, "name": "test"}}
                ws.portal.call(main.ws_manager.broadcast, campaign, event)
                self.assertEqual(ws.receive_json(), event)
        self.assertEqual(main.ws_manager.active_connections, {})

    def test_campaign_broadcast_does_not_cross_owner_streams(self):
        self.login(1, "demo")
        with self.client.websocket_connect("/ws/101") as ws_one:
            self.login(2, "paid")
            with self.client.websocket_connect("/ws/102") as ws_two:
                own_one = {"type": "NEW_LEAD", "data": {"campaign_id": 101}}
                own_two = {"type": "NEW_LEAD", "data": {"campaign_id": 102}}
                ws_one.portal.call(main.ws_manager.broadcast, 101, own_one)
                ws_two.portal.call(main.ws_manager.broadcast, 102, own_two)
                self.assertEqual(ws_one.receive_json(), own_one)
                self.assertEqual(ws_two.receive_json(), own_two)
                # A trailing event from another campaign would arrive before pong.
                for ws in (ws_one, ws_two):
                    ws.send_text("ping")
                    self.assertEqual(ws.receive_text(), "pong")

    def test_global_stream_requires_current_admin(self):
        self.assert_ws_denied("/ws/events", 4401)
        for uid, role, code in ((1, "demo", 4403), (2, "paid", 4403),
                                (7, "admin", 4403), (6, "admin", 4401)):
            self.login(uid, role)
            self.assert_ws_denied("/ws/events", code)

    def test_global_events_do_not_leak_into_regular_campaign_stream(self):
        self.login(1, "demo")
        with self.client.websocket_connect("/ws/101") as ws:
            ws.portal.call(main.ws_manager.broadcast_all, {"type": "NEW_FL_ORDER", "data": {"id": 42}})
            ws.send_text("ping")
            self.assertEqual(ws.receive_text(), "pong")

    def test_admin_keeps_global_events_on_both_stream_types(self):
        for uid, role, path in ((3, "admin", "/ws/101"), (3, "paid", "/ws/events"),
                                (4, "superuser", "/ws/events"), (5, "root", "/ws/events")):
            self.login(uid, role)
            with self.client.websocket_connect(path) as ws:
                event = {"type": "NEW_FL_ORDER", "data": {"id": 42}}
                ws.portal.call(main.ws_manager.broadcast_all, event)
                self.assertEqual(ws.receive_json(), event)
        self.assertEqual(main.ws_manager.global_connections, [])

    def test_existing_session_loses_access_after_deactivation(self):
        async def set_active(value):
            async with self.sessions() as db:
                user = await db.get(User, 1)
                user.is_active = value
                await db.commit()
        self.login(1, "demo")
        try:
            with self.client.websocket_connect("/ws/101") as ws:
                ws.portal.call(set_active, False)
                self.assertEqual(self.client.get("/api/reports").status_code, 401)
                ws.portal.call(main.ws_manager.broadcast, 101, {"type": "NEW_LEAD"})
                with self.assertRaises(WebSocketDisconnect):
                    ws.receive_json()
        finally:
            asyncio.run(set_active(True))

    def test_open_admin_stream_and_http_lose_demoted_role(self):
        async def set_role(value):
            async with self.sessions() as db:
                user = await db.get(User, 3)
                user.role = value
                await db.commit()
        self.login(3, "admin")
        try:
            with self.client.websocket_connect("/ws/events") as ws:
                ws.portal.call(set_role, "paid")
                self.assertEqual(self.client.get("/api/users").status_code, 403)
                ws.portal.call(main.ws_manager.broadcast_all, {"type": "NEW_FL_ORDER"})
                with self.assertRaises(WebSocketDisconnect):
                    ws.receive_json()
        finally:
            asyncio.run(set_role("admin"))

    def test_idle_stream_checks_revocation_on_timeout(self):
        async def run():
            ws = AsyncMock()
            ws.receive_text.side_effect = asyncio.TimeoutError
            check = AsyncMock(return_value=False)
            await main.receive_stream(ws, check)
            check.assert_awaited_once()
            ws.close.assert_awaited_once_with(code=4403)
            ws.send_text.assert_not_awaited()
        asyncio.run(run())

    def test_campaign_actions_reject_other_users_without_side_effects(self):
        self.login(1, "demo")
        for route, method in (("/stop", "stop_campaign"), ("/captcha/resolved", "signal_captcha_resolved")):
            for cid in (102, 103, 999):
                with self.subTest(route=route, cid=cid), patch.object(search.task_manager, method) as action:
                    response = self.client.post("/api/search" + route, json={"campaign_id": cid})
                    self.assertEqual(response.status_code, 404)
                    action.assert_not_called()

    def test_campaign_actions_preserve_owner_and_admin_access(self):
        for uid, role, cid in ((1, "demo", 101), (2, "paid", 102), (3, "admin", 102), (4, "superuser", 103), (5, "root", 101)):
            self.login(uid, role)
            for route, method in (("/stop", "stop_campaign"), ("/captcha/resolved", "signal_captcha_resolved")):
                with self.subTest(uid=uid, route=route), patch.object(search.task_manager, method, return_value=True) as action:
                    response = self.client.post("/api/search" + route, json={"campaign_id": cid})
                    self.assertEqual(response.status_code, 200)
                    action.assert_called_once_with(cid)

    def test_campaign_routes_reject_service_key_and_stale_privileges(self):
        for uid, role, expected in ((None, None, 401), (6, "admin", 401), (1, "admin", 404)):
            self.client.cookies.clear()
            if uid is not None:
                self.login(uid, role)
            headers = {"X-Internal-Secret": os.environ["INTERNAL_API_SECRET"]}
            with patch.object(search.task_manager, "stop_campaign") as stop, patch.object(search.task_manager, "signal_captcha_resolved") as captcha:
                for path in ("/api/search/stop", "/api/search/captcha/resolved"):
                    response = self.client.post(path, json={"campaign_id": 102}, headers=headers)
                    self.assertEqual(response.status_code, expected)
                self.assertEqual(self.client.get("/api/leads/102/pitch", headers=headers).status_code, expected)
                stop.assert_not_called()
                captcha.assert_not_called()

    def test_pitch_is_private_to_owner_and_current_admin(self):
        self.login(1, "demo")
        for cid in (102, 103, 999):
            response = self.client.get(f"/api/leads/{cid}/pitch")
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("private pitch", response.text)
        for uid, role, cid in ((1, "demo", 101), (2, "paid", 102), (3, "admin", 103)):
            self.login(uid, role)
            response = self.client.get(f"/api/leads/{cid}/pitch")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["full_text"], f"private pitch {cid}")

    def test_telegram_campaign_controls_require_explicit_operator(self):
        from app import config
        from app.services.telegram import handlers

        async def run():
            for allowed, uid, permitted in ((set(), 10, False), ({20}, 10, False), ({20}, 20, True)):
                for handler, method, data in (
                    (handlers.cb_maps_stop, "stop_campaign", "maps_stop"),
                    (handlers.cb_resolve_captcha, "signal_captcha_resolved", "resolve_captcha_101"),
                ):
                    call = SimpleNamespace(from_user=SimpleNamespace(id=uid), data=data,
                                           answer=AsyncMock(), message=AsyncMock())
                    with patch.object(config, "ADMIN_TELEGRAM_IDS", allowed), patch.object(handlers, "async_session_factory", self.sessions), patch.object(search.task_manager, method, return_value=True) as action:
                        await handler(call)
                        if permitted:
                            action.assert_called_once_with(101)
                        else:
                            action.assert_not_called()
                            call.message.answer.assert_not_awaited()
                            call.message.edit_text.assert_not_awaited()
        asyncio.run(run())

    def test_telegram_admin_middleware_denies_empty_allowlist(self):
        from app.services.telegram import admin_bot

        async def run():
            for allowed, uid, permitted in ((set(), 10, False), ({20}, 10, False), ({20}, 20, True)):
                for middleware in (admin_bot.admin_auth_middleware, admin_bot.admin_auth_cb_middleware):
                    event = SimpleNamespace(from_user=SimpleNamespace(id=uid), answer=AsyncMock())
                    handler = AsyncMock(return_value="handled")
                    with patch.object(admin_bot, "ADMIN_TELEGRAM_IDS", allowed):
                        await middleware(handler, event, {})
                    if permitted:
                        handler.assert_awaited_once_with(event, {})
                    else:
                        handler.assert_not_awaited()
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
