#!/usr/bin/env python3
"""
Functional Tests - User Workflows
==================================

End-to-end testing of complete user workflows including:
- User registration and email verification
- Authentication and JWT token handling
- Photo upload and management
- Permission-based access control
"""

import pytest
import requests
import jwt
import io
import subprocess
import time
from PIL import Image
from datetime import datetime, timezone, timedelta


class TestUserRegistrationWorkflow:
    """Test complete user registration and verification workflow."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    JWT_SECRET = "your-very-secure-jwt-secret-key-minimum-256-bits"
    
    def get_verification_token_from_db(self, email):
        """Get verification token from database."""
        try:
            result = subprocess.run([
                "docker", "compose", "-f", "docker-compose.separated.yml", "exec", "-T", "auth-db",
                "psql", "-U", "auth_user", "-d", "photo_share_auth", "-c", 
                f"SELECT secret FROM email_verifications WHERE email = '{email}' AND is_used = false ORDER BY created_at DESC LIMIT 1;"
            ], capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('secret') and not line.startswith('---') and len(line) > 10:
                    return line
            return None
        except:
            return None
    
    @pytest.mark.functional
    def test_complete_registration_workflow(self):
        """Test complete user registration and verification workflow."""
        # Generate unique email for this test
        timestamp = int(time.time())
        test_email = f"functional-test-{timestamp}@example.com"
        
        # Step 1: Register user
        user_data = {
            "email": test_email,
            "password": "TestPassword123!",
            "first_name": "Functional",
            "last_name": "Test"
        }
        
        response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/register", json=user_data)
        
        # Handle rate limiting
        if response.status_code == 429:
            pytest.skip("Rate limited - this is expected behavior in security testing")
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        user_info = response.json()
        assert user_info["email"] == test_email
        assert user_info["is_verified"] is False, "User should be unverified initially"
        assert "user" in user_info["roles"], "User should have default role"
        
        user_uuid = user_info["uuid"]
        user_id = user_info["id"]
        
        # Step 2: Get verification token
        verification_token = self.get_verification_token_from_db(test_email)
        assert verification_token is not None, "Verification token should be created"
        
        # Step 3: Verify email
        verify_response = requests.get(f"{self.AUTH_BASE_URL}/api/auth/verify-email/{verification_token}")
        assert verify_response.status_code == 200, f"Email verification failed: {verify_response.text}"
        
        verify_data = verify_response.json()
        assert verify_data["status"] == "verified", "Email should be verified successfully"
        assert verify_data["user_email"] == test_email
        
        # Step 4: Verify user is now verified
        user_response = requests.get(f"{self.AUTH_BASE_URL}/api/auth/users/{user_uuid}")
        assert user_response.status_code == 200, "User lookup should work after verification"
        
        verified_user = user_response.json()
        assert verified_user["is_verified"] is True, "User should be verified now"
        assert len(verified_user["permissions"]) > 0, "Verified user should have permissions"
        
        # Store for other tests
        self.test_user_data = {
            "uuid": user_uuid,
            "id": user_id,
            "email": test_email,
            "is_verified": True
        }
    
    @pytest.mark.functional
    def test_verification_request_workflow(self):
        """Test requesting new verification link workflow."""
        # Test with non-existent email (should succeed for security)
        response = requests.post(
            f"{self.AUTH_BASE_URL}/api/auth/request-verification",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should return success even for non-existent email (security feature)
        if response.status_code != 429:  # Skip if rate limited
            assert response.status_code == 200
            assert "verification link has been sent" in response.json()["message"]


class TestAuthenticationWorkflow:
    """Test authentication and JWT token workflows."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    APP_BASE_URL = "http://localhost:8000"
    JWT_SECRET = "your-very-secure-jwt-secret-key-minimum-256-bits"
    
    def create_jwt_token(self, user_uuid, user_id, email):
        """Create a JWT token for testing."""
        payload = {
            "sub": user_uuid,
            "user_id": str(user_id),
            "email": email,
            "aud": "photoshare-app",
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        return jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")
    
    @pytest.mark.functional
    def test_jwt_authentication_workflow(self):
        """Test complete JWT authentication workflow."""
        # Use existing verified user
        test_user_uuid = "05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b"
        test_user_id = 4
        test_user_email = "verify-test@example.com"
        
        # Step 1: Create JWT token
        token = self.create_jwt_token(test_user_uuid, test_user_id, test_user_email)
        assert len(token) > 0, "JWT token should be created"
        
        # Step 2: Verify token structure
        decoded = jwt.decode(token, self.JWT_SECRET, algorithms=["HS256"])
        assert decoded["sub"] == test_user_uuid
        assert decoded["user_id"] == str(test_user_id)
        assert decoded["email"] == test_user_email
        
        # Step 3: Test token with auth service
        user_response = requests.get(f"{self.AUTH_BASE_URL}/api/auth/users/{test_user_uuid}")
        assert user_response.status_code == 200, "User should exist in auth service"
        
        user_data = user_response.json()
        assert user_data["is_verified"] is True, "User should be verified"
        assert len(user_data["permissions"]) > 0, "User should have permissions"
        
        # Step 4: Test token with app service
        headers = {"Authorization": f"Bearer {token}"}
        app_response = requests.get(f"{self.APP_BASE_URL}/api/photos/", headers=headers)
        assert app_response.status_code not in [401, 403], "Valid JWT should be accepted by app service"


class TestPhotoWorkflow:
    """Test complete photo upload and management workflows."""
    
    APP_BASE_URL = "http://localhost:8000"
    JWT_SECRET = "your-very-secure-jwt-secret-key-minimum-256-bits"
    
    def create_test_image(self, color='blue', size=(150, 150)):
        """Create a test image."""
        img = Image.new('RGB', size, color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes.getvalue()
    
    def create_jwt_token(self, user_uuid="05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b", user_id=4):
        """Create a JWT token for testing."""
        payload = {
            "sub": user_uuid,
            "user_id": str(user_id),
            "email": "verify-test@example.com",
            "aud": "photoshare-app",
            "iss": "photoshare-auth",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        return jwt.encode(payload, self.JWT_SECRET, algorithm="HS256")
    
    @pytest.mark.functional
    def test_complete_photo_workflow(self):
        """Test complete photo upload, listing, and management workflow."""
        # Step 1: Create authentication
        token = self.create_jwt_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Upload photo
        image_data = self.create_test_image('green', (200, 200))
        files = {'file': ('functional-test-photo.jpg', image_data, 'image/jpeg')}
        data = {
            'title': 'Functional Test Photo',
            'description': 'Photo uploaded during functional testing',
            'is_public': 'true'
        }
        
        upload_response = requests.post(
            f"{self.APP_BASE_URL}/api/photos/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert upload_response.status_code == 200, f"Photo upload failed: {upload_response.text}"
        
        upload_data = upload_response.json()
        assert "id" in upload_data, "Upload should return photo ID"
        assert upload_data["title"] == "Functional Test Photo"
        assert upload_data["is_public"] is True
        
        photo_id = upload_data["id"]
        
        # Step 3: List user photos
        list_response = requests.get(f"{self.APP_BASE_URL}/api/photos/", headers=headers)
        assert list_response.status_code == 200, "Photo listing should work"
        
        list_data = list_response.json()
        assert list_data["total"] >= 1, "Should have at least the uploaded photo"
        
        # Find our photo in the list
        our_photo = None
        for photo in list_data.get("photos", []):
            if photo["id"] == photo_id:
                our_photo = photo
                break
        
        assert our_photo is not None, "Uploaded photo should appear in user's photo list"
        
        # Step 4: Test public photo access (no auth required)
        public_response = requests.get(f"{self.APP_BASE_URL}/api/photos/public")
        assert public_response.status_code == 200, "Public photos should be accessible"
        
        public_data = public_response.json()
        assert public_data["total"] >= 1, "Should have at least one public photo"
        
        # Our photo should be in public list since is_public=true
        public_photo_found = any(
            photo["id"] == photo_id
            for photo in public_data.get("photos", [])
        )
        assert public_photo_found, "Public photo should appear in public listing"
    
    @pytest.mark.functional
    def test_unauthorized_photo_access(self):
        """Test that unauthorized users cannot access protected photo endpoints."""
        # Test without authentication
        response = requests.get(f"{self.APP_BASE_URL}/api/photos/")
        assert response.status_code in [401, 403], "Should reject unauthorized access to user photos"
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        response = requests.get(f"{self.APP_BASE_URL}/api/photos/", headers=headers)
        assert response.status_code in [401, 403], "Should reject invalid tokens"


class TestRBACWorkflow:
    """Test Role-Based Access Control workflows."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    
    @pytest.mark.functional
    def test_rbac_permission_workflow(self):
        """Test that RBAC permissions are properly assigned and checked."""
        # Use existing verified user
        test_user_uuid = "05a4f3ec-3e12-4f4a-abf1-28338e8e5b4b"
        
        # Step 1: Get user info with roles and permissions
        user_response = requests.get(f"{self.AUTH_BASE_URL}/api/auth/users/{test_user_uuid}")
        assert user_response.status_code == 200, "User lookup should work"
        
        user_data = user_response.json()
        
        # Step 2: Verify role assignment
        assert "roles" in user_data, "User should have roles"
        assert "user" in user_data["roles"], "User should have default 'user' role"
        
        # Step 3: Verify permissions
        assert "permissions" in user_data, "User should have permissions"
        permissions = user_data["permissions"]
        assert len(permissions) > 0, "User should have at least some permissions"
        
        # Check for essential permissions
        required_permissions = ['photos:create', 'photos:read', 'photos:update', 'photos:delete']
        for perm in required_permissions:
            assert perm in permissions, f"User should have '{perm}' permission"
        
        # Step 4: Test permission lookup endpoint
        perm_response = requests.get(f"{self.AUTH_BASE_URL}/api/auth/users/{test_user_uuid}/permissions")
        assert perm_response.status_code == 200, "Permission lookup should work"
        
        perm_data = perm_response.json()
        assert "permissions" in perm_data, "Should return permissions data"


class TestServiceHealthWorkflow:
    """Test service health and availability workflows."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    APP_BASE_URL = "http://localhost:8000"
    
    @pytest.mark.functional
    def test_service_health_workflow(self):
        """Test complete service health checking workflow."""
        # Step 1: Check auth service health
        auth_response = requests.get(f"{self.AUTH_BASE_URL}/health", timeout=10)
        assert auth_response.status_code == 200, "Auth service should be healthy"
        
        auth_health = auth_response.json()
        assert auth_health["status"] == "healthy", "Auth service should report healthy status"
        assert "database" in auth_health, "Auth service should report database status"
        assert auth_health["database"] == "healthy", "Auth database should be healthy"
        
        # Step 2: Check app service health  
        app_response = requests.get(f"{self.APP_BASE_URL}/health", timeout=10)
        assert app_response.status_code == 200, "App service should be healthy"
        
        app_health = app_response.json()
        assert app_health["status"] == "healthy", "App service should report healthy status"
        
        # Step 3: Verify services are responsive
        start_time = time.time()
        requests.get(f"{self.AUTH_BASE_URL}/health")
        auth_response_time = time.time() - start_time
        
        start_time = time.time()
        requests.get(f"{self.APP_BASE_URL}/health")
        app_response_time = time.time() - start_time
        
        assert auth_response_time < 5.0, f"Auth service too slow: {auth_response_time}s"
        assert app_response_time < 5.0, f"App service too slow: {app_response_time}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "functional"])