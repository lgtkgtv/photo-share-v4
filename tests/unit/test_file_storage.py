"""
Unit tests for file storage components.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
import tempfile
import os

from file_storage import (
    FileStorageService, LocalFileStorage, PlatformFileStorage,
    validate_file_type, calculate_file_hash
)


class TestFileStorageService:
    """Test FileStorageService class."""

    @pytest.mark.unit
    def test_init(self):
        """Test file storage service initialization."""
        storage = FileStorageService()
        
        assert storage is not None
        assert hasattr(storage, 'local_storage')
        assert hasattr(storage, 'platform_storage')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_file(self):
        """Test file storage."""
        storage = FileStorageService()
        
        # Mock file data
        file_data = b"fake image data"
        filename = "test.jpg"
        content_type = "image/jpeg"
        
        with patch.object(storage.local_storage, 'store_file', return_value={
            'storage_path': '/tmp/test.jpg',
            'file_size': len(file_data),
            'content_type': content_type
        }):
            result = await storage.store_file(file_data, filename, content_type)
            
            assert result['storage_path'] == '/tmp/test.jpg'
            assert result['file_size'] == len(file_data)
            assert result['content_type'] == content_type

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_file(self):
        """Test file retrieval."""
        storage = FileStorageService()
        
        storage_path = "/tmp/test.jpg"
        expected_data = b"fake image data"
        
        with patch.object(storage.local_storage, 'retrieve_file', return_value=expected_data):
            result = await storage.retrieve_file(storage_path)
            
            assert result == expected_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_file(self):
        """Test file deletion."""
        storage = FileStorageService()
        
        storage_path = "/tmp/test.jpg"
        
        with patch.object(storage.local_storage, 'delete_file', return_value=True):
            result = await storage.delete_file(storage_path)
            
            assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        storage = FileStorageService()
        
        with patch.object(storage.local_storage, 'health_check', return_value=True), \
             patch.object(storage.platform_storage, 'health_check', return_value=True):
            
            result = await storage.health_check()
            
            assert result['local_storage'] is True
            assert result['platform_storage'] is True

    @pytest.mark.unit
    def test_get_file_url(self):
        """Test getting file URL."""
        storage = FileStorageService()
        
        storage_path = "/tmp/test.jpg"
        expected_url = "http://localhost/files/test.jpg"
        
        with patch.object(storage.local_storage, 'get_file_url', return_value=expected_url):
            result = storage.get_file_url(storage_path)
            
            assert result == expected_url


class TestLocalFileStorage:
    """Test LocalFileStorage class."""

    @pytest.mark.unit
    def test_init(self):
        """Test local file storage initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorage(base_path=temp_dir)
            
            assert storage is not None
            assert storage.base_path == temp_dir

    @pytest.mark.unit
    def test_store_file(self):
        """Test local file storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorage(base_path=temp_dir)
            
            file_data = b"test file content"
            filename = "test.txt"
            content_type = "text/plain"
            
            result = storage.store_file(file_data, filename, content_type)
            
            assert 'storage_path' in result
            assert result['file_size'] == len(file_data)
            assert result['content_type'] == content_type
            
            # Verify file was actually created
            assert os.path.exists(result['storage_path'])

    @pytest.mark.unit
    def test_retrieve_file(self):
        """Test local file retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorage(base_path=temp_dir)
            
            # First store a file
            file_data = b"test file content"
            store_result = storage.store_file(file_data, "test.txt", "text/plain")
            
            # Then retrieve it
            retrieved_data = storage.retrieve_file(store_result['storage_path'])
            
            assert retrieved_data == file_data

    @pytest.mark.unit
    def test_delete_file(self):
        """Test local file deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorage(base_path=temp_dir)
            
            # Store then delete
            file_data = b"test file content"
            store_result = storage.store_file(file_data, "test.txt", "text/plain")
            
            success = storage.delete_file(store_result['storage_path'])
            
            assert success is True
            assert not os.path.exists(store_result['storage_path'])

    @pytest.mark.unit
    def test_health_check(self):
        """Test local storage health check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorage(base_path=temp_dir)
            
            is_healthy = storage.health_check()
            
            assert is_healthy is True

    @pytest.mark.unit
    def test_get_file_url(self):
        """Test getting file URL from local storage."""
        storage = LocalFileStorage()
        
        storage_path = "/uploads/photos/test.jpg"
        url = storage.get_file_url(storage_path)
        
        assert url.startswith("http://")
        assert "test.jpg" in url


class TestPlatformFileStorage:
    """Test PlatformFileStorage class."""

    @pytest.mark.unit
    def test_init(self):
        """Test platform file storage initialization."""
        storage = PlatformFileStorage()
        
        assert storage is not None
        assert hasattr(storage, 'platform_config')

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_file(self):
        """Test platform file storage."""
        storage = PlatformFileStorage()
        
        file_data = b"test file content"
        filename = "test.txt"
        content_type = "text/plain"
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                'storage_path': 'platform://test.txt',
                'file_size': len(file_data),
                'content_type': content_type
            })
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await storage.store_file(file_data, filename, content_type)
            
            assert result['storage_path'] == 'platform://test.txt'
            assert result['file_size'] == len(file_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_file(self):
        """Test platform file retrieval."""
        storage = PlatformFileStorage()
        
        storage_path = "platform://test.txt"
        expected_data = b"test file content"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=expected_data)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await storage.retrieve_file(storage_path)
            
            assert result == expected_data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_file(self):
        """Test platform file deletion."""
        storage = PlatformFileStorage()
        
        storage_path = "platform://test.txt"
        
        with patch('aiohttp.ClientSession.delete') as mock_delete:
            mock_response = Mock()
            mock_response.status = 200
            mock_delete.return_value.__aenter__.return_value = mock_response
            
            result = await storage.delete_file(storage_path)
            
            assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test platform storage health check."""
        storage = PlatformFileStorage()
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await storage.health_check()
            
            assert result is True


class TestFileValidationFunctions:
    """Test file validation utility functions."""

    @pytest.mark.unit
    def test_validate_file_type_valid(self):
        """Test valid file type validation."""
        is_valid = validate_file_type("image/jpeg")
        assert is_valid is True
        
        is_valid = validate_file_type("image/png")
        assert is_valid is True

    @pytest.mark.unit
    def test_validate_file_type_invalid(self):
        """Test invalid file type validation."""
        is_valid = validate_file_type("application/x-executable")
        assert is_valid is False
        
        is_valid = validate_file_type("text/html")
        assert is_valid is False

    @pytest.mark.unit
    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        file_data = b"test file content"
        file_hash = calculate_file_hash(file_data)
        
        assert isinstance(file_hash, str)
        assert len(file_hash) > 0
        
        # Same content should produce same hash
        file_hash2 = calculate_file_hash(file_data)
        assert file_hash == file_hash2
        
        # Different content should produce different hash
        different_data = b"different content"
        different_hash = calculate_file_hash(different_data)
        assert file_hash != different_hash