"""Pytest configuration and fixtures."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.clients import ServiceClient
from app.config import settings
from app.services import (
    CircuitBreakerService,
    JWTService,
    RateLimitService,
    ServiceDiscovery,
)
from main import app


@pytest_asyncio.fixture
async def client():
    """Create test client with app lifespan context and initialized services."""
    # Initialize services in app state for proper testing
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
    service_discovery = ServiceDiscovery(check_interval=settings.HEALTH_CHECK_INTERVAL)
    service_client = ServiceClient(timeout=settings.REQUEST_TIMEOUT)

    # Store in app state
    app.state.jwt_service = jwt_service
    app.state.rate_limit_service = rate_limit_service
    app.state.circuit_breaker = circuit_breaker
    app.state.service_discovery = service_discovery
    app.state.service_client = service_client

    # Use ASGITransport to properly handle lifespan events
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def sample_jwt_token():
    """Generate a sample JWT token for testing."""
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    payload = {
        "user_id": "test-user-123",
        "tenant_id": "test-tenant-456",
        "roles": ["user", "customer"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token


@pytest.fixture
def auth_headers(sample_jwt_token):
    """Create authorization headers with JWT token."""
    return {"Authorization": f"Bearer {sample_jwt_token}"}
