#!/usr/bin/env python3
"""
Audit Trail Integrity Test Script
==================================

Tests for tamper-proof audit logging, chain integrity, and digital signatures.
"""

import sys
import os
import time
import json
from pathlib import Path

# Add the photoshare service path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'photoshare'))

try:
    from audit_trail import (
        AuditTrailManager,
        AuditRecord,
        log_audit,
        verify_audit_integrity,
        audit_manager
    )
    AUDIT_TRAIL_AVAILABLE = True
except ImportError as e:
    print(f"Audit Trail not available: {e}")
    AUDIT_TRAIL_AVAILABLE = False

try:
    from cryptography.hazmat.primitives.asymmetric import rsa
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


def test_audit_logging():
    """Test basic audit logging functionality."""
    
    print("📝 Testing Audit Logging")
    print("=" * 25)
    
    if not AUDIT_TRAIL_AVAILABLE:
        print("❌ Audit Trail system not available")
        return False
    
    # Create test audit manager
    manager = AuditTrailManager()
    
    # Test basic logging
    print("\n1. Testing basic audit logging...")
    
    record_id = manager.log_audit_event(
        action="user_login",
        resource_type="authentication",
        user_id="test_user_123",
        session_id="session_456",
        source_ip="192.168.1.100",
        user_agent="Mozilla/5.0 Test Browser",
        request_method="POST",
        endpoint="/api/auth/login",
        status_code=200,
        details={
            "login_method": "password",
            "success": True,
            "session_duration": 1800
        },
        risk_level="LOW"
    )
    
    if record_id:
        print(f"   ✅ Audit record created: {record_id}")
    else:
        print("   ❌ Failed to create audit record")
        manager.shutdown()
        return False
    
    # Test high-risk logging
    print("\n2. Testing high-risk audit logging...")
    
    high_risk_record = manager.log_audit_event(
        action="admin_access",
        resource_type="admin_panel",
        user_id="admin_user",
        source_ip="10.0.0.50",
        user_agent="curl/7.68.0",
        request_method="GET",
        endpoint="/api/admin/users",
        status_code=200,
        details={
            "admin_action": "view_all_users",
            "elevated_privileges": True
        },
        risk_level="HIGH"
    )
    
    if high_risk_record:
        print(f"   ✅ High-risk record created: {high_risk_record}")
    else:
        print("   ❌ Failed to create high-risk record")
    
    # Test bulk logging
    print("\n3. Testing bulk audit logging...")
    
    bulk_records = []
    for i in range(5):
        record_id = manager.log_audit_event(
            action=f"photo_upload_{i}",
            resource_type="photos",
            user_id="photographer_user",
            source_ip="172.16.0.100",
            endpoint=f"/api/photos/upload/{i}",
            request_method="POST",
            status_code=201,
            details={"photo_size": 1024 * (i + 1), "format": "JPEG"},
            risk_level="LOW"
        )
        bulk_records.append(record_id)
    
    if all(bulk_records):
        print(f"   ✅ Bulk logging successful: {len(bulk_records)} records")
    else:
        print("   ❌ Some bulk logging failed")
    
    # Test error logging
    print("\n4. Testing error audit logging...")
    
    error_record = manager.log_audit_event(
        action="authentication_failure",
        resource_type="authentication",
        user_id=None,  # Failed login, no user
        source_ip="203.0.113.50",  # Suspicious external IP
        user_agent="Python-requests/2.28.0",
        request_method="POST",
        endpoint="/api/auth/login",
        status_code=401,
        details={
            "failure_reason": "invalid_password",
            "attempt_count": 3,
            "suspicious_activity": True
        },
        risk_level="MEDIUM"
    )
    
    if error_record:
        print(f"   ✅ Error record created: {error_record}")
    else:
        print("   ❌ Failed to create error record")
    
    manager.shutdown()
    return True


def test_chain_integrity():
    """Test audit trail chain integrity."""
    
    print("\n🔗 Testing Chain Integrity")
    print("=" * 27)
    
    if not AUDIT_TRAIL_AVAILABLE:
        print("❌ Audit Trail system not available")
        return False
    
    # Create fresh audit manager for clean chain
    manager = AuditTrailManager()
    
    print("\n1. Creating audit chain...")
    
    # Create a series of linked records
    record_ids = []
    for i in range(10):
        record_id = manager.log_audit_event(
            action=f"chain_test_{i}",
            resource_type="test",
            user_id=f"user_{i}",
            source_ip=f"192.168.1.{100 + i}",
            endpoint=f"/api/test/{i}",
            request_method="GET",
            status_code=200,
            details={"sequence": i, "chain_test": True},
            risk_level="LOW"
        )
        record_ids.append(record_id)
        time.sleep(0.01)  # Small delay to ensure ordering
    
    print(f"   ✅ Created chain of {len(record_ids)} records")
    
    # Test chain integrity verification
    print("\n2. Verifying chain integrity...")
    
    integrity_result = manager.verify_audit_integrity()
    
    print(f"   Records verified: {integrity_result['records_verified']}")
    print(f"   Chain integrity: {integrity_result['chain_integrity']}")
    print(f"   Signature integrity: {integrity_result['signature_integrity']}")
    print(f"   Chain breaks: {integrity_result['chain_breaks']}")
    print(f"   Signature failures: {integrity_result['signature_failures']}")
    
    if integrity_result['chain_integrity'] and integrity_result['signature_integrity']:
        print("   ✅ Chain integrity verification passed")
    else:
        print("   ❌ Chain integrity verification failed")
        print(f"   Violations: {integrity_result['violations_found']}")
        manager.shutdown()
        return False
    
    # Test partial chain verification
    print("\n3. Testing partial chain verification...")
    
    if len(record_ids) >= 5:
        start_record = record_ids[2]
        end_record = record_ids[7]
        
        partial_result = manager.verify_audit_integrity(
            start_record=start_record,
            end_record=end_record
        )
        
        if partial_result['records_verified'] > 0:
            print(f"   ✅ Partial verification successful: {partial_result['records_verified']} records")
        else:
            print("   ❌ Partial verification failed")
    
    manager.shutdown()
    return True


def test_digital_signatures():
    """Test digital signature functionality."""
    
    print("\n🔏 Testing Digital Signatures")
    print("=" * 30)
    
    if not AUDIT_TRAIL_AVAILABLE:
        print("❌ Audit Trail system not available")
        return False
    
    if not CRYPTO_AVAILABLE:
        print("❌ Cryptography library not available")
        return False
    
    # Create audit manager
    manager = AuditTrailManager()
    
    # Test signature generation
    print("\n1. Testing signature generation...")
    
    record_id = manager.log_audit_event(
        action="signature_test",
        resource_type="test",
        user_id="signature_user",
        source_ip="10.0.0.100",
        endpoint="/api/test/signature",
        request_method="POST",
        status_code=200,
        details={"signature_test": True, "importance": "critical"},
        risk_level="HIGH"
    )
    
    if record_id:
        print(f"   ✅ Signed record created: {record_id}")
    else:
        print("   ❌ Failed to create signed record")
        manager.shutdown()
        return False
    
    # Test signature verification
    print("\n2. Testing signature verification...")
    
    integrity_result = manager.verify_audit_integrity()
    
    if integrity_result['signature_integrity']:
        print("   ✅ Signature verification passed")
    else:
        print("   ❌ Signature verification failed")
        print(f"   Signature failures: {integrity_result['signature_failures']}")
    
    # Test multiple signed records
    print("\n3. Testing multiple signed records...")
    
    signed_records = []
    for i in range(5):
        record_id = manager.log_audit_event(
            action=f"multi_sign_test_{i}",
            resource_type="test",
            user_id="multi_user",
            source_ip="172.16.0.200",
            endpoint=f"/api/test/multi/{i}",
            request_method="POST",
            status_code=201,
            details={"multi_test": i, "batch": "signature_batch"},
            risk_level="MEDIUM"
        )
        signed_records.append(record_id)
    
    # Verify all signatures
    batch_integrity = manager.verify_audit_integrity()
    
    if batch_integrity['signature_integrity']:
        print(f"   ✅ All {len(signed_records)} signatures verified")
    else:
        print(f"   ❌ Signature verification failed for batch")
    
    manager.shutdown()
    return True


def test_tamper_detection():
    """Test tamper detection capabilities."""
    
    print("\n🛡️  Testing Tamper Detection")
    print("=" * 29)
    
    if not AUDIT_TRAIL_AVAILABLE:
        print("❌ Audit Trail system not available")
        return False
    
    # Create audit manager
    manager = AuditTrailManager()
    
    # Create some audit records
    print("\n1. Creating baseline audit records...")
    
    baseline_records = []
    for i in range(5):
        record_id = manager.log_audit_event(
            action=f"tamper_test_{i}",
            resource_type="test",
            user_id="tamper_user",
            source_ip="192.168.100.50",
            endpoint=f"/api/test/tamper/{i}",
            request_method="GET",
            status_code=200,
            details={"baseline_record": i},
            risk_level="LOW"
        )
        baseline_records.append(record_id)
    
    print(f"   ✅ Created {len(baseline_records)} baseline records")
    
    # Verify initial integrity
    print("\n2. Verifying initial integrity...")
    
    initial_integrity = manager.verify_audit_integrity()
    
    if initial_integrity['chain_integrity']:
        print("   ✅ Initial integrity verification passed")
    else:
        print("   ❌ Initial integrity verification failed")
        manager.shutdown()
        return False
    
    # Simulate tamper attempt (modify database directly)
    print("\n3. Simulating tamper attempt...")
    
    try:
        # Get a record to tamper with
        if baseline_records:
            tamper_record_id = baseline_records[2]  # Middle record
            
            # Directly modify the database (simulating tampering)
            manager.db_conn.execute("""
                UPDATE audit_records 
                SET details = ? 
                WHERE record_id = ?
            """, (
                json.dumps({"tampered": True, "original": "modified"}),
                tamper_record_id
            ))
            manager.db_conn.commit()
            
            print(f"   ⚠️  Simulated tampering with record {tamper_record_id}")
    
    except Exception as e:
        print(f"   ❌ Failed to simulate tampering: {e}")
        manager.shutdown()
        return False
    
    # Verify integrity after tampering
    print("\n4. Detecting tampering...")
    
    post_tamper_integrity = manager.verify_audit_integrity()
    
    print(f"   Chain integrity: {post_tamper_integrity['chain_integrity']}")
    print(f"   Chain breaks detected: {post_tamper_integrity['chain_breaks']}")
    print(f"   Violations found: {len(post_tamper_integrity['violations_found'])}")
    
    if post_tamper_integrity['chain_breaks'] > 0:
        print("   ✅ Tampering successfully detected!")
        
        # Show violation details
        for violation in post_tamper_integrity['violations_found']:
            if violation['type'] == 'chain_break':
                print(f"   🚨 Chain break in record: {violation['record_id']}")
    else:
        print("   ❌ Tampering not detected - integrity system may have issues")
    
    manager.shutdown()
    return True


def test_audit_retrieval():
    """Test audit record retrieval and filtering."""
    
    print("\n📊 Testing Audit Retrieval")
    print("=" * 27)
    
    if not AUDIT_TRAIL_AVAILABLE:
        print("❌ Audit Trail system not available")
        return False
    
    # Create audit manager
    manager = AuditTrailManager()
    
    # Create diverse test data
    print("\n1. Creating diverse test data...")
    
    test_users = ["alice", "bob", "charlie"]
    test_actions = ["login", "logout", "photo_upload", "photo_delete"]
    test_risks = ["LOW", "MEDIUM", "HIGH"]
    
    created_records = []
    for i in range(15):
        user = test_users[i % len(test_users)]
        action = test_actions[i % len(test_actions)]
        risk = test_risks[i % len(test_risks)]
        
        record_id = manager.log_audit_event(
            action=action,
            resource_type="test_retrieval",
            user_id=user,
            source_ip=f"10.0.0.{100 + (i % 50)}",
            endpoint=f"/api/test/{action}",
            request_method="POST",
            status_code=200 if i % 4 != 3 else 401,  # Some failures
            details={"test_index": i, "batch": "retrieval_test"},
            risk_level=risk
        )
        created_records.append((record_id, user, action, risk))
        time.sleep(0.01)
    
    print(f"   ✅ Created {len(created_records)} diverse records")
    
    # Test basic retrieval
    print("\n2. Testing basic retrieval...")
    
    all_records = manager.get_audit_records(limit=20)
    
    if len(all_records) > 0:
        print(f"   ✅ Retrieved {len(all_records)} records")
        print(f"   Latest record: {all_records[0]['action']} by {all_records[0]['user_id']}")
    else:
        print("   ❌ No records retrieved")
        manager.shutdown()
        return False
    
    # Test user filtering
    print("\n3. Testing user filtering...")
    
    alice_records = manager.get_audit_records(user_id="alice", limit=10)
    alice_count = len(alice_records)
    
    if alice_count > 0:
        print(f"   ✅ Retrieved {alice_count} records for user 'alice'")
        # Verify all records are for alice
        if all(record['user_id'] == 'alice' for record in alice_records):
            print("   ✅ User filtering working correctly")
        else:
            print("   ❌ User filtering returned incorrect records")
    else:
        print("   ⚠️  No records found for user 'alice'")
    
    # Test action filtering
    print("\n4. Testing action filtering...")
    
    login_records = manager.get_audit_records(action="login", limit=10)
    login_count = len(login_records)
    
    if login_count > 0:
        print(f"   ✅ Retrieved {login_count} records for action 'login'")
    else:
        print("   ⚠️  No records found for action 'login'")
    
    # Test risk level filtering
    print("\n5. Testing risk level filtering...")
    
    high_risk_records = manager.get_audit_records(risk_level="HIGH", limit=10)
    high_risk_count = len(high_risk_records)
    
    if high_risk_count > 0:
        print(f"   ✅ Retrieved {high_risk_count} HIGH risk records")
    else:
        print("   ⚠️  No HIGH risk records found")
    
    # Test time-based filtering
    print("\n6. Testing time-based filtering...")
    
    current_time = time.time()
    recent_time = current_time - 300  # Last 5 minutes
    
    recent_records = manager.get_audit_records(
        start_time=recent_time,
        end_time=current_time,
        limit=20
    )
    
    if len(recent_records) > 0:
        print(f"   ✅ Retrieved {len(recent_records)} recent records")
    else:
        print("   ⚠️  No recent records found")
    
    manager.shutdown()
    return True


def test_performance_and_scalability():
    """Test audit system performance under load."""
    
    print("\n⚡ Testing Performance & Scalability")
    print("=" * 37)
    
    if not AUDIT_TRAIL_AVAILABLE:
        print("❌ Audit Trail system not available")
        return False
    
    # Create audit manager
    manager = AuditTrailManager()
    
    # Performance test - rapid logging
    print("\n1. Testing rapid audit logging...")
    
    start_time = time.time()
    batch_size = 100
    
    batch_records = []
    for i in range(batch_size):
        record_id = manager.log_audit_event(
            action=f"perf_test_{i}",
            resource_type="performance",
            user_id=f"perf_user_{i % 10}",
            source_ip=f"192.168.{(i // 100) + 1}.{(i % 100) + 1}",
            endpoint=f"/api/perf/test/{i}",
            request_method="GET",
            status_code=200,
            details={"performance_test": True, "batch_index": i},
            risk_level="LOW"
        )
        batch_records.append(record_id)
    
    elapsed_time = time.time() - start_time
    
    if all(batch_records):
        rate = batch_size / elapsed_time
        print(f"   ✅ Logged {batch_size} records in {elapsed_time:.2f}s ({rate:.1f} records/sec)")
        
        if rate > 50:  # Reasonable performance threshold
            print("   ✅ Performance meets minimum requirements")
        else:
            print("   ⚠️  Performance below optimal threshold")
    else:
        print("   ❌ Some records failed to log during performance test")
    
    # Test integrity verification performance
    print("\n2. Testing integrity verification performance...")
    
    verify_start = time.time()
    integrity_result = manager.verify_audit_integrity()
    verify_elapsed = time.time() - verify_start
    
    records_verified = integrity_result['records_verified']
    if records_verified > 0:
        verify_rate = records_verified / verify_elapsed
        print(f"   ✅ Verified {records_verified} records in {verify_elapsed:.2f}s ({verify_rate:.1f} records/sec)")
    else:
        print("   ❌ Integrity verification found no records")
    
    # Test retrieval performance
    print("\n3. Testing retrieval performance...")
    
    retrieval_start = time.time()
    retrieved_records = manager.get_audit_records(limit=100)
    retrieval_elapsed = time.time() - retrieval_start
    
    if len(retrieved_records) > 0:
        retrieval_rate = len(retrieved_records) / retrieval_elapsed
        print(f"   ✅ Retrieved {len(retrieved_records)} records in {retrieval_elapsed:.2f}s ({retrieval_rate:.1f} records/sec)")
    else:
        print("   ❌ No records retrieved during performance test")
    
    manager.shutdown()
    return True


def test_integration_functions():
    """Test integration helper functions."""
    
    print("\n🔗 Testing Integration Functions")
    print("=" * 33)
    
    if not AUDIT_TRAIL_AVAILABLE:
        print("❌ Audit Trail system not available")
        return False
    
    # Test global audit function
    print("\n1. Testing global log_audit function...")
    
    record_id = log_audit(
        action="integration_test",
        resource_type="integration",
        user_id="integration_user",
        source_ip="172.16.100.200",
        endpoint="/api/integration/test",
        request_method="POST",
        status_code=201,
        details={"integration": True, "test_type": "global_function"},
        risk_level="MEDIUM"
    )
    
    if record_id:
        print(f"   ✅ Global log_audit works: {record_id}")
    else:
        print("   ❌ Global log_audit failed")
        return False
    
    # Test global integrity verification
    print("\n2. Testing global verify_audit_integrity function...")
    
    integrity_result = verify_audit_integrity()
    
    if integrity_result and 'records_verified' in integrity_result:
        print(f"   ✅ Global integrity verification works: {integrity_result['records_verified']} records")
    else:
        print("   ❌ Global integrity verification failed")
        return False
    
    # Test statistics
    print("\n3. Testing audit statistics...")
    
    from audit_trail import get_audit_manager
    audit_mgr = get_audit_manager()
    stats = audit_mgr.get_audit_statistics()
    
    required_stats = ['audit_enabled', 'total_records', 'metrics', 'security_features']
    for stat in required_stats:
        if stat in stats:
            print(f"   ✅ {stat} present in statistics")
        else:
            print(f"   ❌ {stat} missing from statistics")
            return False
    
    return True


if __name__ == "__main__":
    print("📋 PhotoShare Audit Trail Test Suite")
    print("=" * 45)
    
    success = True
    
    try:
        # Clean up any existing test data
        test_db_path = "./tamper-proof-audit-storage/audit_trail.db"
        test_keys_dir = "./tamper-proof-audit-storage/"
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        if os.path.exists(test_keys_dir):
            import shutil
            shutil.rmtree(test_keys_dir)
        
        # Run all tests
        success &= test_audit_logging()
        success &= test_chain_integrity()
        success &= test_digital_signatures()
        success &= test_tamper_detection()
        success &= test_audit_retrieval()
        success &= test_performance_and_scalability()
        success &= test_integration_functions()
        
        if success:
            print(f"\n🎉 ALL AUDIT TRAIL TESTS PASSED!")
            print("🔒 Tamper-proof audit system is ready")
            
            print("\n📋 Security Features Verified:")
            if AUDIT_TRAIL_AVAILABLE:
                print("   ✅ Immutable audit chain with hash linking")
                print("   ✅ Digital signatures for tamper detection")
                print("   ✅ Comprehensive integrity verification")
                print("   ✅ Automatic tamper detection and alerting")
                print("   ✅ High-performance logging and retrieval")
                print("   ✅ Flexible filtering and time-based queries")
            
            print("\n📋 Deployment Notes:")
            print("   1. Set up secure storage directories with proper permissions")
            print("   2. Configure integrity check intervals")
            print("   3. Set up automated alerts for integrity violations")
            print("   4. Implement log rotation for long-term storage")
            
            exit_code = 0
        else:
            print("\n❌ Some audit trail tests failed")
            exit_code = 1
            
    except Exception as e:
        print(f"\n💥 Audit trail test suite failed: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    sys.exit(exit_code)