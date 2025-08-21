#!/usr/bin/env python3
"""
Database Integration for Photo Share Service
==========================================

SQLAlchemy models and database connection setup for real PostgreSQL integration.
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, LargeBinary
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@platform-db:5432/photo_share"
)

# SQLAlchemy setup
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_verified": self.is_verified,
            "is_active": self.is_active
        }

class Photo(Base):
    __tablename__ = "photos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Should be ForeignKey in production
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "storage_path": self.storage_path,
            "title": self.title,
            "description": self.description,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # Should be ForeignKey in production
    token = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token": self.token,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active
        }

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    secret = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "secret": self.secret,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

# Database Engine and Session
class DatabaseManager:
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        
    async def initialize(self):
        """Initialize database connection and create tables."""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
            logger.info("Database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
            
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            if not self.engine:
                return False
                
            from sqlalchemy import text
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session."""
    async for session in db_manager.get_session():
        yield session

# Database operations
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_user(self, email: str, password_hash: str) -> User:
        """Create a new user."""
        user = User(email=email, password_hash=password_hash, is_verified=False)  # Require email verification
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        from sqlalchemy import select
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        from sqlalchemy import select
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def update_user_verification(self, user_id: int, is_verified: bool) -> Optional[User]:
        """Update user verification status."""
        from sqlalchemy import select, update
        
        # Update the user
        await self.session.execute(
            update(User).where(User.id == user_id).values(is_verified=is_verified)
        )
        await self.session.commit()
        
        # Return updated user
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

class PhotoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_photo(self, user_id: int, filename: str, original_filename: str, 
                          content_type: str, file_size: int, storage_path: str,
                          title: str = None, description: str = None, is_public: bool = False) -> Photo:
        """Create a new photo record."""
        photo = Photo(
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path,
            title=title,
            description=description,
            is_public=is_public
        )
        self.session.add(photo)
        await self.session.commit()
        await self.session.refresh(photo)
        return photo
    
    async def get_photo_by_id(self, photo_id: int) -> Optional[Photo]:
        """Get photo by ID."""
        from sqlalchemy import select
        result = await self.session.execute(select(Photo).where(Photo.id == photo_id))
        return result.scalar_one_or_none()
    
    async def get_photos_by_user(self, user_id: int, skip: int = 0, limit: int = 20):
        """Get photos for a user."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(Photo).where(Photo.user_id == user_id).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_public_photos(self, skip: int = 0, limit: int = 20):
        """Get public photos."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(Photo).where(Photo.is_public == True).offset(skip).limit(limit)
        )
        return result.scalars().all()

class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_session(self, user_id: int, token: str) -> Session:
        """Create a new session."""
        session_obj = Session(user_id=user_id, token=token)
        self.session.add(session_obj)
        await self.session.commit()
        await self.session.refresh(session_obj)
        return session_obj
    
    async def get_session_by_token(self, token: str) -> Optional[Session]:
        """Get session by token."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(Session).where(Session.token == token, Session.is_active == True)
        )
        return result.scalar_one_or_none()
    
    async def invalidate_session(self, token: str):
        """Invalidate a session."""
        from sqlalchemy import update
        await self.session.execute(
            update(Session).where(Session.token == token).values(is_active=False)
        )
        await self.session.commit()

class EmailVerificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_verification(self, email: str, secret: str, expires_at: datetime) -> EmailVerification:
        """Create email verification record."""
        verification = EmailVerification(
            email=email,
            secret=secret,
            expires_at=expires_at
        )
        self.session.add(verification)
        await self.session.commit()
        await self.session.refresh(verification)
        return verification
    
    async def get_verification_by_secret(self, secret: str) -> Optional[EmailVerification]:
        """Get verification record by secret."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(EmailVerification).where(EmailVerification.secret == secret)
        )
        return result.scalar_one_or_none()
    
    async def delete_verification(self, secret: str):
        """Delete verification record."""
        from sqlalchemy import delete
        await self.session.execute(
            delete(EmailVerification).where(EmailVerification.secret == secret)
        )
        await self.session.commit()
    
    async def cleanup_expired_verifications(self):
        """Remove expired verification records."""
        from sqlalchemy import delete
        now = datetime.now(timezone.utc)
        await self.session.execute(
            delete(EmailVerification).where(EmailVerification.expires_at < now)
        )
        await self.session.commit()