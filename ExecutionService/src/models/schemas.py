from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field, HttpUrl

class ExecutionEnvironment(str, Enum):
    LOCAL = "local"
    AIRFLOW = "airflow"
    SIMULATED = "simulated"

class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMEOUT = "timeout"

# PUBLIC_INTERFACE
class GitSource(BaseModel):
    """Git source inputs for cloning the repo and locating the script."""
    repository_url: HttpUrl = Field(..., description="HTTPS URL for the repository (GitLab/GitHub/Gerrit).")
    branch: Optional[str] = Field(None, description="Branch to checkout; default repository default.")
    commit_sha: Optional[str] = Field(None, description="Optional commit SHA for deterministic runs.")
    subpath: Optional[str] = Field(None, description="Subfolder within the repository containing the script(s).")

# PUBLIC_INTERFACE
class ExecutionRequest(BaseModel):
    """
    Define an execution request with a git source, target script or entrypoint,
    parameters and selected environment.
    """
    git: GitSource = Field(..., description="Git repository location to fetch code from.")
    entrypoint: str = Field(..., description="Script or command to execute (e.g., path/to/script.py).")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Key/Value parameters to pass to the job.")
    environment: ExecutionEnvironment = Field(ExecutionEnvironment.SIMULATED, description="Execution environment selector.")
    correlation_id: Optional[str] = Field(None, description="Optional correlation id provided by caller (e.g., certification run id).")
    timeout_seconds: Optional[int] = Field(None, description="Optional wall clock timeout for the execution.")
    notify: Optional[Dict[str, Any]] = Field(None, description="Optional notification configuration.")

# PUBLIC_INTERFACE
class ExecutionSummary(BaseModel):
    """Minimal execution metadata for listings."""
    execution_id: str = Field(..., description="Unique execution id.")
    status: ExecutionStatus = Field(..., description="Current status.")
    environment: ExecutionEnvironment = Field(..., description="Execution environment.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")
    correlation_id: Optional[str] = Field(None, description="Correlation id if provided by caller.")

# PUBLIC_INTERFACE
class ExecutionDetail(ExecutionSummary):
    """Full execution details."""
    git: GitSource = Field(..., description="Git source details used for execution.")
    entrypoint: str = Field(..., description="Entrypoint executed.")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters passed.")
    result: Optional[Dict[str, Any]] = Field(None, description="Structured result payload upon completion.")
    error: Optional[str] = Field(None, description="Error message when status is FAILED.")
    logs_pointer: Optional[str] = Field(None, description="Opaque pointer to logs retrieval (e.g., logs id, url).")

# PUBLIC_INTERFACE
class LogsResponse(BaseModel):
    """Logs payload returned by the service."""
    execution_id: str = Field(..., description="Execution id associated with these logs.")
    lines: List[str] = Field(default_factory=list, description="Captured logs as lines.")
    next_offset: int = Field(0, description="Next offset for incremental fetching.")
    eof: bool = Field(False, description="True if execution completed and no further logs will be produced.")

# PUBLIC_INTERFACE
class SubmitResponse(BaseModel):
    """Response returned after submitting an execution request."""
    execution_id: str = Field(..., description="Assigned execution id.")
    status: ExecutionStatus = Field(..., description="Initial status (typically queued).")

# PUBLIC_INTERFACE
class MonitoringInfo(BaseModel):
    """Self monitoring information returned by monitoring endpoints."""
    service: str = Field(..., description="Service name.")
    version: str = Field(..., description="Service version.")
    uptime_seconds: float = Field(..., description="Approximate uptime in seconds.")
    total_executions: int = Field(..., description="Total number of executions ever submitted.")
    running_executions: int = Field(..., description="Currently running executions.")
    queued_executions: int = Field(..., description="Currently queued executions.")
