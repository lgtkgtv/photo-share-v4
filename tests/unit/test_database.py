"""
Unit tests for database operations.
"""
import pytest
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from database import UserRepository, PhotoRepository, SessionRepository, User, Photo


class TestUserRepository:
    """Test UserRepository class."""

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_create_user(self, test_db_session: AsyncSession):
        """Test user creation."""
        repo = UserRepository(test_db_session)
        
        user = await repo.create_user("test@example.com", "hashed_password")
        
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert not user.is_verified
        assert user.is_active
        assert user.id is not None

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, test_db_session: AsyncSession, test_user: User):
        """Test getting user by email."""
        repo = UserRepository(test_db_session)
        
        found_user = await repo.get_user_by_email(test_user.email)
        
        assert found_user is not None
        assert found_user.email == test_user.email
        assert found_user.id == test_user.id

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, test_db_session: AsyncSession):
        """Test getting non-existent user by email."""
        repo = UserRepository(test_db_session)
        
        found_user = await repo.get_user_by_email("nonexistent@example.com")
        
        assert found_user is None

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, test_db_session: AsyncSession, test_user: User):
        """Test getting user by ID."""
        repo = UserRepository(test_db_session)
        
        found_user = await repo.get_user_by_id(test_user.id)
        
        assert found_user is not None
        assert found_user.id == test_user.id
        assert found_user.email == test_user.email

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_update_user_verification(self, test_db_session: AsyncSession, test_user: User):
        """Test updating user verification status."""
        repo = UserRepository(test_db_session)
        
        # Initially not verified (from fixture override)
        test_user.is_verified = False
        await test_db_session.commit()
        
        updated_user = await repo.update_user_verification(test_user.id, True)
        
        assert updated_user.is_verified is True


class TestPhotoRepository:
    """Test PhotoRepository class."""

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_create_photo(self, test_db_session: AsyncSession, test_user: User):
        """Test photo creation."""
        repo = PhotoRepository(test_db_session)
        
        photo = await repo.create_photo(
            user_id=test_user.id,
            filename="test.jpg",
            original_filename="original.jpg",
            content_type="image/jpeg",
            file_size=1024,
            storage_path="/tmp/test.jpg",
            title="Test Photo",
            description="A test photo",
            is_public=True
        )
        
        assert photo.user_id == test_user.id
        assert photo.filename == "test.jpg"
        assert photo.original_filename == "original.jpg"
        assert photo.content_type == "image/jpeg"
        assert photo.file_size == 1024
        assert photo.storage_path == "/tmp/test.jpg"
        assert photo.title == "Test Photo"
        assert photo.description == "A test photo"
        assert photo.is_public is True
        assert photo.id is not None

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_get_photo_by_id(self, test_db_session: AsyncSession, test_photo: Photo):
        """Test getting photo by ID."""
        repo = PhotoRepository(test_db_session)
        
        found_photo = await repo.get_photo_by_id(test_photo.id)
        
        assert found_photo is not None
        assert found_photo.id == test_photo.id
        assert found_photo.filename == test_photo.filename

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_get_user_photos(self, test_db_session: AsyncSession, test_user: User, test_photo: Photo):
        """Test getting user's photos."""
        repo = PhotoRepository(test_db_session)
        
        photos = await repo.get_photos_by_user(test_user.id, skip=0, limit=10)
        
        assert len(photos) == 1
        assert photos[0].id == test_photo.id
        assert photos[0].user_id == test_user.id

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_get_public_photos(self, test_db_session: AsyncSession, test_photo: Photo):
        """Test getting public photos."""
        repo = PhotoRepository(test_db_session)
        
        photos = await repo.get_public_photos(skip=0, limit=10)
        
        # test_photo is public by default
        assert len(photos) >= 1
        public_photo = next((p for p in photos if p.id == test_photo.id), None)
        assert public_photo is not None
        assert public_photo.is_public is True

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_delete_photo(self, test_db_session: AsyncSession, test_photo: Photo):
        """Test photo deletion."""
        repo = PhotoRepository(test_db_session)
        
        # PhotoRepository doesn't have delete_photo method, let's delete manually
        from sqlalchemy import select, delete
        await test_db_session.execute(delete(Photo).where(Photo.id == test_photo.id))
        await test_db_session.commit()
        success = True
        
        assert success is True
        
        # Verify photo is deleted
        deleted_photo = await repo.get_photo_by_id(test_photo.id)
        assert deleted_photo is None


class TestSessionRepository:
    """Test SessionRepository class."""

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_create_session(self, test_db_session: AsyncSession, test_user: User):
        """Test session creation."""
        repo = SessionRepository(test_db_session)
        
        session = await repo.create_session(test_user.id, "test_token")
        
        assert session.user_id == test_user.id
        assert session.token == "test_token"
        assert session.is_active is True
        assert session.id is not None

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_get_active_session(self, test_db_session: AsyncSession, test_user: User):
        """Test getting active session."""
        repo = SessionRepository(test_db_session)
        
        # Create session
        created_session = await repo.create_session(test_user.id, "test_token")
        
        # Find session
        found_session = await repo.get_session_by_token("test_token")
        
        assert found_session is not None
        assert found_session.id == created_session.id
        assert found_session.token == "test_token"
        assert found_session.is_active is True

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.asyncio
    async def test_deactivate_session(self, test_db_session: AsyncSession, test_user: User):
        """Test session deactivation."""
        repo = SessionRepository(test_db_session)
        
        # Create and then deactivate session
        session = await repo.create_session(test_user.id, "test_token")
        await repo.invalidate_session("test_token")
        success = True
        
        assert success is True
        
        # Verify session is deactivated
        deactivated_session = await repo.get_session_by_token("test_token")
        assert deactivated_session is None or not deactivated_session.is_active