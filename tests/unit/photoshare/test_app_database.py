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
        Photo, Album, AlbumPhoto, PhotoShare, PhotoTag, PhotoComment,
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