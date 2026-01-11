"""Response models for API Gateway."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class ErrorCode(str, Enum):
    """Standard error codes."""

    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"


class ErrorDetail(BaseModel):
    """Error detail information."""

    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None


class StandardResponse(BaseModel):
    """Standard response envelope."""

    success: bool
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": "123", "name": "John Doe"},
                "error": None,
                "metadata": {
                    "timestamp": "2024-01-10T10:30:00Z",
                    "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                },
            }
        }
    )


class ErrorResponse(BaseModel):
    """Error response envelope."""

    success: bool = False
    data: None = None
    error: ErrorDetail
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "data": None,
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or expired JWT token",
                    "details": None,
                },
                "metadata": {
                    "timestamp": "2024-01-10T10:30:00Z",
                    "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                },
            }
        }
    )


class ServiceStatus(BaseModel):
    """Health status of a service."""

    service_name: str
    status: str  # healthy, degraded, unhealthy
    last_check_at: datetime
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    consecutive_failures: int = 0


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # healthy or degraded
    timestamp: str
    uptime_seconds: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-10T10:30:00Z",
                "uptime_seconds": 3600,
            }
        }
    )


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    ready: bool
    services: Dict[str, ServiceStatus]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ready": True,
                "services": {
                    "auth-service": {
                        "service_name": "auth-service",
                        "status": "healthy",
                        "last_check_at": "2024-01-10T10:30:00Z",
                        "response_time_ms": 50,
                        "error": None,
                        "consecutive_failures": 0,
                    }
                },
            }
        }
    )
