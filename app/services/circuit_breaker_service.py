"""Circuit breaker service for fault tolerance."""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for a single service."""

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ):
        """Initialize circuit breaker.

        Args:
            service_name: Name of the service
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Max calls in half-open state
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

    async def call(self) -> bool:
        """Check if call is allowed.

        Returns:
            True if call is allowed, False if circuit is open
        """
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self.last_failure_time:
                    elapsed = (
                        datetime.utcnow() - self.last_failure_time
                    ).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        logger.info(
                            f"Circuit breaker for {self.service_name} entering half-open state"
                        )
                        self.state = CircuitState.HALF_OPEN
                        self.half_open_calls = 0
                        return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False

            return True

    async def record_success(self):
        """Record successful call."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                # If all half-open calls succeed, close circuit
                if self.success_count >= self.half_open_max_calls:
                    logger.info(
                        f"Circuit breaker for {self.service_name} closing (recovered)"
                    )
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.half_open_calls = 0
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                if self.failure_count > 0:
                    self.failure_count = 0

    async def record_failure(self):
        """Record failed call."""
        async with self._lock:
            self.last_failure_time = datetime.utcnow()

            if self.state == CircuitState.HALF_OPEN:
                # Failure in half-open state, reopen circuit
                logger.warning(
                    f"Circuit breaker for {self.service_name} reopening (recovery failed)"
                )
                self.state = CircuitState.OPEN
                self.success_count = 0
                self.half_open_calls = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    logger.error(
                        f"Circuit breaker for {self.service_name} opening "
                        f"(threshold: {self.failure_threshold})"
                    )
                    self.state = CircuitState.OPEN

    def get_state(self) -> Dict:
        """Get circuit breaker state.

        Returns:
            Dict with state information
        """
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
        }


class CircuitBreakerService:
    """Service managing circuit breakers for all downstream services."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ):
        """Initialize circuit breaker service.

        Args:
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Max calls in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service.

        Args:
            service_name: Service name

        Returns:
            CircuitBreaker instance
        """
        if service_name not in self._breakers:
            self._breakers[service_name] = CircuitBreaker(
                service_name=service_name,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
                half_open_max_calls=self.half_open_max_calls,
            )
        return self._breakers[service_name]

    async def is_call_allowed(self, service_name: str) -> bool:
        """Check if call to service is allowed.

        Args:
            service_name: Service name

        Returns:
            True if allowed, False if circuit is open
        """
        breaker = self.get_breaker(service_name)
        return await breaker.call()

    async def record_success(self, service_name: str):
        """Record successful call to service.

        Args:
            service_name: Service name
        """
        breaker = self.get_breaker(service_name)
        await breaker.record_success()

    async def record_failure(self, service_name: str):
        """Record failed call to service.

        Args:
            service_name: Service name
        """
        breaker = self.get_breaker(service_name)
        await breaker.record_failure()

    def get_all_states(self) -> Dict[str, Dict]:
        """Get state of all circuit breakers.

        Returns:
            Dict mapping service name to state
        """
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}
