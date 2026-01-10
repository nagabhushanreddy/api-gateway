"""Tests for rate limiting service."""

from datetime import datetime

import pytest

from app.services.rate_limit_service import RateLimitService


@pytest.fixture
def rate_limit_service():
    """Create rate limit service instance."""
    return RateLimitService(
        per_user_per_minute=10, per_tenant_per_minute=100, per_ip_per_minute=50
    )


@pytest.mark.asyncio
async def test_first_request_allowed(rate_limit_service):
    """Test that first request is allowed."""
    allowed, remaining, reset_at = await rate_limit_service.check_rate_limit(
        "test-key", 10
    )

    assert allowed is True
    assert remaining == 9
    assert isinstance(reset_at, datetime)


@pytest.mark.asyncio
async def test_rate_limit_exceeded(rate_limit_service):
    """Test that rate limit is enforced."""
    key = "test-key"
    limit = 5

    # Make 5 requests (should all be allowed)
    for i in range(5):
        allowed, remaining, reset_at = await rate_limit_service.check_rate_limit(
            key, limit
        )
        assert allowed is True
        assert remaining == limit - (i + 1)

    # 6th request should be blocked
    allowed, remaining, reset_at = await rate_limit_service.check_rate_limit(key, limit)
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_user_rate_limit(rate_limit_service):
    """Test per-user rate limiting."""
    user_id = "user-123"

    # First request allowed
    allowed, remaining, reset_at = await rate_limit_service.check_user_rate_limit(
        user_id
    )
    assert allowed is True
    assert remaining == 9


@pytest.mark.asyncio
async def test_tenant_rate_limit(rate_limit_service):
    """Test per-tenant rate limiting."""
    tenant_id = "tenant-456"

    # First request allowed
    allowed, remaining, reset_at = await rate_limit_service.check_tenant_rate_limit(
        tenant_id
    )
    assert allowed is True
    assert remaining == 99


@pytest.mark.asyncio
async def test_ip_rate_limit(rate_limit_service):
    """Test per-IP rate limiting."""
    ip_address = "192.168.1.1"

    # First request allowed
    allowed, remaining, reset_at = await rate_limit_service.check_ip_rate_limit(
        ip_address
    )
    assert allowed is True
    assert remaining == 49


@pytest.mark.asyncio
async def test_check_all_limits(rate_limit_service):
    """Test checking all rate limits."""
    allowed, remaining, reset_at, limit_type = (
        await rate_limit_service.check_all_limits(
            user_id="user-123", tenant_id="tenant-456", ip_address="192.168.1.1"
        )
    )

    assert allowed is True
    assert isinstance(reset_at, datetime)
    assert limit_type in ["ip", "user", "tenant", "none"]


@pytest.mark.asyncio
async def test_get_rate_limit_status(rate_limit_service):
    """Test getting rate limit status."""
    key = "test-key"

    # Make a request first
    await rate_limit_service.check_rate_limit(key, 10)

    # Get status
    status = await rate_limit_service.get_rate_limit_status(key)

    assert status is not None
    assert status["key"] == key
    assert status["current_usage"] == 1
    assert "window_start_at" in status
    assert "reset_at" in status


@pytest.mark.asyncio
async def test_reset_rate_limit(rate_limit_service):
    """Test resetting rate limit."""
    key = "test-key"

    # Make some requests
    await rate_limit_service.check_rate_limit(key, 10)
    await rate_limit_service.check_rate_limit(key, 10)

    # Reset
    await rate_limit_service.reset_rate_limit(key)

    # Next request should be treated as first
    allowed, remaining, reset_at = await rate_limit_service.check_rate_limit(key, 10)
    assert allowed is True
    assert remaining == 9
