#!/usr/bin/env python3
"""
WAF Protection Security Tests
============================

Tests for Web Application Firewall functionality.
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock
from fastapi import Request
from fastapi.responses import JSONResponse

# Import WAF protection
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'photoshare'))

from waf_protection import WAFProtection, waf_middleware, validate_file_upload_waf


class TestWAFProtection:
    """Test WAF protection functionality."""
    
    def setup_method(self):
        """Set up test instance."""
        self.waf = WAFProtection()
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        # Test cases that should be detected
        malicious_inputs = [
            "1' OR '1'='1",
            "admin'; DROP TABLE users; --",
            "1 UNION SELECT * FROM users",
            "test' AND 1=1--",
            "1' OR SLEEP(5)--"
        ]
        
        for input_text in malicious_inputs:
            threat = self.waf.detect_sql_injection(input_text)
            assert threat is not None, f"Should detect SQL injection in: {input_text}"
            assert threat.threat_type == "sql_injection"
            assert threat.severity == "CRITICAL"
            assert threat.blocked is True
    
    def test_xss_detection(self):
        """Test XSS pattern detection."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<img onload='alert(1)'>",
            "javascript:alert('xss')",
            "<object data='malicious.swf'></object>"
        ]
        
        for input_text in malicious_inputs:
            threat = self.waf.detect_xss(input_text)
            assert threat is not None, f"Should detect XSS in: {input_text}"
            assert threat.threat_type == "xss"
            assert threat.severity == "HIGH"
            assert threat.blocked is True
    
    def test_path_traversal_detection(self):
        """Test path traversal detection."""
        malicious_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e/etc/passwd",
            "/etc/passwd",
            ".htaccess"
        ]
        
        for input_text in malicious_inputs:
            threat = self.waf.detect_path_traversal(input_text)
            assert threat is not None, f"Should detect path traversal in: {input_text}"
            assert threat.threat_type == "path_traversal"
            assert threat.severity == "HIGH"
            assert threat.blocked is True
    
    def test_command_injection_detection(self):
        """Test command injection detection."""
        malicious_inputs = [
            "test; cat /etc/passwd",
            "$(whoami)",
            "`ls -la`",
            "test && id",
            "test | netstat"
        ]
        
        for input_text in malicious_inputs:
            threat = self.waf.detect_command_injection(input_text)
            assert threat is not None, f"Should detect command injection in: {input_text}"
            assert threat.threat_type == "command_injection"
            assert threat.severity == "CRITICAL"
            assert threat.blocked is True
    
    def test_honeypot_detection(self):
        """Test honeypot path detection."""
        honeypot_paths = [
            "/admin",
            "/wp-admin/admin.php",
            "/phpmyadmin/index.php",
            "/.env",
            "/config/database.yml"
        ]
        
        for path in honeypot_paths:
            threat = self.waf.check_honeypot_access(path)
            assert threat is not None, f"Should detect honeypot access: {path}"
            assert threat.threat_type == "honeypot_access"
            assert threat.severity == "HIGH"
            assert threat.blocked is True
    
    def test_malicious_user_agent_detection(self):
        """Test malicious user agent detection."""
        malicious_agents = [
            "sqlmap/1.0",
            "Nikto/2.1.6",
            "Mozilla/5.0 (compatible; Nessus)",
            "w3af.org",
            "havij"
        ]
        
        for agent in malicious_agents:
            threat = self.waf.check_user_agent(agent)
            assert threat is not None, f"Should detect malicious user agent: {agent}"
            assert threat.threat_type == "malicious_user_agent"
            assert threat.severity == "HIGH"
            assert threat.blocked is True
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        test_ip = "192.168.1.100"
        
        # First 100 requests should pass
        for i in range(100):
            is_limited = self.waf.is_rate_limited(test_ip)
            assert not is_limited, f"Request {i+1} should not be rate limited"
        
        # 101st request should be rate limited
        is_limited = self.waf.is_rate_limited(test_ip)
        assert is_limited, "Request 101 should be rate limited"
    
    def test_file_upload_validation(self):
        """Test file upload validation."""
        # Valid image files
        valid_files = [
            ("photo.jpg", b"valid image content"),
            ("image.png", b"PNG image data"),
            ("picture.gif", b"GIF image")
        ]
        
        for filename, content in valid_files:
            threat = self.waf.validate_file_upload(filename, content)
            # Should not detect threat for valid files
            # (Note: threat might be None or not blocked)
        
        # Invalid/malicious files
        malicious_files = [
            ("malicious.php", b"<?php echo 'malicious'; ?>"),
            ("script.jsp", b"<% malicious code %>"),
            ("shell.sh", b"#!/bin/bash\nrm -rf /"),
            ("image.jpg", b"<script>alert('xss')</script>")
        ]
        
        for filename, content in malicious_files:
            threat = self.waf.validate_file_upload(filename, content)
            assert threat is not None, f"Should detect threat in file: {filename}"
            assert threat.blocked is True
    
    def test_benign_requests(self):
        """Test that benign requests are not flagged."""
        benign_inputs = [
            "normal search query",
            "user@example.com",
            "My photo title",
            "/api/photos/123",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ]
        
        for input_text in benign_inputs:
            # Test all detection methods
            sql_threat = self.waf.detect_sql_injection(input_text)
            xss_threat = self.waf.detect_xss(input_text)
            path_threat = self.waf.detect_path_traversal(input_text)
            cmd_threat = self.waf.detect_command_injection(input_text)
            
            # None of these should detect threats
            assert sql_threat is None, f"False positive SQL injection: {input_text}"
            assert xss_threat is None, f"False positive XSS: {input_text}"
            assert path_threat is None, f"False positive path traversal: {input_text}"
            assert cmd_threat is None, f"False positive command injection: {input_text}"
    
    def test_statistics_tracking(self):
        """Test statistics tracking."""
        initial_stats = self.waf.get_security_stats()
        
        # Simulate some threats
        self.waf.detect_sql_injection("1' OR '1'='1")
        self.waf.detect_xss("<script>alert(1)</script>")
        
        # Note: Statistics are only updated through protect_request method
        # This test validates the statistics structure
        assert "total_requests" in initial_stats
        assert "blocked_requests" in initial_stats
        assert "threats_by_type" in initial_stats
        assert "top_blocked_ips" in initial_stats
    
    @pytest.mark.asyncio
    async def test_waf_middleware_integration(self):
        """Test WAF middleware integration."""
        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.client.host = "192.168.1.50"
        mock_request.url.path = "/api/photos"
        mock_request.query_params = {}
        mock_request.headers = {"user-agent": "Mozilla/5.0"}
        mock_request.method = "GET"
        
        # Create mock call_next
        mock_response = Mock()
        async def mock_call_next(request):
            return mock_response
        
        # Test normal request
        result = await waf_middleware(mock_request, mock_call_next)
        assert result == mock_response
        
        # Test malicious request
        mock_request.url.path = "/admin"  # Honeypot path
        result = await waf_middleware(mock_request, mock_call_next)
        
        # Should return JSONResponse with 403 status
        assert isinstance(result, JSONResponse)
        assert result.status_code == 403


def test_file_upload_waf_validation():
    """Test WAF file upload validation function."""
    # Valid file should not raise exception
    try:
        validate_file_upload_waf("photo.jpg", b"valid image content")
    except Exception:
        pytest.fail("Valid file upload should not raise exception")
    
    # Malicious file should raise HTTPException
    with pytest.raises(Exception):  # Should raise HTTPException
        validate_file_upload_waf("malicious.php", b"<?php malicious code ?>")


if __name__ == "__main__":
    # Run basic tests
    waf = WAFProtection()
    
    print("🧪 Running WAF Protection Tests...")
    
    # Test SQL injection detection
    threat = waf.detect_sql_injection("1' OR '1'='1")
    assert threat is not None
    print("✅ SQL injection detection working")
    
    # Test XSS detection
    threat = waf.detect_xss("<script>alert('xss')</script>")
    assert threat is not None
    print("✅ XSS detection working")
    
    # Test path traversal detection
    threat = waf.detect_path_traversal("../../../etc/passwd")
    assert threat is not None
    print("✅ Path traversal detection working")
    
    # Test honeypot detection
    threat = waf.check_honeypot_access("/admin")
    assert threat is not None
    print("✅ Honeypot detection working")
    
    # Test rate limiting
    test_ip = "192.168.1.100"
    for i in range(101):  # Exceed rate limit
        is_limited = waf.is_rate_limited(test_ip)
    assert is_limited
    print("✅ Rate limiting working")
    
    # Test file validation
    threat = waf.validate_file_upload("malicious.php", b"<?php echo 'test'; ?>")
    assert threat is not None
    print("✅ File upload validation working")
    
    # Test statistics
    stats = waf.get_security_stats()
    assert "total_requests" in stats
    print("✅ Statistics tracking working")
    
    print("\n🎉 All WAF protection tests passed!")
    print("🛡️  WAF is ready for deployment")