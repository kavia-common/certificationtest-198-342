from fastapi.testclient import TestClient


def test_health_root(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Healthy"}


def test_readiness(client: TestClient):
    r = client.get("/monitoring/readiness")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_info(client: TestClient):
    r = client.get("/monitoring/info")
    assert r.status_code == 200
    payload = r.json()
    # Basic contract checks
    assert payload["service"] == "ExecutionService"
    assert payload["version"] == "0.1.0"
    assert isinstance(payload["uptime_seconds"], (int, float))
    assert payload["total_executions"] >= 0
    assert payload["running_executions"] >= 0
    assert payload["queued_executions"] >= 0


def test_websocket_docs(client: TestClient):
    r = client.get("/monitoring/websocket-docs")
    assert r.status_code == 200
    data = r.json()
    assert data["websocket"] == "planned"
    assert "logs" in data["note"]
