"""Configuration management for API Gateway."""

from typing import Dict, List, Optional

from pydantic_settings import BaseSettings


class ServiceConfig(BaseSettings):
    """Configuration for a downstream service."""

    host: str
    port: int
    path_prefix: str
    health_check_path: str = "/health"
    health_check_interval: int = 30
    timeout: int = 30000  # milliseconds
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    critical: bool = True


class Settings(BaseSettings):
    """Application settings."""

    # Service Identity
    SERVICE_NAME: str = "api-gateway"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "local"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_PUBLIC_KEY_URL: Optional[str] = None
    AUTH_SERVICE_URL: str = "http://localhost:8001"

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_USER_PER_MINUTE: int = 1000
    RATE_LIMIT_PER_TENANT_PER_MINUTE: int = 100000
    RATE_LIMIT_PER_IP_PER_MINUTE: int = 10000
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # CORS Configuration
    CORS_ENABLED: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_HEADERS: List[str] = ["*"]

    # Service Registry
    AUTHZ_SERVICE_URL: str = "http://localhost:8002"
    PROFILE_SERVICE_URL: str = "http://localhost:8006"
    LOAN_SERVICE_URL: str = "http://localhost:8005"
    DOCUMENT_SERVICE_URL: str = "http://localhost:8003"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8007"
    AUDIT_SERVICE_URL: str = "http://localhost:8008"

    # Request Configuration
    MAX_REQUEST_BODY_SIZE: int = 10485760  # 10MB
    MAX_RESPONSE_BODY_SIZE: int = 104857600  # 100MB
    REQUEST_TIMEOUT: int = 30  # seconds

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = 3

    # Health Check Configuration
    HEALTH_CHECK_INTERVAL: int = 30

    # OpenAPI Configuration
    OPENAPI_TITLE: str = "Multi-Finance API Gateway"
    OPENAPI_VERSION: str = "1.0.0"
    OPENAPI_DESCRIPTION: str = "API Gateway for Multi-Finance User Application"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Service registry with configuration
SERVICE_REGISTRY: Dict[str, Dict] = {
    "auth-service": {
        "url": settings.AUTH_SERVICE_URL,
        "path_prefix": "/api/v1/auth",
        "health_check_path": "/health",
        "timeout": 30000,
        "critical": True,
    },
    "authz-service": {
        "url": settings.AUTHZ_SERVICE_URL,
        "path_prefix": "/api/v1/authz",
        "health_check_path": "/health",
        "timeout": 5000,
        "critical": True,
    },
    "profile-service": {
        "url": settings.PROFILE_SERVICE_URL,
        "path_prefix": "/api/v1/profiles",
        "health_check_path": "/health",
        "timeout": 30000,
        "critical": True,
    },
    "loan-service": {
        "url": settings.LOAN_SERVICE_URL,
        "path_prefix": "/api/v1/loans",
        "health_check_path": "/health",
        "timeout": 30000,
        "critical": True,
    },
    "document-service": {
        "url": settings.DOCUMENT_SERVICE_URL,
        "path_prefix": "/api/v1/documents",
        "health_check_path": "/health",
        "timeout": 30000,
        "critical": False,
    },
    "notification-service": {
        "url": settings.NOTIFICATION_SERVICE_URL,
        "path_prefix": "/api/v1/notifications",
        "health_check_path": "/health",
        "timeout": 30000,
        "critical": False,
    },
    "audit-service": {
        "url": settings.AUDIT_SERVICE_URL,
        "path_prefix": "/api/v1/audit",
        "health_check_path": "/health",
        "timeout": 30000,
        "critical": False,
    },
}
