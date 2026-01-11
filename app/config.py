import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from utils import config, init_utils


# Ensure utils-config reads from the service config directory (respects CONFIG_DIR override)
CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "config"))
init_utils(str(CONFIG_DIR))

def _get_bool(key: str, default: bool) -> bool:
    value = config.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)


def _get_int(key: str, default: int) -> int:
    try:
        return int(config.get(key, default))
    except (TypeError, ValueError):
        return default


def _get_float(key: str, default: float) -> float:
    try:
        return float(config.get(key, default))
    except (TypeError, ValueError):
        return default


class Settings(BaseSettings):
    """API Gateway service settings loaded via utils.config defaults with env overrides."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Service Configuration
    SERVICE_NAME: str = config.get("service.name", "api-gateway")
    SERVICE_VERSION: str = config.get("service.version", "1.0.0")
    ENVIRONMENT: str = config.get("service.environment", "development")
    HOST: str = config.get("server.host", "0.0.0.0")
    PORT: int = _get_int("server.port", 8080)
    WORKERS: int = _get_int("service.workers", 4)
    DEBUG: bool = _get_bool("service.debug", True)

    # Security Configuration
    JWT_SECRET_KEY: str = config.get("jwt.access_secret", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = config.get("jwt.algorithm", "HS256")
    JWT_PUBLIC_KEY_URL: Optional[str] = config.get("jwt.public_key_url")
    API_KEY_HEADER: str = config.get("api_key.header", "X-API-Key")
    AUTHZ_SERVICE_URL: str = config.get("services.authz.url", "http://localhost:8002")
    AUTHZ_SERVICE_TIMEOUT: int = _get_int("services.authz.timeout", 5)
    AUTHZ_SERVICE_RETRY_ATTEMPTS: int = _get_int("services.authz.retry_attempts", 2)

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = _get_bool("rate_limiting.enabled", True)
    RATE_LIMIT_PER_USER_PER_MINUTE: int = _get_int("rate_limiting.max_requests_per_user_per_minute", 1000)
    RATE_LIMIT_PER_TENANT_PER_MINUTE: int = _get_int("rate_limiting.max_requests_per_tenant_per_minute", 100000)
    RATE_LIMIT_PER_IP_PER_MINUTE: int = _get_int("rate_limiting.max_requests_per_ip_per_minute", 10000)
    REDIS_HOST: str = config.get("redis.host", "localhost")
    REDIS_PORT: int = _get_int("redis.port", 6379)
    REDIS_DB: int = _get_int("redis.db", 0)
    REDIS_PASSWORD: Optional[str] = config.get("redis.password")

    # CORS Configuration
    CORS_ENABLED: bool = _get_bool("cors.enabled", True)
    CORS_ORIGINS: list = config.get("cors.origins", ["http://localhost:3000", "http://localhost:8080"])
    CORS_METHODS: list = config.get("cors.methods", ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    CORS_HEADERS: list = config.get("cors.headers", ["*"])

    # External Services Configuration
    AUTH_SERVICE_URL: str = config.get("services.auth.url", "http://localhost:3001")
    AUTH_SERVICE_TIMEOUT: int = _get_int("services.auth.timeout", 5)
    AUTH_SERVICE_RETRY_ATTEMPTS: int = _get_int("services.auth.retry_attempts", 2)

    PROFILE_SERVICE_URL: str = config.get("services.profile.url", "http://localhost:8006")
    PROFILE_SERVICE_TIMEOUT: int = _get_int("services.profile.timeout", 30)
    PROFILE_SERVICE_RETRY_ATTEMPTS: int = _get_int("services.profile.retry_attempts", 3)

    LOAN_SERVICE_URL: str = config.get("services.loan.url", "http://localhost:8005")
    LOAN_SERVICE_TIMEOUT: int = _get_int("services.loan.timeout", 30)
    LOAN_SERVICE_RETRY_ATTEMPTS: int = _get_int("services.loan.retry_attempts", 3)

    DOCUMENT_SERVICE_URL: str = config.get("services.document.url", "http://localhost:8001")
    DOCUMENT_SERVICE_TIMEOUT: int = _get_int("services.document.timeout", 30)
    DOCUMENT_SERVICE_RETRY_ATTEMPTS: int = _get_int("services.document.retry_attempts", 3)

    NOTIFICATION_SERVICE_URL: str = config.get("services.notification.url", "http://localhost:8004")
    NOTIFICATION_SERVICE_TIMEOUT: int = _get_int("services.notification.timeout", 30)
    NOTIFICATION_SERVICE_RETRY_ATTEMPTS: int = _get_int("services.notification.retry_attempts", 3)

    AUDIT_SERVICE_URL: str = config.get("services.audit.url", "http://localhost:8008")
    AUDIT_SERVICE_TIMEOUT: int = _get_int("services.audit.timeout", 30)
    AUDIT_SERVICE_RETRY_ATTEMPTS: int = _get_int("services.audit.retry_attempts", 3)

    # Request Configuration
    MAX_REQUEST_BODY_SIZE: int = _get_int("requests.max_body_size", 10485760)
    MAX_RESPONSE_BODY_SIZE: int = _get_int("requests.max_response_size", 104857600)
    REQUEST_TIMEOUT: int = _get_int("requests.timeout", 30)

    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = _get_int("circuit_breaker.failure_threshold", 5)
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = _get_int("circuit_breaker.timeout_seconds", 60)
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = _get_int("circuit_breaker.success_threshold", 3)

    # Health Check Configuration
    HEALTH_CHECK_INTERVAL: int = _get_int("health_check.interval_seconds", 30)

    # Logging Configuration
    LOG_LEVEL: str = config.get("logging.level", "INFO")
    LOG_FORMAT: str = config.get("logging.format", "json")

    # OpenAPI Configuration
    OPENAPI_TITLE: str = config.get("api_docs.title", "Multi-Finance API Gateway")
    OPENAPI_VERSION: str = config.get("api_docs.version", "1.0.0")
    OPENAPI_DESCRIPTION: str = config.get("api_docs.description", "API Gateway for Multi-Finance User Application")

    # Database Configuration (optional)
    DATABASE_URL: Optional[str] = config.get("database.url")


def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Service Registry for service discovery and configuration
SERVICE_REGISTRY: dict = {
    "auth-service": {
        "url": settings.AUTH_SERVICE_URL,
        "path_prefix": "/api/v1/auth",
        "health_check_path": config.get("services.auth.health_check", "/health"),
        "timeout": settings.AUTH_SERVICE_TIMEOUT,
        "critical": True,
    },
    "authz-service": {
        "url": settings.AUTHZ_SERVICE_URL,
        "path_prefix": "/api/v1/authz",
        "health_check_path": config.get("services.authz.health_check", "/health"),
        "timeout": settings.AUTHZ_SERVICE_TIMEOUT,
        "critical": True,
    },
    "profile-service": {
        "url": settings.PROFILE_SERVICE_URL,
        "path_prefix": "/api/v1/profiles",
        "health_check_path": config.get("services.profile.health_check", "/health"),
        "timeout": settings.PROFILE_SERVICE_TIMEOUT,
        "critical": True,
    },
    "loan-service": {
        "url": settings.LOAN_SERVICE_URL,
        "path_prefix": "/api/v1/loans",
        "health_check_path": config.get("services.loan.health_check", "/health"),
        "timeout": settings.LOAN_SERVICE_TIMEOUT,
        "critical": True,
    },
    "document-service": {
        "url": settings.DOCUMENT_SERVICE_URL,
        "path_prefix": "/api/v1/documents",
        "health_check_path": config.get("services.document.health_check", "/health"),
        "timeout": settings.DOCUMENT_SERVICE_TIMEOUT,
        "critical": False,
    },
    "notification-service": {
        "url": settings.NOTIFICATION_SERVICE_URL,
        "path_prefix": "/api/v1/notifications",
        "health_check_path": config.get("services.notification.health_check", "/health"),
        "timeout": settings.NOTIFICATION_SERVICE_TIMEOUT,
        "critical": False,
    },
    "audit-service": {
        "url": settings.AUDIT_SERVICE_URL,
        "path_prefix": "/api/v1/audit",
        "health_check_path": config.get("services.audit.health_check", "/health"),
        "timeout": settings.AUDIT_SERVICE_TIMEOUT,
        "critical": False,
    },
}
