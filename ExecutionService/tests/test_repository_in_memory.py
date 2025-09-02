from src.repositories.in_memory import InMemoryExecutionRepository
from src.models.schemas import (
    ExecutionEnvironment,
    ExecutionStatus,
    GitSource,
)


def _git():
    return GitSource(repository_url="https://example.com/repo.git", branch="main", subpath="scripts")


def test_create_and_get_and_list_and_stats():
    repo = InMemoryExecutionRepository()
    # Create
    d1 = repo.create_execution(
        execution_id="e1",
        git=_git(),
        entrypoint="run.py",
        parameters={"x": 1},
        environment=ExecutionEnvironment.SIMULATED,
        correlation_id="c1",
    )
    assert d1.execution_id == "e1"
    assert d1.status == ExecutionStatus.QUEUED
    assert repo.get_execution("e1") is not None

    # Logs append and read pre-terminal -> eof False
    repo.append_logs("e1", ["line1", "line2", "line3"])
    lines, next_offset, eof = repo.read_logs("e1", offset=0, limit=2)
    assert lines == ["line1", "line2"]
    assert next_offset == 2
    assert eof is False

    # Update to completed and read rest -> eof True once end reached
    repo.update_status("e1", ExecutionStatus.COMPLETED, result={"ok": True})
    lines2, next_offset2, eof2 = repo.read_logs("e1", offset=2, limit=10)
    assert lines2 == ["line3"]
    assert next_offset2 == 3
    assert eof2 is True

    # Stats reflect state
    stats = repo.stats()
    assert stats["total"] == 1
    assert stats["completed"] == 1

    # List filter
    # Create another queued
    repo.create_execution(
        execution_id="e2",
        git=_git(),
        entrypoint="run.py",
        parameters={},
        environment=ExecutionEnvironment.SIMULATED,
        correlation_id=None,
    )
    lst_all = repo.list_executions(limit=10, status=None)
    assert len(lst_all) == 2
    lst_completed = repo.list_executions(limit=10, status=ExecutionStatus.COMPLETED)
    assert all(x.status == ExecutionStatus.COMPLETED for x in lst_completed)
