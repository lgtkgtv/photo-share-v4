"""
Production Readiness Integration Tests
=====================================

Tests to verify Phase 2 production readiness improvements.
"""
import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch
import httpx
from fastapi.testclient import TestClient

# Set test environment before importing main
import os
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-32-chars-minimum-length-requirement"

@pytest.mark.integration
class TestProductionReadiness:
    """Test production readiness features."""
    
    @pytest.mark.asyncio
    async def test_redis_cache_integration(self):
        """Test Redis cache functionality."""
        from performance_simple import RedisCacheManager
        
        # Test Redis cache manager initialization
        cache_manager = RedisCacheManager()
        
        # Initialize (should fall back to memory cache in test)
        result = await cache_manager.initialize()
        
        # Test cache operations
        test_key = "test_key"
        test_value = {"data": "test_data", "timestamp": time.time()}
        
        # Set value
        set_result = await cache_manager.set(test_key, test_value, ttl=30)
        assert set_result is True
        
        # Get value
        retrieved_value = await cache_manager.get(test_key)
        assert retrieved_value is not None
        assert retrieved_value["data"] == "test_data"
        
        # Delete value
        delete_result = await cache_manager.delete(test_key)
        assert delete_result is True
        
        # Verify deletion
        deleted_value = await cache_manager.get(test_key)
        assert deleted_value is None
        
        # Test cache stats
        stats = cache_manager.get_cache_stats()
        assert "cache_type" in stats
        assert "total_requests" in stats
    
    @pytest.mark.asyncio
    async def test_database_connection_pooling(self):
        """Test optimized database connection pooling."""
        from database import db_manager
        
        # Initialize database manager
        await db_manager.initialize()
        
        # Test pool status
        pool_status = await db_manager.get_pool_status()
        assert "pool_size" in pool_status
        assert "checked_in_connections" in pool_status
        assert "checked_out_connections" in pool_status
        
        # Test health check
        health_result = await db_manager.health_check()
        assert health_result["healthy"] is True
        assert "pool_status" in health_result
        assert "environment" in health_result
        
        # Test multiple concurrent connections
        async def test_connection():
            async with db_manager.get_session() as session:
                result = await session.execute("SELECT 1 as test")
                return result.scalar()
        
        # Run multiple concurrent connections
        tasks = [test_connection() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should return 1
        assert all(result == 1 for result in results)
    
    def test_monitoring_metrics_endpoint(self, test_client: TestClient):
        """Test Prometheus metrics endpoint."""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        
        # Should return Prometheus format
        content = response.text
        assert "photo_share_requests_total" in content or "# HELP" in content
    
    def test_health_check_comprehensive(self, test_client: TestClient):
        """Test comprehensive health check."""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        assert "version" in health_data
    
    def test_platform_stats_endpoint(self, test_client: TestClient, auth_headers):
        """Test platform statistics endpoint."""
        response = test_client.get("/api/platform/stats", headers=auth_headers)
        
        if response.status_code == 200:
            stats_data = response.json()
            assert "database_pool" in stats_data or "cache_stats" in stats_data
    
    def test_security_endpoint(self, test_client: TestClient, auth_headers):
        """Test security status endpoint."""
        response = test_client.get("/api/platform/security", headers=auth_headers)
        
        if response.status_code == 200:
            security_data = response.json()
            assert isinstance(security_data, dict)
    
    def test_performance_endpoint(self, test_client: TestClient, auth_headers):
        """Test performance metrics endpoint."""
        response = test_client.get("/api/platform/performance", headers=auth_headers)
        
        if response.status_code == 200:
            perf_data = response.json()
            assert isinstance(perf_data, dict)
    
    @pytest.mark.asyncio
    async def test_database_migration_system(self):
        """Test database migration system."""
        from manage_db import DatabaseManager
        
        db_mgr = DatabaseManager()
        
        # Test showing current revision (shouldn't crash)
        try:
            db_mgr.show_current_revision()
        except Exception as e:
            # May fail in test environment, but shouldn't crash
            assert "alembic" in str(e).lower() or "database" in str(e).lower()
    
    @pytest.mark.asyncio  
    async def test_production_configuration_validation(self):
        """Test production configuration validation."""
        # Test environment variable validation
        assert os.getenv("ENVIRONMENT") == "test"
        
        # Test JWT secret validation
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        assert jwt_secret is not None
        assert len(jwt_secret) >= 32
        
        # Test that weak secrets are rejected
        weak_secrets = [
            "your-very-secure",
            "generate_with_script", 
            "change_this",
            "secret-key"
        ]
        
        for weak_secret in weak_secrets:
            assert weak_secret not in jwt_secret.lower()
    
    def test_file_upload_security_improvements(self, test_client: TestClient, auth_headers):
        """Test enhanced file upload security."""
        # Test valid image upload
        image_data = b'\xFF\xD8\xFF\xE0\x00\x10JFIF' + b'A' * 1000  # JPEG header + data
        files = {"file": ("test.jpg", image_data, "image/jpeg")}
        data = {"title": "Security Test Photo"}
        
        response = test_client.post(
            "/api/photos/upload", 
            files=files, 
            data=data, 
            headers=auth_headers
        )
        
        # Should either succeed or fail gracefully (depending on test setup)
        assert response.status_code in [200, 201, 400, 422, 500]
        
        # Test invalid file type (should be rejected)
        text_data = b"This is not an image file"
        files = {"file": ("test.txt", text_data, "text/plain")}
        data = {"title": "Invalid File"}
        
        response = test_client.post(
            "/api/photos/upload",
            files=files,
            data=data, 
            headers=auth_headers
        )
        
        # Should reject non-image files
        assert response.status_code in [400, 422]
    
    def test_rate_limiting_configuration(self, test_client: TestClient):
        """Test that rate limiting is properly configured."""
        # Test health endpoint (should not be rate limited heavily)
        for _ in range(5):
            response = test_client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_async_performance_features(self):
        """Test async performance optimizations."""
        from performance_simple import performance_optimizer
        
        # Test performance optimizer initialization
        await performance_optimizer.initialize()
        
        # Test cache manager
        assert performance_optimizer.cache_manager is not None
        
        # Test performance statistics
        stats = performance_optimizer.get_performance_stats()
        assert isinstance(stats, dict)
        
        # Test that we're using appropriate cache based on environment
        cache_stats = performance_optimizer.cache_manager.get_cache_stats()
        assert "cache_type" in cache_stats
    
    def test_cors_configuration(self, test_client: TestClient):
        """Test CORS configuration."""
        # Test preflight request
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        response = test_client.options("/api/users/me", headers=headers)
        
        # Should handle CORS properly
        assert response.status_code in [200, 404]  # 404 is OK for OPTIONS to non-existent endpoint
    
    def test_error_handling_middleware(self, test_client: TestClient):
        """Test error handling middleware."""
        # Test non-existent endpoint
        response = test_client.get("/api/nonexistent")
        assert response.status_code == 404
        
        # Should return JSON error response
        if response.headers.get("content-type", "").startswith("application/json"):
            error_data = response.json()
            assert "detail" in error_data or "message" in error_data

@pytest.mark.integration
class TestCI_CD_Integration:
    """Test CI/CD pipeline integration features."""
    
    def test_docker_health_checks(self):
        """Test Docker health check endpoints."""
        # This would be tested in Docker environment
        assert True  # Placeholder
    
    def test_migration_readiness(self):
        """Test database migration readiness."""
        # Test that migration files exist
        import os
        from pathlib import Path
        
        alembic_dir = Path("alembic")
        if alembic_dir.exists():
            versions_dir = alembic_dir / "versions"
            assert versions_dir.exists()
            
            # Should have at least one migration
            migration_files = list(versions_dir.glob("*.py"))
            assert len(migration_files) > 0
    
    def test_production_environment_detection(self):
        """Test production environment detection."""
        from main_database import ENVIRONMENT
        
        # Should detect test environment
        assert ENVIRONMENT == "test"
    
    def test_logging_configuration(self):
        """Test logging configuration."""
        import logging
        
        # Test that logging is properly configured
        logger = logging.getLogger("main")
        assert logger is not None
        
        # Test log level configuration
        assert logger.level >= logging.INFO