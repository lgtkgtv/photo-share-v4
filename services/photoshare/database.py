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
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, LargeBinary, ForeignKey, UniqueConstraint
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

# Role-Based Access Control Models
class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False, index=True)  # e.g., 'photos', 'users', 'admin'
    action = Column(String(50), nullable=False, index=True)    # e.g., 'read', 'write', 'delete'
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (UniqueConstraint('resource', 'action', name='_resource_action_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "resource": self.resource,
            "action": self.action,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class RolePermission(Base):
    __tablename__ = "role_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who granted this permission
    
    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='_role_permission_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "role_id": self.role_id,
            "permission_id": self.permission_id,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "granted_by": self.granted_by
        }

class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who assigned this role
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Optional expiration
    is_active = Column(Boolean, default=True, index=True)
    
    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='_user_role_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by": self.assigned_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active
        }

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_verified = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
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
            # Production-optimized connection pool settings
            environment = os.getenv("ENVIRONMENT", "development")
            
            if environment == "production":
                # Production settings: more connections, better performance
                pool_settings = {
                    "pool_size": 50,        # Base number of connections
                    "max_overflow": 100,    # Additional connections when busy
                    "pool_timeout": 30,     # Wait time for connection
                    "pool_recycle": 3600,   # Recycle connections every hour
                    "pool_pre_ping": True,  # Validate connections
                    "echo": False,          # Disable SQL logging in production
                }
            elif environment == "test":
                # Test settings: minimal connections, fast cleanup
                pool_settings = {
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_timeout": 10,
                    "pool_recycle": 300,
                    "pool_pre_ping": True,
                    "echo": False,
                }
            else:
                # Development settings: moderate connections, debugging enabled
                pool_settings = {
                    "pool_size": 20,
                    "max_overflow": 30,
                    "pool_timeout": 20,
                    "pool_recycle": 300,
                    "pool_pre_ping": True,
                    "echo": os.getenv("SQL_DEBUG", "false").lower() == "true",
                }
            
            self.engine = create_async_engine(
                self.database_url,
                **pool_settings
            )
            
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create all tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
            # Log pool configuration
            logger.info(f"Database pool initialized - Environment: {environment}")
            logger.info(f"Pool size: {pool_settings['pool_size']}, Max overflow: {pool_settings['max_overflow']}")
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
    
    async def get_pool_status(self) -> dict:
        """Get database connection pool status."""
        if not self.engine:
            return {"error": "Database not initialized"}
        
        pool = self.engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in_connections": pool.checkedin(),
            "checked_out_connections": pool.checkedout(),
            "overflow_connections": pool.overflow(),
            "invalid_connections": pool.invalid(),
            "total_connections": pool.size() + pool.overflow(),
            "pool_recreate_count": getattr(pool, '_total_connects', 0),
        }
    
    async def health_check(self) -> dict:
        """Comprehensive database health check."""
        try:
            if not self.engine:
                return {"healthy": False, "error": "Database not initialized"}
            
            # Test basic connection
            async with self.get_session() as session:
                result = await session.execute("SELECT 1 as test")
                test_value = result.scalar()
            
            if test_value != 1:
                return {"healthy": False, "error": "Connection test failed"}
            
            # Get pool statistics
            pool_status = await self.get_pool_status()
            
            return {
                "healthy": True,
                "database_url": self.database_url.split('@')[-1] if '@' in self.database_url else "hidden",
                "pool_status": pool_status,
                "environment": os.getenv("ENVIRONMENT", "development")
            }
            
        except Exception as e:
            return {"healthy": False, "error": str(e)}

# Import enhanced models to ensure they're registered with Base
from models_enhanced import (
    PhotoMetadata, PhotoTag, PhotoLike, PhotoComment, UserFollow, 
    UserProfile, Album, AlbumPhoto, Notification, PhotoShare
)

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

class RoleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_role(self, name: str, description: str = None) -> Role:
        """Create a new role."""
        role = Role(name=name, description=description)
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        from sqlalchemy import select
        result = await self.session.execute(select(Role).where(Role.name == name, Role.is_active == True))
        return result.scalar_one_or_none()
    
    async def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """Get role by ID."""
        from sqlalchemy import select
        result = await self.session.execute(select(Role).where(Role.id == role_id, Role.is_active == True))
        return result.scalar_one_or_none()
    
    async def get_all_roles(self) -> list[Role]:
        """Get all active roles."""
        from sqlalchemy import select
        result = await self.session.execute(select(Role).where(Role.is_active == True))
        return result.scalars().all()

class PermissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_permission(self, name: str, resource: str, action: str, description: str = None) -> Permission:
        """Create a new permission."""
        permission = Permission(name=name, resource=resource, action=action, description=description)
        self.session.add(permission)
        await self.session.commit()
        await self.session.refresh(permission)
        return permission
    
    async def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name."""
        from sqlalchemy import select
        result = await self.session.execute(select(Permission).where(Permission.name == name))
        return result.scalar_one_or_none()
    
    async def get_permission_by_resource_action(self, resource: str, action: str) -> Optional[Permission]:
        """Get permission by resource and action."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(Permission).where(Permission.resource == resource, Permission.action == action)
        )
        return result.scalar_one_or_none()
    
    async def get_all_permissions(self) -> list[Permission]:
        """Get all permissions."""
        from sqlalchemy import select
        result = await self.session.execute(select(Permission))
        return result.scalars().all()

class RolePermissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def grant_permission_to_role(self, role_id: int, permission_id: int, granted_by: int = None) -> RolePermission:
        """Grant a permission to a role."""
        role_permission = RolePermission(
            role_id=role_id, 
            permission_id=permission_id, 
            granted_by=granted_by
        )
        self.session.add(role_permission)
        await self.session.commit()
        await self.session.refresh(role_permission)
        return role_permission
    
    async def revoke_permission_from_role(self, role_id: int, permission_id: int):
        """Revoke a permission from a role."""
        from sqlalchemy import delete
        await self.session.execute(
            delete(RolePermission).where(
                RolePermission.role_id == role_id, 
                RolePermission.permission_id == permission_id
            )
        )
        await self.session.commit()
    
    async def get_role_permissions(self, role_id: int) -> list[Permission]:
        """Get all permissions for a role."""
        from sqlalchemy import select, join
        result = await self.session.execute(
            select(Permission).select_from(
                join(Permission, RolePermission, Permission.id == RolePermission.permission_id)
            ).where(RolePermission.role_id == role_id)
        )
        return result.scalars().all()

class UserRoleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def assign_role_to_user(self, user_id: int, role_id: int, assigned_by: int = None, expires_at: datetime = None) -> UserRole:
        """Assign a role to a user."""
        user_role = UserRole(
            user_id=user_id, 
            role_id=role_id, 
            assigned_by=assigned_by,
            expires_at=expires_at
        )
        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)
        return user_role
    
    async def revoke_role_from_user(self, user_id: int, role_id: int):
        """Revoke a role from a user."""
        from sqlalchemy import update
        await self.session.execute(
            update(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            ).values(is_active=False)
        )
        await self.session.commit()
    
    async def get_user_roles(self, user_id: int) -> list[Role]:
        """Get all active roles for a user."""
        from sqlalchemy import select, join
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Role).select_from(
                join(Role, UserRole, Role.id == UserRole.role_id)
            ).where(
                UserRole.user_id == user_id,
                UserRole.is_active == True,
                (UserRole.expires_at.is_(None) | (UserRole.expires_at > now))
            )
        )
        return result.scalars().all()
    
    async def get_user_permissions(self, user_id: int) -> list[Permission]:
        """Get all permissions for a user through their roles."""
        from sqlalchemy import select, join
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Permission).select_from(
                join(Permission, RolePermission, Permission.id == RolePermission.permission_id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == Role.id)
            ).where(
                UserRole.user_id == user_id,
                UserRole.is_active == True,
                Role.is_active == True,
                (UserRole.expires_at.is_(None) | (UserRole.expires_at > now))
            )
        )
        return result.scalars().all()
    
    async def has_permission(self, user_id: int, resource: str, action: str) -> bool:
        """Check if user has specific permission."""
        from sqlalchemy import select, join
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Permission).select_from(
                join(Permission, RolePermission, Permission.id == RolePermission.permission_id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == Role.id)
            ).where(
                UserRole.user_id == user_id,
                UserRole.is_active == True,
                Role.is_active == True,
                Permission.resource == resource,
                Permission.action == action,
                (UserRole.expires_at.is_(None) | (UserRole.expires_at > now))
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
    
    async def cleanup_expired_roles(self):
        """Remove expired user role assignments."""
        from sqlalchemy import update
        now = datetime.now(timezone.utc)
        await self.session.execute(
            update(UserRole).where(
                UserRole.expires_at < now,
                UserRole.is_active == True
            ).values(is_active=False)
        )
        await self.session.commit()