"""API Gateway - Main entry point for all client requests."""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import router
from app.middleware import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
    JWTAuthMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlingMiddleware,
)
from app.services import (
    JWTService,
    RateLimitService,
    CircuitBreakerService,
    ServiceDiscovery,
)
from app.clients import ServiceClient
from utils import init_utils, logger

try:
    import uvicorn
except ImportError:  # pragma: no cover - uvicorn optional for ASGI deployments
    uvicorn = None

CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "config"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    # Startup: Initialize utils-service configuration and logging
    init_utils(CONFIG_DIR)
    logger.info(
        f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}"
    )
    logger.info(
        "Environment: %s | Server: %s:%s",
        settings.ENVIRONMENT,
        settings.HOST,
        settings.PORT,
    )
    
    # Initialize services
    jwt_service = JWTService()
    rate_limit_service = RateLimitService(
        per_user_per_minute=settings.RATE_LIMIT_PER_USER_PER_MINUTE,
        per_tenant_per_minute=settings.RATE_LIMIT_PER_TENANT_PER_MINUTE,
        per_ip_per_minute=settings.RATE_LIMIT_PER_IP_PER_MINUTE,
    )
    circuit_breaker = CircuitBreakerService(
        failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        half_open_max_calls=settings.CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS,
    )
    service_discovery = ServiceDiscovery(
        check_interval=settings.HEALTH_CHECK_INTERVAL
    )
    service_client = ServiceClient(timeout=settings.REQUEST_TIMEOUT)
    
    # Store in app state
    app.state.jwt_service = jwt_service
    app.state.rate_limit_service = rate_limit_service
    app.state.circuit_breaker = circuit_breaker
    app.state.service_discovery = service_discovery
    app.state.service_client = service_client
    
    # Start health checks
    await service_discovery.start_health_checks()
    logger.info("Health checks started")
    
    logger.info(f"{settings.SERVICE_NAME} startup complete")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await service_discovery.stop_health_checks()
    await service_discovery.close()
    await service_client.close()
    logger.info(f"{settings.SERVICE_NAME} shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.OPENAPI_TITLE,
    version=settings.SERVICE_VERSION,
    description=settings.OPENAPI_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
    )

# Add custom middleware (order matters - last added is executed first)
# Error handling should be outermost
app.add_middleware(ErrorHandlingMiddleware)
# Security headers
app.add_middleware(SecurityHeadersMiddleware)
# Rate limiting (requires JWT context)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)
# JWT authentication
app.add_middleware(JWTAuthMiddleware)
# Request logging
app.add_middleware(RequestLoggingMiddleware)
# Correlation ID (innermost - sets correlation_id first)
app.add_middleware(CorrelationIdMiddleware)

# Include routers
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint returning service metadata."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
    }

logger.info("FastAPI application configured")


if __name__ == "__main__" and uvicorn:
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT.lower() == "development",
    )
