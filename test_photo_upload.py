#!/usr/bin/env python3
"""
Test photo upload functionality
"""
import requests
import io
from PIL import Image

def create_test_image():
    """Create a simple test image"""
    # Create a 100x100 red image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def test_photo_upload():
    """Test photo upload with a valid JWT token"""
    
    print("Testing photo upload...")
    
    # Create a JWT token for testing (same as our earlier test)
    import jwt
    from datetime import datetime, timezone, timedelta
    
    payload = {
        "sub": "test-user-uuid-123",
        "user_id": "1",
        "email": "test@example.com",
        "aud": "photoshare-app",
        "iss": "photoshare-auth",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    
    secret_key = "your-very-secure-jwt-secret-key-minimum-256-bits"
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    print(f"Using JWT token: {token[:50]}...")
    
    # Test upload with auth
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create test image
    image_data = create_test_image()
    
    files = {'file': ('test.jpg', image_data, 'image/jpeg')}
    data = {
        'title': 'Test Photo',
        'description': 'A test photo upload',
        'is_public': 'true'
    }
    
    response = requests.post(
        "http://localhost:8000/api/photos/upload",
        files=files,
        data=data,
        headers=headers
    )
    
    print(f"\nUpload with auth - Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test public photos endpoint (should work without auth)
    response = requests.get("http://localhost:8000/api/photos/public")
    print(f"\nPublic photos - Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test user photos endpoint (with auth)
    response = requests.get("http://localhost:8000/api/photos/", headers=headers)
    print(f"\nUser photos - Status: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_photo_upload()