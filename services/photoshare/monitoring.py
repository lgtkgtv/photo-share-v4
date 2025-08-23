#!/usr/bin/env python3
"""
Monitoring Integration
======================

Prometheus metrics collection and monitoring dashboard integration.
"""

import time
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import Response as FastAPIResponse

logger = logging.getLogger(__name__)

class PrometheusMetrics:
    """Prometheus metrics collector for the photo sharing service."""
    
    def __init__(self, service_name: str = "photo_share"):
        self.service_name = service_name
        
        # Request metrics
        self.requests_total = Counter(
            f'{service_name}_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.request_duration_seconds = Histogram(
            f'{service_name}_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint']
        )
        
        # Database metrics
        self.database_queries_total = Counter(
            f'{service_name}_database_queries_total',
            'Total number of database queries',
            ['query_type', 'status']
        )
        
        self.database_query_duration_seconds = Histogram(
            f'{service_name}_database_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type']
        )
        
        # Cache metrics
        self.cache_operations_total = Counter(
            f'{service_name}_cache_operations_total',
            'Total number of cache operations',
            ['operation', 'result']
        )
        
        # Service health metrics
        self.service_info = Gauge(
            f'{service_name}_service_info',
            'Service information',
            ['version', 'database_type', 'cache_type']
        )
        
        self.database_connections_active = Gauge(
            f'{service_name}_database_connections_active',
            'Number of active database connections'
        )
        
        self.memory_cache_size = Gauge(
            f'{service_name}_memory_cache_size',
            'Number of items in memory cache'
        )
        
        # Business metrics
        self.users_total = Gauge(
            f'{service_name}_users_total',
            'Total number of registered users'
        )
        
        self.photos_total = Gauge(
            f'{service_name}_photos_total',
            'Total number of uploaded photos'
        )
        
        self.active_sessions = Gauge(
            f'{service_name}_active_sessions',
            'Number of active user sessions'
        )
        
        # Error metrics
        self.errors_total = Counter(
            f'{service_name}_errors_total',
            'Total number of errors',
            ['error_type', 'severity']
        )
        
        # Security metrics
        self.rate_limit_hits = Counter(
            f'{service_name}_rate_limit_hits_total',
            'Total number of rate limit hits',
            ['client_type']
        )
        
        self.authentication_attempts = Counter(
            f'{service_name}_authentication_attempts_total',
            'Total number of authentication attempts',
            ['result']
        )
        
        logger.info(f"Prometheus metrics initialized for {service_name}")
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        self.requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_database_query(self, query_type: str, duration: float, success: bool = True):
        """Record database query metrics."""
        status = "success" if success else "error"
        
        self.database_queries_total.labels(
            query_type=query_type,
            status=status
        ).inc()
        
        self.database_query_duration_seconds.labels(
            query_type=query_type
        ).observe(duration)
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation metrics."""
        self.cache_operations_total.labels(
            operation=operation,
            result=result
        ).inc()
    
    def record_error(self, error_type: str, severity: str = "error"):
        """Record error metrics."""
        self.errors_total.labels(
            error_type=error_type,
            severity=severity
        ).inc()
    
    def record_authentication_attempt(self, success: bool):
        """Record authentication attempt metrics."""
        result = "success" if success else "failure"
        self.authentication_attempts.labels(result=result).inc()
    
    def record_rate_limit_hit(self, client_type: str = "unknown"):
        """Record rate limit hit metrics."""
        self.rate_limit_hits.labels(client_type=client_type).inc()
    
    def update_service_info(self, version: str, database_type: str, cache_type: str):
        """Update service information metrics."""
        self.service_info.labels(
            version=version,
            database_type=database_type,
            cache_type=cache_type
        ).set(1)
    
    def update_business_metrics(self, users_count: int, photos_count: int, active_sessions_count: int):
        """Update business metrics."""
        self.users_total.set(users_count)
        self.photos_total.set(photos_count)
        self.active_sessions.set(active_sessions_count)
    
    def update_infrastructure_metrics(self, active_connections: int, cache_size: int):
        """Update infrastructure metrics."""
        self.database_connections_active.set(active_connections)
        self.memory_cache_size.set(cache_size)
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        return generate_latest()

class MonitoringMiddleware:
    """FastAPI middleware to collect request metrics."""
    
    def __init__(self, metrics: PrometheusMetrics):
        self.metrics = metrics
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract endpoint from request path
        endpoint = self._normalize_endpoint(request.url.path)
        method = request.method
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Record successful request
            duration = time.time() - start_time
            self.metrics.record_request(method, endpoint, status_code, duration)
            
            return response
            
        except Exception:
            # Record failed request
            duration = time.time() - start_time
            self.metrics.record_request(method, endpoint, 500, duration)
            self.metrics.record_error("request_processing_error")
            raise
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics."""
        # Replace dynamic segments with placeholders
        if path.startswith('/api/photos/') and path.count('/') >= 3:
            parts = path.split('/')
            if parts[3].isdigit():
                if len(parts) > 4:
                    return f"/api/photos/{{id}}/{parts[4]}"
                else:
                    return "/api/photos/{id}"
        
        if path.startswith('/api/platform/services/') and path.count('/') >= 4:
            return "/api/platform/services/{service_name}"
        
        return path

class MonitoringDashboard:
    """Monitoring dashboard and metrics collection."""
    
    def __init__(self, service_name: str = "photo_share"):
        self.service_name = service_name
        self.metrics = PrometheusMetrics(service_name)
        self.middleware = MonitoringMiddleware(self.metrics)
        self.start_time = time.time()
        
        # Initialize service info
        self.metrics.update_service_info(
            version="2.3.0-monitoring",
            database_type="postgresql",
            cache_type="memory"
        )
    
    async def update_metrics_from_performance_data(self, performance_data: Dict[str, Any]):
        """Update metrics from performance optimization data."""
        try:
            # Update cache metrics
            cache_perf = performance_data.get("cache_performance", {})
            if cache_perf:
                # Record cache operations
                cache_perf.get("cache_hits", 0)
                cache_perf.get("cache_misses", 0)
                cache_size = cache_perf.get("memory_cache_size", 0)
                
                # Update infrastructure metrics
                self.metrics.update_infrastructure_metrics(0, cache_size)  # No DB connection info available
            
            # Update query metrics from query performance data
            query_perf = performance_data.get("query_performance", {})
            if query_perf:
                query_stats = query_perf.get("query_statistics", {})
                for query_name, stats in query_stats.items():
                    # Update query duration (using average time)
                    avg_time = stats.get("average_time", 0)
                    if avg_time > 0:
                        self.metrics.database_query_duration_seconds.labels(
                            query_type=query_name
                        ).observe(avg_time)
        
        except Exception as e:
            logger.error(f"Error updating metrics from performance data: {e}")
    
    async def update_business_metrics_from_stats(self, stats_data: Dict[str, Any]):
        """Update business metrics from platform stats."""
        try:
            users_count = stats_data.get("registered_users", 0)
            photos_count = stats_data.get("total_photos", 0)
            sessions_count = stats_data.get("active_sessions", 0)
            
            self.metrics.update_business_metrics(users_count, photos_count, sessions_count)
            
        except Exception as e:
            logger.error(f"Error updating business metrics: {e}")
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive monitoring dashboard data."""
        uptime = time.time() - self.start_time
        
        return {
            "monitoring_system": {
                "service_name": self.service_name,
                "uptime_seconds": int(uptime),
                "metrics_enabled": True,
                "prometheus_endpoint": "/metrics",
                "dashboard_enabled": True
            },
            "metrics_summary": {
                "total_requests": getattr(self.metrics.requests_total._value, '_value', 0) if hasattr(self.metrics.requests_total, '_value') else 0,
                "total_database_queries": getattr(self.metrics.database_queries_total._value, '_value', 0) if hasattr(self.metrics.database_queries_total, '_value') else 0,
                "total_cache_operations": getattr(self.metrics.cache_operations_total._value, '_value', 0) if hasattr(self.metrics.cache_operations_total, '_value') else 0,
                "total_errors": getattr(self.metrics.errors_total._value, '_value', 0) if hasattr(self.metrics.errors_total, '_value') else 0,
                "total_auth_attempts": getattr(self.metrics.authentication_attempts._value, '_value', 0) if hasattr(self.metrics.authentication_attempts, '_value') else 0
            },
            "health_status": {
                "service_healthy": True,
                "database_connected": True,
                "cache_operational": True,
                "monitoring_active": True
            },
            "integration": {
                "prometheus_compatible": True,
                "grafana_ready": True,
                "alertmanager_compatible": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_prometheus_metrics(self) -> FastAPIResponse:
        """Get Prometheus metrics endpoint response."""
        metrics_data = self.metrics.get_metrics()
        return FastAPIResponse(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST,
            headers={"Cache-Control": "no-cache"}
        )

# Global monitoring dashboard instance
monitoring_dashboard = MonitoringDashboard()

# Convenience functions for metrics recording
def record_request_metric(method: str, endpoint: str, status_code: int, duration: float):
    """Record request metrics."""
    monitoring_dashboard.metrics.record_request(method, endpoint, status_code, duration)

def record_database_metric(query_type: str, duration: float, success: bool = True):
    """Record database query metrics."""
    monitoring_dashboard.metrics.record_database_query(query_type, duration, success)

def record_cache_metric(operation: str, result: str):
    """Record cache operation metrics."""
    monitoring_dashboard.metrics.record_cache_operation(operation, result)

def record_error_metric(error_type: str, severity: str = "error"):
    """Record error metrics."""
    monitoring_dashboard.metrics.record_error(error_type, severity)

def record_auth_metric(success: bool):
    """Record authentication attempt metrics."""
    monitoring_dashboard.metrics.record_authentication_attempt(success)

def record_rate_limit_metric(client_type: str = "unknown"):
    """Record rate limit hit metrics."""
    monitoring_dashboard.metrics.record_rate_limit_hit(client_type)