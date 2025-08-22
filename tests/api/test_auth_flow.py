#!/usr/bin/env python3
"""
API test script for complete authentication flow.

Tests the full authentication workflow including:
- User registration
- Email verification
- User login and token management
- Protected endpoint access
"""

import pytest
import os
import sys

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.auth
class TestAuthenticationFlow:
    """Test complete authentication flow."""

    async def test_complete_auth_workflow(self, async_test_client: AsyncClient):
        """Test complete authentication workflow from registration to API access."""
        
        # Test data
        user_data = {
            "email": "authtest@example.com",
            "password": "SecurePassword123!"
        }
        
        # Step 1: User Registration
        register_response = await async_test_client.post(
            "/api/users/register",
            json=user_data
        )
        
        assert register_response.status_code == 200
        register_data = register_response.json()
        assert register_data["email"] == user_data["email"]
        assert register_data["is_verified"] is False
        assert "id" in register_data
        
        user_id = register_data["id"]
        
        # Step 2: Request Email Verification
        verification_request = await async_test_client.post(
            "/api/users/request-verification",
            json={"email": user_data["email"]}
        )
        
        assert verification_request.status_code == 200
        verification_data = verification_request.json()
        assert "verification_link" in verification_data
        
        # Extract verification secret from the link
        verification_link = verification_data["verification_link"]
        verification_secret = verification_link.split("/")[-1]
        
        # Step 3: Verify Email
        verify_response = await async_test_client.get(
            f"/api/users/verify/{verification_secret}"
        )
        
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["message"] == "Email verified successfully"
        assert verify_data["user"]["is_verified"] is True
        
        # Step 4: Login with Verified Account
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        login_response = await async_test_client.post(
            "/api/users/login",
            data=login_data
        )
        
        assert login_response.status_code == 200
        login_result = login_response.json()
        assert "access_token" in login_result
        assert "token_type" in login_result
        assert login_result["token_type"] == "bearer"
        assert login_result["user_id"] == user_id
        
        access_token = login_result["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 5: Access Protected Endpoint
        profile_response = await async_test_client.get(
            "/api/users/me",
            headers=auth_headers
        )
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["email"] == user_data["email"]
        assert profile_data["is_verified"] is True
        assert profile_data["is_active"] is True

    async def test_login_before_verification(self, async_test_client: AsyncClient):
        """Test that login fails for unverified users."""
        
        user_data = {
            "email": "unverified@example.com",
            "password": "SecurePassword123!"
        }
        
        # Register user (unverified)
        await async_test_client.post(
            "/api/users/register",
            json=user_data
        )
        
        # Try to login without verification
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        login_response = await async_test_client.post(
            "/api/users/login",
            data=login_data
        )
        
        # Should fail for unverified user
        assert login_response.status_code == 401
        error_data = login_response.json()
        assert "not verified" in error_data["detail"].lower()

    async def test_invalid_credentials(self, async_test_client: AsyncClient):
        """Test login with invalid credentials."""
        
        # Try login with non-existent user
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        login_response = await async_test_client.post(
            "/api/users/login",
            data=login_data
        )
        
        assert login_response.status_code == 401
        error_data = login_response.json()
        assert "invalid" in error_data["detail"].lower()

    async def test_expired_verification_secret(self, async_test_client: AsyncClient):
        """Test verification with invalid/expired secret."""
        
        # Try to verify with invalid secret
        verify_response = await async_test_client.get(
            "/api/users/verify/invalid-secret-token"
        )
        
        assert verify_response.status_code == 400
        error_data = verify_response.json()
        assert "invalid" in error_data["detail"].lower() or "expired" in error_data["detail"].lower()

    async def test_duplicate_registration(self, async_test_client: AsyncClient):
        """Test registering with already existing email."""
        
        user_data = {
            "email": "duplicate@example.com",
            "password": "SecurePassword123!"
        }
        
        # First registration
        first_response = await async_test_client.post(
            "/api/users/register",
            json=user_data
        )
        assert first_response.status_code == 200
        
        # Second registration with same email
        second_response = await async_test_client.post(
            "/api/users/register",
            json=user_data
        )
        
        assert second_response.status_code == 400
        error_data = second_response.json()
        assert "already registered" in error_data["detail"].lower()

    async def test_password_validation(self, async_test_client: AsyncClient):
        """Test password validation during registration."""
        
        # Test weak password
        weak_password_data = {
            "email": "weakpass@example.com",
            "password": "123"
        }
        
        response = await async_test_client.post(
            "/api/users/register",
            json=weak_password_data
        )
        
        assert response.status_code == 422  # Validation error

    async def test_email_validation(self, async_test_client: AsyncClient):
        """Test email validation during registration."""
        
        # Test invalid email format
        invalid_email_data = {
            "email": "not-an-email",
            "password": "SecurePassword123!"
        }
        
        response = await async_test_client.post(
            "/api/users/register",
            json=invalid_email_data
        )
        
        assert response.status_code == 422  # Validation error

    async def test_protected_endpoint_without_token(self, async_test_client: AsyncClient):
        """Test accessing protected endpoint without token."""
        
        response = await async_test_client.get("/api/users/me")
        
        assert response.status_code == 401
        error_data = response.json()
        assert "not authenticated" in error_data["detail"].lower()

    async def test_protected_endpoint_with_invalid_token(self, async_test_client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        
        response = await async_test_client.get(
            "/api/users/me",
            headers=invalid_headers
        )
        
        assert response.status_code == 401

    async def test_token_expiration_handling(self, async_test_client: AsyncClient):
        """Test handling of token expiration."""
        
        # This test would require manipulating token expiration
        # For now, test with a malformed token that should be rejected
        expired_headers = {"Authorization": "Bearer expired.token.here"}
        
        response = await async_test_client.get(
            "/api/users/me",
            headers=expired_headers
        )
        
        assert response.status_code == 401

    async def test_multiple_verification_requests(self, async_test_client: AsyncClient):
        """Test multiple verification requests for same user."""
        
        user_data = {
            "email": "multiverify@example.com",
            "password": "SecurePassword123!"
        }
        
        # Register user
        await async_test_client.post(
            "/api/users/register",
            json=user_data
        )
        
        # First verification request
        first_request = await async_test_client.post(
            "/api/users/request-verification",
            json={"email": user_data["email"]}
        )
        assert first_request.status_code == 200
        
        # Second verification request
        second_request = await async_test_client.post(
            "/api/users/request-verification",
            json={"email": user_data["email"]}
        )
        # Should still work (might invalidate previous or extend)
        assert second_request.status_code == 200


@pytest.mark.api
@pytest.mark.performance
class TestAuthenticationPerformance:
    """Test authentication performance aspects."""

    async def test_login_response_time(self, async_test_client: AsyncClient):
        """Test login response time is acceptable."""
        import time
        
        # Setup verified user first
        user_data = {
            "email": "perftest@example.com", 
            "password": "SecurePassword123!"
        }
        
        # Register and verify user (setup)
        await async_test_client.post("/api/users/register", json=user_data)
        verification_response = await async_test_client.post(
            "/api/users/request-verification",
            json={"email": user_data["email"]}
        )
        verification_link = verification_response.json()["verification_link"]
        verification_secret = verification_link.split("/")[-1]
        await async_test_client.get(f"/api/users/verify/{verification_secret}")
        
        # Test login performance
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        start_time = time.time()
        login_response = await async_test_client.post(
            "/api/users/login",
            data=login_data
        )
        end_time = time.time()
        
        assert login_response.status_code == 200
        
        # Login should complete within reasonable time (2 seconds)
        response_time = end_time - start_time
        assert response_time < 2.0, f"Login took {response_time:.2f}s, should be < 2.0s"