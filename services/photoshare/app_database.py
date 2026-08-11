#!/usr/bin/env python3
"""
Application Database Schema (Photo Sharing)
============================================

Dedicated database for application data only - no authentication concerns.
All auth is handled by the separate authentication service.
"""

import os
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, UniqueConstraint, Numeric
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSON
import logging

logger = logging.getLogger(__name__)

# Application database configuration (separate from auth database)
def get_app_database_url():
    """Get application database URL - separate from authentication database."""
    db_host = os.getenv("APP_DB_HOST", "app-db")
    db_port = os.getenv("APP_DB_PORT", "5432")
    db_user = os.getenv("APP_POSTGRES_USER", "app_user")
    db_password = os.getenv("APP_POSTGRES_PASSWORD", "app_secure_password")
    db_name = os.getenv("APP_POSTGRES_DB", "photo_share_app")
    
    return os.getenv(
        "APP_DATABASE_URL", 
        f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

APP_DATABASE_URL = get_app_database_url()

# SQLAlchemy setup for application database
AppBase = declarative_base()

# Legacy Photo class for backward compatibility
class Photo(AppBase):
    """Legacy photo metadata - use Media class for new implementations."""
    __tablename__ = "photos"  # This will be renamed to "media" in migration
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference (UUID from auth service, not foreign key)
    user_uuid = Column(String(36), nullable=False, index=True)  # UUID from auth service
    user_email = Column(String(255), nullable=False, index=True)  # Denormalized for queries
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    
    # Photo metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Photo properties
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    orientation = Column(String(20), nullable=True)  # landscape, portrait, square
    
    # EXIF data (optional)
    exif_data = Column(JSON, nullable=True)
    
    # GPS coordinates (optional)
    latitude = Column(String(50), nullable=True)
    longitude = Column(String(50), nullable=True)
    location_name = Column(String(255), nullable=True)
    
    # Photo classification
    is_public = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    
    # Content moderation
    is_approved = Column(Boolean, default=True, index=True)
    moderation_status = Column(String(20), default="approved", index=True)  # pending, approved, rejected
    moderation_notes = Column(Text, nullable=True)
    
    # Analytics
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    taken_at = Column(DateTime(timezone=True), nullable=True)  # When photo was actually taken
    
    def to_dict(self, include_sensitive_data=False):
        """
        Convert photo to dictionary.
        
        Args:
            include_sensitive_data: If True, includes storage_path and EXIF data
        """
        data = {
            "id": self.id,
            "user_uuid": self.user_uuid,
            "user_email": self.user_email,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "title": self.title,
            "description": self.description,
            "width": self.width,
            "height": self.height,
            "orientation": self.orientation,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "is_archived": self.is_archived,
            "is_approved": self.is_approved,
            "moderation_status": self.moderation_status,
            "view_count": self.view_count,
            "download_count": self.download_count,
            "like_count": self.like_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "taken_at": self.taken_at.isoformat() if self.taken_at else None,
            # API endpoints for secure access
            "download_url": f"/api/photos/{self.id}/download",
            "metadata_url": f"/api/photos/{self.id}"
        }
        
        # Only include sensitive data if explicitly requested (for admin/internal use)
        if include_sensitive_data:
            data.update({
                "storage_path": self.storage_path,
                "exif_data": self.exif_data,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "location_name": self.location_name
            })
        else:
            # For public photos, still include location if the photo owner made it public
            if self.is_public and self.location_name:
                data["location_name"] = self.location_name
                
        return data

class Media(AppBase):
    """Unified media metadata for photos and videos."""
    __tablename__ = "media"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference (UUID from auth service, not foreign key)
    user_uuid = Column(String(36), nullable=False, index=True)  # UUID from auth service
    user_email = Column(String(255), nullable=False, index=True)  # Denormalized for queries
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    
    # Media type and processing
    media_type = Column(String(10), nullable=False, default='photo', index=True)  # 'photo', 'video'
    processing_status = Column(String(20), default='completed', index=True)  # pending, processing, completed, failed
    
    # Media metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Common properties (both photos and videos)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    orientation = Column(String(20), nullable=True)  # landscape, portrait, square
    
    # Video-specific properties
    duration = Column(Integer, nullable=True)  # Video duration in seconds
    video_codec = Column(String(20), nullable=True)  # H.264, H.265, VP9, AV1
    audio_codec = Column(String(20), nullable=True)  # AAC, MP3, Opus
    resolution = Column(String(20), nullable=True)  # 1080p, 720p, 4K
    framerate = Column(Numeric(5,2), nullable=True)  # 30.0, 60.0 fps
    bitrate = Column(Integer, nullable=True)  # Video bitrate in kbps
    thumbnail_path = Column(String(500), nullable=True)  # Video thumbnail storage
    transcoded_variants = Column(JSON, nullable=True)  # Different quality variants
    
    # EXIF/metadata (for photos primarily)
    exif_data = Column(JSON, nullable=True)
    
    # GPS coordinates (optional)
    latitude = Column(String(50), nullable=True)
    longitude = Column(String(50), nullable=True)
    location_name = Column(String(255), nullable=True)
    
    # Media classification
    is_public = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    
    # Content moderation
    is_approved = Column(Boolean, default=True, index=True)
    moderation_status = Column(String(20), default="approved", index=True)  # pending, approved, rejected
    moderation_notes = Column(Text, nullable=True)
    
    # Analytics
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    taken_at = Column(DateTime(timezone=True), nullable=True)  # When photo/video was actually taken
    
    @property
    def is_video(self) -> bool:
        """Check if this media item is a video."""
        return self.media_type == 'video'
    
    @property
    def is_photo(self) -> bool:
        """Check if this media item is a photo."""
        return self.media_type == 'photo'
    
    @property
    def is_processing(self) -> bool:
        """Check if media is still being processed."""
        return self.processing_status in ['pending', 'processing']
    
    def to_dict(self, include_sensitive_data=False):
        """
        Convert media to dictionary.
        
        Args:
            include_sensitive_data: If True, includes storage_path and EXIF data
        """
        data = {
            "id": self.id,
            "user_uuid": self.user_uuid,
            "user_email": self.user_email,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "media_type": self.media_type,
            "processing_status": self.processing_status,
            "title": self.title,
            "description": self.description,
            "width": self.width,
            "height": self.height,
            "orientation": self.orientation,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "is_archived": self.is_archived,
            "is_approved": self.is_approved,
            "moderation_status": self.moderation_status,
            "view_count": self.view_count,
            "download_count": self.download_count,
            "like_count": self.like_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "taken_at": self.taken_at.isoformat() if self.taken_at else None,
        }
        
        # Add video-specific fields for videos
        if self.is_video:
            data.update({
                "duration": self.duration,
                "video_codec": self.video_codec,
                "audio_codec": self.audio_codec,
                "resolution": self.resolution,
                "framerate": float(self.framerate) if self.framerate else None,
                "bitrate": self.bitrate,
                "transcoded_variants": self.transcoded_variants,
                # API endpoints for videos
                "stream_url": f"/api/media/{self.id}/stream",
                "thumbnail_url": f"/api/media/{self.id}/thumbnail" if self.thumbnail_path else None,
            })
        
        # API endpoints for secure access
        data.update({
            "download_url": f"/api/media/{self.id}/download",
            "metadata_url": f"/api/media/{self.id}"
        })
        
        # Only include sensitive data if explicitly requested (for admin/internal use)
        if include_sensitive_data:
            data.update({
                "storage_path": self.storage_path,
                "thumbnail_path": self.thumbnail_path,
                "exif_data": self.exif_data,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "location_name": self.location_name
            })
        else:
            # For public media, still include location if the owner made it public
            if self.is_public and self.location_name:
                data["location_name"] = self.location_name
                
        return data

class Album(AppBase):
    """Photo albums/collections."""
    __tablename__ = "albums"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference (UUID from auth service)
    user_uuid = Column(String(36), nullable=False, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    
    # Album information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Album properties
    is_public = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    
    # Album metadata
    photo_count = Column(Integer, default=0)
    cover_photo_id = Column(Integer, nullable=True)  # Reference to Photo.id
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_uuid": self.user_uuid,
            "user_email": self.user_email,
            "name": self.name,
            "description": self.description,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "photo_count": self.photo_count,
            "cover_photo_id": self.cover_photo_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class AlbumPhoto(AppBase):
    """Album-Photo relationship."""
    __tablename__ = "album_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    album_id = Column(Integer, ForeignKey("albums.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Ordering within album
    sort_order = Column(Integer, default=0, index=True)
    
    # Timestamps
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (UniqueConstraint('album_id', 'photo_id', name='_album_photo_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "album_id": self.album_id,
            "photo_id": self.photo_id,
            "sort_order": self.sort_order,
            "added_at": self.added_at.isoformat() if self.added_at else None
        }

class PhotoShare(AppBase):
    """Photo sharing records."""
    __tablename__ = "photo_shares"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Sharing information
    share_token = Column(String(64), unique=True, nullable=False, index=True)
    share_type = Column(String(20), nullable=False)  # public, private, password
    password_hash = Column(String(255), nullable=True)  # For password-protected shares
    
    # Access control
    max_downloads = Column(Integer, nullable=True)
    download_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Sharing metadata
    shared_by_uuid = Column(String(36), nullable=False)
    shared_with_email = Column(String(255), nullable=True)  # For private shares
    share_message = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "share_token": self.share_token,
            "share_type": self.share_type,
            "max_downloads": self.max_downloads,
            "download_count": self.download_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "shared_by_uuid": self.shared_by_uuid,
            "shared_with_email": self.shared_with_email,
            "share_message": self.share_message,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }

class PhotoTag(AppBase):
    """Photo tags for organization."""
    __tablename__ = "photo_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Tag information
    tag = Column(String(50), nullable=False, index=True)
    tag_type = Column(String(20), default="user")  # user, auto, system
    confidence = Column(String(10), nullable=True)  # For AI-generated tags: high, medium, low
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (UniqueConstraint('photo_id', 'tag', name='_photo_tag_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "tag": self.tag,
            "tag_type": self.tag_type,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class PhotoComment(AppBase):
    """Comments on photos."""
    __tablename__ = "photo_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Commenter information (from auth service)
    commenter_uuid = Column(String(36), nullable=False, index=True)
    commenter_email = Column(String(255), nullable=False)
    commenter_name = Column(String(255), nullable=True)
    
    # Comment content
    comment = Column(Text, nullable=False)
    
    # Comment status
    is_approved = Column(Boolean, default=True, index=True)
    is_flagged = Column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "commenter_uuid": self.commenter_uuid,
            "commenter_email": self.commenter_email,
            "commenter_name": self.commenter_name,
            "comment": self.comment,
            "is_approved": self.is_approved,
            "is_flagged": self.is_flagged,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class PhotoAnalytics(AppBase):
    """Photo analytics and metrics."""
    __tablename__ = "photo_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Analytics data
    event_type = Column(String(20), nullable=False, index=True)  # view, download, share, like
    viewer_uuid = Column(String(36), nullable=True)  # If authenticated
    viewer_ip = Column(String(45), nullable=True)  # IPv6 compatible
    
    # Context
    referrer = Column(String(255), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "event_type": self.event_type,
            "viewer_uuid": self.viewer_uuid,
            "viewer_ip": self.viewer_ip,
            "referrer": self.referrer,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

class UserPreference(AppBase):
    """User application preferences (not auth-related)."""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User reference (UUID from auth service)
    user_uuid = Column(String(36), unique=True, nullable=False, index=True)
    
    # Preference data
    preferences = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_uuid": self.user_uuid,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

# Database connection and session management
class AppDatabaseManager:
    """Manages application database connections and sessions."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        
    async def initialize(self):
        """Initialize database connection."""
        try:
            engine_kwargs = {
                "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
            }
            # SQLite's async driver uses a single StaticPool connection and doesn't
            # accept QueuePool-only kwargs like pool_size/max_overflow/pool_recycle.
            if not APP_DATABASE_URL.startswith("sqlite"):
                engine_kwargs.update(
                    pool_size=20,
                    max_overflow=0,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )

            self.engine = create_async_engine(APP_DATABASE_URL, **engine_kwargs)

            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Application database manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize application database: {e}")
            return False
            
    async def create_tables(self):
        """Create all application database tables."""
        if not self.engine:
            await self.initialize()
            
        async with self.engine.begin() as conn:
            await conn.run_sync(AppBase.metadata.create_all)
            
        logger.info("Application database tables created successfully")
        
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
                
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            if not self.engine:
                logger.error("Database engine not initialized")
                return False
                
            async with self.session_factory() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Application database health check failed: {e}")
            return False
            
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Application database connections closed")

# Global application database manager
app_db_manager = AppDatabaseManager()

def get_app_db_manager() -> AppDatabaseManager:
    """Get the global application database manager instance."""
    return app_db_manager