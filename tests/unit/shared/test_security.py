#!/usr/bin/env python3
"""
Unit tests for shared security utilities.
"""
import pytest
import time
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from services.shared.security import RateLimiter, SecurityMiddleware

class TestRateLimiter:
    """Test Rate Limiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with test settings."""
        return RateLimiter(requests_per_minute=60, burst_limit=10)
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-browser"}
        return request
    
    def test_rate_limiter_creation(self, rate_limiter):
        """Test rate limiter initialization."""
        assert rate_limiter.requests_per_minute == 60
        assert rate_limiter.burst_limit == 10
        assert len(rate_limiter.requests) == 0
        assert len(rate_limiter.blocked_ips) == 0
    
    def test_get_client_id(self, rate_limiter, mock_request):
        """Test client ID generation."""
        client_id = rate_limiter._get_client_id(mock_request)
        
        assert isinstance(client_id, str)
        assert len(client_id) == 32  # MD5 hash length
        
        # Same request should generate same client ID
        client_id2 = rate_limiter._get_client_id(mock_request)
        assert client_id == client_id2
    
    def test_rate_limit_under_limit(self, rate_limiter, mock_request):
        """Test rate limiting when under the limit."""
        is_limited, info = rate_limiter.is_rate_limited(mock_request, max_requests=10, window_minutes=1)
        
        assert is_limited is False
        assert "requests_remaining" in info
        assert info["requests_remaining"] == 9  # 10 - 1 (current request)
        assert "reset_time" in info
    
    def test_rate_limit_at_limit(self, rate_limiter, mock_request):
        """Test rate limiting when at the limit."""
        # Make requests up to the limit
        max_requests = 5
        for _ in range(max_requests):
            is_limited, info = rate_limiter.is_rate_limited(mock_request, max_requests=max_requests, window_minutes=1)
        
        # Next request should be limited
        is_limited, info = rate_limiter.is_rate_limited(mock_request, max_requests=max_requests, window_minutes=1)
        
        assert is_limited is True
        assert info["error"] == "Rate limit exceeded"
        assert info["max_requests"] == max_requests
        assert "current_requests" in info
    
    def test_rate_limit_ip_blocking(self, rate_limiter, mock_request):
        """Test IP blocking for excessive requests."""
        max_requests = 3  
        current_time = time.time()
        client_id = rate_limiter._get_client_id(mock_request)
        
        # Manually simulate a situation where there are already 2x max_requests in the time window
        # This simulates the case where requests came in so fast they all recorded before rate limiting
        excessive_requests = [current_time - i for i in range(max_requests * 2)]  # 6 requests
        rate_limiter.requests[client_id] = excessive_requests
        
        # Now when we check rate limiting, IP should get blocked
        is_limited, info = rate_limiter.is_rate_limited(mock_request, max_requests=max_requests, window_minutes=1)
        
        # Should be rate limited and IP should be blocked
        assert is_limited is True
        assert mock_request.client.host in rate_limiter.blocked_ips
        
        # Subsequent requests should be blocked due to IP blocking
        is_limited, info = rate_limiter.is_rate_limited(mock_request, max_requests=max_requests, window_minutes=1)
        
        assert is_limited is True
        assert info["error"] == "IP temporarily blocked"
        assert "blocked_until" in info
    
    def test_rate_limit_different_clients(self, rate_limiter):
        """Test rate limiting with different clients."""
        request1 = Mock()
        request1.client = Mock()
        request1.client.host = "127.0.0.1"
        request1.headers = {"user-agent": "browser1"}
        
        request2 = Mock()
        request2.client = Mock()
        request2.client.host = "127.0.0.2"
        request2.headers = {"user-agent": "browser2"}
        
        # Both clients should be able to make requests independently
        is_limited1, _ = rate_limiter.is_rate_limited(request1, max_requests=2, window_minutes=1)
        is_limited2, _ = rate_limiter.is_rate_limited(request2, max_requests=2, window_minutes=1)
        
        assert is_limited1 is False
        assert is_limited2 is False
        
        # Each should have their own rate limit tracking
        assert len(rate_limiter.requests) == 2
    
    def test_cleanup_old_requests(self, rate_limiter, mock_request):
        """Test cleanup of old request records."""
        # Make some requests
        rate_limiter.is_rate_limited(mock_request, max_requests=10, window_minutes=1)
        
        # Manually trigger cleanup by setting last_cleanup to old time
        rate_limiter.last_cleanup = time.time() - 400  # More than cleanup_interval (300s)
        
        # Force cleanup by making another request
        rate_limiter.is_rate_limited(mock_request, max_requests=10, window_minutes=1)
        
        # Cleanup should have been triggered (last_cleanup updated)
        assert rate_limiter.last_cleanup > time.time() - 10  # Recent cleanup
    
    def test_get_rate_limit_stats(self, rate_limiter, mock_request):
        """Test rate limit statistics."""
        # Make some requests
        rate_limiter.is_rate_limited(mock_request, max_requests=10, window_minutes=1)
        
        stats = rate_limiter.get_rate_limit_stats()
        
        assert "active_clients" in stats
        assert "blocked_ips" in stats
        assert "total_tracked_requests" in stats
        assert "blocked_until" in stats
        
        assert stats["active_clients"] >= 1
        assert stats["total_tracked_requests"] >= 1

class TestSecurityMiddleware:
    """Test Security Middleware functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for middleware."""
        return RateLimiter(requests_per_minute=60, burst_limit=10)
    
    @pytest.fixture
    def security_middleware(self, rate_limiter):
        """Create security middleware."""
        app = Mock()
        return SecurityMiddleware(app, rate_limiter=rate_limiter)
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {
            "user-agent": "test-browser",
            "content-length": "100"
        }
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "GET"
        return request
    
    @pytest.mark.asyncio
    async def test_middleware_initialization(self, security_middleware):
        """Test middleware initialization."""
        assert security_middleware.rate_limiter is not None
        assert security_middleware.request_validator is not None
    
    @pytest.mark.asyncio
    async def test_middleware_valid_request(self, security_middleware, mock_request):
        """Test middleware with valid request."""
        # Mock the call_next function to return a proper response
        async def mock_call_next(request):
            response = Mock()
            response.status_code = 200
            response.headers = {}  # Add headers dict for middleware to modify
            return response
        
        # Mock the request validator to return valid
        security_middleware.request_validator.validate_request = AsyncMock(return_value={
            "is_valid": True,
            "threats_detected": [],
            "risk_score": 0
        })
        
        response = await security_middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
    
    @pytest.mark.asyncio  
    async def test_middleware_rate_limited_request(self, security_middleware, mock_request):
        """Test middleware with rate limited request."""
        # Force rate limiting by blocking the IP
        security_middleware.rate_limiter.blocked_ips[mock_request.client.host] = time.time() + 900
        
        async def mock_call_next(request):
            return Mock(status_code=200)
        
        # Mock the request validator to return valid (so we get to rate limiting)
        security_middleware.request_validator.validate_request = AsyncMock(return_value={
            "is_valid": True,
            "threats_detected": [],
            "risk_score": 0
        })
        
        # Should return 429 response due to rate limiting
        response = await security_middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 429