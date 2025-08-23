#!/usr/bin/env python3
"""
Test configuration and fixtures for the separated architecture.
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch

# Set test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["AUTH_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["APP_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["TWOFA_ENCRYPTION_KEY"] = "4SimbvVNZ3lFGeJLcn1y0pBOCXgVrwmaMGHY1VvyxMs="
os.environ["SMS_PROVIDER_API_KEY"] = "test_sms_key"
os.environ["SMS_FROM_NUMBER"] = "+1234567890"
os.environ["WEBAUTHN_RP_ID"] = "localhost"
os.environ["WEBAUTHN_RP_NAME"] = "PhotoShare Test"
os.environ["GOOGLE_CLIENT_ID"] = "test_google_id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test_google_secret"
os.environ["STORAGE_PATH"] = "/tmp/test_storage"
os.environ["MAX_FILE_SIZE"] = "10485760"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_auth_db_manager():
    """Mock authentication database manager."""
    manager = Mock()
    manager.initialize = AsyncMock(return_value=True)
    manager.health_check = AsyncMock(return_value=True)
    manager.close = AsyncMock()
    
    async def mock_get_session():
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        yield session
    
    manager.get_session = mock_get_session
    return manager

@pytest.fixture
def mock_app_db_manager():
    """Mock application database manager."""
    manager = Mock()
    manager.initialize = AsyncMock(return_value=True)
    manager.health_check = AsyncMock(return_value=True)
    manager.close = AsyncMock()
    
    async def mock_get_session():
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        yield session
    
    manager.get_session = mock_get_session
    return manager

@pytest.fixture
def mock_auth_client():
    """Mock authentication service client."""
    client = Mock()
    client.verify_jwt_token = AsyncMock(return_value={"sub": "test-user-uuid", "user_id": 1})
    client.get_user_info = AsyncMock(return_value={
        "uuid": "test-user-uuid",
        "id": 1,
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "is_verified": True,
        "is_active": True
    })
    client.get_user_permissions = AsyncMock(return_value=["photos:read", "photos:write"])
    client.health_check = AsyncMock(return_value={"status": "healthy"})
    return client

@pytest.fixture
def mock_sso_manager():
    """Mock SSO provider manager."""
    manager = Mock()
    manager.initialize = AsyncMock()
    manager.get_provider_list = AsyncMock(return_value=[
        {"name": "google", "display_name": "Google", "provider": "google"}
    ])
    manager.get_authorization_url = AsyncMock(return_value="https://example.com/auth")
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    return manager

@pytest.fixture
def mock_twofa_manager():
    """Mock two-factor authentication manager."""
    manager = Mock()
    manager.setup_totp = AsyncMock(return_value={
        "device_id": "test-device",
        "secret": "test-secret",
        "qr_code": "data:image/png;base64,test",
        "backup_codes": ["12345678"]
    })
    manager.verify_totp = AsyncMock(return_value=True)
    manager.is_2fa_enabled_for_user = AsyncMock(return_value=False)
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    return manager

@pytest.fixture
def mock_file_storage():
    """Mock file storage service."""
    storage = Mock()
    storage.store_file = Mock(return_value={
        "storage_path": "/tmp/test_file.jpg",
        "file_size": 1024,
        "content_type": "image/jpeg"
    })
    storage.retrieve_file = Mock(return_value=b"fake_file_data")
    storage.delete_file = Mock(return_value=True)
    storage.health_check = Mock(return_value={"local_storage": True})
    return storage

@pytest.fixture
def sample_image_data():
    """Sample image file data for testing."""
    # Minimal valid JPEG
    header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
    padding = b'\x00' * (100 - len(header) - 2)
    footer = b'\xff\xd9'
    return header + padding + footer

@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "uuid": "test-user-uuid",
        "id": 1,
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "is_verified": True,
        "is_active": True
    }

@pytest.fixture
def test_photo_data():
    """Test photo data."""
    return {
        "id": 1,
        "user_uuid": "test-user-uuid",
        "filename": "test_photo.jpg",
        "original_filename": "my_photo.jpg",
        "content_type": "image/jpeg",
        "file_size": 1024,
        "title": "Test Photo",
        "description": "A test photo",
        "is_public": True
    }