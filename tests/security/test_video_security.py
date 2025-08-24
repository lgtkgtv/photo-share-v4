#!/usr/bin/env python3
"""
Security Tests for Video Processing
===================================

Tests security aspects of video processing including:
- Video file security validation
- Malicious content detection
- Codec allowlisting
- File size and duration limits
- Container format validation
- Content scanning
"""

import pytest
import tempfile
import os
import hashlib
from unittest.mock import Mock, patch, AsyncMock, mock_open
from typing import Dict, Any

# Import video security components
try:
    from services.photoshare.video_processing.video_security import VideoSecurityValidator
    VIDEO_SECURITY_AVAILABLE = True
except ImportError:
    VIDEO_SECURITY_AVAILABLE = False


@pytest.fixture
def video_security_validator():
    """Create VideoSecurityValidator instance for testing."""
    if not VIDEO_SECURITY_AVAILABLE:
        pytest.skip("Video security validator not available")
    return VideoSecurityValidator()


@pytest.fixture
def safe_video_metadata():
    """Sample safe video metadata."""
    return {
        'file_size': 10 * 1024 * 1024,  # 10MB
        'duration': 60,  # 1 minute
        'width': 1920,
        'height': 1080,
        'video_codec': 'h264',
        'audio_codec': 'aac',
        'bitrate': 2000,
        'format_name': 'mp4'
    }


@pytest.fixture
def malicious_video_metadata():
    """Sample metadata for potentially malicious video."""
    return {
        'file_size': 600 * 1024 * 1024,  # 600MB (over limit)
        'duration': 7200,  # 2 hours (over limit)
        'width': 8192,  # Very high resolution
        'height': 4608,
        'video_codec': 'rv40',  # Blocked codec
        'audio_codec': 'cook',  # Blocked codec
        'bitrate': 60000,  # Over limit
        'format_name': 'unknown_format'
    }


class TestVideoSecurityConfiguration:
    """Test video security configuration and limits."""
    
    def test_default_security_limits(self, video_security_validator):
        """Test default security configuration."""
        config = video_security_validator.get_security_config()
        
        assert config['max_video_size_mb'] > 0
        assert config['max_duration_minutes'] > 0
        assert config['max_bitrate_kbps'] > 0
        assert len(config['allowed_video_codecs']) > 0
        assert len(config['allowed_audio_codecs']) > 0
        assert len(config['blocked_video_codecs']) > 0
    
    def test_update_security_limits(self, video_security_validator):
        """Test updating security limits."""
        original_size = video_security_validator.max_video_size
        
        # Update limits
        video_security_validator.update_security_limits(
            max_size_mb=200,
            max_duration_minutes=90,
            max_bitrate_kbps=10000
        )
        
        # Verify updates
        assert video_security_validator.max_video_size == 200 * 1024 * 1024
        assert video_security_validator.max_duration == 90 * 60
        assert video_security_validator.max_bitrate == 10000
    
    def test_allowed_codecs_configuration(self, video_security_validator):
        """Test codec allowlist configuration."""
        # Check that common safe codecs are allowed
        assert 'h264' in video_security_validator.allowed_codecs['video']
        assert 'h265' in video_security_validator.allowed_codecs['video']
        assert 'vp8' in video_security_validator.allowed_codecs['video']
        assert 'vp9' in video_security_validator.allowed_codecs['video']
        assert 'av1' in video_security_validator.allowed_codecs['video']
        
        assert 'aac' in video_security_validator.allowed_codecs['audio']
        assert 'mp3' in video_security_validator.allowed_codecs['audio']
        assert 'opus' in video_security_validator.allowed_codecs['audio']
    
    def test_blocked_codecs_configuration(self, video_security_validator):
        """Test codec blocklist configuration."""
        # Check that known dangerous codecs are blocked
        assert 'rv40' in video_security_validator.blocked_codecs['video']
        assert 'indeo5' in video_security_validator.blocked_codecs['video']
        assert 'cook' in video_security_validator.blocked_codecs['audio']


class TestVideoValidation:
    """Test video security validation logic."""
    
    @pytest.mark.asyncio
    async def test_valid_video_passes_validation(self, video_security_validator, safe_video_metadata):
        """Test that valid video passes security validation."""
        with patch.object(video_security_validator, '_validate_file_header', return_value=True):
            with patch.object(video_security_validator, '_scan_video_content', return_value=False):
                is_safe, message = await video_security_validator.validate_video_security(
                    '/fake/path/video.mp4', safe_video_metadata
                )
        
        assert is_safe is True
        assert 'validation passed' in message.lower()
    
    @pytest.mark.asyncio
    async def test_oversized_video_rejected(self, video_security_validator, safe_video_metadata):
        """Test that oversized video is rejected."""
        oversized_metadata = safe_video_metadata.copy()
        oversized_metadata['file_size'] = 1024 * 1024 * 1024  # 1GB
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', oversized_metadata
        )
        
        assert is_safe is False
        assert 'too large' in message.lower()
    
    @pytest.mark.asyncio
    async def test_too_long_video_rejected(self, video_security_validator, safe_video_metadata):
        """Test that video exceeding duration limit is rejected."""
        long_metadata = safe_video_metadata.copy()
        long_metadata['duration'] = 7200  # 2 hours
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', long_metadata
        )
        
        assert is_safe is False
        assert 'too long' in message.lower()
    
    @pytest.mark.asyncio
    async def test_too_short_video_rejected(self, video_security_validator, safe_video_metadata):
        """Test that video shorter than minimum duration is rejected."""
        short_metadata = safe_video_metadata.copy()
        short_metadata['duration'] = 0.05  # 50ms
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', short_metadata
        )
        
        assert is_safe is False
        assert 'too short' in message.lower()
    
    @pytest.mark.asyncio
    async def test_high_resolution_video_rejected(self, video_security_validator, safe_video_metadata):
        """Test that video with excessive resolution is rejected."""
        hires_metadata = safe_video_metadata.copy()
        hires_metadata['width'] = 10000  # Excessive width
        hires_metadata['height'] = 8000  # Excessive height
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', hires_metadata
        )
        
        assert is_safe is False
        assert 'resolution too high' in message.lower()
    
    @pytest.mark.asyncio
    async def test_blocked_video_codec_rejected(self, video_security_validator, safe_video_metadata):
        """Test that video with blocked codec is rejected."""
        blocked_metadata = safe_video_metadata.copy()
        blocked_metadata['video_codec'] = 'rv40'  # Blocked codec
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', blocked_metadata
        )
        
        assert is_safe is False
        assert 'blocked' in message.lower()
        assert 'rv40' in message.lower()
    
    @pytest.mark.asyncio
    async def test_blocked_audio_codec_rejected(self, video_security_validator, safe_video_metadata):
        """Test that video with blocked audio codec is rejected."""
        blocked_metadata = safe_video_metadata.copy()
        blocked_metadata['audio_codec'] = 'cook'  # Blocked codec
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', blocked_metadata
        )
        
        assert is_safe is False
        assert 'blocked' in message.lower()
        assert 'cook' in message.lower()
    
    @pytest.mark.asyncio
    async def test_unsupported_video_codec_rejected(self, video_security_validator, safe_video_metadata):
        """Test that video with unsupported codec is rejected."""
        unsupported_metadata = safe_video_metadata.copy()
        unsupported_metadata['video_codec'] = 'unknown_codec'
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', unsupported_metadata
        )
        
        assert is_safe is False
        assert 'unsupported' in message.lower()
    
    @pytest.mark.asyncio
    async def test_high_bitrate_video_rejected(self, video_security_validator, safe_video_metadata):
        """Test that video with excessive bitrate is rejected."""
        high_bitrate_metadata = safe_video_metadata.copy()
        high_bitrate_metadata['bitrate'] = 100000  # 100Mbps
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', high_bitrate_metadata
        )
        
        assert is_safe is False
        assert 'bitrate too high' in message.lower()
    
    @pytest.mark.asyncio
    async def test_tiny_file_rejected(self, video_security_validator, safe_video_metadata):
        """Test that suspiciously small file is rejected."""
        tiny_metadata = safe_video_metadata.copy()
        tiny_metadata['file_size'] = 100  # 100 bytes
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/path/video.mp4', tiny_metadata
        )
        
        assert is_safe is False
        assert 'too small' in message.lower()


class TestFileHeaderValidation:
    """Test video file header validation."""
    
    @pytest.mark.asyncio
    async def test_valid_mp4_header(self, video_security_validator):
        """Test validation of valid MP4 file header."""
        # Create a valid MP4 header
        mp4_header = b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom' + b'\x00' * 1000
        
        with patch('builtins.open', mock_open(read_data=mp4_header)):
            result = await video_security_validator._validate_file_header('/fake/video.mp4')
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_valid_avi_header(self, video_security_validator):
        """Test validation of valid AVI file header."""
        # Create a valid AVI header
        avi_header = b'RIFF\x00\x00\x00\x00AVI LIST' + b'\x00' * 1000
        
        with patch('builtins.open', mock_open(read_data=avi_header)):
            result = await video_security_validator._validate_file_header('/fake/video.avi')
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_valid_webm_header(self, video_security_validator):
        """Test validation of valid WebM file header."""
        # Create a valid WebM (EBML) header
        webm_header = b'\x1a\x45\xdf\xa3' + b'\x00' * 1000
        
        with patch('builtins.open', mock_open(read_data=webm_header)):
            result = await video_security_validator._validate_file_header('/fake/video.webm')
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_invalid_file_header(self, video_security_validator):
        """Test rejection of invalid file header."""
        # Create an invalid header
        invalid_header = b'INVALID_VIDEO_HEADER' + b'\x00' * 1000
        
        with patch('builtins.open', mock_open(read_data=invalid_header)):
            result = await video_security_validator._validate_file_header('/fake/video.mp4')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_file_header_validation_error(self, video_security_validator):
        """Test file header validation with file read error."""
        with patch('builtins.open', side_effect=IOError("File not found")):
            result = await video_security_validator._validate_file_header('/fake/video.mp4')
        
        assert result is False


class TestContentScanning:
    """Test video content scanning for malicious patterns."""
    
    @pytest.mark.asyncio
    async def test_clean_content_passes(self, video_security_validator):
        """Test that clean video content passes scanning."""
        clean_content = b'\x00\x01\x02\x03' * 10000  # 40KB of clean binary data
        
        with patch('os.path.getsize', return_value=len(clean_content)):
            with patch('builtins.open', mock_open(read_data=clean_content)):
                result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is False  # No malicious content found
    
    @pytest.mark.asyncio
    async def test_php_injection_detected(self, video_security_validator):
        """Test detection of PHP injection attempt."""
        malicious_content = b'clean video data' + b'<?php eval($_GET["cmd"]); ?>' + b'more video data'
        
        # Create a proper mock file that supports chunked reading
        mock_file = Mock()
        mock_file.read.return_value = malicious_content
        mock_file.seek = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        
        with patch('os.path.getsize', return_value=len(malicious_content)):
            with patch('builtins.open', return_value=mock_file):
                result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is True  # Malicious content detected
    
    @pytest.mark.asyncio
    async def test_javascript_injection_detected(self, video_security_validator):
        """Test detection of JavaScript injection attempt."""
        malicious_content = b'video header' + b'<script>alert("xss")</script>' + b'video footer'
        
        mock_file = Mock()
        mock_file.read.return_value = malicious_content
        mock_file.seek = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        
        with patch('os.path.getsize', return_value=len(malicious_content)):
            with patch('builtins.open', return_value=mock_file):
                result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is True  # Malicious content detected
    
    @pytest.mark.asyncio
    async def test_buffer_overflow_pattern_detected(self, video_security_validator):
        """Test detection of buffer overflow patterns."""
        malicious_content = b'video data' + b'A' * 1500 + b'more data'  # Long sequence of 'A's
        
        mock_file = Mock()
        mock_file.read.return_value = malicious_content
        mock_file.seek = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        
        with patch('os.path.getsize', return_value=len(malicious_content)):
            with patch('builtins.open', return_value=mock_file):
                result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is True  # Malicious pattern detected
    
    @pytest.mark.asyncio
    async def test_nop_sled_detected(self, video_security_validator):
        """Test detection of NOP sled patterns."""
        malicious_content = b'video data' + b'\x90' * 150 + b'shellcode'  # NOP sled
        
        mock_file = Mock()
        mock_file.read.return_value = malicious_content
        mock_file.seek = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        
        with patch('os.path.getsize', return_value=len(malicious_content)):
            with patch('builtins.open', return_value=mock_file):
                result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is True  # Malicious pattern detected
    
    @pytest.mark.asyncio
    async def test_suspicious_html_detected(self, video_security_validator):
        """Test detection of suspicious HTML/iframe content."""
        malicious_content = b'normal video' + b'<iframe src="evil.com"></iframe>' + b'more video'
        
        mock_file = Mock()
        mock_file.read.return_value = malicious_content
        mock_file.seek = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        
        with patch('os.path.getsize', return_value=len(malicious_content)):
            with patch('builtins.open', return_value=mock_file):
                result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is True  # Malicious content detected
    
    @pytest.mark.asyncio
    async def test_content_scanning_error_handling(self, video_security_validator):
        """Test content scanning error handling."""
        with patch('os.path.getsize', side_effect=OSError("File access error")):
            result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is True  # Err on the side of caution


class TestContainerFormatValidation:
    """Test video container format validation."""
    
    def test_allowed_container_formats(self, video_security_validator):
        """Test validation of allowed container formats."""
        allowed_formats = [
            {'format_name': 'mp4'},
            {'format_name': 'mov'},
            {'format_name': 'avi'},
            {'format_name': 'webm'},
            {'format_name': 'matroska'},
            {'format_name': 'quicktime'},
            {'format_name': 'flv'},
            {'format_name': 'ogg'},
            {'format_name': '3gp'}
        ]
        
        for metadata in allowed_formats:
            assert video_security_validator._validate_container_format(metadata) is True
    
    def test_blocked_container_formats(self, video_security_validator):
        """Test rejection of unknown/suspicious container formats."""
        blocked_formats = [
            {'format_name': 'unknown_format'},
            {'format_name': 'suspicious_container'},
            {'format_name': ''},
            {}
        ]
        
        for metadata in blocked_formats:
            assert video_security_validator._validate_container_format(metadata) is False
    
    def test_partial_format_name_matching(self, video_security_validator):
        """Test that partial format name matching works."""
        # Some formats might have additional qualifiers
        complex_formats = [
            {'format_name': 'mov,mp4,m4a,3gp,3g2,mj2'},
            {'format_name': 'matroska,webm'},
            {'format_name': 'avi (AVI (Audio Video Interleaved))'}
        ]
        
        for metadata in complex_formats:
            assert video_security_validator._validate_container_format(metadata) is True


class TestFileIntegrityValidation:
    """Test file integrity and hash validation."""
    
    def test_calculate_file_hash(self, video_security_validator):
        """Test file hash calculation."""
        test_content = b'test video content for hash calculation'
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        with patch('builtins.open', mock_open(read_data=test_content)):
            calculated_hash = video_security_validator.calculate_file_hash('/fake/video.mp4')
        
        assert calculated_hash == expected_hash
        assert len(calculated_hash) == 64  # SHA-256 length
    
    def test_hash_calculation_error_handling(self, video_security_validator):
        """Test hash calculation with file read error."""
        with patch('builtins.open', side_effect=IOError("Cannot read file")):
            hash_result = video_security_validator.calculate_file_hash('/fake/video.mp4')
        
        assert hash_result == ""  # Empty string on error
    
    def test_hash_large_file_chunked_reading(self, video_security_validator):
        """Test hash calculation for large files with chunked reading."""
        # Create complete test data
        chunk_data = b'video_chunk_data' * 100  # ~1.6KB chunk
        complete_data = chunk_data * 10  # Complete file data
        
        expected_hash = hashlib.sha256(complete_data).hexdigest()
        
        # Create proper mock file with context manager support
        mock_file = Mock()
        
        # Mock chunked reading - return chunks of data then EOF
        read_calls = 0
        def mock_read(size=4096):
            nonlocal read_calls
            if read_calls == 0:
                read_calls += 1
                return complete_data[:size] if len(complete_data) > size else complete_data
            elif read_calls == 1 and len(complete_data) > 4096:
                read_calls += 1
                return complete_data[4096:]
            else:
                return b''  # EOF
        
        mock_file.read = mock_read
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        
        with patch('builtins.open', return_value=mock_file):
            calculated_hash = video_security_validator.calculate_file_hash('/fake/large_video.mp4')
        
        assert calculated_hash == expected_hash


class TestSecurityIntegration:
    """Test integration of all security components."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_validation_pass(self, video_security_validator):
        """Test complete security validation for a safe video."""
        safe_metadata = {
            'file_size': 25 * 1024 * 1024,  # 25MB
            'duration': 300,  # 5 minutes
            'width': 1920,
            'height': 1080, 
            'video_codec': 'h264',
            'audio_codec': 'aac',
            'bitrate': 4000,
            'format_name': 'mp4'
        }
        
        # Mock all validation components to pass
        safe_content = b'\x00\x01\x02\x03' * 10000  # Clean content
        mp4_header = b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom' + safe_content
        
        with patch('builtins.open', mock_open(read_data=mp4_header)):
            with patch('os.path.getsize', return_value=len(mp4_header)):
                is_safe, message = await video_security_validator.validate_video_security(
                    '/fake/safe_video.mp4', safe_metadata
                )
        
        assert is_safe is True
        assert 'validation passed' in message.lower()
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_validation_fail(self, video_security_validator):
        """Test complete security validation for a malicious video."""
        malicious_metadata = {
            'file_size': 1024 * 1024 * 1024,  # 1GB - too large
            'duration': 3600,  # 1 hour - might be too long
            'width': 1920,
            'height': 1080,
            'video_codec': 'rv40',  # Blocked codec
            'audio_codec': 'aac',
            'bitrate': 2000,
            'format_name': 'mp4'
        }
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/malicious_video.mp4', malicious_metadata
        )
        
        assert is_safe is False
        # Should fail on the first check (file size)
        assert 'too large' in message.lower()
    
    @pytest.mark.asyncio
    async def test_validation_exception_handling(self, video_security_validator, safe_video_metadata):
        """Test that validation handles exceptions gracefully."""
        # Mock an exception during validation
        with patch.object(video_security_validator, '_validate_file_header', side_effect=Exception("Mock error")):
            is_safe, message = await video_security_validator.validate_video_security(
                '/fake/video.mp4', safe_video_metadata
            )
        
        assert is_safe is False
        assert 'validation error' in message.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])