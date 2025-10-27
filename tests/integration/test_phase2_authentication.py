"""
Phase 2 Integration Tests - Authentication System
Tests auth service, JWT tokens, password hashing, and API endpoints
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
import time

from backend.main import app
from backend.services import AuthService
from backend.config import settings
from backend.database.models import User


# ==================== AuthService Unit Tests ====================

class TestAuthService:
    """Test AuthService methods"""

    def test_hash_password(self, db_session):
        """Test password hashing with bcrypt"""
        auth_service = AuthService(db_session)
        password = "MySecurePassword123"

        hashed = auth_service.hash_password(password)

        # Hash should be different from original
        assert hashed != password
        # Hash should be long (bcrypt generates ~60 chars)
        assert len(hashed) > 50
        # Hash should start with $2b$ (bcrypt identifier)
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self, db_session):
        """Test password verification with correct password"""
        auth_service = AuthService(db_session)
        password = "MySecurePassword123"
        hashed = auth_service.hash_password(password)

        # Correct password should verify
        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, db_session):
        """Test password verification with incorrect password"""
        auth_service = AuthService(db_session)
        password = "MySecurePassword123"
        wrong_password = "WrongPassword456"
        hashed = auth_service.hash_password(password)

        # Wrong password should not verify
        assert auth_service.verify_password(wrong_password, hashed) is False

    def test_create_jwt_token(self, db_session):
        """Test JWT token creation"""
        auth_service = AuthService(db_session)
        user_id = "test-user-123"
        email = "test@example.com"

        token = auth_service.create_access_token(user_id, email)

        # Token should be a string
        assert isinstance(token, str)
        # Token should have 3 parts (header.payload.signature)
        assert len(token.split(".")) == 3

    def test_decode_jwt_token(self, db_session):
        """Test JWT token decoding"""
        auth_service = AuthService(db_session)
        user_id = "test-user-123"
        email = "test@example.com"

        token = auth_service.create_access_token(user_id, email)
        payload = auth_service.decode_token(token)

        # Payload should contain user_id and email
        assert payload["user_id"] == user_id
        assert payload["email"] == email
        # Payload should have expiry and issued-at timestamps
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_expired_token(self, db_session):
        """Test that expired tokens are rejected"""
        auth_service = AuthService(db_session)

        # Create a token that expired 1 hour ago
        expired_payload = {
            "user_id": "test-user",
            "email": "test@test.com",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )

        # Decoding should raise HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.decode_token(expired_token)

        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()

    def test_decode_invalid_token(self, db_session):
        """Test that invalid tokens are rejected"""
        auth_service = AuthService(db_session)
        invalid_token = "invalid.token.here"

        # Decoding should raise HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.decode_token(invalid_token)

        assert exc_info.value.status_code == 401

    def test_password_strength_validation_too_short(self, db_session):
        """Test password validation rejects too-short passwords"""
        auth_service = AuthService(db_session)
        short_password = "Short1"

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_password_strength(short_password)

        assert exc_info.value.status_code == 400
        assert "at least" in str(exc_info.value.detail).lower()

    def test_password_strength_validation_no_uppercase(self, db_session):
        """Test password validation requires uppercase"""
        auth_service = AuthService(db_session)
        no_upper = "alllowercase123"

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_password_strength(no_upper)

        assert exc_info.value.status_code == 400

    def test_password_strength_validation_no_digit(self, db_session):
        """Test password validation requires digit"""
        auth_service = AuthService(db_session)
        no_digit = "NoDigitsHere"

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.validate_password_strength(no_digit)

        assert exc_info.value.status_code == 400

    def test_register_user_success(self, db_session):
        """Test successful user registration"""
        auth_service = AuthService(db_session)

        user = auth_service.register_user(
            email="newuser@test.com",
            password="SecurePass123",
            full_name="New User"
        )

        assert user.id is not None
        assert user.email == "newuser@test.com"
        assert user.full_name == "New User"
        assert user.is_active is True
        assert user.is_admin is False
        # Password should be hashed
        assert user.hashed_password != "SecurePass123"
        assert user.hashed_password.startswith("$2b$")

    def test_register_user_duplicate_email(self, db_session, sample_user):
        """Test that duplicate email registration fails"""
        auth_service = AuthService(db_session)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.register_user(
                email=sample_user.email,  # Duplicate
                password="SecurePass123"
            )

        assert exc_info.value.status_code == 400
        assert "already registered" in str(exc_info.value.detail).lower()

    def test_authenticate_user_success(self, db_session):
        """Test successful user authentication"""
        auth_service = AuthService(db_session)
        password = "TestPassword123"

        # Create user
        user = auth_service.register_user(
            email="authtest@test.com",
            password=password
        )

        # Authenticate
        authenticated_user = auth_service.authenticate_user(
            email="authtest@test.com",
            password=password
        )

        assert authenticated_user.id == user.id
        assert authenticated_user.email == user.email

    def test_authenticate_user_wrong_password(self, db_session):
        """Test authentication fails with wrong password"""
        auth_service = AuthService(db_session)

        # Create user
        auth_service.register_user(
            email="authfail@test.com",
            password="CorrectPassword123"
        )

        # Try to authenticate with wrong password
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.authenticate_user(
                email="authfail@test.com",
                password="WrongPassword456"
            )

        assert exc_info.value.status_code == 401
        assert "invalid" in str(exc_info.value.detail).lower()

    def test_authenticate_user_nonexistent_email(self, db_session):
        """Test authentication fails with nonexistent email"""
        auth_service = AuthService(db_session)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.authenticate_user(
                email="nonexistent@test.com",
                password="AnyPassword123"
            )

        assert exc_info.value.status_code == 401

    def test_authenticate_inactive_user(self, db_session):
        """Test authentication fails for inactive users"""
        auth_service = AuthService(db_session)

        # Create user and deactivate
        user = auth_service.register_user(
            email="inactive@test.com",
            password="Password123"
        )
        user.is_active = False
        db_session.commit()

        # Try to authenticate
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            auth_service.authenticate_user(
                email="inactive@test.com",
                password="Password123"
            )

        assert exc_info.value.status_code == 403
        assert "inactive" in str(exc_info.value.detail).lower()


# ==================== API Endpoint Tests ====================

class TestAuthEndpoints:
    """Test authentication API endpoints"""

    def test_register_endpoint_success(self, test_client, db_session):
        """Test POST /auth/register endpoint"""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "apiuser@test.com",
                "password": "ApiPassword123",
                "full_name": "API Test User"
            }
        )

        assert response.status_code == 201
        data = response.json()

        # Should return token and user info
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "apiuser@test.com"
        assert data["user"]["full_name"] == "API Test User"

    def test_register_endpoint_duplicate_email(self, test_client, db_session):
        """Test register with duplicate email fails"""
        # Register once
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@test.com",
                "password": "Password123"
            }
        )

        # Try to register again
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@test.com",
                "password": "DifferentPass456"
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_endpoint_weak_password(self, test_client):
        """Test register with weak password fails"""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "weakpass@test.com",
                "password": "weak"  # Too short
            }
        )

        # FastAPI pydantic validation returns 422 for min_length constraint
        assert response.status_code == 422

    def test_login_endpoint_success(self, test_client):
        """Test POST /auth/login endpoint"""
        # Register user first
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "logintest@test.com",
                "password": "LoginPass123"
            }
        )

        # Login
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "logintest@test.com",
                "password": "LoginPass123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "logintest@test.com"

    def test_login_endpoint_wrong_password(self, test_client):
        """Test login with wrong password fails"""
        # Register user
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpass@test.com",
                "password": "CorrectPass123"
            }
        )

        # Login with wrong password
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpass@test.com",
                "password": "WrongPass456"
            }
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_endpoint_nonexistent_user(self, test_client):
        """Test login with nonexistent email fails"""
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "AnyPassword123"
            }
        )

        assert response.status_code == 401

    def test_me_endpoint_with_valid_token(self, test_client):
        """Test GET /auth/me with valid token"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "metest@test.com",
                "password": "MeTestPass123",
                "full_name": "Me Test User"
            }
        )
        token = reg_response.json()["access_token"]

        # Access /me endpoint
        response = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == "metest@test.com"
        assert data["full_name"] == "Me Test User"
        assert data["is_active"] is True

    def test_me_endpoint_without_token(self, test_client):
        """Test GET /auth/me without token fails"""
        response = test_client.get("/api/v1/auth/me")

        assert response.status_code == 403  # FastAPI returns 403 for missing auth

    def test_me_endpoint_with_invalid_token(self, test_client):
        """Test GET /auth/me with invalid token fails"""
        response = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401

    def test_refresh_token_endpoint(self, test_client):
        """Test POST /auth/refresh endpoint"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@test.com",
                "password": "RefreshPass123"
            }
        )
        old_token = reg_response.json()["access_token"]

        # Wait 1 second to ensure different timestamp (iat field)
        time.sleep(1)

        # Refresh token
        response = test_client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {old_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return new token
        assert "access_token" in data
        new_token = data["access_token"]
        # New token should be different (due to different iat timestamp)
        assert new_token != old_token

    def test_logout_endpoint(self, test_client):
        """Test POST /auth/logout endpoint"""
        # Register and get token
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@test.com",
                "password": "LogoutPass123"
            }
        )
        token = reg_response.json()["access_token"]

        # Logout
        response = test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "message" in response.json()

    def test_auth_health_check(self, test_client):
        """Test GET /auth/health endpoint"""
        response = test_client.get("/api/v1/auth/health")

        assert response.status_code == 200
        assert "message" in response.json()


# ==================== End-to-End Flow Tests ====================

class TestAuthFlow:
    """Test complete authentication flows"""

    def test_complete_registration_login_flow(self, test_client):
        """Test complete flow: register → login → access protected route"""
        email = "flowtest@test.com"
        password = "FlowTestPass123"

        # 1. Register
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password}
        )
        assert reg_response.status_code == 201
        reg_token = reg_response.json()["access_token"]

        # 2. Access protected route with registration token
        me_response1 = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {reg_token}"}
        )
        assert me_response1.status_code == 200

        # 3. Login (separate session)
        login_response = test_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        login_token = login_response.json()["access_token"]

        # 4. Access protected route with login token
        me_response2 = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_token}"}
        )
        assert me_response2.status_code == 200
        assert me_response2.json()["email"] == email

    def test_token_persists_across_requests(self, test_client):
        """Test that token works for multiple requests"""
        # Register
        reg_response = test_client.post(
            "/api/v1/auth/register",
            json={"email": "persist@test.com", "password": "PersistPass123"}
        )
        token = reg_response.json()["access_token"]

        # Make multiple requests with same token
        for _ in range(5):
            response = test_client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
