#!/usr/bin/env python3
"""
Simple RBAC Test
================

Test RBAC with existing users and JWT tokens
"""
import requests
import jwt
import io
from PIL import Image
from datetime import datetime, timezone, timedelta

def create_test_image():
    img = Image.new('RGB', (100, 100), 'blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

def create_jwt_for_existing_user():
    """Create JWT for an existing user"""
    # Use the user we just created (from the successful registration above)
    payload = {
        "sub": "bfbe9a2e-26e5-4472-8e54-18b2d94e1a7d",  # Real UUID from registration
        "user_id": "3",  # User ID from registration response
        "email": "test-db-fix@example.com",
        "aud": "photoshare-app", 
        "iss": "photoshare-auth",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    secret_key = "your-very-secure-jwt-secret-key-minimum-256-bits"
    return jwt.encode(payload, secret_key, algorithm="HS256")

def test_rbac_simple():
    print("🔐 Simple RBAC Test - Using Existing User")
    print("=" * 50)
    
    # Create JWT token
    token = create_jwt_for_existing_user()
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"🎫 JWT Token: {token[:50]}...")
    
    # Test 1: Get user info from auth service
    print("\n👤 Test 1: Auth Service User Info")
    response = requests.get("http://localhost:8001/api/auth/users/bfbe9a2e-26e5-4472-8e54-18b2d94e1a7d")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        user_data = response.json()
        print(f"   ✅ User: {user_data.get('email')}")
        print(f"   🎭 Roles: {user_data.get('roles', [])}")
        print(f"   🔑 Permissions: {user_data.get('permissions', [])}")
    else:
        print(f"   Response: {response.text}")
    
    # Test 2: Test photo upload with RBAC
    print("\n📸 Test 2: Photo Upload with Permissions")
    
    image_data = create_test_image()
    files = {'file': ('rbac-test.jpg', image_data, 'image/jpeg')}
    data = {
        'title': 'RBAC Test Photo',
        'description': 'Testing RBAC permissions', 
        'is_public': 'true'
    }
    
    response = requests.post(
        "http://localhost:8000/api/photos/upload",
        files=files,
        data=data,
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Test 3: Photo listing
    print("\n📋 Test 3: User Photos")  
    response = requests.get("http://localhost:8000/api/photos/", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")
    
    # Test 4: Public photos
    print("\n🌍 Test 4: Public Photos")
    response = requests.get("http://localhost:8000/api/photos/public")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Public photos: {data.get('total', 0)} found")
    else:
        print(f"   Response: {response.text}")

if __name__ == "__main__":
    test_rbac_simple()