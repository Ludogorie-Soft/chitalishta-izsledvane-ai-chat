"""API endpoints for authentication."""

from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
import bcrypt
from sqlalchemy.orm import Session

from app.api.auth_schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenResponse,
)
from app.core.config import settings
from app.core.jwt import create_access_token, create_refresh_token, verify_token
from app.db.database import get_db
from app.db.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a bcrypt hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hash (as string)

    Returns:
        True if password matches, False otherwise
    """
    try:
        # Encode both to bytes
        password_bytes = plain_password.encode("utf-8")
        # Truncate if longer than 72 bytes (bcrypt limit)
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]

        hash_bytes = hashed_password.encode("utf-8")

        # Use bcrypt.checkpw to verify
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        logger.warning("password_verification_error", error=str(e))
        return False


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT tokens.

    Authenticates against the users table in the database.
    Returns both access token (30 minutes) and refresh token (7 days).

    Args:
        request: Login request with username and password
        db: Database session

    Returns:
        TokenResponse with access_token and refresh_token

    Raises:
        HTTPException 401: If credentials are invalid or user is inactive
    """
    # Find user by username
    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        logger.warning(
            "login_failed",
            username=request.username,
            reason="user_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        logger.warning(
            "login_failed",
            username=request.username,
            reason="user_inactive",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        logger.warning(
            "login_failed",
            username=request.username,
            reason="invalid_password",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_login timestamp
    try:
        user.last_login = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        logger.warning("failed_to_update_last_login", username=request.username, error=str(e))
        # Don't fail login if last_login update fails
        db.rollback()

    # Create tokens with user's role from database
    try:
        access_token = create_access_token(username=user.username, role=user.role)
        refresh_token = create_refresh_token(username=user.username, role=user.role)

        logger.info("login_successful", username=user.username, role=user.role)

        # Calculate expiration in seconds
        expires_in = int(timedelta(minutes=settings.jwt_access_token_expire_minutes).total_seconds())

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
        )
    except Exception as e:
        logger.error("token_creation_failed", username=user.username, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tokens",
        )


@router.post("/refresh", response_model=RefreshTokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.

    Args:
        request: Refresh token request with refresh_token
        db: Database session

    Returns:
        RefreshTokenResponse with new access_token

    Raises:
        HTTPException 401: If refresh token is invalid, expired, or user is inactive
    """
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token, token_type="refresh")
        username = payload.get("sub")
        role = payload.get("role", "administrator")

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Verify user still exists and is active
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.warning("token_refresh_failed", username=username, reason="user_not_found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            logger.warning("token_refresh_failed", username=username, reason="user_inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
            )

        # Use role from database (in case it changed)
        role = user.role

        # Create new access token
        access_token = create_access_token(username=username, role=role)

        logger.info("token_refreshed", username=username, role=role)

        # Calculate expiration in seconds
        expires_in = int(timedelta(minutes=settings.jwt_access_token_expire_minutes).total_seconds())

        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("token_refresh_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

