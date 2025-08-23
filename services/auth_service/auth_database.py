#!/usr/bin/env python3
"""
Authentication Service Database Schema
======================================

Dedicated database for authentication, authorization, SSO, and 2FA.
Completely separated from application data.
"""

import os
from datetime import datetime, timezone
from typing import AsyncGenerator
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSON, UUID
import uuid
import logging

logger = logging.getLogger(__name__)

# Database configuration for AUTH database only
def get_auth_database_url():
    """Get authentication database URL - separate from application database."""
    db_host = os.getenv("AUTH_DB_HOST", "auth-db")
    db_port = os.getenv("AUTH_DB_PORT", "5432") 
    db_user = os.getenv("AUTH_POSTGRES_USER", "auth_user")
    db_password = os.getenv("AUTH_POSTGRES_PASSWORD", "auth_secure_password")
    db_name = os.getenv("AUTH_POSTGRES_DB", "photo_share_auth")
    
    return os.getenv(
        "AUTH_DATABASE_URL",
        f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

AUTH_DATABASE_URL = get_auth_database_url()

# SQLAlchemy setup for auth database
AuthBase = declarative_base()

class User(AuthBase):
    """User authentication and profile information."""
    __tablename__ = "auth_users"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for SSO-only users
    
    # Profile information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Account status
    is_verified = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    is_locked = Column(Boolean, default=False, index=True)
    failed_login_attempts = Column(Integer, default=0)
    last_login_attempt = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    sso_accounts = relationship("SSOAccount", back_populates="user", cascade="all, delete-orphan")
    twofa_devices = relationship("TwoFactorDevice", back_populates="user", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", foreign_keys="UserRole.user_id")
    
    def to_dict(self):
        return {
            "id": self.id,
            "uuid": str(self.uuid),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

class Session(AuthBase):
    """User authentication sessions."""
    __tablename__ = "auth_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    jwt_token = Column(Text, nullable=True)  # Store full JWT if needed
    
    # Session binding for security
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent_hash = Column(String(64), nullable=True)
    
    # Session lifecycle
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True, index=True)
    
    # Logout tracking
    logout_at = Column(DateTime(timezone=True), nullable=True)
    logout_reason = Column(String(50), nullable=True)  # manual, timeout, admin, security
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "is_active": self.is_active,
            "logout_at": self.logout_at.isoformat() if self.logout_at else None,
            "logout_reason": self.logout_reason
        }

class SSOAccount(AuthBase):
    """SSO provider account linkage."""
    __tablename__ = "sso_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    provider = Column(String(50), nullable=False, index=True)  # google, microsoft, okta, etc.
    external_id = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    
    # Profile data from SSO provider
    profile_data = Column(JSON, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sso_accounts")
    
    __table_args__ = (UniqueConstraint('provider', 'external_id', name='_provider_external_id_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "external_id": self.external_id,
            "email": self.email,
            "is_active": self.is_active,
            "is_email_verified": self.is_email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

class TwoFactorDevice(AuthBase):
    """Two-factor authentication devices."""
    __tablename__ = "twofa_devices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    device_id = Column(String(32), unique=True, nullable=False, index=True)
    method = Column(String(20), nullable=False)  # totp, sms, webauthn, backup_codes
    name = Column(String(100), nullable=False)  # User-friendly name
    
    # Encrypted device-specific data
    encrypted_secret = Column(Text, nullable=True)  # TOTP secret, phone number, etc.
    device_data = Column(JSON, nullable=True)  # WebAuthn credential data, etc.
    
    # Device status
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    
    # Usage tracking
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    verified_at = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="twofa_devices")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "method": self.method,
            "name": self.name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None
        }

class BackupCode(AuthBase):
    """Two-factor authentication backup codes."""
    __tablename__ = "twofa_backup_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    code_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 hash
    
    # Usage tracking
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_used = Column(Boolean, default=False, index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "is_used": self.is_used
        }

# RBAC Tables

class Role(AuthBase):
    """User roles for RBAC."""
    __tablename__ = "auth_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    
    # Role hierarchy
    parent_role_id = Column(Integer, ForeignKey("auth_roles.id"), nullable=True)
    level = Column(Integer, default=0)  # 0=basic, 1=elevated, 2=admin
    
    # Role status
    is_active = Column(Boolean, default=True, index=True)
    is_system_role = Column(Boolean, default=False)  # Cannot be deleted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_role_id": self.parent_role_id,
            "level": self.level,
            "is_active": self.is_active,
            "is_system_role": self.is_system_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Permission(AuthBase):
    """System permissions."""
    __tablename__ = "auth_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False, index=True)  # photos, users, admin
    action = Column(String(50), nullable=False, index=True)    # read, write, delete, manage
    description = Column(String(255), nullable=True)
    
    # Permission categorization
    category = Column(String(50), nullable=True)  # user_management, content, admin
    is_sensitive = Column(Boolean, default=False)  # Requires additional verification
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint('resource', 'action', name='_resource_action_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "resource": self.resource,
            "action": self.action,
            "description": self.description,
            "category": self.category,
            "is_sensitive": self.is_sensitive,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class RolePermission(AuthBase):
    """Role-Permission mapping."""
    __tablename__ = "auth_role_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("auth_permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Assignment tracking
    granted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    granted_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True)
    
    # Conditional permissions
    conditions = Column(JSON, nullable=True)  # Resource-specific conditions
    
    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    
    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='_role_permission_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "role_id": self.role_id,
            "permission_id": self.permission_id,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "granted_by_user_id": self.granted_by_user_id,
            "conditions": self.conditions
        }

class UserRole(AuthBase):
    """User-Role assignment."""
    __tablename__ = "auth_user_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("auth_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Assignment lifecycle
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    assigned_by_user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by_user_id])
    
    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='_user_role_uc'),)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by_user_id": self.assigned_by_user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active
        }

class EmailVerification(AuthBase):
    """Email verification tokens."""
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    secret = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Token lifecycle
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_used = Column(Boolean, default=False, index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "is_used": self.is_used
        }

class AuditLog(AuthBase):
    """Security audit trail."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=True, index=True)
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # login, logout, 2fa_setup, role_change
    event_category = Column(String(30), nullable=False, index=True)  # authentication, authorization, security
    resource = Column(String(50), nullable=True)
    action = Column(String(50), nullable=True)
    
    # Event data
    event_data = Column(JSON, nullable=True)
    result = Column(String(20), nullable=False)  # success, failure, blocked
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "event_category": self.event_category,
            "resource": self.resource,
            "action": self.action,
            "event_data": self.event_data,
            "result": self.result,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

# Database connection and session management
class AuthDatabaseManager:
    """Manages authentication database connections and sessions."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        
    async def initialize(self):
        """Initialize database connection."""
        try:
            self.engine = create_async_engine(
                AUTH_DATABASE_URL,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Auth database manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize auth database: {e}")
            return False
            
    async def create_tables(self):
        """Create all auth database tables."""
        if not self.engine:
            await self.initialize()
            
        async with self.engine.begin() as conn:
            await conn.run_sync(AuthBase.metadata.create_all)
            
        logger.info("Auth database tables created successfully")
        
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
            async with self.session_factory() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Auth database health check failed: {e}")
            return False
            
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Auth database connections closed")

# Global auth database manager
auth_db_manager = AuthDatabaseManager()