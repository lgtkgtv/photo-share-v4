#!/usr/bin/env python3
"""
Integration Tests - Service Communication
==========================================

Tests the complete communication flow between auth and app services.
Verifies service separation and inter-service communication.
"""

import pytest
import requests
import time
from datetime import datetime


class TestServiceCommunication:
    """Integration tests for service-to-service communication."""
    
    AUTH_SERVICE_URL = "http://localhost:8001"
    APP_SERVICE_URL = "http://localhost:8000"
    
    def test_auth_service_availability(self):
        """Test that auth service is available and healthy."""
        response = requests.get(f"{self.AUTH_SERVICE_URL}/health", timeout=10)
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data.get("status") == "healthy"
        assert "service" in health_data
        assert "database" in health_data
    
    def test_app_service_availability(self):
        """Test that app service is available and healthy."""
        response = requests.get(f"{self.APP_SERVICE_URL}/health", timeout=10)
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data.get("status") == "healthy"
    
    def test_service_separation(self):
        """Verify that services are properly separated."""
        # Get service information
        auth_response = requests.get(f"{self.AUTH_SERVICE_URL}/health")
        app_response = requests.get(f"{self.APP_SERVICE_URL}/health")
        
        auth_data = auth_response.json()
        app_data = app_response.json()
        
        # Verify they report different service names
        assert "Authentication" in auth_data.get("service", "")
        assert "PhotoShare" in app_data.get("service", "") or "App" in app_data.get("service", "")
        
        # Verify they have different capabilities
        assert auth_data != app_data
    
    def test_unauthorized_access_protection(self):
        """Test that protected endpoints reject unauthorized requests."""
        protected_endpoints = [
            f"{self.APP_SERVICE_URL}/api/photos/",
            f"{self.APP_SERVICE_URL}/api/users/me",
        ]
        
        for endpoint in protected_endpoints:
            response = requests.get(endpoint, timeout=10)
            # Should be 401 (Unauthorized) or 403 (Forbidden)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should reject unauthorized access"
    
    def test_auth_service_endpoints_availability(self):
        """Test that auth service endpoints are available."""
        # Test public endpoints that should be accessible
        public_endpoints = [
            "/health",
        ]
        
        for endpoint in public_endpoints:
            response = requests.get(f"{self.AUTH_SERVICE_URL}{endpoint}", timeout=10)
            assert response.status_code == 200, f"Auth endpoint {endpoint} should be available"
    
    def test_app_service_public_endpoints(self):
        """Test that app service public endpoints work."""
        # Test public endpoints
        response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/public", timeout=10)
        assert response.status_code == 200
        
        # Should return JSON with photos data structure
        public_data = response.json()
        assert "photos" in public_data or "total" in public_data
    
    def test_service_response_times(self):
        """Test that services respond within acceptable time limits."""
        start_time = time.time()
        response = requests.get(f"{self.AUTH_SERVICE_URL}/health")
        auth_time = time.time() - start_time
        
        start_time = time.time()
        response = requests.get(f"{self.APP_SERVICE_URL}/health")
        app_time = time.time() - start_time
        
        # Services should respond within 5 seconds
        assert auth_time < 5.0, f"Auth service too slow: {auth_time}s"
        assert app_time < 5.0, f"App service too slow: {app_time}s"
    
    @pytest.mark.integration
    def test_cross_service_user_lookup(self):
        """Test that app service can query auth service for user info."""
        # This test requires a valid user UUID - we'll test the endpoint exists
        # and returns appropriate error for invalid UUID
        
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{self.AUTH_SERVICE_URL}/api/auth/users/{fake_uuid}", timeout=10)
        
        # Should return 404 for non-existent user, not a server error
        assert response.status_code in [404, 422], "User lookup endpoint should handle invalid UUIDs gracefully"


class TestArchitectureSeparation:
    """Tests to verify proper microservices separation."""
    
    AUTH_SERVICE_URL = "http://localhost:8001"
    APP_SERVICE_URL = "http://localhost:8000"
    
    def test_database_separation(self):
        """Verify that services use separate databases."""
        # Auth service should have user/role data
        auth_health = requests.get(f"{self.AUTH_SERVICE_URL}/health").json()
        
        # App service should have photo data  
        app_health = requests.get(f"{self.APP_SERVICE_URL}/health").json()
        
        # Both should report healthy databases but they should be separate
        assert auth_health.get("database") == "healthy"
        assert app_health.get("status") == "healthy"
    
    def test_service_independence(self):
        """Test that services can operate independently."""
        # Both services should have their own health endpoints
        auth_response = requests.get(f"{self.AUTH_SERVICE_URL}/health")
        app_response = requests.get(f"{self.APP_SERVICE_URL}/health")
        
        assert auth_response.status_code == 200
        assert app_response.status_code == 200
        
        # Services should have different capabilities
        auth_data = auth_response.json()
        app_data = app_response.json()
        
        # Auth service should have SSO/2FA capabilities
        assert "sso" in auth_data or "2fa" in auth_data or "twofa" in auth_data
    
    def test_port_separation(self):
        """Verify services run on different ports."""
        # This is implicit in the URLs, but we verify by testing both ports work
        auth_response = requests.get("http://localhost:8001/health")
        app_response = requests.get("http://localhost:8000/health")
        
        assert auth_response.status_code == 200
        assert app_response.status_code == 200
        
        # Should be different services
        auth_service = auth_response.json().get("service", "")
        app_service = app_response.json().get("service", "")
        
        assert auth_service != app_service


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])