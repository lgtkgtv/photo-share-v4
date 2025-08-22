#!/usr/bin/env python3
"""
API test script for photo upload and management endpoints.

Tests the complete photo management workflow including:
- Photo upload with various file types
- Photo metadata management
- Photo retrieval and download
- Photo permissions and privacy
"""

import pytest
import os
import sys
import tempfile
from io import BytesIO

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.auth
class TestPhotoUpload:
    """Test photo upload and management endpoints."""

    async def test_upload_valid_image(self, async_test_client: AsyncClient, auth_headers, sample_image_data):
        """Test uploading a valid image file."""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(sample_image_data)
            temp_file_path = temp_file.name
        
        try:
            # Upload photo
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("test_photo.jpg", file, "image/jpeg")}
                data = {
                    "title": "Test Photo Upload",
                    "description": "Testing photo upload functionality",
                    "is_public": "true"
                }
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            photo_data = response.json()
            assert photo_data["title"] == data["title"]
            assert photo_data["description"] == data["description"]
            assert photo_data["is_public"] is True
            assert "id" in photo_data
            assert "filename" in photo_data
            assert "created_at" in photo_data
            
        finally:
            # Cleanup
            os.unlink(temp_file_path)

    async def test_upload_png_image(self, async_test_client: AsyncClient, auth_headers):
        """Test uploading a PNG image."""
        
        # Create minimal PNG data
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc```\x00'
            b'\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(png_data)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("test_photo.png", file, "image/png")}
                data = {
                    "title": "PNG Test Photo",
                    "description": "Testing PNG upload",
                    "is_public": "false"
                }
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            photo_data = response.json()
            assert photo_data["is_public"] is False
            assert "png" in photo_data["filename"].lower()
            
        finally:
            os.unlink(temp_file_path)

    async def test_upload_without_authentication(self, async_test_client: AsyncClient, sample_image_data):
        """Test photo upload without authentication."""
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(sample_image_data)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("test_photo.jpg", file, "image/jpeg")}
                data = {"title": "Unauthorized Upload"}
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data
                )
            
            assert response.status_code == 401  # Unauthorized
            
        finally:
            os.unlink(temp_file_path)

    async def test_upload_invalid_file_type(self, async_test_client: AsyncClient, auth_headers):
        """Test uploading non-image file."""
        
        # Create text file
        text_data = b"This is not an image file"
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(text_data)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("malicious.jpg", file, "image/jpeg")}  # Wrong content type
                data = {"title": "Invalid File"}
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            # Should reject invalid file
            assert response.status_code in [400, 422]
            
        finally:
            os.unlink(temp_file_path)

    async def test_upload_oversized_file(self, async_test_client: AsyncClient, auth_headers):
        """Test uploading file that exceeds size limit."""
        
        # Create large file (simulate oversized image)
        large_data = b'\xff\xd8\xff\xe0' + b'0' * (50 * 1024 * 1024)  # 50MB+ "JPEG"
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(large_data)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("huge_photo.jpg", file, "image/jpeg")}
                data = {"title": "Oversized Photo"}
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            # Should reject oversized file
            assert response.status_code in [400, 413, 422]
            
        finally:
            os.unlink(temp_file_path)

    async def test_get_user_photos(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test retrieving user's photos."""
        
        response = await async_test_client.get(
            "/api/photos/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        photos = response.json()
        assert isinstance(photos, list)
        assert len(photos) >= 1
        
        # Verify test photo is in the list
        photo_ids = [photo["id"] for photo in photos]
        assert test_photo.id in photo_ids

    async def test_get_public_photos(self, async_test_client: AsyncClient):
        """Test retrieving public photos without authentication."""
        
        response = await async_test_client.get("/api/photos/public")
        
        assert response.status_code == 200
        photos = response.json()
        assert isinstance(photos, list)
        
        # All returned photos should be public
        for photo in photos:
            assert photo["is_public"] is True

    async def test_get_photo_by_id(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test retrieving specific photo by ID."""
        
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        photo_data = response.json()
        assert photo_data["id"] == test_photo.id
        assert photo_data["title"] == test_photo.title

    async def test_get_nonexistent_photo(self, async_test_client: AsyncClient, auth_headers):
        """Test retrieving non-existent photo."""
        
        response = await async_test_client.get(
            "/api/photos/999999",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    async def test_download_photo(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test downloading photo file."""
        
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/download",
            headers=auth_headers
        )
        
        # Should return file content or redirect
        assert response.status_code in [200, 302, 307]
        
        if response.status_code == 200:
            # Direct file content
            assert len(response.content) > 0
            assert response.headers["content-type"].startswith("image/")

    async def test_get_photo_urls(self, async_test_client: AsyncClient, auth_headers, test_photo):
        """Test getting photo URLs."""
        
        response = await async_test_client.get(
            f"/api/photos/{test_photo.id}/url",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        url_data = response.json()
        assert "original_url" in url_data
        assert "thumbnail_url" in url_data

    async def test_photo_validation_required_fields(self, async_test_client: AsyncClient, auth_headers, sample_image_data):
        """Test photo upload validation for required fields."""
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(sample_image_data)
            temp_file_path = temp_file.name
        
        try:
            # Upload without title
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("test_photo.jpg", file, "image/jpeg")}
                data = {
                    "description": "Photo without title",
                    "is_public": "true"
                }
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            # Should either accept (title optional) or reject (title required)
            assert response.status_code in [200, 422]
            
        finally:
            os.unlink(temp_file_path)

    async def test_photo_privacy_settings(self, async_test_client: AsyncClient, auth_headers, sample_image_data):
        """Test photo privacy settings."""
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(sample_image_data)
            temp_file_path = temp_file.name
        
        try:
            # Upload private photo
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("private_photo.jpg", file, "image/jpeg")}
                data = {
                    "title": "Private Photo",
                    "description": "This photo is private",
                    "is_public": "false"
                }
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            assert response.status_code == 200
            photo_data = response.json()
            assert photo_data["is_public"] is False
            
            # Private photo should not appear in public photos
            public_response = await async_test_client.get("/api/photos/public")
            public_photos = public_response.json()
            private_photo_ids = [photo["id"] for photo in public_photos]
            assert photo_data["id"] not in private_photo_ids
            
        finally:
            os.unlink(temp_file_path)


@pytest.mark.api
@pytest.mark.performance
class TestPhotoUploadPerformance:
    """Test photo upload performance aspects."""

    async def test_upload_response_time(self, async_test_client: AsyncClient, auth_headers, sample_image_data):
        """Test photo upload response time."""
        import time
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(sample_image_data)
            temp_file_path = temp_file.name
        
        try:
            start_time = time.time()
            
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("performance_test.jpg", file, "image/jpeg")}
                data = {
                    "title": "Performance Test",
                    "description": "Testing upload speed",
                    "is_public": "true"
                }
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            end_time = time.time()
            
            assert response.status_code == 200
            
            # Upload should complete within reasonable time (5 seconds)
            response_time = end_time - start_time
            assert response_time < 5.0, f"Upload took {response_time:.2f}s, should be < 5.0s"
            
        finally:
            os.unlink(temp_file_path)

    async def test_multiple_photos_list_performance(self, async_test_client: AsyncClient, auth_headers):
        """Test performance of listing photos."""
        import time
        
        start_time = time.time()
        
        response = await async_test_client.get(
            "/api/photos/",
            headers=auth_headers
        )
        
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Photo listing should be fast (1 second)
        response_time = end_time - start_time
        assert response_time < 1.0, f"Photo listing took {response_time:.2f}s, should be < 1.0s"


@pytest.mark.api
@pytest.mark.security
class TestPhotoSecurity:
    """Test photo upload security aspects."""

    async def test_malicious_file_upload(self, async_test_client: AsyncClient, auth_headers):
        """Test uploading potentially malicious files."""
        
        # Create file with script content but image extension
        malicious_content = b"<?php system($_GET['cmd']); ?>"
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(malicious_content)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("malicious.jpg", file, "image/jpeg")}
                data = {"title": "Malicious File"}
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            # Should reject malicious file
            assert response.status_code in [400, 422]
            
        finally:
            os.unlink(temp_file_path)

    async def test_filename_sanitization(self, async_test_client: AsyncClient, auth_headers, sample_image_data):
        """Test that uploaded filenames are properly sanitized."""
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(sample_image_data)
            temp_file_path = temp_file.name
        
        try:
            # Upload with potentially dangerous filename
            with open(temp_file_path, 'rb') as file:
                files = {"file": ("../../../etc/passwd.jpg", file, "image/jpeg")}
                data = {"title": "Path Traversal Test"}
                
                response = await async_test_client.post(
                    "/api/photos/upload",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            if response.status_code == 200:
                # If upload succeeds, filename should be sanitized
                photo_data = response.json()
                assert "../" not in photo_data["filename"]
                assert "passwd" not in photo_data["filename"]
            
        finally:
            os.unlink(temp_file_path)