from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import executions, monitoring, simulator

def create_app() -> FastAPI:
    """
    Factory to create and configure the FastAPI application.
    """
    app = FastAPI(
        title="Execution Service",
        description="Manages execution of scripts across environments (local, airflow, simulated). Provides async routing, logs, status, and self-monitoring.",
        version="0.1.0",
        openapi_tags=[
            {"name": "executions", "description": "Submit and manage execution requests."},
            {"name": "logs", "description": "Retrieve execution logs and streaming info."},
            {"name": "monitoring", "description": "Self-monitoring, health, and metrics."},
            {"name": "simulator", "description": "Simulated execution endpoints for developer/test use."},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(executions.router)
    app.include_router(monitoring.router)
    app.include_router(simulator.router)
    return app

app = create_app()

# PUBLIC_INTERFACE
@app.get("/", tags=["monitoring"], summary="Health Check")
def health_check():
    """Basic health check endpoint for liveness probes."""
    return {"message": "Healthy"}
