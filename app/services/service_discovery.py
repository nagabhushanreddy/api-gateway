"""Service discovery and health checking."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from app.clients.service_client import ServiceClient
from app.config import SERVICE_REGISTRY

logger = logging.getLogger(__name__)


class ServiceHealth:
    """Health status for a service."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.status = "unknown"  # healthy, degraded, unhealthy, unknown
        self.last_check_at: Optional[datetime] = None
        self.response_time_ms: Optional[int] = None
        self.error: Optional[str] = None
        self.consecutive_failures = 0


class ServiceDiscovery:
    """Service discovery and health monitoring."""

    def __init__(self, check_interval: int = 30):
        """Initialize service discovery.

        Args:
            check_interval: Health check interval in seconds
        """
        self.check_interval = check_interval
        self.service_health: Dict[str, ServiceHealth] = {}
        self.service_client = ServiceClient(timeout=5)
        self._health_check_task: Optional[asyncio.Task] = None

        # Initialize health status for all services
        for service_name in SERVICE_REGISTRY.keys():
            self.service_health[service_name] = ServiceHealth(service_name)

    async def start_health_checks(self):
        """Start periodic health checks."""
        logger.info("Starting periodic health checks")
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_checks(self):
        """Stop periodic health checks."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped periodic health checks")

    async def _health_check_loop(self):
        """Background loop for health checks."""
        while True:
            try:
                await self.check_all_services()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def check_service_health(self, service_name: str) -> bool:
        """Check health of a specific service.

        Args:
            service_name: Service name

        Returns:
            True if healthy, False otherwise
        """
        if service_name not in SERVICE_REGISTRY:
            logger.warning(f"Unknown service: {service_name}")
            return False

        service_config = SERVICE_REGISTRY[service_name]
        health_url = f"{service_config['url']}{service_config.get('health_check_path', '/health')}"

        health = self.service_health.get(service_name)
        if not health:
            health = ServiceHealth(service_name)
            self.service_health[service_name] = health

        try:
            start_time = datetime.utcnow()
            is_healthy = await self.service_client.health_check(health_url)
            end_time = datetime.utcnow()

            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            if is_healthy:
                health.status = "healthy"
                health.consecutive_failures = 0
                health.error = None
                logger.debug(
                    f"Service {service_name} is healthy (latency: {response_time_ms}ms)"
                )
            else:
                health.consecutive_failures += 1
                health.status = (
                    "unhealthy" if health.consecutive_failures >= 3 else "degraded"
                )
                health.error = "Health check returned non-200 status"
                logger.warning(
                    f"Service {service_name} health check failed "
                    f"(failures: {health.consecutive_failures})"
                )

            health.last_check_at = end_time
            health.response_time_ms = response_time_ms

            return is_healthy

        except Exception as e:
            health.consecutive_failures += 1
            health.status = (
                "unhealthy" if health.consecutive_failures >= 3 else "degraded"
            )
            health.error = str(e)
            health.last_check_at = datetime.utcnow()

            logger.error(
                f"Error checking health of {service_name}: {e} "
                f"(failures: {health.consecutive_failures})"
            )
            return False

    async def check_all_services(self):
        """Check health of all registered services."""
        tasks = [
            self.check_service_health(service_name)
            for service_name in SERVICE_REGISTRY.keys()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get service URL.

        Args:
            service_name: Service name

        Returns:
            Service URL or None
        """
        service_config = SERVICE_REGISTRY.get(service_name)
        return service_config["url"] if service_config else None

    def get_service_by_path(self, path: str) -> Optional[tuple[str, str]]:
        """Get service name and URL by request path.

        Args:
            path: Request path (e.g., /api/v1/auth/login)

        Returns:
            Tuple of (service_name, service_url) or None
        """
        for service_name, config in SERVICE_REGISTRY.items():
            prefix = config["path_prefix"]
            if path.startswith(prefix):
                return service_name, config["url"]
        return None

    def is_service_healthy(self, service_name: str) -> bool:
        """Check if service is healthy.

        Args:
            service_name: Service name

        Returns:
            True if healthy, False otherwise
        """
        health = self.service_health.get(service_name)
        return health.status == "healthy" if health else False

    def is_service_critical(self, service_name: str) -> bool:
        """Check if service is critical.

        Args:
            service_name: Service name

        Returns:
            True if critical, False otherwise
        """
        service_config = SERVICE_REGISTRY.get(service_name)
        return service_config.get("critical", True) if service_config else False

    def get_all_health_status(self) -> Dict[str, Dict]:
        """Get health status of all services.

        Returns:
            Dict mapping service name to health status
        """
        return {
            name: {
                "service_name": health.service_name,
                "status": health.status,
                "last_check_at": (
                    health.last_check_at.isoformat() if health.last_check_at else None
                ),
                "response_time_ms": health.response_time_ms,
                "error": health.error,
                "consecutive_failures": health.consecutive_failures,
            }
            for name, health in self.service_health.items()
        }

    def are_critical_services_healthy(self) -> bool:
        """Check if all critical services are healthy.

        Returns:
            True if all critical services are healthy, False otherwise
        """
        for service_name, config in SERVICE_REGISTRY.items():
            if config.get("critical", True):
                health = self.service_health.get(service_name)
                if not health or health.status != "healthy":
                    return False
        return True

    async def close(self):
        """Clean up resources."""
        await self.stop_health_checks()
        await self.service_client.close()
