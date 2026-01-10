"""API Gateway - Main entry point for all client requests."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

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

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    
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
    version=settings.OPENAPI_VERSION,
    description=settings.OPENAPI_DESCRIPTION,
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

logger.info("FastAPI application configured")

