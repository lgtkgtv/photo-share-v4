"""
Simple integration test to verify the test framework works.
"""
import pytest
import requests
import time
from unittest.mock import patch, MagicMock


@pytest.mark.integration
def test_simple_http_request():
    """Test that we can make basic HTTP requests."""
    # This is a very simple test that doesn't require the full app
    # Just to verify the test framework basics are working
    
    # Mock the requests to avoid external dependencies
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        response = requests.get("http://example.com")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.integration
def test_environment_variables():
    """Test that environment variables are set correctly."""
    import os
    
    assert os.environ.get("ENVIRONMENT") == "test"
    assert os.environ.get("JWT_SECRET_KEY") is not None
    assert len(os.environ.get("JWT_SECRET_KEY")) > 32


@pytest.mark.integration 
def test_basic_imports():
    """Test that we can import the main modules."""
    from main import PhotoShareDatabaseService
    from database import Base, User, Photo
    
    # Test that we can create basic instances
    assert PhotoShareDatabaseService is not None
    assert Base is not None
    assert User is not None
    assert Photo is not None


@pytest.mark.integration
def test_async_function():
    """Test that async functions work in the test environment."""
    import asyncio
    
    async def async_test():
        await asyncio.sleep(0.001)  # Very short sleep
        return "success"
    
    result = asyncio.run(async_test())
    assert result == "success"