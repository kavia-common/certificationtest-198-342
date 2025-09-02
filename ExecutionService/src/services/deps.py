from functools import lru_cache
from .execution_service import ExecutionService

@lru_cache()
def get_execution_service() -> ExecutionService:
    """
    Creates or returns a singleton ExecutionService for the process.
    """
    return ExecutionService()
