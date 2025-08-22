#!/usr/bin/env python3
"""
Integration tests for Photo Sharing System API endpoints.

Tests the complete photo sharing system including:
- Share link creation and management
- Password-protected sharing
- Expiration date handling
- Share statistics and access control
"""

import pytest
import os
import sys
from datetime import datetime, timedelta

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.auth
class TestPhotoSharing:
    """Test photo sharing endpoints."""

    async def test_create_photo_share(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test creating a photo share link."""
        share_data = {
            "title": "Shared Vacation Photo",
            "description": "Sharing this beautiful sunset from our vacation",
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "max_views": 100,
            "password": "secret123",
            "allow_download": True
        }
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == share_data["title"]
        assert data["description"] == share_data["description"]
        assert data["max_views"] == share_data["max_views"]
        assert data["allow_download"] == share_data["allow_download"]
        assert "share_token" in data
        assert "share_url" in data
        assert data["view_count"] == 0

    async def test_create_public_photo_share(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test creating a public photo share (no password)."""
        share_data = {
            "title": "Public Share",
            "description": "Public photo share",
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "allow_download": False
        }
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == share_data["title"]
        assert "share_token" in data
        assert data["allow_download"] is False

    async def test_get_user_shares(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test retrieving user's photo shares."""
        # First create a share
        share_data = {
            "title": "Test Share",
            "description": "Test description",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Get user's shares
        response = await async_test_client.get(
            "/api/shares",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        shares = response.json()
        assert isinstance(shares, list)
        assert len(shares) >= 1
        assert shares[0]["title"] == share_data["title"]

    async def test_get_photo_shares(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test retrieving shares for a specific photo."""
        # First create a share
        share_data = {
            "title": "Photo Share",
            "description": "Share for specific photo",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Get shares for this photo
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/shares",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        shares = response.json()
        assert isinstance(shares, list)
        assert len(shares) >= 1
        assert shares[0]["photo_id"] == test_photo.id

    async def test_access_shared_photo_public(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test accessing a public shared photo."""
        # Create public share
        share_data = {
            "title": "Public Share",
            "description": "Public access test",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        share_token = create_response.json()["share_token"]
        
        # Access shared photo (no auth required)
        response = await async_test_client.get(f"/api/shared/{share_token}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["photo"]["id"] == test_photo.id
        assert data["share"]["title"] == share_data["title"]

    async def test_access_shared_photo_with_password(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test accessing a password-protected shared photo."""
        # Create password-protected share
        share_data = {
            "title": "Protected Share",
            "description": "Password protected test",
            "password": "secret123",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        share_token = create_response.json()["share_token"]
        
        # Try to access without password (should fail)
        response = await async_test_client.get(f"/api/shared/{share_token}")
        assert response.status_code == 401  # Unauthorized - password required
        
        # Access with correct password
        response = await async_test_client.post(
            f"/api/shared/{share_token}/access",
            json={"password": "secret123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["photo"]["id"] == test_photo.id

    async def test_update_photo_share(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test updating a photo share."""
        # Create share first
        share_data = {
            "title": "Original Title",
            "description": "Original description",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        share_id = create_response.json()["id"]
        
        # Update share
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "max_views": 50,
            "allow_download": False
        }
        
        response = await async_test_client.put(
            f"/api/shares/{share_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert data["max_views"] == update_data["max_views"]
        assert data["allow_download"] == update_data["allow_download"]

    async def test_delete_photo_share(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test deleting a photo share."""
        # Create share first
        share_data = {
            "title": "Share to Delete",
            "description": "This will be deleted",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        share_id = create_response.json()["id"]
        share_token = create_response.json()["share_token"]
        
        # Delete share
        response = await async_test_client.delete(
            f"/api/shares/{share_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify share is deleted - accessing should return 404
        access_response = await async_test_client.get(f"/api/shared/{share_token}")
        assert access_response.status_code == 404

    async def test_share_expiration(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share expiration handling."""
        # Create share that expires in the past
        past_date = datetime.utcnow() - timedelta(days=1)
        share_data = {
            "title": "Expired Share",
            "description": "This share has expired",
            "expires_at": past_date.isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        share_token = create_response.json()["share_token"]
        
        # Try to access expired share
        response = await async_test_client.get(f"/api/shared/{share_token}")
        assert response.status_code == 410  # Gone - expired

    async def test_share_view_limit(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share view limit enforcement."""
        # Create share with low view limit
        share_data = {
            "title": "Limited Views Share",
            "description": "Limited to 1 view",
            "max_views": 1,
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        share_token = create_response.json()["share_token"]
        
        # First access should work
        response1 = await async_test_client.get(f"/api/shared/{share_token}")
        assert response1.status_code == 200
        
        # Second access should be denied (view limit exceeded)
        response2 = await async_test_client.get(f"/api/shared/{share_token}")
        assert response2.status_code == 403  # Forbidden - view limit exceeded

    async def test_share_statistics(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share statistics tracking."""
        # Create share
        share_data = {
            "title": "Stats Test Share",
            "description": "Testing statistics",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        share_id = create_response.json()["id"]
        share_token = create_response.json()["share_token"]
        
        # Access the share to increment view count
        await async_test_client.get(f"/api/shared/{share_token}")
        
        # Get share statistics
        response = await async_test_client.get(
            f"/api/shares/{share_id}/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        stats = response.json()
        assert stats["view_count"] >= 1
        assert "last_accessed" in stats

    async def test_share_authorization(self, async_test_client: AsyncClient, test_photo):
        """Test share endpoints require authentication."""
        share_data = {
            "title": "Unauthorized Share",
            "description": "Should not work",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        # Try to create share without auth
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data
        )
        
        assert response.status_code == 401  # Unauthorized

    async def test_share_validation(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share input validation."""
        # Test share without title
        invalid_data = {
            "description": "No title provided",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_share_nonexistent_photo(self, async_test_client: AsyncClient, auth_headers):
        """Test creating share for non-existent photo."""
        share_data = {
            "title": "Share for Missing Photo",
            "description": "This photo doesn't exist",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        response = await async_test_client.post(
            "/api/photos/999999/share",  # Non-existent photo ID
            json=share_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404  # Not found