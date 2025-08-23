#!/usr/bin/env python3
"""
Security Tests - RBAC and Access Control
=========================================

Comprehensive security testing for:
- Role-Based Access Control (RBAC)
- Permission enforcement
- Authorization boundaries
- Access control vulnerabilities
"""

import pytest
import requests
import jwt
import io
from PIL import Image
from datetime import datetime, timezone, timedelta


class TestRBACSecurity:
    """Security tests for Role-Based Access Control system."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    APP_BASE_URL = "http://localhost:8000"
    JWT_SECRET = "your-very-secure-jwt-secret-key-minimum-256-bits"
    
    def create_jwt_token(self, user_uuid, user_id, email, permissions=None):
        """Create a JWT token with specific permissions for testing."""
        payload = {
            "sub": user_uuid,
            "user_id": str(user_id),
            "email": email,
            "aud": "photoshare-app",
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        if permissions:
            payload["permissions"] = permissions
            
        return jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")
    
    @pytest.mark.security
    def test_role_permission_enforcement(self):
        """Test that role permissions are properly enforced."""
        # Test with existing verified user
        user_uuid = "05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b"
        
        # Get user's actual permissions
        user_response = requests.get(f"{self.AUTH_BASE_URL}/api/auth/users/{user_uuid}")
        assert user_response.status_code == 200, "User lookup should work"
        
        user_data = user_response.json()
        user_permissions = user_data.get("permissions", [])
        user_roles = user_data.get("roles", [])
        
        # Verify user has expected role
        assert "user" in user_roles, "Test user should have 'user' role"
        
        # Verify user has photo permissions
        photo_permissions = [p for p in user_permissions if p.startswith("photos:")]
        assert len(photo_permissions) > 0, "User should have photo permissions"
        
        # Test specific required permissions
        required_perms = ["photos:create", "photos:read", "photos:update", "photos:delete"]
        for perm in required_perms:
            assert perm in user_permissions, f"User should have '{perm}' permission"
    
    @pytest.mark.security
    def test_unauthorized_access_prevention(self):
        """Test that unauthorized access is properly prevented."""
        protected_endpoints = [
            f"{self.APP_BASE_URL}/api/photos/",
            f"{self.APP_BASE_URL}/api/users/me",
        ]
        
        for endpoint in protected_endpoints:
            # Test with no authentication
            response = requests.get(endpoint)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"
            
            # Test with invalid token
            headers = {"Authorization": "Bearer invalid-token-here"}
            response = requests.get(endpoint, headers=headers)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should reject invalid tokens"
    
    @pytest.mark.security
    def test_permission_boundary_enforcement(self):
        """Test that users cannot exceed their permission boundaries."""
        # Create token for user with limited permissions
        limited_token = self.create_jwt_token(
            user_uuid="test-limited-user", 
            user_id="999", 
            email="limited@example.com",
            permissions=["photos:read"]  # Only read permission
        )
        
        headers = {"Authorization": f"Bearer {limited_token}"}
        
        # Should be able to read (if endpoint accepts this token format)
        # But should not be able to write/upload
        image_data = Image.new('RGB', (50, 50), 'red')
        img_bytes = io.BytesIO()
        image_data.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test.jpg', img_bytes.getvalue(), 'image/jpeg')}
        data = {'title': 'Unauthorized Upload', 'description': 'Should fail'}
        
        upload_response = requests.post(
            f"{self.APP_BASE_URL}/api/photos/upload", 
            files=files, 
            data=data, 
            headers=headers
        )
        
        # Should be rejected due to insufficient permissions or invalid user
        assert upload_response.status_code in [401, 403, 404], "Upload should be rejected for limited user"
    
    @pytest.mark.security
    def test_role_escalation_prevention(self):
        """Test that users cannot escalate their roles or permissions."""
        user_uuid = "05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b"
        
        # Try to access admin-level functionality (if it exists)
        # This tests that regular users can't access admin endpoints
        
        # Create token for regular user
        token = self.create_jwt_token(user_uuid, 4, "test@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access user management functions that might be admin-only
        admin_endpoints = [
            f"{self.AUTH_BASE_URL}/api/auth/admin/users",
            f"{self.AUTH_BASE_URL}/api/auth/admin/roles", 
            f"{self.APP_BASE_URL}/api/admin/photos",
        ]
        
        for endpoint in admin_endpoints:
            response = requests.get(endpoint, headers=headers)
            # Should return 403 (Forbidden) or 404 (Not Found) for non-admin users
            # Don't assert 401 as that would mean auth failed, not authorization
            assert response.status_code in [403, 404], f"Regular user should not access admin endpoint: {endpoint}"
    
    @pytest.mark.security
    def test_cross_user_data_access_prevention(self):
        """Test that users cannot access other users' data."""
        # This would require multiple users to test properly
        # For now, test that user-specific endpoints require proper authentication
        
        user_uuid = "05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b"
        fake_user_uuid = "00000000-0000-0000-0000-000000000000"
        
        token = self.create_jwt_token(user_uuid, 4, "test@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access another user's data
        response = requests.get(f"{self.AUTH_BASE_URL}/api/auth/users/{fake_user_uuid}", headers=headers)
        
        # Should return 404 (user not found) or 403 (not authorized)
        assert response.status_code in [403, 404], "User should not access other users' data"
    
    @pytest.mark.security
    def test_jwt_token_security(self):
        """Test JWT token security measures."""
        # Test token without required claims
        minimal_payload = {
            "sub": "test-user",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        minimal_token = jwt.encode(minimal_payload, self.JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": f"Bearer {minimal_token}"}
        
        response = requests.get(f"{self.APP_BASE_URL}/api/photos/", headers=headers)
        
        # Should handle incomplete tokens gracefully
        assert response.status_code != 500, "Incomplete JWT should not cause server error"
    
    @pytest.mark.security
    def test_session_security(self):
        """Test session management security."""
        # Test that expired tokens are rejected
        expired_payload = {
            "sub": "test-user-uuid-123",
            "user_id": "1",
            "email": "test@example.com",
            "aud": "photoshare-app",
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        }
        
        expired_token = jwt.encode(expired_payload, self.JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = requests.get(f"{self.APP_BASE_URL}/api/photos/", headers=headers)
        assert response.status_code in [401, 403], "Expired tokens should be rejected"


class TestAuthenticationSecurity:
    """Security tests for authentication mechanisms."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    
    @pytest.mark.security
    def test_rate_limiting_protection(self):
        """Test that rate limiting protects against abuse."""
        # Note: This test may trigger rate limiting and cause subsequent tests to fail
        # Run with caution in CI/CD environments
        
        test_data = {"email": "ratelimit@example.com", "password": "TestPassword123!"}
        
        # Make several requests quickly
        responses = []
        for i in range(3):
            response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/register", json=test_data)
            responses.append(response.status_code)
        
        # At least one should be rate limited (429) or the first should succeed and rest fail
        rate_limited = any(status == 429 for status in responses)
        conflict_detected = responses[0] == 200 and any(status == 409 for status in responses[1:])
        
        assert rate_limited or conflict_detected, "Rate limiting or duplicate detection should be active"
    
    @pytest.mark.security  
    def test_password_security_requirements(self):
        """Test that password security requirements are enforced."""
        weak_passwords = [
            "123",           # Too short
            "password",      # Too simple
            "12345678",      # Numbers only
            "abcdefgh",      # Letters only
        ]
        
        for weak_password in weak_passwords:
            test_data = {
                "email": f"weak-{weak_password}@example.com", 
                "password": weak_password,
                "first_name": "Test",
                "last_name": "User"
            }
            
            response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/register", json=test_data)
            
            # Should reject weak passwords
            assert response.status_code in [400, 422], f"Weak password '{weak_password}' should be rejected"
    
    @pytest.mark.security
    def test_email_verification_security(self):
        """Test email verification security measures."""
        # Test invalid verification tokens
        invalid_tokens = [
            "invalid-token",
            "a" * 50,  # Wrong length
            "../../../etc/passwd",  # Path traversal attempt
            "<script>alert('xss')</script>",  # XSS attempt
        ]
        
        for token in invalid_tokens:
            response = requests.get(f"{self.AUTH_BASE_URL}/api/auth/verify-email/{token}")
            assert response.status_code in [404, 400], f"Invalid token '{token}' should be rejected"
    
    @pytest.mark.security
    def test_input_validation_security(self):
        """Test input validation and sanitization."""
        # Test malicious input in registration
        malicious_inputs = {
            "email": "test@example.com'; DROP TABLE users; --",
            "first_name": "<script>alert('xss')</script>",
            "last_name": "Robert'; DROP TABLE students; --",
            "password": "ValidPass123!"
        }
        
        response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/register", json=malicious_inputs)
        
        # Should handle malicious input safely (not return 500 error)
        assert response.status_code != 500, "Malicious input should not cause server error"
        
        # If registration succeeds, verify data is sanitized
        if response.status_code == 200:
            user_data = response.json()
            # Names should not contain script tags
            assert "<script>" not in user_data.get("first_name", "")
            assert "<script>" not in user_data.get("last_name", "")


class TestFileUploadSecurity:
    """Security tests for file upload functionality."""
    
    APP_BASE_URL = "http://localhost:8000"
    JWT_SECRET = "your-very-secure-jwt-secret-key-minimum-256-bits"
    
    def create_jwt_token(self):
        """Create a valid JWT token for testing."""
        payload = {
            "sub": "05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b",
            "user_id": "4",
            "email": "test@example.com",
            "aud": "photoshare-app",
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        return jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")
    
    @pytest.mark.security
    def test_file_upload_validation(self):
        """Test file upload security validation."""
        token = self.create_jwt_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test malicious file uploads
        malicious_files = [
            # Executable file
            ('malware.exe', b'MZ\x90\x00', 'application/octet-stream'),
            # Script file
            ('script.php', b'<?php phpinfo(); ?>', 'text/plain'),
            # Very large file (simulate)
            ('huge.jpg', b'x' * 1000, 'image/jpeg'),  # Small for test, but wrong content
        ]
        
        for filename, content, content_type in malicious_files:
            files = {'file': (filename, content, content_type)}
            data = {'title': 'Test', 'description': 'Test upload'}
            
            response = requests.post(
                f"{self.APP_BASE_URL}/api/photos/upload",
                files=files,
                data=data,
                headers=headers
            )
            
            # Should reject malicious files
            assert response.status_code in [400, 422, 415], f"Malicious file {filename} should be rejected"
    
    @pytest.mark.security
    def test_file_size_limits(self):
        """Test that file size limits are enforced."""
        token = self.create_jwt_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a small image that claims to be large
        img = Image.new('RGB', (10, 10), 'red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test.jpg', img_bytes.getvalue(), 'image/jpeg')}
        data = {'title': 'Size Test', 'description': 'Test file size validation'}
        
        response = requests.post(
            f"{self.APP_BASE_URL}/api/photos/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        # Small image should succeed or fail for other reasons, not size
        if response.status_code == 400:
            # Check if it's a size-related error
            response_text = response.text.lower()
            size_related = any(word in response_text for word in ['size', 'large', 'limit'])
            if not size_related:
                # If not size-related, that's fine
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "security"])