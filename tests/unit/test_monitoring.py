"""
Unit tests for monitoring components - Fixed version.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, Response
from prometheus_client import CollectorRegistry

from monitoring import PrometheusMetrics, MonitoringMiddleware, MonitoringDashboard


class TestPrometheusMetrics:
    """Test PrometheusMetrics class."""
    
    def teardown_method(self):
        """Clean up after each test."""
        from prometheus_client import REGISTRY
        # Clear any collectors that might conflict
        try:
            collectors = list(REGISTRY._collector_to_names.keys())
            for collector in collectors:
                if hasattr(collector, '_name') and 'test_service' in str(collector._name):
                    REGISTRY.unregister(collector)
        except:
            pass

    @pytest.mark.unit
    def test_init(self):
        """Test metrics initialization."""
        import uuid
        service_name = f"test_service_{uuid.uuid4().hex[:8]}"
        metrics = PrometheusMetrics(service_name=service_name)
        
        assert metrics is not None
        assert metrics.service_name == service_name
        assert hasattr(metrics, 'requests_total')
        assert hasattr(metrics, 'request_duration_seconds')

    @pytest.mark.unit
    def test_record_request(self):
        """Test request recording."""
        import uuid
        service_name = f"test_service_{uuid.uuid4().hex[:8]}"
        metrics = PrometheusMetrics(service_name=service_name)
        
        # Record a request - this should not raise an exception
        metrics.record_request("GET", "/api/test", 200, 0.5)
        
        # Verify the method exists and can be called
        assert hasattr(metrics, 'record_request')
        assert callable(getattr(metrics, 'record_request'))

    @pytest.mark.unit
    def test_record_error(self):
        """Test error recording."""
        import uuid
        service_name = f"test_service_{uuid.uuid4().hex[:8]}"
        metrics = PrometheusMetrics(service_name=service_name)
        
        # Record an error - this should not raise an exception
        metrics.record_error("authentication", "error")
        
        # Verify the method exists and can be called
        assert hasattr(metrics, 'record_error')
        assert callable(getattr(metrics, 'record_error'))

    @pytest.mark.unit
    def test_record_database_query(self):
        """Test database query recording."""
        import uuid
        service_name = f"test_service_{uuid.uuid4().hex[:8]}"
        metrics = PrometheusMetrics(service_name=service_name)
        
        # Record database query - this should not raise an exception
        metrics.record_database_query("SELECT", 0.1, True)
        
        # Verify the method exists and can be called
        assert hasattr(metrics, 'record_database_query')
        assert callable(getattr(metrics, 'record_database_query'))

    @pytest.mark.unit
    def test_record_cache_operation(self):
        """Test cache operation recording."""
        import uuid
        service_name = f"test_service_{uuid.uuid4().hex[:8]}"
        metrics = PrometheusMetrics(service_name=service_name)
        
        # Record cache operation - this should not raise an exception
        metrics.record_cache_operation("get", "hit")
        
        # Verify the method exists and can be called
        assert hasattr(metrics, 'record_cache_operation')
        assert callable(getattr(metrics, 'record_cache_operation'))


class TestMonitoringMiddleware:
    """Test MonitoringMiddleware class."""

    @pytest.mark.unit
    def test_init(self):
        """Test middleware initialization."""
        import uuid
        service_name = f"test_service_{uuid.uuid4().hex[:8]}"
        metrics = PrometheusMetrics(service_name=service_name)
        middleware = MonitoringMiddleware(metrics=metrics)
        
        assert middleware is not None
        assert middleware.metrics == metrics

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call(self):
        """Test middleware call."""
        import uuid
        service_name = f"test_service_{uuid.uuid4().hex[:8]}"
        metrics = PrometheusMetrics(service_name=service_name)
        middleware = MonitoringMiddleware(metrics=metrics)
        
        # Mock request and call_next
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"
        
        call_next = AsyncMock()
        response = Mock(spec=Response)
        response.status_code = 200
        call_next.return_value = response
        
        # Test __call__
        result = await middleware(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)


class TestMonitoringDashboard:
    """Test MonitoringDashboard class."""

    @pytest.mark.unit
    def test_init(self):
        """Test dashboard initialization."""
        service_name = "test_service"
        dashboard = MonitoringDashboard(service_name=service_name)
        
        assert dashboard is not None
        assert dashboard.service_name == service_name
        assert hasattr(dashboard, 'metrics')
        assert hasattr(dashboard, 'middleware')

    @pytest.mark.unit
    def test_get_metrics_endpoint(self):
        """Test metrics endpoint."""
        service_name = "test_service"
        dashboard = MonitoringDashboard(service_name=service_name)
        
        # Test get_prometheus_metrics method
        response = dashboard.get_prometheus_metrics()
        
        assert response is not None
        # FastAPI Response should have status_code
        assert hasattr(response, 'status_code')

    @pytest.mark.unit
    def test_get_monitoring_dashboard(self):
        """Test monitoring dashboard endpoint."""
        service_name = "test_service"
        dashboard = MonitoringDashboard(service_name=service_name)
        
        # Test get_monitoring_dashboard
        stats = dashboard.get_monitoring_dashboard()
        
        assert isinstance(stats, dict)
        assert "health_status" in stats
        assert "metrics_summary" in stats