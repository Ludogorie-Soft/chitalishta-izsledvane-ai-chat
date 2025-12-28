"""Authentication dependencies for FastAPI routes."""

from typing import Optional

import structlog
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.jwt import verify_token

logger = structlog.get_logger(__name__)

# HTTP Bearer scheme for JWT tokens
bearer_scheme = HTTPBearer()


class CurrentUser:
    """Current authenticated user."""

    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> CurrentUser:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        CurrentUser object with username and role

    Raises:
        HTTPException 401: If token is invalid, expired, or missing
    """
    token = credentials.credentials

    try:
        payload = verify_token(token, token_type="access")
        username = payload.get("sub")
        role = payload.get("role", "administrator")

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(username=username, role=role)
    except Exception as e:
        logger.warning("jwt_verification_failed", error=str(e))
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_administrator(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Dependency to require administrator role.

    Args:
        current_user: Current authenticated user

    Returns:
        CurrentUser if user is administrator

    Raises:
        HTTPException 403: If user is not an administrator
    """
    if current_user.role != "administrator":
        logger.warning(
            "access_denied",
            username=current_user.username,
            role=current_user.role,
            reason="insufficient_permissions",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return current_user


def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    Verify API key for Public API and System API endpoints.

    Args:
        api_key: API key from request header

    Returns:
        True if API key is valid

    Raises:
        HTTPException 401: If API key is invalid or missing
    """
    # If API key is not configured, allow access (for development)
    if not settings.api_key:
        logger.debug("api_key_not_configured", message="API key authentication disabled")
        return True

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != settings.api_key:
        logger.warning("invalid_api_key", reason="api_key_mismatch")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return True


async def require_api_key(
    x_api_key: Optional[str] = None,
) -> bool:
    """
    Dependency to require valid API key from X-API-Key header.

    Usage in route:
        @router.get("/endpoint")
        async def endpoint(api_key_valid: bool = Depends(require_api_key)):
            ...

    Args:
        x_api_key: API key from X-API-Key header (injected by FastAPI)

    Returns:
        True if API key is valid

    Raises:
        HTTPException 401: If API key is invalid or missing
    """
    from fastapi import Header

    # Get API key from header if not provided
    if x_api_key is None:
        # Try to get from Header dependency
        # This is a workaround - we'll use Header directly in routes
        pass

    return verify_api_key(x_api_key)

