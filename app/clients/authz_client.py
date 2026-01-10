"""AuthZ service client for authorization checks."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class AuthzClient:
    """Client for authz service interactions."""

    def __init__(self, authz_service_url: str, timeout: int = 5):
        """Initialize authz client.

        Args:
            authz_service_url: Base URL of authz service
            timeout: Request timeout in seconds
        """
        self.authz_service_url = authz_service_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def check_permission(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        action: str,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Check if user has permission for action.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            resource: Resource to access
            action: Action to perform
            correlation_id: Request correlation ID

        Returns:
            True if authorized, False otherwise
        """
        try:
            url = f"{self.authz_service_url}/api/v1/authz/check"
            headers = {}
            if correlation_id:
                headers["X-Correlation-Id"] = correlation_id

            payload = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "resource": resource,
                "action": action,
            }

            response = await self.client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return data.get("authorized", False)
            else:
                logger.warning(
                    f"Authorization check failed: status={response.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"Error checking authorization: {e}")
            # Fail closed - deny access on error
            return False

    async def has_role(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Check if user has specific role.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            role: Role name to check
            correlation_id: Request correlation ID

        Returns:
            True if user has role, False otherwise
        """
        try:
            url = f"{self.authz_service_url}/api/v1/authz/roles/check"
            headers = {}
            if correlation_id:
                headers["X-Correlation-Id"] = correlation_id

            payload = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "role": role,
            }

            response = await self.client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return data.get("has_role", False)
            else:
                logger.warning(f"Role check failed: status={response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error checking role: {e}")
            # Fail closed - deny access on error
            return False
