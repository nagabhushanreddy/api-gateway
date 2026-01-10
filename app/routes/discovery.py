"""Service discovery endpoints."""

from typing import List

from fastapi import APIRouter, Request

from app.config import SERVICE_REGISTRY
from app.models.service import ServiceDiscoveryResponse, ServiceInfo

router = APIRouter()


@router.get("/discovery", response_model=ServiceDiscoveryResponse)
async def get_service_discovery(request: Request):
    """Get service catalog and API discovery information.

    Provides machine-readable service discovery for AI agents and clients.
    Returns available services, endpoints, and rate limit information.
    """
    service_discovery = getattr(request.app.state, "service_discovery", None)

    # Build service info list
    services: List[ServiceInfo] = []

    for service_name, config in SERVICE_REGISTRY.items():
        # Get health status
        status_str = "unknown"
        if service_discovery:
            health = service_discovery.service_health.get(service_name)
            status_str = health.status if health else "unknown"

        # Create service info
        service_info = ServiceInfo(
            name=service_name,
            description=f"{service_name.replace('-', ' ').title()}",
            base_path=config["path_prefix"],
            status=status_str,
            version="1.0.0",
            endpoints=[],  # Could be populated from OpenAPI specs
        )
        services.append(service_info)

    # Rate limit information
    rate_limits = {
        "per_user_per_minute": 1000,
        "per_tenant_per_minute": 100000,
        "per_ip_per_minute": 10000,
    }

    return ServiceDiscoveryResponse(
        services=services, authentication_required=True, rate_limits=rate_limits
    )
