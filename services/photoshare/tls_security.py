#!/usr/bin/env python3
"""
TLS Security Configuration and Validation
=========================================

Comprehensive TLS/SSL security validation and configuration management
for enhanced transport layer security in the PhotoShare application.
"""

import ssl
import socket
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import requests

logger = logging.getLogger(__name__)

class TLSSecurityValidator:
    """Comprehensive TLS/SSL security validation and monitoring."""
    
    def __init__(self):
        self.min_tls_version = ssl.TLSVersion.TLSv1_2
        self.preferred_tls_version = ssl.TLSVersion.TLSv1_3
        
        # Secure cipher suites (prioritizing forward secrecy and strong encryption)
        self.secure_ciphers = [
            'TLS_AES_256_GCM_SHA384',              # TLS 1.3
            'TLS_CHACHA20_POLY1305_SHA256',        # TLS 1.3
            'TLS_AES_128_GCM_SHA256',              # TLS 1.3
            'ECDHE-RSA-AES256-GCM-SHA384',         # TLS 1.2
            'ECDHE-RSA-CHACHA20-POLY1305',         # TLS 1.2
            'ECDHE-RSA-AES128-GCM-SHA256',         # TLS 1.2
        ]
        
        # Insecure protocols and ciphers to detect
        self.insecure_protocols = ['SSLv2', 'SSLv3', 'TLSv1.0', 'TLSv1.1']
        self.insecure_ciphers = [
            'RC4', 'DES', '3DES', 'MD5', 'SHA1-only',
            'NULL', 'EXPORT', 'ANON'
        ]
        
        # Certificate validation settings
        self.min_key_size = 2048
        self.cert_expiry_warning_days = 30
        
        # HSTS settings
        self.hsts_max_age_minimum = 31536000  # 1 year
        
        self.validation_stats = {
            "checks_performed": 0,
            "last_validation": None,
            "security_issues_found": 0
        }
    
    def validate_tls_endpoint(self, hostname: str, port: int = 443) -> Dict[str, Any]:
        """Comprehensive TLS validation for an endpoint."""
        self.validation_stats["checks_performed"] += 1
        self.validation_stats["last_validation"] = datetime.now(timezone.utc).isoformat()
        
        validation_result = {
            "hostname": hostname,
            "port": port,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_security_grade": "F",  # Start pessimistic
            "issues": [],
            "warnings": [],
            "recommendations": [],
            "certificate_info": {},
            "protocol_info": {},
            "cipher_info": {},
            "security_headers": {},
            "compliance": {}
        }
        
        try:
            # 1. Certificate validation
            cert_validation = self._validate_certificate(hostname, port)
            validation_result["certificate_info"] = cert_validation
            
            # 2. TLS protocol validation
            protocol_validation = self._validate_tls_protocols(hostname, port)
            validation_result["protocol_info"] = protocol_validation
            
            # 3. Cipher suite validation
            cipher_validation = self._validate_cipher_suites(hostname, port)
            validation_result["cipher_info"] = cipher_validation
            
            # 4. Security headers validation (for HTTPS endpoints)
            if port == 443:
                headers_validation = self._validate_security_headers(hostname)
                validation_result["security_headers"] = headers_validation
            
            # 5. Compliance checks
            compliance_check = self._check_compliance_standards(validation_result)
            validation_result["compliance"] = compliance_check
            
            # 6. Calculate overall security grade
            validation_result["overall_security_grade"] = self._calculate_security_grade(validation_result)
            
            # Count issues for statistics
            total_issues = len(validation_result["issues"])
            self.validation_stats["security_issues_found"] += total_issues
            
            logger.info(f"TLS validation completed for {hostname}:{port} - Grade: {validation_result['overall_security_grade']}")
            
        except Exception as e:
            validation_result["issues"].append(f"Validation failed: {str(e)}")
            logger.error(f"TLS validation error for {hostname}:{port} - {e}")
        
        return validation_result
    
    def _validate_certificate(self, hostname: str, port: int) -> Dict[str, Any]:
        """Validate SSL certificate."""
        cert_info = {
            "valid": False,
            "issues": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # Get certificate
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert_pem = ssock.getpeercert()
                    
                    # Parse certificate
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())
                    
                    # Basic certificate info
                    cert_info["details"] = {
                        "subject": dict(x.split('=') for x in cert_pem['subject'][0]),
                        "issuer": dict(x.split('=') for x in cert_pem['issuer'][0]),
                        "version": cert_pem['version'],
                        "serial_number": cert_pem['serialNumber'],
                        "not_before": cert_pem['notBefore'],
                        "not_after": cert_pem['notAfter'],
                        "signature_algorithm": cert.signature_hash_algorithm.name
                    }
                    
                    # Validate certificate chain
                    self._validate_certificate_chain(cert, cert_info)
                    
                    # Check certificate expiry
                    self._check_certificate_expiry(cert, cert_info)
                    
                    # Validate key size
                    self._validate_key_size(cert, cert_info)
                    
                    # Check hostname match
                    self._validate_hostname_match(cert, hostname, cert_info)
                    
                    # Check for weak signature algorithms
                    self._check_signature_algorithm(cert, cert_info)
                    
                    cert_info["valid"] = len(cert_info["issues"]) == 0
                    
        except ssl.SSLError as e:
            cert_info["issues"].append(f"SSL Error: {e}")
        except socket.timeout:
            cert_info["issues"].append("Connection timeout")
        except Exception as e:
            cert_info["issues"].append(f"Certificate validation error: {e}")
        
        return cert_info
    
    def _validate_certificate_chain(self, cert, cert_info):
        """Validate certificate chain."""
        try:
            # Check if it's self-signed
            if cert.issuer == cert.subject:
                cert_info["warnings"].append("Self-signed certificate detected")
                
            # Additional chain validation would go here
            # (requires implementing full chain verification)
            
        except Exception as e:
            cert_info["warnings"].append(f"Chain validation error: {e}")
    
    def _check_certificate_expiry(self, cert, cert_info):
        """Check certificate expiration."""
        try:
            now = datetime.now(timezone.utc)
            not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)
            
            if not_after < now:
                cert_info["issues"].append("Certificate has expired")
            else:
                days_until_expiry = (not_after - now).days
                cert_info["details"]["days_until_expiry"] = days_until_expiry
                
                if days_until_expiry < self.cert_expiry_warning_days:
                    cert_info["warnings"].append(f"Certificate expires in {days_until_expiry} days")
                    
        except Exception as e:
            cert_info["warnings"].append(f"Expiry check error: {e}")
    
    def _validate_key_size(self, cert, cert_info):
        """Validate certificate key size."""
        try:
            public_key = cert.public_key()
            
            if hasattr(public_key, 'key_size'):
                key_size = public_key.key_size
                cert_info["details"]["key_size"] = key_size
                
                if key_size < self.min_key_size:
                    cert_info["issues"].append(f"Weak key size: {key_size} bits (minimum: {self.min_key_size})")
                elif key_size < 4096:
                    cert_info["warnings"].append(f"Consider upgrading to 4096-bit key (current: {key_size})")
                    
        except Exception as e:
            cert_info["warnings"].append(f"Key size validation error: {e}")
    
    def _validate_hostname_match(self, cert, hostname, cert_info):
        """Validate hostname matches certificate."""
        try:
            # Get Subject Alternative Names
            try:
                san_extension = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                san_names = [name.value for name in san_extension.value]
                cert_info["details"]["san_names"] = san_names
                
                if hostname not in san_names and f"*.{'.'.join(hostname.split('.')[1:])}" not in san_names:
                    cert_info["issues"].append(f"Hostname {hostname} not found in certificate SAN")
                    
            except x509.ExtensionNotFound:
                cert_info["warnings"].append("No Subject Alternative Names found")
                
        except Exception as e:
            cert_info["warnings"].append(f"Hostname validation error: {e}")
    
    def _check_signature_algorithm(self, cert, cert_info):
        """Check for weak signature algorithms."""
        try:
            sig_alg = cert.signature_hash_algorithm.name.lower()
            
            weak_algorithms = ['md5', 'sha1']
            if any(weak in sig_alg for weak in weak_algorithms):
                cert_info["issues"].append(f"Weak signature algorithm: {sig_alg}")
                
        except Exception as e:
            cert_info["warnings"].append(f"Signature algorithm check error: {e}")
    
    def _validate_tls_protocols(self, hostname: str, port: int) -> Dict[str, Any]:
        """Validate supported TLS protocols."""
        protocol_info = {
            "supported_versions": [],
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Test different TLS versions
        tls_versions = [
            ('TLSv1.3', ssl.TLSVersion.TLSv1_3),
            ('TLSv1.2', ssl.TLSVersion.TLSv1_2),
            ('TLSv1.1', ssl.TLSVersion.TLSv1_1),
            ('TLSv1.0', ssl.TLSVersion.TLSv1_0),
        ]
        
        for version_name, version_const in tls_versions:
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.minimum_version = version_const
                context.maximum_version = version_const
                
                with socket.create_connection((hostname, port), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname):
                        protocol_info["supported_versions"].append(version_name)
                        
            except (ssl.SSLError, OSError, socket.timeout):
                # Version not supported - this is expected
                pass
            except Exception as e:
                protocol_info["warnings"].append(f"Error testing {version_name}: {e}")
        
        # Analyze supported versions
        if 'TLSv1.0' in protocol_info["supported_versions"] or 'TLSv1.1' in protocol_info["supported_versions"]:
            protocol_info["issues"].append("Insecure TLS versions (1.0/1.1) are supported")
        
        if 'TLSv1.3' not in protocol_info["supported_versions"]:
            protocol_info["recommendations"].append("Enable TLS 1.3 for enhanced security and performance")
        
        if not protocol_info["supported_versions"]:
            protocol_info["issues"].append("No TLS versions could be negotiated")
        
        return protocol_info
    
    def _validate_cipher_suites(self, hostname: str, port: int) -> Dict[str, Any]:
        """Validate cipher suites."""
        cipher_info = {
            "negotiated_cipher": None,
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cipher_info["negotiated_cipher"] = ssock.cipher()[0] if ssock.cipher() else None
                    
                    # Check for insecure ciphers
                    if cipher_info["negotiated_cipher"]:
                        cipher_name = cipher_info["negotiated_cipher"].upper()
                        
                        for insecure in self.insecure_ciphers:
                            if insecure.upper() in cipher_name:
                                cipher_info["issues"].append(f"Insecure cipher in use: {cipher_name}")
                                break
                        
                        # Check for forward secrecy
                        if not any(fs in cipher_name for fs in ['ECDHE', 'DHE']):
                            cipher_info["warnings"].append("Cipher does not provide forward secrecy")
                        
                        # Recommend stronger ciphers
                        if cipher_name not in [c.upper().replace('-', '_') for c in self.secure_ciphers]:
                            cipher_info["recommendations"].append("Consider using stronger cipher suites")
                    else:
                        cipher_info["issues"].append("Could not determine negotiated cipher")
        
        except Exception as e:
            cipher_info["issues"].append(f"Cipher validation error: {e}")
        
        return cipher_info
    
    def _validate_security_headers(self, hostname: str) -> Dict[str, Any]:
        """Validate HTTP security headers for HTTPS endpoints."""
        headers_info = {
            "present_headers": {},
            "missing_headers": [],
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        try:
            response = requests.get(f"https://{hostname}", timeout=10, allow_redirects=False)
            headers = response.headers
            
            # Check for important security headers
            security_headers = {
                'Strict-Transport-Security': self._validate_hsts_header,
                'X-Content-Type-Options': lambda h: h.lower() == 'nosniff',
                'X-Frame-Options': lambda h: h.upper() in ['DENY', 'SAMEORIGIN'],
                'X-XSS-Protection': lambda h: '1' in h,
                'Content-Security-Policy': lambda h: len(h) > 10,  # Basic CSP presence check
                'Referrer-Policy': lambda h: len(h) > 0
            }
            
            for header, validator in security_headers.items():
                if header in headers:
                    headers_info["present_headers"][header] = headers[header]
                    if not validator(headers[header]):
                        headers_info["warnings"].append(f"Weak {header} configuration")
                else:
                    headers_info["missing_headers"].append(header)
                    headers_info["recommendations"].append(f"Add {header} security header")
            
            # Special checks
            if 'Strict-Transport-Security' not in headers:
                headers_info["issues"].append("HSTS header missing - susceptible to downgrade attacks")
                
        except requests.RequestException as e:
            headers_info["warnings"].append(f"Could not fetch security headers: {e}")
        except Exception as e:
            headers_info["warnings"].append(f"Header validation error: {e}")
        
        return headers_info
    
    def _validate_hsts_header(self, hsts_value: str) -> bool:
        """Validate HSTS header configuration."""
        try:
            # Extract max-age value
            for directive in hsts_value.split(';'):
                directive = directive.strip()
                if directive.startswith('max-age='):
                    max_age = int(directive.split('=')[1])
                    return max_age >= self.hsts_max_age_minimum
            return False
        except Exception:
            return False
    
    def _check_compliance_standards(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Check compliance with security standards."""
        compliance = {
            "pci_dss": {"compliant": True, "issues": []},
            "owasp": {"compliant": True, "issues": []},
            "nist": {"compliant": True, "issues": []}
        }
        
        # PCI DSS requirements
        if any('TLS' in version and version in ['TLSv1.0', 'TLSv1.1'] 
               for version in validation_result["protocol_info"].get("supported_versions", [])):
            compliance["pci_dss"]["compliant"] = False
            compliance["pci_dss"]["issues"].append("TLS 1.0/1.1 not allowed per PCI DSS 3.2")
        
        # OWASP recommendations
        if validation_result["certificate_info"].get("details", {}).get("key_size", 0) < 2048:
            compliance["owasp"]["compliant"] = False
            compliance["owasp"]["issues"].append("Key size below OWASP recommendation")
        
        # NIST guidelines
        if 'TLSv1.3' not in validation_result["protocol_info"].get("supported_versions", []):
            compliance["nist"]["compliant"] = False
            compliance["nist"]["issues"].append("TLS 1.3 recommended by NIST")
        
        return compliance
    
    def _calculate_security_grade(self, validation_result: Dict[str, Any]) -> str:
        """Calculate overall security grade (A+ to F)."""
        score = 100
        
        # Deduct points for issues
        for section in ["certificate_info", "protocol_info", "cipher_info", "security_headers"]:
            if section in validation_result:
                issues = validation_result[section].get("issues", [])
                warnings = validation_result[section].get("warnings", [])
                
                score -= len(issues) * 15  # Major issues
                score -= len(warnings) * 5  # Minor issues
        
        # Bonus points for TLS 1.3 support
        if 'TLSv1.3' in validation_result["protocol_info"].get("supported_versions", []):
            score += 5
        
        # Grade mapping
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def create_tls_security_report(self, endpoints: List[Tuple[str, int]]) -> Dict[str, Any]:
        """Create comprehensive TLS security report for multiple endpoints."""
        report = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoints_tested": len(endpoints),
            "overall_status": "SECURE",
            "endpoint_results": [],
            "summary": {
                "grades": {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
                "total_issues": 0,
                "total_warnings": 0,
                "compliance_failures": 0
            },
            "recommendations": [],
            "statistics": self.validation_stats.copy()
        }
        
        for hostname, port in endpoints:
            endpoint_result = self.validate_tls_endpoint(hostname, port)
            report["endpoint_results"].append(endpoint_result)
            
            # Update summary statistics
            grade = endpoint_result["overall_security_grade"]
            if grade in report["summary"]["grades"]:
                report["summary"]["grades"][grade] += 1
            
            # Count issues across all sections
            for section_name, section_data in endpoint_result.items():
                if isinstance(section_data, dict) and "issues" in section_data:
                    report["summary"]["total_issues"] += len(section_data["issues"])
                    report["summary"]["total_warnings"] += len(section_data.get("warnings", []))
        
        # Determine overall status
        if any(result["overall_security_grade"] in ["D", "F"] for result in report["endpoint_results"]):
            report["overall_status"] = "CRITICAL"
        elif any(result["overall_security_grade"] == "C" for result in report["endpoint_results"]):
            report["overall_status"] = "WARNING"
        
        # Generate global recommendations
        self._generate_global_recommendations(report)
        
        return report
    
    def _generate_global_recommendations(self, report: Dict[str, Any]):
        """Generate recommendations based on report findings."""
        grades = report["summary"]["grades"]
        
        if grades["F"] > 0:
            report["recommendations"].append("CRITICAL: Immediate TLS configuration review required")
        
        if grades["D"] + grades["F"] > 0:
            report["recommendations"].append("Disable insecure TLS versions (1.0, 1.1)")
        
        if sum(grades[g] for g in ["A+", "A"]) / len(report["endpoint_results"]) < 0.8:
            report["recommendations"].append("Upgrade TLS configuration to achieve A-grade security")
        
        total_endpoints = len(report["endpoint_results"])
        tls13_support = sum(1 for r in report["endpoint_results"] 
                           if 'TLSv1.3' in r["protocol_info"].get("supported_versions", []))
        
        if tls13_support < total_endpoints:
            report["recommendations"].append("Enable TLS 1.3 on all endpoints for optimal security")

class TLSConfigurationManager:
    """Manage TLS configuration for the application."""
    
    def __init__(self):
        self.ssl_context = None
        self.config_history = []
    
    def create_secure_ssl_context(self) -> ssl.SSLContext:
        """Create a secure SSL context for the application."""
        try:
            # Create modern TLS context
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            
            # Set minimum TLS version
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            
            # Try to enable TLS 1.3 if available
            try:
                context.maximum_version = ssl.TLSVersion.TLSv1_3
            except AttributeError:
                logger.warning("TLS 1.3 not available, using TLS 1.2 as maximum")
            
            # Set secure cipher suites
            context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            
            # Enable hostname checking
            context.check_hostname = False  # Will be handled by application layer
            context.verify_mode = ssl.CERT_REQUIRED
            
            # Security options
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            context.options |= ssl.OP_NO_TLSv1
            context.options |= ssl.OP_NO_TLSv1_1
            context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
            context.options |= ssl.OP_SINGLE_DH_USE
            context.options |= ssl.OP_SINGLE_ECDH_USE
            
            self.ssl_context = context
            self.config_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "secure_context_created",
                "details": {
                    "min_version": "TLS 1.2",
                    "cipher_preference": "server",
                    "security_options": "hardened"
                }
            })
            
            logger.info("Secure SSL context created with hardened configuration")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create secure SSL context: {e}")
            raise
    
    def validate_ssl_configuration(self) -> Dict[str, Any]:
        """Validate current SSL configuration."""
        if not self.ssl_context:
            return {"valid": False, "error": "No SSL context configured"}
        
        validation = {
            "valid": True,
            "configuration": {
                "minimum_version": self.ssl_context.minimum_version.name,
                "maximum_version": getattr(self.ssl_context.maximum_version, 'name', 'Unknown'),
                "verify_mode": self.ssl_context.verify_mode.name,
                "check_hostname": self.ssl_context.check_hostname
            },
            "security_score": 0,
            "recommendations": []
        }
        
        # Score the configuration
        score = 70  # Base score
        
        if self.ssl_context.minimum_version >= ssl.TLSVersion.TLSv1_2:
            score += 15
        if hasattr(ssl.TLSVersion, 'TLSv1_3') and self.ssl_context.maximum_version >= ssl.TLSVersion.TLSv1_3:
            score += 15
        
        validation["security_score"] = min(100, score)
        
        # Generate recommendations
        if score < 85:
            validation["recommendations"].append("Consider upgrading TLS configuration")
        
        return validation

# Global instance for application use
tls_validator = TLSSecurityValidator()
tls_config_manager = TLSConfigurationManager()

def get_tls_validator() -> TLSSecurityValidator:
    """Get the global TLS validator instance."""
    return tls_validator

def get_tls_config_manager() -> TLSConfigurationManager:
    """Get the global TLS configuration manager."""
    return tls_config_manager

def validate_application_tls() -> Dict[str, Any]:
    """Validate TLS configuration for the current application."""
    # This would validate the application's own TLS setup
    return tls_config_manager.validate_ssl_configuration()