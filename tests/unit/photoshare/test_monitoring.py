#!/usr/bin/env python3
"""
Unit tests for monitoring functionality.
"""
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from services.photoshare.monitoring import (
    MetricsCollector, PerformanceMonitor, HealthChecker,
    SecurityMonitor, RequestMetrics
)


class TestRequestMetrics:
    """Test Request Metrics data class."""
    
    def test_request_metrics_creation(self):
        """Test request metrics creation."""
        start_time = time.time()
        metrics = RequestMetrics(
            method="GET",
            endpoint="/api/photos",
            status_code=200,
            response_time=0.123,
            user_id="user123",
            request_size=512,
            response_size=2048,
            timestamp=start_time
        )
        
        assert metrics.method == "GET"
        assert metrics.endpoint == "/api/photos"
        assert metrics.status_code == 200
        assert metrics.response_time == 0.123
        assert metrics.user_id == "user123"
        assert metrics.request_size == 512
        assert metrics.response_size == 2048
        assert metrics.timestamp == start_time
    
    def test_request_metrics_to_dict(self):
        """Test request metrics serialization."""
        metrics = RequestMetrics(
            method="POST",
            endpoint="/api/photos/upload",
            status_code=201,
            response_time=1.5
        )
        
        metrics_dict = metrics.to_dict()
        
        assert metrics_dict["method"] == "POST"
        assert metrics_dict["endpoint"] == "/api/photos/upload"
        assert metrics_dict["status_code"] == 201
        assert metrics_dict["response_time"] == 1.5


class TestMetricsCollector:
    """Test Metrics Collector functionality."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector instance."""
        return MetricsCollector()
    
    def test_metrics_collector_initialization(self, metrics_collector):
        """Test metrics collector initialization."""
        assert len(metrics_collector.request_metrics) == 0
        assert metrics_collector.start_time is not None
        assert metrics_collector.total_requests == 0
    
    def test_record_request_metric(self, metrics_collector):
        """Test recording request metrics."""
        metrics = RequestMetrics(
            method="GET",
            endpoint="/api/photos",
            status_code=200,
            response_time=0.5
        )
        
        metrics_collector.record_request(metrics)
        
        assert len(metrics_collector.request_metrics) == 1
        assert metrics_collector.total_requests == 1
        assert metrics_collector.request_metrics[0].method == "GET"
    
    def test_get_request_stats(self, metrics_collector):
        """Test getting request statistics."""
        # Record multiple requests
        metrics_collector.record_request(RequestMetrics("GET", "/api/photos", 200, 0.1))
        metrics_collector.record_request(RequestMetrics("POST", "/api/photos", 201, 0.5))
        metrics_collector.record_request(RequestMetrics("GET", "/api/photos", 404, 0.2))
        
        stats = metrics_collector.get_request_stats()
        
        assert stats["total_requests"] == 3
        assert stats["avg_response_time"] == 0.26666666666666666  # (0.1 + 0.5 + 0.2) / 3
        assert stats["success_rate"] == 66.67  # 2/3 * 100
        assert "status_codes" in stats
        assert stats["status_codes"]["200"] == 1
        assert stats["status_codes"]["201"] == 1
        assert stats["status_codes"]["404"] == 1
    
    def test_get_endpoint_stats(self, metrics_collector):
        """Test getting endpoint-specific statistics."""
        metrics_collector.record_request(RequestMetrics("GET", "/api/photos", 200, 0.1))
        metrics_collector.record_request(RequestMetrics("GET", "/api/photos", 200, 0.2))
        metrics_collector.record_request(RequestMetrics("POST", "/api/photos", 201, 0.5))
        
        stats = metrics_collector.get_endpoint_stats()
        
        assert "/api/photos" in stats
        assert stats["/api/photos"]["total_requests"] == 3
        assert stats["/api/photos"]["avg_response_time"] == 0.26666666666666666
    
    def test_get_user_stats(self, metrics_collector):
        """Test getting user-specific statistics."""
        metrics_collector.record_request(RequestMetrics("GET", "/api/photos", 200, 0.1, "user1"))
        metrics_collector.record_request(RequestMetrics("GET", "/api/photos", 200, 0.2, "user1"))
        metrics_collector.record_request(RequestMetrics("POST", "/api/photos", 201, 0.5, "user2"))
        
        stats = metrics_collector.get_user_stats()
        
        assert "user1" in stats
        assert "user2" in stats
        assert stats["user1"]["total_requests"] == 2
        assert stats["user2"]["total_requests"] == 1
    
    def test_cleanup_old_metrics(self, metrics_collector):
        """Test cleanup of old metrics."""
        old_time = time.time() - 7200  # 2 hours ago
        recent_time = time.time()
        
        metrics_collector.record_request(RequestMetrics("GET", "/api/photos", 200, 0.1, timestamp=old_time))
        metrics_collector.record_request(RequestMetrics("GET", "/api/photos", 200, 0.2, timestamp=recent_time))
        
        assert len(metrics_collector.request_metrics) == 2
        
        metrics_collector.cleanup_old_metrics(max_age_hours=1)
        
        assert len(metrics_collector.request_metrics) == 1
        assert metrics_collector.request_metrics[0].timestamp == recent_time


class TestPerformanceMonitor:
    """Test Performance Monitor functionality."""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor instance."""
        return PerformanceMonitor()
    
    def test_performance_monitor_initialization(self, performance_monitor):
        """Test performance monitor initialization."""
        assert performance_monitor.metrics_collector is not None
        assert len(performance_monitor.system_metrics) == 0
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, performance_monitor):
        """Test system metrics collection."""
        with patch('psutil.cpu_percent', return_value=45.5):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 67.8
                mock_memory.return_value.used = 8589934592  # 8GB
                mock_memory.return_value.total = 17179869184  # 16GB
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 23.4
                    mock_disk.return_value.used = 1073741824  # 1GB
                    mock_disk.return_value.total = 10737418240  # 10GB
                    
                    metrics = await performance_monitor.collect_system_metrics()
                    
                    assert metrics["cpu_percent"] == 45.5
                    assert metrics["memory_percent"] == 67.8
                    assert metrics["disk_percent"] == 23.4
                    assert "timestamp" in metrics
    
    @pytest.mark.asyncio
    async def test_get_performance_report(self, performance_monitor):
        """Test performance report generation."""
        # Add some test metrics
        performance_monitor.system_metrics = [
            {"cpu_percent": 45.5, "memory_percent": 67.8, "timestamp": time.time()},
            {"cpu_percent": 52.3, "memory_percent": 71.2, "timestamp": time.time()},
        ]
        
        # Add request metrics
        performance_monitor.metrics_collector.record_request(
            RequestMetrics("GET", "/api/photos", 200, 0.1)
        )
        
        report = await performance_monitor.get_performance_report()
        
        assert "system_metrics" in report
        assert "request_metrics" in report
        assert "uptime" in report
        assert report["system_metrics"]["avg_cpu_percent"] == 48.9
        assert report["system_metrics"]["avg_memory_percent"] == 69.5
    
    def test_is_system_healthy(self, performance_monitor):
        """Test system health checking."""
        # Healthy system
        healthy_metrics = {
            "cpu_percent": 45.0,
            "memory_percent": 60.0,
            "disk_percent": 40.0
        }
        assert performance_monitor.is_system_healthy(healthy_metrics) is True
        
        # Unhealthy system (high CPU)
        unhealthy_metrics = {
            "cpu_percent": 95.0,
            "memory_percent": 60.0,
            "disk_percent": 40.0
        }
        assert performance_monitor.is_system_healthy(unhealthy_metrics) is False


class TestHealthChecker:
    """Test Health Checker functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create health checker instance."""
        return HealthChecker()
    
    @pytest.mark.asyncio
    async def test_check_database_health_success(self, health_checker):
        """Test successful database health check."""
        mock_db = AsyncMock()
        mock_db.health_check = AsyncMock(return_value=True)
        
        result = await health_checker.check_database_health(mock_db)
        
        assert result["status"] == "healthy"
        assert result["response_time"] > 0
        mock_db.health_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_database_health_failure(self, health_checker):
        """Test failed database health check."""
        mock_db = AsyncMock()
        mock_db.health_check = AsyncMock(side_effect=Exception("Connection failed"))
        
        result = await health_checker.check_database_health(mock_db)
        
        assert result["status"] == "unhealthy"
        assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_check_auth_service_health_success(self, health_checker):
        """Test successful auth service health check."""
        mock_auth_client = AsyncMock()
        mock_auth_client.health_check = AsyncMock(return_value={"status": "healthy"})
        
        result = await health_checker.check_auth_service_health(mock_auth_client)
        
        assert result["status"] == "healthy"
        assert result["response_time"] > 0
    
    @pytest.mark.asyncio
    async def test_check_storage_health(self, health_checker):
        """Test storage health check."""
        with patch('os.path.exists', return_value=True):
            with patch('os.access', return_value=True):
                with patch('os.statvfs') as mock_statvfs:
                    mock_statvfs.return_value.f_bavail = 1000000
                    mock_statvfs.return_value.f_frsize = 4096
                    
                    result = await health_checker.check_storage_health("/tmp/storage")
                    
                    assert result["status"] == "healthy"
                    assert result["free_space_gb"] > 0
    
    @pytest.mark.asyncio
    async def test_get_overall_health(self, health_checker):
        """Test overall health assessment."""
        with patch.object(health_checker, 'check_database_health') as mock_db_health:
            with patch.object(health_checker, 'check_auth_service_health') as mock_auth_health:
                with patch.object(health_checker, 'check_storage_health') as mock_storage_health:
                    mock_db_health.return_value = {"status": "healthy"}
                    mock_auth_health.return_value = {"status": "healthy"}
                    mock_storage_health.return_value = {"status": "healthy"}
                    
                    health = await health_checker.get_overall_health(Mock(), Mock(), "/tmp")
                    
                    assert health["status"] == "healthy"
                    assert "database" in health["services"]
                    assert "auth_service" in health["services"]
                    assert "storage" in health["services"]


class TestSecurityMonitor:
    """Test Security Monitor functionality."""
    
    @pytest.fixture
    def security_monitor(self):
        """Create security monitor instance."""
        return SecurityMonitor()
    
    def test_security_monitor_initialization(self, security_monitor):
        """Test security monitor initialization."""
        assert len(security_monitor.security_events) == 0
        assert len(security_monitor.failed_attempts) == 0
    
    def test_record_security_event(self, security_monitor):
        """Test recording security events."""
        security_monitor.record_security_event(
            event_type="failed_login",
            user_id="user123",
            ip_address="192.168.1.100",
            details={"reason": "invalid_password"}
        )
        
        assert len(security_monitor.security_events) == 1
        event = security_monitor.security_events[0]
        assert event["event_type"] == "failed_login"
        assert event["user_id"] == "user123"
        assert event["ip_address"] == "192.168.1.100"
    
    def test_record_failed_attempt(self, security_monitor):
        """Test recording failed login attempts."""
        security_monitor.record_failed_attempt("user123", "192.168.1.100")
        security_monitor.record_failed_attempt("user123", "192.168.1.100")
        
        attempts = security_monitor.get_failed_attempts("user123")
        assert len(attempts) == 2
    
    def test_is_account_locked(self, security_monitor):
        """Test account lockout detection."""
        # Record multiple failed attempts
        for _ in range(5):
            security_monitor.record_failed_attempt("user123", "192.168.1.100")
        
        assert security_monitor.is_account_locked("user123") is True
        assert security_monitor.is_account_locked("user456") is False
    
    def test_is_ip_suspicious(self, security_monitor):
        """Test suspicious IP detection."""
        # Record multiple failed attempts from same IP
        for _ in range(10):
            security_monitor.record_failed_attempt(f"user{_}", "192.168.1.100")
        
        assert security_monitor.is_ip_suspicious("192.168.1.100") is True
        assert security_monitor.is_ip_suspicious("192.168.1.200") is False
    
    def test_get_security_stats(self, security_monitor):
        """Test security statistics."""
        # Record various security events
        security_monitor.record_security_event("failed_login", "user1", "192.168.1.100")
        security_monitor.record_security_event("successful_login", "user1", "192.168.1.100")
        security_monitor.record_security_event("failed_login", "user2", "192.168.1.200")
        
        stats = security_monitor.get_security_stats()
        
        assert stats["total_events"] == 3
        assert "event_types" in stats
        assert stats["event_types"]["failed_login"] == 2
        assert stats["event_types"]["successful_login"] == 1
    
    def test_cleanup_old_events(self, security_monitor):
        """Test cleanup of old security events."""
        old_time = time.time() - 7200  # 2 hours ago
        recent_time = time.time()
        
        security_monitor.security_events = [
            {"event_type": "failed_login", "timestamp": old_time},
            {"event_type": "successful_login", "timestamp": recent_time}
        ]
        
        security_monitor.cleanup_old_events(max_age_hours=1)
        
        assert len(security_monitor.security_events) == 1
        assert security_monitor.security_events[0]["event_type"] == "successful_login"