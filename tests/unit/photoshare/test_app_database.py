#!/usr/bin/env python3
"""
Unit tests for application database models and operations.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

class MockAsyncContextManager:
    """Helper class for mocking async context managers."""
    def __init__(self, return_value):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

# Mock the database module before importing
with patch.dict('os.environ', {'APP_DATABASE_URL': 'sqlite+aiosqlite:///:memory:'}):
    from services.photoshare.app_database import (
        Photo, Media, Album, AlbumPhoto, PhotoShare, PhotoTag, PhotoComment,
        PhotoAnalytics, UserPreference, AppDatabaseManager
    )

class TestPhotoModel:
    """Test Photo model."""
    
    def test_photo_creation(self):
        """Test photo creation with valid data."""
        photo = Photo(
            user_uuid="test-user-uuid",
            user_email="test@example.com",
            filename="test_photo.jpg",
            original_filename="my_photo.jpg",
            content_type="image/jpeg",
            file_size=1024,
            storage_path="/storage/test_photo.jpg",
            title="Test Photo",
            description="A test photo",
            is_public=True
        )
        
        assert photo.user_uuid == "test-user-uuid"
        assert photo.user_email == "test@example.com"
        assert photo.filename == "test_photo.jpg"
        assert photo.original_filename == "my_photo.jpg"
        assert photo.content_type == "image/jpeg"
        assert photo.file_size == 1024
        assert photo.title == "Test Photo"
        assert photo.description == "A test photo"
        assert photo.is_public is True
    
    def test_photo_to_dict(self):
        """Test photo serialization to dictionary."""
        created_at = datetime.now(timezone.utc)
        
        photo = Photo(
            id=1,
            user_uuid="test-user-uuid",
            user_email="test@example.com",
            filename="test_photo.jpg",
            content_type="image/jpeg",
            file_size=1024,
            title="Test Photo",
            is_public=True
        )
        photo.created_at = created_at
        
        photo_dict = photo.to_dict()
        
        assert photo_dict["id"] == 1
        assert photo_dict["user_uuid"] == "test-user-uuid"
        assert photo_dict["user_email"] == "test@example.com"
        assert photo_dict["filename"] == "test_photo.jpg"
        assert photo_dict["title"] == "Test Photo"
        assert photo_dict["is_public"] is True
        assert photo_dict["created_at"] == created_at.isoformat()

class TestAlbumModel:
    """Test Album model."""
    
    def test_album_creation(self):
        """Test album creation with valid data."""
        album = Album(
            user_uuid="test-user-uuid",
            user_email="test@example.com",
            name="Test Album",
            description="My test album",
            is_public=False,
            photo_count=5,
            cover_photo_id=1
        )
        
        assert album.user_uuid == "test-user-uuid"
        assert album.user_email == "test@example.com"
        assert album.name == "Test Album"
        assert album.description == "My test album"
        assert album.is_public is False
        assert album.photo_count == 5
        assert album.cover_photo_id == 1
    
    def test_album_to_dict(self):
        """Test album serialization to dictionary."""
        album = Album(
            id=1,
            user_uuid="test-user-uuid",
            name="Test Album",
            is_public=False,
            photo_count=3
        )
        
        album_dict = album.to_dict()
        
        assert album_dict["id"] == 1
        assert album_dict["name"] == "Test Album"
        assert album_dict["is_public"] is False
        assert album_dict["photo_count"] == 3

class TestAlbumPhotoModel:
    """Test Album-Photo relationship model."""
    
    def test_album_photo_creation(self):
        """Test album-photo relationship creation."""
        added_at = datetime.now(timezone.utc)
        
        album_photo = AlbumPhoto(
            album_id=1,
            photo_id=2,
            sort_order=0,
            added_at=added_at
        )
        
        assert album_photo.album_id == 1
        assert album_photo.photo_id == 2
        assert album_photo.sort_order == 0
        assert album_photo.added_at == added_at
    
    def test_album_photo_to_dict(self):
        """Test album-photo serialization to dictionary."""
        added_at = datetime.now(timezone.utc)
        
        album_photo = AlbumPhoto(
            id=1,
            album_id=2,
            photo_id=3,
            sort_order=1,
            added_at=added_at
        )
        
        album_photo_dict = album_photo.to_dict()
        
        assert album_photo_dict["id"] == 1
        assert album_photo_dict["album_id"] == 2
        assert album_photo_dict["photo_id"] == 3
        assert album_photo_dict["sort_order"] == 1
        assert album_photo_dict["added_at"] == added_at.isoformat()

class TestPhotoShareModel:
    """Test Photo Share model."""
    
    def test_photo_share_creation(self):
        """Test photo share creation with valid data."""
        expires_at = datetime.now(timezone.utc)
        
        photo_share = PhotoShare(
            photo_id=1,
            share_token="share123",
            share_type="public",
            max_downloads=10,
            shared_by_uuid="user-uuid",
            shared_with_email="recipient@example.com",
            share_message="Check out this photo!",
            expires_at=expires_at,
            is_active=True
        )
        
        assert photo_share.photo_id == 1
        assert photo_share.share_token == "share123"
        assert photo_share.share_type == "public"
        assert photo_share.max_downloads == 10
        assert photo_share.shared_by_uuid == "user-uuid"
        assert photo_share.shared_with_email == "recipient@example.com"
        assert photo_share.expires_at == expires_at
        assert photo_share.is_active is True

class TestPhotoTagModel:
    """Test Photo Tag model."""
    
    def test_photo_tag_creation(self):
        """Test photo tag creation with valid data."""
        photo_tag = PhotoTag(
            photo_id=1,
            tag="sunset",
            tag_type="user",
            confidence="high"
        )
        
        assert photo_tag.photo_id == 1
        assert photo_tag.tag == "sunset"
        assert photo_tag.tag_type == "user"
        assert photo_tag.confidence == "high"
    
    def test_photo_tag_auto(self):
        """Test auto-generated photo tag."""
        photo_tag = PhotoTag(
            photo_id=1,
            tag="person",
            tag_type="auto",
            confidence="medium"
        )
        
        assert photo_tag.tag_type == "auto"
        assert photo_tag.confidence == "medium"

class TestPhotoCommentModel:
    """Test Photo Comment model."""
    
    def test_photo_comment_creation(self):
        """Test photo comment creation with valid data."""
        photo_comment = PhotoComment(
            photo_id=1,
            commenter_uuid="commenter-uuid",
            commenter_email="commenter@example.com",
            commenter_name="John Doe",
            comment="Great photo!",
            is_approved=True,
            is_flagged=False
        )
        
        assert photo_comment.photo_id == 1
        assert photo_comment.commenter_uuid == "commenter-uuid"
        assert photo_comment.commenter_email == "commenter@example.com"
        assert photo_comment.commenter_name == "John Doe"
        assert photo_comment.comment == "Great photo!"
        assert photo_comment.is_approved is True
        assert photo_comment.is_flagged is False

class TestPhotoAnalyticsModel:
    """Test Photo Analytics model."""
    
    def test_photo_analytics_creation(self):
        """Test photo analytics creation with valid data."""
        timestamp = datetime.now(timezone.utc)
        
        analytics = PhotoAnalytics(
            photo_id=1,
            event_type="view",
            viewer_uuid="viewer-uuid",
            viewer_ip="192.168.1.1",
            referrer="https://example.com",
            user_agent="Mozilla/5.0...",
            timestamp=timestamp
        )
        
        assert analytics.photo_id == 1
        assert analytics.event_type == "view"
        assert analytics.viewer_uuid == "viewer-uuid"
        assert analytics.viewer_ip == "192.168.1.1"
        assert analytics.timestamp == timestamp
    
    def test_photo_analytics_events(self):
        """Test different analytics event types."""
        events = ["view", "download", "share", "like"]
        
        for event in events:
            analytics = PhotoAnalytics(
                photo_id=1,
                event_type=event,
                viewer_ip="192.168.1.1"
            )
            assert analytics.event_type == event

class TestUserPreferenceModel:
    """Test User Preference model."""
    
    def test_user_preference_creation(self):
        """Test user preference creation with valid data."""
        preferences = {
            "theme": "dark",
            "notifications": {
                "email": True,
                "push": False
            },
            "privacy": {
                "default_photo_visibility": "private",
                "allow_comments": True
            }
        }
        
        user_pref = UserPreference(
            user_uuid="user-uuid",
            preferences=preferences
        )
        
        assert user_pref.user_uuid == "user-uuid"
        assert user_pref.preferences == preferences
        assert user_pref.preferences["theme"] == "dark"
        assert user_pref.preferences["notifications"]["email"] is True


class TestMediaModel:
    """Test Media model (unified photo/video model)."""
    
    def test_media_photo_creation(self):
        """Test media creation for photo."""
        media = Media(
            user_uuid="test-user-uuid",
            user_email="test@example.com",
            filename="test_photo.jpg",
            original_filename="my_photo.jpg", 
            content_type="image/jpeg",
            file_size=1024,
            storage_path="/storage/test_photo.jpg",
            title="Test Photo",
            description="A test photo",
            is_public=True,
            media_type="photo"
        )
        
        assert media.user_uuid == "test-user-uuid"
        assert media.user_email == "test@example.com"
        assert media.filename == "test_photo.jpg"
        assert media.original_filename == "my_photo.jpg"
        assert media.content_type == "image/jpeg"
        assert media.file_size == 1024
        assert media.storage_path == "/storage/test_photo.jpg"
        assert media.title == "Test Photo"
        assert media.description == "A test photo"
        assert media.is_public is True
        assert media.media_type == "photo"
        # Video-specific fields should be None for photos
        assert media.duration is None
        assert media.video_codec is None
        assert media.audio_codec is None
    
    def test_media_video_creation(self):
        """Test media creation for video."""
        media = Media(
            user_uuid="test-user-uuid",
            user_email="test@example.com",
            filename="test_video.mp4",
            original_filename="my_video.mp4",
            content_type="video/mp4", 
            file_size=10485760,  # 10MB
            storage_path="/storage/test_video.mp4",
            title="Test Video",
            description="A test video",
            is_public=False,
            media_type="video",
            duration=120,  # 2 minutes
            width=1920,
            height=1080,
            video_codec="h264",
            audio_codec="aac",
            framerate=30.0
        )
        
        assert media.user_uuid == "test-user-uuid"
        assert media.user_email == "test@example.com"
        assert media.filename == "test_video.mp4"
        assert media.content_type == "video/mp4"
        assert media.file_size == 10485760
        assert media.storage_path == "/storage/test_video.mp4"
        assert media.media_type == "video"
        assert media.duration == 120
        assert media.width == 1920
        assert media.height == 1080
        assert media.video_codec == "h264"
        assert media.audio_codec == "aac"
        assert media.framerate == 30.0
    
    def test_media_to_dict_photo(self):
        """Test photo media serialization to dictionary."""
        created_at = datetime.now(timezone.utc)
        
        media = Media(
            id=1,
            user_uuid="test-user-uuid",
            user_email="test@example.com",
            filename="test_photo.jpg",
            original_filename="test_photo.jpg",
            content_type="image/jpeg",
            file_size=1024,
            storage_path="/storage/test_photo.jpg",
            title="Test Photo",
            is_public=True,
            media_type="photo",
            created_at=created_at
        )
        
        media_dict = media.to_dict()
        
        assert media_dict["id"] == 1
        assert media_dict["user_uuid"] == "test-user-uuid"
        assert media_dict["filename"] == "test_photo.jpg"
        assert media_dict["content_type"] == "image/jpeg"
        assert media_dict["media_type"] == "photo"
        assert media_dict["is_public"] is True
        assert "duration" not in media_dict or media_dict["duration"] is None
    
    def test_media_to_dict_video(self):
        """Test video media serialization to dictionary."""
        created_at = datetime.now(timezone.utc)
        
        media = Media(
            id=2,
            user_uuid="test-user-uuid",
            user_email="test@example.com",
            filename="test_video.mp4",
            original_filename="test_video.mp4",
            content_type="video/mp4",
            file_size=5242880,
            storage_path="/storage/test_video.mp4",
            title="Test Video",
            media_type="video",
            duration=90,
            width=1280,
            height=720,
            video_codec="h264",
            created_at=created_at
        )
        
        media_dict = media.to_dict()
        
        assert media_dict["id"] == 2
        assert media_dict["media_type"] == "video"
        assert media_dict["duration"] == 90
        assert media_dict["width"] == 1280
        assert media_dict["height"] == 720
        assert media_dict["video_codec"] == "h264"
    
    def test_media_is_video_property(self):
        """Test is_video property."""
        photo_media = Media(
            user_uuid="test-user", 
            user_email="test@example.com",
            filename="photo.jpg", 
            original_filename="photo.jpg",
            content_type="image/jpeg",
            file_size=1024,
            storage_path="/storage/photo.jpg",
            media_type="photo"
        )
        video_media = Media(
            user_uuid="test-user", 
            user_email="test@example.com",
            filename="video.mp4", 
            original_filename="video.mp4",
            content_type="video/mp4",
            file_size=1024,
            storage_path="/storage/video.mp4",
            media_type="video"
        )
        
        assert photo_media.is_video is False
        assert video_media.is_video is True
    
    def test_media_is_photo_property(self):
        """Test is_photo property."""
        photo_media = Media(
            user_uuid="test-user", 
            user_email="test@example.com",
            filename="photo.jpg", 
            original_filename="photo.jpg",
            content_type="image/jpeg",
            file_size=1024,
            storage_path="/storage/photo.jpg",
            media_type="photo"
        )
        video_media = Media(
            user_uuid="test-user", 
            user_email="test@example.com",
            filename="video.mp4", 
            original_filename="video.mp4",
            content_type="video/mp4",
            file_size=1024,
            storage_path="/storage/video.mp4",
            media_type="video"
        )
        
        assert photo_media.is_photo is True
        assert video_media.is_photo is False
        
    def test_media_to_dict_includes_video_fields(self):
        """Test that video media dict includes video-specific fields."""
        video_media = Media(
            user_uuid="test-user",
            user_email="test@example.com", 
            filename="video.mp4",
            original_filename="video.mp4",
            content_type="video/mp4",
            file_size=1024,
            storage_path="/storage/video.mp4",
            media_type="video",
            duration=120,
            width=1920,
            height=1080,
            video_codec="h264"
        )
        
        media_dict = video_media.to_dict()
        
        # Should include video-specific fields
        assert "duration" in media_dict
        assert "video_codec" in media_dict  
        assert "stream_url" in media_dict
        assert media_dict["stream_url"] == f"/api/media/{video_media.id}/stream"


class TestAppDatabaseManager:
    """Test Application Database Manager."""
    
    @pytest.fixture
    def db_manager(self):
        """Create database manager instance."""
        return AppDatabaseManager()
    
    @pytest.mark.asyncio
    async def test_initialize(self, db_manager):
        """Test database manager initialization."""
        with patch('services.photoshare.app_database.create_async_engine') as mock_engine:
            with patch('services.photoshare.app_database.async_sessionmaker') as mock_sessionmaker:
                mock_engine.return_value = Mock()
                mock_sessionmaker.return_value = Mock()
                
                result = await db_manager.initialize()
                
                assert result is True
                assert db_manager.engine is not None
                assert db_manager.session_factory is not None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, db_manager):
        """Test successful health check."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        
        # Create a proper async context manager mock
        def mock_session_factory():
            return MockAsyncContextManager(mock_session)
        
        db_manager.session_factory = mock_session_factory
        
        result = await db_manager.health_check()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, db_manager):
        """Test health check failure."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))
        
        # Create a proper async context manager mock
        def mock_session_factory():
            return MockAsyncContextManager(mock_session)
        
        db_manager.session_factory = mock_session_factory
        
        result = await db_manager.health_check()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_tables(self, db_manager):
        """Test database table creation."""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()
        
        mock_engine = Mock()
        mock_engine.begin = Mock(return_value=MockAsyncContextManager(mock_conn))
        
        db_manager.engine = mock_engine
        
        await db_manager.create_tables()
        
        mock_conn.run_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, db_manager):
        """Test database connection cleanup."""
        mock_engine = AsyncMock()
        db_manager.engine = mock_engine
        
        await db_manager.close()
        
        mock_engine.dispose.assert_called_once()