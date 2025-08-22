"""
Unit tests for security components.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import Request
from fastapi.responses import JSONResponse

from security import (
    RateLimiter, InputValidator, SecurityAudit, JWTSecurity,
    validate_file_security
)


class TestRateLimiter:
    """Test RateLimiter class."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_init(self):
        """Test rate limiter initialization."""
        rate_limiter = RateLimiter(requests_per_minute=100, burst_limit=10)
        
        assert rate_limiter.requests_per_minute == 100
        assert rate_limiter.burst_limit == 10
        assert isinstance(rate_limiter.request_counts, dict)
        assert isinstance(rate_limiter.blocked_ips, dict)

    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self):
        """Test rate limit check for allowed request."""
        rate_limiter = RateLimiter(requests_per_minute=60, burst_limit=10)
        
        result = await rate_limiter.check_rate_limit("192.168.1.1")
        
        assert result is True

    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_check_rate_limit_blocked_ip(self):
        """Test rate limit check for blocked IP."""
        rate_limiter = RateLimiter()
        rate_limiter.blocked_ips.add("192.168.1.1")
        
        result = await rate_limiter.check_rate_limit("192.168.1.1")
        
        assert result is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_get_rate_limit_stats(self):
        """Test getting rate limit statistics."""
        rate_limiter = RateLimiter()
        rate_limiter.request_counts["192.168.1.1"] = [1234567890] * 5
        rate_limiter.blocked_ips.add("192.168.1.2")
        
        stats = rate_limiter.get_rate_limit_stats()
        
        assert "total_requests" in stats
        assert "active_clients" in stats
        assert "blocked_ips_count" in stats
        assert stats["blocked_ips_count"] == 1


class TestInputValidator:
    """Test InputValidator class."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_email_valid(self):
        """Test email validation with valid email."""
        validator = InputValidator()
        
        assert validator.validate_email("test@example.com") is True
        assert validator.validate_email("user.name+tag@domain.co.uk") is True

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_email_invalid(self):
        """Test email validation with invalid email."""
        validator = InputValidator()
        
        assert validator.validate_email("invalid-email") is False
        assert validator.validate_email("@domain.com") is False
        assert validator.validate_email("user@") is False
        assert validator.validate_email("") is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_password_strong(self):
        """Test password validation with strong password."""
        validator = InputValidator()
        
        is_strong, issues = validator.validate_password("StrongP@ssw0rd123")
        
        assert is_strong is True
        assert len(issues) == 0

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_password_weak(self):
        """Test password validation with weak password."""
        validator = InputValidator()
        
        is_strong, issues = validator.validate_password("weak")
        
        assert is_strong is False
        assert len(issues) > 0
        assert "at least 8 characters" in " ".join(issues)

    @pytest.mark.unit
    @pytest.mark.security
    def test_validate_password_no_uppercase(self):
        """Test password validation without uppercase."""
        validator = InputValidator()
        
        is_strong, issues = validator.validate_password("lowercase123!")
        
        assert is_strong is False
        assert any("uppercase" in issue for issue in issues)

    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_filename_clean(self):
        """Test filename sanitization with clean filename."""
        validator = InputValidator()
        
        sanitized = validator.sanitize_filename("clean_filename.jpg")
        
        assert sanitized == "clean_filename.jpg"

    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_filename_malicious(self):
        """Test filename sanitization with malicious filename."""
        validator = InputValidator()
        
        sanitized = validator.sanitize_filename("../../../etc/passwd")
        
        assert "../" not in sanitized
        assert sanitized != "../../../etc/passwd"

    @pytest.mark.unit
    @pytest.mark.security
    def test_sanitize_filename_special_chars(self):
        """Test filename sanitization with special characters."""
        validator = InputValidator()
        
        sanitized = validator.sanitize_filename("file<>:\"|?*.jpg")
        
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert ":" not in sanitized
        assert "|" not in sanitized
        assert "?" not in sanitized
        assert "*" not in sanitized


class TestSecurityAudit:
    """Test SecurityAudit class."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_log_security_event(self):
        """Test logging security event."""
        audit = SecurityAudit()
        
        audit.log_security_event(
            "TEST_EVENT",
            {"test": "data"},
            "warning",
            "192.168.1.1"
        )
        
        assert len(audit.security_events) == 1
        event = audit.security_events[0]
        assert event["event_type"] == "TEST_EVENT"
        assert event["event_data"] == {"test": "data"}
        assert event["severity"] == "warning"
        assert event["client_ip"] == "192.168.1.1"

    @pytest.mark.unit
    @pytest.mark.security
    def test_get_security_summary(self):
        """Test getting security summary."""
        audit = SecurityAudit()
        
        # Add some test events
        audit.log_security_event("EVENT1", {}, "info", "192.168.1.1")
        audit.log_security_event("EVENT2", {}, "warning", "192.168.1.2")
        audit.log_security_event("EVENT1", {}, "error", "192.168.1.1")
        
        summary = audit.get_security_summary()
        
        assert "total_events" in summary
        assert "event_types" in summary
        assert "severity_breakdown" in summary
        assert "recent_events" in summary
        assert summary["total_events"] == 3
        assert summary["event_types"]["EVENT1"] == 2
        assert summary["event_types"]["EVENT2"] == 1


class TestJWTSecurity:
    """Test JWTSecurity class."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_init(self):
        """Test JWT security initialization."""
        jwt_security = JWTSecurity("test-secret-key")
        
        assert jwt_security.secret_key == "test-secret-key"
        assert isinstance(jwt_security.revoked_tokens, set)

    @pytest.mark.unit
    @pytest.mark.security
    def test_revoke_token(self):
        """Test token revocation."""
        jwt_security = JWTSecurity("test-secret-key")
        
        jwt_security.revoke_token("test-token")
        
        assert "test-token" in jwt_security.revoked_tokens

    @pytest.mark.unit
    @pytest.mark.security
    def test_is_token_revoked(self):
        """Test checking if token is revoked."""
        jwt_security = JWTSecurity("test-secret-key")
        
        # Token not revoked initially
        assert jwt_security.is_token_revoked("test-token") is False
        
        # Revoke token
        jwt_security.revoke_token("test-token")
        
        # Token should be revoked now
        assert jwt_security.is_token_revoked("test-token") is True


class TestFileValidation:
    """Test file validation functions."""

    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_validate_file_security_valid_image(self, sample_image_data):
        """Test file validation with valid image."""
        # Should not raise exception
        await validate_file_security(sample_image_data, "image/jpeg", "test.jpg")

    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_validate_file_security_malicious_content(self):
        """Test file validation with malicious content."""
        malicious_content = b"<script>alert('xss')</script>"
        
        with pytest.raises(Exception):  # Should raise validation error
            await validate_file_security(malicious_content, "text/html", "malicious.html")

    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_validate_file_security_oversized_file(self):
        """Test file validation with oversized file."""
        # Create 60MB file (over 50MB limit)
        large_content = b"x" * (60 * 1024 * 1024)
        
        with pytest.raises(Exception):  # Should raise size validation error
            await validate_file_security(large_content, "application/octet-stream", "large.bin")

    @pytest.mark.unit
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_validate_file_security_invalid_image(self):
        """Test file validation with invalid image format."""
        fake_image = b"not-an-image"
        
        with pytest.raises(Exception):  # Should raise format validation error
            await validate_file_security(fake_image, "image/jpeg", "fake.jpg")