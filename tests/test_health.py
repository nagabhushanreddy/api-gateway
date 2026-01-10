"""Tests for health check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test basic health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_healthz_endpoint(client):
    """Test Kubernetes liveness probe endpoint."""
    response = await client.get("/healthz")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "OK"


@pytest.mark.asyncio
async def test_ready_endpoint(client):
    """Test Kubernetes readiness probe endpoint."""
    response = await client.get("/ready")

    # May return 200 or 503 depending on service health
    assert response.status_code in [200, 503]

    data = response.json()
    assert "ready" in data
    assert "services" in data
    assert isinstance(data["services"], dict)
