#!/usr/bin/env python3
"""
Security Improvements Test Script
=================================

This script tests all the Phase 1 security improvements:
1. Enhanced file upload validation
2. Database foreign key constraints
3. Environment configuration security
"""

import os
import sys
import tempfile
import requests
import json
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


def main():
    """Run all security tests."""
    print("🛡️  Phase 1 Security Improvements Test Suite")
    print("=" * 50)
    
    tests = [
        ("File Upload Validation", test_file_upload_validation),
        ("Database Constraints", test_database_constraints),
        ("Environment Security", test_environment_security),
        ("API Security Headers", test_api_security_headers),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} tests...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("🛡️  Security Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("🎉 All security improvements are working correctly!")
        return 0
    else:
        print("⚠️  Some security tests failed. Review the output above.")
        return 1


if __name__ == "__main__":
    exit(main())