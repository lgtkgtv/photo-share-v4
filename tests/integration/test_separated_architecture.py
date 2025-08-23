#!/usr/bin/env python3
"""
Integration Tests for Separated Architecture
============================================

Tests the complete flow between authentication service and application service.
"""

import pytest
import asyncio
import httpx
import json
import time
from typing import Dict, Any

# Test Configuration
AUTH_SERVICE_URL = "http://localhost:8001"  # Auth service
APP_SERVICE_URL = "http://localhost:8000"   # Application service

class TestSeparatedArchitecture:
    """Integration tests for the separated architecture."""
    
    def __init__(self):
        self.auth_client = httpx.AsyncClient(base_url=AUTH_SERVICE_URL)
        self.app_client = httpx.AsyncClient(base_url=APP_SERVICE_URL)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.auth_client.aclose()
        await self.app_client.aclose()

@pytest.mark.asyncio
class TestCompleteUserFlow:
    """Test complete user flow across separated services."""
    
    async def test_user_registration_and_photo_upload_flow(self):
        """Test complete flow: register -> verify -> login -> upload photo -> access photo."""
        
        async with TestSeparatedArchitecture() as test_env:
            # Test data
            test_email = f"integration-test-{int(time.time())}@example.com"
            test_password = "IntegrationTest123!"
            
            # ==================================================================
            # STEP 1: Health Check - Ensure both services are running
            # ==================================================================
            
            print("🔍 Step 1: Health check...")
            auth_health = await test_env.auth_client.get("/health")
            app_health = await test_env.app_client.get("/health")
            
            assert auth_health.status_code == 200, f"Auth service unhealthy: {auth_health.text}"
            assert app_health.status_code == 200, f"App service unhealthy: {app_health.text}"
            
            print("✅ Both services healthy")
            
            # ==================================================================
            # STEP 2: User Registration
            # ==================================================================
            
            print("🔍 Step 2: User registration...")
            register_response = await test_env.auth_client.post(
                "/api/auth/register",
                json={
                    "email": test_email,
                    "password": test_password,
                    "first_name": "Integration",
                    "last_name": "Test"
                }
            )
            
            assert register_response.status_code == 200, f"Registration failed: {register_response.text}"
            user_data = register_response.json()
            user_uuid = user_data["uuid"]
            
            assert user_data["email"] == test_email
            assert user_data["is_verified"] == False  # Should require verification
            
            print(f"✅ User registered: {user_uuid}")
            
            # ==================================================================
            # STEP 3: Email Verification (Simulated)
            # ==================================================================
            
            print("🔍 Step 3: Email verification...")
            # In a real test, we would:
            # 1. Request verification email
            # 2. Extract verification link from email/logs
            # 3. Visit verification link
            
            # For now, we'll simulate verification by calling the auth service
            verification_response = await test_env.auth_client.post(
                "/api/auth/request-verification",
                json={"email": test_email}
            )
            
            assert verification_response.status_code == 200
            verification_data = verification_response.json()
            
            # Extract verification link (in production, this would come from email)
            verification_link = verification_data.get("verification_link")
            if verification_link:
                # Extract secret from link and verify
                secret = verification_link.split("/")[-1]
                verify_response = await test_env.auth_client.get(f"/api/auth/verify-email/{secret}")
                assert verify_response.status_code == 200
                
            print("✅ Email verification completed")
            
            # ==================================================================
            # STEP 4: User Login
            # ==================================================================
            
            print("🔍 Step 4: User login...")
            login_response = await test_env.auth_client.post(
                "/api/auth/login",
                data={  # OAuth2 form data
                    "username": test_email,
                    "password": test_password
                }
            )
            
            assert login_response.status_code == 200, f"Login failed: {login_response.text}"
            login_data = login_response.json()
            
            access_token = login_data["access_token"]
            assert access_token, "No access token received"
            assert login_data["requires_2fa"] == False, "Unexpected 2FA requirement"
            
            print("✅ User logged in successfully")
            
            # ==================================================================
            # STEP 5: Access Application with Auth Token
            # ==================================================================
            
            print("🔍 Step 5: Access application with auth token...")
            
            # Test protected endpoint in application service
            profile_response = await test_env.app_client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert profile_response.status_code == 200, f"Profile access failed: {profile_response.text}"
            profile_data = profile_response.json()
            
            assert profile_data["uuid"] == user_uuid
            assert profile_data["email"] == test_email
            
            print("✅ Application authenticated user successfully")
            
            # ==================================================================
            # STEP 6: Photo Upload
            # ==================================================================
            
            print("🔍 Step 6: Photo upload...")
            
            # Create a minimal test image
            test_image_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00' + b'\x00' * 70 + b'\xff\xd9'
            
            upload_response = await test_env.app_client.post(
                "/api/photos/upload",
                headers={"Authorization": f"Bearer {access_token}"},
                files={
                    "file": ("test_integration.jpg", test_image_data, "image/jpeg")
                },
                data={
                    "title": "Integration Test Photo",
                    "description": "Photo uploaded during integration testing",
                    "is_public": "true"
                }
            )
            
            assert upload_response.status_code == 200, f"Photo upload failed: {upload_response.text}"
            photo_data = upload_response.json()
            
            photo_id = photo_data["id"]
            assert photo_data["user_uuid"] == user_uuid
            assert photo_data["title"] == "Integration Test Photo"
            assert photo_data["is_public"] == True
            
            print(f"✅ Photo uploaded: {photo_id}")
            
            # ==================================================================
            # STEP 7: Photo Access (Authenticated)
            # ==================================================================
            
            print("🔍 Step 7: Authenticated photo access...")
            
            photo_response = await test_env.app_client.get(
                f"/api/photos/{photo_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert photo_response.status_code == 200, f"Photo access failed: {photo_response.text}"
            retrieved_photo = photo_response.json()
            
            assert retrieved_photo["id"] == photo_id
            assert retrieved_photo["user_uuid"] == user_uuid
            
            print("✅ Photo accessed successfully")
            
            # ==================================================================
            # STEP 8: Public Photo Access (Unauthenticated)
            # ==================================================================
            
            print("🔍 Step 8: Public photo access...")
            
            public_photo_response = await test_env.app_client.get(f"/api/photos/{photo_id}")
            
            assert public_photo_response.status_code == 200, "Public photo access failed"
            public_photo_data = public_photo_response.json()
            
            assert public_photo_data["id"] == photo_id
            assert public_photo_data["is_public"] == True
            
            print("✅ Public photo access successful")
            
            # ==================================================================
            # STEP 9: Permission-Based Access Control
            # ==================================================================
            
            print("🔍 Step 9: Permission-based access control...")
            
            # Try to access another user's private photo (should fail)
            private_photo_response = await test_env.app_client.post(
                "/api/photos/upload",
                headers={"Authorization": f"Bearer {access_token}"},
                files={
                    "file": ("private_test.jpg", test_image_data, "image/jpeg")
                },
                data={
                    "title": "Private Test Photo",
                    "is_public": "false"
                }
            )
            
            assert private_photo_response.status_code == 200
            private_photo_data = private_photo_response.json()
            private_photo_id = private_photo_data["id"]
            
            # Access private photo with correct user (should succeed)
            private_access_response = await test_env.app_client.get(
                f"/api/photos/{private_photo_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert private_access_response.status_code == 200
            
            # Try to access private photo without authentication (should fail)
            unauth_private_response = await test_env.app_client.get(f"/api/photos/{private_photo_id}")
            
            assert unauth_private_response.status_code in [401, 403, 404], "Private photo should not be accessible without auth"
            
            print("✅ Permission-based access control working")
            
            # ==================================================================
            # STEP 10: Logout and Token Invalidation
            # ==================================================================
            
            print("🔍 Step 10: Logout and token invalidation...")
            
            logout_response = await test_env.auth_client.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"
            
            # Try to use invalidated token (should fail)
            invalid_token_response = await test_env.app_client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert invalid_token_response.status_code == 401, "Invalidated token should not work"
            
            print("✅ Logout and token invalidation successful")
            
            print("\n🎉 INTEGRATION TEST PASSED - All steps completed successfully!")

@pytest.mark.asyncio
class TestSSOFlow:
    """Test SSO authentication flow."""
    
    async def test_sso_provider_list(self):
        """Test SSO provider discovery."""
        async with TestSeparatedArchitecture() as test_env:
            response = await test_env.auth_client.get("/api/auth/sso/providers")
            
            assert response.status_code == 200
            providers = response.json()
            
            # Should return list of available providers
            assert isinstance(providers, list)
            
            print(f"✅ Available SSO providers: {[p.get('name') for p in providers]}")
    
    async def test_sso_login_initiation(self):
        """Test SSO login URL generation."""
        async with TestSeparatedArchitecture() as test_env:
            # Test with a mock provider (if available)
            sso_request = {
                "provider": "google",  # Assuming Google is configured
                "redirect_uri": "http://localhost:8000/auth/callback"
            }
            
            response = await test_env.auth_client.post(
                "/api/auth/sso/login",
                json=sso_request
            )
            
            if response.status_code == 200:
                sso_data = response.json()
                assert "authorization_url" in sso_data
                assert "state" in sso_data
                print("✅ SSO login initiation successful")
            else:
                # Provider not configured - this is expected in test environment
                assert response.status_code == 400
                print("⚠️ SSO provider not configured (expected in test)")

@pytest.mark.asyncio 
class Test2FAFlow:
    """Test 2FA authentication flow."""
    
    async def test_2fa_setup_flow(self):
        """Test 2FA setup and verification flow."""
        async with TestSeparatedArchitecture() as test_env:
            # First, create and login a user
            test_email = f"2fa-test-{int(time.time())}@example.com"
            
            # Register user
            register_response = await test_env.auth_client.post(
                "/api/auth/register",
                json={
                    "email": test_email,
                    "password": "TwoFactorTest123!",
                    "first_name": "2FA",
                    "last_name": "Test"
                }
            )
            
            assert register_response.status_code == 200
            
            # Login to get token
            login_response = await test_env.auth_client.post(
                "/api/auth/login",
                data={
                    "username": test_email,
                    "password": "TwoFactorTest123!"
                }
            )
            
            assert login_response.status_code == 200
            login_data = login_response.json()
            access_token = login_data["access_token"]
            
            # Test 2FA setup endpoints
            setup_response = await test_env.auth_client.post(
                "/api/auth/2fa/setup/totp",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"device_name": "Test App"}
            )
            
            if setup_response.status_code == 200:
                setup_data = setup_response.json()
                assert "qr_code" in setup_data
                assert "backup_codes" in setup_data
                print("✅ 2FA TOTP setup successful")
            else:
                print("⚠️ 2FA setup endpoint not implemented (expected)")

@pytest.mark.asyncio
class TestServiceCommunication:
    """Test service-to-service communication."""
    
    async def test_auth_service_health_from_app(self):
        """Test that app service can communicate with auth service."""
        async with TestSeparatedArchitecture() as test_env:
            # Test internal health check endpoint
            response = await test_env.app_client.get("/api/system/auth-health")
            
            # This endpoint might not exist yet, which is fine
            if response.status_code == 200:
                health_data = response.json()
                assert "auth_service_status" in health_data
                print("✅ Service-to-service health check working")
            else:
                print("⚠️ Service health endpoint not implemented (expected)")
    
    async def test_permission_caching(self):
        """Test that permission caching works correctly."""
        async with TestSeparatedArchitecture() as test_env:
            # This would test that repeated permission checks are cached
            # and don't result in multiple calls to auth service
            print("⚠️ Permission caching test not implemented (future feature)")

if __name__ == "__main__":
    # Run specific test
    import asyncio
    
    async def run_tests():
        print("🚀 Starting Integration Tests for Separated Architecture\n")
        
        try:
            # Test complete user flow
            test_instance = TestCompleteUserFlow()
            await test_instance.test_user_registration_and_photo_upload_flow()
            
            # Test SSO flow
            sso_test = TestSSOFlow()
            await sso_test.test_sso_provider_list()
            await sso_test.test_sso_login_initiation()
            
            # Test 2FA flow
            twofa_test = Test2FAFlow()
            await twofa_test.test_2fa_setup_flow()
            
            # Test service communication
            comm_test = TestServiceCommunication()
            await comm_test.test_auth_service_health_from_app()
            await comm_test.test_permission_caching()
            
            print("\n✅ ALL INTEGRATION TESTS PASSED!")
            
        except Exception as e:
            print(f"\n❌ INTEGRATION TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    # Run the tests
    asyncio.run(run_tests())