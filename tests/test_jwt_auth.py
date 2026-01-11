"""Tests for JWT authentication."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import settings


@pytest.mark.asyncio
async def test_missing_authorization_header(client):
    """Test request without authorization header."""
    response = await client.get("/api/v1/discovery")
    assert response.status_code == 401

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Missing Authorization header" in data["error"]["message"]


@pytest.mark.asyncio
async def test_invalid_authorization_format(client):
    """Test request with invalid authorization format."""
    response = await client.get(
        "/api/v1/discovery", headers={"Authorization": "InvalidFormat token123"}
    )
    assert response.status_code == 401

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_invalid_jwt_token(client):
    """Test request with invalid JWT token."""
    response = await client.get(
        "/api/v1/discovery", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Invalid or expired JWT token" in data["error"]["message"]


@pytest.mark.asyncio
async def test_expired_jwt_token(client):
    """Test request with expired JWT token."""
    # Create expired token
    payload = {
        "user_id": "test-user-123",
        "tenant_id": "test-tenant-456",
        "roles": ["user"],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
    }

    expired_token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    response = await client.get(
        "/api/v1/discovery", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_jwt_token(client, auth_headers):
    """Test request with valid JWT token."""
    response = await client.get("/api/v1/discovery", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "services" in data


@pytest.mark.asyncio
async def test_excluded_paths_no_auth(client):
    """Test that excluded paths don't require authentication."""
    excluded_paths = [
        "/health",
        "/healthz",
        "/ready",
        "/docs",
        "/openapi.json",
    ]

    for path in excluded_paths:
        response = await client.get(path)
        # Should not return 401
        assert response.status_code != 401
