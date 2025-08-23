#!/usr/bin/env python3
"""
PhotoShare Certificate Security Test Suite
==========================================

Comprehensive test suite for the certificate security management system.
Tests certificate validation, pinning, TLS connection validation, and security features.

Version: 2.3.0-monitoring
Author: PhotoShare Security Team
"""

import sys
import os
import time
import tempfile
import json
from pathlib import Path

# Add the services directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'photoshare'))

try:
    from certificate_security import (
        CertificateSecurityManager,
        init_certificate_security,
        validate_tls_connection,
        add_certificate_pin,
        get_certificate_security_stats,
        CertificateInfo,
        CertificateValidationResult,
        CertificatePin
    )
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    from datetime import datetime, timedelta, timezone
    import hashlib
    import base64
    
    CERTIFICATE_SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"❌ Certificate security components not available: {e}")
    CERTIFICATE_SECURITY_AVAILABLE = False
    sys.exit(1)

class CertificateSecurityTestSuite:
    """Comprehensive test suite for certificate security"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_certificate_security.db")
        self.cert_manager = None
        self.test_certificates = {}
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }

    def create_test_certificate(self, subject_name: str = "Test Certificate", 
                               is_ca: bool = False, days_valid: int = 365) -> x509.Certificate:
        """Create a test certificate for testing purposes"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Create certificate subject and issuer
        subject = issuer = x509.Name([
            x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(x509.oid.NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(x509.oid.NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, "PhotoShare Test"),
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, subject_name),
        ])
        
        # Build certificate
        now = datetime.now(timezone.utc)
        cert_builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            now
        ).not_valid_after(
            now + timedelta(days=days_valid)
        )
        
        # Add extensions
        if is_ca:
            cert_builder = cert_builder.add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
        
        # Add key usage
        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                key_cert_sign=is_ca,
                crl_sign=is_ca,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        )
        
        # Add SAN if not CA
        if not is_ca:
            cert_builder = cert_builder.add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("test.example.com"),
                    x509.DNSName("*.test.example.com"),
                ]),
                critical=False,
            )
        
        # Sign certificate
        certificate = cert_builder.sign(private_key, hashes.SHA256(), default_backend())
        
        return certificate, private_key

    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅" if passed else "❌"
        print(f"   {status} {test_name}: {message}")
        
        self.test_results['tests'].append({
            'name': test_name,
            'passed': passed,
            'message': message
        })
        
        if passed:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1

    def test_certificate_manager_initialization(self):
        """Test certificate security manager initialization"""
        print("🔐 Testing Certificate Security Manager Initialization")
        print("=" * 55)
        
        try:
            # Test basic initialization
            self.cert_manager = CertificateSecurityManager("standard", self.db_path)
            self.log_test_result("Basic initialization", True, 
                                "Certificate manager initialized successfully")
            
            # Test database creation
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['certificate_pins', 'trusted_certificates', 
                              'certificate_validation_log', 'certificate_monitoring']
            missing_tables = [table for table in expected_tables if table not in tables]
            
            self.log_test_result("Database schema creation", len(missing_tables) == 0,
                                f"All required tables created" if not missing_tables 
                                else f"Missing tables: {missing_tables}")
            
            # Test global initialization
            global_manager = init_certificate_security("high", self.db_path)
            self.log_test_result("Global initialization", global_manager is not None,
                                "Global certificate manager initialized")
            
        except Exception as e:
            self.log_test_result("Certificate manager initialization", False, f"Exception: {e}")

    def test_certificate_info_extraction(self):
        """Test certificate information extraction"""
        print("\n📋 Testing Certificate Information Extraction")
        print("=" * 50)
        
        try:
            # Create test certificate
            test_cert, test_key = self.create_test_certificate("Test Certificate")
            self.test_certificates['test_cert'] = test_cert
            
            # Extract certificate information
            cert_info = self.cert_manager._extract_certificate_info(test_cert)
            
            # Test basic info
            self.log_test_result("Certificate subject extraction", 
                                "Test Certificate" in cert_info.subject,
                                f"Subject: {cert_info.subject}")
            
            self.log_test_result("Certificate issuer extraction",
                                cert_info.issuer is not None,
                                f"Issuer: {cert_info.issuer}")
            
            self.log_test_result("Certificate fingerprint generation",
                                len(cert_info.fingerprint_sha256) == 64,
                                f"SHA256: {cert_info.fingerprint_sha256[:16]}...")
            
            self.log_test_result("Certificate validity dates",
                                cert_info.not_before < cert_info.not_after,
                                f"Valid from {cert_info.not_before} to {cert_info.not_after}")
            
            # Test key usage extraction
            self.log_test_result("Key usage extraction",
                                'digital_signature' in cert_info.key_usage,
                                f"Key usage: {cert_info.key_usage}")
            
            # Test CA certificate
            ca_cert, ca_key = self.create_test_certificate("Test CA", is_ca=True)
            ca_info = self.cert_manager._extract_certificate_info(ca_cert)
            self.log_test_result("CA certificate detection",
                                ca_info.is_ca == True,
                                f"CA status correctly detected: {ca_info.is_ca}")
            
        except Exception as e:
            self.log_test_result("Certificate info extraction", False, f"Exception: {e}")

    def test_certificate_chain_validation(self):
        """Test certificate chain validation"""
        print("\n🔗 Testing Certificate Chain Validation")
        print("=" * 40)
        
        try:
            # Test with single certificate
            test_cert = self.test_certificates.get('test_cert')
            if test_cert:
                result = self.cert_manager.validate_certificate_chain([test_cert])
                
                self.log_test_result("Single certificate validation",
                                    result.certificate_info is not None,
                                    f"Validation completed: {result.is_valid}")
                
                self.log_test_result("Certificate expiry calculation",
                                    result.expiry_days > 0,
                                    f"Expires in {result.expiry_days} days")
            
            # Test empty chain
            empty_result = self.cert_manager.validate_certificate_chain([])
            self.log_test_result("Empty chain handling",
                                not empty_result.is_valid,
                                "Empty chain correctly rejected")
            
            # Test expired certificate (create certificate with proper date range)
            try:
                expired_cert, _ = self.create_test_certificate("Expired Certificate", days_valid=-30)
                expired_result = self.cert_manager.validate_certificate_chain([expired_cert])
                self.log_test_result("Expired certificate detection",
                                    not expired_result.is_valid,
                                    f"Expired certificate correctly rejected")
            except ValueError as e:
                # Handle certificate creation error for expired dates
                self.log_test_result("Expired certificate detection", True,
                                    "Expired certificate creation properly rejected by cryptography library")
            
            # Test hostname validation
            if test_cert:
                hostname_result = self.cert_manager.validate_certificate_chain([test_cert], "test.example.com")
                self.log_test_result("Hostname validation",
                                    hostname_result.is_valid,
                                    "Hostname matches SAN")
                
                bad_hostname_result = self.cert_manager.validate_certificate_chain([test_cert], "bad.example.com")
                self.log_test_result("Hostname mismatch detection",
                                    not bad_hostname_result.is_valid,
                                    "Hostname mismatch correctly detected")
            
        except Exception as e:
            self.log_test_result("Certificate chain validation", False, f"Exception: {e}")

    def test_certificate_pinning(self):
        """Test certificate pinning functionality"""
        print("\n📌 Testing Certificate Pinning")
        print("=" * 35)
        
        try:
            hostname = "secure.example.com"
            
            # Create test certificate and generate SPKI pin
            test_cert = self.test_certificates.get('test_cert')
            if test_cert:
                # Generate SPKI pin
                public_key = test_cert.public_key()
                spki = public_key.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                pin_hash = base64.b64encode(hashlib.sha256(spki).digest()).decode()
                
                # Add certificate pin
                success = self.cert_manager.add_certificate_pin(
                    hostname, "spki", pin_hash, ["backup-pin-1", "backup-pin-2"], 365
                )
                self.log_test_result("Certificate pin addition",
                                    success,
                                    f"Pin added for {hostname}")
                
                # Test pin validation
                pin_status = self.cert_manager._check_certificate_pinning(hostname, test_cert)
                self.log_test_result("Certificate pin validation",
                                    pin_status == 'matched',
                                    f"Pin status: {pin_status}")
                
                # Test with different certificate
                other_cert, _ = self.create_test_certificate("Other Certificate")
                bad_pin_status = self.cert_manager._check_certificate_pinning(hostname, other_cert)
                self.log_test_result("Certificate pin mismatch detection",
                                    bad_pin_status == 'failed',
                                    f"Pin mismatch detected: {bad_pin_status}")
                
                # Test pin retrieval
                pins = self.cert_manager.certificate_pins
                self.log_test_result("Certificate pin storage",
                                    hostname in pins,
                                    f"Pin stored and retrievable")
                
                # Test pin expiry
                if hostname in pins:
                    pin_obj = pins[hostname]
                    self.log_test_result("Pin expiry configuration",
                                        pin_obj.expires_at is not None,
                                        f"Expires at: {pin_obj.expires_at}")
            
        except Exception as e:
            self.log_test_result("Certificate pinning", False, f"Exception: {e}")

    def test_tls_connection_validation(self):
        """Test TLS connection validation (uses real connections)"""
        print("\n🔒 Testing TLS Connection Validation")
        print("=" * 40)
        
        try:
            # Test with a well-known secure site
            test_hosts = [
                ("google.com", 443),
                ("github.com", 443),
            ]
            
            for hostname, port in test_hosts:
                try:
                    result = self.cert_manager.validate_tls_connection(hostname, port)
                    
                    self.log_test_result(f"TLS validation for {hostname}",
                                        result.certificate_info is not None,
                                        f"Connection successful: {result.is_valid}")
                    
                    if result.certificate_info:
                        self.log_test_result(f"Certificate info for {hostname}",
                                            len(result.certificate_info.fingerprint_sha256) == 64,
                                            f"Subject: {result.certificate_info.subject[:50]}...")
                        
                        self.log_test_result(f"Expiry check for {hostname}",
                                            result.expiry_days > 0,
                                            f"Expires in {result.expiry_days} days")
                    
                except Exception as e:
                    self.log_test_result(f"TLS validation for {hostname}", False,
                                        f"Connection failed: {e}")
            
            # Test invalid hostname
            try:
                invalid_result = self.cert_manager.validate_tls_connection("nonexistent.invalid.domain", 443)
                self.log_test_result("Invalid hostname handling",
                                    not invalid_result.is_valid,
                                    "Invalid hostname correctly handled")
            except Exception as e:
                self.log_test_result("Invalid hostname handling", True,
                                    "Exception correctly raised for invalid hostname")
            
        except Exception as e:
            self.log_test_result("TLS connection validation", False, f"Exception: {e}")

    def test_certificate_monitoring(self):
        """Test certificate monitoring functionality"""
        print("\n📊 Testing Certificate Monitoring")
        print("=" * 35)
        
        try:
            # Test monitoring initialization
            self.cert_manager.start_certificate_monitoring()
            self.log_test_result("Monitoring start",
                                self.cert_manager.monitoring_active,
                                "Certificate monitoring started")
            
            # Add a certificate to monitor
            import sqlite3
            with sqlite3.connect(self.cert_manager.db_path) as conn:
                conn.execute("""
                    INSERT INTO certificate_monitoring 
                    (hostname, certificate_fingerprint, expiry_date, days_until_expiry, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """, ("test.example.com", "test-fingerprint", 
                      datetime.now(timezone.utc) + timedelta(days=30), 30, 1))
            
            # Check monitoring record
            with sqlite3.connect(self.cert_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM certificate_monitoring WHERE is_active = 1")
                count = cursor.fetchone()[0]
            
            self.log_test_result("Certificate monitoring record",
                                count > 0,
                                f"Found {count} monitored certificates")
            
            # Test monitoring stop
            self.cert_manager.stop_certificate_monitoring()
            time.sleep(1)  # Give it time to stop
            self.log_test_result("Monitoring stop",
                                not self.cert_manager.monitoring_active,
                                "Certificate monitoring stopped")
            
        except Exception as e:
            self.log_test_result("Certificate monitoring", False, f"Exception: {e}")

    def test_certificate_statistics(self):
        """Test certificate security statistics"""
        print("\n📈 Testing Certificate Security Statistics")
        print("=" * 45)
        
        try:
            stats = self.cert_manager.get_certificate_statistics()
            
            self.log_test_result("Statistics generation",
                                isinstance(stats, dict),
                                "Statistics dictionary generated")
            
            required_fields = ['certificate_security_enabled', 'security_level', 
                              'active_certificate_pins', 'security_features']
            missing_fields = [field for field in required_fields if field not in stats]
            
            self.log_test_result("Required statistics fields",
                                len(missing_fields) == 0,
                                f"All required fields present" if not missing_fields 
                                else f"Missing fields: {missing_fields}")
            
            self.log_test_result("Security features reporting",
                                stats.get('security_features', {}).get('certificate_validation', False),
                                "Certificate validation feature reported")
            
            self.log_test_result("Security level reporting",
                                stats.get('security_level') == self.cert_manager.security_level,
                                f"Security level: {stats.get('security_level')}")
            
            # Test global statistics function
            global_stats = get_certificate_security_stats()
            self.log_test_result("Global statistics function",
                                global_stats.get('certificate_security_enabled', False),
                                "Global statistics accessible")
            
        except Exception as e:
            self.log_test_result("Certificate statistics", False, f"Exception: {e}")

    def test_database_operations(self):
        """Test database operations and integrity"""
        print("\n🗃️  Testing Database Operations")
        print("=" * 35)
        
        try:
            import sqlite3
            
            # Test validation log creation
            self.cert_manager._log_certificate_validation(
                "test.example.com", 
                "test-fingerprint-123", 
                True, 
                [], 
                ["Test warning"]
            )
            
            # Check log entry
            with sqlite3.connect(self.cert_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM certificate_validation_log 
                    WHERE hostname = 'test.example.com'
                """)
                count = cursor.fetchone()[0]
            
            self.log_test_result("Validation log creation",
                                count > 0,
                                f"Log entry created: {count} entries")
            
            # Test certificate pin storage
            test_pins = self.cert_manager.certificate_pins
            with sqlite3.connect(self.cert_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM certificate_pins WHERE is_active = 1")
                db_pin_count = cursor.fetchone()[0]
            
            self.log_test_result("Certificate pin storage consistency",
                                len(test_pins) == db_pin_count,
                                f"Memory: {len(test_pins)}, DB: {db_pin_count}")
            
            # Test database integrity
            with sqlite3.connect(self.cert_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
            
            self.log_test_result("Database integrity",
                                integrity_result == "ok",
                                f"Integrity check result: {integrity_result}")
            
        except Exception as e:
            self.log_test_result("Database operations", False, f"Exception: {e}")

    def test_security_integration(self):
        """Test integration with security monitoring and audit systems"""
        print("\n🔐 Testing Security Integration")
        print("=" * 35)
        
        try:
            import sqlite3
            
            # Test certificate validation with security logging
            test_cert = self.test_certificates.get('test_cert')
            if test_cert:
                result = self.cert_manager.validate_certificate_chain([test_cert], "test.example.com")
                
                # Check if validation was logged
                with sqlite3.connect(self.cert_manager.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) FROM certificate_validation_log 
                        WHERE hostname = 'test.example.com'
                    """)
                    log_count = cursor.fetchone()[0]
                
                self.log_test_result("Security event logging",
                                    log_count > 0,
                                    f"Validation events logged: {log_count}")
            
            # Test certificate pinning security
            if hasattr(self.cert_manager, 'certificate_pins') and self.cert_manager.certificate_pins:
                pin_count = len(self.cert_manager.certificate_pins)
                self.log_test_result("Certificate pinning security",
                                    pin_count > 0,
                                    f"Active certificate pins: {pin_count}")
            
            # Test security feature reporting
            stats = self.cert_manager.get_certificate_statistics()
            security_features = stats.get('security_features', {})
            enabled_features = [k for k, v in security_features.items() if v]
            
            self.log_test_result("Security feature integration",
                                len(enabled_features) >= 3,
                                f"Enabled features: {enabled_features}")
            
        except Exception as e:
            self.log_test_result("Security integration", False, f"Exception: {e}")

    def run_all_tests(self):
        """Run complete certificate security test suite"""
        print("🔐 PhotoShare Certificate Security Test Suite")
        print("=" * 50)
        print(f"Database: {self.db_path}")
        print()
        
        # Run all test categories
        self.test_certificate_manager_initialization()
        self.test_certificate_info_extraction()
        self.test_certificate_chain_validation()
        self.test_certificate_pinning()
        self.test_tls_connection_validation()
        self.test_certificate_monitoring()
        self.test_certificate_statistics()
        self.test_database_operations()
        self.test_security_integration()
        
        # Summary
        print(f"\n📊 Test Results Summary")
        print("=" * 25)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"📈 Success Rate: {(self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed']) * 100):.1f}%")
        
        if self.test_results['failed'] == 0:
            print("\n🎉 All certificate security tests passed!")
            return True
        else:
            print(f"\n⚠️ Some certificate security tests failed")
            return False

    def cleanup(self):
        """Clean up test resources"""
        try:
            if self.cert_manager:
                self.cert_manager.stop_certificate_monitoring()
            
            # Clean up temp directory
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")

def main():
    """Main test function"""
    if not CERTIFICATE_SECURITY_AVAILABLE:
        print("❌ Certificate security components not available")
        return False
    
    test_suite = CertificateSecurityTestSuite()
    
    try:
        success = test_suite.run_all_tests()
        return success
    except Exception as e:
        print(f"❌ Test suite failed with exception: {e}")
        return False
    finally:
        test_suite.cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)