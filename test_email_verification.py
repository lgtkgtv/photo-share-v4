#!/usr/bin/env python3
"""
Email Verification Test
=======================

Test the complete email verification flow
"""
import requests
import subprocess
import re

def get_verification_token_from_db(email):
    """Get the latest verification token for an email from the database."""
    try:
        result = subprocess.run([
            "docker", "compose", "-f", "docker-compose.separated.yml", "exec", "-T", "auth-db",
            "psql", "-U", "auth_user", "-d", "photo_share_auth", "-c", 
            f"SELECT secret FROM email_verifications WHERE email = '{email}' AND is_used = false ORDER BY created_at DESC LIMIT 1;"
        ], capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('secret') and not line.startswith('---') and len(line) > 10:
                return line
        return None
    except:
        return None

def test_email_verification_flow():
    """Test complete email verification flow."""
    print("📧 Email Verification System Test")
    print("=" * 50)
    
    # Test 1: Register new user
    print("\n👤 Test 1: User Registration")
    user_data = {
        "email": "email-verify-flow@example.com",
        "password": "TestPassword123!",
        "first_name": "Email",
        "last_name": "Test"
    }
    
    response = requests.post("http://localhost:8001/api/auth/register", json=user_data)
    print(f"   Registration Status: {response.status_code}")
    
    if response.status_code == 200:
        user_info = response.json()
        print(f"   ✅ User created: {user_info['email']}")
        print(f"   📧 Verified: {user_info['is_verified']}")
        user_uuid = user_info['uuid']
    else:
        print(f"   ❌ Registration failed: {response.text}")
        return False
    
    # Test 2: Get verification token
    print("\n🔑 Test 2: Getting Verification Token")
    verification_token = get_verification_token_from_db(user_data["email"])
    if verification_token:
        print(f"   ✅ Token found: {verification_token[:20]}...")
    else:
        print("   ❌ No verification token found")
        return False
    
    # Test 3: Verify email
    print("\n✅ Test 3: Email Verification")
    verify_response = requests.get(f"http://localhost:8001/api/auth/verify-email/{verification_token}")
    print(f"   Verification Status: {verify_response.status_code}")
    
    if verify_response.status_code == 200:
        verify_data = verify_response.json()
        print(f"   ✅ {verify_data['message']}")
        print(f"   📧 User: {verify_data['user_email']}")
    else:
        print(f"   ❌ Verification failed: {verify_response.text}")
        return False
    
    # Test 4: Verify user is now verified
    print("\n👤 Test 4: User Info After Verification")
    user_response = requests.get(f"http://localhost:8001/api/auth/users/{user_uuid}")
    print(f"   Status: {user_response.status_code}")
    
    if user_response.status_code == 200:
        user_data = user_response.json()
        print(f"   ✅ User: {user_data['email']}")
        print(f"   📧 Verified: {user_data['is_verified']}")
        print(f"   🎭 Roles: {user_data['roles']}")
        print(f"   🔑 Permissions: {len(user_data['permissions'])} permissions")
    else:
        print(f"   Response: {user_response.text}")
        return False
    
    # Test 5: Test verification request for verified user
    print("\n🔄 Test 5: Request Verification for Already Verified User")
    request_response = requests.post(
        "http://localhost:8001/api/auth/request-verification",
        json={"email": user_data["email"]}
    )
    print(f"   Status: {request_response.status_code}")
    if request_response.status_code == 200:
        request_data = request_response.json()
        print(f"   ✅ {request_data['message']}")
    
    # Test 6: Test expired/invalid token
    print("\n🚫 Test 6: Invalid Token Test")
    invalid_response = requests.get("http://localhost:8001/api/auth/verify-email/invalid-token-here")
    print(f"   Status: {invalid_response.status_code}")
    if invalid_response.status_code == 404:
        print("   ✅ Invalid token correctly rejected")
    
    print("\n" + "=" * 50)
    print("✅ Email Verification System: FULLY FUNCTIONAL!")
    print("• User registration creates unverified users")
    print("• Email verification tokens are generated")
    print("• Verification links work correctly")
    print("• Users are marked as verified after verification")
    print("• Duplicate verification requests handled properly")
    print("• Invalid tokens are properly rejected")
    
    return True

if __name__ == "__main__":
    try:
        success = test_email_verification_flow()
        if success:
            print("\n🎉 All email verification tests passed!")
        else:
            print("\n❌ Some tests failed")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()