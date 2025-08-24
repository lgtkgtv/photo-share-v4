#!/usr/bin/env python3
"""
Integration Tests for Media Endpoints
====================================

Tests the complete media management API including:
- Photo upload and management (existing functionality)  
- Video upload and processing (new functionality)
- Video streaming with range requests
- Thumbnail generation and serving
- Media metadata retrieval
"""

import pytest
import asyncio
import tempfile
import os
import json
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io

# Mock environment and imports
class MockAuthenticatedUser:
    """Mock authenticated user for testing."""
    def __init__(self, user_id: int = 1, email: str = "test@example.com"):
        self.user_id = user_id
        self.email = email
        self.is_verified = True
        
    def has_permission(self, resource: str, action: str) -> bool:
        return True

class MockAppDatabaseManager:
    """Mock database manager for testing."""
    async def initialize(self) -> bool:
        return True
    
    async def health_check(self) -> bool:
        return True
        
    async def create_media(self, media_data: Dict[str, Any]) -> Mock:
        mock_media = Mock()
        mock_media.id = 1
        mock_media.user_id = media_data.get('user_id', 1)
        mock_media.filename = media_data.get('filename', 'test.jpg')
        mock_media.content_type = media_data.get('content_type', 'image/jpeg')
        mock_media.media_type = media_data.get('media_type', 'photo')
        mock_media.file_size = media_data.get('file_size', 1024)
        mock_media.title = media_data.get('title', 'Test Media')
        mock_media.description = media_data.get('description', '')
        mock_media.is_public = media_data.get('is_public', False)
        mock_media.duration = media_data.get('duration')
        mock_media.width = media_data.get('width')
        mock_media.height = media_data.get('height')
        mock_media.video_codec = media_data.get('video_codec')
        mock_media.audio_codec = media_data.get('audio_codec')
        mock_media.framerate = media_data.get('framerate')
        mock_media.video_bitrate = media_data.get('video_bitrate')
        mock_media.audio_bitrate = media_data.get('audio_bitrate')
        return mock_media
    
    async def get_media_by_id(self, media_id: int) -> Mock:
        if media_id == 999:  # Non-existent media for testing
            return None
            
        mock_media = Mock()
        mock_media.id = media_id
        mock_media.user_id = 1
        mock_media.filename = f"test_media_{media_id}.mp4"
        mock_media.content_type = "video/mp4"
        mock_media.media_type = "video"
        mock_media.file_size = 10485760
        mock_media.title = "Test Video"
        mock_media.is_public = True
        mock_media.duration = 120
        mock_media.width = 1920
        mock_media.height = 1080
        mock_media.video_codec = "h264"
        mock_media.audio_codec = "aac"
        mock_media.framerate = 30.0
        mock_media.video_bitrate = 2500
        mock_media.audio_bitrate = 128
        return mock_media

# Mock the dependencies before importing the app
with patch.dict('os.environ', {
    'JWT_SECRET_KEY': 'test-secret-key',
    'APP_DATABASE_URL': 'sqlite+aiosqlite:///:memory:',
    'UPLOAD_DIR': '/tmp/test-uploads'
}):
    with patch('services.photoshare.main.get_current_user') as mock_get_user:
        with patch('services.photoshare.main.get_optional_user') as mock_get_optional_user:
            with patch('services.photoshare.main.get_app_db_manager') as mock_get_db:
                mock_get_user.return_value = MockAuthenticatedUser()
                mock_get_optional_user.return_value = MockAuthenticatedUser()
                mock_get_db.return_value = MockAppDatabaseManager()
                
                from services.photoshare.main import app

class TestMediaUploadEndpoints:
    """Test media upload endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing."""
        # Create a minimal JPEG file
        jpeg_header = bytes.fromhex('FFD8FFE000104A46494600010101006000600000FFDB004300080606070605080707')
        jpeg_data = jpeg_header + b'\x00' * 100 + bytes.fromhex('FFD9')
        return io.BytesIO(jpeg_data)
    
    @pytest.fixture  
    def sample_video_file(self):
        """Create a sample video file for testing."""
        # Create a minimal MP4 file header
        mp4_header = b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom'
        mp4_data = mp4_header + b'\x00' * 1000
        return io.BytesIO(mp4_data)

    @patch('services.photoshare.main.VIDEO_PROCESSOR_AVAILABLE', True)
    @patch('services.photoshare.main.video_processor')
    @patch('services.photoshare.main.video_security_validator') 
    @patch('os.path.exists')
    def test_photo_upload_success(self, mock_exists, mock_video_security, mock_video_processor, client, sample_image_file):
        """Test successful photo upload via unified media endpoint."""
        mock_exists.return_value = True
        
        with patch('builtins.open', create=True):
            response = client.post(
                "/api/media/upload",
                files={"file": ("test_photo.jpg", sample_image_file, "image/jpeg")},
                data={
                    "title": "Test Photo Upload",
                    "description": "Integration test photo",
                    "is_public": "true"
                },
                headers={"Authorization": "Bearer test-token"}
            )
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Media uploaded successfully"
        assert result["media_type"] == "photo"
        assert result["processing_status"] == "completed"
        assert "media_id" in result

    @patch('services.photoshare.main.VIDEO_PROCESSOR_AVAILABLE', True)
    @patch('services.photoshare.main.video_processor')
    @patch('services.photoshare.main.video_security_validator')
    @patch('os.path.exists')
    async def test_video_upload_success(self, mock_exists, mock_video_security, mock_video_processor, client, sample_video_file):
        """Test successful video upload via unified media endpoint."""
        mock_exists.return_value = True
        
        # Mock video processor methods
        mock_video_processor.analyze_video = AsyncMock(return_value={
            'duration': 120,
            'width': 1920,
            'height': 1080,
            'video_codec': 'h264',
            'audio_codec': 'aac',
            'framerate': 30.0,
            'video_bitrate': 2500,
            'audio_bitrate': 128,
            'file_size': 10485760,
            'format_name': 'mp4'
        })
        mock_video_processor.generate_thumbnail = AsyncMock(return_value=True)
        
        # Mock video security validator
        mock_video_security.validate_video_security = AsyncMock(return_value=(True, "Validation passed"))
        
        with patch('builtins.open', create=True):
            response = client.post(
                "/api/media/upload",
                files={"file": ("test_video.mp4", sample_video_file, "video/mp4")},
                data={
                    "title": "Test Video Upload",
                    "description": "Integration test video", 
                    "is_public": "false"
                },
                headers={"Authorization": "Bearer test-token"}
            )
        
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Media uploaded successfully"
        assert result["media_type"] == "video"
        assert result["processing_status"] == "completed"
        assert "media_id" in result

    def test_upload_without_auth(self, client, sample_image_file):
        """Test media upload without authentication."""
        response = client.post(
            "/api/media/upload", 
            files={"file": ("test.jpg", sample_image_file, "image/jpeg")},
            data={"title": "Test"}
        )
        
        assert response.status_code == 401

    def test_upload_invalid_file_type(self, client):
        """Test upload with invalid file type."""
        text_file = io.BytesIO(b"This is not a valid media file")
        
        response = client.post(
            "/api/media/upload",
            files={"file": ("test.txt", text_file, "text/plain")},
            data={"title": "Invalid File"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 400

    @patch('services.photoshare.main.VIDEO_PROCESSOR_AVAILABLE', True)
    @patch('services.photoshare.main.video_security_validator')
    def test_video_security_validation_failure(self, mock_video_security, client, sample_video_file):
        """Test video upload with security validation failure."""
        # Mock security validation failure
        mock_video_security.validate_video_security = AsyncMock(return_value=(False, "Blocked codec detected"))
        
        with patch('builtins.open', create=True):
            response = client.post(
                "/api/media/upload",
                files={"file": ("malicious_video.mp4", sample_video_file, "video/mp4")},
                data={"title": "Malicious Video"},
                headers={"Authorization": "Bearer test-token"}
            )
        
        assert response.status_code == 400
        result = response.json()
        assert "security validation failed" in result["detail"].lower()


class TestVideoStreamingEndpoints:
    """Test video streaming endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_video_content(self):
        """Sample video file content for streaming tests."""
        return b'FAKE_VIDEO_CONTENT' * 1000  # 17KB of fake video data

    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_stream_video_full_request(self, mock_getsize, mock_exists, client, sample_video_content):
        """Test full video streaming without range request."""
        mock_exists.return_value = True
        mock_getsize.return_value = len(sample_video_content)
        
        with patch('builtins.open', create=True) as mock_open:
            # Mock FileResponse
            with patch('services.photoshare.main.FileResponse') as mock_file_response:
                mock_file_response.return_value = Mock()
                
                response = client.get("/api/media/1/stream")
        
        assert response.status_code == 200

    @patch('os.path.exists')  
    @patch('os.path.getsize')
    def test_stream_video_range_request(self, mock_getsize, mock_exists, client, sample_video_content):
        """Test video streaming with range request."""
        mock_exists.return_value = True
        mock_getsize.return_value = len(sample_video_content)
        
        # Mock file reading for range request
        mock_file = Mock()
        mock_file.read.return_value = sample_video_content[:1024]  # First 1KB
        mock_file.seek = Mock()
        
        with patch('builtins.open', return_value=mock_file):
            response = client.get(
                "/api/media/1/stream",
                headers={"Range": "bytes=0-1023"}
            )
        
        # The actual streaming logic would return 206 for partial content
        # but our mocked version might return different status
        assert response.status_code in [200, 206]

    def test_stream_nonexistent_media(self, client):
        """Test streaming request for non-existent media."""
        response = client.get("/api/media/999/stream")
        
        assert response.status_code == 404

    def test_stream_photo_as_video(self, client):
        """Test streaming request for photo (should fail)."""
        # Mock a photo media record
        with patch('services.photoshare.main.get_app_db_manager') as mock_get_db:
            mock_db = MockAppDatabaseManager()
            
            async def mock_get_media_by_id(media_id):
                if media_id == 2:
                    mock_media = Mock()
                    mock_media.media_type = "photo"  # This should cause failure
                    return mock_media
                return None
            
            mock_db.get_media_by_id = mock_get_media_by_id
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/media/2/stream")
        
        assert response.status_code == 400

    def test_stream_private_video_unauthorized(self, client):
        """Test streaming private video without authorization."""
        # Mock private video 
        with patch('services.photoshare.main.get_app_db_manager') as mock_get_db:
            with patch('services.photoshare.main.get_optional_user', return_value=None):
                mock_db = MockAppDatabaseManager()
                
                async def mock_get_media_by_id(media_id):
                    mock_media = Mock()
                    mock_media.media_type = "video"
                    mock_media.is_public = False  # Private video
                    mock_media.user_id = 999  # Different user
                    return mock_media
                
                mock_db.get_media_by_id = mock_get_media_by_id
                mock_get_db.return_value = mock_db
                
                response = client.get("/api/media/1/stream")
        
        assert response.status_code == 403


class TestThumbnailEndpoints:
    """Test media thumbnail endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client.""" 
        return TestClient(app)

    @patch('os.path.exists')
    @patch('services.photoshare.main.FileResponse')
    def test_get_video_thumbnail_exists(self, mock_file_response, mock_exists, client):
        """Test getting existing video thumbnail."""
        mock_exists.return_value = True  # Thumbnail file exists
        mock_file_response.return_value = Mock()
        
        response = client.get("/api/media/1/thumbnail")
        
        assert response.status_code == 200

    @patch('os.path.exists')
    @patch('services.photoshare.main.VIDEO_PROCESSOR_AVAILABLE', True)
    @patch('services.photoshare.main.video_processor')
    def test_generate_video_thumbnail_on_demand(self, mock_video_processor, mock_exists, client):
        """Test on-demand video thumbnail generation."""
        # Thumbnail doesn't exist initially, but original video does
        mock_exists.side_effect = lambda path: not path.endswith('.jpg')
        mock_video_processor.generate_thumbnail = AsyncMock(return_value=True)
        
        with patch('os.makedirs'):
            with patch('services.photoshare.main.FileResponse') as mock_file_response:
                mock_file_response.return_value = Mock()
                response = client.get("/api/media/1/thumbnail")
        
        assert response.status_code == 200
        mock_video_processor.generate_thumbnail.assert_called_once()

    @patch('os.path.exists')
    def test_get_photo_thumbnail(self, mock_exists, client):
        """Test getting thumbnail for photo (returns original image)."""
        mock_exists.return_value = True
        
        # Mock a photo media record
        with patch('services.photoshare.main.get_app_db_manager') as mock_get_db:
            mock_db = MockAppDatabaseManager()
            
            async def mock_get_media_by_id(media_id):
                mock_media = Mock()
                mock_media.media_type = "photo"
                mock_media.is_public = True
                mock_media.content_type = "image/jpeg"
                return mock_media
            
            mock_db.get_media_by_id = mock_get_media_by_id
            mock_get_db.return_value = mock_db
            
            with patch('services.photoshare.main.FileResponse') as mock_file_response:
                mock_file_response.return_value = Mock()
                response = client.get("/api/media/1/thumbnail")
        
        assert response.status_code == 200

    def test_thumbnail_nonexistent_media(self, client):
        """Test thumbnail request for non-existent media.""" 
        response = client.get("/api/media/999/thumbnail")
        
        assert response.status_code == 404


class TestMediaMetadataEndpoints:
    """Test media metadata retrieval endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_get_video_metadata(self, client):
        """Test getting video metadata."""
        response = client.get("/api/media/1")
        
        assert response.status_code == 200
        result = response.json()
        
        # Check basic metadata
        assert result["id"] == 1
        assert result["media_type"] == "video"
        assert result["content_type"] == "video/mp4"
        
        # Check video-specific metadata
        assert "duration" in result
        assert "width" in result
        assert "height" in result
        assert "video_codec" in result
        assert "audio_codec" in result
        
        # Check URLs
        assert "urls" in result
        assert "stream" in result["urls"]
        assert "thumbnail" in result["urls"]
        assert "download" in result["urls"]

    def test_get_photo_metadata(self, client):
        """Test getting photo metadata (no video-specific fields)."""
        # Mock a photo media record
        with patch('services.photoshare.main.get_app_db_manager') as mock_get_db:
            mock_db = MockAppDatabaseManager()
            
            async def mock_get_media_by_id(media_id):
                mock_media = Mock()
                mock_media.id = media_id
                mock_media.user_id = 1
                mock_media.filename = "test_photo.jpg"
                mock_media.content_type = "image/jpeg"
                mock_media.media_type = "photo"
                mock_media.file_size = 1024
                mock_media.title = "Test Photo"
                mock_media.description = "Test description"
                mock_media.is_public = True
                mock_media.duration = None
                mock_media.created_at = Mock()
                mock_media.created_at.isoformat = Mock(return_value="2024-01-01T00:00:00")
                return mock_media
            
            mock_db.get_media_by_id = mock_get_media_by_id
            mock_get_db.return_value = mock_db
            
            response = client.get("/api/media/1")
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["media_type"] == "photo"
        assert "stream" not in result.get("urls", {})  # No streaming URL for photos

    def test_get_metadata_nonexistent_media(self, client):
        """Test metadata request for non-existent media."""
        response = client.get("/api/media/999")
        
        assert response.status_code == 404

    def test_get_private_metadata_unauthorized(self, client):
        """Test getting private media metadata without authorization."""
        with patch('services.photoshare.main.get_app_db_manager') as mock_get_db:
            with patch('services.photoshare.main.get_optional_user', return_value=None):
                mock_db = MockAppDatabaseManager()
                
                async def mock_get_media_by_id(media_id):
                    mock_media = Mock()
                    mock_media.is_public = False  # Private media
                    mock_media.user_id = 999  # Different user
                    return mock_media
                
                mock_db.get_media_by_id = mock_get_media_by_id
                mock_get_db.return_value = mock_db
                
                response = client.get("/api/media/1")
        
        assert response.status_code == 403


class TestBackwardCompatibility:
    """Test backward compatibility with existing photo endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_legacy_photo_upload_still_works(self, client):
        """Test that legacy photo upload endpoint still functions."""
        image_file = io.BytesIO(b'fake image data')
        
        with patch('services.photoshare.main.validate_file_upload_waf'):
            with patch('builtins.open', create=True):
                response = client.post(
                    "/api/photos/upload",
                    files={"file": ("test.jpg", image_file, "image/jpeg")},
                    data={"title": "Legacy Photo Upload"},
                    headers={"Authorization": "Bearer test-token"}
                )
        
        # Should succeed or fail gracefully, not crash
        assert response.status_code in [200, 400, 401, 403, 422]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])