import logging
from typing import Dict, List, Any, Callable, Awaitable
from fastapi import WebSocket

logger = logging.getLogger("connection_manager")

class ConnectionManager:
    """Менеджер WebSocket-соединений с группировкой по ID поисковой кампании"""

    def __init__(self):
        # campaign_id -> список активных WebSocket соединений
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.global_connections: List[WebSocket] = []
        self.privileged_campaign_connections: set[WebSocket] = set()
        self.access_checks: Dict[WebSocket, Callable[[bool], Awaitable[bool]]] = {}

    async def connect_global(self, websocket: WebSocket, *, check: Callable[[bool], Awaitable[bool]]):
        await websocket.accept()
        self.access_checks[websocket] = check
        self.global_connections.append(websocket)
        logger.info("Global WebSocket client connected")

    def disconnect_global(self, websocket: WebSocket):
        self.access_checks.pop(websocket, None)
        if websocket in self.global_connections:
            self.global_connections.remove(websocket)
        logger.info("Global WebSocket client disconnected")

    async def connect(self, campaign_id: int, websocket: WebSocket, *, check: Callable[[bool], Awaitable[bool]], receive_global: bool = False):
        await websocket.accept()
        self.access_checks[websocket] = check
        if campaign_id not in self.active_connections:
            self.active_connections[campaign_id] = []
        self.active_connections[campaign_id].append(websocket)
        if receive_global:
            self.privileged_campaign_connections.add(websocket)
        logger.info(f"WebSocket client connected to campaign {campaign_id}")

    def disconnect(self, campaign_id: int, websocket: WebSocket):
        self.access_checks.pop(websocket, None)
        self.privileged_campaign_connections.discard(websocket)
        if campaign_id in self.active_connections:
            if websocket in self.active_connections[campaign_id]:
                self.active_connections[campaign_id].remove(websocket)
            if not self.active_connections[campaign_id]:
                del self.active_connections[campaign_id]
        logger.info(f"WebSocket client disconnected from campaign {campaign_id}")

    async def can_deliver(self, connection: WebSocket, global_event: bool = False) -> bool:
        check = self.access_checks.get(connection)
        try:
            allowed = check is not None and await check(global_event)
        except Exception:
            allowed = False  # Fail closed if the current authorization cannot be established.
        if allowed:
            return True
        self.disconnect_global(connection)
        for campaign_id in list(self.active_connections):
            if connection in self.active_connections[campaign_id]:
                self.disconnect(campaign_id, connection)
        try:
            await connection.close(code=4403)
        except Exception:
            pass
        return False

    async def broadcast(self, campaign_id: int, event: Dict[str, Any]):
        """Безопасная рассылка события всем подписчикам кампании"""
        if campaign_id not in self.active_connections:
            return

        dead_sockets = []
        for connection in list(self.active_connections[campaign_id]):
            try:
                if not await self.can_deliver(connection):
                    continue
                await connection.send_json(event)
            except Exception:
                dead_sockets.append(connection)

        # Удаляем отключившиеся сокеты
        for dead in dead_sockets:
            self.disconnect(campaign_id, dead)

    async def broadcast_all(self, event: Dict[str, Any]):
        """Глобальные FL-события доступны только административным соединениям."""
        all_sockets = set(self.global_connections) | self.privileged_campaign_connections

        for connection in set(all_sockets):
            try:
                if not await self.can_deliver(connection, global_event=True):
                    continue
                await connection.send_json(event)
            except Exception:
                pass

ws_manager = ConnectionManager()
