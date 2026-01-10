"""Service models for API Gateway."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceEndpoint(BaseModel):
    """Service endpoint information."""

    path: str
    method: str
    summary: str
    tags: List[str] = Field(default_factory=list)
    authenticated: bool = True


class ServiceInfo(BaseModel):
    """Service information for discovery."""

    name: str
    description: str
    base_path: str
    status: str
    version: str = "1.0.0"
    endpoints: List[ServiceEndpoint] = Field(default_factory=list)


class ServiceDiscoveryResponse(BaseModel):
    """Service discovery response."""

    services: List[ServiceInfo]
    authentication_required: bool = True
    rate_limits: Dict[str, Any] = Field(default_factory=dict)


class GatewayStatusResponse(BaseModel):
    """Gateway status response for admin."""

    uptime_seconds: int
    request_count: Dict[str, int]
    error_rate: float
    active_connections: int
    queue_depth: int
    service_latencies: Dict[str, Dict[str, int]]
    endpoint_request_counts: Dict[str, int]


class RateLimitStatus(BaseModel):
    """Rate limit status for a key."""

    key: str
    current_usage: int
    limit: int
    reset_at: str
    window_start_at: str
