"""WebSocket real-time notification tests."""

from __future__ import annotations

from starlette.testclient import TestClient

from agentrelay.api.app import app
from agentrelay.services.notification_service import notification_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_agent(tc: TestClient, name: str, *, quota_profile: dict | None = None) -> dict:
    payload: dict = {"name": name}
    if quota_profile is not None:
        payload["quota_profile"] = quota_profile
    resp = tc.post("/agents", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {"id": data["id"], "api_key": data["api_key"]}


def _auth(api_key: str) -> dict:
    return {"X-API-Key": api_key}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWebSocketConnection:
    """Basic WebSocket connectivity."""

    def test_connect_and_close(self):
        with TestClient(app) as tc:
            with tc.websocket_connect("/ws") as ws:
                ws.close()

    def test_multiple_clients(self):
        with TestClient(app) as tc:
            with tc.websocket_connect("/ws") as ws1:
                with tc.websocket_connect("/ws") as ws2:
                    assert len(notification_service._connections) >= 2
                    ws2.close()
                ws1.close()


class TestWebSocketBroadcast:
    """Broadcast delivers events to connected clients via real HTTP triggers."""

    def test_task_created_event(self):
        with TestClient(app) as tc:
            agent = _register_agent(tc, "ws-publisher")

            with tc.websocket_connect("/ws") as ws:
                resp = tc.post(
                    "/tasks",
                    json={
                        "task_spec": {"type": "coding", "token_estimate": 1000},
                        "publisher_id": agent["id"],
                        "reward": 5.0,
                    },
                    headers=_auth(agent["api_key"]),
                )
                assert resp.status_code == 201
                task_id = resp.json()["id"]

                msg = ws.receive_json()
                assert msg["event"] == "task_created"
                assert msg["data"]["task_id"] == task_id
                assert msg["data"]["status"] == "open"
                ws.close()

    def test_task_claimed_event(self):
        with TestClient(app) as tc:
            publisher = _register_agent(tc, "ws-pub-claim")
            worker = _register_agent(
                tc, "ws-worker-claim", quota_profile={"safe_token_cap": 50000}
            )

            task_resp = tc.post(
                "/tasks",
                json={
                    "task_spec": {"type": "coding", "token_estimate": 500},
                    "publisher_id": publisher["id"],
                    "reward": 3.0,
                },
                headers=_auth(publisher["api_key"]),
            )
            task_id = task_resp.json()["id"]

            with tc.websocket_connect("/ws") as ws:
                claim_resp = tc.post(
                    f"/tasks/{task_id}/claim",
                    json={"agent_id": worker["id"]},
                    headers=_auth(worker["api_key"]),
                )
                assert claim_resp.status_code == 200

                msg = ws.receive_json()
                assert msg["event"] == "task_claimed"
                assert msg["data"]["task_id"] == task_id
                assert msg["data"]["agent_id"] == worker["id"]
                ws.close()

    def test_task_completed_or_failed_event(self):
        with TestClient(app) as tc:
            publisher = _register_agent(tc, "ws-pub-submit")
            worker = _register_agent(
                tc, "ws-worker-submit", quota_profile={"safe_token_cap": 50000}
            )

            task_resp = tc.post(
                "/tasks",
                json={
                    "task_spec": {
                        "type": "data_structuring",
                        "token_estimate": 500,
                        "validation_method": "schema",
                        "output_schema": {
                            "type": "object",
                            "properties": {"result": {"type": "string"}},
                            "required": ["result"],
                        },
                    },
                    "publisher_id": publisher["id"],
                    "reward": 2.0,
                },
                headers=_auth(publisher["api_key"]),
            )
            task_id = task_resp.json()["id"]

            tc.post(
                f"/tasks/{task_id}/claim",
                json={"agent_id": worker["id"]},
                headers=_auth(worker["api_key"]),
            )

            with tc.websocket_connect("/ws") as ws:
                submit_resp = tc.post(
                    f"/tasks/{task_id}/submit",
                    json={
                        "task_id": task_id,
                        "agent_id": worker["id"],
                        "output_data": {"result": "hello world"},
                    },
                    headers=_auth(worker["api_key"]),
                )
                assert submit_resp.status_code == 200

                msg = ws.receive_json()
                assert msg["event"] in ("task_completed", "task_failed")
                assert msg["data"]["task_id"] == task_id

                ws.close()


class TestWebSocketDisconnect:
    """Disconnected clients are cleaned up."""

    def test_disconnected_client_removed(self):
        with TestClient(app) as tc:
            initial = len(notification_service._connections)
            with tc.websocket_connect("/ws") as ws:
                assert len(notification_service._connections) == initial + 1
                ws.close()
            assert len(notification_service._connections) <= initial



async def test_broadcast_no_clients():
    """Broadcast with zero clients does not raise."""
    await notification_service.broadcast("task_created", {"task_id": "x"})
