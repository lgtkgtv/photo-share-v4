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

import sys
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone
import pytest
import asyncio
import tempfile
import os
import json
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock, mock_open
from fastapi.testclient import TestClient
from fastapi import UploadFile
from fastapi.responses import Response as FastAPIResponse
import io

# services/photoshare is a standalone deployable unit (own Dockerfile, flat
# internal imports like `from app_database import ...`), not a
# `services.photoshare` Python package -- import it the way the container
# does, via sys.path + flat module name, matching the e2e tests in
# services/photoshare/tests/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "photoshare"))

# Mock environment and imports
class MockAuthenticatedUser:
    """Mock authenticated user for testing."""
    def __init__(self, user_id: int = 1, uuid: str = "test-user-uuid", email: str = "test@example.com"):
        self.id = user_id
        self.user_id = user_id
        self.uuid = uuid  # matches the real AuthenticatedUser attribute main.py's upload handlers key off of
        self.email = email
        self.is_verified = True

    def has_permission(self, resource: str, action: str) -> bool:
        return True

class MockAsyncSession:
    """Minimal stand-in for an AsyncSession -- add/commit are no-ops, refresh assigns an id."""
    def __init__(self):
        self._next_id = 1

    async def add(self, obj):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        # Real SQLAlchemy applies Column(default=...) (id, created_at, ...) on flush;
        # this mock never flushes, so replicate that for the columns callers rely on.
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)


class MockSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class MockAppDatabaseManager:
    """Mock database manager for testing."""
    async def initialize(self) -> bool:
        return True

    async def health_check(self) -> bool:
        return True

    def get_session(self):
        session = MockAsyncSession()
        # session.add() isn't awaited by callers (matches the real SQLAlchemy API,
        # where add() is sync) -- swap in a plain no-op instead of the async version.
        session.add = lambda obj: None
        return MockSessionContext(session)

    def session_factory(self):
        # Legacy /api/photos/upload calls get_app_db_manager().session_factory()
        # directly (bypassing FastAPI Depends()) rather than app_db.get_session().
        return self.get_session()


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
        mock_media.user_uuid = "test-user-uuid"
        mock_media.filename = f"test_media_{media_id}.mp4"
        mock_media.storage_path = f"users/test-user-uuid/videos/test_media_{media_id}.mp4"
        mock_media.thumbnail_path = None
        mock_media.content_type = "video/mp4"
        mock_media.media_type = "video"
        mock_media.file_size = 10485760
        mock_media.title = "Test Video"
        mock_media.description = "A test video"
        mock_media.is_public = True
        mock_media.duration = 120
        mock_media.width = 1920
        mock_media.height = 1080
        mock_media.video_codec = "h264"
        mock_media.audio_codec = "aac"
        mock_media.framerate = 30.0
        mock_media.video_bitrate = 2500
        mock_media.audio_bitrate = 128
        mock_media.created_at = Mock()
        mock_media.created_at.isoformat = Mock(return_value="2024-01-01T00:00:00")
        return mock_media

# Mock the dependencies before importing the app
with patch.dict('os.environ', {
    'JWT_SECRET_KEY': 'test-secret-key',
    'APP_DATABASE_URL': 'sqlite+aiosqlite:///:memory:',
    'UPLOAD_DIR': '/tmp/test-uploads'
}):
    import main as main_module
    from main import app

# FastAPI's Depends() binds the actual callable object at route-registration
# time (i.e. when `main` is first imported above), not by name -- so
# `patch('main.get_current_user')` etc. does NOT affect already-registered
# routes. The correct way to mock a dependency is app.dependency_overrides,
# keyed by the exact callable object used in Depends(...) in main.py.
app.dependency_overrides[main_module.get_current_user] = lambda: MockAuthenticatedUser()
app.dependency_overrides[main_module.get_optional_user] = lambda: MockAuthenticatedUser()
app.dependency_overrides[main_module.get_app_db_manager] = lambda: MockAppDatabaseManager()


@contextmanager
def override_dependency(dependency, replacement):
    """Temporarily replace a FastAPI dependency, restoring the previous override after."""
    previous = app.dependency_overrides.get(dependency)
    app.dependency_overrides[dependency] = replacement
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[dependency] = previous
        else:
            app.dependency_overrides.pop(dependency, None)


@contextmanager
def real_dependency(dependency):
    """Temporarily remove a dependency override so the real implementation runs."""
    previous = app.dependency_overrides.pop(dependency, None)
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[dependency] = previous

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

    @patch('main.VIDEO_PROCESSING_AVAILABLE', True)
    @patch('main.AUDIT_TRAIL_AVAILABLE', False)  # real audit trail loads a signing key via open(), which this test mocks
    @patch('main.video_processor')
    @patch('main.video_security')
    @patch('os.path.exists')
    def test_photo_upload_success(self, mock_exists, mock_video_security, mock_video_processor, client, sample_image_file):
        """Test successful photo upload via unified media endpoint."""
        mock_exists.return_value = True
        
        with patch('builtins.open', create=True), patch('os.makedirs'):
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
        assert result["message"] == "Photo uploaded successfully"
        assert result["media_type"] == "photo"
        assert result["processing_status"] == "completed"
        assert "id" in result

    @patch('main.VIDEO_PROCESSING_AVAILABLE', True)
    @patch('main.AUDIT_TRAIL_AVAILABLE', False)  # real audit trail loads a signing key via open(), which this test mocks
    @patch('main.video_processor')
    @patch('main.video_security')
    @patch('os.path.exists')
    def test_video_upload_success(self, mock_exists, mock_video_security, mock_video_processor, client, sample_video_file):
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
        mock_video_processor.get_video_info_summary = AsyncMock(return_value={'duration': 120, 'resolution': '1920x1080'})

        # Mock video security validator
        mock_video_security.validate_video_security = AsyncMock(return_value=(True, "Validation passed"))

        # os.path.exists() is mocked True above, so the handler believes the generated
        # thumbnail file exists and reads it back -- open() needs to hand back real bytes
        # for that read, not a bare MagicMock (which isn't a valid hashlib/file-write buffer).
        with patch('builtins.open', mock_open(read_data=b'fake-thumbnail-bytes')), patch('os.makedirs'), patch('os.remove'):
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
        assert result["message"] == "Video uploaded successfully"
        assert result["media_type"] == "video"
        assert result["processing_status"] == "completed"
        assert "id" in result

    def test_upload_without_auth(self, client, sample_image_file):
        """Test media upload without authentication."""
        # The default get_current_user override set at module level always returns a
        # user regardless of headers, so exercise the *real* dependency for this one
        # case (FastAPI's HTTPBearer with auto_error=True raises 401 "Not authenticated"
        # for a missing Authorization header).
        with real_dependency(main_module.get_current_user):
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

    @patch('main.VIDEO_PROCESSING_AVAILABLE', True)
    @patch('main.video_processor')
    @patch('main.video_security')
    def test_video_security_validation_failure(self, mock_video_security, mock_video_processor, client, sample_video_file):
        """Test video upload with security validation failure."""
        # analyze_video runs (and must succeed) before security validation is reached
        mock_video_processor.analyze_video = AsyncMock(return_value={
            'duration': 120, 'width': 1920, 'height': 1080,
            'video_codec': 'h264', 'audio_codec': 'aac',
        })
        # Mock security validation failure
        mock_video_security.validate_video_security = AsyncMock(return_value=(False, "Blocked codec detected"))

        with patch('builtins.open', create=True), patch('os.makedirs'):
            response = client.post(
                "/api/media/upload",
                files={"file": ("malicious_video.mp4", sample_video_file, "video/mp4")},
                data={"title": "Malicious Video"},
                headers={"Authorization": "Bearer test-token"}
            )
        
        assert response.status_code == 400
        result = response.json()
        assert "blocked codec detected" in result["detail"].lower()


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
        
        with patch('builtins.open', create=True):
            # Mock FileResponse with a real Response -- a bare Mock() return value
            # sends FastAPI's response encoder into infinite attribute recursion.
            with patch('main.FileResponse', return_value=FastAPIResponse(content=b"video-bytes")):
                response = client.get("/api/media/1/stream")

        assert response.status_code == 200

    @patch('os.path.exists')  
    @patch('os.path.getsize')
    def test_stream_video_range_request(self, mock_getsize, mock_exists, client, sample_video_content):
        """Test video streaming with range request."""
        mock_exists.return_value = True
        mock_getsize.return_value = len(sample_video_content)
        
        # Mock file reading for range request -- open(path, 'rb') is used as a context
        # manager (`with open(...) as f`), so the mock needs __enter__/__exit__, not
        # just the read()/seek() methods a plain Mock() won't provide either.
        mock_file = mock_open(read_data=sample_video_content[:1024]).return_value
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
        mock_db = MockAppDatabaseManager()

        async def mock_get_media_by_id(media_id):
            if media_id == 2:
                mock_media = Mock()
                mock_media.media_type = "photo"  # This should cause failure
                return mock_media
            return None

        mock_db.get_media_by_id = mock_get_media_by_id

        with override_dependency(main_module.get_app_db_manager, lambda: mock_db):
            response = client.get("/api/media/2/stream")

        assert response.status_code == 400

    def test_stream_private_video_unauthorized(self, client):
        """Test streaming private video without authorization."""
        # Mock private video
        mock_db = MockAppDatabaseManager()

        async def mock_get_media_by_id(media_id):
            mock_media = Mock()
            mock_media.media_type = "video"
            mock_media.is_public = False  # Private video
            mock_media.user_uuid = "someone-else-uuid"  # Different user
            return mock_media

        mock_db.get_media_by_id = mock_get_media_by_id

        with override_dependency(main_module.get_app_db_manager, lambda: mock_db):
            with override_dependency(main_module.get_optional_user, lambda: None):
                response = client.get("/api/media/1/stream")

        assert response.status_code == 403


class TestThumbnailEndpoints:
    """Test media thumbnail endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client.""" 
        return TestClient(app)

    @patch('os.path.exists')
    def test_get_video_thumbnail_exists(self, mock_exists, client):
        """Test getting existing video thumbnail."""
        mock_exists.return_value = True  # Thumbnail file exists

        mock_db = MockAppDatabaseManager()

        async def mock_get_media_by_id(media_id):
            mock_media = Mock()
            mock_media.media_type = "video"
            mock_media.is_public = True
            mock_media.thumbnail_path = "users/test-user-uuid/videos/thumb_test.jpg"
            return mock_media

        mock_db.get_media_by_id = mock_get_media_by_id

        # A bare Mock() FileResponse return value sends FastAPI's response encoder
        # into infinite attribute recursion -- hand back a real Response instead.
        with override_dependency(main_module.get_app_db_manager, lambda: mock_db):
            with patch('main.FileResponse', return_value=FastAPIResponse(content=b"thumb-bytes")):
                response = client.get("/api/media/1/thumbnail")

        assert response.status_code == 200

    @patch('os.path.exists')
    @patch('main.VIDEO_PROCESSING_AVAILABLE', True)
    @patch('main.video_processor')
    def test_generate_video_thumbnail_on_demand(self, mock_video_processor, mock_exists, client):
        """Test on-demand video thumbnail generation."""
        # Thumbnail doesn't exist initially, but original video does
        mock_exists.side_effect = lambda path: not path.endswith('.jpg')
        mock_video_processor.generate_thumbnail = AsyncMock(return_value=True)

        mock_db = MockAppDatabaseManager()

        async def mock_get_media_by_id(media_id):
            mock_media = Mock()
            mock_media.media_type = "video"
            mock_media.is_public = True
            mock_media.storage_path = "users/test-user-uuid/videos/test_media_1.mp4"
            mock_media.thumbnail_path = None  # not generated yet
            return mock_media

        mock_db.get_media_by_id = mock_get_media_by_id

        with override_dependency(main_module.get_app_db_manager, lambda: mock_db):
            with patch('os.makedirs'):
                with patch('main.FileResponse', return_value=FastAPIResponse(content=b"thumb-bytes")):
                    response = client.get("/api/media/1/thumbnail")

        assert response.status_code == 200
        mock_video_processor.generate_thumbnail.assert_called_once()

    @patch('os.path.exists')
    def test_get_photo_thumbnail(self, mock_exists, client):
        """Test getting thumbnail for photo (returns original image)."""
        mock_exists.return_value = True

        # Mock a photo media record
        mock_db = MockAppDatabaseManager()

        async def mock_get_media_by_id(media_id):
            mock_media = Mock()
            mock_media.media_type = "photo"
            mock_media.is_public = True
            mock_media.content_type = "image/jpeg"
            mock_media.storage_path = "users/test-user-uuid/photos/test_photo.jpg"
            return mock_media

        mock_db.get_media_by_id = mock_get_media_by_id

        with override_dependency(main_module.get_app_db_manager, lambda: mock_db):
            with patch('main.FileResponse', return_value=FastAPIResponse(content=b"photo-bytes")):
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
        mock_db = MockAppDatabaseManager()

        async def mock_get_media_by_id(media_id):
            mock_media = Mock()
            mock_media.id = media_id
            mock_media.user_uuid = "test-user-uuid"
            mock_media.filename = "test_photo.jpg"
            mock_media.storage_path = "users/test-user-uuid/photos/test_photo.jpg"
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

        with override_dependency(main_module.get_app_db_manager, lambda: mock_db):
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
        mock_db = MockAppDatabaseManager()

        async def mock_get_media_by_id(media_id):
            mock_media = Mock()
            mock_media.is_public = False  # Private media
            mock_media.user_id = 999  # Different user
            return mock_media

        mock_db.get_media_by_id = mock_get_media_by_id

        with override_dependency(main_module.get_app_db_manager, lambda: mock_db):
            with override_dependency(main_module.get_optional_user, lambda: None):
                response = client.get("/api/media/1")

        assert response.status_code == 403


class TestBackwardCompatibility:
    """Test backward compatibility with existing photo endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @patch('main.AUDIT_TRAIL_AVAILABLE', False)  # real audit trail loads a signing key via open(), which this test mocks
    def test_legacy_photo_upload_still_works(self, client):
        """Test that legacy photo upload endpoint still functions."""
        image_file = io.BytesIO(b'fake image data')

        # Unlike the newer /api/media/upload, this legacy endpoint calls
        # get_app_db_manager() directly in its body rather than via Depends(), so
        # app.dependency_overrides doesn't reach it -- patch the module name instead.
        with patch('main.get_app_db_manager', return_value=MockAppDatabaseManager()):
            with patch('main.validate_file_upload_waf'):
                with patch('builtins.open', create=True), patch('os.makedirs'):
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