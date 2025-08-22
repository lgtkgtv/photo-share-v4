#!/usr/bin/env python3
"""
End-to-End Tests for User Registration and Onboarding.

Complete user journey testing from initial registration through 
first photo upload and social interaction.
"""

import pytest
import os
import sys
import asyncio
import time
from datetime import datetime, timedelta

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteUserRegistration:
    """Test complete user registration and onboarding journey."""

    async def test_complete_user_onboarding_journey(self, async_test_client: AsyncClient):
        """Test complete user onboarding from registration to first social interaction."""
        
        # Generate unique test data
        timestamp = int(time.time())
        user_email = f"e2e_user_{timestamp}@example.com"
        user_password = "SecurePassword123!"
        
        # Step 1: User Registration
        print("🔹 Step 1: User Registration")
        registration_data = {
            "email": user_email,
            "password": user_password
        }
        
        register_response = await async_test_client.post(
            "/api/users/register",
            json=registration_data
        )
        
        assert register_response.status_code == 200
        user_data = register_response.json()
        assert user_data["email"] == user_email
        assert user_data["is_verified"] is False
        user_id = user_data["id"]
        
        print(f"   ✅ User registered successfully: {user_email}")
        
        # Step 2: Email Verification Request
        print("🔹 Step 2: Email Verification Request")
        verification_request = await async_test_client.post(
            "/api/users/request-verification",
            json={"email": user_email}
        )
        
        assert verification_request.status_code == 200
        verification_data = verification_request.json()
        assert "verification_link" in verification_data
        
        # Extract verification secret
        verification_link = verification_data["verification_link"]
        verification_secret = verification_link.split("/")[-1]
        
        print(f"   ✅ Verification email requested successfully")
        
        # Step 3: Email Verification
        print("🔹 Step 3: Email Verification")
        verify_response = await async_test_client.get(
            f"/api/users/verify/{verification_secret}"
        )
        
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["user"]["is_verified"] is True
        
        print(f"   ✅ Email verified successfully")
        
        # Step 4: User Login
        print("🔹 Step 4: User Login")
        login_data = {
            "username": user_email,
            "password": user_password
        }
        
        login_response = await async_test_client.post(
            "/api/users/login",
            data=login_data
        )
        
        assert login_response.status_code == 200
        login_result = login_response.json()
        access_token = login_result["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        print(f"   ✅ User logged in successfully")
        
        # Step 5: Create User Profile
        print("🔹 Step 5: Create User Profile")
        profile_data = {
            "display_name": f"Test User {timestamp}",
            "bio": "I'm new to this photo sharing platform and excited to share my photos!",
            "location": "Test City, Test Country",
            "is_private": False,
            "allow_comments": True,
            "allow_tags": True
        }
        
        profile_response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        
        assert profile_response.status_code == 200
        profile_result = profile_response.json()
        assert profile_result["display_name"] == profile_data["display_name"]
        
        print(f"   ✅ User profile created successfully")
        
        # Step 6: Create First Album
        print("🔹 Step 6: Create First Album")
        album_data = {
            "name": "My First Album",
            "description": "This is my very first photo album on the platform!",
            "is_public": True
        }
        
        album_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        
        assert album_response.status_code == 200
        album_result = album_response.json()
        album_id = album_result["id"]
        
        print(f"   ✅ First album created successfully")
        
        # Step 7: Upload First Photo (simulated)
        print("🔹 Step 7: Upload First Photo")
        # Create a minimal valid image for testing
        image_data = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82'
            b'<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02'
            b'\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00'
            b'\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11'
            b'\x00\x3f\x00\xaa\xff\xd9'
        )
        
        # Create temporary file for upload
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(image_data)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("first_photo.jpg", file, "image/jpeg")}
                photo_data = {
                    "title": "My First Photo",
                    "description": "This is my very first photo on the platform!",
                    "is_public": True
                }
                
                upload_response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=photo_data,
                    headers=auth_headers
                )
            
            assert upload_response.status_code == 200
            photo_result = upload_response.json()
            photo_id = photo_result["id"]
            
            print(f"   ✅ First photo uploaded successfully")
            
        finally:
            os.unlink(temp_file_path)
        
        # Step 8: Add Photo to Album
        print("🔹 Step 8: Add Photo to Album")
        add_to_album_response = await async_test_client.post(
            f"/api/albums/{album_id}/photos/{photo_id}",
            headers=auth_headers
        )
        
        assert add_to_album_response.status_code == 200
        
        print(f"   ✅ Photo added to album successfully")
        
        # Step 9: Add Tags to Photo
        print("🔹 Step 9: Add Tags to Photo")
        tag_data = {
            "tags": ["first-photo", "newbie", "excited", "photography", "sharing"]
        }
        
        tag_response = await async_test_client.post(
            f"/api/photos/{photo_id}/tags",
            json=tag_data,
            headers=auth_headers
        )
        
        assert tag_response.status_code == 200
        
        print(f"   ✅ Tags added to photo successfully")
        
        # Step 10: Create a Share Link
        print("🔹 Step 10: Create Share Link")
        share_data = {
            "title": "Check out my first photo!",
            "description": "I just joined this platform and wanted to share my first photo with you.",
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "allow_download": True
        }
        
        share_response = await async_test_client.post(
            f"/api/photos/{photo_id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        assert share_response.status_code == 200
        share_result = share_response.json()
        share_token = share_result["share_token"]
        
        print(f"   ✅ Share link created successfully")
        
        # Step 11: Test Share Link Access (Simulating friend accessing the link)
        print("🔹 Step 11: Test Share Link Access")
        share_access_response = await async_test_client.get(
            f"/api/shared/{share_token}"
        )
        
        assert share_access_response.status_code == 200
        shared_photo_data = share_access_response.json()
        assert shared_photo_data["photo"]["id"] == photo_id
        
        print(f"   ✅ Share link accessible successfully")
        
        # Step 12: Verify Complete User Journey
        print("🔹 Step 12: Verify Complete User Journey")
        
        # Check user profile
        profile_check = await async_test_client.get(
            "/api/profiles/me",
            headers=auth_headers
        )
        assert profile_check.status_code == 200
        
        # Check user's photos
        photos_check = await async_test_client.get(
            "/api/photos/",
            headers=auth_headers
        )
        assert photos_check.status_code == 200
        user_photos = photos_check.json()
        assert len(user_photos) >= 1
        
        # Check user's albums
        albums_check = await async_test_client.get(
            "/api/albums",
            headers=auth_headers
        )
        assert albums_check.status_code == 200
        user_albums = albums_check.json()
        assert len(user_albums) >= 1
        
        # Check user's shares
        shares_check = await async_test_client.get(
            "/api/shares",
            headers=auth_headers
        )
        assert shares_check.status_code == 200
        user_shares = shares_check.json()
        assert len(user_shares) >= 1
        
        print(f"   ✅ User journey verification completed successfully")
        
        print("\n🎉 Complete user onboarding journey test PASSED!")
        print(f"   User: {user_email}")
        print(f"   Profile: {profile_data['display_name']}")
        print(f"   Albums: {len(user_albums)}")
        print(f"   Photos: {len(user_photos)}")
        print(f"   Shares: {len(user_shares)}")

    async def test_user_registration_validation_journey(self, async_test_client: AsyncClient):
        """Test user registration with various validation scenarios."""
        
        print("🔹 Testing User Registration Validation Journey")
        
        # Test 1: Invalid email format
        invalid_email_data = {
            "email": "not-an-email",
            "password": "ValidPassword123!"
        }
        
        response = await async_test_client.post(
            "/api/users/register",
            json=invalid_email_data
        )
        assert response.status_code == 422
        print("   ✅ Invalid email format properly rejected")
        
        # Test 2: Weak password
        weak_password_data = {
            "email": "test@example.com",
            "password": "123"
        }
        
        response = await async_test_client.post(
            "/api/users/register",
            json=weak_password_data
        )
        assert response.status_code == 422
        print("   ✅ Weak password properly rejected")
        
        # Test 3: Valid registration
        timestamp = int(time.time())
        valid_data = {
            "email": f"valid_user_{timestamp}@example.com",
            "password": "StrongPassword123!"
        }
        
        response = await async_test_client.post(
            "/api/users/register",
            json=valid_data
        )
        assert response.status_code == 200
        print("   ✅ Valid registration accepted")
        
        # Test 4: Duplicate email
        response = await async_test_client.post(
            "/api/users/register",
            json=valid_data
        )
        assert response.status_code == 400
        print("   ✅ Duplicate email properly rejected")

    async def test_multi_user_interaction_journey(self, async_test_client: AsyncClient):
        """Test interaction between multiple users."""
        
        print("🔹 Testing Multi-User Interaction Journey")
        
        timestamp = int(time.time())
        
        # Create two users
        users = []
        for i in range(2):
            user_data = {
                "email": f"user_{i}_{timestamp}@example.com",
                "password": "TestPassword123!"
            }
            
            # Register user
            register_response = await async_test_client.post(
                "/api/users/register",
                json=user_data
            )
            assert register_response.status_code == 200
            
            # Request verification
            verification_request = await async_test_client.post(
                "/api/users/request-verification",
                json={"email": user_data["email"]}
            )
            verification_link = verification_request.json()["verification_link"]
            verification_secret = verification_link.split("/")[-1]
            
            # Verify email
            await async_test_client.get(f"/api/users/verify/{verification_secret}")
            
            # Login
            login_response = await async_test_client.post(
                "/api/users/login",
                data={
                    "username": user_data["email"],
                    "password": user_data["password"]
                }
            )
            
            access_token = login_response.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            
            users.append({
                "email": user_data["email"],
                "headers": auth_headers,
                "user_id": register_response.json()["id"]
            })
        
        print(f"   ✅ Created {len(users)} test users")
        
        # User 1 creates a public photo
        user1_headers = users[0]["headers"]
        
        # Create minimal image
        image_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9'
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(image_data)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("social_photo.jpg", file, "image/jpeg")}
                photo_data = {
                    "title": "Social Test Photo",
                    "description": "Photo for testing social interactions",
                    "is_public": True
                }
                
                upload_response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=photo_data,
                    headers=user1_headers
                )
            
            assert upload_response.status_code == 200
            photo_id = upload_response.json()["id"]
            
        finally:
            os.unlink(temp_file_path)
        
        print("   ✅ User 1 uploaded public photo")
        
        # User 2 interacts with User 1's photo
        user2_headers = users[1]["headers"]
        
        # Like the photo
        like_response = await async_test_client.post(
            f"/api/photos/{photo_id}/like",
            headers=user2_headers
        )
        assert like_response.status_code == 200
        print("   ✅ User 2 liked User 1's photo")
        
        # Comment on the photo
        comment_data = {"content": "Great photo! Love the composition."}
        comment_response = await async_test_client.post(
            f"/api/photos/{photo_id}/comments",
            json=comment_data,
            headers=user2_headers
        )
        assert comment_response.status_code == 200
        print("   ✅ User 2 commented on User 1's photo")
        
        # User 1 replies to the comment
        comment_id = comment_response.json()["id"]
        reply_data = {
            "content": "Thank you! I appreciate the feedback.",
            "parent_id": comment_id
        }
        
        reply_response = await async_test_client.post(
            f"/api/photos/{photo_id}/comments",
            json=reply_data,
            headers=user1_headers
        )
        assert reply_response.status_code == 200
        print("   ✅ User 1 replied to User 2's comment")
        
        # Verify social interactions
        comments_response = await async_test_client.get(
            f"/api/photos/{photo_id}/comments",
            headers=user1_headers
        )
        comments = comments_response.json()
        assert len(comments) >= 2  # Original comment + reply
        
        likes_response = await async_test_client.get(
            f"/api/photos/{photo_id}/likes",
            headers=user1_headers
        )
        likes = likes_response.json()
        assert len(likes) >= 1
        
        print("   ✅ Social interactions verified successfully")
        
        print("\n🎉 Multi-user interaction journey test PASSED!")


@pytest.mark.e2e
@pytest.mark.performance
class TestUserOnboardingPerformance:
    """Test performance of user onboarding process."""

    async def test_registration_performance(self, async_test_client: AsyncClient):
        """Test registration process performance."""
        
        timestamp = int(time.time())
        user_data = {
            "email": f"perf_user_{timestamp}@example.com",
            "password": "TestPassword123!"
        }
        
        # Measure registration time
        start_time = time.time()
        response = await async_test_client.post(
            "/api/users/register",
            json=user_data
        )
        registration_time = time.time() - start_time
        
        assert response.status_code == 200
        assert registration_time < 2.0, f"Registration took {registration_time:.2f}s, should be < 2.0s"
        
        print(f"✅ Registration completed in {registration_time:.2f}s")

    async def test_login_performance(self, async_test_client: AsyncClient):
        """Test login process performance."""
        
        # First create and verify a user
        timestamp = int(time.time())
        user_data = {
            "email": f"login_perf_{timestamp}@example.com",
            "password": "TestPassword123!"
        }
        
        # Register
        await async_test_client.post("/api/users/register", json=user_data)
        
        # Request verification
        verification_request = await async_test_client.post(
            "/api/users/request-verification",
            json={"email": user_data["email"]}
        )
        verification_link = verification_request.json()["verification_link"]
        verification_secret = verification_link.split("/")[-1]
        
        # Verify
        await async_test_client.get(f"/api/users/verify/{verification_secret}")
        
        # Measure login time
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        start_time = time.time()
        response = await async_test_client.post("/api/users/login", data=login_data)
        login_time = time.time() - start_time
        
        assert response.status_code == 200
        assert login_time < 1.0, f"Login took {login_time:.2f}s, should be < 1.0s"
        
        print(f"✅ Login completed in {login_time:.2f}s")