#!/usr/bin/env python3
"""
Unit tests for monitoring functionality.

Rewritten to match the actual monitoring implementation
(services/photoshare/monitoring.py). The classes this file used to test
(MetricsCollector, PerformanceMonitor, HealthChecker, SecurityMonitor,
RequestMetrics) do not exist in the codebase -- the real module wraps
prometheus_client directly (PrometheusMetrics, MonitoringMiddleware,
MonitoringDashboard) rather than rolling its own in-memory stats/health/
security tracking.
"""
import uuid

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import Request
from fastapi.responses import Response as FastAPIResponse

from services.photoshare.monitoring import (
    PrometheusMetrics, MonitoringMiddleware, MonitoringDashboard,
    record_request_metric, record_database_metric, record_cache_metric,
    record_error_metric, record_auth_metric, record_rate_limit_metric,
    monitoring_dashboard,
)


def _unique_service_name():
    # prometheus_client registers metrics globally by name; each test needs
    # its own namespace or it collides with metrics from other tests / the
    # module-level `monitoring_dashboard` singleton.
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def metrics():
    return PrometheusMetrics(service_name=_unique_service_name())


class TestPrometheusMetricsRecording:
    def test_record_request_updates_counter_and_histogram(self, metrics):
        metrics.record_request("GET", "/api/photos", 200, 0.25)

        count = metrics.requests_total.labels(method="GET", endpoint="/api/photos", status_code="200")._value.get()
        assert count == 1

    def test_record_database_query_success(self, metrics):
        metrics.record_database_query("select", 0.01, success=True)

        count = metrics.database_queries_total.labels(query_type="select", status="success")._value.get()
        assert count == 1

    def test_record_database_query_failure(self, metrics):
        metrics.record_database_query("insert", 0.02, success=False)

        count = metrics.database_queries_total.labels(query_type="insert", status="error")._value.get()
        assert count == 1

    def test_record_cache_operation(self, metrics):
        metrics.record_cache_operation("get", "hit")

        count = metrics.cache_operations_total.labels(operation="get", result="hit")._value.get()
        assert count == 1

    def test_record_error(self, metrics):
        metrics.record_error("validation_error", severity="warning")

        count = metrics.errors_total.labels(error_type="validation_error", severity="warning")._value.get()
        assert count == 1

    def test_record_authentication_attempt_success_and_failure(self, metrics):
        metrics.record_authentication_attempt(True)
        metrics.record_authentication_attempt(False)

        assert metrics.authentication_attempts.labels(result="success")._value.get() == 1
        assert metrics.authentication_attempts.labels(result="failure")._value.get() == 1

    def test_record_rate_limit_hit(self, metrics):
        metrics.record_rate_limit_hit("anonymous")

        count = metrics.rate_limit_hits.labels(client_type="anonymous")._value.get()
        assert count == 1

    def test_update_service_info(self, metrics):
        metrics.update_service_info(version="9.9.9", database_type="postgresql", cache_type="memory")

        value = metrics.service_info.labels(version="9.9.9", database_type="postgresql", cache_type="memory")._value.get()
        assert value == 1

    def test_update_business_metrics(self, metrics):
        metrics.update_business_metrics(users_count=10, photos_count=20, active_sessions_count=3)

        assert metrics.users_total._value.get() == 10
        assert metrics.photos_total._value.get() == 20
        assert metrics.active_sessions._value.get() == 3

    def test_update_infrastructure_metrics(self, metrics):
        metrics.update_infrastructure_metrics(active_connections=5, cache_size=42)

        assert metrics.database_connections_active._value.get() == 5
        assert metrics.memory_cache_size._value.get() == 42

    def test_get_metrics_returns_prometheus_text_format(self, metrics):
        metrics.record_request("GET", "/api/photos", 200, 0.1)
        output = metrics.get_metrics()

        assert isinstance(output, bytes)
        assert metrics.service_name.encode() in output


class TestMonitoringMiddleware:
    @pytest.fixture
    def middleware(self, metrics):
        return MonitoringMiddleware(metrics)

    @staticmethod
    def _make_request(path="/api/photos"):
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = path
        request.method = "GET"
        return request

    @pytest.mark.asyncio
    async def test_call_records_successful_request(self, middleware, metrics):
        request = self._make_request()
        response = Mock()
        response.status_code = 200
        call_next = AsyncMock(return_value=response)

        result = await middleware(request, call_next)

        assert result is response
        count = metrics.requests_total.labels(method="GET", endpoint="/api/photos", status_code="200")._value.get()
        assert count == 1

    @pytest.mark.asyncio
    async def test_call_records_error_and_reraises(self, middleware, metrics):
        request = self._make_request()
        call_next = AsyncMock(side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError):
            await middleware(request, call_next)

        count = metrics.requests_total.labels(method="GET", endpoint="/api/photos", status_code="500")._value.get()
        assert count == 1
        error_count = metrics.errors_total.labels(error_type="request_processing_error", severity="error")._value.get()
        assert error_count == 1

    def test_normalize_endpoint_collapses_photo_id(self, middleware):
        assert middleware._normalize_endpoint("/api/photos/123") == "/api/photos/{id}"

    def test_normalize_endpoint_collapses_photo_id_subresource(self, middleware):
        assert middleware._normalize_endpoint("/api/photos/123/download") == "/api/photos/{id}/download"

    def test_normalize_endpoint_collapses_service_name(self, middleware):
        assert middleware._normalize_endpoint("/api/platform/services/auth-service") == "/api/platform/services/{service_name}"

    def test_normalize_endpoint_leaves_other_paths_untouched(self, middleware):
        assert middleware._normalize_endpoint("/health") == "/health"


class TestMonitoringDashboard:
    @pytest.fixture
    def dashboard(self):
        return MonitoringDashboard(service_name=_unique_service_name())

    def test_init_sets_service_info(self, dashboard):
        value = dashboard.metrics.service_info.labels(
            version="2.3.0-monitoring", database_type="postgresql", cache_type="memory"
        )._value.get()
        assert value == 1

    def test_get_monitoring_dashboard_shape(self, dashboard):
        data = dashboard.get_monitoring_dashboard()

        assert data["monitoring_system"]["service_name"] == dashboard.service_name
        assert data["monitoring_system"]["prometheus_endpoint"] == "/metrics"
        assert "metrics_summary" in data
        assert data["health_status"]["service_healthy"] is True
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_update_business_metrics_from_stats(self, dashboard):
        await dashboard.update_business_metrics_from_stats(
            {"registered_users": 5, "total_photos": 12, "active_sessions": 2}
        )

        assert dashboard.metrics.users_total._value.get() == 5
        assert dashboard.metrics.photos_total._value.get() == 12
        assert dashboard.metrics.active_sessions._value.get() == 2

    @pytest.mark.asyncio
    async def test_update_metrics_from_performance_data(self, dashboard):
        await dashboard.update_metrics_from_performance_data({
            "cache_performance": {"cache_hits": 10, "cache_misses": 2, "memory_cache_size": 7},
            "query_performance": {"query_statistics": {"select_photos": {"average_time": 0.05}}},
        })

        assert dashboard.metrics.memory_cache_size._value.get() == 7

    def test_get_prometheus_metrics_returns_fastapi_response(self, dashboard):
        response = dashboard.get_prometheus_metrics()

        assert isinstance(response, FastAPIResponse)
        assert response.headers["Cache-Control"] == "no-cache"


class TestConvenienceFunctions:
    """Test the module-level helpers that delegate to the global monitoring_dashboard."""

    def test_record_request_metric_delegates(self):
        with patch.object(monitoring_dashboard.metrics, "record_request") as mock_record:
            record_request_metric("POST", "/api/photos/upload", 201, 0.4)
        mock_record.assert_called_once_with("POST", "/api/photos/upload", 201, 0.4)

    def test_record_database_metric_delegates(self):
        with patch.object(monitoring_dashboard.metrics, "record_database_query") as mock_record:
            record_database_metric("select", 0.02, success=True)
        mock_record.assert_called_once_with("select", 0.02, True)

    def test_record_cache_metric_delegates(self):
        with patch.object(monitoring_dashboard.metrics, "record_cache_operation") as mock_record:
            record_cache_metric("get", "miss")
        mock_record.assert_called_once_with("get", "miss")

    def test_record_error_metric_delegates(self):
        with patch.object(monitoring_dashboard.metrics, "record_error") as mock_record:
            record_error_metric("timeout", severity="critical")
        mock_record.assert_called_once_with("timeout", "critical")

    def test_record_auth_metric_delegates(self):
        with patch.object(monitoring_dashboard.metrics, "record_authentication_attempt") as mock_record:
            record_auth_metric(True)
        mock_record.assert_called_once_with(True)

    def test_record_rate_limit_metric_delegates(self):
        with patch.object(monitoring_dashboard.metrics, "record_rate_limit_hit") as mock_record:
            record_rate_limit_metric("bot")
        mock_record.assert_called_once_with("bot")
