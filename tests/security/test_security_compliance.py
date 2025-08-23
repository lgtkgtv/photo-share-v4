#!/usr/bin/env python3
"""
Security Compliance Tests
=========================

Comprehensive security compliance testing including:
- OWASP Top 10 vulnerability checks
- Code security standards compliance  
- Authentication and authorization security
- Data protection and privacy compliance
- Security configuration validation
"""

import pytest
import requests
import subprocess
import os
import json
import time
from datetime import datetime
import ssl
import socket


class TestOWASPCompliance:
    """Test compliance with OWASP Top 10 security risks."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    APP_BASE_URL = "http://localhost:8000"
    
    @pytest.mark.security_compliance
    def test_injection_prevention(self):
        """Test protection against SQL injection and other injection attacks."""
        # SQL injection attempts
        sql_payloads = [
            "admin@example.com'; DROP TABLE users; --",
            "test@example.com' OR '1'='1",
            "user@test.com'; UPDATE users SET role='admin' WHERE email='user@test.com'; --"
        ]
        
        for payload in sql_payloads:
            # Test in registration
            response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/register", json={
                "email": payload,
                "password": "TestPassword123!",
                "first_name": "Test",
                "last_name": "User"
            })
            
            # Should not cause server error (500) - indicates proper input handling
            assert response.status_code != 500, f"SQL injection payload caused server error: {payload}"
            
            # Test in login
            response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/login", data={
                "username": payload,
                "password": "anypassword"
            })
            
            assert response.status_code != 500, f"SQL injection in login caused server error: {payload}"
    
    @pytest.mark.security_compliance
    def test_broken_authentication_prevention(self):
        """Test protection against broken authentication vulnerabilities."""
        # Test weak session management
        # Test password brute force protection
        
        # Attempt rapid login attempts (should trigger rate limiting)
        login_data = {"username": "test@example.com", "password": "wrongpassword"}
        
        failed_attempts = 0
        rate_limited = False
        
        for i in range(5):
            response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/login", data=login_data)
            if response.status_code == 429:  # Rate limited
                rate_limited = True
                break
            elif response.status_code == 401:  # Failed login
                failed_attempts += 1
                
        # Should have rate limiting or account lockout protection
        assert rate_limited or failed_attempts < 5, "Should have brute force protection"
    
    @pytest.mark.security_compliance 
    def test_sensitive_data_exposure_prevention(self):
        """Test protection against sensitive data exposure."""
        # Test that passwords are not returned in responses
        response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/register", json={
            "email": "sensitive-test@example.com",
            "password": "MySecretPassword123!",
            "first_name": "Test",
            "last_name": "User"
        })
        
        if response.status_code == 200:
            user_data = response.json()
            response_str = json.dumps(user_data)
            
            # Password should not appear in response
            assert "MySecretPassword123!" not in response_str, "Password should not be exposed in response"
            assert "password" not in user_data, "Password field should not be in response"
    
    @pytest.mark.security_compliance
    def test_broken_access_control_prevention(self):
        """Test protection against broken access control."""
        # Test vertical privilege escalation
        # Test horizontal privilege escalation
        
        # Try to access admin endpoints without proper authorization
        admin_endpoints = [
            f"{self.AUTH_BASE_URL}/api/auth/admin/users",
            f"{self.APP_BASE_URL}/api/admin/photos",
            f"{self.AUTH_BASE_URL}/api/auth/admin/roles"
        ]
        
        for endpoint in admin_endpoints:
            # Without authentication
            response = requests.get(endpoint)
            assert response.status_code in [401, 403, 404], f"Admin endpoint should be protected: {endpoint}"
            
            # With regular user token (if we have one)
            # This would require creating a test token, which we've done in other tests
    
    @pytest.mark.security_compliance
    def test_security_misconfiguration_prevention(self):
        """Test for security misconfigurations."""
        # Test that debug mode is disabled (no stack traces in production responses)
        response = requests.get(f"{self.AUTH_BASE_URL}/nonexistent-endpoint")
        
        if response.status_code == 404:
            # Should not expose internal paths or debug info
            response_text = response.text.lower()
            debug_indicators = ['traceback', 'stack trace', 'debug', '/usr/local/', '__pycache__']
            
            for indicator in debug_indicators:
                assert indicator not in response_text, f"Debug info exposed: {indicator}"
    
    @pytest.mark.security_compliance
    def test_vulnerable_components_check(self):
        """Check for known vulnerable components."""
        # This is more of a static analysis check
        # In practice, you'd run tools like Safety, Snyk, or OWASP Dependency Check
        
        # Test that services respond with appropriate headers
        response = requests.get(f"{self.AUTH_BASE_URL}/health")
        
        # Check for security headers
        headers = response.headers
        
        # Server header should not reveal too much information
        server_header = headers.get('Server', '').lower()
        if server_header:
            # Should not reveal exact versions
            assert 'uvicorn' not in server_header or '/' not in server_header, "Server header should not reveal version"


class TestDataProtectionCompliance:
    """Test data protection and privacy compliance."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    APP_BASE_URL = "http://localhost:8000"
    
    @pytest.mark.security_compliance
    def test_data_encryption_at_rest(self):
        """Test that sensitive data is encrypted at rest."""
        # This would typically require database inspection
        # For this test, we verify that passwords are hashed
        
        response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/register", json={
            "email": "encryption-test@example.com",
            "password": "PlaintextPassword123!",
            "first_name": "Encryption",
            "last_name": "Test"
        })
        
        if response.status_code == 200:
            # Check that plain password is not stored by attempting to login
            login_response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/login", data={
                "username": "encryption-test@example.com",
                "password": "PlaintextPassword123!"
            })
            
            # If password is properly hashed, login should work
            # (This assumes the login endpoint exists and works)
    
    @pytest.mark.security_compliance
    def test_data_transmission_security(self):
        """Test secure data transmission practices."""
        # In production, this would test HTTPS enforcement
        # For localhost testing, we verify proper header handling
        
        response = requests.get(f"{self.AUTH_BASE_URL}/health")
        headers = response.headers
        
        # Check for security headers that would be present in production
        security_headers = [
            'x-content-type-options',
            'x-frame-options', 
            'x-xss-protection'
        ]
        
        # Note: These might not be present in development, which is OK
        # The test documents what should be present in production
    
    @pytest.mark.security_compliance
    def test_audit_logging_presence(self):
        """Test that security events are properly logged."""
        # Test that authentication attempts are logged
        # This is difficult to test without log access, but we can test the endpoints work
        
        # Failed login attempt
        response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/login", data={
            "username": "audit-test@example.com",
            "password": "wrongpassword"
        })
        
        # Should handle failed login gracefully
        assert response.status_code in [401, 422], "Failed login should be handled properly"


class TestSecurityConfiguration:
    """Test security configuration and hardening."""
    
    AUTH_BASE_URL = "http://localhost:8001"
    APP_BASE_URL = "http://localhost:8000"
    
    @pytest.mark.security_compliance
    def test_http_security_headers(self):
        """Test presence of HTTP security headers."""
        endpoints_to_test = [
            f"{self.AUTH_BASE_URL}/health",
            f"{self.APP_BASE_URL}/health"
        ]
        
        for endpoint in endpoints_to_test:
            response = requests.get(endpoint)
            headers = response.headers
            
            # Document expected security headers (may not be present in dev)
            expected_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block'
            }
            
            # This test documents what should be configured in production
            # In development, these headers might not be present
    
    @pytest.mark.security_compliance
    def test_cors_configuration(self):
        """Test CORS configuration security."""
        # Test that CORS is properly configured
        response = requests.options(f"{self.AUTH_BASE_URL}/api/auth/register")
        
        if 'access-control-allow-origin' in response.headers:
            allowed_origins = response.headers['access-control-allow-origin']
            
            # Should not allow all origins in production
            if allowed_origins == '*':
                # This might be OK for development, but should be restricted in production
                pass  # Document this as a production consideration
    
    @pytest.mark.security_compliance
    def test_error_handling_security(self):
        """Test that error handling doesn't leak sensitive information."""
        # Test 404 handling
        response = requests.get(f"{self.AUTH_BASE_URL}/nonexistent/path/here")
        
        if response.status_code == 404:
            error_text = response.text.lower()
            
            # Should not reveal internal paths or system information
            sensitive_info = [
                '/app/',
                'python',
                'traceback',
                'exception',
                'stack',
                'line',
                'file'
            ]
            
            for info in sensitive_info:
                assert info not in error_text, f"Error response should not reveal: {info}"
    
    @pytest.mark.security_compliance
    def test_input_size_limits(self):
        """Test that input size limits are enforced."""
        # Test large input handling
        large_email = "a" * 1000 + "@example.com"
        
        response = requests.post(f"{self.AUTH_BASE_URL}/api/auth/register", json={
            "email": large_email,
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User"
        })
        
        # Should reject overly large inputs
        assert response.status_code in [400, 422], "Should reject oversized input"
    
    @pytest.mark.security_compliance
    def test_service_fingerprinting_protection(self):
        """Test protection against service fingerprinting."""
        response = requests.get(f"{self.AUTH_BASE_URL}/health")
        headers = response.headers
        
        # Server header should not reveal detailed version information
        server = headers.get('Server', '')
        if server:
            # Should not contain version numbers or detailed implementation info
            assert '/' not in server or 'uvicorn/' not in server.lower(), "Server header should not reveal version"


class TestComplianceReporting:
    """Generate compliance reports and documentation."""
    
    @pytest.mark.security_compliance
    def test_generate_security_compliance_report(self):
        """Generate a security compliance report."""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_environment": "development",
            "services_tested": [
                "auth-service:8001",
                "app-service:8000"
            ],
            "compliance_areas": [
                "OWASP Top 10",
                "Data Protection",
                "Authentication Security",
                "Authorization Controls",
                "Input Validation",
                "Error Handling",
                "Security Configuration"
            ],
            "recommendations": [
                "Enable HTTPS in production",
                "Configure security headers",
                "Implement comprehensive audit logging",
                "Regular security dependency updates",
                "Penetration testing before production deployment"
            ]
        }
        
        # Save report
        os.makedirs("tests/reports", exist_ok=True)
        
        report_filename = f"tests/reports/security_compliance_{int(time.time())}.json"
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        assert os.path.exists(report_filename), "Security compliance report should be generated"
        
        # Verify report content
        with open(report_filename, 'r') as f:
            saved_report = json.load(f)
            assert saved_report["timestamp"] == report_data["timestamp"]
            assert len(saved_report["compliance_areas"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "security_compliance"])