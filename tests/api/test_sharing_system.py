#!/usr/bin/env python3
"""
API test script for photo sharing system endpoints.

Tests sharing functionality including:
- Share link creation and management
- Password protection and expiration
- Share access control and statistics
- Download permissions
"""

import pytest
import os
import sys
from datetime import datetime, timedelta

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.sharing
class TestPhotoSharing:
    """Test photo sharing system API endpoints."""

    async def test_complete_sharing_workflow(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test complete photo sharing workflow."""
        
        # Step 1: Create share link
        share_data = {
            "title": "Beautiful Sunset Share",
            "description": "Sharing this amazing sunset photo with friends",
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "max_views": 50,
            "password": "sunset2025",
            "allow_download": True
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        assert create_response.status_code == 200
        share = create_response.json()
        assert share["title"] == share_data["title"]
        assert share["description"] == share_data["description"]
        assert share["max_views"] == share_data["max_views"]
        assert share["allow_download"] == share_data["allow_download"]
        assert "share_token" in share
        assert "share_url" in share
        assert share["view_count"] == 0
        
        share_id = share["id"]
        share_token = share["share_token"]
        
        # Step 2: Access shared photo with password
        access_response = await async_test_client.post(
            f"/api/shared/{share_token}/access",
            json={"password": "sunset2025"}
        )
        
        assert access_response.status_code == 200
        access_data = access_response.json()
        assert access_data["photo"]["id"] == test_photo.id
        assert access_data["share"]["title"] == share_data["title"]
        
        # Step 3: Get share statistics
        stats_response = await async_test_client.get(
            f"/api/shares/{share_id}/stats",
            headers=auth_headers
        )
        
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["view_count"] >= 1  # Should have increased from access
        assert "last_accessed" in stats
        
        # Step 4: Update share settings
        update_data = {
            "title": "Updated Sunset Share",
            "description": "Updated description",
            "max_views": 25,
            "allow_download": False
        }
        
        update_response = await async_test_client.put(
            f"/api/shares/{share_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        updated_share = update_response.json()
        assert updated_share["title"] == update_data["title"]
        assert updated_share["max_views"] == update_data["max_views"]
        assert updated_share["allow_download"] == update_data["allow_download"]
        
        # Step 5: Delete share
        delete_response = await async_test_client.delete(
            f"/api/shares/{share_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        
        # Step 6: Verify share is deleted
        access_deleted_response = await async_test_client.get(
            f"/api/shared/{share_token}"
        )
        
        assert access_deleted_response.status_code == 404

    async def test_public_share_access(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test accessing public shares without password."""
        
        # Create public share (no password)
        share_data = {
            "title": "Public Photo Share",
            "description": "No password required",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "allow_download": True
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        share_token = create_response.json()["share_token"]
        
        # Access without password (should work)
        access_response = await async_test_client.get(
            f"/api/shared/{share_token}"
        )
        
        assert access_response.status_code == 200
        access_data = access_response.json()
        assert access_data["photo"]["id"] == test_photo.id

    async def test_password_protected_share(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test password-protected share access."""
        
        # Create password-protected share
        share_data = {
            "title": "Protected Share",
            "description": "Password required",
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
        no_password_response = await async_test_client.get(
            f"/api/shared/{share_token}"
        )
        
        assert no_password_response.status_code == 401  # Password required
        
        # Try with wrong password
        wrong_password_response = await async_test_client.post(
            f"/api/shared/{share_token}/access",
            json={"password": "wrongpassword"}
        )
        
        assert wrong_password_response.status_code == 401  # Wrong password
        
        # Access with correct password
        correct_password_response = await async_test_client.post(
            f"/api/shared/{share_token}/access",
            json={"password": "secret123"}
        )
        
        assert correct_password_response.status_code == 200

    async def test_share_expiration(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share expiration handling."""
        
        # Create share that expires in the past
        past_date = datetime.utcnow() - timedelta(hours=1)
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
        access_response = await async_test_client.get(
            f"/api/shared/{share_token}"
        )
        
        assert access_response.status_code == 410  # Gone (expired)

    async def test_view_limit_enforcement(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share view limit enforcement."""
        
        # Create share with low view limit
        share_data = {
            "title": "Limited Share",
            "description": "Only 2 views allowed",
            "max_views": 2,
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        share_token = create_response.json()["share_token"]
        
        # First two accesses should work
        for i in range(2):
            access_response = await async_test_client.get(
                f"/api/shared/{share_token}"
            )
            assert access_response.status_code == 200
        
        # Third access should be denied
        denied_response = await async_test_client.get(
            f"/api/shared/{share_token}"
        )
        
        assert denied_response.status_code == 403  # Forbidden (view limit exceeded)

    async def test_get_user_shares(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test retrieving user's shares."""
        
        # Create multiple shares
        shares_to_create = [
            {
                "title": "Share 1",
                "description": "First share",
                "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
            },
            {
                "title": "Share 2", 
                "description": "Second share",
                "expires_at": (datetime.utcnow() + timedelta(days=2)).isoformat()
            }
        ]
        
        created_shares = []
        for share_data in shares_to_create:
            response = await async_test_client.post(
                f"/api/photos/{test_photo.id}/share",
                json=share_data,
                headers=auth_headers
            )
            assert response.status_code == 200
            created_shares.append(response.json())
        
        # Get user's shares
        shares_response = await async_test_client.get(
            "/api/shares",
            headers=auth_headers
        )
        
        assert shares_response.status_code == 200
        user_shares = shares_response.json()
        assert len(user_shares) >= len(shares_to_create)
        
        # Verify created shares are in the list
        share_titles = [share["title"] for share in user_shares]
        for share_data in shares_to_create:
            assert share_data["title"] in share_titles

    async def test_get_photo_shares(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test retrieving shares for specific photo."""
        
        # Create share for the photo
        share_data = {
            "title": "Photo Specific Share",
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
        photo_shares_response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/shares",
            headers=auth_headers
        )
        
        assert photo_shares_response.status_code == 200
        photo_shares = photo_shares_response.json()
        assert len(photo_shares) >= 1
        
        # All shares should be for this photo
        for share in photo_shares:
            assert share["photo_id"] == test_photo.id

    async def test_share_validation(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share input validation."""
        
        # Test share without title
        invalid_share = {
            "description": "Share without title",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=invalid_share,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
        
        # Test invalid expiration date
        invalid_date_share = {
            "title": "Invalid Date Share",
            "expires_at": "not-a-date"
        }
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=invalid_date_share,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

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

    async def test_share_nonexistent_photo(self, async_test_client: AsyncClient, auth_headers):
        """Test creating share for non-existent photo."""
        
        share_data = {
            "title": "Share for Missing Photo",
            "description": "Photo doesn't exist",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        response = await async_test_client.post(
            "/api/photos/999999/share",
            json=share_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404  # Photo not found

    async def test_share_permissions(self, async_test_client: AsyncClient, auth_headers):
        """Test share permissions and ownership."""
        
        # Test accessing non-existent share
        nonexistent_token = "nonexistent-token-12345"
        
        response = await async_test_client.get(
            f"/api/shared/{nonexistent_token}"
        )
        
        assert response.status_code == 404
        
        # Test updating non-existent share
        update_data = {"title": "Updated Title"}
        
        response = await async_test_client.put(
            "/api/shares/999999",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_download_permissions(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test download permissions in shares."""
        
        # Create share with download disabled
        no_download_share = {
            "title": "No Download Share",
            "description": "Download not allowed",
            "allow_download": False,
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=no_download_share,
            headers=auth_headers
        )
        
        share_token = create_response.json()["share_token"]
        
        # Access the share
        access_response = await async_test_client.get(
            f"/api/shared/{share_token}"
        )
        
        assert access_response.status_code == 200
        share_data = access_response.json()
        assert share_data["share"]["allow_download"] is False


@pytest.mark.api
@pytest.mark.performance
class TestSharingPerformance:
    """Test sharing system performance."""

    async def test_share_creation_performance(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share creation performance."""
        import time
        
        share_data = {
            "title": "Performance Test Share",
            "description": "Testing creation speed",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        start_time = time.time()
        
        response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Share creation should be fast
        response_time = end_time - start_time
        assert response_time < 1.0, f"Share creation took {response_time:.2f}s, should be < 1.0s"

    async def test_share_access_performance(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test share access performance."""
        import time
        
        # Create share first
        share_data = {
            "title": "Access Performance Test",
            "description": "Testing access speed",
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }
        
        create_response = await async_test_client.post(
            f"/api/photos/{test_photo.id}/share",
            json=share_data,
            headers=auth_headers
        )
        
        share_token = create_response.json()["share_token"]
        
        # Test access performance
        start_time = time.time()
        
        access_response = await async_test_client.get(
            f"/api/shared/{share_token}"
        )
        
        end_time = time.time()
        
        assert access_response.status_code == 200
        
        # Share access should be fast
        response_time = end_time - start_time
        assert response_time < 1.0, f"Share access took {response_time:.2f}s, should be < 1.0s"