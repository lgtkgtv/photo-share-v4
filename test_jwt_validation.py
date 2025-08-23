#!/usr/bin/env python3
"""
Test JWT validation end-to-end
"""
import jwt
import requests
from datetime import datetime, timezone, timedelta

# Create a JWT token manually for testing
def create_test_jwt():
    payload = {
        "sub": "test-user-uuid-123",
        "user_id": "1",
        "email": "test@example.com",
        "aud": "photoshare-app",
        "iss": "photoshare-auth",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    # Use the same secret key from the environment
    secret_key = "your-very-secure-jwt-secret-key-minimum-256-bits"
    
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token

def test_app_service_auth():
    """Test the app service JWT validation"""
    token = create_test_jwt()
    print(f"Created test token: {token[:50]}...")
    
    # Test app service protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("http://localhost:8000/api/users/me", headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    return response.status_code == 200

if __name__ == "__main__":
    success = test_app_service_auth()
    print(f"JWT validation test: {'PASSED' if success else 'FAILED'}")