from fastapi.testclient import TestClient

from src.models.schemas import GitSource, ExecutionRequest, ExecutionEnvironment, ExecutionStatus


def _sample_request():
    return ExecutionRequest(
        git=GitSource(repository_url="https://example.com/repo.git", branch="main", subpath="scripts"),
        entrypoint="scripts/run.py",
        parameters={"a": 1},
        environment=ExecutionEnvironment.SIMULATED,
        correlation_id="corr-123",
    )


def test_submit_execution_happy_path(client: TestClient):
    payload = _sample_request().model_dump(mode="json")
    r = client.post("/executions", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert "execution_id" in data and data["execution_id"]
    assert data["status"] == ExecutionStatus.QUEUED.value


def test_get_execution_detail_and_logs_flow(client: TestClient):
    # Submit
    payload = _sample_request().model_dump(mode="json")
    r = client.post("/executions", json=payload)
    assert r.status_code == 201
    exec_id = r.json()["execution_id"]

    # Get detail
    r2 = client.get(f"/executions/{exec_id}")
    assert r2.status_code == 200
    detail = r2.json()
    # Since fake service marks status progressed to COMPLETED after submission flow
    assert detail["status"] in [ExecutionStatus.QUEUED.value, ExecutionStatus.RUNNING.value, ExecutionStatus.COMPLETED.value]
    assert detail["execution_id"] == exec_id
    assert detail["git"]["repository_url"].startswith("https://")

    # Logs: page 1
    r3 = client.get(f"/executions/{exec_id}/logs?offset=0&limit=2")
    assert r3.status_code == 200
    logs = r3.json()
    assert logs["execution_id"] == exec_id
    assert len(logs["lines"]) <= 2
    assert logs["next_offset"] >= len(logs["lines"])
    assert isinstance(logs["eof"], bool)

    # Logs: next page
    r4 = client.get(f"/executions/{exec_id}/logs?offset={logs['next_offset']}&limit=100")
    assert r4.status_code == 200
    logs2 = r4.json()
    # Should eventually reach eof True as fake service finalizes execution
    assert logs2["execution_id"] == exec_id
    assert logs2["next_offset"] >= logs["next_offset"]
    assert isinstance(logs2["eof"], bool)


def test_list_executions_and_filter(client: TestClient):
    # Create a few executions
    for i in range(3):
        payload = _sample_request().model_dump(mode="json")
        r = client.post("/executions", json=payload)
        assert r.status_code == 201

    # List all
    r = client.get("/executions?limit=10")
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list)
    assert len(arr) >= 3

    # Filter by status completed
    r2 = client.get(f"/executions?status={ExecutionStatus.COMPLETED.value}&limit=10")
    assert r2.status_code == 200
    arr2 = r2.json()
    for d in arr2:
        assert d["status"] == ExecutionStatus.COMPLETED.value


def test_execution_not_found_errors(client: TestClient):
    missing_id = "does-not-exist"
    r = client.get(f"/executions/{missing_id}")
    assert r.status_code == 404
    r2 = client.get(f"/executions/{missing_id}/logs")
    assert r2.status_code == 404
