#!/usr/bin/env python3
"""
Unit tests for authentication database models and operations.
"""
import sys
from pathlib import Path
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

# services/auth-service is a standalone deployable unit (its own Dockerfile,
# flat internal imports like `from auth_database import ...`) rather than a
# `services.auth_service` Python package -- it isn't even a legal package
# name (hyphen). Import it the same way the container does: put the service
# directory on sys.path and import the flat module name.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "services" / "auth-service"))

class MockAsyncContextManager:
    """Helper class for mocking async context managers."""
    def __init__(self, return_value):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

# Mock the database module before importing
with patch.dict('os.environ', {'AUTH_DATABASE_URL': 'sqlite+aiosqlite:///:memory:'}):
    from auth_database import (
        User, Session, SSOAccount, Role, Permission, UserRole,
        RolePermission, TwoFactorDevice, BackupCode, EmailVerification,
        AuditLog, AuthDatabaseManager
    )

class TestUserModel:
    """Test User model."""
    
    def test_user_creation(self):
        """Test user creation with valid data."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            first_name="Test",
            last_name="User",
            is_verified=True,
            is_active=True
        )
        
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.is_verified is True
        assert user.is_active is True
    
    def test_user_to_dict(self):
        """Test user serialization to dictionary."""
        user = User(
            id=1,
            email="test@example.com",
            first_name="Test",
            is_verified=True,
            is_active=True
        )
        
        user_dict = user.to_dict()
        
        assert user_dict["id"] == 1
        assert user_dict["email"] == "test@example.com"
        assert user_dict["first_name"] == "Test"
        assert user_dict["is_verified"] is True
        assert user_dict["is_active"] is True
        assert "password_hash" not in user_dict  # Should not be serialized

class TestRoleModel:
    """Test Role model."""
    
    def test_role_creation(self):
        """Test role creation with valid data."""
        role = Role(
            name="admin",
            description="Administrator role",
            level=2,
            is_active=True,
            is_system_role=True
        )
        
        assert role.name == "admin"
        assert role.description == "Administrator role"
        assert role.level == 2
        assert role.is_active is True
        assert role.is_system_role is True
    
    def test_role_to_dict(self):
        """Test role serialization to dictionary."""
        role = Role(
            id=1,
            name="user",
            description="Standard user role",
            level=0,
            is_active=True
        )
        
        role_dict = role.to_dict()
        
        assert role_dict["id"] == 1
        assert role_dict["name"] == "user"
        assert role_dict["description"] == "Standard user role"
        assert role_dict["level"] == 0
        assert role_dict["is_active"] is True

class TestPermissionModel:
    """Test Permission model."""
    
    def test_permission_creation(self):
        """Test permission creation with valid data."""
        permission = Permission(
            name="photos:read",
            resource="photos",
            action="read",
            description="Read photo metadata",
            category="content",
            is_sensitive=False
        )
        
        assert permission.name == "photos:read"
        assert permission.resource == "photos"
        assert permission.action == "read"
        assert permission.description == "Read photo metadata"
        assert permission.category == "content"
        assert permission.is_sensitive is False

class TestSSOAccountModel:
    """Test SSO Account model."""
    
    def test_sso_account_creation(self):
        """Test SSO account creation with valid data."""
        sso_account = SSOAccount(
            user_id=1,
            provider="google",
            external_id="google123",
            email="test@example.com",
            is_active=True,
            is_email_verified=True
        )
        
        assert sso_account.user_id == 1
        assert sso_account.provider == "google"
        assert sso_account.external_id == "google123"
        assert sso_account.email == "test@example.com"
        assert sso_account.is_active is True
        assert sso_account.is_email_verified is True

class TestTwoFactorDeviceModel:
    """Test Two-Factor Device model."""
    
    def test_2fa_device_creation(self):
        """Test 2FA device creation with valid data."""
        device = TwoFactorDevice(
            user_id=1,
            device_id="device123",
            method="totp",
            name="Mobile App",
            encrypted_secret="encrypted_secret_data",
            is_active=True,
            is_verified=True
        )
        
        assert device.user_id == 1
        assert device.device_id == "device123"
        assert device.method == "totp"
        assert device.name == "Mobile App"
        assert device.encrypted_secret == "encrypted_secret_data"
        assert device.is_active is True
        assert device.is_verified is True

class TestSessionModel:
    """Test Session model."""
    
    def test_session_creation(self):
        """Test session creation with valid data."""
        expires_at = datetime.now(timezone.utc)
        
        session = Session(
            user_id=1,
            session_token="session123",
            jwt_token="jwt_token_here",
            ip_address="192.168.1.1",
            expires_at=expires_at,
            is_active=True
        )
        
        assert session.user_id == 1
        assert session.session_token == "session123"
        assert session.jwt_token == "jwt_token_here"
        assert session.ip_address == "192.168.1.1"
        assert session.expires_at == expires_at
        assert session.is_active is True

class TestAuthDatabaseManager:
    """Test Authentication Database Manager."""
    
    @pytest.fixture
    def db_manager(self):
        """Create database manager instance."""
        return AuthDatabaseManager()
    
    @pytest.mark.asyncio
    async def test_initialize(self, db_manager):
        """Test database manager initialization."""
        with patch('auth_database.create_async_engine') as mock_engine:
            with patch('auth_database.async_sessionmaker') as mock_sessionmaker:
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
        # health_check() calls the *sync* Result.scalar() on the awaited execute()
        # result -- AsyncMock() auto-creates async children, so scalar() must be
        # pinned to a plain Mock or it returns an unawaited coroutine (falsy).
        mock_result = Mock()
        mock_result.scalar = Mock(return_value=1)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Create a proper async context manager mock
        def mock_session_factory():
            return MockAsyncContextManager(mock_session)

        db_manager.engine = Mock()  # health_check() short-circuits to unhealthy if engine is unset
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