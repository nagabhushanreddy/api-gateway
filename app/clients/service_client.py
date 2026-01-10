"""Generic HTTP client for routing requests to downstream services."""

import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class ServiceClient:
    """Generic HTTP client for downstream service communication."""

    def __init__(self, timeout: int = 30):
        """Initialize service client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def forward_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
    ) -> httpx.Response:
        """Forward request to downstream service.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to forward to
            headers: Request headers
            params: Query parameters
            json_data: JSON body
            data: Raw body data

        Returns:
            httpx.Response from downstream service

        Raises:
            HTTPException: If request fails
        """
        try:
            logger.info(f"Forwarding {method} request to {url}")

            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                content=data,
            )

            logger.info(
                f"Received response from {url}: status={response.status_code}, "
                f"latency={response.elapsed.total_seconds() * 1000:.2f}ms"
            )

            return response

        except httpx.TimeoutException:
            logger.error(f"Request to {url} timed out")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request to downstream service timed out",
            )
        except httpx.RequestError as e:
            logger.error(f"Request to {url} failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to downstream service: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error forwarding request to {url}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error: {str(e)}",
            )

    async def health_check(self, url: str) -> bool:
        """Check if a service is healthy.

        Args:
            url: Health check URL

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {url}: {e}")
            return False
