import sys
import types
import time
import uuid
from typing import Dict, Optional, Any, List, Tuple

import pytest
from fastapi.testclient import TestClient

# Import app and dependencies
from src.api.main import app
from src.models.schemas import (
    ExecutionRequest,
    ExecutionDetail,
    ExecutionStatus,
    LogsResponse,
)
from src.services import deps as deps_module


class _FakeRepo:
    """Simple in-memory store mimicking required repository operations for the fake service."""
    def __init__(self) -> None:
        self.executions: Dict[str, ExecutionDetail] = {}
        self.logs: Dict[str, List[str]] = {}

    def create(self, req: ExecutionRequest) -> ExecutionDetail:
        eid = str(uuid.uuid4())
        # Use datetime conversion via pydantic (construct with model values)
        detail = ExecutionDetail(
            execution_id=eid,
            status=ExecutionStatus.QUEUED,
            environment=req.environment,
            created_at=__import__("datetime").datetime.utcnow(),
            updated_at=__import__("datetime").datetime.utcnow(),
            correlation_id=req.correlation_id,
            git=req.git,
            entrypoint=req.entrypoint,
            parameters=req.parameters,
            result=None,
            error=None,
            logs_pointer=f"mem:{eid}",
        )
        self.executions[eid] = detail
        self.logs[eid] = []
        return detail

    def get(self, execution_id: str) -> Optional[ExecutionDetail]:
        return self.executions.get(execution_id)

    def update_status(
        self, execution_id: str, status: ExecutionStatus, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None
    ) -> Optional[ExecutionDetail]:
        d = self.executions.get(execution_id)
        if not d:
            return None
        d.status = status
        if result is not None:
            d.result = result
        if error is not None:
            d.error = error
        d.updated_at = __import__("datetime").datetime.utcnow()
        return d

    def append_logs(self, execution_id: str, lines: List[str]) -> None:
        self.logs.setdefault(execution_id, [])
        self.logs[execution_id].extend(lines)

    def read_logs(self, execution_id: str, offset: int, limit: int) -> Tuple[List[str], int, bool]:
        lines = self.logs.get(execution_id, [])
        end = min(len(lines), offset + limit)
        slice_ = lines[offset:end]
        d = self.executions.get(execution_id)
        terminal = d is not None and d.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELED,
            ExecutionStatus.TIMEOUT,
        }
        eof = terminal and end >= len(lines)
        return slice_, end, eof

    def list(self, limit: int, status: Optional[ExecutionStatus]) -> List[ExecutionDetail]:
        arr = list(self.executions.values())
        if status:
            arr = [x for x in arr if x.status == status]
        arr.sort(key=lambda x: x.created_at, reverse=True)
        return arr[:limit]

    def stats(self) -> Dict[str, int]:
        res = {"total": len(self.executions), "queued": 0, "running": 0, "completed": 0, "failed": 0, "canceled": 0, "timeout": 0}
        for d in self.executions.values():
            key = d.status.value
            if key in res:
                res[key] += 1
        return res


class FakeExecutionService:
    """A fake service implementing expected interface used by routers, simulating async/flows."""

    def __init__(self) -> None:
        self._repo = _FakeRepo()
        self._start_time = time.time()

    # PUBLIC_INTERFACE
    def submit(self, payload: ExecutionRequest):
        detail = self._repo.create(payload)
        # Simulate that a QUEUED execution quickly transitions to RUNNING then COMPLETED with logs
        self._repo.update_status(detail.execution_id, ExecutionStatus.RUNNING)
        self._repo.append_logs(detail.execution_id, [f"Starting: {payload.entrypoint}", "Executing step 1", "Executing step 2"])
        # Mark completed and add final log
        self._repo.append_logs(detail.execution_id, ["Finished successfully"])
        self._repo.update_status(detail.execution_id, ExecutionStatus.COMPLETED, result={"ok": True})
        # Return minimal response used by API
        from src.models.schemas import SubmitResponse
        return SubmitResponse(execution_id=detail.execution_id, status=ExecutionStatus.QUEUED)

    # PUBLIC_INTERFACE
    def get(self, execution_id: str) -> Optional[ExecutionDetail]:
        return self._repo.get(execution_id)

    # PUBLIC_INTERFACE
    def list(self, limit: int = 50, status: Optional[ExecutionStatus] = None) -> List[ExecutionDetail]:
        return self._repo.list(limit=limit, status=status)

    # PUBLIC_INTERFACE
    def logs(self, execution_id: str, offset: int = 0, limit: int = 200) -> Optional[LogsResponse]:
        d = self._repo.get(execution_id)
        if not d:
            return None
        lines, next_offset, eof = self._repo.read_logs(execution_id, offset=offset, limit=limit)
        return LogsResponse(execution_id=execution_id, lines=lines, next_offset=next_offset, eof=eof)

    # PUBLIC_INTERFACE
    def stats(self) -> Dict[str, int]:
        return self._repo.stats()

    # PUBLIC_INTERFACE
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time


@pytest.fixture(scope="session")
def fake_execution_service() -> FakeExecutionService:
    return FakeExecutionService()


@pytest.fixture(autouse=True, scope="session")
def stub_execution_service_module(fake_execution_service):
    """
    Ensure that 'src.services.execution_service' import path exists for routers by
    inserting a stub module into sys.modules with an ExecutionService symbol.
    """
    module_name = "src.services.execution_service"
    mod = types.ModuleType(module_name)
    # Expose ExecutionService class in the module
    setattr(mod, "ExecutionService", FakeExecutionService)
    sys.modules[module_name] = mod
    yield
    # Clean up not strictly necessary for session scope, but keep it tidy
    # del sys.modules[module_name]


@pytest.fixture
def client(fake_execution_service: FakeExecutionService):
    """
    Provides a TestClient with dependency override for get_execution_service to use our fake service instance.
    """
    # Override dependency
    def _override():
        return fake_execution_service
    app.dependency_overrides[deps_module.get_execution_service] = _override

    with TestClient(app) as c:
        yield c

    # Cleanup
    app.dependency_overrides.pop(deps_module.get_execution_service, None)
