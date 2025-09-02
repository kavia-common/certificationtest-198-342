from __future__ import annotations
import threading
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any
from ..models.schemas import ExecutionDetail, ExecutionStatus, ExecutionEnvironment, GitSource

class InMemoryExecutionRepository:
    """
    Thread-safe in-memory repository for executions and logs.
    This is a placeholder. Replace with PostgreSQL-backed repository in future.
    """
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executions: Dict[str, ExecutionDetail] = {}
        self._logs: Dict[str, List[str]] = {}
        self._created_order: List[str] = []

    # PUBLIC_INTERFACE
    def create_execution(
        self,
        execution_id: str,
        git: GitSource,
        entrypoint: str,
        parameters: Dict[str, Any],
        environment: ExecutionEnvironment,
        correlation_id: Optional[str],
    ) -> ExecutionDetail:
        """Create and persist a new execution record with QUEUED status."""
        with self._lock:
            now = datetime.utcnow()
            detail = ExecutionDetail(
                execution_id=execution_id,
                status=ExecutionStatus.QUEUED,
                environment=environment,
                created_at=now,
                updated_at=now,
                correlation_id=correlation_id,
                git=git,
                entrypoint=entrypoint,
                parameters=parameters,
                result=None,
                error=None,
                logs_pointer=f"mem:{execution_id}",
            )
            self._executions[execution_id] = detail
            self._created_order.append(execution_id)
            self._logs.setdefault(execution_id, [])
            return detail

    # PUBLIC_INTERFACE
    def get_execution(self, execution_id: str) -> Optional[ExecutionDetail]:
        """Retrieve an execution by id."""
        with self._lock:
            return self._executions.get(execution_id)

    # PUBLIC_INTERFACE
    def update_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[ExecutionDetail]:
        """Update the status/result/error and timestamp."""
        with self._lock:
            detail = self._executions.get(execution_id)
            if not detail:
                return None
            detail.status = status
            if result is not None:
                detail.result = result
            if error is not None:
                detail.error = error
            detail.updated_at = datetime.utcnow()
            return detail

    # PUBLIC_INTERFACE
    def append_logs(self, execution_id: str, lines: List[str]) -> None:
        """Append log lines to an execution's log store."""
        with self._lock:
            if execution_id not in self._logs:
                self._logs[execution_id] = []
            self._logs[execution_id].extend(lines)

    # PUBLIC_INTERFACE
    def read_logs(self, execution_id: str, offset: int = 0, limit: int = 200) -> Tuple[List[str], int, bool]:
        """
        Read logs incrementally. Returns (lines, next_offset, eof).
        eof is true if execution is terminal and offset reached the end.
        """
        with self._lock:
            lines = self._logs.get(execution_id, [])
            total = len(lines)
            end = min(total, offset + limit)
            slice_lines = lines[offset:end]

            # eof when no more logs and execution terminal
            detail = self._executions.get(execution_id)
            terminal = detail is not None and detail.status in {
                ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELED, ExecutionStatus.TIMEOUT
            }
            eof = terminal and end >= total
            return slice_lines, end, eof

    # PUBLIC_INTERFACE
    def list_executions(self, limit: int = 50, status: Optional[ExecutionStatus] = None) -> List[ExecutionDetail]:
        """List recent executions optionally filtered by status."""
        with self._lock:
            ids = list(self._created_order)[-limit:]
            records = [self._executions[i] for i in ids if i in self._executions]
            if status:
                records = [r for r in records if r.status == status]
            # Latest first
            records.sort(key=lambda r: r.created_at, reverse=True)
            return records

    # PUBLIC_INTERFACE
    def stats(self) -> Dict[str, int]:
        """Compute basic stats such as totals by state."""
        with self._lock:
            totals = {
                "total": len(self._executions),
                "queued": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "canceled": 0,
                "timeout": 0,
            }
            for d in self._executions.values():
                key = d.status.value
                if key in totals:
                    totals[key] += 1
            return totals
