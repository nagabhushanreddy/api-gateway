"""Rate limiting service using in-memory storage."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RateLimitService:
    """In-memory rate limiting service."""

    def __init__(
        self,
        per_user_per_minute: int = 1000,
        per_tenant_per_minute: int = 100000,
        per_ip_per_minute: int = 10000,
    ):
        """Initialize rate limit service.

        Args:
            per_user_per_minute: Max requests per user per minute
            per_tenant_per_minute: Max requests per tenant per minute
            per_ip_per_minute: Max requests per IP per minute
        """
        self.per_user_per_minute = per_user_per_minute
        self.per_tenant_per_minute = per_tenant_per_minute
        self.per_ip_per_minute = per_ip_per_minute

        # In-memory storage: key -> (count, window_start)
        self._storage: Dict[str, tuple] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self, key: str, limit: int, window_seconds: int = 60
    ) -> tuple[bool, int, datetime]:
        """Check if request is within rate limit.

        Args:
            key: Rate limit key (user_id, tenant_id, ip, etc.)
            limit: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, remaining, reset_at)
        """
        async with self._lock:
            now = datetime.now(timezone.utc)

            if key not in self._storage:
                # First request for this key
                self._storage[key] = (1, now)
                reset_at = now + timedelta(seconds=window_seconds)
                return True, limit - 1, reset_at

            count, window_start = self._storage[key]
            window_end = window_start + timedelta(seconds=window_seconds)

            if now > window_end:
                # Window expired, reset
                self._storage[key] = (1, now)
                reset_at = now + timedelta(seconds=window_seconds)
                return True, limit - 1, reset_at

            if count >= limit:
                # Rate limit exceeded
                reset_at = window_end
                return False, 0, reset_at

            # Increment counter
            self._storage[key] = (count + 1, window_start)
            reset_at = window_end
            return True, limit - (count + 1), reset_at

    async def check_user_rate_limit(self, user_id: str) -> tuple[bool, int, datetime]:
        """Check rate limit for user.

        Args:
            user_id: User ID

        Returns:
            Tuple of (allowed, remaining, reset_at)
        """
        key = f"user:{user_id}"
        return await self.check_rate_limit(key, self.per_user_per_minute)

    async def check_tenant_rate_limit(
        self, tenant_id: str
    ) -> tuple[bool, int, datetime]:
        """Check rate limit for tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tuple of (allowed, remaining, reset_at)
        """
        key = f"tenant:{tenant_id}"
        return await self.check_rate_limit(key, self.per_tenant_per_minute)

    async def check_ip_rate_limit(self, ip_address: str) -> tuple[bool, int, datetime]:
        """Check rate limit for IP address.

        Args:
            ip_address: IP address

        Returns:
            Tuple of (allowed, remaining, reset_at)
        """
        key = f"ip:{ip_address}"
        return await self.check_rate_limit(key, self.per_ip_per_minute)

    async def check_all_limits(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> tuple[bool, int, datetime, str]:
        """Check all applicable rate limits.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            ip_address: IP address

        Returns:
            Tuple of (allowed, remaining, reset_at, limit_type)
        """
        # Check IP limit first (most restrictive)
        if ip_address:
            allowed, remaining, reset_at = await self.check_ip_rate_limit(ip_address)
            if not allowed:
                return False, remaining, reset_at, "ip"

        # Check user limit
        if user_id:
            allowed, remaining, reset_at = await self.check_user_rate_limit(user_id)
            if not allowed:
                return False, remaining, reset_at, "user"

        # Check tenant limit
        if tenant_id:
            allowed, remaining, reset_at = await self.check_tenant_rate_limit(tenant_id)
            if not allowed:
                return False, remaining, reset_at, "tenant"

        # All limits passed
        return (
            True,
            remaining if user_id else 0,
            reset_at if user_id else datetime.now(timezone.utc),
            "none",
        )

    async def get_rate_limit_status(self, key: str) -> Optional[Dict]:
        """Get current rate limit status for a key.

        Args:
            key: Rate limit key

        Returns:
            Dict with status or None
        """
        async with self._lock:
            if key not in self._storage:
                return None

            count, window_start = self._storage[key]
            window_end = window_start + timedelta(seconds=60)

            return {
                "key": key,
                "current_usage": count,
                "window_start_at": window_start.isoformat(),
                "reset_at": window_end.isoformat(),
            }

    async def reset_rate_limit(self, key: str):
        """Reset rate limit for a key.

        Args:
            key: Rate limit key
        """
        async with self._lock:
            if key in self._storage:
                del self._storage[key]
                logger.info(f"Reset rate limit for key: {key}")

    async def cleanup_expired(self):
        """Clean up expired rate limit entries."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = []

            for key, (count, window_start) in self._storage.items():
                window_end = window_start + timedelta(seconds=60)
                if now > window_end:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._storage[key]

            if expired_keys:
                logger.info(
                    f"Cleaned up {len(expired_keys)} expired rate limit entries"
                )
