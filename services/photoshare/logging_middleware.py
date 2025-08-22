#!/usr/bin/env python3
"""
Request/Response Logging Middleware with Correlation IDs
======================================================

Comprehensive logging middleware that provides:
- Request correlation IDs for distributed tracing
- Structured request/response logging
- Performance timing
- Error correlation
- Security event tracking
"""

import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Context variable for correlation ID
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

logger = logging.getLogger(__name__)

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and track correlation IDs across requests.
    
    Adds X-Correlation-ID header to all responses and makes it available
    throughout the request lifecycle via context variables.
    """
    
    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract correlation ID
        corr_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        
        # Set in context for use throughout the request
        correlation_id.set(corr_id)
        
        # Add to request state for easy access
        request.state.correlation_id = corr_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers[self.header_name] = corr_id
        
        return response

class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive request/response logging middleware.
    
    Features:
    - Structured JSON logging
    - Request/response timing
    - Request body logging (with size limits and sensitive data filtering)
    - Response status and timing
    - Error correlation
    - Performance metrics
    """
    
    def __init__(
        self,
        app,
        log_level: str = "INFO",
        max_body_size: int = 10000,  # Max body size to log (bytes)
        sensitive_headers: List[str] = None,
        skip_paths: List[str] = None,
        log_request_body: bool = True,
        log_response_body: bool = False  # Usually too verbose
    ):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper())
        self.max_body_size = max_body_size
        self.sensitive_headers = sensitive_headers or [
            'authorization', 'cookie', 'x-api-key', 'x-auth-token'
        ]
        self.skip_paths = skip_paths or ['/health', '/metrics']
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        
        # Statistics tracking
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.slow_requests = 0  # >1s response time
        self.request_sizes = []
        self.response_sizes = []
    
    def _should_skip_logging(self, path: str) -> bool:
        """Check if path should be skipped from detailed logging."""
        return any(skip_path in path for skip_path in self.skip_paths)
    
    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Filter out sensitive headers for logging."""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value
        return filtered
    
    def _sanitize_body(self, body: bytes) -> Optional[str]:
        """Sanitize request/response body for logging."""
        if not body:
            return None
            
        if len(body) > self.max_body_size:
            return f"<TRUNCATED - {len(body)} bytes>"
        
        try:
            # Try to decode as text
            text = body.decode('utf-8')
            
            # If it looks like JSON, try to parse and filter sensitive data
            if text.strip().startswith(('{', '[')):
                try:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        # Filter sensitive fields
                        sensitive_fields = ['password', 'token', 'secret', 'key']
                        for field in sensitive_fields:
                            if field in data:
                                data[field] = "***REDACTED***"
                    return json.dumps(data)
                except json.JSONDecodeError:
                    pass
            
            return text
        except UnicodeDecodeError:
            return f"<BINARY-DATA - {len(body)} bytes>"
    
    def _get_client_info(self, request: Request) -> Dict[str, Any]:
        """Extract client information from request."""
        client_host = "unknown"
        client_port = None
        
        if request.client:
            client_host = request.client.host
            client_port = request.client.port
        
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            client_host = forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            client_host = real_ip
        
        return {
            "ip": client_host,
            "port": client_port,
            "user_agent": request.headers.get('user-agent', 'unknown'),
            "forwarded_for": request.headers.get('x-forwarded-for'),
            "real_ip": request.headers.get('x-real-ip')
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        correlation_id_value = correlation_id.get()
        
        # Skip detailed logging for certain paths
        skip_detailed = self._should_skip_logging(request.url.path)
        
        # Read request body if needed
        request_body = None
        if self.log_request_body and not skip_detailed and request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body_bytes = await request.body()
                request_body = self._sanitize_body(body_bytes)
            except Exception as e:
                request_body = f"<ERROR reading body: {e}>"
        
        # Prepare request log data
        request_data = {
            "event": "request_start",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id_value,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": self._filter_sensitive_headers(dict(request.headers)),
            "client": self._get_client_info(request)
        }
        
        if request_body:
            request_data["body"] = request_body
            request_data["body_size"] = len(request_body.encode('utf-8'))
        
        # Log request start
        if not skip_detailed:
            logger.log(self.log_level, "Request started", extra={"structured_data": request_data})
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate timing
            response_time = time.time() - start_time
            
            # Update statistics
            self.request_count += 1
            self.total_response_time += response_time
            if response_time > 1.0:
                self.slow_requests += 1
            
            # Read response body if configured
            response_body = None
            if self.log_response_body and not skip_detailed:
                try:
                    # This is tricky with StreamingResponse, so we'll be careful
                    if hasattr(response, 'body'):
                        response_body = self._sanitize_body(response.body)
                except Exception as e:
                    response_body = f"<ERROR reading response body: {e}>"
            
            # Prepare response log data
            response_data = {
                "event": "request_complete",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id_value,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "response_time_ms": round(response_time * 1000, 2),
                "response_headers": dict(response.headers),
            }
            
            if response_body:
                response_data["response_body"] = response_body
            
            # Determine log level based on status code
            if response.status_code >= 500:
                log_level = logging.ERROR
                self.error_count += 1
            elif response.status_code >= 400:
                log_level = logging.WARNING
            else:
                log_level = self.log_level
            
            # Log response
            if not skip_detailed or response.status_code >= 400:
                logger.log(log_level, f"Request completed - {response.status_code}", 
                         extra={"structured_data": response_data})
            
            return response
            
        except Exception as e:
            # Log error
            response_time = time.time() - start_time
            self.error_count += 1
            
            error_data = {
                "event": "request_error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id_value,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "error_type": type(e).__name__,
                "response_time_ms": round(response_time * 1000, 2)
            }
            
            logger.error("Request failed", extra={"structured_data": error_data}, exc_info=True)
            
            # Re-raise the exception
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get middleware statistics."""
        avg_response_time = (
            self.total_response_time / max(self.request_count, 1)
        ) * 1000  # Convert to ms
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": (self.error_count / max(self.request_count, 1)) * 100,
            "average_response_time_ms": round(avg_response_time, 2),
            "slow_requests": self.slow_requests,
            "slow_request_rate": (self.slow_requests / max(self.request_count, 1)) * 100
        }

class StructuredLogger:
    """
    Utility class for structured logging with correlation ID support.
    
    Provides convenient methods for logging with automatic correlation ID inclusion.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_with_correlation(self, level: int, message: str, extra_data: Dict[str, Any] = None):
        """Log message with correlation ID and structured data."""
        structured_data = {
            "correlation_id": correlation_id.get(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if extra_data:
            structured_data.update(extra_data)
        
        self.logger.log(level, message, extra={"structured_data": structured_data})
    
    def info(self, message: str, **kwargs):
        """Log info message with correlation ID."""
        self._log_with_correlation(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with correlation ID."""
        self._log_with_correlation(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with correlation ID."""
        self._log_with_correlation(logging.ERROR, message, kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with correlation ID."""
        self._log_with_correlation(logging.DEBUG, message, kwargs)

class LoggingConfig:
    """
    Centralized logging configuration for the application.
    """
    
    @staticmethod
    def setup_structured_logging():
        """Setup structured logging configuration."""
        import logging.config
        
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structured": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "class": "logging.Formatter"
                },
                "json": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(structured_data)s",
                    "class": "logging.Formatter"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "structured",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "json",
                    "filename": "logs/app.log",
                    "mode": "a",
                    "encoding": "utf-8"
                }
            },
            "loggers": {
                "": {  # Root logger
                    "level": "INFO",
                    "handlers": ["console"]
                },
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["console"],
                    "propagate": False
                },
                "sqlalchemy.engine": {
                    "level": "WARNING",  # Reduce SQL query noise
                    "handlers": ["console"],
                    "propagate": False
                }
            }
        }
        
        # Create logs directory if it doesn't exist
        import os
        os.makedirs("logs", exist_ok=True)
        
        # Add file handler in production
        import os
        if os.getenv("ENVIRONMENT") == "production":
            config["loggers"][""]["handlers"].append("file")
        
        logging.config.dictConfig(config)

# Global middleware instances
correlation_middleware = CorrelationIDMiddleware
request_logging_middleware = RequestResponseLoggingMiddleware

# Utility function to get correlation ID
def get_correlation_id() -> str:
    """Get the current request correlation ID."""
    return correlation_id.get()

# Structured logger factory
def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger for the given name."""
    return StructuredLogger(name)