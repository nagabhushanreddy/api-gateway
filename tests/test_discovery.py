"""Tests for discovery endpoint."""

import pytest


@pytest.mark.asyncio
async def test_discovery_endpoint(client, auth_headers):
    """Test service discovery endpoint."""
    response = await client.get("/api/v1/discovery", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "services" in data
    assert "authentication_required" in data
    assert "rate_limits" in data

    assert data["authentication_required"] is True
    assert isinstance(data["services"], list)
    assert isinstance(data["rate_limits"], dict)


@pytest.mark.asyncio
async def test_discovery_returns_service_info(client, auth_headers):
    """Test that discovery endpoint returns service information."""
    response = await client.get("/api/v1/discovery", headers=auth_headers)
    data = response.json()

    services = data["services"]
    assert len(services) > 0

    # Check first service has required fields
    service = services[0]
    assert "name" in service
    assert "description" in service
    assert "base_path" in service
    assert "status" in service
    assert "version" in service


@pytest.mark.asyncio
async def test_discovery_rate_limits_info(client, auth_headers):
    """Test that discovery endpoint returns rate limit information."""
    response = await client.get("/api/v1/discovery", headers=auth_headers)
    data = response.json()

    rate_limits = data["rate_limits"]
    assert "per_user_per_minute" in rate_limits
    assert "per_tenant_per_minute" in rate_limits
    assert "per_ip_per_minute" in rate_limits

    assert rate_limits["per_user_per_minute"] > 0
    assert rate_limits["per_tenant_per_minute"] > 0
    assert rate_limits["per_ip_per_minute"] > 0
