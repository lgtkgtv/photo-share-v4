"""
Basic tests to verify test setup is working.
"""
import pytest
import os
import sys

# Add service path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))


class TestBasicSetup:
    """Test basic setup and environment."""

    @pytest.mark.unit
    def test_environment_setup(self):
        """Test that test environment is properly configured."""
        assert os.environ.get("ENVIRONMENT") == "test"
        assert os.environ.get("JWT_SECRET_KEY") is not None

    @pytest.mark.unit
    def test_imports(self):
        """Test that core modules can be imported."""
        try:
            import main_database
            import database
            import security
            import performance_simple
            import monitoring
            import error_handling
            import file_storage
            import service_discovery
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import required modules: {e}")

    @pytest.mark.unit
    def test_database_models(self):
        """Test that database models are properly defined."""
        from database import User, Photo, Session as DBSession
        
        # Check that models have required attributes
        assert hasattr(User, 'email')
        assert hasattr(User, 'password_hash')
        assert hasattr(Photo, 'filename')
        assert hasattr(Photo, 'user_id')
        assert hasattr(DBSession, 'token')
        assert hasattr(DBSession, 'user_id')

    @pytest.mark.unit
    def test_security_components(self):
        """Test that security components are available."""
        from security import RateLimiter, InputValidator, SecurityAudit
        
        # Test instantiation
        rate_limiter = RateLimiter()
        validator = InputValidator()
        audit = SecurityAudit()
        
        assert rate_limiter is not None
        assert validator is not None
        assert audit is not None

    @pytest.mark.unit
    def test_performance_components(self):
        """Test that performance components are available."""
        from performance_simple import MemoryCacheManager, PerformanceOptimizer
        
        # Test instantiation
        cache = MemoryCacheManager()
        optimizer = PerformanceOptimizer()
        
        assert cache is not None
        assert optimizer is not None
        
        # Test that cache has expected methods (without calling async methods)
        assert hasattr(cache, 'set')
        assert hasattr(cache, 'get')
        assert hasattr(cache, 'delete')
        assert hasattr(cache, 'clear')
        
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_cache_operations(self):
        """Test async cache operations."""
        from performance_simple import MemoryCacheManager
        
        cache = MemoryCacheManager()
        
        # Test async cache operations
        await cache.set('test_key', 'test_value', ttl=60)
        cached_value = await cache.get('test_key')
        assert cached_value == 'test_value'
        
        # Test delete
        await cache.delete('test_key')
        cached_value = await cache.get('test_key')
        assert cached_value is None

    @pytest.mark.unit
    def test_application_creation(self):
        """Test that main application can be created."""
        from main_database import PhotoShareDatabaseService
        
        # This should not raise an exception
        service = PhotoShareDatabaseService()
        assert service is not None
        assert service.app is not None
        assert service.service_name == "photo-share-database"