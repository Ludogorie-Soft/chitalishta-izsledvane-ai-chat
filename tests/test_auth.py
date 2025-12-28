"""Tests for authentication and security features."""

import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.indexing import router as indexing_router
from app.api.ingestion import router as ingestion_router
from app.api.vector_store import router as vector_store_router
from app.core.auth import CurrentUser, get_current_user, require_administrator
from app.core.config import settings
from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.db.database import get_db


@pytest.fixture
def test_app_with_auth(test_db_session, test_credentials, test_rsa_keys_env, test_user):
    """Create test FastAPI app with all routers including auth.

    Note: Depends on test_credentials, test_rsa_keys_env, and test_user to ensure
    settings are loaded and test user exists before routers are imported.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    # Reload modules to pick up new settings
    import importlib
    import app.api.auth
    import app.core.middleware
    importlib.reload(app.api.auth)
    importlib.reload(app.core.middleware)
    from app.api.auth import router as auth_router_reloaded
    from app.core.middleware import SwaggerUIAuthMiddleware

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app = FastAPI()
    # Add Swagger UI auth middleware
    app.add_middleware(SwaggerUIAuthMiddleware)
    app.include_router(auth_router_reloaded)
    app.include_router(chat_router)
    app.include_router(admin_router)
    app.include_router(ingestion_router)
    app.include_router(indexing_router)
    app.include_router(vector_store_router)
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


@pytest.fixture
def test_credentials(monkeypatch):
    """Set up test credentials."""
    monkeypatch.setenv("SWAGGER_UI_USERNAME", "test_admin")
    monkeypatch.setenv("SWAGGER_UI_PASSWORD", "test_password")
    monkeypatch.setenv("API_KEY", "test_api_key_123")
    # Reload settings and auth modules to pick up new environment variables
    import importlib
    import app.core.config
    import app.core.auth

    importlib.reload(app.core.config)
    importlib.reload(app.core.auth)
    return app.core.config.settings


@pytest.fixture
def test_user(test_db_session):
    """Create a test user in the database for authentication tests."""
    import bcrypt
    from app.db.models import User

    # Check if user already exists
    existing_user = test_db_session.query(User).filter(User.username == "test_admin").first()
    if existing_user:
        # Update password if user exists
        password_bytes = "test_password".encode("utf-8")
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        salt = bcrypt.gensalt()
        existing_user.password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")
        existing_user.role = "administrator"
        existing_user.is_active = True
        test_db_session.commit()
        return existing_user

    # Create new user
    password_bytes = "test_password".encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    user = User(
        username="test_admin",
        password_hash=password_hash,
        email="test_admin@example.com",
        role="administrator",
        is_active=True,
    )

    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)

    return user


@pytest.fixture
def test_rsa_keys():
    """Generate test RSA keys for JWT."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    # Generate test keys
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Serialize to PEM
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


@pytest.fixture
def test_rsa_keys_env(monkeypatch, test_rsa_keys):
    """Set RSA keys in environment for testing."""
    private_pem, public_pem = test_rsa_keys
    monkeypatch.setenv("JWT_RSA_PRIVATE_KEY", private_pem)
    monkeypatch.setenv("JWT_RSA_PUBLIC_KEY", public_pem)
    # Reload settings module
    import importlib
    import app.core.config
    import app.core.jwt

    importlib.reload(app.core.config)
    importlib.reload(app.core.jwt)
    return app.core.config.settings


class TestJWTTokens:
    """Tests for JWT token generation and verification."""

    def test_create_access_token(self, test_rsa_keys_env):
        """Test creating access token."""
        token = create_access_token(username="test_user", role="administrator")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, test_rsa_keys_env):
        """Test creating refresh token."""
        token = create_refresh_token(username="test_user", role="administrator")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token(self, test_rsa_keys_env):
        """Test verifying access token."""
        token = create_access_token(username="test_user", role="administrator")
        payload = verify_token(token, token_type="access")

        assert payload["sub"] == "test_user"
        assert payload["role"] == "administrator"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_refresh_token(self, test_rsa_keys_env):
        """Test verifying refresh token."""
        token = create_refresh_token(username="test_user", role="administrator")
        payload = verify_token(token, token_type="refresh")

        assert payload["sub"] == "test_user"
        assert payload["role"] == "administrator"
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_token_wrong_type(self, test_rsa_keys_env):
        """Test that verifying token with wrong type fails."""
        token = create_access_token(username="test_user", role="administrator")

        with pytest.raises(Exception):  # Should raise InvalidTokenError
            verify_token(token, token_type="refresh")

    def test_verify_expired_token(self, test_rsa_keys_env):
        """Test that expired token verification fails."""
        # Create token with very short expiration
        from datetime import timedelta

        token = create_access_token(
            username="test_user",
            role="administrator",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(Exception):  # Should raise ExpiredSignatureError
            verify_token(token, token_type="access")

    def test_token_expiration_time(self, test_rsa_keys_env):
        """Test that token expiration is set correctly."""
        token = create_access_token(username="test_user", role="administrator")
        payload = verify_token(token, token_type="access")

        # Check expiration is approximately 30 minutes from now
        # JWT exp is in UTC timestamp, so use UTC for comparison
        try:
            from datetime import timezone
            UTC = timezone.utc
        except ImportError:
            UTC = datetime.timezone.utc

        exp_time = datetime.datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.datetime.now(UTC)
        expected_exp = now + datetime.timedelta(minutes=30)

        # Allow 5 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 5


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_login_success(self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_user):
        """Test successful login."""
        response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800  # 30 minutes in seconds
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    def test_login_invalid_username(self, test_app_with_auth, test_credentials, test_rsa_keys_env):
        """Test login with invalid username."""
        response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "wrong_user", "password": "test_password"},
        )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    def test_login_invalid_password(self, test_app_with_auth, test_credentials, test_rsa_keys_env):
        """Test login with invalid password."""
        response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "wrong_password"},
        )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    def test_login_missing_credentials(self, test_app_with_auth, test_credentials, test_rsa_keys_env):
        """Test login with missing credentials."""
        response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin"},
        )

        assert response.status_code == 422  # Validation error

    def test_refresh_token_success(self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_user):
        """Test successful token refresh."""
        # First login to get refresh token
        login_response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Refresh the token
        response = test_app_with_auth.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800
        assert "refresh_token" not in data  # Refresh endpoint doesn't return new refresh token

    def test_refresh_token_invalid(self, test_app_with_auth, test_credentials, test_rsa_keys_env):
        """Test refresh with invalid token."""
        response = test_app_with_auth.post(
            "/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == 401
        assert "Invalid or expired refresh token" in response.json()["detail"]

    def test_refresh_token_wrong_type(self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_user):
        """Test refresh with access token instead of refresh token."""
        # Get access token
        login_response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Try to use access token as refresh token
        response = test_app_with_auth.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401


class TestAPIAuthentication:
    """Tests for API key authentication."""

    def test_verify_api_key_success(self, test_credentials):
        """Test successful API key verification."""
        from app.core.auth import verify_api_key

        result = verify_api_key("test_api_key_123")
        assert result is True

    def test_verify_api_key_invalid(self, test_credentials):
        """Test API key verification with invalid key."""
        from app.core.auth import verify_api_key

        with pytest.raises(Exception):  # Should raise HTTPException
            verify_api_key("wrong_api_key")

    def test_verify_api_key_missing(self, test_credentials):
        """Test API key verification with missing key."""
        from app.core.auth import verify_api_key

        with pytest.raises(Exception):  # Should raise HTTPException
            verify_api_key(None)

    def test_verify_api_key_disabled(self, monkeypatch):
        """Test API key verification when disabled (empty API_KEY)."""
        monkeypatch.setenv("API_KEY", "")
        # Reload settings and auth modules to pick up new environment variables
        import importlib
        import app.core.config
        import app.core.auth

        importlib.reload(app.core.config)
        importlib.reload(app.core.auth)
        from app.core.auth import verify_api_key

        # When API key is empty, verification should pass (for development)
        result = verify_api_key(None)
        assert result is True


class TestPublicAPIAuthentication:
    """Tests for Public API endpoints with API key authentication."""

    def test_chat_endpoint_with_valid_api_key(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test chat endpoint with valid API key."""
        with patch("app.api.chat.get_hybrid_pipeline_service") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.query = MagicMock(
                return_value={
                    "answer": "Тестов отговор",
                    "intent": "rag",
                    "routing_confidence": 0.9,
                    "sql_executed": False,
                    "rag_executed": True,
                }
            )
            mock_get_pipeline.return_value = mock_pipeline

            response = test_app_with_auth.post(
                "/chat/",
                json={"message": "Тест", "mode": "medium"},
                headers={"X-API-Key": "test_api_key_123"},
            )

            assert response.status_code == 200
            assert "answer" in response.json()

    def test_chat_endpoint_without_api_key(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test chat endpoint without API key."""
        response = test_app_with_auth.post(
            "/chat/",
            json={"message": "Тест", "mode": "medium"},
        )

        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_chat_endpoint_with_invalid_api_key(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test chat endpoint with invalid API key."""
        response = test_app_with_auth.post(
            "/chat/",
            json={"message": "Тест", "mode": "medium"},
            headers={"X-API-Key": "wrong_key"},
        )

        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_chat_stream_with_valid_api_key(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test chat stream endpoint with valid API key."""
        with patch("app.api.chat.get_hybrid_pipeline_service") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.query = MagicMock(
                return_value={
                    "answer": "Тестов отговор",
                    "intent": "rag",
                    "routing_confidence": 0.9,
                    "sql_executed": False,
                    "rag_executed": True,
                }
            )
            mock_get_pipeline.return_value = mock_pipeline

            response = test_app_with_auth.post(
                "/chat/stream",
                json={"message": "Тест", "mode": "medium"},
                headers={"X-API-Key": "test_api_key_123"},
            )

            assert response.status_code == 200

    def test_chat_history_with_valid_api_key(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test chat history endpoint with valid API key."""
        # Create a conversation first
        with patch("app.api.chat.get_hybrid_pipeline_service") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.query = MagicMock(
                return_value={
                    "answer": "Тестов отговор",
                    "intent": "rag",
                    "routing_confidence": 0.9,
                    "sql_executed": False,
                    "rag_executed": True,
                }
            )
            mock_get_pipeline.return_value = mock_pipeline

            # Create conversation
            chat_response = test_app_with_auth.post(
                "/chat/",
                json={"message": "Тест", "mode": "medium"},
                headers={"X-API-Key": "test_api_key_123"},
            )
            conversation_id = chat_response.json()["conversation_id"]

            # Get history
            response = test_app_with_auth.post(
                "/chat/history",
                json={"conversation_id": conversation_id},
                headers={"X-API-Key": "test_api_key_123"},
            )

            assert response.status_code == 200
            assert "messages" in response.json()


class TestAdminAPIAuthentication:
    """Tests for Admin API endpoints with JWT authentication."""

    def test_admin_endpoint_with_valid_jwt(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_db_session, test_user
    ):
        """Test admin endpoint with valid JWT token."""
        # Login to get token
        login_response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Access admin endpoint
        response = test_app_with_auth.get(
            "/admin/chat",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert "conversations" in response.json()

    def test_admin_endpoint_without_token(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test admin endpoint without JWT token."""
        response = test_app_with_auth.get("/admin/chat")

        assert response.status_code == 403  # FastAPI returns 403 for missing Bearer token

    def test_admin_endpoint_with_invalid_token(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test admin endpoint with invalid JWT token."""
        response = test_app_with_auth.get(
            "/admin/chat",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    def test_admin_endpoint_with_expired_token(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test admin endpoint with expired JWT token."""
        from datetime import timedelta

        # Create expired token
        expired_token = create_access_token(
            username="test_admin",
            role="administrator",
            expires_delta=timedelta(seconds=-1),
        )

        response = test_app_with_auth.get(
            "/admin/chat",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401


class TestSetupAPIAuthentication:
    """Tests for Setup API endpoints with JWT authentication."""

    def test_indexing_endpoint_with_valid_jwt(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_user
    ):
        """Test indexing endpoint with valid JWT token."""
        # Login to get token
        login_response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Access indexing endpoint
        response = test_app_with_auth.get(
            "/index/stats",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

    def test_indexing_endpoint_without_token(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test indexing endpoint without JWT token."""
        response = test_app_with_auth.get("/index/stats")

        assert response.status_code == 403

    def test_ingestion_endpoint_with_valid_jwt(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_db_session, test_user
    ):
        """Test ingestion endpoint with valid JWT token."""
        # Login to get token
        login_response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Access ingestion endpoint
        response = test_app_with_auth.post(
            "/ingest/database",
            json={"limit": 5},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

    def test_vector_store_endpoint_with_valid_jwt(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_user
    ):
        """Test vector store endpoint with valid JWT token."""
        # Login to get token
        login_response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Access vector store endpoint
        response = test_app_with_auth.get(
            "/vector-store/status",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200


class TestAuthenticationDependencies:
    """Tests for authentication dependency functions."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, test_rsa_keys_env):
        """Test get_current_user with valid token."""
        from fastapi.security import HTTPAuthorizationCredentials
        # Import CurrentUser here to avoid module reload issues
        from app.core.auth import CurrentUser as CurrentUserClass

        token = create_access_token(username="test_user", role="administrator")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user(credentials)
        # Check type by class name to avoid module reload issues
        assert type(user).__name__ == "CurrentUser"
        assert isinstance(user, CurrentUserClass)
        assert user.username == "test_user"
        assert user.role == "administrator"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, test_rsa_keys_env):
        """Test get_current_user with invalid token."""
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with pytest.raises(Exception):  # Should raise HTTPException
            await get_current_user(credentials)

    @pytest.mark.asyncio
    async def test_require_administrator_valid_role(self, test_rsa_keys_env):
        """Test require_administrator with administrator role."""
        user = CurrentUser(username="test_user", role="administrator")
        result = await require_administrator(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_require_administrator_invalid_role(self, test_rsa_keys_env):
        """Test require_administrator with non-administrator role."""
        user = CurrentUser(username="test_user", role="user")

        with pytest.raises(Exception):  # Should raise HTTPException 403
            await require_administrator(user)


class TestSecurityIntegration:
    """Integration tests for security across different endpoint groups."""

    def test_public_api_requires_api_key_not_jwt(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_user
    ):
        """Test that Public API endpoints require API key, not JWT."""
        # Get JWT token
        login_response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )
        assert login_response.status_code == 200
        jwt_token = login_response.json()["access_token"]

        # Try to use JWT token on Public API endpoint (should fail)
        with patch("app.api.chat.get_hybrid_pipeline_service") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.query = MagicMock(
                return_value={
                    "answer": "Тестов отговор",
                    "intent": "rag",
                    "routing_confidence": 0.9,
                    "sql_executed": False,
                    "rag_executed": True,
                }
            )
            mock_get_pipeline.return_value = mock_pipeline

            response = test_app_with_auth.post(
                "/chat/",
                json={"message": "Тест", "mode": "medium"},
                headers={"Authorization": f"Bearer {jwt_token}"},
            )

            # Should fail because Public API requires API key, not JWT
            assert response.status_code == 401

    def test_admin_api_requires_jwt_not_api_key(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test that Admin API endpoints require JWT, not API key."""
        # Try to use API key on Admin API endpoint (should fail)
        response = test_app_with_auth.get(
            "/admin/chat",
            headers={"X-API-Key": "test_api_key_123"},
        )

        # Should fail because Admin API requires JWT, not API key
        assert response.status_code == 403

    def test_token_refresh_flow(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env, test_user
    ):
        """Test complete token refresh flow."""
        import time

        # 1. Login
        login_response = test_app_with_auth.post(
            "/auth/login",
            json={"username": "test_admin", "password": "test_password"},
        )
        assert login_response.status_code == 200
        access_token_1 = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # 2. Use access token
        response_1 = test_app_with_auth.get(
            "/admin/chat",
            headers={"Authorization": f"Bearer {access_token_1}"},
        )
        assert response_1.status_code == 200

        # 3. Add small delay to ensure new token has different iat timestamp
        time.sleep(1)

        # 4. Refresh token
        refresh_response = test_app_with_auth.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        access_token_2 = refresh_response.json()["access_token"]

        # 5. Use new access token
        response_2 = test_app_with_auth.get(
            "/admin/chat",
            headers={"Authorization": f"Bearer {access_token_2}"},
        )
        assert response_2.status_code == 200

        # Tokens should be different (due to different iat timestamps)
        assert access_token_1 != access_token_2

    def test_swagger_ui_auth_protection(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test that Swagger UI endpoints require authentication."""
        # Try to access /docs without credentials
        response = test_app_with_auth.get("/docs")
        # Should require authentication (401 or redirect to login)
        assert response.status_code in [401, 403]

    def test_swagger_ui_auth_with_credentials(
        self, test_app_with_auth, test_credentials, test_rsa_keys_env
    ):
        """Test that Swagger UI is accessible with correct credentials."""
        import base64

        # Create Basic Auth header
        credentials = f"{test_credentials.swagger_ui_username}:{test_credentials.swagger_ui_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        auth_header = f"Basic {encoded}"

        response = test_app_with_auth.get(
            "/docs",
            headers={"Authorization": auth_header},
        )
        # Should be accessible with correct credentials
        assert response.status_code == 200

    def test_token_payload_structure(self, test_rsa_keys_env):
        """Test that JWT token contains expected payload structure."""
        token = create_access_token(username="test_user", role="administrator")
        payload = verify_token(token, token_type="access")

        # Verify all expected fields are present
        assert "sub" in payload
        assert "role" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
        assert payload["sub"] == "test_user"
        assert payload["role"] == "administrator"
        assert payload["type"] == "access"

    def test_refresh_token_payload_structure(self, test_rsa_keys_env):
        """Test that refresh token contains expected payload structure."""
        token = create_refresh_token(username="test_user", role="administrator")
        payload = verify_token(token, token_type="refresh")

        # Verify all expected fields are present
        assert "sub" in payload
        assert "role" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
        assert payload["sub"] == "test_user"
        assert payload["role"] == "administrator"
        assert payload["type"] == "refresh"

