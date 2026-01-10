"""Middleware for API Gateway."""

import logging
import time
import uuid
from datetime import datetime
from typing import Callable, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.models.request import GatewayRequestContext
from app.models.response import ErrorCode
from app.services.error_service import ErrorService
from app.services.jwt_service import JWTService
from app.services.rate_limit_service import RateLimitService

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and propagate correlation IDs."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Add correlation ID to request."""
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-Id"] = correlation_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Log request and response."""
        start_time = time.time()
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Log request
        logger.info(
            f"Request started: method={request.method} path={request.url.path} "
            f"correlation_id={correlation_id}"
        )

        # Process request
        response = await call_next(request)

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            f"Request completed: method={request.method} path={request.url.path} "
            f"status={response.status_code} latency={latency_ms:.2f}ms "
            f"correlation_id={correlation_id}"
        )

        return response


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication."""

    # Paths that don't require authentication
    EXCLUDED_PATHS = [
        "/health",
        "/healthz",
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    ]

    async def dispatch(self, request: Request, call_next: Callable):
        """Validate JWT token."""
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Get JWT service from app state
        jwt_service = getattr(request.app.state, "jwt_service", None)

        # If no JWT service (e.g., in tests without lifespan), skip auth
        if not jwt_service:
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            correlation_id = getattr(request.state, "correlation_id", None)
            error_response = ErrorService.create_error_response(
                code=ErrorCode.UNAUTHORIZED,
                message="Missing Authorization header",
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=error_response.model_dump(),
            )

        # Validate Bearer token format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            correlation_id = getattr(request.state, "correlation_id", None)
            error_response = ErrorService.create_error_response(
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid Authorization header format",
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=error_response.model_dump(),
            )

        token = parts[1]

        # Validate token
        payload = jwt_service.validate_token(token)
        if not payload:
            correlation_id = getattr(request.state, "correlation_id", None)
            error_response = ErrorService.create_error_response(
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid or expired JWT token",
                correlation_id=correlation_id,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=error_response.model_dump(),
            )

        # Extract user context
        user_id = jwt_service.get_user_id(payload)
        tenant_id = jwt_service.get_tenant_id(payload)
        roles = jwt_service.get_roles(payload)

        # Store in request state
        request.state.user_id = user_id
        request.state.tenant_id = tenant_id
        request.state.roles = roles
        request.state.jwt_payload = payload

        logger.debug(
            f"Authenticated user: {user_id}, tenant: {tenant_id}, roles: {roles}"
        )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""

    # Paths excluded from rate limiting
    EXCLUDED_PATHS = [
        "/health",
        "/healthz",
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    async def dispatch(self, request: Request, call_next: Callable):
        """Apply rate limiting."""
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Get rate limit service from app state
        rate_limit_service = getattr(request.app.state, "rate_limit_service", None)

        # If no rate limit service (e.g., in tests without lifespan), skip rate limiting
        if not rate_limit_service:
            return await call_next(request)

        # Get user context
        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        ip_address = request.client.host if request.client else None

        # Check rate limits
        allowed, remaining, reset_at, limit_type = (
            await rate_limit_service.check_all_limits(
                user_id=user_id, tenant_id=tenant_id, ip_address=ip_address
            )
        )

        if not allowed:
            correlation_id = getattr(request.state, "correlation_id", None)
            error_response = ErrorService.create_error_response(
                code=ErrorCode.RATE_LIMITED,
                message=f"Rate limit exceeded for {limit_type}",
                details={"reset_at": reset_at.isoformat()},
                correlation_id=correlation_id,
            )

            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error_response.model_dump(),
            )
            response.headers["X-Rate-Limit-Remaining"] = "0"
            response.headers["X-Rate-Limit-Reset"] = reset_at.isoformat()

            logger.warning(
                f"Rate limit exceeded: {limit_type} user_id={user_id} "
                f"tenant_id={tenant_id} ip={ip_address}"
            )

            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-Rate-Limit-Remaining"] = str(remaining)
        response.headers["X-Rate-Limit-Reset"] = reset_at.isoformat()

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers to response."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Handle errors and return standardized responses."""
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            # Handle FastAPI HTTPException
            correlation_id = getattr(request.state, "correlation_id", None)
            error_code = ErrorService.map_http_status_to_error_code(e.status_code)
            error_response = ErrorService.create_error_response(
                code=error_code, message=str(e.detail), correlation_id=correlation_id
            )

            ErrorService.log_error(
                error_code=error_code,
                message=str(e.detail),
                correlation_id=correlation_id,
                user_id=getattr(request.state, "user_id", None),
                path=request.url.path,
            )

            return JSONResponse(
                status_code=e.status_code, content=error_response.model_dump()
            )
        except Exception as e:
            # Handle unexpected errors
            correlation_id = getattr(request.state, "correlation_id", None)
            error_response = ErrorService.create_error_response(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred",
                correlation_id=correlation_id,
            )

            ErrorService.log_error(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=str(e),
                correlation_id=correlation_id,
                user_id=getattr(request.state, "user_id", None),
                path=request.url.path,
            )

            logger.exception(f"Unhandled exception: {e}")

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response.model_dump(),
            )
