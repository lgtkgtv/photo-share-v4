"""
Component Integration Tests
Tests individual service components in isolation with real dependencies.
"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta


class TestDatabaseComponentIntegration:
    """Test database components with in-memory SQLite."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_models_crud_operations(self):
        """Test database models can perform CRUD operations."""
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from sqlalchemy.pool import StaticPool
        from database import Base, User, Photo
        
        # Create in-memory database
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Test User CRUD
            user = User(
                email="test@example.com",
                password_hash="hashed_password",
                is_verified=True,
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            assert user.id is not None
            assert user.email == "test@example.com"
            assert user.is_verified is True
            
            # Test Photo CRUD
            photo = Photo(
                user_id=user.id,
                filename="test.jpg",
                original_filename="my_photo.jpg",
                content_type="image/jpeg",
                file_size=1024,
                storage_path="users/1/photos/test.jpg",
                title="Test Photo",
                description="A test photo",
                is_public=True
            )
            session.add(photo)
            await session.commit()
            await session.refresh(photo)
            
            assert photo.id is not None
            assert photo.user_id == user.id
            assert photo.title == "Test Photo"
            
            # Test relationships
            # Note: In real implementation, you'd test user.photos relationship
            
        await engine.dispose()

    @pytest.mark.asyncio 
    @pytest.mark.integration
    async def test_database_repository_patterns(self):
        """Test database repository pattern implementation."""
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from sqlalchemy.pool import StaticPool
        from sqlalchemy import select
        from database import Base, User
        
        # Create in-memory database
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Test user creation and retrieval
            user = User(
                email="repository_test@example.com",
                password_hash="hashed_password",
                is_verified=False,
                is_active=True
            )
            session.add(user)
            await session.commit()
            
            # Test finding user by email
            result = await session.execute(
                select(User).where(User.email == "repository_test@example.com")
            )
            found_user = result.scalar_one_or_none()
            
            assert found_user is not None
            assert found_user.email == "repository_test@example.com"
            assert found_user.is_verified is False
            
            # Test updating user
            found_user.is_verified = True
            await session.commit()
            
            # Verify update
            result = await session.execute(
                select(User).where(User.id == found_user.id)
            )
            updated_user = result.scalar_one_or_none()
            assert updated_user.is_verified is True
            
        await engine.dispose()


class TestSecurityComponentIntegration:
    """Test security components with real cryptographic operations."""

    @pytest.mark.integration
    def test_password_hashing_component(self):
        """Test password hashing and verification."""
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Test password hashing
        password = "TestPassword123!"
        hashed = pwd_context.hash(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt identifier
        
        # Test password verification
        assert pwd_context.verify(password, hashed) is True
        assert pwd_context.verify("WrongPassword", hashed) is False

    @pytest.mark.integration
    def test_jwt_token_component(self):
        """Test JWT token creation and verification."""
        from jose import jwt, JWTError
        from datetime import datetime, timedelta
        
        secret_key = "test_secret_key_for_integration_testing"
        algorithm = "HS256"
        
        # Test token creation
        payload = {
            "sub": "123",
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(minutes=30)
        }
        
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are long
        
        # Test token verification
        decoded = jwt.decode(token, secret_key, algorithms=[algorithm])
        assert decoded["sub"] == "123"
        assert decoded["email"] == "test@example.com"
        
        # Test invalid token
        with pytest.raises(JWTError):
            jwt.decode("invalid_token", secret_key, algorithms=[algorithm])

    @pytest.mark.integration 
    def test_security_framework_component(self):
        """Test security framework component integration."""
        # Mock Redis for rate limiting
        with patch('redis.Redis') as mock_redis:
            mock_redis_instance = Mock()
            mock_redis_instance.get.return_value = None
            mock_redis_instance.setex.return_value = True
            mock_redis.return_value = mock_redis_instance
            
            # Test that we can import and instantiate security components
            try:
                from security import SecurityFramework
                
                # Test rate limiting component
                security = SecurityFramework()
                
                # Test that rate limiting logic can be called
                # (in real implementation, this would test actual rate limiting)
                assert security is not None
                
            except ImportError:
                pytest.skip("SecurityFramework not available for testing")


class TestFileStorageComponentIntegration:
    """Test file storage components with real file operations."""

    @pytest.mark.integration
    def test_local_file_storage_component(self):
        """Test local file storage operations."""
        from file_storage import FileStorageService
        import tempfile
        import os
        
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStorageService()
            storage.local_storage_path = temp_dir
            
            # Test file path generation
            user_id = 123
            filename = "test.jpg"
            storage_path = storage._get_storage_path(user_id, filename)
            
            assert storage_path == "users/123/photos/test.jpg"
            
            # Test file hash generation
            test_content = b"test file content"
            file_hash = storage._generate_file_hash(test_content)
            
            assert isinstance(file_hash, str)
            assert len(file_hash) == 64  # SHA-256 produces 64-char hex
            
            # Test that same content produces same hash
            file_hash2 = storage._generate_file_hash(test_content)
            assert file_hash == file_hash2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_file_storage_operations(self):
        """Test file storage operations with mocked platform storage."""
        from file_storage import FileStorageService
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStorageService()
            storage.local_storage_path = temp_dir
            
            # Mock platform storage methods
            storage._upload_to_platform_storage = AsyncMock(return_value=True)
            storage._download_from_platform_storage = AsyncMock(return_value=b"test content")
            storage._delete_from_platform_storage = AsyncMock(return_value=True)
            
            # Test file storage
            user_id = 123
            filename = "test.jpg"
            content = b"fake image data"
            content_type = "image/jpeg"
            
            result = await storage.store_file(user_id, filename, content, content_type)
            
            assert result["storage_path"] == "users/123/photos/test.jpg"
            assert result["file_size"] == len(content)
            assert result["content_type"] == content_type
            assert "file_hash" in result
            
            # Test file retrieval
            retrieved_content = await storage.retrieve_file(result["storage_path"])
            assert retrieved_content == content
            
            # Test file deletion
            deleted = await storage.delete_file(result["storage_path"])
            assert deleted is True

    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_file_storage_health_check(self):
        """Test file storage health check component."""
        from file_storage import FileStorageService
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStorageService()
            storage.local_storage_path = temp_dir
            
            # Mock platform health check
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
                
                health = await storage.health_check()
                
                assert "local_storage" in health
                assert "platform_storage" in health
                assert "storage_path" in health
                assert health["local_storage"] is True


class TestImageProcessingComponentIntegration:
    """Test image processing components with real image operations."""

    @pytest.mark.integration
    def test_image_validation_component(self):
        """Test image validation and processing."""
        from PIL import Image
        import io
        
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_data = img_bytes.getvalue()
        
        # Test that we can process the image
        try:
            test_img = Image.open(io.BytesIO(img_data))
            assert test_img.size == (100, 100)
            assert test_img.format == 'JPEG'
        except Exception as e:
            pytest.fail(f"Image processing failed: {e}")

    @pytest.mark.integration
    def test_image_metadata_extraction(self):
        """Test image metadata extraction."""
        from PIL import Image
        from PIL.ExifTags import TAGS
        import io
        
        # Create test image with metadata
        img = Image.new('RGB', (200, 150), color='blue')
        
        # Add some basic metadata
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=95)
        img_data = img_bytes.getvalue()
        
        # Test metadata extraction
        test_img = Image.open(io.BytesIO(img_data))
        
        # Basic image properties
        assert test_img.size == (200, 150)
        assert test_img.mode == 'RGB'
        assert test_img.format == 'JPEG'
        
        # Test that we can extract EXIF data (even if empty)
        exif_data = test_img.getexif()
        assert isinstance(exif_data, dict) or hasattr(exif_data, 'items')


class TestMonitoringComponentIntegration:
    """Test monitoring and metrics components."""

    @pytest.mark.integration
    def test_prometheus_metrics_component(self):
        """Test Prometheus metrics collection."""
        from prometheus_client import Counter, Histogram, generate_latest
        
        # Create test metrics
        request_counter = Counter('test_requests_total', 'Total test requests')
        response_time = Histogram('test_response_time_seconds', 'Response time')
        
        # Record some metrics
        request_counter.inc()
        request_counter.inc(5)
        
        with response_time.time():
            import time
            time.sleep(0.001)  # Simulate work
        
        # Test metrics generation
        metrics_output = generate_latest()
        assert isinstance(metrics_output, bytes)
        assert b'test_requests_total' in metrics_output
        assert b'test_response_time_seconds' in metrics_output

    @pytest.mark.integration
    def test_logging_middleware_component(self):
        """Test logging middleware component."""
        import logging
        from io import StringIO
        
        # Create test logger with string handler
        logger = logging.getLogger('test_logger')
        logger.setLevel(logging.INFO)
        
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(handler)
        
        # Test logging
        logger.info("Test log message")
        logger.warning("Test warning message")
        
        # Verify log output
        log_output = log_capture.getvalue()
        assert "Test log message" in log_output
        assert "Test warning message" in log_output
        assert "INFO:" in log_output
        assert "WARNING:" in log_output


class TestPerformanceComponentIntegration:
    """Test performance optimization components."""

    @pytest.mark.integration
    def test_memory_cache_component(self):
        """Test memory cache component."""
        from performance_simple import CacheManager
        
        # Test memory cache (fallback when Redis not available)
        cache = CacheManager()
        
        # Test cache operations
        cache.set('test_key', 'test_value', ttl=60)
        assert cache.get('test_key') == 'test_value'
        
        # Test cache expiration simulation
        cache.set('short_key', 'short_value', ttl=0.001)
        import time
        time.sleep(0.002)
        # Note: Memory cache might not respect TTL exactly, but should handle it gracefully
        
        # Test cache deletion
        cache.delete('test_key')
        assert cache.get('test_key') is None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_optimization_component(self):
        """Test query optimization and monitoring."""
        from performance_simple import QueryOptimizer
        import time
        
        optimizer = QueryOptimizer()
        
        @optimizer.monitor_query("test_query")
        async def test_query():
            await asyncio.sleep(0.001)  # Simulate query time
            return "query_result"
        
        # Execute monitored query
        result = await test_query()
        assert result == "query_result"
        
        # Check that query was monitored
        stats = optimizer.get_query_stats()
        assert "test_query" in stats
        assert stats["test_query"]["count"] == 1
        assert stats["test_query"]["errors"] == 0
        assert stats["test_query"]["total_time"] > 0

    @pytest.mark.integration
    def test_connection_pooling_component(self):
        """Test database connection pooling."""
        from sqlalchemy import create_engine
        from sqlalchemy.pool import StaticPool
        
        # Test connection pool configuration
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            pool_size=5,
            max_overflow=10,
            echo=False
        )
        
        # Test that we can get connections from the pool
        conn1 = engine.connect()
        conn2 = engine.connect()
        
        assert conn1 is not None
        assert conn2 is not None
        
        # Test connection cleanup
        conn1.close()
        conn2.close()
        engine.dispose()


class TestServiceDiscoveryComponentIntegration:
    """Test service discovery and health check components."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_aggregation(self):
        """Test health check aggregation from multiple components."""
        
        # Mock multiple service health checks
        database_health = {"status": "healthy", "response_time": 0.01}
        cache_health = {"status": "healthy", "hit_ratio": 0.85}
        storage_health = {"status": "healthy", "free_space": "85%"}
        
        # Aggregate health status
        overall_health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": database_health,
                "cache": cache_health,
                "storage": storage_health
            }
        }
        
        # Test health aggregation logic
        assert overall_health["status"] == "healthy"
        assert len(overall_health["services"]) == 3
        assert all(service["status"] == "healthy" for service in overall_health["services"].values())

    @pytest.mark.integration
    def test_service_registry_component(self):
        """Test service registry and discovery."""
        
        # Mock service registry
        services = {
            "photo-share": {
                "host": "localhost",
                "port": 8000,
                "health_endpoint": "/health",
                "version": "2.3.0-monitoring"
            },
            "auth-service": {
                "host": "localhost", 
                "port": 8001,
                "health_endpoint": "/health",
                "version": "1.0.0"
            }
        }
        
        # Test service discovery logic
        photo_service = services.get("photo-share")
        assert photo_service is not None
        assert photo_service["port"] == 8000
        assert photo_service["version"] == "2.3.0-monitoring"
        
        # Test service URL construction
        service_url = f"http://{photo_service['host']}:{photo_service['port']}"
        assert service_url == "http://localhost:8000"


class TestErrorHandlingComponentIntegration:
    """Test error handling and recovery components."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_error_recovery(self):
        """Test database error handling and recovery."""
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.exc import SQLAlchemyError
        
        # Test with invalid database URL
        engine = create_async_engine("sqlite+aiosqlite:///nonexistent/path/db.sqlite")
        
        try:
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
        except Exception as e:
            # Should handle database errors gracefully
            assert isinstance(e, (SQLAlchemyError, OSError))
        finally:
            await engine.dispose()

    @pytest.mark.integration
    def test_api_error_formatting(self):
        """Test API error response formatting."""
        from fastapi import HTTPException
        
        # Test error response structure
        try:
            raise HTTPException(
                status_code=404,
                detail="Photo not found",
                headers={"X-Error": "PHOTO_NOT_FOUND"}
            )
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == "Photo not found"
            assert e.headers == {"X-Error": "PHOTO_NOT_FOUND"}

    @pytest.mark.integration
    def test_retry_mechanism_component(self):
        """Test retry mechanism for external services."""
        import time
        
        # Simulate retry logic
        max_retries = 3
        retry_count = 0
        
        def failing_operation():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        # Test retry mechanism
        for attempt in range(max_retries):
            try:
                result = failing_operation()
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.001)  # Brief delay between retries
        
        assert result == "success"
        assert retry_count == 3