"""Error handling and standardization service."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.models.response import ErrorCode, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class ErrorService:
    """Service for error handling and standardization."""

    @staticmethod
    def create_error_response(
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> ErrorResponse:
        """Create standardized error response.

        Args:
            code: Error code
            message: Error message
            details: Additional error details
            correlation_id: Request correlation ID

        Returns:
            ErrorResponse object
        """
        error_detail = ErrorDetail(code=code, message=message, details=details)

        metadata = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if correlation_id:
            metadata["correlation_id"] = correlation_id

        return ErrorResponse(error=error_detail, metadata=metadata)

    @staticmethod
    def map_http_status_to_error_code(status_code: int) -> ErrorCode:
        """Map HTTP status code to error code.

        Args:
            status_code: HTTP status code

        Returns:
            ErrorCode enum
        """
        mapping = {
            400: ErrorCode.INVALID_REQUEST,
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            429: ErrorCode.RATE_LIMITED,
            500: ErrorCode.INTERNAL_SERVER_ERROR,
            502: ErrorCode.SERVICE_UNAVAILABLE,
            503: ErrorCode.SERVICE_UNAVAILABLE,
            504: ErrorCode.REQUEST_TIMEOUT,
        }
        return mapping.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR)

    @staticmethod
    def translate_service_error(
        status_code: int,
        service_response: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> ErrorResponse:
        """Translate service error to standardized format.

        Args:
            status_code: HTTP status code from service
            service_response: Response body from service
            correlation_id: Request correlation ID

        Returns:
            Standardized ErrorResponse
        """
        error_code = ErrorService.map_http_status_to_error_code(status_code)

        # Try to extract error message from service response
        message = "An error occurred"
        if isinstance(service_response, dict):
            message = (
                service_response.get("error", {}).get("message")
                or service_response.get("message")
                or service_response.get("detail")
                or message
            )

        return ErrorService.create_error_response(
            code=error_code, message=message, correlation_id=correlation_id
        )

    @staticmethod
    def log_error(
        error_code: ErrorCode,
        message: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log error with context.

        Args:
            error_code: Error code
            message: Error message
            correlation_id: Request correlation ID
            user_id: User ID
            path: Request path
            details: Additional details
        """
        log_data = {
            "error_code": error_code.value,
            "message": message,
        }

        if correlation_id:
            log_data["correlation_id"] = correlation_id
        if user_id:
            log_data["user_id"] = user_id
        if path:
            log_data["path"] = path
        if details:
            log_data["details"] = details

        logger.error(f"Error: {log_data}")
