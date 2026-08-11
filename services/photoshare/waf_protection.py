#!/usr/bin/env python3
"""
Web Application Firewall (WAF) Protection
==========================================

Implements WAF functionality to protect against common web attacks:
- SQL Injection detection and blocking
- XSS (Cross-Site Scripting) prevention
- CSRF protection enhancement  
- Rate limiting and DDoS protection
- File upload validation
- Request sanitization
"""

import re
import time
import hashlib
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import ipaddress
import urllib.parse


logger = logging.getLogger(__name__)


# Import security monitoring (with fallback if not available)
try:
    from security_monitoring import log_security_event, security_monitor
    SECURITY_MONITORING_ENABLED = True
except ImportError:
    SECURITY_MONITORING_ENABLED = False
    
    def log_security_event(*args, **kwargs):
        pass


@dataclass
class ThreatDetection:
    """Threat detection result."""
    threat_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    blocked: bool
    details: Dict


class WAFProtection:
    """Web Application Firewall Protection System."""
    
    def __init__(self):
        # SQL Injection patterns
        self.sql_injection_patterns = [
            r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|UNION|EXEC|EXECUTE)\b",
            r"(--|#|\/\*|\*\/)",  # SQL comments
            r"\b(OR|AND)\b\s*\d+\s*=\s*\d+",  # Boolean-based SQLi
            r"\b(OR|AND)\b\s*[\"'].*[\"']\s*=\s*[\"'].*[\"']",  # String-based SQLi  
            r"(UNION\s+SELECT|UNION\s+ALL\s+SELECT)",  # UNION-based SQLi
            r"\bINTO\s+(OUTFILE|DUMPFILE)\b",  # File operations
            r"\b(LOAD_FILE|INTO\s+LOADFILE)\b",  # MySQL functions
            r"\b(xp_cmdshell|sp_executesql)\b",  # SQL Server functions
            r"\b(WAITFOR\s+DELAY|PG_SLEEP)\b",  # Time-based SQLi
            r"'\s*(OR|AND)\s*'",  # Basic SQLi patterns
            r"'\s*=\s*'",  # Equal comparison
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<\s*script[^>]*>.*?<\s*/\s*script\s*>",  # Script tags
            r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>",  # Iframe tags
            r"<\s*object[^>]*>.*?<\s*/\s*object\s*>",  # Object tags
            r"<\s*embed[^>]*>",  # Embed tags
            r"javascript\s*:",  # JavaScript protocol
            r"vbscript\s*:",  # VBScript protocol
            r"on\w+\s*=",  # Event handlers (onclick, onload, etc.)
            r"expression\s*\(",  # CSS expressions
            r"<\s*link[^>]*javascript:",  # Link with JavaScript
            r"<\s*meta[^>]*refresh",  # Meta refresh attacks
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r"\.\.[\\/]",  # Directory traversal
            r"[\\/]\.\.[\\/]",  # Path traversal
            r"%2e%2e[\\/]",  # URL-encoded traversal
            r"[\\/]etc[\\/]passwd",  # Linux passwd file
            r"[\\/]windows[\\/]system32",  # Windows system directory
            r"\.htaccess",  # Apache config file
            r"web\.config",  # IIS config file
        ]
        
        # Command injection patterns.
        # Deliberately no longer includes a bare shell-metacharacter class
        # (r"[;&|`$(){}]"): a single stray ';', '&', '(', etc. is extremely common
        # in benign text (User-Agent strings, JSON bodies, query strings) and made
        # this the single biggest source of WAF false positives. Real injection
        # attempts pair a metacharacter with an actual command or chaining syntax,
        # which the patterns below already catch.
        self.command_injection_patterns = [
            r"\b(cat|ls|ps|id|whoami|uname|netstat|ifconfig)\b",  # Common commands
            r"(&&|\|\|)",  # Command chaining
            r"\$\([^)]+\)",  # Command substitution
            r"`[^`]+`",  # Backtick command execution
        ]
        
        # Rate limiting
        self.request_counts = defaultdict(deque)  # IP -> timestamps
        self.blocked_ips = {}  # IP -> block_until_timestamp
        self.suspicious_ips = set()  # IPs with multiple violations
        
        # Request pattern analysis
        self.request_patterns = defaultdict(list)  # IP -> request signatures
        
        # Blocked user agents and referrers
        self.blocked_user_agents = {
            "sqlmap", "nikto", "dirb", "gobuster", "wpscan", "nessus",
            "burpsuite", "zap", "w3af", "havij", "xmlrpc"
        }
        
        # Honeypot paths (paths that should never be accessed)
        self.honeypot_paths = {
            "/admin", "/wp-admin", "/phpmyadmin", "/.git", "/.env",
            "/config", "/backup", "/database", "/sql", "/dump"
        }
        
        # File upload restrictions
        self.allowed_extensions = {
            # Photos
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
            # Videos (see video_processing/video_processor.py SUPPORTED_FORMATS)
            ".mp4", ".avi", ".mov", ".webm", ".mkv", ".flv", ".wmv", ".m4v", ".3gp", ".ogv",
        }
        self.blocked_extensions = {
            ".php", ".asp", ".jsp", ".py", ".pl", ".cgi", ".sh", ".bat", 
            ".exe", ".dll", ".so", ".jar", ".war", ".ear"
        }
        
        # CSRF token management
        self.csrf_tokens = {}  # session_id -> (token, timestamp)
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "threats_detected": defaultdict(int),
            "top_blocked_ips": defaultdict(int)
        }
    
    def get_client_ip(self, request: Request) -> str:
        """Get real client IP considering proxy headers."""
        # Check common proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to connection IP
        return request.client.host if request.client else "unknown"
    
    def is_rate_limited(self, ip: str) -> bool:
        """Check if IP is rate limited."""
        current_time = time.time()
        
        # Check if IP is currently blocked
        if ip in self.blocked_ips:
            if current_time < self.blocked_ips[ip]:
                return True
            else:
                # Block expired, remove it
                del self.blocked_ips[ip]
        
        # Clean old requests (older than 60 seconds)
        request_times = self.request_counts[ip]
        while request_times and current_time - request_times[0] > 60:
            request_times.popleft()
        
        # Add current request
        request_times.append(current_time)
        
        # Check rate limits
        requests_per_minute = len(request_times)
        
        if requests_per_minute > 100:  # More than 100 requests per minute
            # Block for 15 minutes
            self.blocked_ips[ip] = current_time + (15 * 60)
            self.suspicious_ips.add(ip)
            logger.warning(f"Rate limit exceeded for IP {ip}: {requests_per_minute} requests/min")
            return True
        
        return False
    
    def detect_sql_injection(self, text: str) -> Optional[ThreatDetection]:
        """Detect SQL injection attempts."""
        text_lower = text.lower()
        
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return ThreatDetection(
                    threat_type="sql_injection",
                    severity="CRITICAL",
                    description=f"SQL injection pattern detected: {pattern}",
                    blocked=True,
                    details={"pattern": pattern, "input": text[:100]}
                )
        
        return None
    
    def detect_xss(self, text: str) -> Optional[ThreatDetection]:
        """Detect XSS attempts."""
        text_decoded = urllib.parse.unquote(text)
        
        for pattern in self.xss_patterns:
            if re.search(pattern, text_decoded, re.IGNORECASE):
                return ThreatDetection(
                    threat_type="xss",
                    severity="HIGH",
                    description=f"XSS pattern detected: {pattern}",
                    blocked=True,
                    details={"pattern": pattern, "input": text[:100]}
                )
        
        return None
    
    def detect_path_traversal(self, text: str) -> Optional[ThreatDetection]:
        """Detect path traversal attempts."""
        text_decoded = urllib.parse.unquote(text)
        
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, text_decoded, re.IGNORECASE):
                return ThreatDetection(
                    threat_type="path_traversal",
                    severity="HIGH",
                    description=f"Path traversal pattern detected: {pattern}",
                    blocked=True,
                    details={"pattern": pattern, "input": text[:100]}
                )
        
        return None
    
    def detect_command_injection(self, text: str) -> Optional[ThreatDetection]:
        """Detect command injection attempts."""
        text_decoded = urllib.parse.unquote(text)
        
        for pattern in self.command_injection_patterns:
            if re.search(pattern, text_decoded, re.IGNORECASE):
                return ThreatDetection(
                    threat_type="command_injection",
                    severity="CRITICAL",
                    description=f"Command injection pattern detected: {pattern}",
                    blocked=True,
                    details={"pattern": pattern, "input": text[:100]}
                )
        
        return None
    
    def check_honeypot_access(self, path: str) -> Optional[ThreatDetection]:
        """Check if request is accessing honeypot paths."""
        path_lower = path.lower()
        
        for honeypot in self.honeypot_paths:
            if honeypot in path_lower:
                return ThreatDetection(
                    threat_type="honeypot_access",
                    severity="HIGH",
                    description=f"Access to honeypot path: {honeypot}",
                    blocked=True,
                    details={"honeypot_path": honeypot, "requested_path": path}
                )
        
        return None
    
    def check_user_agent(self, user_agent: str) -> Optional[ThreatDetection]:
        """Check for malicious user agents."""
        if not user_agent:
            return ThreatDetection(
                threat_type="missing_user_agent",
                severity="MEDIUM",
                description="Request missing User-Agent header",
                blocked=False,
                details={"user_agent": ""}
            )
        
        user_agent_lower = user_agent.lower()
        
        for blocked_agent in self.blocked_user_agents:
            if blocked_agent in user_agent_lower:
                return ThreatDetection(
                    threat_type="malicious_user_agent",
                    severity="HIGH",
                    description=f"Malicious user agent detected: {blocked_agent}",
                    blocked=True,
                    details={"user_agent": user_agent}
                )
        
        return None
    
    def validate_file_upload(self, filename: str, content: bytes) -> Optional[ThreatDetection]:
        """Validate file uploads for security threats."""
        if not filename:
            return ThreatDetection(
                threat_type="invalid_filename",
                severity="MEDIUM",
                description="Missing filename in upload",
                blocked=True,
                details={"filename": filename}
            )
        
        # Check file extension
        filename_lower = filename.lower()
        file_ext = None
        
        for ext in self.allowed_extensions:
            if filename_lower.endswith(ext):
                file_ext = ext
                break
        
        if not file_ext:
            return ThreatDetection(
                threat_type="invalid_file_extension",
                severity="HIGH",
                description=f"Invalid file extension: {filename}",
                blocked=True,
                details={"filename": filename}
            )
        
        # Check for blocked extensions
        for blocked_ext in self.blocked_extensions:
            if filename_lower.endswith(blocked_ext):
                return ThreatDetection(
                    threat_type="blocked_file_extension",
                    severity="CRITICAL",
                    description=f"Blocked file extension: {blocked_ext}",
                    blocked=True,
                    details={"filename": filename, "extension": blocked_ext}
                )
        
        # Check file content for malicious patterns
        if content:
            content_text = content.decode('utf-8', errors='ignore')[:1000]  # First 1KB
            
            # Check for script content in images
            if any(pattern in content_text.lower() for pattern in ['<script', '<?php', '<%', 'javascript:', 'eval(']):
                return ThreatDetection(
                    threat_type="malicious_file_content",
                    severity="CRITICAL",
                    description="Malicious content detected in file",
                    blocked=True,
                    details={"filename": filename}
                )
        
        return None
    
    def analyze_request_pattern(self, ip: str, request: Request) -> Optional[ThreatDetection]:
        """Analyze request patterns for anomalies."""
        # Create request signature
        signature = f"{request.method}:{request.url.path}:{len(str(request.query_params))}"
        
        # Store request pattern
        self.request_patterns[ip].append({
            "timestamp": time.time(),
            "signature": signature,
            "user_agent": request.headers.get("user-agent", ""),
            "method": request.method
        })
        
        # Keep only recent patterns (last hour)
        current_time = time.time()
        self.request_patterns[ip] = [
            p for p in self.request_patterns[ip] 
            if current_time - p["timestamp"] < 3600
        ]
        
        patterns = self.request_patterns[ip]
        
        # Check for scanning behavior
        if len(patterns) > 50:  # More than 50 requests in an hour
            unique_paths = len(set(p["signature"].split(":")[1] for p in patterns))
            
            if unique_paths > 30:  # Accessing many different paths
                return ThreatDetection(
                    threat_type="directory_scanning",
                    severity="HIGH",
                    description=f"Directory scanning detected: {unique_paths} unique paths",
                    blocked=True,
                    details={
                        "ip": ip,
                        "unique_paths": unique_paths,
                        "total_requests": len(patterns)
                    }
                )
        
        # Check for brute force patterns
        login_attempts = [p for p in patterns if "/login" in p["signature"] or "/auth" in p["signature"]]
        if len(login_attempts) > 10:  # More than 10 login attempts
            return ThreatDetection(
                threat_type="brute_force_attempt",
                severity="HIGH",
                description=f"Brute force attempt detected: {len(login_attempts)} login attempts",
                blocked=True,
                details={
                    "ip": ip,
                    "login_attempts": len(login_attempts)
                }
            )
        
        return None
    
    async def protect_request(self, request: Request) -> Optional[JSONResponse]:
        """Main WAF protection function."""
        self.stats["total_requests"] += 1
        
        client_ip = self.get_client_ip(request)
        threats = []
        
        # Rate limiting check
        if self.is_rate_limited(client_ip):
            self.stats["blocked_requests"] += 1
            self.stats["threats_detected"]["rate_limit"] += 1
            self.stats["top_blocked_ips"][client_ip] += 1
            
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 900  # 15 minutes
                }
            )
        
        # User agent check
        user_agent = request.headers.get("user-agent", "")
        user_agent_threat = self.check_user_agent(user_agent)
        if user_agent_threat and user_agent_threat.blocked:
            threats.append(user_agent_threat)
        
        # Honeypot check
        path = str(request.url.path)
        honeypot_threat = self.check_honeypot_access(path)
        if honeypot_threat:
            threats.append(honeypot_threat)
        
        # Request pattern analysis
        pattern_threat = self.analyze_request_pattern(client_ip, request)
        if pattern_threat:
            threats.append(pattern_threat)
        
        # Input validation (URL parameters, headers, etc.)
        inputs_to_check = []
        
        # Check query parameters
        for key, value in request.query_params.items():
            inputs_to_check.append(f"{key}={value}")
        
        # Check common headers
        for header in ["referer", "x-forwarded-for", "cookie"]:
            header_value = request.headers.get(header)
            if header_value:
                inputs_to_check.append(header_value)
        
        # Check URL path
        inputs_to_check.append(path)
        
        # Run threat detection on all inputs
        for input_text in inputs_to_check:
            # SQL Injection
            sql_threat = self.detect_sql_injection(input_text)
            if sql_threat:
                threats.append(sql_threat)
            
            # XSS
            xss_threat = self.detect_xss(input_text)
            if xss_threat:
                threats.append(xss_threat)
            
            # Path Traversal
            path_threat = self.detect_path_traversal(input_text)
            if path_threat:
                threats.append(path_threat)
            
            # Command Injection
            cmd_threat = self.detect_command_injection(input_text)
            if cmd_threat:
                threats.append(cmd_threat)
        
        # Process threats
        blocking_threats = [t for t in threats if t.blocked]
        
        if blocking_threats:
            self.stats["blocked_requests"] += 1
            self.stats["top_blocked_ips"][client_ip] += 1
            
            for threat in blocking_threats:
                self.stats["threats_detected"][threat.threat_type] += 1
                logger.warning(f"WAF blocked request from {client_ip}: {threat.description}")
                
                # Log to security monitoring system
                if SECURITY_MONITORING_ENABLED:
                    log_security_event(
                        severity="HIGH" if threat.threat_type in ["sql_injection", "command_injection"] else "MEDIUM",
                        threat_type=threat.threat_type,
                        source_ip=client_ip,
                        endpoint=path,
                        method=request.method,
                        description=threat.description,
                        details=threat.details,
                        user_agent=user_agent
                    )
            
            # Add to suspicious IPs
            self.suspicious_ips.add(client_ip)
            
            # Update security monitoring metrics
            if SECURITY_MONITORING_ENABLED:
                security_monitor.update_request_metrics(blocked=True)
            
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Request blocked by WAF",
                    "message": "Your request has been blocked by our security system.",
                    "incident_id": hashlib.md5(f"{client_ip}{time.time()}".encode()).hexdigest()[:8]
                }
            )
        
        # Log non-blocking threats for monitoring
        for threat in threats:
            if not threat.blocked:
                logger.info(f"WAF detected non-blocking threat from {client_ip}: {threat.description}")
        
        # Update security monitoring metrics for allowed requests
        if SECURITY_MONITORING_ENABLED:
            security_monitor.update_request_metrics(blocked=False)
        
        return None  # Request allowed
    
    def get_security_stats(self) -> Dict:
        """Get WAF security statistics."""
        current_time = time.time()
        
        # Count active blocks
        active_blocks = sum(1 for block_time in self.blocked_ips.values() if block_time > current_time)
        
        return {
            "total_requests": self.stats["total_requests"],
            "blocked_requests": self.stats["blocked_requests"],
            "block_percentage": round((self.stats["blocked_requests"] / max(self.stats["total_requests"], 1)) * 100, 2),
            "active_ip_blocks": active_blocks,
            "suspicious_ips": len(self.suspicious_ips),
            "threats_by_type": dict(self.stats["threats_detected"]),
            "top_blocked_ips": dict(sorted(self.stats["top_blocked_ips"].items(), key=lambda x: x[1], reverse=True)[:10]),
            "honeypot_paths": list(self.honeypot_paths),
            "blocked_extensions": list(self.blocked_extensions)
        }


# Global WAF instance
waf = WAFProtection()


async def waf_middleware(request: Request, call_next):
    """FastAPI middleware for WAF protection."""
    # Skip WAF for health checks and metrics
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    # Apply WAF protection
    block_response = await waf.protect_request(request)
    if block_response:
        return block_response
    
    # Continue with normal request processing
    response = await call_next(request)
    return response


def validate_file_upload_waf(filename: str, content: bytes) -> bool:
    """Validate file upload through WAF."""
    threat = waf.validate_file_upload(filename, content)
    if threat and threat.blocked:
        logger.warning(f"WAF blocked file upload: {threat.description}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File upload blocked: {threat.description}"
        )
    return True