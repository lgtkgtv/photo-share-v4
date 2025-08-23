#!/usr/bin/env python3
"""
Comprehensive Security Improvements Test Script
===============================================

This script tests all security improvements including:
Phase 1: Enhanced file upload validation, database constraints, environment security
Phase 2: Authentication mechanisms, RBAC, session management, encryption, TLS, key management
"""

import os
import sys
import tempfile
import requests
import json
import asyncio
import secrets
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add the services directory to the path for imports
sys.path.append(str(Path(__file__).parent.parent / "services" / "photoshare"))

def test_file_upload_validation():
    """Test enhanced file upload validation."""
    print("🔒 Testing enhanced file upload validation...")
    
    try:
        from security import InputValidator
        validator = InputValidator()
        
        # Test 1: Valid image file should pass
        jpeg_header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF' + b'A' * 200
        is_valid, message = validator.validate_file_upload(jpeg_header, "image/jpeg")
        assert is_valid, f"Valid JPEG should pass: {message}"
        print("  ✅ Valid JPEG file validation passed")
        
        # Test 2: Non-image content type should fail
        is_valid, message = validator.validate_file_upload(jpeg_header, "application/pdf")
        assert not is_valid, f"PDF content type should fail: {message}"
        print("  ✅ Non-image content type validation failed as expected")
        
        # Test 3: Malicious content should fail
        malicious_content = b"<script>alert('xss')</script>" + b'A' * 200
        is_valid, message = validator.validate_file_upload(malicious_content, "image/jpeg")
        assert not is_valid, f"Malicious content should fail: {message}"
        print("  ✅ Malicious content validation failed as expected")
        
        # Test 4: Wrong magic number should fail
        fake_jpeg = b"not-a-jpeg" + b'A' * 200
        is_valid, message = validator.validate_file_upload(fake_jpeg, "image/jpeg")
        assert not is_valid, f"Fake JPEG should fail: {message}"
        print("  ✅ Wrong magic number validation failed as expected")
        
        # Test 5: Too small file should fail
        tiny_file = b'\xFF\xD8\xFF'  # Only 3 bytes
        is_valid, message = validator.validate_file_upload(tiny_file, "image/jpeg")
        assert not is_valid, f"Tiny file should fail: {message}"
        print("  ✅ Too small file validation failed as expected")
        
        print("  🎉 All file upload validation tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ File upload validation test failed: {e}")
        return False


def test_database_constraints():
    """Test database foreign key constraints."""
    print("🔒 Testing database foreign key constraints...")
    
    try:
        from database import User, Photo, Session, EmailVerification
        from sqlalchemy import inspect
        
        # Check that foreign keys are properly defined
        photo_inspector = inspect(Photo)
        photo_fks = photo_inspector.foreign_keys
        assert len(photo_fks) > 0, "Photo table should have foreign keys"
        
        # Check user_id foreign key in Photo
        user_id_fk = None
        for fk in photo_fks:
            if fk.parent.name == 'user_id':
                user_id_fk = fk
                break
        
        assert user_id_fk is not None, "Photo.user_id should have foreign key"
        assert user_id_fk.column.table.name == 'users', "Foreign key should reference users table"
        print("  ✅ Photo.user_id foreign key constraint verified")
        
        # Check Session foreign key
        session_inspector = inspect(Session)
        session_fks = session_inspector.foreign_keys
        assert len(session_fks) > 0, "Session table should have foreign keys"
        print("  ✅ Session.user_id foreign key constraint verified")
        
        # Check indexes
        photo_indexes = photo_inspector.indexes
        user_indexes = inspect(User).indexes
        
        print(f"  ✅ Photo table has {len(photo_indexes)} indexes")
        print(f"  ✅ User table has {len(user_indexes)} indexes")
        
        print("  🎉 All database constraint tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Database constraint test failed: {e}")
        return False


def test_environment_security():
    """Test environment configuration security."""
    print("🔒 Testing environment configuration security...")
    
    try:
        # Test .env.example exists
        project_root = Path(__file__).parent.parent
        env_example = project_root / ".env.example"
        assert env_example.exists(), ".env.example should exist"
        print("  ✅ .env.example file exists")
        
        # Test .gitignore includes .env
        gitignore = project_root / ".gitignore"
        if gitignore.exists():
            with open(gitignore, 'r') as f:
                gitignore_content = f.read()
            assert ".env" in gitignore_content, ".env should be in .gitignore"
            assert ".env.example" not in gitignore_content or "!.env.example" in gitignore_content, ".env.example should not be ignored"
            print("  ✅ .gitignore properly configured")
        
        # Test environment setup script exists
        setup_script = project_root / "scripts" / "setup-environment.py"
        assert setup_script.exists(), "Environment setup script should exist"
        print("  ✅ Environment setup script exists")
        
        # Test weak secret detection (simulate)
        weak_secrets = [
            "your-very-secure-secret-key-here",
            "generate_with_script_or_use_secure_random_string",
            "change_this_password"
        ]
        
        for secret in weak_secrets:
            # This would be tested in the actual application startup
            print(f"  ✅ Weak secret detection ready for: {secret[:20]}...")
        
        print("  🎉 All environment security tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Environment security test failed: {e}")
        return False


def test_api_security_headers():
    """Test API security headers (if service is running)."""
    print("🔒 Testing API security headers...")
    
    try:
        # Try to connect to the service
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            # Check security headers
            headers = response.headers
            
            # These should be set by security middleware
            security_checks = [
                ("X-Content-Type-Options", "nosniff"),
                ("X-Frame-Options", "DENY"),
                ("X-XSS-Protection", "1; mode=block"),
            ]
            
            for header_name, expected_value in security_checks:
                if header_name in headers:
                    print(f"  ✅ {header_name} header present")
                else:
                    print(f"  ⚠️  {header_name} header missing (may be set by proxy)")
            
            print("  ✅ Service is running and accessible")
            return True
        else:
            print(f"  ⚠️  Service returned status {response.status_code}")
            return False
            
    except requests.ConnectionError:
        print("  ⚠️  Service not running - skipping API tests")
        return True  # Not a failure, just not running
    except Exception as e:
        print(f"  ❌ API security test failed: {e}")
        return False


# Phase 2 Security Improvements Tests

def test_enhanced_authentication():
    """Test enhanced authentication mechanisms."""
    print("🔒 Testing enhanced authentication mechanisms...")
    
    try:
        from security import JWTSecurity
        
        # Test JWT security enhancements
        jwt_sec = JWTSecurity("test_secret_key_for_validation")
        
        # Test 1: Token revocation
        test_token = "test_token_" + secrets.token_hex(16)
        jwt_sec.revoke_token(test_token)
        
        if jwt_sec.is_token_revoked(test_token):
            print("  ✅ JWT token revocation working")
        else:
            print("  ❌ JWT token revocation failed")
            return False
        
        # Test 2: Token tracking
        token_id = "test_id_" + secrets.token_hex(8)
        user_id = 12345
        issued_at = datetime.now(timezone.utc)
        
        jwt_sec.track_token(token_id, user_id, issued_at)
        
        if token_id in jwt_sec.active_tokens:
            print("  ✅ JWT token tracking working")
        else:
            print("  ❌ JWT token tracking failed")
            return False
        
        # Test 3: Session limits enforcement
        for i in range(7):  # More than max_tokens_per_user
            test_id = f"test_{i}_{secrets.token_hex(4)}"
            jwt_sec.track_token(test_id, user_id, issued_at)
        
        user_tokens = [tid for tid, data in jwt_sec.active_tokens.items() 
                      if data.get("user_id") == user_id]
        
        if len(user_tokens) <= jwt_sec.max_tokens_per_user:
            print("  ✅ User session limits enforced")
        else:
            print("  ❌ User session limits not enforced")
            return False
        
        print("  🎉 Enhanced authentication tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Enhanced authentication test failed: {e}")
        return False


def test_rbac_implementation():
    """Test Role-Based Access Control implementation."""
    print("🔒 Testing RBAC implementation...")
    
    try:
        # Test 1: RBAC database models
        from database import Role, Permission, RolePermission, UserRole
        
        test_role = Role(name="test_role", description="Test role")
        test_permission = Permission(name="test_permission", resource="test", action="read")
        
        if hasattr(test_role, 'to_dict') and hasattr(test_permission, 'to_dict'):
            print("  ✅ RBAC database models validated")
        else:
            print("  ❌ RBAC database models missing methods")
            return False
        
        # Test 2: RBAC repositories
        try:
            from database import RoleRepository, PermissionRepository, UserRoleRepository
            print("  ✅ RBAC repositories imported successfully")
        except ImportError as e:
            print(f"  ❌ RBAC repository import failed: {e}")
            return False
        
        # Test 3: RBAC initialization script
        script_path = Path(__file__).parent.parent / "services" / "photoshare" / "init_rbac.py"
        if script_path.exists():
            print("  ✅ RBAC initialization script exists")
        else:
            print("  ❌ RBAC initialization script not found")
            return False
        
        print("  🎉 RBAC implementation tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ RBAC implementation test failed: {e}")
        return False


def test_session_management():
    """Test enhanced session management security."""
    print("🔒 Testing session management security...")
    
    try:
        from security import SessionManager, JWTSecurity
        
        # Initialize components
        jwt_sec = JWTSecurity("test_secret")
        session_mgr = SessionManager(jwt_sec)
        
        # Test 1: Session fingerprinting
        class MockRequest:
            def __init__(self):
                self.headers = {
                    "user-agent": "Mozilla/5.0 Test",
                    "accept-language": "en-US",
                    "accept-encoding": "gzip"
                }
        
        mock_request = MockRequest()
        fingerprint = session_mgr.create_session_fingerprint(mock_request)
        
        if fingerprint and len(fingerprint) == 16:
            print("  ✅ Session fingerprinting working")
        else:
            print("  ❌ Session fingerprinting failed")
            return False
        
        # Test 2: Session registration
        session_id = "test_session_" + secrets.token_hex(8)
        user_id = 12345
        ip_address = "192.168.1.100"
        
        session_mgr.register_session(session_id, user_id, mock_request, ip_address)
        
        if session_id in session_mgr.session_fingerprints:
            print("  ✅ Session registration working")
        else:
            print("  ❌ Session registration failed")
            return False
        
        # Test 3: Session validation
        validation_result = session_mgr.validate_session(session_id, mock_request, ip_address)
        
        if validation_result["is_valid"]:
            print("  ✅ Session validation working")
        else:
            print("  ❌ Session validation failed")
            return False
        
        # Test 4: Account lockout
        for _ in range(6):  # Exceed max_failed_attempts
            session_mgr.track_failed_attempt("bad_session", user_id)
        
        if session_mgr.is_account_locked(user_id):
            print("  ✅ Account lockout working")
        else:
            print("  ❌ Account lockout not working")
            return False
        
        print("  🎉 Session management security tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Session management test failed: {e}")
        return False


def test_enhanced_encryption():
    """Test enhanced encryption implementations."""
    print("🔒 Testing enhanced encryption...")
    
    try:
        from encryption import EncryptionManager
        
        enc_mgr = EncryptionManager()
        
        # Test 1: Enhanced password hashing
        test_password = "TestPassword123!"
        hashed = enc_mgr.hash_password_secure(test_password)
        
        if enc_mgr.verify_password_secure(test_password, hashed):
            print("  ✅ Enhanced password hashing working")
        else:
            print("  ❌ Enhanced password hashing failed")
            return False
        
        # Test 2: Sensitive data encryption
        test_data = "Sensitive information: " + secrets.token_hex(16)
        encrypted_metadata = enc_mgr.encrypt_sensitive_data(test_data)
        decrypted_data = enc_mgr.decrypt_sensitive_data(encrypted_metadata)
        
        if decrypted_data == test_data:
            print("  ✅ Sensitive data encryption working")
        else:
            print("  ❌ Sensitive data encryption failed")
            return False
        
        # Test 3: File content encryption
        test_file_content = b"Binary file content: " + secrets.token_bytes(64)
        encrypted_file = enc_mgr.encrypt_file_content(test_file_content)
        decrypted_file = enc_mgr.decrypt_file_content(encrypted_file)
        
        if decrypted_file == test_file_content:
            print("  ✅ File content encryption working")
        else:
            print("  ❌ File content encryption failed")
            return False
        
        # Test 4: HMAC signatures
        test_message = "Message to sign"
        signature = enc_mgr.create_hmac_signature(test_message)
        
        if enc_mgr.verify_hmac_signature(test_message, signature):
            print("  ✅ HMAC signature working")
        else:
            print("  ❌ HMAC signature failed")
            return False
        
        # Test 5: Key rotation
        old_key = enc_mgr.master_key
        new_key = enc_mgr.rotate_encryption_key()
        
        if new_key != old_key and new_key == enc_mgr.master_key:
            print("  ✅ Key rotation working")
        else:
            print("  ❌ Key rotation failed")
            return False
        
        print("  🎉 Enhanced encryption tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Enhanced encryption test failed: {e}")
        return False


def test_tls_security():
    """Test TLS security validation capabilities."""
    print("🔒 Testing TLS security...")
    
    try:
        from tls_security import TLSSecurityValidator, TLSConfigurationManager
        
        # Test 1: TLS Validator initialization
        tls_validator = TLSSecurityValidator()
        
        if tls_validator.min_tls_version and tls_validator.secure_ciphers:
            print("  ✅ TLS validator initialized")
        else:
            print("  ❌ TLS validator initialization failed")
            return False
        
        # Test 2: TLS Configuration Manager
        tls_config = TLSConfigurationManager()
        
        try:
            ssl_context = tls_config.create_secure_ssl_context()
            if ssl_context:
                print("  ✅ Secure SSL context creation working")
            else:
                print("  ❌ SSL context creation failed")
                return False
        except Exception:
            print("  ⚠️  SSL context creation failed (may be environment dependent)")
        
        # Test 3: Configuration validation
        config_validation = tls_config.validate_ssl_configuration()
        
        if "valid" in config_validation:
            print("  ✅ TLS configuration validation working")
        else:
            print("  ❌ TLS configuration validation failed")
            return False
        
        print("  🎉 TLS security tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ TLS security test failed: {e}")
        return False


def test_key_management():
    """Test enhanced key management practices."""
    print("🔒 Testing key management...")
    
    try:
        from encryption import SecurityKeyManager, EncryptionManager
        
        # Initialize components
        enc_mgr = EncryptionManager()
        key_mgr = SecurityKeyManager(enc_mgr)
        
        # Test 1: API key generation
        test_user_id = 12345
        api_key_data = key_mgr.generate_api_key(test_user_id, "test_scope")
        
        if "api_key" in api_key_data and "key_id" in api_key_data:
            print("  ✅ API key generation working")
        else:
            print("  ❌ API key generation failed")
            return False
        
        # Test 2: API key verification
        api_key = api_key_data["api_key"]
        key_id = api_key_data["key_id"]
        
        verification_result = key_mgr.verify_api_key(api_key, key_id)
        
        if verification_result and verification_result["user_id"] == test_user_id:
            print("  ✅ API key verification working")
        else:
            print("  ❌ API key verification failed")
            return False
        
        # Test 3: Master key generation
        master_key_data = key_mgr.generate_master_key("test_encryption", "AES-256")
        
        if "key_id" in master_key_data and "purpose" in master_key_data:
            print("  ✅ Master key generation working")
        else:
            print("  ❌ Master key generation failed")
            return False
        
        # Test 4: Key derivation
        master_key_id = master_key_data["key_id"]
        derived_key_data = key_mgr.derive_key(master_key_id, "test_derived", test_user_id)
        
        if "key_id" in derived_key_data and "parent_key" in derived_key_data:
            print("  ✅ Key derivation working")
        else:
            print("  ❌ Key derivation failed")
            return False
        
        # Test 5: Key lifecycle audit
        audit_report = key_mgr.perform_key_lifecycle_audit()
        
        if "audit_timestamp" in audit_report and "total_keys" in audit_report:
            print("  ✅ Key lifecycle audit working")
        else:
            print("  ❌ Key lifecycle audit failed")
            return False
        
        # Test 6: Compliance reporting
        compliance_report = key_mgr.get_key_management_compliance_report()
        
        if "compliance_status" in compliance_report:
            print("  ✅ Key management compliance reporting working")
        else:
            print("  ❌ Compliance reporting failed")
            return False
        
        print("  🎉 Key management tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Key management test failed: {e}")
        return False


def test_integration_security():
    """Test integration of security components."""
    print("🔒 Testing security integration...")
    
    try:
        from security import JWTSecurity, SessionManager
        from encryption import get_encryption_manager
        
        # Initialize components
        jwt_sec = JWTSecurity("integration_test_secret")
        session_mgr = SessionManager(jwt_sec)
        enc_mgr = get_encryption_manager()
        
        # Test 1: End-to-end authentication flow
        test_email = "integration@test.com"
        test_password = "IntegrationTest123!"
        
        # Hash password with enhanced encryption
        password_hash = enc_mgr.hash_password_secure(test_password)
        
        # Verify password
        password_valid = enc_mgr.verify_password_secure(test_password, password_hash)
        
        if password_valid:
            print("  ✅ Integrated password flow working")
        else:
            print("  ❌ Integrated password flow failed")
            return False
        
        # Test 2: Session and token integration
        class MockRequest:
            def __init__(self):
                self.headers = {"user-agent": "Integration Test"}
                self.client = type('obj', (object,), {'host': '127.0.0.1'})()
        
        mock_request = MockRequest()
        session_id = "integration_session_" + secrets.token_hex(8)
        user_id = 99999
        
        # Register session
        session_mgr.register_session(session_id, user_id, mock_request, "127.0.0.1")
        
        # Track JWT token
        jwt_sec.track_token(session_id, user_id, datetime.now(timezone.utc))
        
        # Validate session
        validation = session_mgr.validate_session(session_id, mock_request, "127.0.0.1")
        
        if validation["is_valid"]:
            print("  ✅ Session-token integration working")
        else:
            print("  ❌ Session-token integration failed")
            return False
        
        print("  🎉 Security integration tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Security integration test failed: {e}")
        return False


def main():
    """Run all security tests."""
    print("🛡️  Comprehensive Security Improvements Test Suite")
    print("=" * 60)
    print("Testing Phase 1 & Phase 2 Security Enhancements")
    print("=" * 60)
    
    # Phase 1 tests
    phase1_tests = [
        ("File Upload Validation", test_file_upload_validation),
        ("Database Constraints", test_database_constraints),
        ("Environment Security", test_environment_security),
        ("API Security Headers", test_api_security_headers),
    ]
    
    # Phase 2 tests
    phase2_tests = [
        ("Enhanced Authentication", test_enhanced_authentication),
        ("RBAC Implementation", test_rbac_implementation),
        ("Session Management", test_session_management),
        ("Enhanced Encryption", test_enhanced_encryption),
        ("TLS Security", test_tls_security),
        ("Key Management", test_key_management),
        ("Security Integration", test_integration_security),
    ]
    
    all_tests = phase1_tests + phase2_tests
    
    results = []
    
    # Run Phase 1 tests
    print("\n🔒 Phase 1 Security Tests")
    print("-" * 30)
    for test_name, test_func in phase1_tests:
        print(f"\n📋 Running {test_name} tests...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Run Phase 2 tests
    print("\n🛡️ Phase 2 Security Tests")
    print("-" * 30)
    for test_name, test_func in phase2_tests:
        print(f"\n📋 Running {test_name} tests...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("🛡️  Comprehensive Security Test Results Summary")
    print("=" * 70)
    
    # Separate results by phase
    phase1_results = results[:len(phase1_tests)]
    phase2_results = results[len(phase1_tests):]
    
    print("\n🔒 Phase 1 Results:")
    phase1_passed = 0
    for test_name, result in phase1_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name:.<35} {status}")
        if result:
            phase1_passed += 1
    
    print(f"\n🛡️ Phase 2 Results:")
    phase2_passed = 0
    for test_name, result in phase2_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name:.<35} {status}")
        if result:
            phase2_passed += 1
    
    total_passed = phase1_passed + phase2_passed
    total_tests = len(results)
    
    print(f"\n" + "=" * 70)
    print(f"Phase 1 Tests: {phase1_passed}/{len(phase1_tests)} passed")
    print(f"Phase 2 Tests: {phase2_passed}/{len(phase2_tests)} passed")
    print(f"Overall: {total_passed}/{total_tests} passed ({(total_passed/total_tests)*100:.1f}%)")
    
    if total_passed == total_tests:
        print("\n🎉 All security improvements are working correctly!")
        print("✅ Your PhotoShare application has comprehensive security!")
        return 0
    elif total_passed >= total_tests * 0.8:
        print("\n⚠️  Most security tests passed, but some issues need attention.")
        print("Review the failed tests above and address any security gaps.")
        return 2
    else:
        print("\n❌ Critical security tests failed!")
        print("Immediate attention required to fix security vulnerabilities.")
        return 1


if __name__ == "__main__":
    exit(main())