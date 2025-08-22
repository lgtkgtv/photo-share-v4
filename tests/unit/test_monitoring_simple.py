"""
Unit tests for monitoring components.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import Request, Response

from monitoring import PrometheusMetrics, MonitoringMiddleware, MonitoringDashboard


class TestPrometheusMetrics:
    """Test PrometheusMetrics class."""

    @pytest.mark.unit
    def test_init(self):
        """Test metrics initialization."""
        metrics = PrometheusMetrics("photo_share")
        
        assert metrics is not None
        assert metrics.service_name == "photo_share"
        assert hasattr(metrics, 'request_count')
        assert hasattr(metrics, 'request_duration')

    @pytest.mark.unit
    def test_record_request(self):
        """Test request recording."""
        metrics = PrometheusMetrics("photo_share")
        
        # Should not raise exception
        metrics.record_request("GET", "/api/photos", 200, 0.5)
        
        assert True

    @pytest.mark.unit  
    def test_record_error(self):
        """Test error recording."""
        metrics = PrometheusMetrics("photo_share")
        
        # Should not raise exception
        metrics.record_error("ValidationError", "api")
        
        assert True


class TestMonitoringMiddleware:
    """Test MonitoringMiddleware class."""

    @pytest.mark.unit
    def test_init(self):
        """Test middleware initialization."""
        app = Mock()
        middleware = MonitoringMiddleware(app)
        
        assert middleware is not None
        assert hasattr(middleware, 'metrics')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dispatch(self):
        """Test request dispatch with monitoring."""
        app = Mock()
        middleware = MonitoringMiddleware(app)
        
        # Mock request and response
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/photos"
        
        response = Mock(spec=Response)
        response.status_code = 200
        
        async def mock_call_next(req):
            return response
        
        result = await middleware.dispatch(request, mock_call_next)
        
        assert result == response


class TestMonitoringDashboard:
    """Test MonitoringDashboard class."""

    @pytest.mark.unit
    def test_init(self):
        """Test dashboard initialization."""
        dashboard = MonitoringDashboard()
        
        assert dashboard is not None

    @pytest.mark.unit
    def test_get_metrics_endpoint(self):
        """Test metrics endpoint."""
        dashboard = MonitoringDashboard()
        
        # Mock FastAPI app
        app = Mock()
        dashboard.setup_dashboard(app)
        
        # Should add routes to app
        assert app.add_api_route.called or hasattr(dashboard, 'get_metrics')

    @pytest.mark.unit
    async def test_get_system_stats(self):
        """Test system statistics."""
        dashboard = MonitoringDashboard()
        
        stats = await dashboard.get_system_stats()
        
        # Should return dict with stats
        assert isinstance(stats, dict)