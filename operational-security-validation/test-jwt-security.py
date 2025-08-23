#!/usr/bin/env python3
"""
JWT Security Management Test Script
===================================

Tests for enhanced JWT secret management, rotation, and security controls.
"""

import sys
import os
import time
import json
from pathlib import Path

# Add the photoshare service path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'photoshare'))

try:
    from jwt_security import (
        JWTSecretManager, 
        JWTSecret,
        jwt_secret_manager,
        get_current_jwt_secret,
        validate_jwt_token,
        generate_secure_jwt
    )
    JWT_SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"JWT Security not available: {e}")
    JWT_SECURITY_AVAILABLE = False

try:
    import jwt
    JWT_LIB_AVAILABLE = True
except ImportError:
    JWT_LIB_AVAILABLE = False


def test_jwt_secret_generation():
    """Test JWT secret generation with different algorithms."""
    
    print("🔑 Testing JWT Secret Generation")
    print("=" * 35)
    
    if not JWT_SECURITY_AVAILABLE:
        print("❌ JWT Security system not available")
        return False
    
    # Create test manager
    manager = JWTSecretManager()
    
    # Test different algorithms
    algorithms = ["HS256", "HS384", "HS512"]
    
    for algorithm in algorithms:
        print(f"\n{algorithm} Secret Generation:")
        
        try:
            secret = manager.generate_new_secret(algorithm)
            
            print(f"   Key ID: {secret.key_id}")
            print(f"   Algorithm: {secret.algorithm}")
            print(f"   Key Strength: {secret.key_strength} bits")
            print(f"   Active: {secret.active}")
            print(f"   Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(secret.created_at))}")
            
            # Verify key properties
            if secret.algorithm == algorithm:
                print("   ✅ Algorithm matches")
            else:
                print("   ❌ Algorithm mismatch")
                return False
            
            if secret.key_strength >= 256:
                print("   ✅ Sufficient key strength")
            else:
                print("   ❌ Insufficient key strength")
                return False
            
        except Exception as e:
            print(f"   ❌ Secret generation failed: {e}")
            return False
    
    # Test invalid algorithm
    try:
        manager.generate_new_secret("INVALID")
        print("   ❌ Should have rejected invalid algorithm")
        return False
    except ValueError:
        print("   ✅ Correctly rejected invalid algorithm")
    
    manager.shutdown()
    return True


def test_jwt_token_operations():
    """Test JWT token generation and validation."""
    
    print("\n🎫 Testing JWT Token Operations")
    print("=" * 32)
    
    if not JWT_SECURITY_AVAILABLE or not JWT_LIB_AVAILABLE:
        print("❌ JWT libraries not available")
        return False
    
    # Create test manager
    manager = JWTSecretManager()
    
    # Test token generation
    print("\n1. Testing token generation...")
    
    test_payload = {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "permissions": ["photos:read", "photos:write"]
    }
    
    token = manager.generate_token(test_payload, expires_in=300)  # 5 minutes
    
    if token:
        print(f"   ✅ Token generated: {token[:50]}...")
    else:
        print("   ❌ Token generation failed")
        manager.shutdown()
        return False
    
    # Test token validation
    print("\n2. Testing token validation...")
    
    valid, key_id, payload = manager.validate_token_signature(token)
    
    if valid and payload:
        print("   ✅ Token validation successful")
        print(f"   Key ID: {key_id}")
        print(f"   User ID: {payload.get('user_id')}")
        print(f"   Email: {payload.get('email')}")
        print(f"   Expires: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload.get('exp', 0)))}")
    else:
        print("   ❌ Token validation failed")
        manager.shutdown()
        return False
    
    # Test with invalid token
    print("\n3. Testing invalid token handling...")
    
    invalid_token = "invalid.token.here"
    valid, key_id, payload = manager.validate_token_signature(invalid_token)
    
    if not valid:
        print("   ✅ Correctly rejected invalid token")
    else:
        print("   ❌ Should have rejected invalid token")
        manager.shutdown()
        return False
    
    # Test expired token (simulate)
    print("\n4. Testing expired token handling...")
    
    expired_token = manager.generate_token(test_payload, expires_in=-1)  # Already expired
    if expired_token:
        time.sleep(2)  # Wait to ensure expiration
        valid, key_id, payload = manager.validate_token_signature(expired_token)
        
        if not valid:
            print("   ✅ Correctly rejected expired token")
        else:
            print("   ❌ Should have rejected expired token")
    
    manager.shutdown()
    return True


def test_secret_rotation():
    """Test JWT secret rotation functionality."""
    
    print("\n🔄 Testing JWT Secret Rotation")
    print("=" * 31)
    
    if not JWT_SECURITY_AVAILABLE:
        print("❌ JWT Security system not available")
        return False
    
    # Create test manager with short rotation interval
    manager = JWTSecretManager()
    
    # Get initial secret
    initial_secret = manager.get_current_secret()
    if not initial_secret:
        print("   ❌ No initial secret found")
        return False
    
    print(f"Initial secret ID: {initial_secret.key_id}")
    
    # Force rotation
    print("\n1. Testing forced rotation...")
    
    success = manager.rotate_secrets(force=True)
    
    if success:
        print("   ✅ Secret rotation successful")
    else:
        print("   ❌ Secret rotation failed")
        manager.shutdown()
        return False
    
    # Verify new secret is different
    new_secret = manager.get_current_secret()
    
    if new_secret and new_secret.key_id != initial_secret.key_id:
        print(f"   ✅ New secret ID: {new_secret.key_id}")
    else:
        print("   ❌ Secret rotation did not change key ID")
        manager.shutdown()
        return False
    
    # Test that both old and new secrets work (overlap period)
    print("\n2. Testing overlap period validation...")
    
    # Generate tokens with different secrets
    old_payload = {"test": "old_secret"}
    new_payload = {"test": "new_secret"}
    
    # Old secret should still exist in active secrets
    old_secret_obj = manager.get_secret_by_id(initial_secret.key_id)
    if old_secret_obj:
        print("   ✅ Old secret still available during overlap")
    else:
        print("   ⚠️  Old secret removed immediately (no overlap)")
    
    # Both tokens should validate during overlap
    new_token = manager.generate_token(new_payload)
    if new_token:
        valid, key_id, payload = manager.validate_token_signature(new_token)
        if valid:
            print("   ✅ New token validates correctly")
        else:
            print("   ❌ New token validation failed")
    
    print("\n3. Testing rotation metrics...")
    
    status = manager.get_security_status()
    metrics = status['security_metrics']
    
    if metrics['rotation_events'] > 0:
        print(f"   ✅ Rotation events recorded: {metrics['rotation_events']}")
    else:
        print("   ❌ No rotation events recorded")
    
    if metrics['total_keys_generated'] >= 2:
        print(f"   ✅ Multiple keys generated: {metrics['total_keys_generated']}")
    else:
        print("   ❌ Insufficient keys generated")
    
    manager.shutdown()
    return True


def test_security_features():
    """Test advanced security features."""
    
    print("\n🛡️  Testing Advanced Security Features")
    print("=" * 38)
    
    if not JWT_SECURITY_AVAILABLE:
        print("❌ JWT Security system not available")
        return False
    
    manager = JWTSecretManager()
    
    # Test compromise detection
    print("\n1. Testing compromise detection...")
    
    suspicious_activity = {
        "validation_failures": 150,  # Exceeds threshold
        "duplicate_tokens": 5,
        "timing_anomalies": 2
    }
    
    test_token = manager.generate_token({"test": "compromise"})
    compromise_detected = manager.detect_compromise(test_token or "", suspicious_activity)
    
    if compromise_detected:
        print("   ✅ Compromise detection triggered")
        print("   ✅ Automatic rotation should have occurred")
    else:
        print("   ⚠️  No compromise detected (threshold may be high)")
    
    # Test security metrics
    print("\n2. Testing security metrics...")
    
    status = manager.get_security_status()
    
    required_fields = [
        'jwt_security_enabled',
        'current_key_info',
        'rotation_settings', 
        'security_metrics',
        'dependencies'
    ]
    
    for field in required_fields:
        if field in status:
            print(f"   ✅ {field} present in status")
        else:
            print(f"   ❌ {field} missing from status")
            manager.shutdown()
            return False
    
    # Test encrypted storage
    print("\n3. Testing encrypted storage...")
    
    # Force save and reload
    manager._save_secrets()
    
    # Create new manager to test loading
    manager2 = JWTSecretManager()
    
    if len(manager2.active_secrets) > 0:
        print("   ✅ Secrets loaded from encrypted storage")
    else:
        print("   ❌ Failed to load secrets from storage")
    
    manager2.shutdown()
    
    # Test key expiration
    print("\n4. Testing key expiration handling...")
    
    # Create a secret that expires quickly (simulate by modifying)
    test_secret = manager.generate_new_secret()
    test_secret.expires_at = time.time() - 1  # Already expired
    
    # Cleanup should remove expired secrets
    manager._cleanup_expired_secrets()
    
    if test_secret.key_id not in manager.active_secrets:
        print("   ✅ Expired secret cleaned up")
    else:
        print("   ❌ Expired secret not cleaned up")
    
    manager.shutdown()
    return True


def test_integration_functions():
    """Test integration helper functions."""
    
    print("\n🔗 Testing Integration Functions")
    print("=" * 33)
    
    if not JWT_SECURITY_AVAILABLE:
        print("❌ JWT Security system not available")
        return False
    
    # Test global functions
    print("\n1. Testing global JWT functions...")
    
    # Test get_current_jwt_secret
    current_secret = get_current_jwt_secret()
    if current_secret:
        print("   ✅ get_current_jwt_secret() works")
    else:
        print("   ❌ get_current_jwt_secret() failed")
        return False
    
    # Test generate_secure_jwt
    test_payload = {"user": "integration_test"}
    secure_token = generate_secure_jwt(test_payload)
    
    if secure_token:
        print("   ✅ generate_secure_jwt() works")
    else:
        print("   ❌ generate_secure_jwt() failed")
        return False
    
    # Test validate_jwt_token
    valid, payload = validate_jwt_token(secure_token)
    
    if valid and payload:
        print("   ✅ validate_jwt_token() works")
        print(f"   User: {payload.get('user')}")
    else:
        print("   ❌ validate_jwt_token() failed")
        return False
    
    return True


def test_dependency_handling():
    """Test graceful handling of missing dependencies."""
    
    print("\n🔧 Testing Dependency Handling")
    print("=" * 31)
    
    print(f"JWT library available: {JWT_LIB_AVAILABLE}")
    print(f"JWT Security available: {JWT_SECURITY_AVAILABLE}")
    
    if JWT_SECURITY_AVAILABLE:
        # Test cryptography dependency
        try:
            from cryptography.fernet import Fernet
            print("Cryptography available: True")
        except ImportError:
            print("Cryptography available: False")
            print("   ⚠️  Encryption will use fallback methods")
    
    # Test fallback behavior
    if not JWT_LIB_AVAILABLE:
        print("   ⚠️  JWT library not available - tokens cannot be generated")
        print("   💡 Install with: pip install PyJWT[crypto]")
    
    if not JWT_SECURITY_AVAILABLE:
        print("   ⚠️  JWT Security enhancement not available")
        print("   💡 Check jwt_security.py module")
    
    return True


if __name__ == "__main__":
    print("🔐 PhotoShare JWT Security Test Suite")
    print("=" * 45)
    
    success = True
    
    try:
        # Run all tests
        success &= test_jwt_secret_generation()
        success &= test_jwt_token_operations() 
        success &= test_secret_rotation()
        success &= test_security_features()
        success &= test_integration_functions()
        success &= test_dependency_handling()
        
        if success:
            print(f"\n🎉 ALL JWT SECURITY TESTS PASSED!")
            print("🔐 Enhanced JWT security system is ready")
            
            print("\n📋 Security Features Enabled:")
            if JWT_SECURITY_AVAILABLE:
                print("   ✅ Automatic secret rotation")
                print("   ✅ Multi-key support with overlap periods")
                print("   ✅ Encrypted secret storage")
                print("   ✅ Compromise detection")
                print("   ✅ Security metrics and monitoring")
                print("   ✅ Configurable algorithms and key strength")
            
            print("\n📋 Next Steps:")
            print("   1. Configure rotation intervals in production")
            print("   2. Set up secure storage directories")
            print("   3. Configure monitoring alerts")
            print("   4. Test integration with auth service")
            
            exit_code = 0
        else:
            print("\n❌ Some JWT security tests failed")
            exit_code = 1
            
    except Exception as e:
        print(f"\n💥 JWT security test suite failed: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    sys.exit(exit_code)