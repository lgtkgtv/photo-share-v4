"""
Test configuration and fixtures for the photo sharing service.
"""
import asyncio
import os
import tempfile
from typing import AsyncGenerator, Dict, Any
from unittest.mock import Mock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment - use SQLite for testing
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
# Use SQLite for all database operations in tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Mock the global db_manager before any imports
from unittest.mock import Mock, AsyncMock, patch
import sys

# Create a mock db_manager with proper async generator
mock_db_manager = Mock()
mock_db_manager.initialize = AsyncMock(return_value=True)
mock_db_manager.health_check = AsyncMock(return_value=True)
mock_db_manager.close = AsyncMock()
mock_db_manager.engine = Mock()
mock_db_manager.session_factory = Mock()

# Import database module first
import database

# Create a proper async generator for get_session that yields None
async def mock_get_session():
    yield Mock()  # Return a mock session

mock_db_manager.get_session = mock_get_session

# Patch db_manager immediately
database.db_manager = mock_db_manager

# Import after setting environment and mocking
from main import PhotoShareDatabaseService
from database import Base, User, Photo, Session as DBSession, get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create test database engine with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_file_storage():
    """Mock file storage service."""
    mock_storage = Mock()
    mock_storage.store_file.return_value = {
        "storage_path": "/tmp/test_photo.jpg",
        "file_size": 1024,
        "content_type": "image/jpeg"
    }
    mock_storage.retrieve_file.return_value = b"fake_image_data"
    mock_storage.delete_file.return_value = True
    mock_storage.health_check.return_value = {
        "local_storage": True,
        "platform_storage": True
    }
    mock_storage.get_file_url.return_value = "http://localhost/files/test_photo.jpg"
    return mock_storage


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "is_verified": True,
        "is_active": True
    }


@pytest.fixture
def test_photo_data():
    """Test photo data."""
    return {
        "filename": "test_photo.jpg",
        "original_filename": "my_photo.jpg",
        "content_type": "image/jpeg",
        "file_size": 1024,
        "storage_path": "/tmp/test_photo.jpg",
        "title": "Test Photo",
        "description": "A test photo",
        "is_public": True
    }


@pytest_asyncio.fixture
async def test_user(test_db_session: AsyncSession, test_user_data: Dict[str, Any]) -> User:
    """Create test user in database."""
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(test_user_data["password"])
    
    user = User(
        email=test_user_data["email"],
        password_hash=hashed_password,
        is_verified=test_user_data["is_verified"],
        is_active=test_user_data["is_active"]
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def test_photo(test_db_session: AsyncSession, test_user: User, test_photo_data: Dict[str, Any]) -> Photo:
    """Create test photo in database."""
    photo = Photo(
        user_id=test_user.id,
        **test_photo_data
    )
    
    test_db_session.add(photo)
    await test_db_session.commit()
    await test_db_session.refresh(photo)
    
    return photo


@pytest.fixture
def app_with_test_db(test_db_session: AsyncSession, mock_file_storage):
    """Create FastAPI app with test database."""
    service = PhotoShareDatabaseService()
    
    # Simple dependency override - this is the FastAPI standard approach
    async def override_get_db():
        yield test_db_session
    
    service.app.dependency_overrides[get_db] = override_get_db
    service.file_storage = mock_file_storage
    
    return service.app


@pytest.fixture
def test_client(app_with_test_db):
    """Create test client."""
    return TestClient(app_with_test_db)


@pytest_asyncio.fixture
async def async_test_client(app_with_test_db):
    """Create async test client."""
    async with AsyncClient(
        app=app_with_test_db, 
        base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture
def auth_headers(test_user: User):
    """Create authentication headers for test user."""
    from jose import jwt
    from datetime import datetime, timedelta
    
    token_data = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    
    token = jwt.encode(token_data, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_image_data():
    """Sample image file data for testing."""
    # Minimal valid JPEG with enough padding to meet the 100 byte minimum
    header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
    # Add padding to reach minimum size requirement (100 bytes)
    padding = b'\x00' * (100 - len(header) - 2)  # -2 for the end marker
    footer = b'\xff\xd9'
    return header + padding + footer


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield f.name
    
    # Cleanup
    try:
        os.unlink(f.name)
    except FileNotFoundError:
        pass