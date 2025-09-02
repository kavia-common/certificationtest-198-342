from fastapi import APIRouter, Depends
from ...models.schemas import MonitoringInfo
from ...services.deps import get_execution_service
from ...services.execution_service import ExecutionService

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# PUBLIC_INTERFACE
@router.get(
    "/readiness",
    summary="Readiness probe",
    description="Returns 200 if the service is ready to accept traffic.",
)
def readiness():
    """Simple readiness endpoint used by orchestrators."""
    return {"status": "ready"}

# PUBLIC_INTERFACE
@router.get(
    "/info",
    response_model=MonitoringInfo,
    summary="Service info and counters",
    description="Returns basic self-monitoring information: uptime and counts by state.",
)
def info(svc: ExecutionService = Depends(get_execution_service)):
    """Return service uptime and queue/running stats."""
    stats = svc.stats()
    return MonitoringInfo(
        service="ExecutionService",
        version="0.1.0",
        uptime_seconds=svc.uptime_seconds(),
        total_executions=stats.get("total", 0),
        running_executions=stats.get("running", 0),
        queued_executions=stats.get("queued", 0),
    )

# PUBLIC_INTERFACE
@router.get(
    "/websocket-docs",
    summary="WebSocket usage (placeholder)",
    description="This service does not expose a WebSocket yet. This endpoint documents intended future usage.",
)
def websocket_docs():
    """
    Provide human-readable docs for future websocket endpoints for real-time logs/updates.
    """
    return {
        "websocket": "planned",
        "note": "Real-time logs/updates may be provided via WebSocket in a future version. For now, poll /executions/{id}/logs.",
    }
