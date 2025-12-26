"""FastAPI middleware for request/response logging and request ID tracking."""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.metrics import track_http_request, track_error

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and track request IDs for request correlation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add request ID to context.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response with request ID header
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Add request ID to context variables (for structlog)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Add request ID to request state (for access in route handlers)
        request.state.request_id = request_id

        # Call next middleware/handler
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response details.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response with logging
        """
        # Get request ID from state (set by RequestIDMiddleware)
        request_id = getattr(request.state, "request_id", None)

        # Start timer
        start_time = time.time()

        # Log request
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=request_id,
        )

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code

            # Calculate duration
            duration = time.time() - start_time
            duration_ms = duration * 1000

            # Track HTTP metrics
            endpoint = request.url.path
            # Normalize endpoint (remove IDs, etc.) for better aggregation
            if endpoint.startswith("/chitalishte/"):
                endpoint = "/chitalishte/{id}"
            elif endpoint.startswith("/chitalishte/"):
                endpoint = "/chitalishte/{id}/cards"

            track_http_request(
                method=request.method,
                endpoint=endpoint,
                status=status_code,
                duration=duration,
            )

            # Log successful response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
            )

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            duration_ms = duration * 1000

            # Track error metrics
            endpoint = request.url.path
            if endpoint.startswith("/chitalishte/"):
                endpoint = "/chitalishte/{id}"
            elif endpoint.startswith("/chitalishte/"):
                endpoint = "/chitalishte/{id}/cards"

            track_error(error_type=type(e).__name__, endpoint=endpoint)

            # Track HTTP metrics for error
            track_http_request(
                method=request.method,
                endpoint=endpoint,
                status=500,  # Will be overridden by FastAPI error handler
                duration=duration,
            )

            # Log error
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
                exc_info=True,
            )

            # Re-raise exception (FastAPI will handle it)
            raise
