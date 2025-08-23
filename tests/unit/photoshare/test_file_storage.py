#!/usr/bin/env python3
"""
Unit tests for file storage functionality.
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from services.photoshare.file_storage import (
    StorageManager, FileMetadata, FileValidationResult, 
    validate_image_file, generate_filename, get_file_hash
)


class TestFileMetadata:
    """Test File Metadata class."""
    
    def test_metadata_creation(self):
        """Test file metadata creation."""
        metadata = FileMetadata(
            filename="test.jpg",
            content_type="image/jpeg",
            size=1024,
            hash="abc123",
            width=800,
            height=600
        )
        
        assert metadata.filename == "test.jpg"
        assert metadata.content_type == "image/jpeg"
        assert metadata.size == 1024
        assert metadata.hash == "abc123"
        assert metadata.width == 800
        assert metadata.height == 600
    
    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        metadata = FileMetadata(
            filename="test.jpg",
            content_type="image/jpeg",
            size=1024
        )
        
        metadata_dict = metadata.to_dict()
        
        assert metadata_dict["filename"] == "test.jpg"
        assert metadata_dict["content_type"] == "image/jpeg"
        assert metadata_dict["size"] == 1024


class TestFileValidationResult:
    """Test File Validation Result class."""
    
    def test_validation_result_valid(self):
        """Test valid file validation result."""
        result = FileValidationResult(
            is_valid=True,
            content_type="image/jpeg",
            file_size=1024
        )
        
        assert result.is_valid is True
        assert result.content_type == "image/jpeg"
        assert result.file_size == 1024
        assert result.errors == []
    
    def test_validation_result_invalid(self):
        """Test invalid file validation result."""
        result = FileValidationResult(
            is_valid=False,
            errors=["File too large", "Invalid format"]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "File too large" in result.errors


class TestFileValidation:
    """Test file validation functions."""
    
    def test_validate_image_file_valid_jpeg(self):
        """Test valid JPEG validation."""
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
            # Create minimal JPEG header
            tmp_file.write(b'\xff\xd8\xff\xe0\x00\x10JFIF')
            tmp_file.flush()
            
            result = validate_image_file(tmp_file.name, "image/jpeg", 1024)
            
            assert result.is_valid is True
            assert result.content_type == "image/jpeg"
    
    def test_validate_image_file_invalid_size(self):
        """Test file size validation."""
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
            tmp_file.write(b'x' * (10 * 1024 * 1024 + 1))  # > 10MB
            tmp_file.flush()
            
            result = validate_image_file(tmp_file.name, "image/jpeg", tmp_file.tell())
            
            assert result.is_valid is False
            assert "File size exceeds limit" in result.errors[0]
    
    def test_validate_image_file_invalid_extension(self):
        """Test file extension validation."""
        with tempfile.NamedTemporaryFile(suffix='.exe') as tmp_file:
            tmp_file.write(b'test data')
            tmp_file.flush()
            
            result = validate_image_file(tmp_file.name, "application/exe", 100)
            
            assert result.is_valid is False
            assert any("not allowed" in error for error in result.errors)


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_generate_filename(self):
        """Test filename generation."""
        filename = generate_filename("test.jpg", "user123")
        
        assert filename.endswith("_test.jpg")
        assert len(filename.split('_')[0]) == 8  # UUID prefix length
    
    def test_generate_filename_sanitization(self):
        """Test filename sanitization."""
        filename = generate_filename("test file with spaces.jpg", "user123")
        
        assert " " not in filename
        assert filename.endswith("_test_file_with_spaces.jpg")
    
    def test_get_file_hash(self):
        """Test file hash generation."""
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(b"test content")
            tmp_file.flush()
            
            file_hash = get_file_hash(tmp_file.name)
            
            assert isinstance(file_hash, str)
            assert len(file_hash) == 64  # SHA256 hex length


class TestStorageManager:
    """Test Storage Manager functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        """Create storage manager instance."""
        with patch.dict('os.environ', {
            'STORAGE_PATH': '/tmp/test_storage',
            'MAX_FILE_SIZE': '10485760'  # 10MB
        }):
            return StorageManager()
    
    def test_storage_manager_initialization(self, storage_manager):
        """Test storage manager initialization."""
        assert storage_manager.storage_path == '/tmp/test_storage'
        assert storage_manager.max_file_size == 10485760
        assert storage_manager.allowed_extensions == {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    @pytest.mark.asyncio
    async def test_save_file_success(self, storage_manager):
        """Test successful file save."""
        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.size = 1024
        mock_file.read = AsyncMock(return_value=b"test image data")
        
        with patch('os.makedirs'):
            with patch('aiofiles.open', create=True) as mock_open:
                mock_file_handle = AsyncMock()
                mock_file_handle.write = AsyncMock()
                mock_open.return_value.__aenter__ = AsyncMock(return_value=mock_file_handle)
                mock_open.return_value.__aexit__ = AsyncMock(return_value=None)
                
                with patch('services.photoshare.file_storage.validate_image_file') as mock_validate:
                    mock_validate.return_value = FileValidationResult(
                        is_valid=True,
                        content_type="image/jpeg",
                        file_size=1024
                    )
                    
                    with patch('services.photoshare.file_storage.get_file_hash', return_value='abc123'):
                        result = await storage_manager.save_file(mock_file, "user123")
                        
                        assert result["success"] is True
                        assert "filename" in result
                        assert "file_path" in result
                        assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_save_file_validation_failure(self, storage_manager):
        """Test file save with validation failure."""
        mock_file = Mock()
        mock_file.filename = "test.exe"
        mock_file.content_type = "application/exe"
        mock_file.size = 1024
        
        with patch('services.photoshare.file_storage.validate_image_file') as mock_validate:
            mock_validate.return_value = FileValidationResult(
                is_valid=False,
                errors=["Invalid file type"]
            )
            
            result = await storage_manager.save_file(mock_file, "user123")
            
            assert result["success"] is False
            assert "Invalid file type" in result["error"]
    
    @pytest.mark.asyncio
    async def test_delete_file_success(self, storage_manager):
        """Test successful file deletion."""
        with patch('os.path.exists', return_value=True):
            with patch('os.remove') as mock_remove:
                result = await storage_manager.delete_file("/tmp/test_storage/test.jpg")
                
                assert result is True
                mock_remove.assert_called_once_with("/tmp/test_storage/test.jpg")
    
    @pytest.mark.asyncio
    async def test_delete_file_not_exists(self, storage_manager):
        """Test file deletion when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            result = await storage_manager.delete_file("/tmp/test_storage/nonexistent.jpg")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_file_info_success(self, storage_manager):
        """Test getting file information."""
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=1024):
                with patch('os.path.getctime', return_value=1234567890):
                    info = await storage_manager.get_file_info("/tmp/test_storage/test.jpg")
                    
                    assert info["exists"] is True
                    assert info["size"] == 1024
                    assert info["created"] == datetime.fromtimestamp(1234567890)
    
    @pytest.mark.asyncio
    async def test_get_file_info_not_exists(self, storage_manager):
        """Test getting file information for non-existent file."""
        with patch('os.path.exists', return_value=False):
            info = await storage_manager.get_file_info("/tmp/test_storage/nonexistent.jpg")
            
            assert info["exists"] is False
            assert info["size"] is None
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, storage_manager):
        """Test cleanup of old files."""
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                ('/tmp/test_storage', [], ['old_file.jpg', 'new_file.jpg'])
            ]
            
            with patch('os.path.getmtime') as mock_getmtime:
                with patch('os.remove') as mock_remove:
                    # Mock old file (30+ days old)
                    mock_getmtime.side_effect = lambda f: 1234567890 if 'old' in f else 1734567890
                    
                    cleaned = await storage_manager.cleanup_old_files(days=30)
                    
                    assert cleaned == 1
                    mock_remove.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_storage_stats(self, storage_manager):
        """Test getting storage statistics."""
        with patch('os.walk') as mock_walk:
            mock_walk.return_value = [
                ('/tmp/test_storage', [], ['file1.jpg', 'file2.png'])
            ]
            
            with patch('os.path.getsize', return_value=1024):
                stats = await storage_manager.get_storage_stats()
                
                assert stats["total_files"] == 2
                assert stats["total_size"] == 2048
                assert "storage_path" in stats