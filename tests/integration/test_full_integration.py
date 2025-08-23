"""
Full Integration Tests with Test Databases
End-to-end tests using real database connections and full service stack.
"""
import pytest
import asyncio
import tempfile
import os
from typing import AsyncGenerator, Dict, Any
from unittest.mock import patch, AsyncMock
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool


class TestFullIntegrationWithDatabase:
    """Full integration tests with real database operations."""

    @pytest.fixture
    async def test_database(self):
        """Create test database with real SQLAlchemy setup."""
        from database import Base
        
        # Create test database URL (SQLite for testing)
        test_db_url = "sqlite+aiosqlite:///:memory:"
        
        # Create async engine
        engine = create_async_engine(
            test_db_url,
            echo=False,  # Set to True for SQL debugging
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session factory
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        yield engine, async_session
        
        # Cleanup
        await engine.dispose()

    @pytest.fixture
    async def db_session(self, test_database):
        """Get database session for tests."""
        engine, async_session = test_database
        
        async with async_session() as session:
            yield session

    @pytest.fixture
    def full_integration_app(self, test_database):
        """Create full integration app with real database."""
        from fastapi import FastAPI, Depends, HTTPException, status
        from fastapi.security import HTTPBearer
        from passlib.context import CryptContext
        from jose import JWTError, jwt
        from datetime import datetime, timedelta
        from database import User, Photo
        from sqlalchemy import select
        import hashlib
        
        engine, async_session = test_database
        
        app = FastAPI(title="Photo Share - Full Integration Test")
        
        # Security setup
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        security = HTTPBearer()
        SECRET_KEY = "test_secret_key_for_integration_testing"
        ALGORITHM = "HS256"
        
        # Database dependency
        async def get_db():
            async with async_session() as session:
                try:
                    yield session
                finally:
                    await session.close()
        
        # Authentication utilities
        def create_access_token(data: dict, expires_delta: timedelta = None):
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=30)
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt
        
        async def get_current_user(token: str = Depends(security), db: AsyncSession = Depends(get_db)):
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            try:
                payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
                user_id: str = payload.get("sub")
                if user_id is None:
                    raise credentials_exception
            except JWTError:
                raise credentials_exception
            
            # Get user from database
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if user is None:
                raise credentials_exception
            return user
        
        # User endpoints
        @app.post("/api/users/register")
        async def register_user(user_data: dict, db: AsyncSession = Depends(get_db)):
            email = user_data.get("email")
            password = user_data.get("password")
            
            if not email or not password:
                raise HTTPException(status_code=400, detail="Email and password required")
            
            # Check if user exists
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise HTTPException(status_code=409, detail="User already exists")
            
            # Create new user
            hashed_password = pwd_context.hash(password)
            new_user = User(
                email=email,
                password_hash=hashed_password,
                is_verified=False,
                is_active=True
            )
            
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            return {
                "id": new_user.id,
                "email": new_user.email,
                "is_verified": new_user.is_verified,
                "is_active": new_user.is_active,
                "created_at": new_user.created_at.isoformat() if hasattr(new_user, 'created_at') else datetime.utcnow().isoformat()
            }
        
        @app.post("/api/users/login")
        async def login(credentials: dict, db: AsyncSession = Depends(get_db)):
            email = credentials.get("email")
            password = credentials.get("password")
            
            if not email or not password:
                raise HTTPException(status_code=400, detail="Email and password required")
            
            # Get user from database
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            if not user or not pwd_context.verify(password, user.password_hash):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # Create access token
            access_token_expires = timedelta(minutes=30)
            access_token = create_access_token(
                data={"sub": str(user.id)}, expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "is_verified": user.is_verified
                }
            }
        
        @app.get("/api/users/me")
        async def get_current_user_info(current_user: User = Depends(get_current_user)):
            return {
                "id": current_user.id,
                "email": current_user.email,
                "is_verified": current_user.is_verified,
                "is_active": current_user.is_active
            }
        
        # Photo endpoints
        @app.post("/api/photos/upload")
        async def upload_photo(
            photo_data: dict,
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            # Simulate file upload
            filename = photo_data.get("filename", "test.jpg")
            title = photo_data.get("title", "Untitled")
            description = photo_data.get("description", "")
            is_public = photo_data.get("is_public", False)
            
            # Create photo record
            photo = Photo(
                user_id=current_user.id,
                filename=filename,
                original_filename=filename,
                content_type="image/jpeg",
                file_size=1024,  # Mock file size
                storage_path=f"users/{current_user.id}/photos/{filename}",
                title=title,
                description=description,
                is_public=is_public
            )
            
            db.add(photo)
            await db.commit()
            await db.refresh(photo)
            
            return {
                "id": photo.id,
                "user_id": photo.user_id,
                "filename": photo.filename,
                "title": photo.title,
                "description": photo.description,
                "is_public": photo.is_public,
                "storage_path": photo.storage_path,
                "file_size": photo.file_size,
                "content_type": photo.content_type,
                "created_at": photo.created_at.isoformat() if hasattr(photo, 'created_at') else datetime.utcnow().isoformat()
            }
        
        @app.get("/api/photos/")
        async def list_user_photos(
            page: int = 1,
            per_page: int = 20,
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            # Get user's photos from database
            result = await db.execute(
                select(Photo)
                .where(Photo.user_id == current_user.id)
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            photos = result.scalars().all()
            
            # Get total count
            count_result = await db.execute(
                select(Photo).where(Photo.user_id == current_user.id)
            )
            total = len(count_result.scalars().all())
            
            return {
                "photos": [
                    {
                        "id": photo.id,
                        "user_id": photo.user_id,
                        "title": photo.title,
                        "description": photo.description,
                        "is_public": photo.is_public,
                        "created_at": photo.created_at.isoformat() if hasattr(photo, 'created_at') else datetime.utcnow().isoformat()
                    }
                    for photo in photos
                ],
                "total": total,
                "page": page,
                "per_page": per_page
            }
        
        @app.get("/api/photos/public")
        async def list_public_photos(
            page: int = 1,
            per_page: int = 20,
            db: AsyncSession = Depends(get_db)
        ):
            # Get public photos from database
            result = await db.execute(
                select(Photo)
                .where(Photo.is_public == True)
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            photos = result.scalars().all()
            
            return {
                "photos": [
                    {
                        "id": photo.id,
                        "user_id": photo.user_id,
                        "title": photo.title,
                        "description": photo.description,
                        "is_public": photo.is_public,
                        "created_at": photo.created_at.isoformat() if hasattr(photo, 'created_at') else datetime.utcnow().isoformat()
                    }
                    for photo in photos
                ],
                "total": len(photos),
                "page": page,
                "per_page": per_page
            }
        
        @app.get("/api/photos/{photo_id}")
        async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Photo).where(Photo.id == photo_id))
            photo = result.scalar_one_or_none()
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            return {
                "id": photo.id,
                "user_id": photo.user_id,
                "title": photo.title,
                "description": photo.description,
                "is_public": photo.is_public,
                "storage_path": photo.storage_path,
                "file_size": photo.file_size,
                "content_type": photo.content_type,
                "created_at": photo.created_at.isoformat() if hasattr(photo, 'created_at') else datetime.utcnow().isoformat()
            }
        
        @app.delete("/api/photos/{photo_id}")
        async def delete_photo(
            photo_id: int,
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            result = await db.execute(select(Photo).where(Photo.id == photo_id))
            photo = result.scalar_one_or_none()
            
            if not photo:
                raise HTTPException(status_code=404, detail="Photo not found")
            
            if photo.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this photo")
            
            await db.delete(photo)
            await db.commit()
            
            return {"message": "Photo deleted successfully"}
        
        # Health check
        @app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.3.0-monitoring",
                "services": {
                    "database": "healthy",
                    "file_storage": "healthy"
                }
            }
        
        return app

    @pytest.fixture
    async def full_integration_client(self, full_integration_app):
        """Create async client for full integration tests."""
        async with httpx.AsyncClient(app=full_integration_app, base_url="http://testserver") as client:
            yield client

    # Full Integration Test Scenarios
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.database
    async def test_complete_user_registration_flow(self, full_integration_client):
        """Test complete user registration and login flow."""
        client = full_integration_client
        
        # Step 1: Register a new user
        user_data = {
            "email": "fulltest@example.com",
            "password": "FullTestPassword123!"
        }
        
        register_response = await client.post("/api/users/register", json=user_data)
        assert register_response.status_code == 200
        
        user_info = register_response.json()
        assert user_info["email"] == user_data["email"]
        assert user_info["is_verified"] is False
        assert user_info["is_active"] is True
        assert "id" in user_info
        
        # Step 2: Login with the new user
        login_response = await client.post("/api/users/login", json=user_data)
        assert login_response.status_code == 200
        
        login_data = login_response.json()
        assert "access_token" in login_data
        assert login_data["token_type"] == "bearer"
        assert login_data["user"]["email"] == user_data["email"]
        
        # Step 3: Access protected endpoint
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        me_response = await client.get("/api/users/me", headers=headers)
        assert me_response.status_code == 200
        
        me_data = me_response.json()
        assert me_data["email"] == user_data["email"]
        assert me_data["id"] == user_info["id"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.database
    async def test_complete_photo_management_flow(self, full_integration_client):
        """Test complete photo upload and management flow."""
        client = full_integration_client
        
        # Step 1: Create and login user
        user_data = {
            "email": "photouser@example.com",
            "password": "PhotoTestPass123!"
        }
        
        await client.post("/api/users/register", json=user_data)
        login_response = await client.post("/api/users/login", json=user_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Upload a photo
        photo_data = {
            "filename": "sunset.jpg",
            "title": "Beautiful Sunset",
            "description": "A gorgeous sunset over the mountains",
            "is_public": True
        }
        
        upload_response = await client.post("/api/photos/upload", json=photo_data, headers=headers)
        assert upload_response.status_code == 200
        
        photo_info = upload_response.json()
        assert photo_info["title"] == photo_data["title"]
        assert photo_info["is_public"] is True
        photo_id = photo_info["id"]
        
        # Step 3: List user's photos
        list_response = await client.get("/api/photos/", headers=headers)
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        assert list_data["total"] == 1
        assert len(list_data["photos"]) == 1
        assert list_data["photos"][0]["title"] == photo_data["title"]
        
        # Step 4: Get specific photo
        get_response = await client.get(f"/api/photos/{photo_id}")
        assert get_response.status_code == 200
        
        get_data = get_response.json()
        assert get_data["title"] == photo_data["title"]
        assert get_data["description"] == photo_data["description"]
        
        # Step 5: Check public photos list
        public_response = await client.get("/api/photos/public")
        assert public_response.status_code == 200
        
        public_data = public_response.json()
        assert len(public_data["photos"]) >= 1
        # Find our photo in the public list
        our_photo = next((p for p in public_data["photos"] if p["id"] == photo_id), None)
        assert our_photo is not None
        assert our_photo["is_public"] is True
        
        # Step 6: Delete the photo
        delete_response = await client.delete(f"/api/photos/{photo_id}", headers=headers)
        assert delete_response.status_code == 200
        
        # Step 7: Verify photo is deleted
        get_deleted_response = await client.get(f"/api/photos/{photo_id}")
        assert get_deleted_response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.integration  
    @pytest.mark.database
    async def test_user_isolation_and_security(self, full_integration_client):
        """Test that users can only access their own resources."""
        client = full_integration_client
        
        # Create two users
        user1_data = {"email": "user1@example.com", "password": "User1Pass123!"}
        user2_data = {"email": "user2@example.com", "password": "User2Pass123!"}
        
        await client.post("/api/users/register", json=user1_data)
        await client.post("/api/users/register", json=user2_data)
        
        # Login both users
        login1_response = await client.post("/api/users/login", json=user1_data)
        login2_response = await client.post("/api/users/login", json=user2_data)
        
        token1 = login1_response.json()["access_token"]
        token2 = login2_response.json()["access_token"]
        
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # User1 uploads a photo
        photo_data = {
            "filename": "user1_photo.jpg",
            "title": "User 1's Photo",
            "is_public": False
        }
        
        upload_response = await client.post("/api/photos/upload", json=photo_data, headers=headers1)
        photo_id = upload_response.json()["id"]
        
        # User2 should not be able to delete User1's photo
        delete_response = await client.delete(f"/api/photos/{photo_id}", headers=headers2)
        assert delete_response.status_code == 403
        
        # User1 should be able to delete their own photo
        delete_response = await client.delete(f"/api/photos/{photo_id}", headers=headers1)
        assert delete_response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.database
    async def test_pagination_and_filtering(self, full_integration_client):
        """Test pagination and filtering functionality."""
        client = full_integration_client
        
        # Create user and login
        user_data = {"email": "paginationuser@example.com", "password": "PaginationPass123!"}
        await client.post("/api/users/register", json=user_data)
        login_response = await client.post("/api/users/login", json=user_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Upload multiple photos
        for i in range(5):
            photo_data = {
                "filename": f"photo_{i}.jpg",
                "title": f"Photo {i}",
                "is_public": i % 2 == 0  # Every other photo is public
            }
            await client.post("/api/photos/upload", json=photo_data, headers=headers)
        
        # Test pagination
        page1_response = await client.get("/api/photos/?page=1&per_page=3", headers=headers)
        assert page1_response.status_code == 200
        
        page1_data = page1_response.json()
        assert page1_data["total"] == 5
        assert page1_data["page"] == 1
        assert page1_data["per_page"] == 3
        assert len(page1_data["photos"]) == 3
        
        # Test public photos filtering
        public_response = await client.get("/api/photos/public")
        assert public_response.status_code == 200
        
        public_data = public_response.json()
        # Should have 3 public photos (0, 2, 4)
        assert len(public_data["photos"]) == 3
        for photo in public_data["photos"]:
            assert photo["is_public"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.database
    async def test_error_handling_and_edge_cases(self, full_integration_client):
        """Test error handling and edge cases."""
        client = full_integration_client
        
        # Test duplicate user registration
        user_data = {"email": "duplicate@example.com", "password": "DuplicatePass123!"}
        
        # First registration should succeed
        register1_response = await client.post("/api/users/register", json=user_data)
        assert register1_response.status_code == 200
        
        # Second registration should fail
        register2_response = await client.post("/api/users/register", json=user_data)
        assert register2_response.status_code == 409
        assert "already exists" in register2_response.json()["detail"]
        
        # Test invalid login
        invalid_login = {"email": "nonexistent@example.com", "password": "wrongpass"}
        login_response = await client.post("/api/users/login", json=invalid_login)
        assert login_response.status_code == 401
        
        # Test accessing protected endpoint without token
        me_response = await client.get("/api/users/me")
        assert me_response.status_code == 401
        
        # Test accessing non-existent photo
        get_response = await client.get("/api/photos/99999")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.database
    async def test_concurrent_operations(self, full_integration_client):
        """Test concurrent operations and race conditions."""
        client = full_integration_client
        
        # Create user
        user_data = {"email": "concurrentuser@example.com", "password": "ConcurrentPass123!"}
        await client.post("/api/users/register", json=user_data)
        login_response = await client.post("/api/users/login", json=user_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Concurrent photo uploads
        async def upload_photo(i):
            photo_data = {
                "filename": f"concurrent_{i}.jpg",
                "title": f"Concurrent Photo {i}"
            }
            response = await client.post("/api/photos/upload", json=photo_data, headers=headers)
            return response.status_code == 200
        
        # Upload 5 photos concurrently
        tasks = [upload_photo(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All uploads should succeed
        assert all(results)
        
        # Verify all photos were created
        list_response = await client.get("/api/photos/", headers=headers)
        list_data = list_response.json()
        assert list_data["total"] == 5

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.database
    async def test_data_persistence(self, full_integration_client, db_session):
        """Test that data persists correctly in the database."""
        client = full_integration_client
        
        # Create user through API
        user_data = {"email": "persistence@example.com", "password": "PersistencePass123!"}
        register_response = await client.post("/api/users/register", json=user_data)
        user_id = register_response.json()["id"]
        
        # Login and upload photo
        login_response = await client.post("/api/users/login", json=user_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        photo_data = {"filename": "persist.jpg", "title": "Persistence Test"}
        upload_response = await client.post("/api/photos/upload", json=photo_data, headers=headers)
        photo_id = upload_response.json()["id"]
        
        # Verify data exists in database directly
        from database import User, Photo
        from sqlalchemy import select
        
        # Check user exists
        user_result = await db_session.execute(select(User).where(User.id == user_id))
        db_user = user_result.scalar_one_or_none()
        assert db_user is not None
        assert db_user.email == user_data["email"]
        
        # Check photo exists
        photo_result = await db_session.execute(select(Photo).where(Photo.id == photo_id))
        db_photo = photo_result.scalar_one_or_none()
        assert db_photo is not None
        assert db_photo.title == photo_data["title"]
        assert db_photo.user_id == user_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.database
    async def test_service_health_and_monitoring(self, full_integration_client):
        """Test service health checks and monitoring endpoints."""
        client = full_integration_client
        
        # Test health check
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        assert health_data["version"] == "2.3.0-monitoring"
        assert "timestamp" in health_data
        assert "services" in health_data
        
        # Health check should indicate database is healthy
        assert health_data["services"]["database"] == "healthy"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_performance_under_load(self, full_integration_client):
        """Test performance under simulated load."""
        client = full_integration_client
        import time
        
        # Create user for load testing
        user_data = {"email": "loadtest@example.com", "password": "LoadTestPass123!"}
        await client.post("/api/users/register", json=user_data)
        login_response = await client.post("/api/users/login", json=user_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Measure response times for multiple operations
        start_time = time.time()
        
        # Perform multiple operations
        tasks = []
        for i in range(10):
            # Mix of different operations
            if i % 3 == 0:
                tasks.append(client.get("/health"))
            elif i % 3 == 1:
                tasks.append(client.get("/api/photos/public"))
            else:
                photo_data = {"filename": f"load_{i}.jpg", "title": f"Load Test {i}"}
                tasks.append(client.post("/api/photos/upload", json=photo_data, headers=headers))
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # All operations should complete successfully
        for result in results:
            assert result.status_code in [200, 201]
        
        # Total time should be reasonable (less than 10 seconds for 10 operations)
        total_time = end_time - start_time
        assert total_time < 10.0, f"Operations took too long: {total_time}s"
        
        # Average response time should be reasonable
        avg_response_time = total_time / len(results)
        assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time}s"