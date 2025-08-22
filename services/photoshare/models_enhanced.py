#!/usr/bin/env python3
"""
Enhanced Database Models for Phase 3 Features
============================================

Additional models for:
- Photo tags and search
- Social features (likes, comments, follows)
- Albums and collections
- User profiles
- Notifications
- Photo metadata and EXIF data
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Import base from existing database
from database import Base

# Enhanced Photo model with metadata
class PhotoMetadata(Base):
    """Extended photo metadata including EXIF data."""
    __tablename__ = "photo_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Image properties
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    format = Column(String(20), nullable=True)
    mode = Column(String(20), nullable=True)
    has_transparency = Column(Boolean, default=False)
    
    # EXIF data
    date_taken = Column(DateTime(timezone=True), nullable=True, index=True)
    camera_make = Column(String(100), nullable=True)
    camera_model = Column(String(100), nullable=True)
    lens_model = Column(String(100), nullable=True)
    software = Column(String(100), nullable=True)
    
    # Camera settings
    exposure_time = Column(String(50), nullable=True)
    f_number = Column(Float, nullable=True)
    iso_speed = Column(Integer, nullable=True)
    focal_length = Column(Float, nullable=True)
    orientation = Column(Integer, nullable=True)
    
    # GPS data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    
    # Processing info
    image_hash = Column(String(32), nullable=True, index=True)  # For duplicate detection
    processed_sizes = Column(JSON, nullable=True)  # Available thumbnail sizes
    
    # Additional metadata
    color_space = Column(String(50), nullable=True)
    dominant_colors = Column(JSON, nullable=True)  # Color palette
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "mode": self.mode,
            "has_transparency": self.has_transparency,
            "date_taken": self.date_taken.isoformat() if self.date_taken else None,
            "camera_make": self.camera_make,
            "camera_model": self.camera_model,
            "lens_model": self.lens_model,
            "software": self.software,
            "exposure_time": self.exposure_time,
            "f_number": self.f_number,
            "iso_speed": self.iso_speed,
            "focal_length": self.focal_length,
            "orientation": self.orientation,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "image_hash": self.image_hash,
            "processed_sizes": self.processed_sizes,
            "color_space": self.color_space,
            "dominant_colors": self.dominant_colors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class PhotoTag(Base):
    """Tags for photos to enable search and categorization."""
    __tablename__ = "photo_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    tag = Column(String(100), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_photo_tags_photo_tag', 'photo_id', 'tag'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "tag": self.tag,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class PhotoLike(Base):
    """Likes for photos - social feature."""
    __tablename__ = "photo_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Ensure one like per user per photo
    __table_args__ = (
        Index('ix_photo_likes_unique', 'photo_id', 'user_id', unique=True),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class PhotoComment(Base):
    """Comments on photos."""
    __tablename__ = "photo_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey("photo_comments.id", ondelete="CASCADE"), nullable=True)  # For replies
    
    is_edited = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "user_id": self.user_id,
            "content": self.content,
            "parent_id": self.parent_id,
            "is_edited": self.is_edited,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class UserFollow(Base):
    """User following relationships."""
    __tablename__ = "user_follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    following_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Ensure one follow relationship per pair
    __table_args__ = (
        Index('ix_user_follows_unique', 'follower_id', 'following_id', unique=True),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "follower_id": self.follower_id,
            "following_id": self.following_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class UserProfile(Base):
    """Extended user profile information."""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Profile info
    display_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Avatar
    avatar_photo_id = Column(Integer, ForeignKey("photos.id", ondelete="SET NULL"), nullable=True)
    
    # Social stats (cached for performance)
    followers_count = Column(Integer, default=0, index=True)
    following_count = Column(Integer, default=0)
    photos_count = Column(Integer, default=0, index=True)
    likes_received_count = Column(Integer, default=0)
    
    # Privacy settings
    is_private = Column(Boolean, default=False, index=True)
    allow_comments = Column(Boolean, default=True)
    allow_tags = Column(Boolean, default=True)
    show_location = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "bio": self.bio,
            "location": self.location,
            "website": self.website,
            "avatar_photo_id": self.avatar_photo_id,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "photos_count": self.photos_count,
            "likes_received_count": self.likes_received_count,
            "is_private": self.is_private,
            "allow_comments": self.allow_comments,
            "allow_tags": self.allow_tags,
            "show_location": self.show_location,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Album(Base):
    """Photo albums/collections."""
    __tablename__ = "albums"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Cover photo
    cover_photo_id = Column(Integer, ForeignKey("photos.id", ondelete="SET NULL"), nullable=True)
    
    # Settings
    is_public = Column(Boolean, default=False, index=True)
    photos_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "cover_photo_id": self.cover_photo_id,
            "is_public": self.is_public,
            "photos_count": self.photos_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class AlbumPhoto(Base):
    """Many-to-many relationship between albums and photos."""
    __tablename__ = "album_photos"
    
    id = Column(Integer, primary_key=True, index=True)
    album_id = Column(Integer, ForeignKey("albums.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    added_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, default=0)  # For ordering photos in album
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Ensure one photo per album (can't add same photo twice)
    __table_args__ = (
        Index('ix_album_photos_unique', 'album_id', 'photo_id', unique=True),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "album_id": self.album_id,
            "photo_id": self.photo_id,
            "added_by": self.added_by,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Notification(Base):
    """User notifications system."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # like, comment, follow, album_share, etc.
    
    # References to related objects
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=True)
    album_id = Column(Integer, ForeignKey("albums.id", ondelete="CASCADE"), nullable=True)
    comment_id = Column(Integer, ForeignKey("photo_comments.id", ondelete="CASCADE"), nullable=True)
    
    # Content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False, index=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "from_user_id": self.from_user_id,
            "photo_id": self.photo_id,
            "album_id": self.album_id,
            "comment_id": self.comment_id,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class PhotoShare(Base):
    """Photo sharing permissions and links."""
    __tablename__ = "photo_shares"
    
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Share settings
    share_token = Column(String(64), unique=True, index=True, nullable=False)  # For public sharing links
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    max_views = Column(Integer, nullable=True)
    current_views = Column(Integer, default=0)
    
    # Permissions
    allow_download = Column(Boolean, default=True)
    allow_comments = Column(Boolean, default=True)
    password_protected = Column(String(255), nullable=True)  # Hashed password
    
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "photo_id": self.photo_id,
            "shared_by": self.shared_by,
            "share_token": self.share_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "max_views": self.max_views,
            "current_views": self.current_views,
            "allow_download": self.allow_download,
            "allow_comments": self.allow_comments,
            "password_protected": bool(self.password_protected),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }