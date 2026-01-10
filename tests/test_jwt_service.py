"""Tests for JWT service."""

from datetime import datetime, timedelta

import pytest
from jose import jwt

from app.config import settings
from app.services.jwt_service import JWTService


@pytest.fixture
def jwt_service():
    """Create JWT service instance."""
    return JWTService()


def test_validate_valid_token(jwt_service):
    """Test validation of valid JWT token."""
    payload = {
        "user_id": "test-user-123",
        "tenant_id": "test-tenant-456",
        "roles": ["user", "admin"],
        "exp": datetime.utcnow() + timedelta(hours=1),
    }

    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    result = jwt_service.validate_token(token)
    assert result is not None
    assert result["user_id"] == "test-user-123"
    assert result["tenant_id"] == "test-tenant-456"


def test_validate_expired_token(jwt_service):
    """Test validation of expired JWT token."""
    payload = {
        "user_id": "test-user-123",
        "exp": datetime.utcnow() - timedelta(hours=1),
    }

    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    result = jwt_service.validate_token(token)
    assert result is None


def test_validate_invalid_token(jwt_service):
    """Test validation of invalid JWT token."""
    result = jwt_service.validate_token("invalid.token.here")
    assert result is None


def test_get_user_id(jwt_service):
    """Test extracting user_id from payload."""
    payload = {"user_id": "user-123"}
    assert jwt_service.get_user_id(payload) == "user-123"

    payload = {"sub": "user-456"}
    assert jwt_service.get_user_id(payload) == "user-456"


def test_get_tenant_id(jwt_service):
    """Test extracting tenant_id from payload."""
    payload = {"tenant_id": "tenant-789"}
    assert jwt_service.get_tenant_id(payload) == "tenant-789"

    payload = {}
    assert jwt_service.get_tenant_id(payload) is None


def test_get_roles(jwt_service):
    """Test extracting roles from payload."""
    payload = {"roles": ["user", "admin"]}
    assert jwt_service.get_roles(payload) == ["user", "admin"]

    payload = {"roles": "user"}
    assert jwt_service.get_roles(payload) == ["user"]

    payload = {}
    assert jwt_service.get_roles(payload) == []


def test_is_token_near_expiry(jwt_service):
    """Test checking if token is near expiry."""
    # Token expiring in 2 minutes
    payload = {"exp": (datetime.utcnow() + timedelta(minutes=2)).timestamp()}
    assert jwt_service.is_token_near_expiry(payload, threshold_minutes=5) is True

    # Token expiring in 10 minutes
    payload = {"exp": (datetime.utcnow() + timedelta(minutes=10)).timestamp()}
    assert jwt_service.is_token_near_expiry(payload, threshold_minutes=5) is False
