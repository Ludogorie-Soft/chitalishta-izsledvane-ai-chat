"""FastAPI middleware for request/response logging and request ID tracking."""

import base64
import json
import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.metrics import track_http_request, track_error
from app.db.database import SessionLocal
from app.services.rate_limiter import AbuseDetected, RateLimitExceeded, RateLimiter

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


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting and abuse protection."""

    # Endpoints that should be rate limited
    RATE_LIMITED_ENDPOINTS = ["/chat", "/chat/stream"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limits and abuse protection before processing request.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response (429 if rate limited, 403 if abuse detected, or normal response)
        """
        # Only apply to rate-limited endpoints
        if request.url.path not in self.RATE_LIMITED_ENDPOINTS:
            return await call_next(request)

        # Only apply to POST requests
        if request.method != "POST":
            return await call_next(request)

        # Get database session
        db = SessionLocal()
        try:
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            if not client_ip or client_ip == "unknown":
                # Try to get from X-Forwarded-For header (for reverse proxy)
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    client_ip = forwarded_for.split(",")[0].strip()

            # Get user agent
            user_agent = request.headers.get("user-agent")

            # Get request body for abuse detection
            # Note: We read the body here for abuse detection, then re-create it for FastAPI
            request_body = None
            if request.url.path in self.RATE_LIMITED_ENDPOINTS:
                try:
                    body_bytes = await request.body()
                    if body_bytes:
                        request_body = body_bytes.decode("utf-8", errors="ignore")
                        # Re-create request body for downstream handlers
                        # (FastAPI needs the body to be available)
                        async def receive():
                            return {"type": "http.request", "body": body_bytes}

                        request._receive = receive
                except Exception as e:
                    # If body reading fails, continue without body-based abuse detection
                    logger.debug("failed_to_read_request_body", error=str(e))
                    request_body = None

            # Initialize rate limiter
            rate_limiter = RateLimiter(db)

            try:
                # Check abuse protection first (before rate limiting)
                rate_limiter.check_abuse(
                    identifier=client_ip,
                    identifier_type="ip",
                    endpoint=request.url.path,
                    method=request.method,
                    request_body=request_body,
                    user_agent=user_agent,
                )

                # Check IP-based rate limit
                rate_limiter.check_rate_limit(
                    identifier=client_ip,
                    identifier_type="ip",
                    endpoint=request.url.path,
                    method=request.method,
                )

            except RateLimitExceeded as e:
                # Return 429 Too Many Requests
                retry_after = e.retry_after
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Превишен е лимитът за заявки. Моля, опитайте отново след {retry_after} секунди.",
                        "retry_after": retry_after,
                        "limit_type": e.limit_type,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            except AbuseDetected as e:
                # Return 403 Forbidden
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "abuse_detected",
                        "message": "Заявката е блокирана поради подозрителна активност.",
                        "abuse_type": e.abuse_type,
                    },
                )

            # Request is allowed, proceed
            return await call_next(request)

        finally:
            db.close()


class SwaggerUIAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to protect Swagger UI with HTTP Basic Authentication."""

    # Endpoints that require Swagger UI authentication
    PROTECTED_ENDPOINTS = ["/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check HTTP Basic Authentication for Swagger UI endpoints.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response (401 if unauthorized, or normal response)
        """
        # Only apply to Swagger UI endpoints
        if request.url.path not in self.PROTECTED_ENDPOINTS:
            return await call_next(request)

        # Check if Swagger UI auth is enabled
        if not settings.swagger_ui_username or not settings.swagger_ui_password:
            # Auth is disabled, allow access
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._unauthorized_response()

        # Parse Basic Auth
        try:
            # Remove "Basic " prefix
            if not auth_header.startswith("Basic "):
                return self._unauthorized_response()

            # Decode base64 credentials
            encoded_credentials = auth_header[6:]  # Remove "Basic "
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)

            # Verify credentials
            if (
                username == settings.swagger_ui_username
                and password == settings.swagger_ui_password
            ):
                # Authentication successful
                return await call_next(request)
            else:
                return self._unauthorized_response()

        except Exception as e:
            logger.debug("swagger_ui_auth_error", error=str(e))
            return self._unauthorized_response()

    @staticmethod
    def _unauthorized_response() -> Response:
        """Return 401 Unauthorized response with WWW-Authenticate header."""
        return Response(
            status_code=401,
            content="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm=\"Swagger UI\""},
        )
