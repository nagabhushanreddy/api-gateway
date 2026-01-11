"""JWT validation service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)


class JWTService:
    """Service for JWT token validation and claims extraction."""

    def __init__(self, secret_key: str = None, algorithm: str = None):
        """Initialize JWT service.

        Args:
            secret_key: JWT secret key
            algorithm: JWT algorithm (default: HS256)
        """
        self.secret_key = secret_key or settings.JWT_SECRET_KEY
        self.algorithm = algorithm or settings.JWT_ALGORITHM

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and extract claims.

        Args:
            token: JWT token string

        Returns:
            Dict of claims if valid, None otherwise
        """
        try:
            # Decode and validate token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check expiration
            exp = payload.get("exp")
            if exp:
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                if datetime.now(timezone.utc) > exp_datetime:
                    logger.warning("Token has expired")
                    return None

            # Validate required claims
            if not payload.get("user_id"):
                logger.warning("Token missing user_id claim")
                return None

            logger.info(
                f"Successfully validated token for user: {payload.get('user_id')}"
            )
            return payload

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating JWT: {e}")
            return None

    def extract_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract claims from JWT without validation (for debugging).

        Args:
            token: JWT token string

        Returns:
            Dict of claims or None
        """
        try:
            # Decode without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.error(f"Failed to extract claims: {e}")
            return None

    def get_user_id(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract user_id from token payload.

        Args:
            payload: Token payload

        Returns:
            User ID or None
        """
        return payload.get("user_id") or payload.get("sub")

    def get_tenant_id(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract tenant_id from token payload.

        Args:
            payload: Token payload

        Returns:
            Tenant ID or None
        """
        return payload.get("tenant_id")

    def get_roles(self, payload: Dict[str, Any]) -> List[str]:
        """Extract roles from token payload.

        Args:
            payload: Token payload

        Returns:
            List of roles
        """
        roles = payload.get("roles", [])
        if isinstance(roles, str):
            return [roles]
        return roles if isinstance(roles, list) else []

    def is_token_near_expiry(
        self, payload: Dict[str, Any], threshold_minutes: int = 5
    ) -> bool:
        """Check if token is near expiry.

        Args:
            payload: Token payload
            threshold_minutes: Minutes before expiry to consider "near"

        Returns:
            True if token expires within threshold
        """
        exp = payload.get("exp")
        if not exp:
            return False

        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        threshold = datetime.now(timezone.utc) + timedelta(minutes=threshold_minutes)

        return exp_datetime <= threshold
