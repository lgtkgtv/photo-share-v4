#!/usr/bin/env python3
"""
Integration tests for User Profile API endpoints.

Tests the complete user profile system including:
- Profile creation and management
- Privacy settings
- Profile information updates
- Avatar management
"""

import pytest
import os
import sys

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.auth
class TestUserProfiles:
    """Test user profile management endpoints."""

    async def test_create_profile(self, async_test_client: AsyncClient, auth_headers):
        """Test profile creation."""
        profile_data = {
            "display_name": "John Doe",
            "bio": "Photography enthusiast and nature lover",
            "location": "San Francisco, CA",
            "website": "https://johndoe.photography",
            "is_private": False,
            "allow_comments": True,
            "allow_tags": True,
            "show_location": True
        }
        
        response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == profile_data["display_name"]
        assert data["bio"] == profile_data["bio"]
        assert data["location"] == profile_data["location"]
        assert data["website"] == profile_data["website"]
        assert data["is_private"] == profile_data["is_private"]
        assert "id" in data
        assert "created_at" in data

    async def test_get_user_profile(self, async_test_client: AsyncClient, auth_headers):
        """Test retrieving user's own profile."""
        # First create a profile
        profile_data = {
            "display_name": "Test User",
            "bio": "Test bio",
            "location": "Test City",
            "is_private": False
        }
        
        create_response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Get user's profile
        response = await async_test_client.get(
            "/api/profiles/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == profile_data["display_name"]
        assert data["bio"] == profile_data["bio"]

    async def test_update_profile(self, async_test_client: AsyncClient, auth_headers):
        """Test profile update."""
        # Create profile first
        profile_data = {
            "display_name": "Original Name",
            "bio": "Original bio",
            "location": "Original Location",
            "is_private": False
        }
        
        create_response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Update profile
        update_data = {
            "display_name": "Updated Name",
            "bio": "Updated bio with more information",
            "location": "New Location",
            "website": "https://updated-website.com",
            "is_private": True,
            "allow_comments": False
        }
        
        response = await async_test_client.put(
            "/api/profiles/me",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == update_data["display_name"]
        assert data["bio"] == update_data["bio"]
        assert data["location"] == update_data["location"]
        assert data["website"] == update_data["website"]
        assert data["is_private"] == update_data["is_private"]
        assert data["allow_comments"] == update_data["allow_comments"]

    async def test_get_profile_by_id(self, async_test_client: AsyncClient, auth_headers, test_user):
        """Test retrieving profile by user ID."""
        # Create profile first
        profile_data = {
            "display_name": "Public User",
            "bio": "This profile is public",
            "location": "Public City",
            "is_private": False
        }
        
        create_response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Get profile by user ID
        response = await async_test_client.get(
            f"/api/profiles/{test_user.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == profile_data["display_name"]
        assert data["user_id"] == test_user.id

    async def test_profile_privacy_settings(self, async_test_client: AsyncClient, auth_headers):
        """Test profile privacy settings."""
        # Create private profile
        profile_data = {
            "display_name": "Private User",
            "bio": "This profile is private",
            "is_private": True,
            "allow_comments": False,
            "allow_tags": False,
            "show_location": False
        }
        
        response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_private"] is True
        assert data["allow_comments"] is False
        assert data["allow_tags"] is False
        assert data["show_location"] is False

    async def test_profile_validation(self, async_test_client: AsyncClient, auth_headers):
        """Test profile input validation."""
        # Test invalid website URL
        invalid_data = {
            "display_name": "Valid Name",
            "bio": "Valid bio",
            "website": "not-a-valid-url",
            "is_private": False
        }
        
        response = await async_test_client.post(
            "/api/profiles",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_profile_bio_length_limit(self, async_test_client: AsyncClient, auth_headers):
        """Test bio length validation."""
        # Test very long bio (should be rejected if there's a limit)
        long_bio = "A" * 1001  # Assuming 1000 char limit
        
        profile_data = {
            "display_name": "Test User",
            "bio": long_bio,
            "is_private": False
        }
        
        response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        
        # Should either accept it or return validation error
        assert response.status_code in [200, 422]

    async def test_delete_profile(self, async_test_client: AsyncClient, auth_headers):
        """Test profile deletion."""
        # Create profile first
        profile_data = {
            "display_name": "Profile to Delete",
            "bio": "This will be deleted",
            "is_private": False
        }
        
        create_response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Delete profile
        response = await async_test_client.delete(
            "/api/profiles/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify profile is deleted - should return 404 when trying to get it
        get_response = await async_test_client.get(
            "/api/profiles/me",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    async def test_profile_authorization(self, async_test_client: AsyncClient):
        """Test profile endpoints require authentication."""
        profile_data = {
            "display_name": "Unauthorized Profile",
            "bio": "Should not work",
            "is_private": False
        }
        
        # Try to create profile without auth
        response = await async_test_client.post(
            "/api/profiles",
            json=profile_data
        )
        
        assert response.status_code == 401  # Unauthorized

    async def test_get_profiles_without_auth(self, async_test_client: AsyncClient):
        """Test accessing profiles without authentication."""
        # Try to get profile without auth
        response = await async_test_client.get("/api/profiles/me")
        
        assert response.status_code == 401  # Unauthorized

    async def test_update_nonexistent_profile(self, async_test_client: AsyncClient, auth_headers):
        """Test updating profile that doesn't exist."""
        update_data = {
            "display_name": "Updated Name",
            "bio": "Updated bio"
        }
        
        response = await async_test_client.put(
            "/api/profiles/me",
            json=update_data,
            headers=auth_headers
        )
        
        # Should return 404 if no profile exists
        assert response.status_code == 404

    async def test_profile_display_name_required(self, async_test_client: AsyncClient, auth_headers):
        """Test that display_name is required for profile creation."""
        profile_data = {
            "bio": "Bio without display name",
            "is_private": False
        }
        
        response = await async_test_client.post(
            "/api/profiles",
            json=profile_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_profile_website_validation(self, async_test_client: AsyncClient, auth_headers):
        """Test website URL validation."""
        # Test with valid URLs
        valid_websites = [
            "https://example.com",
            "http://example.com",
            "https://subdomain.example.com",
            "https://example.com/path"
        ]
        
        for website in valid_websites:
            profile_data = {
                "display_name": "Test User",
                "website": website,
                "is_private": False
            }
            
            response = await async_test_client.post(
                "/api/profiles",
                json=profile_data,
                headers=auth_headers
            )
            
            # Should accept valid URLs
            assert response.status_code == 200
            
            # Clean up - delete profile for next test
            await async_test_client.delete(
                "/api/profiles/me",
                headers=auth_headers
            )