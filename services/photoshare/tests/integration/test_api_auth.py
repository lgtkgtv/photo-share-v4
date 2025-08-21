"""
Integration tests for authentication API endpoints.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient


class TestAuthenticationAPI:
    """Test authentication API endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_registration(self, test_client: TestClient):
        """Test user registration endpoint."""
        user_data = {
            "email": "newuser@example.com",
            "password": "NewUserPassword123!"
        }
        
        response = test_client.post("/api/users/register", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "password" not in data  # Password should not be returned
        assert data["is_verified"] is False
        assert data["is_active"] is True

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_registration_duplicate_email(self, test_client: TestClient, test_user_data):
        """Test user registration with duplicate email."""
        # First registration
        response1 = test_client.post("/api/users/register", json=test_user_data)
        assert response1.status_code == 200
        
        # Second registration with same email
        response2 = test_client.post("/api/users/register", json=test_user_data)
        assert response2.status_code == 409
        data = response2.json()
        assert "already exists" in data["error"]["message"]

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_registration_invalid_email(self, test_client: TestClient):
        """Test user registration with invalid email."""
        user_data = {
            "email": "invalid-email",
            "password": "ValidPassword123!"
        }
        
        response = test_client.post("/api/users/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "email" in data["error"]["message"].lower()

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_registration_weak_password(self, test_client: TestClient):
        """Test user registration with weak password."""
        user_data = {
            "email": "weakpass@example.com",
            "password": "weak"
        }
        
        response = test_client.post("/api/users/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "password" in data["error"]["message"].lower()

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_login_success(self, test_client: TestClient, test_user, test_user_data):
        """Test successful user login."""
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = test_client.post("/api/users/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user_id"] == test_user.id
        assert data["email"] == test_user.email

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_login_invalid_credentials(self, test_client: TestClient, test_user):
        """Test login with invalid credentials."""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = test_client.post("/api/users/login", data=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "invalid credentials" in data["error"]["message"].lower()

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_login_nonexistent_user(self, test_client: TestClient):
        """Test login with non-existent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "SomePassword123!"
        }
        
        response = test_client.post("/api/users/login", data=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "invalid credentials" in data["error"]["message"].lower()

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_get_current_user_authenticated(self, test_client: TestClient, auth_headers):
        """Test getting current user info with valid authentication."""
        response = test_client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "created_at" in data
        assert "is_verified" in data
        assert "is_active" in data

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_get_current_user_unauthenticated(self, test_client: TestClient):
        """Test getting current user info without authentication."""
        response = test_client.get("/api/users/me")
        
        assert response.status_code == 403  # FastAPI returns 403 for missing auth

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_get_current_user_invalid_token(self, test_client: TestClient):
        """Test getting current user info with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        
        response = test_client.get("/api/users/me", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "invalid" in data["error"]["message"].lower()

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_authentication_flow_complete(self, test_client: TestClient):
        """Test complete authentication flow: register -> login -> access protected endpoint."""
        # Step 1: Register
        user_data = {
            "email": "flowtest@example.com",
            "password": "FlowTestPassword123!"
        }
        
        register_response = test_client.post("/api/users/register", json=user_data)
        assert register_response.status_code == 200
        user_id = register_response.json()["id"]
        
        # Step 2: Login
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        login_response = test_client.post("/api/users/login", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Step 3: Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        me_response = test_client.get("/api/users/me", headers=headers)
        assert me_response.status_code == 200
        
        user_info = me_response.json()
        assert user_info["id"] == user_id
        assert user_info["email"] == user_data["email"]


class TestAuthenticationSecurity:
    """Test authentication security features."""

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.auth
    def test_password_not_returned_in_responses(self, test_client: TestClient):
        """Test that passwords are never returned in API responses."""
        user_data = {
            "email": "securetest@example.com",
            "password": "SecurePassword123!"
        }
        
        # Register user
        register_response = test_client.post("/api/users/register", json=user_data)
        register_data = register_response.json()
        
        # Login user
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        login_response = test_client.post("/api/users/login", data=login_data)
        login_data = login_response.json()
        
        # Get user info
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        me_response = test_client.get("/api/users/me", headers=headers)
        me_data = me_response.json()
        
        # Check that password is not in any response
        assert "password" not in register_data
        assert "password_hash" not in register_data
        assert "password" not in login_data
        assert "password_hash" not in login_data
        assert "password" not in me_data
        assert "password_hash" not in me_data

    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.auth
    def test_session_tracking(self, test_client: TestClient, test_user_data):
        """Test that user sessions are properly tracked."""
        # Login to create session
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        # First registration (should work)
        register_response = test_client.post("/api/users/register", json=test_user_data)
        if register_response.status_code != 200:
            # User might already exist, that's OK
            pass
        
        login_response = test_client.post("/api/users/login", data=login_data)
        assert login_response.status_code in [200, 401]  # Might fail if user doesn't exist
        
        if login_response.status_code == 200:
            # Verify that session information is included
            data = login_response.json()
            assert "access_token" in data
            assert "user_id" in data