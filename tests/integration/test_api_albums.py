#!/usr/bin/env python3
"""
Integration tests for Album Management API endpoints.

Tests the complete album system including:
- Album creation and management
- Photo addition to albums
- Album privacy settings
- Album cover photo management
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
class TestAlbumManagement:
    """Test album management endpoints."""

    async def test_create_album(self, async_test_client: AsyncClient, auth_headers):
        """Test album creation."""
        album_data = {
            "name": "Vacation Photos",
            "description": "Photos from our summer vacation",
            "is_public": True
        }
        
        response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == album_data["name"]
        assert data["description"] == album_data["description"]
        assert data["is_public"] == album_data["is_public"]
        assert "id" in data
        assert "created_at" in data

    async def test_get_user_albums(self, async_test_client: AsyncClient, auth_headers):
        """Test retrieving user's albums."""
        # First create an album
        album_data = {
            "name": "Test Album",
            "description": "Test Description",
            "is_public": False
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        
        # Get user's albums
        response = await async_test_client.get(
            "/api/albums",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        albums = response.json()
        assert isinstance(albums, list)
        assert len(albums) >= 1
        assert albums[0]["name"] == album_data["name"]

    async def test_get_album_by_id(self, async_test_client: AsyncClient, auth_headers):
        """Test retrieving specific album by ID."""
        # Create album first
        album_data = {
            "name": "Specific Album",
            "description": "Album to retrieve",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        album_id = create_response.json()["id"]
        
        # Get album by ID
        response = await async_test_client.get(
            f"/api/albums/{album_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == album_id
        assert data["name"] == album_data["name"]

    async def test_update_album(self, async_test_client: AsyncClient, auth_headers):
        """Test album update."""
        # Create album first
        album_data = {
            "name": "Original Name",
            "description": "Original Description",
            "is_public": False
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        album_id = create_response.json()["id"]
        
        # Update album
        update_data = {
            "name": "Updated Name",
            "description": "Updated Description",
            "is_public": True
        }
        
        response = await async_test_client.put(
            f"/api/albums/{album_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["is_public"] == update_data["is_public"]

    async def test_delete_album(self, async_test_client: AsyncClient, auth_headers):
        """Test album deletion."""
        # Create album first
        album_data = {
            "name": "Album to Delete",
            "description": "This will be deleted",
            "is_public": False
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        album_id = create_response.json()["id"]
        
        # Delete album
        response = await async_test_client.delete(
            f"/api/albums/{album_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Verify album is deleted
        get_response = await async_test_client.get(
            f"/api/albums/{album_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    async def test_add_photo_to_album(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test adding photo to album."""
        # Create album first
        album_data = {
            "name": "Photo Album",
            "description": "Album for photos",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        album_id = create_response.json()["id"]
        
        # Add photo to album
        response = await async_test_client.post(
            f"/api/albums/{album_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_remove_photo_from_album(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test removing photo from album."""
        # Create album and add photo
        album_data = {
            "name": "Photo Album",
            "description": "Album for photos",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        album_id = create_response.json()["id"]
        
        # Add photo to album
        await async_test_client.post(
            f"/api/albums/{album_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        # Remove photo from album
        response = await async_test_client.delete(
            f"/api/albums/{album_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_album_photos(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test retrieving photos from album."""
        # Create album and add photo
        album_data = {
            "name": "Photo Album",
            "description": "Album for photos",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        album_id = create_response.json()["id"]
        
        # Add photo to album
        await async_test_client.post(
            f"/api/albums/{album_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        # Get album photos
        response = await async_test_client.get(
            f"/api/albums/{album_id}/photos",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        photos = response.json()
        assert isinstance(photos, list)
        assert len(photos) >= 1
        assert photos[0]["id"] == test_photo.id

    async def test_set_album_cover_photo(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test setting album cover photo."""
        # Create album and add photo
        album_data = {
            "name": "Photo Album",
            "description": "Album for photos",
            "is_public": True
        }
        
        create_response = await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        album_id = create_response.json()["id"]
        
        # Add photo to album
        await async_test_client.post(
            f"/api/albums/{album_id}/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        # Set cover photo
        response = await async_test_client.put(
            f"/api/albums/{album_id}/cover/{test_photo.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_public_albums(self, async_test_client: AsyncClient, auth_headers):
        """Test retrieving public albums."""
        # Create public album
        album_data = {
            "name": "Public Album",
            "description": "This is public",
            "is_public": True
        }
        
        await async_test_client.post(
            "/api/albums",
            json=album_data,
            headers=auth_headers
        )
        
        # Get public albums (no auth required)
        response = await async_test_client.get("/api/albums/public")
        
        assert response.status_code == 200
        albums = response.json()
        assert isinstance(albums, list)
        # Should contain at least our public album
        public_album_names = [album["name"] for album in albums]
        assert "Public Album" in public_album_names

    async def test_album_validation(self, async_test_client: AsyncClient, auth_headers):
        """Test album input validation."""
        # Test empty name
        invalid_data = {
            "name": "",
            "description": "Valid description",
            "is_public": True
        }
        
        response = await async_test_client.post(
            "/api/albums",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

    async def test_album_authorization(self, async_test_client: AsyncClient):
        """Test album endpoints require authentication."""
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

    async def test_album_permissions(self, async_test_client: AsyncClient, auth_headers):
        """Test album permissions (users can only access their own albums)."""
        # This would require creating a second user and testing cross-user access
        # For now, we test that accessing non-existent album returns 404
        response = await async_test_client.get(
            "/api/albums/999999",  # Non-existent album
            headers=auth_headers
        )
        
        assert response.status_code == 404