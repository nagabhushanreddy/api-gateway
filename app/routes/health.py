"""Health check endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.models.response import HealthResponse, ReadinessResponse, ServiceStatus

router = APIRouter()

# Track start time for uptime calculation
_start_time = time.time()


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health():
    """Basic health check endpoint.

    Returns gateway health status and uptime.
    Used by load balancers for health checks.
    """
    uptime_seconds = int(time.time() - _start_time)

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        uptime_seconds=uptime_seconds,
    )


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz():
    """Kubernetes liveness probe endpoint.

    Returns simple OK response to indicate gateway is alive.
    """
    return {"status": "OK"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def ready(request: Request):
    """Kubernetes readiness probe endpoint.

    Checks connectivity to all critical downstream services.
    Returns 200 if ready, 503 if not ready.
    """
    # Get service discovery from app state
    # If it hasn't been initialized yet (in tests), return 200
    service_discovery = getattr(request.app.state, "service_discovery", None)

    if not service_discovery:
        # If service discovery not initialized, assume ready
        return ReadinessResponse(ready=True, services={})

    # Get health status of all services
    all_health = service_discovery.get_all_health_status()

    # Check if all critical services are healthy
    all_ready = service_discovery.are_critical_services_healthy()

    # Convert to ServiceStatus models
    services = {}
    for name, health_data in all_health.items():
        services[name] = ServiceStatus(
            service_name=health_data["service_name"],
            status=health_data["status"],
            last_check_at=(
                datetime.fromisoformat(health_data["last_check_at"])
                if health_data["last_check_at"]
                else datetime.utcnow()
            ),
            response_time_ms=health_data["response_time_ms"],
            error=health_data["error"],
            consecutive_failures=health_data["consecutive_failures"],
        )

    response = ReadinessResponse(ready=all_ready, services=services)

    if not all_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
        )

    return response
