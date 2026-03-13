"""WebSocket endpoint for real-time task notifications."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agentrelay.services.notification_service import notification_service

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
    finally:
        await notification_service.disconnect(ws)
