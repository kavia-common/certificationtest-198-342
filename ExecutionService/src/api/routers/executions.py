from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from ...models.schemas import (
    ExecutionRequest,
    SubmitResponse,
    ExecutionDetail,
    ExecutionStatus,
    LogsResponse,
)
from ...services.deps import get_execution_service
from ...services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])

# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=SubmitResponse,
    summary="Submit execution",
    description="Accepts execution request including git repo, parameters and environment. Returns an execution id.",
    responses={
        201: {"description": "Execution accepted."},
        400: {"description": "Invalid request."},
    },
    status_code=201,
)
def submit_execution(
    payload: ExecutionRequest,
    svc: ExecutionService = Depends(get_execution_service),
):
    """
    Endpoint to submit a new execution.
    Parameters:
    - payload: ExecutionRequest body with git source, entrypoint, parameters, environment, etc.

    Returns: SubmitResponse with assigned execution id and initial status.
    """
    resp = svc.submit(payload)
    return resp

# PUBLIC_INTERFACE
@router.get(
    "/{execution_id}",
    response_model=ExecutionDetail,
    summary="Get execution details",
    description="Retrieve the full details and current state of a single execution.",
)
def get_execution(
    execution_id: str,
    svc: ExecutionService = Depends(get_execution_service),
):
    """
    Retrieve execution detail, including git info, parameters, status, results, and logs pointer.
    """
    detail = svc.get(execution_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Execution not found")
    return detail

# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[ExecutionDetail],
    summary="List executions",
    description="List recent executions, optionally filtered by status.",
)
def list_executions(
    status: Optional[ExecutionStatus] = Query(None, description="Optional filter by status."),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return."),
    svc: ExecutionService = Depends(get_execution_service),
):
    """
    List recent executions ordered by creation time, latest first.
    """
    return svc.list(limit=limit, status=status)

# PUBLIC_INTERFACE
@router.get(
    "/{execution_id}/logs",
    response_model=LogsResponse,
    tags=["logs"],
    summary="Get execution logs",
    description="Retrieve captured logs for an execution. Supports incremental fetching using offset.",
)
def get_execution_logs(
    execution_id: str,
    offset: int = Query(0, ge=0, description="Starting offset to read logs from."),
    limit: int = Query(200, ge=1, le=1000, description="Max number of lines to return."),
    svc: ExecutionService = Depends(get_execution_service),
):
    """
    Fetch logs for an execution with pagination support via offset/limit.
    Returns an eof flag when no further logs are expected.
    """
    resp = svc.logs(execution_id, offset=offset, limit=limit)
    if not resp:
        raise HTTPException(status_code=404, detail="Execution not found")
    return resp
