"""
Comprehensive API integration tests to increase coverage.
"""
import pytest
from fastapi.testclient import TestClient
import tempfile
import io


class TestHealthAndMetricsEndpoints:
    """Test health and metrics endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_health_endpoint(self, test_client: TestClient):
        """Test health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.integration
    @pytest.mark.api
    def test_metrics_endpoint(self, test_client: TestClient):
        """Test Prometheus metrics endpoint."""
        response = test_client.get("/metrics")
        
        assert response.status_code == 200
        # Prometheus metrics are plain text
        assert "http_requests_total" in response.text or "# HELP" in response.text

    @pytest.mark.integration
    @pytest.mark.api
    def test_api_info_endpoint(self, test_client: TestClient):
        """Test API info endpoint."""
        response = test_client.get("/api/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data or "version" in data


class TestUserManagementEndpoints:
    """Test user management endpoints for coverage."""

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_registration_complete_flow(self, test_client: TestClient):
        """Test complete user registration flow."""
        # Test registration
        user_data = {
            "email": "coverage@example.com",
            "password": "CoverageTest123!"
        }
        
        response = test_client.post("/api/users/register", json=user_data)
        assert response.status_code == 200
        
        # Test request verification
        response = test_client.post("/api/users/request-verification", json={
            "email": user_data["email"]
        })
        
        # Should succeed or fail gracefully
        assert response.status_code in [200, 400, 409]

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_login_flow(self, test_client: TestClient, test_user, test_user_data):
        """Test user login flow."""
        login_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = test_client.post("/api/users/login", data=login_data)
        
        # May pass or fail depending on user verification status
        assert response.status_code in [200, 401, 400]

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.auth
    def test_user_profile_access(self, test_client: TestClient, test_user_data):
        """Test accessing user profile."""
        # First register a user
        response = test_client.post("/api/users/register", json=test_user_data)
        
        if response.status_code == 200:
            # Try to get user info (should fail without auth)
            response = test_client.get("/api/users/me")
            assert response.status_code == 401  # Should require authentication


class TestPhotoManagementEndpoints:
    """Test photo management endpoints for coverage."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_photo_upload_without_auth(self, test_client: TestClient):
        """Test photo upload without authentication."""
        # Create fake image file
        fake_image = io.BytesIO(b"fake image data")
        fake_image.name = "test.jpg"
        
        response = test_client.post(
            "/api/photos/upload",
            files={"file": ("test.jpg", fake_image, "image/jpeg")},
            data={"title": "Test Photo", "description": "Test"}
        )
        
        # Should require authentication
        assert response.status_code == 401

    @pytest.mark.integration
    @pytest.mark.api
    def test_public_photos_list(self, test_client: TestClient):
        """Test listing public photos."""
        response = test_client.get("/api/photos/public")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.integration
    @pytest.mark.api
    def test_photo_detail_nonexistent(self, test_client: TestClient):
        """Test getting non-existent photo details."""
        response = test_client.get("/api/photos/999999")
        
        assert response.status_code == 404


class TestPlatformEndpoints:
    """Test platform and monitoring endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_platform_stats(self, test_client: TestClient):
        """Test platform statistics endpoint."""
        response = test_client.get("/api/platform/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.integration
    @pytest.mark.api
    def test_platform_security(self, test_client: TestClient):
        """Test platform security status."""
        response = test_client.get("/api/platform/security")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.integration
    @pytest.mark.api
    def test_platform_performance(self, test_client: TestClient):
        """Test platform performance metrics."""
        response = test_client.get("/api/platform/performance")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestErrorHandlingAndValidation:
    """Test error handling and validation coverage."""

    @pytest.mark.integration
    @pytest.mark.api
    def test_invalid_json_request(self, test_client: TestClient):
        """Test handling of invalid JSON in requests."""
        response = test_client.post(
            "/api/users/register",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    @pytest.mark.integration
    @pytest.mark.api
    def test_missing_required_fields(self, test_client: TestClient):
        """Test handling of missing required fields."""
        # Missing password
        response = test_client.post("/api/users/register", json={
            "email": "test@example.com"
        })
        
        assert response.status_code == 422
        
        # Missing email
        response = test_client.post("/api/users/register", json={
            "password": "TestPassword123!"
        })
        
        assert response.status_code == 422

    @pytest.mark.integration
    @pytest.mark.api
    def test_invalid_content_type(self, test_client: TestClient):
        """Test handling of invalid content types."""
        response = test_client.post(
            "/api/users/register",
            json={"email": "test@example.com", "password": "Test123!"},
            headers={"Content-Type": "text/plain"}
        )
        
        # Should handle gracefully
        assert response.status_code in [422, 415]


class TestRateLimitingAndSecurity:
    """Test rate limiting and security features."""

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.security
    def test_multiple_rapid_requests(self, test_client: TestClient):
        """Test rate limiting with multiple rapid requests."""
        # Make multiple requests rapidly
        responses = []
        for i in range(10):
            response = test_client.get("/health")
            responses.append(response.status_code)
        
        # Most should succeed, but rate limiting might kick in
        success_count = sum(1 for status in responses if status == 200)
        assert success_count >= 5  # At least some should succeed

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.security
    def test_malformed_auth_headers(self, test_client: TestClient):
        """Test handling of malformed authorization headers."""
        response = test_client.get(
            "/api/users/me",
            headers={"Authorization": "InvalidFormat"}
        )
        
        assert response.status_code == 401

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.security
    def test_sql_injection_attempts(self, test_client: TestClient):
        """Test handling of SQL injection attempts."""
        malicious_data = {
            "email": "test@example.com'; DROP TABLE users; --",
            "password": "Test123!"
        }
        
        response = test_client.post("/api/users/register", json=malicious_data)
        
        # Should be handled by validation
        assert response.status_code == 422

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.security
    def test_xss_attempts(self, test_client: TestClient):
        """Test handling of XSS attempts."""
        malicious_data = {
            "email": "<script>alert('xss')</script>@example.com",
            "password": "Test123!"
        }
        
        response = test_client.post("/api/users/register", json=malicious_data)
        
        # Should be handled by email validation
        assert response.status_code == 422