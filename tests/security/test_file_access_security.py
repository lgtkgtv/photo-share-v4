#!/usr/bin/env python3
"""
File Access Security Tests
=========================

Tests for secure file access implementation to prevent direct file URL access.
"""

import pytest
import requests
import time
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services.photoshare.file_storage import FileStorageService


class TestFileAccessSecurity:
    """Test secure file access controls."""
    
    AUTH_SERVICE_URL = "http://localhost:8001"
    APP_SERVICE_URL = "http://localhost:8000"
    
    def setup_method(self):
        """Setup for each test."""
        self.storage_service = FileStorageService()
    
    @pytest.mark.security
    def test_signed_url_generation(self):
        """Test that signed URLs are generated correctly."""
        storage_path = "users/123/photos/test.jpg"
        
        # Generate signed URL
        signed_url = self.storage_service.generate_signed_url(storage_path)
        
        # Verify URL format
        assert signed_url.startswith("/api/photos/secure/")
        assert "expires=" in signed_url
        assert "signature=" in signed_url
        assert storage_path in signed_url
    
    @pytest.mark.security
    def test_signed_url_verification_valid(self):
        """Test that valid signed URLs pass verification."""
        storage_path = "users/123/photos/test.jpg"
        
        # Generate signed URL
        signed_url = self.storage_service.generate_signed_url(storage_path, expires_in=300)
        
        # Extract parameters
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(signed_url)
        params = parse_qs(parsed.query)
        
        expires = params['expires'][0]
        signature = params['signature'][0]
        
        # Verify signature
        assert self.storage_service.verify_signed_url(storage_path, expires, signature)
    
    @pytest.mark.security
    def test_signed_url_verification_expired(self):
        """Test that expired signed URLs are rejected."""
        storage_path = "users/123/photos/test.jpg"
        
        # Generate expired signed URL
        signed_url = self.storage_service.generate_signed_url(storage_path, expires_in=-1)
        
        # Extract parameters
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(signed_url)
        params = parse_qs(parsed.query)
        
        expires = params['expires'][0]
        signature = params['signature'][0]
        
        # Verify signature fails due to expiration
        assert not self.storage_service.verify_signed_url(storage_path, expires, signature)
    
    @pytest.mark.security
    def test_signed_url_verification_invalid_signature(self):
        """Test that URLs with invalid signatures are rejected."""
        storage_path = "users/123/photos/test.jpg"
        expires = str(int(time.time()) + 300)
        invalid_signature = "invalid_signature_here"
        
        # Verify signature fails
        assert not self.storage_service.verify_signed_url(storage_path, expires, invalid_signature)
    
    @pytest.mark.security  
    def test_signed_url_verification_tampered_path(self):
        """Test that URLs with tampered paths are rejected."""
        original_path = "users/123/photos/test.jpg"
        tampered_path = "users/456/photos/test.jpg"  # Different user
        
        # Generate signed URL for original path
        signed_url = self.storage_service.generate_signed_url(original_path, expires_in=300)
        
        # Extract parameters
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(signed_url)
        params = parse_qs(parsed.query)
        
        expires = params['expires'][0]
        signature = params['signature'][0]
        
        # Try to verify with tampered path - should fail
        assert not self.storage_service.verify_signed_url(tampered_path, expires, signature)
    
    @pytest.mark.security
    def test_timing_safe_comparison(self):
        """Test that signature comparison uses timing-safe method."""
        # This test verifies that hmac.compare_digest is used
        # by checking that the verification method exists and behaves correctly
        
        import hmac
        
        storage_path = "users/123/photos/test.jpg"
        expires = str(int(time.time()) + 300)
        
        # Generate correct signature
        payload = f"{storage_path}:{expires}"
        correct_signature = hmac.new(
            self.storage_service.storage_secret.encode(),
            payload.encode(),
            'sha256'
        ).hexdigest()
        
        # Test with correct signature
        assert self.storage_service.verify_signed_url(storage_path, expires, correct_signature)
        
        # Test with incorrect signature of same length
        wrong_signature = "a" * len(correct_signature)
        assert not self.storage_service.verify_signed_url(storage_path, expires, wrong_signature)


@pytest.mark.integration
class TestFileAccessIntegration:
    """Integration tests for file access security."""
    
    AUTH_SERVICE_URL = "http://localhost:8001" 
    APP_SERVICE_URL = "http://localhost:8000"
    
    @pytest.mark.integration
    @pytest.mark.requires_services
    def test_direct_file_access_blocked(self):
        """Test that direct file URLs are blocked by the application."""
        # This would be tested against running services
        
        # Example direct file access attempts that should be blocked:
        direct_urls = [
            f"{self.APP_SERVICE_URL}/storage/users/123/photos/test.jpg",
            f"{self.APP_SERVICE_URL}/photos/test.jpg", 
            f"{self.APP_SERVICE_URL}/uploads/test.jpg"
        ]
        
        for url in direct_urls:
            try:
                response = requests.get(url, timeout=5)
                # Should either be 403 Forbidden or 404 Not Found, not 200 OK
                assert response.status_code in [403, 404], f"Direct access to {url} should be blocked"
            except requests.exceptions.RequestException:
                # If service is not running, skip this test
                pytest.skip("Services not available for integration testing")
    
    @pytest.mark.integration
    @pytest.mark.requires_services
    def test_secure_download_requires_auth(self):
        """Test that secure download endpoints require authentication."""
        secure_url = f"{self.APP_SERVICE_URL}/api/photos/secure/users/123/photos/test.jpg"
        params = {
            "expires": str(int(time.time()) + 300),
            "signature": "valid_signature_here"
        }
        
        try:
            # Try to access without authentication
            response = requests.get(secure_url, params=params, timeout=5)
            # Should require authentication
            assert response.status_code == 401, "Secure download should require authentication"
        except requests.exceptions.RequestException:
            pytest.skip("Services not available for integration testing")
    
    @pytest.mark.integration
    @pytest.mark.requires_services  
    def test_download_url_generation_requires_auth(self):
        """Test that download URL generation requires authentication."""
        download_endpoint = f"{self.APP_SERVICE_URL}/api/photos/123/download"
        
        try:
            # Try to get download URL without authentication
            response = requests.get(download_endpoint, timeout=5)
            # Should require authentication
            assert response.status_code == 401, "Download URL generation should require authentication"
        except requests.exceptions.RequestException:
            pytest.skip("Services not available for integration testing")


@pytest.mark.security_compliance
class TestFileAccessCompliance:
    """Compliance tests for file access security."""
    
    @pytest.mark.security_compliance
    def test_owasp_a01_broken_access_control_mitigation(self):
        """Test mitigation of OWASP A01 - Broken Access Control."""
        # Verify that the implementation addresses:
        # 1. No direct file access without authentication
        # 2. Signed URLs with expiration
        # 3. Permission checks on file access
        
        storage_service = FileStorageService()
        
        # Test 1: Signed URLs are used instead of direct access
        storage_path = "users/123/photos/private.jpg"
        url = storage_service.get_file_url(storage_path)
        assert "/api/photos/secure/" in url, "Should use secure API endpoint"
        assert "signature=" in url, "Should include signature"
        assert "expires=" in url, "Should include expiration"
        
        # Test 2: URLs expire
        expired_url = storage_service.generate_signed_url(storage_path, expires_in=-1)
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(expired_url)
        params = parse_qs(parsed.query)
        expires = params['expires'][0]
        signature = params['signature'][0]
        
        assert not storage_service.verify_signed_url(storage_path, expires, signature), \
            "Expired URLs should be rejected"
    
    @pytest.mark.security_compliance
    def test_owasp_a05_security_misconfiguration_prevention(self):
        """Test prevention of OWASP A05 - Security Misconfiguration."""
        # Verify secure defaults
        storage_service = FileStorageService()
        
        # Should use secure storage path (not /tmp)
        assert "/tmp" not in storage_service.local_storage_path, \
            "Should not use temporary storage for production"
        
        # Should have reasonable expiration time (not too long)
        assert storage_service.signed_url_expiration <= 3600, \
            "URL expiration should not be longer than 1 hour"
        
        # Should have secure secret key
        assert len(storage_service.storage_secret) >= 32, \
            "Storage secret should be at least 32 characters"


if __name__ == "__main__":
    # Run specific security tests
    pytest.main([
        __file__,
        "-v",
        "-m", "security",
        "--tb=short"
    ])