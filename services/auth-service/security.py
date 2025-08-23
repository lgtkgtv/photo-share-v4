#!/usr/bin/env python3
"""
Security Middleware and Utilities
==================================

Security utilities for the authentication service including rate limiting,
input validation, and security headers.
"""

import os
import time
import hashlib
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from functools import wraps
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiting implementation for API endpoints."""
    
    def __init__(self):
        # In-memory storage for rate limiting
        # In production, this should use Redis
        self.requests = defaultdict(lambda: deque())
        self.blocked_ips = {}
        
    def is_rate_limited(self, identifier: str, limit: int = 60, window: int = 60) -> bool:
        """
        Check if an identifier (IP, user ID, etc.) is rate limited.
        
        Args:
            identifier: Unique identifier (IP address, user ID, etc.)
            limit: Number of requests allowed in the window
            window: Time window in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        
        # Check if IP is temporarily blocked
        if identifier in self.blocked_ips:
            if current_time < self.blocked_ips[identifier]:
                return True
            else:
                del self.blocked_ips[identifier]
        
        # Clean old requests
        request_times = self.requests[identifier]
        while request_times and request_times[0] <= current_time - window:
            request_times.popleft()
            
        # Check if limit exceeded
        if len(request_times) >= limit:
            # Block for additional time if severely over limit
            if len(request_times) >= limit * 2:
                self.blocked_ips[identifier] = current_time + 300  # 5 minute block
                logger.warning(f"Rate limit severely exceeded for {identifier}, blocking for 5 minutes")
            return True
            
        # Add current request
        request_times.append(current_time)
        return False
    
    def get_rate_limit_info(self, identifier: str, limit: int = 60, window: int = 60) -> Dict[str, Any]:
        """Get rate limiting information for an identifier."""
        current_time = time.time()
        request_times = self.requests[identifier]
        
        # Clean old requests
        while request_times and request_times[0] <= current_time - window:
            request_times.popleft()
            
        remaining = max(0, limit - len(request_times))
        reset_time = int(current_time + window)
        
        return {
            "limit": limit,
            "remaining": remaining,
            "reset": reset_time,
            "window": window
        }

class SecurityMiddleware:
    """Security middleware for authentication service."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        
    async def __call__(self, request: Request, call_next):
        """Apply security middleware to requests."""
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Apply rate limiting based on endpoint
        if await self.should_rate_limit(request, client_ip):
            rate_info = self.rate_limiter.get_rate_limit_info(client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "rate_limit": rate_info
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(rate_info["window"])
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response = self.add_security_headers(response)
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (when behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
            
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
            
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"
    
    async def should_rate_limit(self, request: Request, client_ip: str) -> bool:
        """Determine if request should be rate limited."""
        path = request.url.path
        
        # Different rate limits for different endpoints
        if path.startswith("/api/auth/login"):
            # Stricter limits for login attempts
            return self.rate_limiter.is_rate_limited(f"login:{client_ip}", limit=5, window=60)
        elif path.startswith("/api/auth/register"):
            # Moderate limits for registration
            return self.rate_limiter.is_rate_limited(f"register:{client_ip}", limit=3, window=300)
        elif path.startswith("/api/auth/2fa"):
            # Strict limits for 2FA attempts
            return self.rate_limiter.is_rate_limited(f"2fa:{client_ip}", limit=10, window=300)
        elif path.startswith("/api/auth/"):
            # General auth endpoints
            return self.rate_limiter.is_rate_limited(f"auth:{client_ip}", limit=30, window=60)
        
        # General API limits
        return self.rate_limiter.is_rate_limited(f"api:{client_ip}", limit=100, window=60)
    
    def add_security_headers(self, response):
        """Add security headers to response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    score = 0
    
    # Length check
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    else:
        score += 1
        
    if len(password) >= 12:
        score += 1
        
    # Character type checks
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password)
    
    if not has_upper:
        errors.append("Password must contain at least one uppercase letter")
    else:
        score += 1
        
    if not has_lower:
        errors.append("Password must contain at least one lowercase letter")
    else:
        score += 1
        
    if not has_digit:
        errors.append("Password must contain at least one number")
    else:
        score += 1
        
    if not has_special:
        errors.append("Password must contain at least one special character")
    else:
        score += 1
        
    # Common password check (basic)
    common_passwords = {
        "password", "123456", "password123", "admin", "qwerty",
        "letmein", "welcome", "monkey", "dragon", "master"
    }
    
    if password.lower() in common_passwords:
        errors.append("Password is too common")
        score = max(0, score - 2)
    
    # Determine strength
    if score <= 2:
        strength = "weak"
    elif score <= 4:
        strength = "medium"
    else:
        strength = "strong"
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength": strength,
        "score": score
    }

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash password with salt.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = os.urandom(32).hex()
    
    # Use PBKDF2 for password hashing
    import hashlib
    pwdhash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # 100k iterations
    )
    
    return pwdhash.hex(), salt

def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        password: Plain text password
        hashed_password: Stored hash
        salt: Salt used for hashing
        
    Returns:
        True if password matches, False otherwise
    """
    pwdhash, _ = hash_password(password, salt)
    return pwdhash == hashed_password

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure token."""
    return os.urandom(length).hex()

def validate_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Create global instances
rate_limiter = RateLimiter()
security_middleware = SecurityMiddleware()

def require_rate_limit(limit: int = 60, window: int = 60, key_func=None):
    """Decorator for applying rate limiting to individual endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request found, proceed without rate limiting
                return await func(*args, **kwargs)
            
            # Generate rate limit key
            if key_func:
                key = key_func(request)
            else:
                client_ip = security_middleware.get_client_ip(request)
                key = f"{func.__name__}:{client_ip}"
            
            # Check rate limit
            if rate_limiter.is_rate_limited(key, limit, window):
                rate_info = rate_limiter.get_rate_limit_info(key, limit, window)
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(rate_info["limit"]),
                        "X-RateLimit-Remaining": str(rate_info["remaining"]),
                        "X-RateLimit-Reset": str(rate_info["reset"]),
                        "Retry-After": str(rate_info["window"])
                    }
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator