"""Request models for API Gateway."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class GatewayRequestContext(BaseModel):
    """Context information for a gateway request."""

    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: str
    request_method: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_context: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user-123",
                "tenant_id": "tenant-456",
                "roles": ["user", "customer"],
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "request_path": "/api/v1/profiles/me",
                "request_method": "GET",
                "timestamp": "2024-01-10T10:30:00Z",
            }
        }
    )


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    per_user_per_minute: int = 1000
    per_tenant_per_minute: int = 100000
    per_ip_per_minute: int = 10000
    per_endpoint_overrides: dict = Field(default_factory=dict)
