#!/usr/bin/env python3
"""
Enhanced Error Handling and Logging
===================================

Provides comprehensive error handling, logging, and monitoring capabilities.
"""

import logging
import traceback
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import asyncio

class ErrorHandler:
    """Centralized error handling and logging with enhanced validation."""
    
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
        self.max_history = 100
        self.validation_errors = []
        self.error_trends = {}
        
        # Setup structured logging
        self.setup_logging()
    
    def setup_logging(self):
        """Configure structured logging."""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", '
            '"file": "%(filename)s", "line": %(lineno)d, "message": "%(message)s"}'
        )
        
        # Get root logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Console handler with detailed format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_formatter)
        logger.addHandler(console_handler)
        
        # Error file handler (JSON format for parsing)
        try:
            error_handler = logging.FileHandler('/tmp/photo_share_errors.log')
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(json_formatter)
            logger.addHandler(error_handler)
        except Exception:
            # If file logging fails, continue with console only
            pass
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Log error with context and update statistics."""
        logger = logging.getLogger(__name__)
        
        # Update error counts
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Create error record
        error_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "count": self.error_counts[error_type]
        }
        
        # Add to history
        self.error_history.append(error_record)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)
        
        # Log the error
        logger.error(f"{error_type}: {error_message} | Context: {context}")
        
        return error_record
    
    def _categorize_error(self, status_code: int, error_type: str) -> str:
        """Categorize errors for better client handling."""
        if status_code == 400:
            return "CLIENT_ERROR"
        elif status_code == 401:
            return "AUTHENTICATION_ERROR"
        elif status_code == 403:
            return "AUTHORIZATION_ERROR"
        elif status_code == 404:
            return "NOT_FOUND_ERROR"
        elif status_code == 409:
            return "CONFLICT_ERROR"
        elif status_code == 413:
            return "PAYLOAD_TOO_LARGE"
        elif status_code == 422:
            return "VALIDATION_ERROR"
        elif status_code == 429:
            return "RATE_LIMIT_ERROR"
        elif 500 <= status_code < 600:
            return "SERVER_ERROR"
        else:
            return "UNKNOWN_ERROR"
    
    def _get_error_suggestions(self, status_code: int, error_type: str) -> List[str]:
        """Provide helpful suggestions based on error type."""
        suggestions = []
        
        if status_code == 400:
            suggestions = ["Check request format and required fields", "Validate input data types"]
        elif status_code == 401:
            suggestions = ["Verify authentication credentials", "Check if token is expired", "Ensure proper authorization header"]
        elif status_code == 403:
            suggestions = ["Verify user permissions", "Check resource access rights"]
        elif status_code == 404:
            suggestions = ["Verify resource ID or path", "Check if resource exists"]
        elif status_code == 409:
            suggestions = ["Check for duplicate resources", "Verify unique constraints"]
        elif status_code == 413:
            suggestions = ["Reduce file size", "Check upload limits"]
        elif status_code == 422:
            suggestions = ["Validate input format", "Check required fields", "Verify data types"]
        elif status_code == 429:
            suggestions = ["Reduce request frequency", "Implement backoff strategy", "Check rate limits"]
        elif 500 <= status_code < 600:
            suggestions = ["Try again later", "Contact support if problem persists"]
        
        return suggestions
    
    def _calculate_error_trends(self) -> Dict[str, Any]:
        """Calculate error trends over time."""
        if not self.error_history:
            return {}
        
        now = datetime.now(timezone.utc)
        trends = {}
        
        # Group errors by hour for the last 24 hours
        for i in range(24):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)
            
            hour_errors = [e for e in self.error_history if 
                          hour_start <= datetime.fromisoformat(e["timestamp"].replace('Z', '+00:00')) < hour_end]
            
            trends[f"hour_{i}"] = len(hour_errors)
        
        return trends
    
    def _analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns for insights."""
        if not self.error_history:
            return {}
        
        patterns = {}
        
        # Most common error types
        error_type_counts = {}
        for error in self.error_history[-100:]:  # Last 100 errors
            error_type = error.get("error_type", "UNKNOWN")
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
        
        patterns["most_common_errors"] = sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Error frequency analysis
        if len(self.error_history) > 1:
            recent_errors = self.error_history[-10:]
            time_diffs = []
            for i in range(1, len(recent_errors)):
                prev_time = datetime.fromisoformat(recent_errors[i-1]["timestamp"].replace('Z', '+00:00'))
                curr_time = datetime.fromisoformat(recent_errors[i]["timestamp"].replace('Z', '+00:00'))
                time_diffs.append((curr_time - prev_time).total_seconds())
            
            if time_diffs:
                patterns["average_error_interval"] = sum(time_diffs) / len(time_diffs)
                patterns["error_frequency_trend"] = "increasing" if time_diffs[-1] < time_diffs[0] else "decreasing"
        
        return patterns
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        total_errors = sum(self.error_counts.values())
        
        # Calculate error trends
        recent_errors = [e for e in self.error_history if 
                        datetime.fromisoformat(e["timestamp"].replace('Z', '+00:00')) > 
                        datetime.now(timezone.utc) - timedelta(hours=1)]
        
        validation_errors = [e for e in self.error_history if e["error_type"] == "VALIDATION_ERROR"]
        
        return {
            "total_errors": total_errors,
            "error_types": dict(self.error_counts),
            "recent_errors": self.error_history[-10:] if self.error_history else [],
            "hourly_error_rate": len(recent_errors),
            "validation_errors_count": len(validation_errors),
            "top_error_types": sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "error_trends": self._calculate_error_trends(),
            "error_patterns": self._analyze_error_patterns()
        }
    
    def create_error_response(self, status_code: int, error_type: str, 
                            message: str, details: Dict[str, Any] = None) -> JSONResponse:
        """Create standardized error response with enhanced format."""
        error_record = self.log_error(error_type, message, details)
        
        # Determine error category for better client handling
        error_category = self._categorize_error(status_code, error_type)
        
        response_data = {
            "success": False,
            "error": {
                "type": error_type,
                "category": error_category,
                "message": message,
                "status_code": status_code,
                "timestamp": error_record["timestamp"],
                "request_id": error_record.get("request_id", ""),
                "details": details or {},
                "suggestions": self._get_error_suggestions(status_code, error_type)
            },
            "data": None
        }
        
        # Add CORS headers for error responses
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "X-Error-Type": error_type,
            "X-Error-Category": error_category
        }
        
        return JSONResponse(
            status_code=status_code,
            content=response_data,
            headers=headers
        )

# Global error handler instance
error_handler = ErrorHandler()

# Exception handlers for FastAPI
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    context = {
        "method": request.method,
        "url": str(request.url),
        "status_code": exc.status_code
    }
    
    return error_handler.create_error_response(
        status_code=exc.status_code,
        error_type="HTTP_EXCEPTION",
        message=exc.detail,
        details=context
    )

async def starlette_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette HTTP exceptions."""
    context = {
        "method": request.method,
        "url": str(request.url),
        "status_code": exc.status_code
    }
    
    return error_handler.create_error_response(
        status_code=exc.status_code,
        error_type="STARLETTE_HTTP_EXCEPTION", 
        message=exc.detail,
        details=context
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    # Convert validation errors to JSON-serializable format
    validation_errors = []
    for error in exc.errors():
        # Ensure all values are JSON serializable
        clean_error = {
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": str(error["msg"]),
            "type": str(error["type"])
        }
        # Handle any bytes objects in input
        if "input" in error and isinstance(error["input"], bytes):
            clean_error["input"] = error["input"].decode('utf-8', errors='replace')
        elif "input" in error:
            clean_error["input"] = str(error["input"])
        validation_errors.append(clean_error)
    
    context = {
        "method": request.method,
        "url": str(request.url),
        "validation_errors": validation_errors
    }
    
    return error_handler.create_error_response(
        status_code=422,
        error_type="VALIDATION_ERROR", 
        message="Request validation failed",
        details={
            "validation_errors": validation_errors,
            "request_info": context
        }
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    context = {
        "method": request.method,
        "url": str(request.url),
        "exception_type": type(exc).__name__,
        "traceback": traceback.format_exc()
    }
    
    return error_handler.create_error_response(
        status_code=500,
        error_type="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        details=context
    )

class DatabaseErrorHandler:
    """Specialized error handling for database operations."""
    
    @staticmethod
    def handle_db_connection_error(error: Exception) -> HTTPException:
        """Handle database connection errors."""
        error_handler.log_error(
            "DATABASE_CONNECTION_ERROR",
            str(error),
            {"error_type": type(error).__name__}
        )
        
        return HTTPException(
            status_code=503,
            detail="Database service temporarily unavailable"
        )
    
    @staticmethod
    def handle_db_query_error(error: Exception, query_context: str = None) -> HTTPException:
        """Handle database query errors."""
        error_handler.log_error(
            "DATABASE_QUERY_ERROR",
            str(error),
            {
                "error_type": type(error).__name__,
                "query_context": query_context
            }
        )
        
        return HTTPException(
            status_code=500,
            detail="Database operation failed"
        )
    
    @staticmethod
    def handle_db_constraint_error(error: Exception) -> HTTPException:
        """Handle database constraint violations."""
        error_handler.log_error(
            "DATABASE_CONSTRAINT_ERROR",
            str(error),
            {"error_type": type(error).__name__}
        )
        
        # Try to provide user-friendly messages for common constraints
        error_msg = str(error).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            return HTTPException(
                status_code=409,
                detail="Resource already exists"
            )
        elif "foreign key" in error_msg:
            return HTTPException(
                status_code=400,
                detail="Invalid reference to related resource"
            )
        else:
            return HTTPException(
                status_code=400,
                detail="Data constraint violation"
            )

class AuthenticationErrorHandler:
    """Specialized error handling for authentication."""
    
    @staticmethod
    def handle_invalid_credentials() -> HTTPException:
        """Handle invalid login credentials."""
        error_handler.log_error(
            "AUTHENTICATION_FAILED",
            "Invalid credentials provided"
        )
        
        return HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
    
    @staticmethod
    def handle_invalid_token(token_error: str = None) -> HTTPException:
        """Handle invalid JWT tokens."""
        error_handler.log_error(
            "INVALID_TOKEN",
            token_error or "Invalid or expired token"
        )
        
        return HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    
    @staticmethod
    def handle_insufficient_permissions(required_permission: str = None) -> HTTPException:
        """Handle insufficient permissions."""
        error_handler.log_error(
            "INSUFFICIENT_PERMISSIONS",
            f"Access denied - required permission: {required_permission}"
        )
        
        return HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )

class FileStorageErrorHandler:
    """Specialized error handling for file storage operations."""
    
    @staticmethod
    def handle_file_upload_error(error: Exception, filename: str = None) -> HTTPException:
        """Handle file upload errors."""
        error_handler.log_error(
            "FILE_UPLOAD_ERROR",
            str(error),
            {"filename": filename, "error_type": type(error).__name__}
        )
        
        return HTTPException(
            status_code=500,
            detail="File upload failed"
        )
    
    @staticmethod
    def handle_file_not_found(filename: str) -> HTTPException:
        """Handle file not found errors."""
        error_handler.log_error(
            "FILE_NOT_FOUND",
            f"File not found: {filename}"
        )
        
        return HTTPException(
            status_code=404,
            detail="File not found"
        )
    
    @staticmethod
    def handle_file_size_error(file_size: int, max_size: int) -> HTTPException:
        """Handle file size limit errors."""
        error_handler.log_error(
            "FILE_SIZE_LIMIT_EXCEEDED",
            f"File size {file_size} exceeds limit {max_size}"
        )
        
        return HTTPException(
            status_code=413,
            detail=f"File too large (max: {max_size // (1024*1024)}MB)"
        )

class PerformanceMonitor:
    """Monitor and log performance metrics."""
    
    def __init__(self):
        self.request_times = []
        self.slow_requests = []
        self.max_history = 1000
        self.slow_threshold = 2.0  # seconds
    
    def log_request_time(self, method: str, path: str, duration: float, status_code: int):
        """Log request timing information."""
        request_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "path": path,
            "duration": duration,
            "status_code": status_code
        }
        
        self.request_times.append(request_info)
        if len(self.request_times) > self.max_history:
            self.request_times.pop(0)
        
        # Track slow requests
        if duration > self.slow_threshold:
            self.slow_requests.append(request_info)
            if len(self.slow_requests) > 50:  # Keep last 50 slow requests
                self.slow_requests.pop(0)
            
            error_handler.log_error(
                "SLOW_REQUEST",
                f"Slow request: {method} {path} took {duration:.2f}s",
                request_info
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.request_times:
            return {"message": "No requests recorded"}
        
        durations = [r["duration"] for r in self.request_times]
        
        return {
            "total_requests": len(self.request_times),
            "average_response_time": sum(durations) / len(durations),
            "min_response_time": min(durations),
            "max_response_time": max(durations),
            "slow_requests_count": len(self.slow_requests),
            "slow_threshold": self.slow_threshold,
            "recent_slow_requests": self.slow_requests[-5:] if self.slow_requests else []
        }

# Global performance monitor
performance_monitor = PerformanceMonitor()