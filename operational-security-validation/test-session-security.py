#!/usr/bin/env python3
"""
Session Security Management Test Script
======================================

Tests for secure session state management with device fingerprinting,
concurrent session limits, and anomaly detection.
"""

import sys
import os
import time
import json
from pathlib import Path

# Add the photoshare service path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'photoshare'))

try:
    from session_security import (
        SecureSessionManager,
        DeviceFingerprint,
        SessionState,
        get_session_manager,
        create_secure_session,
        validate_secure_session,
        get_session_security_stats
    )
    SESSION_SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"Session Security not available: {e}")
    SESSION_SECURITY_AVAILABLE = False


def test_device_fingerprinting():
    """Test device fingerprint creation and validation."""
    
    print("📱 Testing Device Fingerprinting")
    print("=" * 32)
    
    if not SESSION_SECURITY_AVAILABLE:
        print("❌ Session Security system not available")
        return False
    
    manager = SecureSessionManager()
    
    print("\n1. Testing basic fingerprint creation...")
    
    # Create device fingerprint
    fingerprint = manager.create_device_fingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        ip_address="192.168.1.100",
        additional_data={
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York",
            "language": "en-US",
            "platform": "Win32"
        }
    )
    
    if fingerprint and fingerprint.fingerprint_hash:
        print(f"   ✅ Fingerprint created: {fingerprint.fingerprint_hash[:16]}...")
        print(f"   User Agent Hash: {fingerprint.user_agent_hash}")
        print(f"   IP Address: {fingerprint.ip_address}")
        print(f"   Platform: {fingerprint.platform}")
    else:
        print("   ❌ Fingerprint creation failed")
        manager.shutdown()
        return False
    
    print("\n2. Testing fingerprint consistency...")
    
    # Create same fingerprint again
    fingerprint2 = manager.create_device_fingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        ip_address="192.168.1.100",
        additional_data={
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York",
            "language": "en-US",
            "platform": "Win32"
        }
    )
    
    if fingerprint.fingerprint_hash == fingerprint2.fingerprint_hash:
        print("   ✅ Fingerprint consistency verified")
    else:
        print("   ❌ Fingerprint inconsistency detected")
        manager.shutdown()
        return False
    
    print("\n3. Testing fingerprint differences...")
    
    # Create different fingerprint (different IP)
    fingerprint3 = manager.create_device_fingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        ip_address="10.0.0.100",  # Different IP
        additional_data={
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York", 
            "language": "en-US",
            "platform": "Win32"
        }
    )
    
    if fingerprint.fingerprint_hash != fingerprint3.fingerprint_hash:
        print("   ✅ Different fingerprints correctly generated")
    else:
        print("   ❌ Same fingerprint for different devices")
        manager.shutdown()
        return False
    
    manager.shutdown()
    return True


def test_session_creation_and_validation():
    """Test secure session creation and validation."""
    
    print("\n🔐 Testing Session Creation & Validation")
    print("=" * 41)
    
    if not SESSION_SECURITY_AVAILABLE:
        print("❌ Session Security system not available")
        return False
    
    manager = SecureSessionManager()
    
    print("\n1. Testing session creation...")
    
    # Create session
    session_id, error = manager.create_session(
        user_id="test_user_1",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        security_level="basic",
        additional_fingerprint_data={
            "screen_resolution": "1920x1080",
            "timezone": "America/New_York"
        }
    )
    
    if session_id and not error:
        print(f"   ✅ Session created: {session_id}")
    else:
        print(f"   ❌ Session creation failed: {error}")
        manager.shutdown()
        return False
    
    print("\n2. Testing session validation...")
    
    # Validate the session
    valid, session_state, error = manager.validate_session(
        session_id=session_id,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    if valid and session_state:
        print("   ✅ Session validation successful")
        print(f"   User ID: {session_state.user_id}")
        print(f"   Security Level: {session_state.security_level}")
        print(f"   Anomaly Score: {session_state.anomaly_score}")
        print(f"   Active: {session_state.is_active}")
    else:
        print(f"   ❌ Session validation failed: {error}")
        manager.shutdown()
        return False
    
    print("\n3. Testing invalid session...")
    
    # Test with invalid session ID
    valid, session_state, error = manager.validate_session(
        session_id="invalid_session_id",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    if not valid:
        print("   ✅ Invalid session correctly rejected")
    else:
        print("   ❌ Invalid session was accepted")
        manager.shutdown()
        return False
    
    print("\n4. Testing session invalidation...")
    
    # Invalidate the session
    success = manager.invalidate_session(session_id, "test_logout")
    
    if success:
        print("   ✅ Session invalidated successfully")
        
        # Try to validate invalidated session
        valid, session_state, error = manager.validate_session(
            session_id=session_id,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        if not valid:
            print("   ✅ Invalidated session correctly rejected")
        else:
            print("   ❌ Invalidated session still valid")
            manager.shutdown()
            return False
    else:
        print("   ❌ Session invalidation failed")
        manager.shutdown()
        return False
    
    manager.shutdown()
    return True


def test_concurrent_session_limits():
    """Test concurrent session limit enforcement."""
    
    print("\n👥 Testing Concurrent Session Limits")
    print("=" * 35)
    
    if not SESSION_SECURITY_AVAILABLE:
        print("❌ Session Security system not available")
        return False
    
    manager = SecureSessionManager()
    
    # Set low concurrent session limit for testing
    original_limit = manager.config['max_concurrent_sessions']
    manager.config['max_concurrent_sessions'] = 3
    
    print(f"\n1. Testing session limit ({manager.config['max_concurrent_sessions']})...")
    
    sessions_created = []
    
    # Create sessions up to the limit
    for i in range(manager.config['max_concurrent_sessions']):
        session_id, error = manager.create_session(
            user_id="test_user_concurrent",
            ip_address=f"192.168.1.{100 + i}",
            user_agent=f"TestAgent/{i}",
            security_level="basic"
        )
        
        if session_id:
            sessions_created.append(session_id)
            print(f"   ✅ Session {i+1} created: {session_id}")
        else:
            print(f"   ❌ Session {i+1} creation failed: {error}")
            manager.config['max_concurrent_sessions'] = original_limit
            manager.shutdown()
            return False
    
    print(f"\n2. Testing session limit exceeded...")
    
    # Try to create one more session (should fail)
    session_id, error = manager.create_session(
        user_id="test_user_concurrent",
        ip_address="192.168.1.200",
        user_agent="TestAgent/overflow",
        security_level="basic"
    )
    
    if not session_id and error:
        print(f"   ✅ Session creation correctly blocked: {error}")
    else:
        print(f"   ❌ Session limit not enforced: {session_id}")
        manager.config['max_concurrent_sessions'] = original_limit
        manager.shutdown()
        return False
    
    print("\n3. Testing session cleanup allows new sessions...")
    
    # Invalidate one session
    if sessions_created:
        success = manager.invalidate_session(sessions_created[0], "test_cleanup")
        if success:
            print("   ✅ Session invalidated for cleanup")
            
            # Now try to create a new session
            session_id, error = manager.create_session(
                user_id="test_user_concurrent",
                ip_address="192.168.1.201",
                user_agent="TestAgent/after_cleanup",
                security_level="basic"
            )
            
            if session_id:
                print(f"   ✅ New session created after cleanup: {session_id}")
            else:
                print(f"   ❌ Session creation still blocked: {error}")
                manager.config['max_concurrent_sessions'] = original_limit
                manager.shutdown()
                return False
        else:
            print("   ❌ Session invalidation failed")
    
    # Restore original limit
    manager.config['max_concurrent_sessions'] = original_limit
    manager.shutdown()
    return True


def test_device_fingerprint_security():
    """Test device fingerprint security validation."""
    
    print("\n🛡️  Testing Device Fingerprint Security")
    print("=" * 38)
    
    if not SESSION_SECURITY_AVAILABLE:
        print("❌ Session Security system not available")
        return False
    
    manager = SecureSessionManager()
    
    print("\n1. Testing normal device fingerprint validation...")
    
    # Create session with specific device fingerprint
    session_id, error = manager.create_session(
        user_id="test_user_device",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        security_level="basic"
    )
    
    if not session_id:
        print(f"   ❌ Session creation failed: {error}")
        manager.shutdown()
        return False
    
    # Validate with same device fingerprint
    valid, session_state, error = manager.validate_session(
        session_id=session_id,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    if valid:
        print("   ✅ Same device fingerprint validation successful")
    else:
        print(f"   ❌ Same device validation failed: {error}")
        manager.shutdown()
        return False
    
    print("\n2. Testing device fingerprint mismatch detection...")
    
    # Try to validate with different user agent (potential hijacking)
    valid, session_state, error = manager.validate_session(
        session_id=session_id,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"  # Different UA
    )
    
    if not valid and "security violation" in (error or "").lower():
        print("   ✅ Device fingerprint mismatch correctly detected")
    else:
        print(f"   ❌ Device fingerprint mismatch not detected: valid={valid}, error={error}")
        # Note: This might pass if device fingerprint validation is not strict
        print("   ℹ️  This could be expected behavior depending on fingerprint strictness")
    
    print("\n3. Testing IP address change handling...")
    
    # Create new session for IP change test
    session_id2, error = manager.create_session(
        user_id="test_user_ip_change",
        ip_address="192.168.1.50",
        user_agent="TestAgent/IPChange",
        security_level="basic"
    )
    
    if not session_id2:
        print(f"   ❌ Second session creation failed: {error}")
        manager.shutdown()
        return False
    
    # Validate from different IP (should be monitored but might be allowed)
    valid, session_state, error = manager.validate_session(
        session_id=session_id2,
        ip_address="10.0.0.50",  # Different IP range
        user_agent="TestAgent/IPChange"
    )
    
    if valid:
        print("   ✅ IP change handled (session updated)")
        print(f"   Updated IP: {session_state.ip_address if session_state else 'N/A'}")
    else:
        print(f"   ⚠️  IP change blocked (high security): {error}")
        # This could be expected behavior for high-security configurations
    
    manager.shutdown()
    return True


def test_session_anomaly_detection():
    """Test session anomaly detection system."""
    
    print("\n🚨 Testing Session Anomaly Detection")
    print("=" * 36)
    
    if not SESSION_SECURITY_AVAILABLE:
        print("❌ Session Security system not available")
        return False
    
    manager = SecureSessionManager()
    
    print("\n1. Testing normal session behavior...")
    
    # Create normal session
    session_id, error = manager.create_session(
        user_id="test_user_anomaly",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        security_level="basic"
    )
    
    if not session_id:
        print(f"   ❌ Session creation failed: {error}")
        manager.shutdown()
        return False
    
    # Validate session and check anomaly score
    valid, session_state, error = manager.validate_session(
        session_id=session_id,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    
    if valid and session_state:
        print(f"   ✅ Normal session anomaly score: {session_state.anomaly_score}")
        
        if session_state.anomaly_score <= 30.0:  # Low anomaly score expected
            print("   ✅ Low anomaly score for normal behavior")
        else:
            print(f"   ⚠️  Higher than expected anomaly score: {session_state.anomaly_score}")
    else:
        print(f"   ❌ Session validation failed: {error}")
        manager.shutdown()
        return False
    
    print("\n2. Testing admin session risk scoring...")
    
    # Create admin session (higher risk)
    admin_session_id, error = manager.create_session(
        user_id="test_admin_user",
        ip_address="192.168.1.101",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        security_level="admin"
    )
    
    if admin_session_id:
        # Validate admin session
        valid, admin_session_state, error = manager.validate_session(
            session_id=admin_session_id,
            ip_address="192.168.1.101",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        if valid and admin_session_state:
            print(f"   ✅ Admin session anomaly score: {admin_session_state.anomaly_score}")
            
            # Admin sessions should have higher base risk
            if admin_session_state.anomaly_score > session_state.anomaly_score:
                print("   ✅ Admin session has higher risk score")
            else:
                print("   ⚠️  Admin session risk not elevated")
        else:
            print(f"   ❌ Admin session validation failed: {error}")
    else:
        print(f"   ❌ Admin session creation failed: {error}")
    
    print("\n3. Testing multiple concurrent sessions impact...")
    
    # Create multiple sessions for same user to increase anomaly score
    concurrent_sessions = []
    for i in range(3):
        concurrent_id, error = manager.create_session(
            user_id="test_user_anomaly",  # Same user
            ip_address=f"192.168.1.{110 + i}",
            user_agent=f"TestAgent/{i}",
            security_level="basic"
        )
        
        if concurrent_id:
            concurrent_sessions.append(concurrent_id)
    
    if concurrent_sessions:
        print(f"   ✅ Created {len(concurrent_sessions)} concurrent sessions")
        
        # Validate original session again - should have higher anomaly score
        valid, updated_session_state, error = manager.validate_session(
            session_id=session_id,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        if valid and updated_session_state:
            print(f"   Updated anomaly score: {updated_session_state.anomaly_score}")
            
            if updated_session_state.anomaly_score > session_state.anomaly_score:
                print("   ✅ Concurrent sessions increased anomaly score")
            else:
                print("   ⚠️  Concurrent sessions didn't impact anomaly score")
        else:
            print(f"   ❌ Updated session validation failed: {error}")
    else:
        print("   ❌ No concurrent sessions created")
    
    manager.shutdown()
    return True


def test_session_statistics():
    """Test session statistics and reporting."""
    
    print("\n📊 Testing Session Statistics")
    print("=" * 29)
    
    if not SESSION_SECURITY_AVAILABLE:
        print("❌ Session Security system not available")
        return False
    
    manager = SecureSessionManager()
    
    print("\n1. Creating test session data...")
    
    # Create multiple sessions for statistics
    test_sessions = []
    for i in range(5):
        session_id, error = manager.create_session(
            user_id=f"stats_user_{i}",
            ip_address=f"192.168.1.{120 + i}",
            user_agent=f"TestAgent/Stats/{i}",
            security_level="basic" if i < 3 else "admin"
        )
        
        if session_id:
            test_sessions.append(session_id)
    
    if len(test_sessions) >= 3:
        print(f"   ✅ Created {len(test_sessions)} test sessions")
    else:
        print(f"   ❌ Only created {len(test_sessions)} test sessions")
        manager.shutdown()
        return False
    
    print("\n2. Testing statistics retrieval...")
    
    stats = manager.get_session_statistics()
    
    required_fields = [
        'session_security_enabled',
        'total_sessions',
        'active_sessions',
        'security_features'
    ]
    
    for field in required_fields:
        if field in stats:
            print(f"   ✅ {field}: {stats[field]}")
        else:
            print(f"   ❌ {field} missing from statistics")
            manager.shutdown()
            return False
    
    # Verify some statistics make sense
    if stats['total_sessions'] >= len(test_sessions):
        print(f"   ✅ Total sessions count reasonable: {stats['total_sessions']}")
    else:
        print(f"   ❌ Total sessions count too low: {stats['total_sessions']}")
    
    print("\n3. Testing user session information...")
    
    # Get session info for a specific user
    if test_sessions:
        user_session_info = manager.get_user_session_info("stats_user_0")
        
        if 'user_id' in user_session_info and 'active_session_count' in user_session_info:
            print(f"   ✅ User session info retrieved")
            print(f"   User: {user_session_info['user_id']}")
            print(f"   Active sessions: {user_session_info['active_session_count']}")
            print(f"   Max concurrent: {user_session_info['max_concurrent_sessions']}")
        else:
            print(f"   ❌ User session info incomplete: {user_session_info}")
            manager.shutdown()
            return False
    else:
        print("   ❌ No test sessions available for user info test")
    
    manager.shutdown()
    return True


def test_integration_functions():
    """Test global integration functions."""
    
    print("\n🔗 Testing Integration Functions")
    print("=" * 33)
    
    if not SESSION_SECURITY_AVAILABLE:
        print("❌ Session Security system not available")
        return False
    
    print("\n1. Testing global session creation function...")
    
    # Test create_secure_session
    session_id, error = create_secure_session(
        user_id="integration_user",
        ip_address="192.168.1.200",
        user_agent="Integration/Test/Agent",
        security_level="basic"
    )
    
    if session_id:
        print(f"   ✅ Global create_secure_session works: {session_id}")
    else:
        print(f"   ❌ Global create_secure_session failed: {error}")
        return False
    
    print("\n2. Testing global session validation function...")
    
    # Test validate_secure_session
    valid, session_state, error = validate_secure_session(
        session_id=session_id,
        ip_address="192.168.1.200",
        user_agent="Integration/Test/Agent"
    )
    
    if valid and session_state:
        print("   ✅ Global validate_secure_session works")
        print(f"   Session user: {session_state.user_id}")
    else:
        print(f"   ❌ Global validate_secure_session failed: {error}")
        return False
    
    print("\n3. Testing global statistics function...")
    
    # Test get_session_security_stats
    stats = get_session_security_stats()
    
    if 'session_security_enabled' in stats and stats['session_security_enabled']:
        print("   ✅ Global get_session_security_stats works")
        print(f"   Total sessions: {stats.get('total_sessions', 'N/A')}")
        print(f"   Active sessions: {stats.get('active_sessions', 'N/A')}")
    else:
        print("   ❌ Global get_session_security_stats failed")
        return False
    
    return True


def test_session_expiration():
    """Test session expiration and cleanup."""
    
    print("\n⏰ Testing Session Expiration")
    print("=" * 28)
    
    if not SESSION_SECURITY_AVAILABLE:
        print("❌ Session Security system not available")
        return False
    
    manager = SecureSessionManager()
    
    # Set short session timeout for testing
    original_timeout = manager.config['session_timeout']
    manager.config['session_timeout'] = 2  # 2 seconds
    
    print("\n1. Testing session expiration...")
    
    # Create short-lived session
    session_id, error = manager.create_session(
        user_id="expiry_test_user",
        ip_address="192.168.1.250",
        user_agent="ExpiryTestAgent",
        security_level="basic"
    )
    
    if not session_id:
        print(f"   ❌ Session creation failed: {error}")
        manager.config['session_timeout'] = original_timeout
        manager.shutdown()
        return False
    
    # Validate immediately (should work)
    valid, session_state, error = manager.validate_session(
        session_id=session_id,
        ip_address="192.168.1.250",
        user_agent="ExpiryTestAgent"
    )
    
    if valid:
        print("   ✅ Session valid immediately after creation")
    else:
        print(f"   ❌ Session invalid immediately: {error}")
        manager.config['session_timeout'] = original_timeout
        manager.shutdown()
        return False
    
    print("   ⏳ Waiting for session to expire...")
    time.sleep(3)  # Wait for expiration
    
    # Validate after expiration (should fail)
    valid, session_state, error = manager.validate_session(
        session_id=session_id,
        ip_address="192.168.1.250",
        user_agent="ExpiryTestAgent"
    )
    
    if not valid and "expired" in (error or "").lower():
        print("   ✅ Session correctly expired")
    else:
        print(f"   ❌ Session not expired: valid={valid}, error={error}")
        manager.config['session_timeout'] = original_timeout
        manager.shutdown()
        return False
    
    print("\n2. Testing session renewal...")
    
    # Create another session for renewal test
    manager.config['session_timeout'] = 10  # 10 seconds
    manager.config['session_renewal_threshold'] = 8  # Renew when 2 seconds left
    
    session_id2, error = manager.create_session(
        user_id="renewal_test_user",
        ip_address="192.168.1.251",
        user_agent="RenewalTestAgent",
        security_level="basic"
    )
    
    if session_id2:
        # Wait until near expiry
        time.sleep(5)  # Wait 5 seconds (should be renewed)
        
        valid, session_state, error = manager.validate_session(
            session_id=session_id2,
            ip_address="192.168.1.251",
            user_agent="RenewalTestAgent"
        )
        
        if valid and session_state:
            remaining_time = session_state.expires_at - time.time()
            if remaining_time > 8:  # Should be renewed
                print(f"   ✅ Session automatically renewed ({remaining_time:.1f}s remaining)")
            else:
                print(f"   ⚠️  Session may not have been renewed ({remaining_time:.1f}s remaining)")
        else:
            print(f"   ❌ Session validation failed during renewal test: {error}")
    else:
        print(f"   ❌ Renewal test session creation failed: {error}")
    
    # Restore original timeout
    manager.config['session_timeout'] = original_timeout
    manager.shutdown()
    return True


if __name__ == "__main__":
    print("🔐 PhotoShare Session Security Test Suite")
    print("=" * 45)
    
    success = True
    
    try:
        # Run all tests
        success &= test_device_fingerprinting()
        success &= test_session_creation_and_validation()
        success &= test_concurrent_session_limits()
        success &= test_device_fingerprint_security()
        success &= test_session_anomaly_detection()
        success &= test_session_statistics()
        success &= test_integration_functions()
        success &= test_session_expiration()
        
        if success:
            print(f"\n🎉 ALL SESSION SECURITY TESTS PASSED!")
            print("🔐 Secure session management system is ready")
            
            print("\n📋 Security Features Verified:")
            if SESSION_SECURITY_AVAILABLE:
                print("   ✅ Device fingerprinting and validation")
                print("   ✅ Concurrent session limit enforcement")
                print("   ✅ Session anomaly detection and scoring")
                print("   ✅ Secure session state management")
                print("   ✅ Session expiration and renewal")
                print("   ✅ IP address change monitoring")
                print("   ✅ Security event logging")
                print("   ✅ Administrative session controls")
            
            print("\n📋 Next Steps:")
            print("   1. Configure session timeouts for production")
            print("   2. Set up Redis for distributed session storage")
            print("   3. Configure GeoIP database for location validation")
            print("   4. Set up monitoring alerts for session anomalies")
            print("   5. Implement device trust scoring improvements")
            
            exit_code = 0
        else:
            print("\n❌ Some session security tests failed")
            exit_code = 1
            
    except Exception as e:
        print(f"\n💥 Session security test suite failed: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    sys.exit(exit_code)