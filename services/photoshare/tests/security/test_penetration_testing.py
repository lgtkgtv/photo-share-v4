"""
Penetration Testing Scripts
===========================

Comprehensive penetration testing suite for the photo sharing service.
Simulates real-world attack scenarios and security assessments.
"""

import pytest
import asyncio
import time
import json
import base64
import hashlib
import random
import string
from typing import Dict, Any, List, Optional
from httpx import AsyncClient
from unittest.mock import patch
import subprocess


class PenetrationTester:
    """Advanced penetration testing framework."""
    
    def __init__(self, client: AsyncClient):
        self.client = client
        self.findings = []
        self.attack_results = {}
        self.session_data = {}
        
    def log_finding(self, severity: str, category: str, description: str, evidence: Dict[str, Any]):
        """Log penetration testing findings."""
        finding = {
            "timestamp": time.time(),
            "severity": severity,
            "category": category,
            "description": description,
            "evidence": evidence,
            "cvss_score": self._calculate_cvss(severity, category)
        }
        self.findings.append(finding)
        
        if severity in ["CRITICAL", "HIGH"]:
            print(f"🚨 {severity}: {description}")
    
    def _calculate_cvss(self, severity: str, category: str) -> float:
        """Calculate CVSS score for findings."""
        base_scores = {
            "CRITICAL": 9.0,
            "HIGH": 7.5,
            "MEDIUM": 5.0,
            "LOW": 2.5,
            "INFO": 0.0
        }
        return base_scores.get(severity, 0.0)
    
    async def test_authentication_bypass(self) -> Dict[str, Any]:
        """Test for authentication bypass vulnerabilities."""
        print("🔓 Testing authentication bypass...")
        
        bypass_attempts = [
            # SQL injection in login
            {"username": "admin'--", "password": "anything"},
            {"username": "admin'/*", "password": "anything"},
            {"username": "' OR '1'='1'--", "password": "anything"},
            
            # NoSQL injection
            {"username": {"$ne": None}, "password": {"$ne": None}},
            {"username": {"$regex": ".*"}, "password": {"$regex": ".*"}},
            
            # Empty/null bypass
            {"username": "", "password": ""},
            {"username": None, "password": None},
            
            # Unicode normalization attacks
            {"username": "admin\u0041", "password": "password"},
            {"username": "admin\u200B", "password": "password"},
        ]
        
        successful_bypasses = []
        
        for attempt in bypass_attempts:
            try:
                response = await self.client.post("/api/users/login", json=attempt)
                
                if response.status_code == 200:
                    token_data = response.json()
                    if "access_token" in token_data:
                        successful_bypasses.append({
                            "payload": attempt,
                            "response": token_data
                        })
                        
                        self.log_finding(
                            "CRITICAL",
                            "Authentication Bypass",
                            f"Authentication bypass successful with payload: {attempt}",
                            {"payload": attempt, "response_status": response.status_code}
                        )
                        
            except Exception as e:
                # Errors might indicate injection attempts are being processed
                if "sql" in str(e).lower() or "syntax" in str(e).lower():
                    self.log_finding(
                        "HIGH",
                        "SQL Injection",
                        f"Potential SQL injection in login: {e}",
                        {"payload": attempt, "error": str(e)}
                    )
        
        return {"successful_bypasses": successful_bypasses}
    
    async def test_jwt_security(self) -> Dict[str, Any]:
        """Test JWT token security and manipulation."""
        print("🎫 Testing JWT security...")
        
        # First, get a valid token
        registration_data = {
            "email": f"pentest_{random.randint(1000,9999)}@example.com",
            "password": "TestPassword123!"
        }
        
        reg_response = await self.client.post("/api/users/register", json=registration_data)
        if reg_response.status_code != 201:
            return {"error": "Could not create test user for JWT testing"}
        
        login_response = await self.client.post("/api/users/login", json={
            "username": registration_data["email"],
            "password": registration_data["password"]
        })
        
        if login_response.status_code != 200:
            return {"error": "Could not login for JWT testing"}
        
        token = login_response.json().get("access_token")
        if not token:
            return {"error": "No access token received"}
        
        jwt_vulnerabilities = []
        
        # Test JWT manipulation attacks
        jwt_attacks = [
            # Algorithm confusion
            self._modify_jwt_algorithm(token, "none"),
            self._modify_jwt_algorithm(token, "HS256"),
            
            # Token manipulation
            self._modify_jwt_payload(token, {"sub": "1", "email": "admin@example.com"}),
            self._modify_jwt_payload(token, {"sub": "999999"}),
            
            # Signature stripping
            ".".join(token.split(".")[:-1]) + ".",
            
            # Invalid tokens
            "invalid.token.here",
            token + "modified",
            token[:-5] + "AAAAA",  # Modified signature
        ]
        
        for manipulated_token in jwt_attacks:
            if not manipulated_token:
                continue
                
            try:
                headers = {"Authorization": f"Bearer {manipulated_token}"}
                response = await self.client.get("/api/users/me", headers=headers)
                
                if response.status_code == 200:
                    jwt_vulnerabilities.append({
                        "attack_type": "JWT Manipulation",
                        "token": manipulated_token[:50] + "...",
                        "response_status": response.status_code
                    })
                    
                    self.log_finding(
                        "CRITICAL",
                        "JWT Security",
                        "JWT token manipulation successful",
                        {"manipulated_token": manipulated_token[:50], "response": response.status_code}
                    )
                    
            except Exception as e:
                pass  # Expected for invalid tokens
        
        return {"jwt_vulnerabilities": jwt_vulnerabilities}
    
    def _modify_jwt_algorithm(self, token: str, new_alg: str) -> Optional[str]:
        """Modify JWT algorithm."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            # Decode header
            header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
            header["alg"] = new_alg
            
            # Re-encode header
            new_header = base64.urlsafe_b64encode(
                json.dumps(header, separators=(",", ":")).encode()
            ).decode().rstrip("=")
            
            if new_alg.lower() == "none":
                return f"{new_header}.{parts[1]}."
            else:
                return f"{new_header}.{parts[1]}.{parts[2]}"
                
        except Exception:
            return None
    
    def _modify_jwt_payload(self, token: str, new_payload: Dict[str, Any]) -> Optional[str]:
        """Modify JWT payload."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            # Decode and modify payload
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
            payload.update(new_payload)
            
            # Re-encode payload
            new_payload_encoded = base64.urlsafe_b64encode(
                json.dumps(payload, separators=(",", ":")).encode()
            ).decode().rstrip("=")
            
            return f"{parts[0]}.{new_payload_encoded}.{parts[2]}"
            
        except Exception:
            return None
    
    async def test_authorization_flaws(self) -> Dict[str, Any]:
        """Test for authorization and access control flaws."""
        print("🛡️ Testing authorization flaws...")
        
        # Create two test users
        user1_data = {
            "email": f"pentest_user1_{random.randint(1000,9999)}@example.com",
            "password": "TestPassword123!"
        }
        user2_data = {
            "email": f"pentest_user2_{random.randint(1000,9999)}@example.com", 
            "password": "TestPassword123!"
        }
        
        # Register users
        await self.client.post("/api/users/register", json=user1_data)
        await self.client.post("/api/users/register", json=user2_data)
        
        # Login as user1
        login1_response = await self.client.post("/api/users/login", json={
            "username": user1_data["email"],
            "password": user1_data["password"]
        })
        
        if login1_response.status_code != 200:
            return {"error": "Could not login user1 for authorization testing"}
        
        user1_token = login1_response.json().get("access_token")
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        
        # Login as user2  
        login2_response = await self.client.post("/api/users/login", json={
            "username": user2_data["email"],
            "password": user2_data["password"]
        })
        
        if login2_response.status_code != 200:
            return {"error": "Could not login user2 for authorization testing"}
        
        user2_token = login2_response.json().get("access_token")
        
        authorization_flaws = []
        
        # Test IDOR (Insecure Direct Object References)
        idor_tests = [
            # Try to access other user's data with different IDs
            "/api/photos/1",
            "/api/photos/2", 
            "/api/photos/999",
            "/api/users/1",
            "/api/users/2",
        ]
        
        for endpoint in idor_tests:
            try:
                response = await self.client.get(endpoint, headers=user1_headers)
                
                # If we get 200 for resources that shouldn't belong to user1
                if response.status_code == 200:
                    authorization_flaws.append({
                        "vulnerability": "IDOR",
                        "endpoint": endpoint,
                        "description": "Accessed resource belonging to another user"
                    })
                    
                    self.log_finding(
                        "HIGH",
                        "Authorization",
                        f"IDOR vulnerability at {endpoint}",
                        {"endpoint": endpoint, "user_token": user1_token[:20]}
                    )
                    
            except Exception:
                pass
        
        # Test privilege escalation attempts
        privilege_escalation_payloads = [
            {"role": "admin"},
            {"is_admin": True},
            {"privileges": ["admin", "write", "delete"]},
            {"user_type": "administrator"}
        ]
        
        for payload in privilege_escalation_payloads:
            try:
                response = await self.client.put(
                    "/api/users/profile", 
                    headers=user1_headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    # Check if privilege escalation was successful
                    profile_response = await self.client.get("/api/users/me", headers=user1_headers)
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        
                        # Check if any admin-like attributes were set
                        for key in payload.keys():
                            if key in profile_data:
                                authorization_flaws.append({
                                    "vulnerability": "Privilege Escalation",
                                    "payload": payload,
                                    "description": f"Successfully set {key} attribute"
                                })
                                
                                self.log_finding(
                                    "CRITICAL",
                                    "Authorization",
                                    f"Privilege escalation via {key} attribute",
                                    {"payload": payload}
                                )
                                
            except Exception:
                pass
        
        return {"authorization_flaws": authorization_flaws}
    
    async def test_injection_attacks(self) -> Dict[str, Any]:
        """Test for various injection vulnerabilities."""
        print("💉 Testing injection attacks...")
        
        injection_payloads = {
            "sql_injection": [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM users --",
                "'; INSERT INTO users VALUES ('hacker'); --"
            ],
            "nosql_injection": [
                {"$ne": None},
                {"$regex": ".*"},
                {"$where": "function() { return true; }"}
            ],
            "xss_injection": [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "<svg onload=alert('xss')>"
            ],
            "command_injection": [
                "; cat /etc/passwd",
                "| whoami",
                "`id`",
                "$(whoami)"
            ],
            "ldap_injection": [
                "*)(uid=*))(|(uid=*",
                "admin)(&(password=*))"
            ]
        }
        
        injection_vulnerabilities = []
        
        # Test injection in registration
        for injection_type, payloads in injection_payloads.items():
            for payload in payloads:
                test_data = {
                    "email": f"test{payload}@example.com" if isinstance(payload, str) else payload,
                    "password": payload if isinstance(payload, str) else "TestPassword123!"
                }
                
                try:
                    response = await self.client.post("/api/users/register", json=test_data)
                    
                    # Check for injection success indicators
                    if response.status_code == 500:
                        response_text = response.text.lower()
                        if any(keyword in response_text for keyword in [
                            "sql", "syntax error", "mysql", "postgresql", 
                            "ora-", "database", "query"
                        ]):
                            injection_vulnerabilities.append({
                                "type": injection_type,
                                "payload": str(payload),
                                "endpoint": "/api/users/register",
                                "evidence": "Database error disclosure"
                            })
                            
                            self.log_finding(
                                "HIGH",
                                "Injection",
                                f"{injection_type} vulnerability in registration",
                                {"payload": str(payload), "response": response.text[:200]}
                            )
                            
                except Exception as e:
                    # Exceptions might indicate successful injection
                    if "sql" in str(e).lower() or "syntax" in str(e).lower():
                        injection_vulnerabilities.append({
                            "type": injection_type,
                            "payload": str(payload),
                            "endpoint": "/api/users/register",
                            "evidence": f"Exception: {str(e)}"
                        })
        
        return {"injection_vulnerabilities": injection_vulnerabilities}
    
    async def test_file_upload_attacks(self) -> Dict[str, Any]:
        """Test file upload security vulnerabilities."""
        print("📁 Testing file upload attacks...")
        
        file_upload_attacks = []
        
        # Malicious file payloads
        malicious_files = [
            # PHP webshell
            {
                "filename": "shell.php",
                "content": b"<?php system($_GET['cmd']); ?>",
                "content_type": "application/x-php"
            },
            # ASP webshell
            {
                "filename": "shell.asp",
                "content": b"<%eval request('cmd')%>",
                "content_type": "application/x-asp"
            },
            # Script in image extension
            {
                "filename": "image.jpg.php",
                "content": b"\xFF\xD8\xFF\xE0<?php system($_GET['cmd']); ?>",
                "content_type": "image/jpeg"
            },
            # XXE attack
            {
                "filename": "xxe.xml",
                "content": b"""<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<foo>&xxe;</foo>""",
                "content_type": "application/xml"
            },
            # Directory traversal
            {
                "filename": "../../../shell.php",
                "content": b"<?php system($_GET['cmd']); ?>",
                "content_type": "application/x-php"
            },
            # Large file DoS
            {
                "filename": "large.txt",
                "content": b"A" * 10000000,  # 10MB
                "content_type": "text/plain"
            }
        ]
        
        # Get auth token for file upload tests
        test_user = {
            "email": f"filetest_{random.randint(1000,9999)}@example.com",
            "password": "TestPassword123!"
        }
        
        await self.client.post("/api/users/register", json=test_user)
        login_response = await self.client.post("/api/users/login", json={
            "username": test_user["email"],
            "password": test_user["password"]
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            for file_attack in malicious_files:
                try:
                    files = {
                        "file": (
                            file_attack["filename"],
                            file_attack["content"],
                            file_attack["content_type"]
                        )
                    }
                    
                    response = await self.client.post(
                        "/api/photos/upload",
                        headers=headers,
                        files=files
                    )
                    
                    if response.status_code == 200:
                        # File upload succeeded - check for vulnerabilities
                        upload_data = response.json()
                        
                        file_upload_attacks.append({
                            "filename": file_attack["filename"],
                            "attack_type": "Malicious file upload",
                            "upload_response": upload_data
                        })
                        
                        self.log_finding(
                            "HIGH",
                            "File Upload",
                            f"Malicious file upload successful: {file_attack['filename']}",
                            {"filename": file_attack["filename"], "response": upload_data}
                        )
                        
                except Exception as e:
                    # Some exceptions might indicate successful attacks
                    if "executed" in str(e).lower() or "shell" in str(e).lower():
                        file_upload_attacks.append({
                            "filename": file_attack["filename"],
                            "attack_type": "File execution",
                            "evidence": str(e)
                        })
        
        return {"file_upload_attacks": file_upload_attacks}
    
    async def test_session_management(self) -> Dict[str, Any]:
        """Test session management vulnerabilities."""
        print("🔐 Testing session management...")
        
        session_vulnerabilities = []
        
        # Create test user
        test_user = {
            "email": f"sessiontest_{random.randint(1000,9999)}@example.com",
            "password": "TestPassword123!"
        }
        
        await self.client.post("/api/users/register", json=test_user)
        login_response = await self.client.post("/api/users/login", json={
            "username": test_user["email"],
            "password": test_user["password"]
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test token reuse after logout
            logout_response = await self.client.post("/api/users/logout", headers=headers)
            
            # Try to use token after logout
            profile_response = await self.client.get("/api/users/me", headers=headers)
            
            if profile_response.status_code == 200:
                session_vulnerabilities.append({
                    "vulnerability": "Token valid after logout",
                    "description": "JWT token remains valid after logout"
                })
                
                self.log_finding(
                    "MEDIUM",
                    "Session Management",
                    "JWT token not invalidated on logout",
                    {"token_status": "valid_after_logout"}
                )
            
            # Test concurrent sessions
            login_response2 = await self.client.post("/api/users/login", json={
                "username": test_user["email"],
                "password": test_user["password"]
            })
            
            if login_response2.status_code == 200:
                token2 = login_response2.json().get("access_token")
                headers2 = {"Authorization": f"Bearer {token2}"}
                
                # Both tokens should work (or system should invalidate old one)
                profile1 = await self.client.get("/api/users/me", headers=headers)
                profile2 = await self.client.get("/api/users/me", headers=headers2)
                
                if profile1.status_code == 200 and profile2.status_code == 200:
                    # This might be acceptable, but worth noting
                    session_vulnerabilities.append({
                        "vulnerability": "Concurrent sessions allowed",
                        "description": "Multiple valid sessions for same user"
                    })
        
        return {"session_vulnerabilities": session_vulnerabilities}
    
    async def generate_penetration_report(self) -> Dict[str, Any]:
        """Generate comprehensive penetration testing report."""
        print("📊 Generating penetration testing report...")
        
        # Run all penetration tests
        auth_results = await self.test_authentication_bypass()
        jwt_results = await self.test_jwt_security()
        authz_results = await self.test_authorization_flaws()
        injection_results = await self.test_injection_attacks()
        file_results = await self.test_file_upload_attacks()
        session_results = await self.test_session_management()
        
        # Compile comprehensive report
        report = {
            "report_metadata": {
                "generated_at": time.time(),
                "test_type": "Penetration Testing",
                "version": "1.0.0",
                "target": "Photo Sharing Service"
            },
            "executive_summary": {
                "total_tests_performed": 6,
                "vulnerabilities_found": len(self.findings),
                "critical_findings": len([f for f in self.findings if f["severity"] == "CRITICAL"]),
                "high_findings": len([f for f in self.findings if f["severity"] == "HIGH"]),
                "medium_findings": len([f for f in self.findings if f["severity"] == "MEDIUM"]),
                "low_findings": len([f for f in self.findings if f["severity"] == "LOW"]),
                "overall_risk_rating": self._calculate_overall_risk()
            },
            "test_results": {
                "authentication_bypass": auth_results,
                "jwt_security": jwt_results,
                "authorization_flaws": authz_results,
                "injection_attacks": injection_results,
                "file_upload_attacks": file_results,
                "session_management": session_results
            },
            "detailed_findings": self.findings,
            "recommendations": self._generate_recommendations(),
            "remediation_timeline": self._create_remediation_timeline()
        }
        
        return report
    
    def _calculate_overall_risk(self) -> str:
        """Calculate overall risk rating."""
        critical_count = len([f for f in self.findings if f["severity"] == "CRITICAL"])
        high_count = len([f for f in self.findings if f["severity"] == "HIGH"])
        
        if critical_count > 0:
            return "CRITICAL"
        elif high_count > 2:
            return "HIGH"
        elif high_count > 0:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations."""
        recommendations = [
            "Implement comprehensive input validation",
            "Use parameterized queries to prevent SQL injection",
            "Implement proper JWT token management and invalidation",
            "Enforce strict access controls and authorization checks",
            "Validate and sanitize all file uploads",
            "Implement rate limiting on authentication endpoints",
            "Use HTTPS for all communications",
            "Regular security testing and code reviews",
            "Implement comprehensive logging and monitoring"
        ]
        
        # Add specific recommendations based on findings
        if any(f["category"] == "Authentication Bypass" for f in self.findings):
            recommendations.append("🚨 URGENT: Fix authentication bypass vulnerabilities")
        
        if any(f["category"] == "JWT Security" for f in self.findings):
            recommendations.append("🚨 URGENT: Implement proper JWT validation")
        
        return recommendations
    
    def _create_remediation_timeline(self) -> Dict[str, List[str]]:
        """Create remediation timeline."""
        return {
            "immediate": [
                "Fix critical authentication bypasses",
                "Patch SQL injection vulnerabilities",
                "Implement JWT token validation"
            ],
            "week_1": [
                "Fix authorization flaws",
                "Implement file upload validation",
                "Add input sanitization"
            ],
            "week_2": [
                "Implement comprehensive logging",
                "Add rate limiting",
                "Security testing integration"
            ],
            "month_1": [
                "Security training for developers",
                "Regular penetration testing schedule",
                "Security monitoring implementation"
            ]
        }


@pytest.mark.security
@pytest.mark.penetration
@pytest.mark.asyncio
class TestPenetrationTesting:
    """Penetration testing test suite."""
    
    async def test_comprehensive_penetration_test(self, async_test_client: AsyncClient):
        """Run comprehensive penetration testing suite."""
        print("🎯 Starting comprehensive penetration testing...")
        
        tester = PenetrationTester(async_test_client)
        report = await tester.generate_penetration_report()
        
        # Write report to file
        with open("/tmp/penetration_testing_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate summary
        summary = f"""
=== PENETRATION TESTING REPORT ===

🎯 Target: Photo Sharing Service
📅 Date: {time.strftime('%Y-%m-%d %H:%M:%S')}

📊 EXECUTIVE SUMMARY:
- Overall Risk Rating: {report['executive_summary']['overall_risk_rating']}
- Total Vulnerabilities: {report['executive_summary']['vulnerabilities_found']}
- Critical: {report['executive_summary']['critical_findings']}
- High: {report['executive_summary']['high_findings']} 
- Medium: {report['executive_summary']['medium_findings']}
- Low: {report['executive_summary']['low_findings']}

🔍 TESTS PERFORMED:
- Authentication Bypass Testing
- JWT Security Assessment
- Authorization Flaw Testing
- Injection Attack Testing
- File Upload Security Testing
- Session Management Testing

📋 TOP RECOMMENDATIONS:
"""
        for rec in report['recommendations'][:5]:
            summary += f"- {rec}\n"
        
        with open("/tmp/penetration_testing_summary.txt", "w") as f:
            f.write(summary)
        
        print(summary)
        print(f"\n📄 Detailed reports saved:")
        print(f"   - JSON Report: /tmp/penetration_testing_report.json")
        print(f"   - Summary: /tmp/penetration_testing_summary.txt")
        
        # Test should pass unless critical vulnerabilities found
        critical_count = report['executive_summary']['critical_findings']
        assert critical_count == 0, f"Critical vulnerabilities found: {critical_count}"


if __name__ == "__main__":
    # For standalone execution
    print("🔒 Penetration Testing Suite")
    print("This module provides comprehensive penetration testing capabilities.")
    print("Run with: pytest tests/security/test_penetration_testing.py -v")