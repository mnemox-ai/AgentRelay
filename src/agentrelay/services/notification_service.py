"""WebSocket notification service — broadcasts task events to connected clients."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationService:
    """Manages WebSocket connections and broadcasts task events."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WebSocket client connected (%d total)", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info("WebSocket client disconnected (%d remaining)", len(self._connections))

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Send an event to all connected clients. Silently drops dead connections."""
        message = json.dumps({"event": event_type, "data": data})
        async with self._lock:
            alive: list[WebSocket] = []
            for ws in self._connections:
                try:
                    await ws.send_text(message)
                    alive.append(ws)
                except Exception:
                    logger.warning("Dropping dead WebSocket connection")
            self._connections = alive


# Module-level singleton so routes and services share the same instance.
notification_service = NotificationService()
