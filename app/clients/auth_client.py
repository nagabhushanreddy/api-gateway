"""Auth service client for JWT validation."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class AuthClient:
    """Client for auth service interactions."""

    def __init__(self, auth_service_url: str, timeout: int = 5):
        """Initialize auth client.

        Args:
            auth_service_url: Base URL of auth service
            timeout: Request timeout in seconds
        """
        self.auth_service_url = auth_service_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self._public_key_cache: Optional[str] = None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_public_key(self) -> Optional[str]:
        """Fetch JWT public key from auth service.

        Returns:
            Public key string or None if unavailable
        """
        if self._public_key_cache:
            return self._public_key_cache

        try:
            url = f"{self.auth_service_url}/api/v1/auth/public-key"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                self._public_key_cache = data.get("public_key")
                logger.info("Successfully fetched JWT public key from auth service")
                return self._public_key_cache
            else:
                logger.warning(
                    f"Failed to fetch public key: status={response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error fetching public key from auth service: {e}")
            return None

    def clear_public_key_cache(self):
        """Clear cached public key."""
        self._public_key_cache = None
