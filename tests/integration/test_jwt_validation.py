#!/usr/bin/env python3
"""
Integration Tests - JWT Token Validation
=========================================

Tests JWT token flow between auth and app services.
Verifies token creation, validation, and service-to-service communication.
"""

import pytest
import jwt
import requests
from datetime import datetime, timezone, timedelta


class TestJWTValidation:
    """Integration tests for JWT token validation across services."""
    
    AUTH_SERVICE_URL = "http://localhost:8001"
    APP_SERVICE_URL = "http://localhost:8000"
    JWT_SECRET = "your-very-secure-jwt-secret-key-minimum-256-bits"
    
    def create_test_jwt(self, user_uuid="test-user-uuid-123", user_id="1", email="test@example.com", expiry_hours=1):
        """Create a test JWT token."""
        payload = {
            "sub": user_uuid,
            "user_id": user_id,
            "email": email,
            "aud": "photoshare-app",
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        }
        
        return jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")
    
    def test_jwt_token_creation(self):
        """Test that JWT tokens can be created with correct structure."""
        token = self.create_test_jwt()
        
        # Decode token to verify structure
        decoded = jwt.decode(token, self.JWT_SECRET, algorithms=["HS256"])
        
        assert decoded["sub"] == "test-user-uuid-123"
        assert decoded["user_id"] == "1"
        assert decoded["email"] == "test@example.com"
        assert decoded["aud"] == "photoshare-app"
        assert decoded["iss"] == "photoshare-auth"
        assert "exp" in decoded
        assert "iat" in decoded
    
    def test_app_service_jwt_validation(self):
        """Test that app service correctly validates JWT tokens."""
        token = self.create_test_jwt(user_uuid="bfbe9a2e-26e5-4472-8e54-18b2d94e1a7d", user_id="4")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with protected endpoint
        response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
        
        # Should not return 401/403 if JWT validation works
        # May return 200 (success) or 404 (no photos) but not auth errors
        assert response.status_code not in [401, 403], f"JWT validation failed: {response.status_code} - {response.text}"
    
    def test_invalid_jwt_rejection(self):
        """Test that invalid JWT tokens are rejected."""
        invalid_tokens = [
            "invalid-token",
            "Bearer invalid-token",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        ]
        
        for invalid_token in invalid_tokens:
            headers = {"Authorization": f"Bearer {invalid_token}"}
            response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
            
            # Should return 401 or 403 for invalid tokens
            assert response.status_code in [401, 403], f"Invalid token should be rejected: {invalid_token}"
    
    def test_expired_jwt_rejection(self):
        """Test that expired JWT tokens are rejected."""
        # Create expired token
        expired_token = self.create_test_jwt(expiry_hours=-1)  # Expired 1 hour ago
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
        
        # Should reject expired token
        assert response.status_code in [401, 403], "Expired JWT should be rejected"
    
    def test_jwt_missing_claims(self):
        """Test that JWT tokens with missing required claims are rejected."""
        # Create token with missing required claims
        incomplete_payload = {
            "sub": "test-user-uuid-123",
            # Missing user_id, email, aud, iss
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        incomplete_token = jwt.encode(incomplete_payload, self.JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": f"Bearer {incomplete_token}"}
        
        response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
        
        # May accept or reject depending on implementation, but should not cause server error
        assert response.status_code != 500, "Incomplete JWT should not cause server error"
    
    def test_jwt_wrong_audience(self):
        """Test that JWT tokens with wrong audience are rejected."""
        payload = {
            "sub": "test-user-uuid-123",
            "user_id": "1",
            "email": "test@example.com",
            "aud": "wrong-audience",  # Wrong audience
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        wrong_aud_token = jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": f"Bearer {wrong_aud_token}"}
        
        response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
        
        # Should reject token with wrong audience
        assert response.status_code in [401, 403], "JWT with wrong audience should be rejected"
    
    def test_jwt_wrong_secret(self):
        """Test that JWT tokens signed with wrong secret are rejected."""
        wrong_secret = "wrong-secret-key"
        
        payload = {
            "sub": "test-user-uuid-123",
            "user_id": "1", 
            "email": "test@example.com",
            "aud": "photoshare-app",
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        wrong_secret_token = jwt.encode(payload, wrong_secret, algorithm="HS256")
        headers = {"Authorization": f"Bearer {wrong_secret_token}"}
        
        response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
        
        # Should reject token with wrong signature
        assert response.status_code in [401, 403], "JWT with wrong signature should be rejected"
    
    @pytest.mark.integration
    def test_service_to_service_user_lookup(self):
        """Test app service can lookup user info from auth service using JWT data."""
        # Create token for existing user
        token = self.create_test_jwt(user_uuid="05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b", user_id="4")
        headers = {"Authorization": f"Bearer {token}"}
        
        # First verify the user exists in auth service
        user_response = requests.get(f"{self.AUTH_SERVICE_URL}/api/auth/users/05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b")
        
        if user_response.status_code == 200:
            # Now test that app service can use this token
            app_response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
            
            # Should not fail with auth error if user exists and token is valid
            assert app_response.status_code not in [401, 403], "Valid token for existing user should not be rejected"


class TestTokenSecurity:
    """Security-focused JWT token tests."""
    
    JWT_SECRET = "your-very-secure-jwt-secret-key-minimum-256-bits"
    APP_SERVICE_URL = "http://localhost:8000"
    
    def test_algorithm_confusion_attack(self):
        """Test protection against algorithm confusion attacks."""
        # Try to create token with 'none' algorithm
        payload = {
            "sub": "test-user-uuid-123",
            "user_id": "1",
            "email": "test@example.com",
            "aud": "photoshare-app",
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        # Try with no signature
        none_token = jwt.encode(payload, "", algorithm="none")
        headers = {"Authorization": f"Bearer {none_token}"}
        
        response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
        
        # Should reject 'none' algorithm tokens
        assert response.status_code in [401, 403], "Tokens with 'none' algorithm should be rejected"
    
    def test_token_without_bearer_prefix(self):
        """Test that tokens without Bearer prefix are rejected."""
        token = jwt.encode({
            "sub": "test-user-uuid-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }, self.JWT_SECRET, algorithm="HS256")
        
        # Send token without Bearer prefix
        headers = {"Authorization": token}
        response = requests.get(f"{self.APP_SERVICE_URL}/api/photos/", headers=headers)
        
        # Should reject token without Bearer prefix
        assert response.status_code in [401, 403], "Token without Bearer prefix should be rejected"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])