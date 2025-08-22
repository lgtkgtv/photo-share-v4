#!/usr/bin/env python3
"""
API test script for album management endpoints.

Tests album functionality including:
- Album creation and management
- Photo organization within albums
- Album privacy settings
- Album cover photos
"""

import pytest
import os
import sys

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.albums
class TestAlbumManagement:
    """Test album management API endpoints."""

    async def test_complete_album_workflow(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test complete album management workflow."""
        
        # Step 1: Create album
        album_data = {
            "name": "Vacation 2025",
            "description": "Photos from our amazing summer vacation in Europe",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        
        assert create_response.status_code == 200
        album = create_response.json()
        assert album["name"] == album_data["name"]
        assert album["description"] == album_data["description"]
        assert album["is_public"] == album_data["is_public"]
        assert "id" in album
        album_id = album["id"]
        
        # Step 2: Add photo to album
        add_photo_response = await async_test_client.post(
            f"/api/albums/{album_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        assert add_photo_response.status_code == 200
        add_result = add_photo_response.json()
        assert add_result["success"] is True
        
        # Step 3: Get album photos
        photos_response = await async_test_client.get(
            f"/api/albums/{album_id}/photos",
            headers=auth_headers
        )
        
        assert photos_response.status_code == 200
        album_photos = photos_response.json()
        assert len(album_photos) >= 1
        assert album_photos[0]["id"] == test_photo.id
        
        # Step 4: Set cover photo
        cover_response = await async_test_client.put(
            f"/api/albums/{album_id}/cover/{test_photo.id}",
            headers=auth_headers
        )
        
        assert cover_response.status_code == 200
        cover_result = cover_response.json()
        assert cover_result["success"] is True
        
        # Step 5: Update album
        update_data = {
            "name": "European Adventure 2025",
            "description": "Updated description with more details",
            "is_public": False
        }
        
        update_response = await async_test_client.put(
            f"/api/albums/{album_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        updated_album = update_response.json()
        assert updated_album["name"] == update_data["name"]
        assert updated_album["is_public"] == update_data["is_public"]
        
        # Step 6: Remove photo from album
        remove_response = await async_test_client.delete(
            f"/api/albums/{album_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        assert remove_response.status_code == 200
        remove_result = remove_response.json()
        assert remove_result["success"] is True
        
        # Step 7: Verify photo is removed
        final_photos_response = await async_test_client.get(
            f"/api/albums/{album_id}/photos",
            headers=auth_headers
        )
        
        final_photos = final_photos_response.json()
        photo_ids = [photo["id"] for photo in final_photos]
        assert test_photo.id not in photo_ids
        
        # Step 8: Delete album
        delete_response = await async_test_client.delete(
            f"/api/albums/{album_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        
        # Step 9: Verify album is deleted
        get_deleted_response = await async_test_client.get(
            f"/api/albums/{album_id}",
            headers=auth_headers
        )
        
        assert get_deleted_response.status_code == 404

    async def test_get_user_albums(self, async_test_client: AsyncClient, auth_headers):
        """Test retrieving user's albums."""
        
        # Create multiple albums
        albums_to_create = [
            {"name": "Family Photos", "description": "Family memories", "is_public": False},
            {"name": "Nature Photography", "description": "Beautiful landscapes", "is_public": True},
            {"name": "Travel Adventures", "description": "Adventures around the world", "is_public": True}
        ]
        
        created_albums = []
        for album_data in albums_to_create:
            response = await async_test_client.post(
                "/api/albums",
                json=album_data,
                headers=auth_headers
            )
            assert response.status_code == 200
            created_albums.append(response.json())
        
        # Get user's albums
        albums_response = await async_test_client.get(
            "/api/albums",
            headers=auth_headers
        )
        
        assert albums_response.status_code == 200
        user_albums = albums_response.json()
        assert len(user_albums) >= len(albums_to_create)
        
        # Verify all created albums are in the list
        album_names = [album["name"] for album in user_albums]
        for album_data in albums_to_create:
            assert album_data["name"] in album_names

    async def test_public_albums_access(self, async_test_client: AsyncClient, auth_headers):
        """Test accessing public albums."""
        
        # Create public album
        public_album_data = {
            "name": "Public Gallery",
            "description": "Public photo gallery",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=public_album_data,
            headers=auth_headers
        )
        
        assert create_response.status_code == 200
        
        # Get public albums (no auth required)
        public_response = await async_test_client.get("/api/albums/public")
        
        assert public_response.status_code == 200
        public_albums = public_response.json()
        assert isinstance(public_albums, list)
        
        # All returned albums should be public
        for album in public_albums:
            assert album["is_public"] is True
        
        # Our album should be in the list
        album_names = [album["name"] for album in public_albums]
        assert public_album_data["name"] in album_names

    async def test_album_privacy_enforcement(self, async_test_client: AsyncClient, auth_headers):
        """Test that private albums don't appear in public listings."""
        
        # Create private album
        private_album_data = {
            "name": "Private Family Album",
            "description": "Private family photos",
            "is_public": False
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=private_album_data,
            headers=auth_headers
        )
        
        assert create_response.status_code == 200
        
        # Get public albums
        public_response = await async_test_client.get("/api/albums/public")
        public_albums = public_response.json()
        
        # Private album should NOT be in public list
        private_album_names = [album["name"] for album in public_albums]
        assert private_album_data["name"] not in private_album_names

    async def test_album_validation(self, async_test_client: AsyncClient, auth_headers):
        """Test album input validation."""
        
        # Test empty name
        invalid_album = {
            "name": "",
            "description": "Album with empty name",
            "is_public": True
        }
        
        response = await async_test_client.post(
            "/api/albums",
            json=invalid_album,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
        
        # Test missing required fields
        incomplete_album = {
            "description": "Album without name"
        }
        
        response = await async_test_client.post(
            "/api/albums",
            json=incomplete_album,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_album_photo_management(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test adding and removing photos from albums."""
        
        # Create album
        album_data = {
            "name": "Photo Management Test",
            "description": "Testing photo operations",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        
        album_id = create_response.json()["id"]
        
        # Add photo multiple times (should be idempotent)
        for _ in range(3):
            add_response = await async_test_client.post(
                f"/api/albums/{album_id}/photos/{test_photo.id}",
                headers=auth_headers
            )
            assert add_response.status_code == 200
        
        # Verify photo is in album only once
        photos_response = await async_test_client.get(
            f"/api/albums/{album_id}/photos",
            headers=auth_headers
        )
        
        album_photos = photos_response.json()
        photo_count = sum(1 for photo in album_photos if photo["id"] == test_photo.id)
        assert photo_count == 1  # Should appear only once despite multiple adds

    async def test_nonexistent_album_operations(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test operations on non-existent albums."""
        
        nonexistent_id = 999999
        
        # Try to get non-existent album
        get_response = await async_test_client.get(
            f"/api/albums/{nonexistent_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
        
        # Try to add photo to non-existent album
        add_response = await async_test_client.post(
            f"/api/albums/{nonexistent_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        assert add_response.status_code == 404
        
        # Try to update non-existent album
        update_data = {"name": "Updated Name"}
        update_response = await async_test_client.put(
            f"/api/albums/{nonexistent_id}",
            json=update_data,
            headers=auth_headers
        )
        assert update_response.status_code == 404

    async def test_unauthorized_album_operations(self, async_test_client: AsyncClient):
        """Test album operations without authentication."""
        
        album_data = {
            "name": "Unauthorized Album",
            "description": "Should not work",
            "is_public": True
        }
        
        # Try to create album without auth
        response = await async_test_client.post(
            "/api/albums",
            json=album_data
        )
        
        assert response.status_code == 401  # Unauthorized

    async def test_album_cover_photo_management(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test album cover photo functionality."""
        
        # Create album
        album_data = {
            "name": "Cover Photo Test",
            "description": "Testing cover photo functionality",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        
        album_id = create_response.json()["id"]
        
        # Add photo to album first
        await async_test_client.post(
            f"/api/albums/{album_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        # Set as cover photo
        cover_response = await async_test_client.put(
            f"/api/albums/{album_id}/cover/{test_photo.id}",
            headers=auth_headers
        )
        
        assert cover_response.status_code == 200
        
        # Try to set cover photo that's not in album
        nonexistent_photo_id = 999999
        invalid_cover_response = await async_test_client.put(
            f"/api/albums/{album_id}/cover/{nonexistent_photo_id}",
            headers=auth_headers
        )
        
        assert invalid_cover_response.status_code == 404

    async def test_album_ordering_and_pagination(self, async_test_client: AsyncClient, auth_headers):
        """Test album ordering and pagination."""
        
        # Create multiple albums with different names
        for i in range(5):
            album_data = {
                "name": f"Album {i:02d}",
                "description": f"Album number {i}",
                "is_public": True
            }
            
            response = await async_test_client.post(
                "/api/albums",
                json=album_data,
                headers=auth_headers
            )
            assert response.status_code == 200
        
        # Get albums with pagination
        paginated_response = await async_test_client.get(
            "/api/albums?limit=3&offset=0",
            headers=auth_headers
        )
        
        assert paginated_response.status_code == 200
        paginated_albums = paginated_response.json()
        assert len(paginated_albums) <= 3


@pytest.mark.api
@pytest.mark.performance
class TestAlbumPerformance:
    """Test album management performance."""

    async def test_album_creation_performance(self, async_test_client: AsyncClient, auth_headers):
        """Test album creation performance."""
        import time
        
        album_data = {
            "name": "Performance Test Album",
            "description": "Testing creation performance",
            "is_public": True
        }
        
        start_time = time.time()
        
        response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Album creation should be fast
        response_time = end_time - start_time
        assert response_time < 1.0, f"Album creation took {response_time:.2f}s, should be < 1.0s"

    async def test_album_listing_performance(self, async_test_client: AsyncClient, auth_headers):
        """Test album listing performance."""
        import time
        
        start_time = time.time()
        
        response = await async_test_client.get(
            "/api/albums",
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Album listing should be fast
        response_time = end_time - start_time
        assert response_time < 1.0, f"Album listing took {response_time:.2f}s, should be < 1.0s"