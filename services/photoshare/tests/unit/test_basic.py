"""
Basic tests to verify test setup is working.
"""
import pytest
import os


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
            import main
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

    @pytest.mark.unit
    def test_application_creation(self):
        """Test that main application can be created."""
        from main import PhotoShareDatabaseService
        
        # This should not raise an exception
        service = PhotoShareDatabaseService()
        assert service is not None
        assert service.app is not None
        assert service.service_name == "photo-share-database"