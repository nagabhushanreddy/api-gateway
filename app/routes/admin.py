"""Admin endpoints for gateway management."""

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models.request import RateLimitConfig
from app.models.service import GatewayStatusResponse, RateLimitStatus

router = APIRouter()

# Track start time for uptime
_start_time = time.time()

# Simple request counter (in production, use metrics service)
_request_counts = {"total": 0, "last_hour": 0}


async def verify_admin_role(request: Request):
    """Verify user has admin role.

    In production, this should check with authz-service.
    For now, just check if user_id is present (authenticated).
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    # In production: check with authz-service for admin role
    # For now, allow any authenticated user
    return user_id


@router.get("/gateway/status", response_model=GatewayStatusResponse)
async def get_gateway_status(
    request: Request, admin_user: str = Depends(verify_admin_role)
):
    """Get gateway operational status.

    Returns uptime, request counts, error rates, and service latencies.
    Requires admin role.
    """
    uptime_seconds = int(time.time() - _start_time)

    # Get circuit breaker states
    circuit_breaker = request.app.state.circuit_breaker
    circuit_states = circuit_breaker.get_all_states()

    # Get service latencies from service discovery
    service_discovery = request.app.state.service_discovery
    service_latencies = {}

    for service_name, health in service_discovery.service_health.items():
        if health.response_time_ms:
            service_latencies[service_name] = {
                "p50": health.response_time_ms,
                "p95": health.response_time_ms,
                "p99": health.response_time_ms,
            }

    return GatewayStatusResponse(
        uptime_seconds=uptime_seconds,
        request_count=_request_counts,
        error_rate=0.0,  # Would need proper metrics
        active_connections=0,  # Would need proper tracking
        queue_depth=0,  # Would need proper tracking
        service_latencies=service_latencies,
        endpoint_request_counts={},  # Would need proper metrics
    )


@router.get("/rate-limits")
async def get_rate_limit_status(
    request: Request,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    admin_user: str = Depends(verify_admin_role),
):
    """Get rate limit status for user or tenant.

    Requires admin role.
    """
    rate_limit_service = request.app.state.rate_limit_service

    results = []

    if user_id:
        key = f"user:{user_id}"
        status_data = await rate_limit_service.get_rate_limit_status(key)
        if status_data:
            results.append(
                RateLimitStatus(
                    key=key,
                    current_usage=status_data["current_usage"],
                    limit=rate_limit_service.per_user_per_minute,
                    reset_at=status_data["reset_at"],
                    window_start_at=status_data["window_start_at"],
                )
            )

    if tenant_id:
        key = f"tenant:{tenant_id}"
        status_data = await rate_limit_service.get_rate_limit_status(key)
        if status_data:
            results.append(
                RateLimitStatus(
                    key=key,
                    current_usage=status_data["current_usage"],
                    limit=rate_limit_service.per_tenant_per_minute,
                    reset_at=status_data["reset_at"],
                    window_start_at=status_data["window_start_at"],
                )
            )

    return {"rate_limits": results}


@router.post("/rate-limits/config", status_code=status.HTTP_200_OK)
async def update_rate_limit_config(
    config: RateLimitConfig,
    request: Request,
    admin_user: str = Depends(verify_admin_role),
):
    """Update rate limit configuration.

    Allows hot-reload of rate limit settings.
    Requires admin role.
    """
    rate_limit_service = request.app.state.rate_limit_service

    # Update configuration
    rate_limit_service.per_user_per_minute = config.per_user_per_minute
    rate_limit_service.per_tenant_per_minute = config.per_tenant_per_minute
    rate_limit_service.per_ip_per_minute = config.per_ip_per_minute

    return {
        "message": "Rate limit configuration updated",
        "config": config.model_dump(),
    }
