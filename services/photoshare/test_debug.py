"""Debug test to isolate the hanging issue."""
import pytest
from fastapi.testclient import TestClient

def test_basic_health_check():
    """Test basic health endpoint without database."""
    from main import PhotoShareDatabaseService
    app = PhotoShareDatabaseService().app
    client = TestClient(app)
    
    response = client.get("/health")
    print(f"Health check response: {response.status_code}")
    assert response.status_code == 200

if __name__ == "__main__":
    test_basic_health_check()