"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request for login endpoint."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Response with JWT tokens."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")


class RefreshTokenRequest(BaseModel):
    """Request for refresh token endpoint."""

    refresh_token: str = Field(..., description="JWT refresh token")


class RefreshTokenResponse(BaseModel):
    """Response with new access token."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")

