#!/usr/bin/env python3
"""
Test login functionality
"""
import requests

# Login test
def test_login():
    url = "http://localhost:8001/api/auth/login"
    data = {
        "username": "testuser@example.com",
        "password": "TestPass123!"
    }
    
    response = requests.post(url, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response

if __name__ == "__main__":
    test_login()