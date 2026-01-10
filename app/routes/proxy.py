"""Proxy endpoints for routing to downstream services."""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def proxy_request(path: str, request: Request):
    """Proxy requests to downstream services.

    This catch-all route forwards requests to the appropriate microservice
    based on the path prefix.
    """
    # Get services from app state
    service_discovery = getattr(request.app.state, "service_discovery", None)
    circuit_breaker = getattr(request.app.state, "circuit_breaker", None)
    service_client = getattr(request.app.state, "service_client", None)

    # If services not initialized (e.g., in tests), return 503
    if not all([service_discovery, circuit_breaker, service_client]):
        logger.warning("Required services not initialized for proxy request")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        )

    # Determine target service from path
    full_path = f"/api/v1/{path}"
    service_info = service_discovery.get_service_by_path(full_path)

    if not service_info:
        logger.warning(f"No service found for path: {full_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No service found for path: {full_path}",
        )

    service_name, service_url = service_info

    # Check circuit breaker
    is_allowed = await circuit_breaker.is_call_allowed(service_name)
    if not is_allowed:
        logger.error(f"Circuit breaker open for service: {service_name}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service {service_name} is currently unavailable",
        )

    # Build target URL
    target_url = f"{service_url}{full_path}"

    # Prepare headers
    headers = dict(request.headers)
    # Remove host header to avoid conflicts
    headers.pop("host", None)

    # Add correlation ID
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        headers["X-Correlation-Id"] = correlation_id

    # Add user context headers for downstream services
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)
    if user_id:
        headers["X-User-Id"] = user_id
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id

    # Get request body
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()

    try:
        # Forward request
        logger.info(f"Forwarding {request.method} {full_path} to {service_name}")

        response = await service_client.forward_request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=dict(request.query_params),
            data=body if body else None,
        )

        # Record success in circuit breaker
        await circuit_breaker.record_success(service_name)

        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )

    except httpx.TimeoutException:
        # Record failure in circuit breaker
        await circuit_breaker.record_failure(service_name)
        logger.error(f"Request to {service_name} timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Request to {service_name} timed out",
        )
    except httpx.RequestError as e:
        # Record failure in circuit breaker
        await circuit_breaker.record_failure(service_name)
        logger.error(f"Request to {service_name} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to {service_name}",
        )
    except Exception as e:
        # Record failure in circuit breaker
        await circuit_breaker.record_failure(service_name)
        logger.error(f"Unexpected error forwarding to {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
