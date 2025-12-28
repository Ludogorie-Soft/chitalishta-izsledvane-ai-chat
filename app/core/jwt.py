"""JWT token generation and verification utilities."""

import datetime
from typing import Optional

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings

# Use timezone-aware datetime (Python 3.2+)
UTC = datetime.timezone.utc


def get_rsa_keys():
    """
    Get RSA key pair for JWT signing/verification.

    Returns:
        Tuple of (private_key, public_key) as PEM strings
    """
    # If keys are provided in settings, use them
    if settings.jwt_rsa_private_key and settings.jwt_rsa_public_key:
        return settings.jwt_rsa_private_key, settings.jwt_rsa_public_key

    # Otherwise, generate new keys (not recommended for production)
    # This is useful for development/testing
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Serialize to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def get_private_key():
    """Get RSA private key for JWT signing."""
    private_key_pem, _ = get_rsa_keys()
    return serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"), password=None
    )


def get_public_key():
    """Get RSA public key for JWT verification."""
    _, public_key_pem = get_rsa_keys()
    return serialization.load_pem_public_key(public_key_pem.encode("utf-8"))


def create_access_token(
    username: str, role: str = "administrator", expires_delta: Optional[datetime.timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        username: Username (subject)
        role: User role (default: "administrator")
        expires_delta: Optional expiration time delta (default: 30 minutes)

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = datetime.timedelta(minutes=settings.jwt_access_token_expire_minutes)

    expire = datetime.datetime.now(UTC) + expires_delta
    iat = datetime.datetime.now(UTC)

    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": iat,
        "type": "access",
    }

    private_key = get_private_key()
    token = jwt.encode(payload, private_key, algorithm=settings.jwt_algorithm)
    return token


def create_refresh_token(
    username: str, role: str = "administrator", expires_delta: Optional[datetime.timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        username: Username (subject)
        role: User role (default: "administrator")
        expires_delta: Optional expiration time delta (default: 7 days)

    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta is None:
        expires_delta = datetime.timedelta(days=settings.jwt_refresh_token_expire_days)

    expire = datetime.datetime.now(UTC) + expires_delta
    iat = datetime.datetime.now(UTC)

    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": iat,
        "type": "refresh",
    }

    private_key = get_private_key()
    token = jwt.encode(payload, private_key, algorithm=settings.jwt_algorithm)
    return token


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        public_key = get_public_key()
        payload = jwt.decode(
            token, public_key, algorithms=[settings.jwt_algorithm], options={"verify_exp": True}
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise jwt.InvalidTokenError(f"Invalid token type. Expected {token_type}")

        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")

