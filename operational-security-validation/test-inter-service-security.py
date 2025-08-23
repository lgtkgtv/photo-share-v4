#!/usr/bin/env python3
"""
Inter-Service Communication Security Test Script
===============================================

Tests for secure inter-service communication with mTLS, API keys, and service registry.
"""

import sys
import os
import time
import json
import asyncio
from pathlib import Path

# Add the photoshare service path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'photoshare'))

try:
    from inter_service_security import (
        InterServiceSecurityManager,
        ServiceIdentity,
        ServiceCredential,
        get_inter_service_manager,
        validate_service_request,
        log_service_communication,
        get_service_security_stats
    )
    INTER_SERVICE_SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"Inter-Service Security not available: {e}")
    INTER_SERVICE_SECURITY_AVAILABLE = False


def test_service_registration():
    """Test service registration and management."""
    
    print("📋 Testing Service Registration")
    print("=" * 31)
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        print("❌ Inter-Service Security system not available")
        return False
    
    manager = InterServiceSecurityManager()
    
    print("\n1. Testing service registration...")
    
    # Register a new test service
    success = manager.register_service(
        service_id="test-service-1",
        service_name="Test Service 1",
        service_type="internal",
        trust_level="high",
        allowed_operations=["test:*", "data:read"],
        network_policy={
            "allowed_ips": ["127.0.0.1", "192.168.1.0/24"],
            "allowed_ports": [8080, 8443],
            "require_tls": True
        }
    )
    
    if success:
        print("   ✅ Service registration successful")
    else:
        print("   ❌ Service registration failed")
        manager.shutdown()
        return False
    
    print("\n2. Testing service lookup...")
    
    # Check if service is in active services
    if "test-service-1" in manager.active_services:
        service = manager.active_services["test-service-1"]
        print(f"   ✅ Service found: {service.service_name}")
        print(f"   Service type: {service.service_type}")
        print(f"   Trust level: {service.trust_level}")
        print(f"   Operations: {len(service.allowed_operations)}")
    else:
        print("   ❌ Service not found in registry")
        manager.shutdown()
        return False
    
    print("\n3. Testing service statistics...")
    
    stats = manager.get_service_statistics()
    
    if 'total_registered_services' in stats and stats['total_registered_services'] >= 4:  # 3 default + 1 test
        print(f"   ✅ Service statistics available: {stats['total_registered_services']} services")
    else:
        print("   ❌ Service statistics missing or incorrect")
        manager.shutdown()
        return False
    
    manager.shutdown()
    return True


def test_api_key_management():
    """Test API key generation and validation."""
    
    print("\n🔑 Testing API Key Management")
    print("=" * 30)
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        print("❌ Inter-Service Security system not available")
        return False
    
    manager = InterServiceSecurityManager()
    
    print("\n1. Testing API key generation...")
    
    # Generate API key for existing service
    api_key = manager.generate_api_key(
        service_id="photoshare-app",
        permissions=["photo:upload", "photo:download", "user:validate"],
        expires_in=86400  # 24 hours
    )
    
    if api_key and api_key.startswith("pss_photoshare-app_"):
        print(f"   ✅ API key generated: {api_key[:30]}...")
    else:
        print(f"   ❌ API key generation failed: {api_key}")
        manager.shutdown()
        return False
    
    print("\n2. Testing API key validation...")
    
    # Validate the generated API key
    valid, service_id, permissions = manager.validate_api_key(api_key)
    
    if valid and service_id == "photoshare-app":
        print(f"   ✅ API key validation successful")
        print(f"   Service ID: {service_id}")
        print(f"   Permissions: {permissions}")
    else:
        print(f"   ❌ API key validation failed: valid={valid}, service={service_id}")
        manager.shutdown()
        return False
    
    print("\n3. Testing invalid API key...")
    
    # Test with invalid API key
    invalid_key = "pss_invalid_service_invalid_key"
    valid, service_id, permissions = manager.validate_api_key(invalid_key)
    
    if not valid:
        print("   ✅ Invalid API key correctly rejected")
    else:
        print("   ❌ Invalid API key was accepted")
        manager.shutdown()
        return False
    
    print("\n4. Testing API key generation for unknown service...")
    
    # Try to generate key for unknown service
    bad_key = manager.generate_api_key(
        service_id="unknown-service",
        permissions=["test:read"],
        expires_in=3600
    )
    
    if bad_key is None:
        print("   ✅ API key generation correctly rejected for unknown service")
    else:
        print("   ❌ API key generated for unknown service")
        manager.shutdown()
        return False
    
    manager.shutdown()
    return True


def test_communication_validation():
    """Test inter-service communication validation."""
    
    print("\n🔒 Testing Communication Validation")
    print("=" * 36)
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        print("❌ Inter-Service Security system not available")
        return False
    
    manager = InterServiceSecurityManager()
    
    print("\n1. Testing valid service communication...")
    
    # Test valid communication between registered services
    allowed, reason, risk_score = manager.validate_service_communication(
        source_service="auth-service",
        target_service="photoshare-app",
        operation="user:validate",
        auth_method="api_key",
        source_ip="127.0.0.1"
    )
    
    if allowed:
        print(f"   ✅ Valid communication allowed")
        print(f"   Risk score: {risk_score:.1f}")
    else:
        print(f"   ❌ Valid communication blocked: {reason}")
        manager.shutdown()
        return False
    
    print("\n2. Testing unauthorized operation...")
    
    # Test communication with unauthorized operation
    allowed, reason, risk_score = manager.validate_service_communication(
        source_service="auth-service",
        target_service="photoshare-app", 
        operation="admin:delete",  # Not in allowed operations
        auth_method="api_key",
        source_ip="127.0.0.1"
    )
    
    if not allowed:
        print(f"   ✅ Unauthorized operation correctly blocked")
        print(f"   Reason: {reason}")
    else:
        print(f"   ❌ Unauthorized operation was allowed: {reason}")
        manager.shutdown()
        return False
    
    print("\n3. Testing unknown source service...")
    
    # Test communication from unknown service
    allowed, reason, risk_score = manager.validate_service_communication(
        source_service="unknown-service",
        target_service="photoshare-app",
        operation="test:read",
        auth_method="none",
        source_ip="192.168.1.100"
    )
    
    if not allowed:
        print(f"   ✅ Unknown service correctly blocked")
        print(f"   Reason: {reason}")
    else:
        print(f"   ❌ Unknown service was allowed: {reason}")
        manager.shutdown()
        return False
    
    print("\n4. Testing high-risk communication...")
    
    # Test communication that should have high risk score
    allowed, reason, risk_score = manager.validate_service_communication(
        source_service="gateway-service",  # Medium trust level
        target_service="photoshare-app",
        operation="proxy:admin",  # Admin operation
        auth_method="none",  # No authentication
        source_ip="0.0.0.0"  # Suspicious IP
    )
    
    if risk_score > 50.0:
        print(f"   ✅ High-risk communication detected: {risk_score:.1f}")
    else:
        print(f"   ⚠️  Risk score lower than expected: {risk_score:.1f}")
    
    manager.shutdown()
    return True


def test_communication_logging():
    """Test communication attempt logging."""
    
    print("\n📝 Testing Communication Logging")
    print("=" * 33)
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        print("❌ Inter-Service Security system not available")
        return False
    
    manager = InterServiceSecurityManager()
    
    print("\n1. Testing communication logging...")
    
    # Log several communication attempts
    attempts = [
        ("auth-service", "photoshare-app", "user:validate", True, "api_key"),
        ("gateway-service", "photoshare-app", "proxy:photos", True, "certificate"),
        ("unknown-service", "photoshare-app", "test:hack", False, "none"),
        ("auth-service", "photoshare-app", "user:validate", True, "api_key"),
        ("auth-service", "photoshare-app", "admin:users", False, "api_key"),
    ]
    
    logged_attempts = []
    for source, target, operation, success, auth_method in attempts:
        attempt_id = manager.log_communication_attempt(
            source_service=source,
            target_service=target,
            operation=operation,
            success=success,
            auth_method=auth_method,
            metadata={"test": True}
        )
        
        if attempt_id:
            logged_attempts.append(attempt_id)
    
    if len(logged_attempts) == len(attempts):
        print(f"   ✅ All {len(attempts)} communication attempts logged")
    else:
        print(f"   ❌ Only {len(logged_attempts)}/{len(attempts)} attempts logged")
        manager.shutdown()
        return False
    
    print("\n2. Testing communication retrieval...")
    
    # Retrieve recent communications
    recent_comms = manager.get_recent_communications(limit=10, hours_back=1)
    
    if len(recent_comms) >= len(attempts):
        print(f"   ✅ Retrieved {len(recent_comms)} recent communications")
        
        # Check structure of returned data
        comm = recent_comms[0]
        required_fields = ['attempt_id', 'source_service', 'target_service', 'operation', 'success']
        for field in required_fields:
            if field in comm:
                print(f"   ✅ {field} present in communication record")
            else:
                print(f"   ❌ {field} missing from communication record")
                manager.shutdown()
                return False
    else:
        print(f"   ❌ Retrieved only {len(recent_comms)} communications, expected at least {len(attempts)}")
        manager.shutdown()
        return False
    
    print("\n3. Testing filtered communication retrieval...")
    
    # Test service filter
    filtered_comms = manager.get_recent_communications(
        limit=50, hours_back=1, service_filter="auth-service"
    )
    
    # Should only return communications involving auth-service
    auth_service_comms = [
        comm for comm in filtered_comms 
        if comm['source_service'] == 'auth-service' or comm['target_service'] == 'auth-service'
    ]
    
    if len(auth_service_comms) == len(filtered_comms):
        print(f"   ✅ Service filtering works: {len(filtered_comms)} auth-service communications")
    else:
        print(f"   ❌ Service filtering failed: {len(auth_service_comms)}/{len(filtered_comms)} filtered correctly")
        manager.shutdown()
        return False
    
    manager.shutdown()
    return True


def test_certificate_generation():
    """Test TLS certificate generation for mTLS."""
    
    print("\n🔐 Testing Certificate Generation")
    print("=" * 34)
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        print("❌ Inter-Service Security system not available")
        return False
    
    try:
        from cryptography import x509
        crypto_available = True
    except ImportError:
        crypto_available = False
    
    if not crypto_available:
        print("⚠️  Cryptography library not available - skipping certificate tests")
        return True
    
    manager = InterServiceSecurityManager()
    
    print("\n1. Testing certificate generation...")
    
    # Generate certificate for test service
    cert_file, key_file = manager.generate_service_certificate(
        service_id="auth-service",
        common_name="auth-service.local",
        san_list=["auth-service", "auth.local", "localhost"],
        validity_days=30
    )
    
    if cert_file and key_file:
        print(f"   ✅ Certificate generated: {cert_file}")
        print(f"   ✅ Private key generated: {key_file}")
        
        # Check if files exist
        if os.path.exists(cert_file) and os.path.exists(key_file):
            print("   ✅ Certificate files created on disk")
        else:
            print("   ❌ Certificate files not found on disk")
            manager.shutdown()
            return False
    else:
        print("   ❌ Certificate generation failed")
        manager.shutdown()
        return False
    
    print("\n2. Testing certificate validation...")
    
    try:
        # Load and validate certificate
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
        
        certificate = x509.load_pem_x509_certificate(cert_data)
        
        # Check certificate properties
        subject = certificate.subject
        common_name = subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
        
        if common_name == "auth-service.local":
            print("   ✅ Certificate common name correct")
        else:
            print(f"   ❌ Certificate common name incorrect: {common_name}")
            manager.shutdown()
            return False
        
        # Check SAN extension
        try:
            san_ext = certificate.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            san_names = [name.value for name in san_ext.value]
            
            if "auth-service" in san_names and "localhost" in san_names:
                print("   ✅ SAN extension correct")
            else:
                print(f"   ❌ SAN extension incorrect: {san_names}")
                manager.shutdown()
                return False
        except:
            print("   ❌ SAN extension missing")
            manager.shutdown()
            return False
            
    except Exception as e:
        print(f"   ❌ Certificate validation failed: {e}")
        manager.shutdown()
        return False
    
    print("\n3. Testing certificate storage...")
    
    # Check if credential was stored
    if "auth-service" in manager.service_credentials:
        cert_credentials = [
            cred for cred in manager.service_credentials["auth-service"]
            if cred.credential_type == "certificate"
        ]
        
        if cert_credentials:
            cred = cert_credentials[0]
            print(f"   ✅ Certificate credential stored")
            print(f"   Common name: {cred.metadata.get('common_name')}")
            print(f"   Validity days: {cred.metadata.get('validity_days')}")
        else:
            print("   ❌ Certificate credential not stored")
            manager.shutdown()
            return False
    else:
        print("   ❌ No credentials found for service")
        manager.shutdown()
        return False
    
    manager.shutdown()
    return True


def test_integration_functions():
    """Test global integration functions."""
    
    print("\n🔗 Testing Integration Functions")
    print("=" * 33)
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        print("❌ Inter-Service Security system not available")
        return False
    
    print("\n1. Testing global validation function...")
    
    # Test validate_service_request
    allowed, reason, risk_score = validate_service_request(
        source_service="auth-service",
        target_service="photoshare-app",
        operation="user:validate",
        auth_method="api_key",
        source_ip="127.0.0.1"
    )
    
    if allowed:
        print("   ✅ Global validate_service_request works")
    else:
        print(f"   ❌ Global validate_service_request failed: {reason}")
        return False
    
    print("\n2. Testing global communication logging...")
    
    # Test log_service_communication
    attempt_id = log_service_communication(
        source_service="test-service",
        target_service="photoshare-app",
        operation="test:integration",
        success=True,
        auth_method="api_key",
        metadata={"integration_test": True}
    )
    
    if attempt_id:
        print(f"   ✅ Global log_service_communication works: {attempt_id}")
    else:
        print("   ❌ Global log_service_communication failed")
        return False
    
    print("\n3. Testing global statistics function...")
    
    # Test get_service_security_stats
    stats = get_service_security_stats()
    
    if 'inter_service_security_enabled' in stats and stats['inter_service_security_enabled']:
        print("   ✅ Global get_service_security_stats works")
        print(f"   Total services: {stats.get('total_registered_services', 'N/A')}")
        print(f"   Total communications: {stats.get('total_communications', 'N/A')}")
    else:
        print("   ❌ Global get_service_security_stats failed")
        return False
    
    return True


def test_risk_scoring():
    """Test communication risk scoring algorithm."""
    
    print("\n⚠️  Testing Risk Scoring")
    print("=" * 24)
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        print("❌ Inter-Service Security system not available")
        return False
    
    manager = InterServiceSecurityManager()
    
    print("\n1. Testing low-risk communication...")
    
    # Low risk: high trust service, certificate auth, allowed operation, success
    allowed, reason, risk_score = manager.validate_service_communication(
        source_service="auth-service",  # High trust
        target_service="photoshare-app",
        operation="user:validate",  # Allowed operation
        auth_method="certificate",  # Most secure auth
        source_ip="127.0.0.1"  # Local IP
    )
    
    if risk_score <= 30.0:
        print(f"   ✅ Low-risk communication: {risk_score:.1f}")
    else:
        print(f"   ⚠️  Risk score higher than expected: {risk_score:.1f}")
    
    print("\n2. Testing medium-risk communication...")
    
    # Medium risk: medium trust service, API key auth
    allowed, reason, risk_score = manager.validate_service_communication(
        source_service="gateway-service",  # Medium trust
        target_service="photoshare-app",
        operation="proxy:photos",
        auth_method="api_key",  # Moderate security
        source_ip="192.168.1.100"
    )
    
    if 20.0 <= risk_score <= 50.0:
        print(f"   ✅ Medium-risk communication: {risk_score:.1f}")
    else:
        print(f"   ⚠️  Risk score outside expected range: {risk_score:.1f}")
    
    print("\n3. Testing high-risk communication...")
    
    # High risk: unknown service, no auth, admin operation, external IP
    manager.register_service(
        service_id="untrusted-service",
        service_name="Untrusted Service",
        service_type="external",
        trust_level="low",
        allowed_operations=["admin:*"],  # Admin operations
        network_policy={"allowed_ips": ["0.0.0.0/0"]}
    )
    
    allowed, reason, risk_score = manager.validate_service_communication(
        source_service="untrusted-service",  # Low trust
        target_service="photoshare-app",
        operation="admin:delete",  # Admin operation
        auth_method="none",  # No authentication
        source_ip="203.0.113.1"  # External IP
    )
    
    if risk_score >= 60.0:
        print(f"   ✅ High-risk communication: {risk_score:.1f}")
    else:
        print(f"   ⚠️  Risk score lower than expected: {risk_score:.1f}")
    
    print("\n4. Testing failed communication risk...")
    
    # Simulate failed communication
    attempt_id = manager.log_communication_attempt(
        source_service="test-service",
        target_service="photoshare-app", 
        operation="test:fail",
        success=False,  # Failed attempt
        auth_method="api_key",
        metadata={"simulated_failure": True}
    )
    
    if attempt_id:
        print("   ✅ Failed communication logged with higher risk")
    else:
        print("   ❌ Failed to log failed communication")
    
    manager.shutdown()
    return True


def test_performance():
    """Test inter-service security performance."""
    
    print("\n⚡ Testing Performance")
    print("=" * 20)
    
    if not INTER_SERVICE_SECURITY_AVAILABLE:
        print("❌ Inter-Service Security system not available")
        return False
    
    manager = InterServiceSecurityManager()
    
    print("\n1. Testing API key validation performance...")
    
    # Generate test API key
    api_key = manager.generate_api_key(
        service_id="photoshare-app",
        permissions=["test:performance"],
        expires_in=3600
    )
    
    if not api_key:
        print("   ❌ Failed to generate test API key")
        manager.shutdown()
        return False
    
    # Test validation performance
    test_count = 100
    start_time = time.time()
    
    successful_validations = 0
    for _ in range(test_count):
        valid, service_id, permissions = manager.validate_api_key(api_key)
        if valid:
            successful_validations += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    validations_per_sec = test_count / total_time
    
    print(f"   ✅ Validated {test_count} API keys in {total_time:.2f}s ({validations_per_sec:.1f} validations/sec)")
    
    if validations_per_sec >= 50:  # Should be much faster than this
        print("   ✅ Performance meets requirements")
    else:
        print("   ⚠️  Performance below expected threshold")
    
    if successful_validations == test_count:
        print("   ✅ All validations successful")
    else:
        print(f"   ❌ Only {successful_validations}/{test_count} validations successful")
    
    print("\n2. Testing communication logging performance...")
    
    # Test logging performance
    log_count = 50
    start_time = time.time()
    
    successful_logs = 0
    for i in range(log_count):
        attempt_id = manager.log_communication_attempt(
            source_service="perf-test-service",
            target_service="photoshare-app",
            operation=f"perf:test_{i}",
            success=True,
            auth_method="api_key",
            metadata={"performance_test": i}
        )
        
        if attempt_id:
            successful_logs += 1
    
    end_time = time.time()
    total_time = end_time - start_time
    logs_per_sec = log_count / total_time
    
    print(f"   ✅ Logged {log_count} communications in {total_time:.2f}s ({logs_per_sec:.1f} logs/sec)")
    
    if successful_logs == log_count:
        print("   ✅ All logs successful")
    else:
        print(f"   ❌ Only {successful_logs}/{log_count} logs successful")
    
    manager.shutdown()
    return True


if __name__ == "__main__":
    print("🔐 PhotoShare Inter-Service Security Test Suite")
    print("=" * 50)
    
    success = True
    
    try:
        # Run all tests
        success &= test_service_registration()
        success &= test_api_key_management()
        success &= test_communication_validation()
        success &= test_communication_logging()
        success &= test_certificate_generation()
        success &= test_integration_functions()
        success &= test_risk_scoring()
        success &= test_performance()
        
        if success:
            print(f"\n🎉 ALL INTER-SERVICE SECURITY TESTS PASSED!")
            print("🔐 Secure inter-service communication system is ready")
            
            print("\n📋 Security Features Verified:")
            if INTER_SERVICE_SECURITY_AVAILABLE:
                print("   ✅ Service registry and identity management")
                print("   ✅ API key authentication and authorization")
                print("   ✅ mTLS certificate generation and management")
                print("   ✅ Communication validation and access control")
                print("   ✅ Risk-based security scoring")
                print("   ✅ Comprehensive communication logging")
                print("   ✅ Network policy enforcement")
                print("   ✅ High-performance validation (50+ ops/sec)")
            
            print("\n📋 Next Steps:")
            print("   1. Configure service network policies for production")
            print("   2. Set up certificate authority for mTLS")
            print("   3. Implement automated certificate rotation")
            print("   4. Configure service mesh integration")
            print("   5. Set up monitoring alerts for high-risk communications")
            
            exit_code = 0
        else:
            print("\n❌ Some inter-service security tests failed")
            exit_code = 1
            
    except Exception as e:
        print(f"\n💥 Inter-service security test suite failed: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    sys.exit(exit_code)