"""WebSocket endpoint for real-time task notifications."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agentrelay.services.notification_service import notification_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await notification_service.connect(ws)
    try:
        # Keep the connection alive — wait for client messages (pings/close).
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("WebSocket connection error (timeout or protocol failure)")
    finally:
        await notification_service.disconnect(ws)
