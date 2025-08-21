"""
Unit tests for performance optimization components.
"""
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch

from performance_simple import (
    MemoryCacheManager, QueryOptimizer, PerformanceOptimizer,
    OptimizedDatabaseOperations
)


class TestMemoryCacheManager:
    """Test MemoryCacheManager class."""

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_init(self):
        """Test cache manager initialization."""
        cache = MemoryCacheManager()
        
        assert cache.max_memory_cache_size == 2000
        assert cache.cache_stats["hits"] == 0
        assert cache.cache_stats["misses"] == 0
        assert cache.cache_warming_enabled is True

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_set_and_get(self):
        """Test setting and getting cache values."""
        cache = MemoryCacheManager()
        
        # Set value
        success = await cache.set("test_key", "test_value", ttl=300)
        assert success is True
        
        # Get value
        value = await cache.get("test_key")
        assert value == "test_value"
        
        # Check stats
        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 0

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_get_missing_key(self):
        """Test getting non-existent key."""
        cache = MemoryCacheManager()
        
        value = await cache.get("missing_key")
        
        assert value is None
        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 1

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_expiration(self):
        """Test cache expiration."""
        cache = MemoryCacheManager()
        
        # Set value with short TTL
        await cache.set("expire_key", "expire_value", ttl=1)
        
        # Should be available immediately
        value = await cache.get("expire_key")
        assert value == "expire_value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        value = await cache.get("expire_key")
        assert value is None

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_delete(self):
        """Test cache deletion."""
        cache = MemoryCacheManager()
        
        await cache.set("delete_key", "delete_value")
        
        # Verify it exists
        value = await cache.get("delete_key")
        assert value == "delete_value"
        
        # Delete
        success = await cache.delete("delete_key")
        assert success is True
        
        # Verify it's gone
        value = await cache.get("delete_key")
        assert value is None

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_clear_pattern(self):
        """Test pattern-based cache clearing."""
        cache = MemoryCacheManager()
        
        # Set multiple keys
        await cache.set("user:1:profile", "profile1")
        await cache.set("user:2:profile", "profile2")
        await cache.set("photo:1:data", "photo1")
        
        # Clear user pattern
        cleared = await cache.clear_pattern("user:*")
        
        assert cleared >= 2  # Should clear at least the user keys
        
        # Verify user keys are gone but photo key remains
        assert await cache.get("user:1:profile") is None
        assert await cache.get("user:2:profile") is None
        assert await cache.get("photo:1:data") == "photo1"

    @pytest.mark.unit
    @pytest.mark.performance
    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        cache = MemoryCacheManager()
        
        # Simulate some activity
        cache.cache_stats["hits"] = 10
        cache.cache_stats["misses"] = 5
        cache.cache_stats["total_requests"] = 15
        
        stats = cache.get_cache_stats()
        
        assert stats["cache_hits"] == 10
        assert stats["cache_misses"] == 5
        assert stats["total_requests"] == 15
        assert stats["hit_rate_percentage"] == 66.67
        assert "cache_type" in stats
        assert "features" in stats


class TestQueryOptimizer:
    """Test QueryOptimizer class."""

    @pytest.mark.unit
    @pytest.mark.performance
    def test_init(self):
        """Test query optimizer initialization."""
        optimizer = QueryOptimizer()
        
        assert isinstance(optimizer.query_stats, dict)
        assert isinstance(optimizer.slow_queries, list)
        assert optimizer.slow_query_threshold == 1.0

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_monitor_query_decorator(self):
        """Test query monitoring decorator."""
        optimizer = QueryOptimizer()
        
        @optimizer.monitor_query("test_query")
        async def test_function():
            time.sleep(0.1)  # Simulate work
            return "result"
        
        result = await test_function()
        
        assert result == "result"
        assert "test_query" in optimizer.query_stats
        
        stats = optimizer.query_stats["test_query"]
        assert stats["count"] == 1
        assert stats["total_time"] > 0
        assert stats["errors"] == 0

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_monitor_query_with_error(self):
        """Test query monitoring with errors."""
        optimizer = QueryOptimizer()
        
        @optimizer.monitor_query("error_query")
        async def error_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await error_function()
        
        assert "error_query" in optimizer.query_stats
        stats = optimizer.query_stats["error_query"]
        assert stats["errors"] == 1

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_slow_query_detection(self):
        """Test slow query detection."""
        optimizer = QueryOptimizer()
        optimizer.slow_query_threshold = 0.05  # 50ms
        
        @optimizer.monitor_query("slow_query")
        async def slow_function():
            time.sleep(0.1)  # 100ms - should be detected as slow
            return "result"
        
        await slow_function()
        
        assert len(optimizer.slow_queries) == 1
        slow_query = optimizer.slow_queries[0]
        assert slow_query["query_name"] == "slow_query"
        assert slow_query["duration"] > 0.05

    @pytest.mark.unit
    @pytest.mark.performance
    def test_get_query_stats(self):
        """Test getting query statistics."""
        optimizer = QueryOptimizer()
        
        # Simulate query stats
        optimizer.query_stats["test_query"] = {
            "count": 5,
            "total_time": 0.5,
            "min_time": 0.05,
            "max_time": 0.15,
            "errors": 1
        }
        
        stats = optimizer.get_query_stats()
        
        assert "query_statistics" in stats
        assert "slow_queries_count" in stats
        
        query_stats = stats["query_statistics"]["test_query"]
        assert query_stats["count"] == 5
        assert query_stats["average_time"] == 0.1  # 0.5 / 5
        assert query_stats["error_rate"] == 20.0  # 1 / 5 * 100


class TestPerformanceOptimizer:
    """Test PerformanceOptimizer class."""

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_init(self):
        """Test performance optimizer initialization."""
        optimizer = PerformanceOptimizer()
        
        assert optimizer.cache_manager is not None
        assert optimizer.pool_manager is not None
        assert optimizer.query_optimizer is not None

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_initialize(self):
        """Test performance optimizer initialization."""
        optimizer = PerformanceOptimizer()
        
        success = await optimizer.initialize()
        
        assert success is True

    @pytest.mark.unit
    @pytest.mark.performance
    def test_record_request_time(self):
        """Test recording request times."""
        optimizer = PerformanceOptimizer()
        
        optimizer.record_request_time(0.5)
        optimizer.record_request_time(0.3)
        
        assert len(optimizer.request_times) == 2
        assert optimizer.request_times[0]["duration"] == 0.5
        assert optimizer.request_times[1]["duration"] == 0.3

    @pytest.mark.unit
    @pytest.mark.performance
    def test_get_performance_summary(self):
        """Test getting performance summary."""
        optimizer = PerformanceOptimizer()
        
        # Simulate some request times
        current_time = time.time()
        optimizer.request_times = [
            {"duration": 0.1, "timestamp": current_time - 30},
            {"duration": 0.2, "timestamp": current_time - 20},
            {"duration": 0.15, "timestamp": current_time - 10}
        ]
        
        summary = optimizer.get_performance_summary()
        
        assert "performance_metrics" in summary
        assert "cache_performance" in summary
        assert "query_performance" in summary
        assert "optimization_status" in summary
        
        metrics = summary["performance_metrics"]
        assert "requests_per_second" in metrics
        assert "average_response_time_ms" in metrics

    @pytest.mark.unit
    @pytest.mark.performance
    def test_get_cache_analytics(self):
        """Test getting cache analytics."""
        optimizer = PerformanceOptimizer()
        
        analytics = optimizer.get_cache_analytics()
        
        assert "cache_performance" in analytics
        assert "recommendations" in analytics
        assert "timestamp" in analytics

    @pytest.mark.unit
    @pytest.mark.performance
    def test_cache_recommendations(self):
        """Test cache performance recommendations."""
        optimizer = PerformanceOptimizer()
        
        # Simulate poor cache performance
        test_stats = {
            "hit_rate_percentage": 25,
            "cache_hits": 25,
            "cache_evictions": 100,
            "memory_cache_size": 1900,
            "max_cache_size": 2000
        }
        
        recommendations = optimizer._get_cache_recommendations(test_stats)
        
        assert len(recommendations) > 0
        assert any("TTL" in rec for rec in recommendations)


class TestOptimizedDatabaseOperations:
    """Test OptimizedDatabaseOperations class."""

    @pytest.mark.unit
    @pytest.mark.performance
    def test_init(self):
        """Test optimized DB operations initialization."""
        mock_perf = Mock()
        db_ops = OptimizedDatabaseOperations(mock_perf)
        
        assert db_ops.perf == mock_perf

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_invalidate_user_cache(self):
        """Test user cache invalidation."""
        mock_perf = Mock()
        mock_perf.cache_manager = AsyncMock()
        
        db_ops = OptimizedDatabaseOperations(mock_perf)
        
        await db_ops.invalidate_user_cache(123)
        
        mock_perf.cache_manager.clear_pattern.assert_called()

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_invalidate_photo_cache(self):
        """Test photo cache invalidation."""
        mock_perf = Mock()
        mock_perf.cache_manager = AsyncMock()
        
        db_ops = OptimizedDatabaseOperations(mock_perf)
        
        await db_ops.invalidate_photo_cache()
        
        # Should call clear_pattern multiple times
        assert mock_perf.cache_manager.clear_pattern.call_count >= 2

    @pytest.mark.unit
    @pytest.mark.performance
    async def test_get_performance_recommendations(self):
        """Test getting performance recommendations."""
        mock_perf = Mock()
        db_ops = OptimizedDatabaseOperations(mock_perf)
        
        recommendations = await db_ops.get_performance_recommendations()
        
        assert "recommended_indexes" in recommendations
        assert "query_optimizations" in recommendations
        assert "cache_strategy" in recommendations
        
        # Check that we have specific index recommendations
        indexes = recommendations["recommended_indexes"]
        assert len(indexes) > 0
        assert any("photos" in idx["table"] for idx in indexes)
        assert any("CREATE INDEX" in idx["index"] for idx in indexes)