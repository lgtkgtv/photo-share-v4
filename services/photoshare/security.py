#!/usr/bin/env python3
"""
Security Enhancements
====================

Comprehensive security features including rate limiting, input validation,
and security headers.
"""

import asyncio
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Advanced rate limiting with multiple strategies."""
    
    def __init__(self):
        self.requests = {}  # {client_id: [timestamp, ...]}
        self.blocked_ips = {}  # {ip: blocked_until_timestamp}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
    
    def _cleanup_old_requests(self):
        """Remove old request records."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - 3600  # Keep 1 hour of history
        
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > cutoff_time
            ]
            if not self.requests[client_id]:
                del self.requests[client_id]
        
        # Clean up expired blocks
        for ip in list(self.blocked_ips.keys()):
            if self.blocked_ips[ip] < current_time:
                del self.blocked_ips[ip]
        
        self.last_cleanup = current_time
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use IP + User-Agent for more accurate rate limiting
        ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        return hashlib.md5(f"{ip}:{user_agent}".encode()).hexdigest()
    
    def is_rate_limited(self, request: Request, max_requests: int = 100, 
                       window_minutes: int = 60) -> tuple[bool, Dict[str, Any]]:
        """Check if request should be rate limited."""
        self._cleanup_old_requests()
        
        client_id = self._get_client_id(request)
        current_time = time.time()
        window_start = current_time - (window_minutes * 60)
        
        # Check if IP is blocked
        client_ip = request.client.host if request.client else "unknown"
        if client_ip in self.blocked_ips:
            if self.blocked_ips[client_ip] > current_time:
                return True, {
                    "error": "IP temporarily blocked",
                    "blocked_until": datetime.fromtimestamp(self.blocked_ips[client_ip]).isoformat(),
                    "reason": "Excessive requests"
                }
            else:
                del self.blocked_ips[client_ip]
        
        # Get recent requests for this client
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        recent_requests = [
            req_time for req_time in self.requests[client_id]
            if req_time > window_start
        ]
        
        # Check rate limit
        if len(recent_requests) >= max_requests:
            # Block IP for 15 minutes if excessive requests
            if len(recent_requests) >= max_requests * 2:
                self.blocked_ips[client_ip] = current_time + 900  # 15 minutes
                logger.warning(f"IP {client_ip} blocked for excessive requests")
            
            return True, {
                "error": "Rate limit exceeded",
                "max_requests": max_requests,
                "window_minutes": window_minutes,
                "current_requests": len(recent_requests),
                "reset_time": datetime.fromtimestamp(window_start + (window_minutes * 60)).isoformat()
            }
        
        # Record this request
        self.requests[client_id] = recent_requests + [current_time]
        
        return False, {
            "requests_remaining": max_requests - len(recent_requests) - 1,
            "reset_time": datetime.fromtimestamp(window_start + (window_minutes * 60)).isoformat()
        }
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        self._cleanup_old_requests()
        
        return {
            "active_clients": len(self.requests),
            "blocked_ips": len(self.blocked_ips),
            "total_tracked_requests": sum(len(reqs) for reqs in self.requests.values()),
            "blocked_until": [
                {
                    "ip": ip,
                    "blocked_until": datetime.fromtimestamp(until).isoformat()
                }
                for ip, until in self.blocked_ips.items()
            ]
        }

class SecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware with request validation and protection."""
    
    def __init__(self, app, rate_limiter: RateLimiter = None, request_validator: "RequestValidationMiddleware" = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self.request_validator = request_validator or RequestValidationMiddleware()
        
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Apply request validation first
        validation_result = await self.request_validator.validate_request(request)
        
        if not validation_result["is_valid"]:
            # Log security event
            security_audit.log_security_event(
                "MALICIOUS_REQUEST_BLOCKED",
                {
                    "client_ip": self.request_validator._get_client_ip(request),
                    "threats_detected": validation_result["threats_detected"],
                    "risk_score": validation_result["risk_score"],
                    "url": str(request.url),
                    "method": request.method,
                    "user_agent": request.headers.get("user-agent", "unknown")
                },
                "critical" if validation_result["risk_score"] > 50 else "warning"
            )
            
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "type": "SECURITY_VIOLATION",
                        "category": "BLOCKED_REQUEST",
                        "message": "Request blocked due to security policy violation",
                        "status_code": 403,
                        "details": {
                            "threats_detected": validation_result["threats_detected"],
                            "risk_score": validation_result["risk_score"]
                        },
                        "suggestions": ["Ensure request contains no malicious content", "Contact support if this is an error"]
                    }
                },
                headers={
                    "X-Security-Block-Reason": ",".join(validation_result["threats_detected"]),
                    "X-Risk-Score": str(validation_result["risk_score"])
                }
            )
        
        # Apply rate limiting
        is_limited, limit_info = self.rate_limiter.is_rate_limited(request)
        
        if is_limited:
            return Response(
                content=f'{{"error": "{limit_info["error"]}", "details": {limit_info}}}',
                status_code=429,
                headers={"Content-Type": "application/json"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Enhanced security headers
        path = str(request.url.path)
        
        # Core security headers for all endpoints
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Path-specific security headers
        if path.startswith('/api/'):
            # Strict security for API endpoints
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            
            # Additional API security headers
            response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
            
        elif path in ['/docs', '/redoc', '/openapi.json']:
            # Relaxed for documentation
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data: https:; "
                "style-src 'self' 'unsafe-inline' https:; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
                "font-src 'self' https:"
            )
            
        elif path in ['/health', '/metrics']:
            # Minimal headers for monitoring endpoints
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Cache-Control"] = "no-cache, max-age=0"
            
        else:
            # Default security for other endpoints
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        
        # HSTS only if HTTPS is detected
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Permission Policy for privacy protection
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "speaker=(), vibrate=(), fullscreen=(self), "
            "accelerometer=(), ambient-light-sensor=(), autoplay=(), "
            "battery=(), display-capture=(), document-domain=(), "
            "encrypted-media=(), execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), wake-lock=(), "
            "web-share=(), xr-spatial-tracking=()"
        )
        
        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(limit_info.get("requests_remaining", 0))
        response.headers["X-RateLimit-Reset"] = limit_info.get("reset_time", "")
        
        # Add performance header
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        
        return response

class RequestValidationMiddleware:
    """Comprehensive request/response validation middleware."""
    
    def __init__(self):
        self.validation_stats = {
            "total_requests": 0,
            "validation_failures": 0,
            "suspicious_requests": 0,
            "blocked_requests": 0
        }
        self.blocked_ips = set()
        self.suspicious_patterns = [
            r"<script[^>]*>",  # Script injection
            r"javascript:",   # JavaScript protocol
            r"vbscript:",     # VBScript protocol
            r"on\w+\s*=",     # Event handlers
            r"\.\.[\/\\]",    # Path traversal
            r"union\s+select", # SQL injection
            r"drop\s+table",  # SQL injection
            r"exec\s*\(",     # Code execution
            r"eval\s*\(",     # Code evaluation
        ]
    
    async def validate_request(self, request: Request) -> Dict[str, Any]:
        """Validate incoming request for security threats."""
        self.validation_stats["total_requests"] += 1
        validation_result = {
            "is_valid": True,
            "threats_detected": [],
            "risk_score": 0,
            "blocked": False
        }
        
        # Check if IP is blocked
        client_ip = self._get_client_ip(request)
        if client_ip in self.blocked_ips:
            validation_result["is_valid"] = False
            validation_result["blocked"] = True
            validation_result["threats_detected"].append("BLOCKED_IP")
            self.validation_stats["blocked_requests"] += 1
            return validation_result
        
        # Validate headers
        header_threats = self._validate_headers(request.headers)
        validation_result["threats_detected"].extend(header_threats)
        validation_result["risk_score"] += len(header_threats) * 10
        
        # Validate URL and query parameters
        url_threats = self._validate_url(str(request.url))
        validation_result["threats_detected"].extend(url_threats)
        validation_result["risk_score"] += len(url_threats) * 15
        
        # Validate body content if present
        if request.method in ["POST", "PUT", "PATCH"]:
            body_threats = await self._validate_body(request)
            validation_result["threats_detected"].extend(body_threats)
            validation_result["risk_score"] += len(body_threats) * 20
        
        # Check for suspicious patterns
        if validation_result["threats_detected"] or validation_result["risk_score"] > 30:
            validation_result["is_valid"] = False
            self.validation_stats["validation_failures"] += 1
            
            if validation_result["risk_score"] > 50:
                self.validation_stats["suspicious_requests"] += 1
                # Temporarily block IP for high-risk requests
                self.blocked_ips.add(client_ip)
        
        return validation_result
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _validate_headers(self, headers) -> List[str]:
        """Validate request headers for threats."""
        threats = []
        
        # Check for suspicious user agents
        user_agent = headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "masscan", "zap", "burp"]
        if any(agent in user_agent for agent in suspicious_agents):
            threats.append("SUSPICIOUS_USER_AGENT")
        
        # Check for malicious headers
        for name, value in headers.items():
            if any(pattern in value.lower() for pattern in ["<script", "javascript:", "vbscript:"]):
                threats.append(f"MALICIOUS_HEADER_{name.upper()}")
        
        return threats
    
    def _validate_url(self, url: str) -> List[str]:
        """Validate URL for threats."""
        threats = []
        url_lower = url.lower()
        
        # Check for path traversal
        if "../" in url or "..\\" in url:
            threats.append("PATH_TRAVERSAL")
        
        # Check for suspicious patterns
        import re
        for pattern in self.suspicious_patterns:
            if re.search(pattern, url_lower, re.IGNORECASE):
                threats.append(f"SUSPICIOUS_PATTERN_{pattern[:10]}")
        
        return threats
    
    async def _validate_body(self, request: Request) -> List[str]:
        """Validate request body for threats."""
        threats = []
        
        try:
            # Get content type
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                # For JSON, we'll check during parsing
                pass
            elif "multipart/form-data" in content_type:
                # File upload validation handled separately
                pass
            elif "application/x-www-form-urlencoded" in content_type:
                # Form data validation
                form_data = await request.form()
                for key, value in form_data.items():
                    if isinstance(value, str) and self._contains_malicious_content(value):
                        threats.append(f"MALICIOUS_FORM_DATA_{key}")
        
        except Exception:
            # If body parsing fails, it might be malicious
            threats.append("MALFORMED_BODY")
        
        return threats
    
    def _contains_malicious_content(self, content: str) -> bool:
        """Check if content contains malicious patterns."""
        import re
        content_lower = content.lower()
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        return False
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        stats = dict(self.validation_stats)
        stats["blocked_ips_count"] = len(self.blocked_ips)
        stats["validation_success_rate"] = (
            (stats["total_requests"] - stats["validation_failures"]) / 
            max(stats["total_requests"], 1)
        ) * 100
        return stats
    
    def clear_blocked_ips(self):
        """Clear blocked IPs (for periodic cleanup)."""
        self.blocked_ips.clear()

class InputValidator:
    """Enhanced input validation and sanitization."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format and security."""
        if not email or len(email) > 254:
            return False
        
        # Basic format check
        if email.count("@") != 1:
            return False
        
        local, domain = email.split("@")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            "../", "script", "<", ">", "javascript:", "data:",
            "\\", "'", '"', ";", "--", "/*", "*/"
        ]
        
        email_lower = email.lower()
        for pattern in suspicious_patterns:
            if pattern in email_lower:
                return False
        
        return True
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, List[str]]:
        """Validate password strength."""
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if len(password) > 128:
            issues.append("Password must be less than 128 characters")
        
        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one number")
        
        # Check for common weak passwords
        weak_passwords = [
            "password", "123456", "123456789", "qwerty", "abc123",
            "password123", "admin", "letmein", "welcome", "monkey"
        ]
        
        if password.lower() in weak_passwords:
            issues.append("Password is too common")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize file names for security."""
        if not filename:
            return "unnamed_file"
        
        # Remove path traversal attempts
        filename = filename.replace("../", "").replace("..\\", "")
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        return filename
    
    @staticmethod
    def validate_file_upload(file_content: bytes, content_type: str, max_size: int = 50 * 1024 * 1024) -> tuple[bool, str]:
        """Validate uploaded file for security - PHOTOS ONLY."""
        # Check file size
        if len(file_content) > max_size:
            return False, f"File too large (max: {max_size // (1024*1024)}MB)"
        
        # STRICT: Only allow image files for photo sharing service
        allowed_content_types = [
            "image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"
        ]
        
        if content_type not in allowed_content_types:
            return False, f"Invalid file type. Only images allowed: {', '.join(allowed_content_types)}"
        
        # Check for malicious content in file headers (expanded list)
        malicious_signatures = [
            b"<script", b"javascript:", b"<iframe", b"<object",
            b"<?php", b"<%", b"<html", b"<body", b"<svg", b"<xml",
            b"#!/bin/", b"#!/usr/bin/", b"<embed", b"<link",
            b"data:text/", b"data:application/"
        ]
        
        file_start = file_content[:2048].lower()  # Check first 2KB
        for signature in malicious_signatures:
            if signature in file_start:
                return False, "File contains potentially malicious content"
        
        # STRICT: Validate content type matches actual file content (magic number validation)
        image_headers = {
            "image/jpeg": [b"\xFF\xD8\xFF"],
            "image/jpg": [b"\xFF\xD8\xFF"],
            "image/png": [b"\x89PNG\r\n\x1a\n"],
            "image/gif": [b"GIF87a", b"GIF89a"],
            "image/webp": [b"RIFF"]  # WebP starts with RIFF, followed by file size, then WEBP
        }
        
        # Get expected headers for the content type
        expected_headers = image_headers.get(content_type, [])
        if not expected_headers:
            return False, f"Unsupported image format: {content_type}"
        
        # Check if file content starts with valid magic number
        has_valid_header = any(file_content.startswith(header) for header in expected_headers)
        if not has_valid_header:
            return False, f"File content does not match declared type: {content_type}"
        
        # Additional WebP validation
        if content_type == "image/webp":
            if len(file_content) < 12 or file_content[8:12] != b"WEBP":
                return False, "Invalid WebP file format"
        
        # Check minimum file size (prevent empty or tiny malicious files)
        if len(file_content) < 100:
            return False, "File too small to be a valid image"
        
        return True, "File validation passed"
    
    @staticmethod
    def validate_json_input(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate JSON input against schema with security checks."""
        errors = []
        
        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types and values
        field_types = schema.get("fields", {})
        for field, field_schema in field_types.items():
            if field in data:
                value = data[field]
                expected_type = field_schema.get("type")
                
                # Type validation
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field {field} must be a string")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field {field} must be an integer")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field {field} must be a boolean")
                elif expected_type == "email" and not InputValidator.validate_email(value):
                    errors.append(f"Field {field} must be a valid email")
                
                # Length validation for strings
                if isinstance(value, str):
                    min_length = field_schema.get("min_length", 0)
                    max_length = field_schema.get("max_length", 10000)
                    if len(value) < min_length:
                        errors.append(f"Field {field} must be at least {min_length} characters")
                    if len(value) > max_length:
                        errors.append(f"Field {field} must be less than {max_length} characters")
                
                # Security validation for strings
                if isinstance(value, str) and InputValidator._contains_malicious_patterns(value):
                    errors.append(f"Field {field} contains potentially malicious content")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _contains_malicious_patterns(text: str) -> bool:
        """Check for malicious patterns in text input."""
        malicious_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"vbscript:",
            r"on\w+\s*=",
            r"\.\.[\/\\]",
            r"union\s+select",
            r"drop\s+table",
            r"insert\s+into",
            r"delete\s+from",
            r"exec\s*\(",
            r"eval\s*\(",
            r"<iframe",
            r"<object",
            r"<embed",
            r"data:text/html"
        ]
        
        import re
        text_lower = text.lower()
        for pattern in malicious_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def sanitize_html_input(text: str) -> str:
        """Sanitize HTML input by removing/escaping dangerous elements."""
        if not text:
            return ""
        
        # HTML entity encoding for basic protection
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#x27;")
        text = text.replace("/", "&#x2F;")
        
        return text
    
    @staticmethod
    def validate_numeric_range(value: int, min_val: int = None, max_val: int = None) -> tuple[bool, str]:
        """Validate numeric value is within acceptable range."""
        if min_val is not None and value < min_val:
            return False, f"Value must be at least {min_val}"
        
        if max_val is not None and value > max_val:
            return False, f"Value must be at most {max_val}"
        
        return True, "Valid"

class JWTSecurity:
    """Enhanced JWT security."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.revoked_tokens = set()  # In production, use Redis or database
        self.token_blacklist_cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()
    
    def revoke_token(self, token: str):
        """Revoke a JWT token."""
        self.revoked_tokens.add(token)
        logger.info(f"Token revoked: {token[:20]}...")
    
    def is_token_revoked(self, token: str) -> bool:
        """Check if token is revoked."""
        return token in self.revoked_tokens
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens from blacklist."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.token_blacklist_cleanup_interval:
            return
        
        # In a real implementation, you'd decode tokens and check expiration
        # For now, we'll just clear very old entries periodically
        if len(self.revoked_tokens) > 10000:
            self.revoked_tokens.clear()
            logger.info("Cleared token blacklist")
        
        self.last_cleanup = current_time

class SecurityAudit:
    """Security auditing and monitoring."""
    
    def __init__(self):
        self.security_events = []
        self.max_events = 1000
        
    def log_security_event(self, event_type: str, details: Dict[str, Any], 
                          severity: str = "info", client_ip: str = None):
        """Log security-related events."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "client_ip": client_ip,
            "details": details
        }
        
        self.security_events.append(event)
        if len(self.security_events) > self.max_events:
            self.security_events.pop(0)
        
        # Log to standard logging
        log_level = getattr(logging, severity.upper(), logging.INFO)
        logger.log(log_level, f"Security Event: {event_type} - {details}")
        
        return event
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security audit summary."""
        if not self.security_events:
            return {"message": "No security events recorded"}
        
        # Count events by type and severity
        event_types = {}
        severities = {}
        
        for event in self.security_events:
            event_type = event["event_type"]
            severity = event["severity"]
            
            event_types[event_type] = event_types.get(event_type, 0) + 1
            severities[severity] = severities.get(severity, 0) + 1
        
        return {
            "total_events": len(self.security_events),
            "event_types": event_types,
            "severity_distribution": severities,
            "recent_critical_events": [
                event for event in self.security_events[-50:]
                if event["severity"] in ["critical", "warning"]
            ]
        }

# Global security instances
rate_limiter = RateLimiter()
input_validator = InputValidator()
security_audit = SecurityAudit()
request_validator = RequestValidationMiddleware()

# Security dependency functions
async def require_rate_limit(request: Request, max_requests: int = 100):
    """Dependency to enforce rate limiting."""
    is_limited, limit_info = rate_limiter.is_rate_limited(request, max_requests)
    
    if is_limited:
        security_audit.log_security_event(
            "RATE_LIMIT_EXCEEDED",
            limit_info,
            "warning",
            request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=429,
            detail=limit_info,
            headers={"Retry-After": "60"}
        )
    
    return limit_info

async def validate_file_security(file_content: bytes, content_type: str, filename: str = None):
    """Dependency to validate file uploads."""
    is_valid, message = input_validator.validate_file_upload(file_content, content_type)
    
    if not is_valid:
        security_audit.log_security_event(
            "MALICIOUS_FILE_UPLOAD_ATTEMPT",
            {
                "filename": filename,
                "content_type": content_type,
                "file_size": len(file_content),
                "validation_message": message
            },
            "warning"
        )
        raise HTTPException(status_code=400, detail=message)
    
    return True