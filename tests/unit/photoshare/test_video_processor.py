#!/usr/bin/env python3
"""
Unit Tests for Video Processor
==============================

Tests the video processing functionality including:
- Video metadata analysis
- Thumbnail generation 
- Video transcoding
- Format validation
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Import the video processor
try:
    from services.photoshare.video_processing.video_processor import VideoProcessor
    from services.photoshare.video_processing.video_security import VideoSecurityValidator
    VIDEO_PROCESSOR_AVAILABLE = True
except ImportError:
    VIDEO_PROCESSOR_AVAILABLE = False


@pytest.fixture
def video_processor():
    """Create a VideoProcessor instance for testing."""
    if not VIDEO_PROCESSOR_AVAILABLE:
        pytest.skip("Video processor not available")
    
    # Mock FFmpeg paths for testing
    with patch('shutil.which') as mock_which:
        mock_which.return_value = '/usr/bin/ffmpeg'  # Mock FFmpeg found
        return VideoProcessor()


@pytest.fixture
def video_security_validator():
    """Create a VideoSecurityValidator instance for testing."""
    if not VIDEO_PROCESSOR_AVAILABLE:
        pytest.skip("Video security validator not available")
    return VideoSecurityValidator()


@pytest.fixture
def sample_video_metadata():
    """Sample video metadata for testing."""
    return {
        'format': {
            'duration': '10.0',
            'size': '1048576',
            'bit_rate': '1000000',
            'format_name': 'mp4',
            'nb_streams': 2
        },
        'streams': [
            {
                'codec_type': 'video',
                'codec_name': 'h264',
                'width': 1920,
                'height': 1080,
                'r_frame_rate': '30/1',
                'pix_fmt': 'yuv420p',
                'bit_rate': '800000'
            },
            {
                'codec_type': 'audio',
                'codec_name': 'aac',
                'sample_rate': '44100',
                'channels': 2,
                'bit_rate': '128000'
            }
        ]
    }


class TestVideoProcessor:
    """Test cases for VideoProcessor class."""

    def test_initialization(self, video_processor):
        """Test VideoProcessor initialization."""
        assert video_processor.supported_formats
        assert 'mp4' in video_processor.supported_formats
        assert 'webm' in video_processor.supported_formats
        assert video_processor.quality_presets
        assert '1080p' in video_processor.quality_presets

    def test_supported_format_validation(self, video_processor):
        """Test video format validation."""
        # Test supported formats
        assert video_processor.is_supported_format('video/mp4')
        assert video_processor.is_supported_format('video/webm')
        assert video_processor.is_supported_format('video/quicktime')
        
        # Test unsupported formats
        assert not video_processor.is_supported_format('video/fake')
        assert not video_processor.is_supported_format('image/jpeg')

    def test_get_supported_formats(self, video_processor):
        """Test getting list of supported formats."""
        formats = video_processor.get_supported_formats()
        assert isinstance(formats, list)
        assert 'video/mp4' in formats
        assert len(formats) > 5

    def test_parse_framerate(self, video_processor):
        """Test framerate parsing."""
        # Test normal fraction
        assert video_processor._parse_framerate('30/1') == 30.0
        assert video_processor._parse_framerate('29970/1000') == 29.97
        
        # Test direct number
        assert video_processor._parse_framerate('30') == 30.0
        
        # Test invalid values
        assert video_processor._parse_framerate('invalid') is None
        assert video_processor._parse_framerate('30/0') is None

    def test_determine_resolution(self, video_processor):
        """Test resolution category determination."""
        # Test standard resolutions
        assert video_processor._determine_resolution(1920, 1080) == '1080p'
        assert video_processor._determine_resolution(1280, 720) == '720p'
        assert video_processor._determine_resolution(3840, 2160) == '4K'
        assert video_processor._determine_resolution(2560, 1440) == '1440p'
        
        # Test custom resolution (600 >= 480, so it will be '480p')
        assert video_processor._determine_resolution(800, 600) == '480p'
        
        # Test invalid input
        assert video_processor._determine_resolution(None, None) == 'unknown'

    def test_parse_video_metadata(self, video_processor, sample_video_metadata):
        """Test video metadata parsing."""
        parsed = video_processor._parse_video_metadata(sample_video_metadata)
        
        # Test basic format info
        assert parsed['duration'] == 10.0
        assert parsed['file_size'] == 1048576
        assert parsed['bitrate'] == 1000
        assert parsed['format_name'] == 'mp4'
        
        # Test video stream info
        assert parsed['video_codec'] == 'h264'
        assert parsed['width'] == 1920
        assert parsed['height'] == 1080
        assert parsed['framerate'] == 30.0
        assert parsed['resolution'] == '1080p'
        
        # Test audio stream info
        assert parsed['audio_codec'] == 'aac'
        assert parsed['sample_rate'] == '44100'
        assert parsed['channels'] == 2

    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_analyze_video_success(self, mock_subprocess, video_processor, sample_video_metadata):
        """Test successful video analysis."""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            json.dumps(sample_video_metadata).encode(),
            b''
        )
        mock_subprocess.return_value = mock_process
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            result = await video_processor.analyze_video('/fake/path/video.mp4')
        
        assert result['duration'] == 10.0
        assert result['video_codec'] == 'h264'
        assert result['resolution'] == '1080p'

    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_analyze_video_file_not_found(self, mock_subprocess, video_processor):
        """Test video analysis with missing file."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(ValueError, match="Video analysis error"):
                await video_processor.analyze_video('/fake/path/video.mp4')

    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_analyze_video_ffprobe_error(self, mock_subprocess, video_processor):
        """Test video analysis with FFprobe error."""
        # Mock subprocess failure
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'FFprobe error')
        mock_subprocess.return_value = mock_process
        
        with patch('os.path.exists', return_value=True):
            with pytest.raises(ValueError, match="Video analysis failed"):
                await video_processor.analyze_video('/fake/path/video.mp4')

    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_generate_thumbnail_success(self, mock_subprocess, video_processor):
        """Test successful thumbnail generation."""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'', b'')
        mock_subprocess.return_value = mock_process
        
        with patch('os.path.exists', side_effect=[True, True]):  # source exists, output created
            with patch('os.makedirs'):
                result = await video_processor.generate_thumbnail(
                    '/fake/video.mp4', '/fake/thumb.jpg'
                )
        
        assert result is True

    @patch('asyncio.create_subprocess_exec')
    @pytest.mark.asyncio
    async def test_generate_thumbnail_failure(self, mock_subprocess, video_processor):
        """Test thumbnail generation failure."""
        # Mock subprocess failure
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'FFmpeg error')
        mock_subprocess.return_value = mock_process
        
        with patch('os.path.exists', return_value=True):
            with patch('os.makedirs'):
                result = await video_processor.generate_thumbnail(
                    '/fake/video.mp4', '/fake/thumb.jpg'
                )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_video_info_summary(self, video_processor, sample_video_metadata):
        """Test video info summary generation."""
        with patch.object(video_processor, 'analyze_video', return_value={
            'resolution': '1080p',
            'width': 1920,
            'height': 1080,
            'duration': 125.5,  # 2:05
            'file_size': 104857600,  # 100MB
            'video_codec': 'h264',
            'framerate': 29.97
        }):
            summary = await video_processor.get_video_info_summary('/fake/video.mp4')
        
        assert 'Resolution: 1080p' in summary
        assert '1920x1080' in summary
        assert '2:05' in summary  # Duration formatting
        assert '100.0MB' in summary
        assert 'h264' in summary
        assert '30.0fps' in summary


class TestVideoSecurityValidator:
    """Test cases for VideoSecurityValidator class."""

    def test_initialization(self, video_security_validator):
        """Test VideoSecurityValidator initialization."""
        validator = video_security_validator
        assert validator.max_video_size > 0
        assert validator.max_duration > 0
        assert validator.allowed_codecs['video']
        assert validator.allowed_codecs['audio']
        assert validator.blocked_codecs['video']
        assert validator.malicious_patterns

    def test_get_security_config(self, video_security_validator):
        """Test getting security configuration."""
        config = video_security_validator.get_security_config()
        
        assert 'max_video_size_mb' in config
        assert 'max_duration_minutes' in config
        assert 'allowed_video_codecs' in config
        assert 'blocked_video_codecs' in config
        assert isinstance(config['allowed_video_codecs'], list)

    def test_update_security_limits(self, video_security_validator):
        """Test updating security limits."""
        original_size = video_security_validator.max_video_size
        
        # Update limits
        video_security_validator.update_security_limits(
            max_size_mb=100,
            max_duration_minutes=30,
            max_bitrate_kbps=5000
        )
        
        assert video_security_validator.max_video_size == 100 * 1024 * 1024
        assert video_security_validator.max_duration == 30 * 60
        assert video_security_validator.max_bitrate == 5000

    @pytest.mark.asyncio
    async def test_validate_video_security_success(self, video_security_validator):
        """Test successful video security validation."""
        metadata = {
            'file_size': 10 * 1024 * 1024,  # 10MB
            'duration': 60,  # 1 minute
            'width': 1920,
            'height': 1080,
            'video_codec': 'h264',
            'audio_codec': 'aac',
            'bitrate': 2000,
            'format_name': 'mp4'
        }
        
        with patch.object(video_security_validator, '_validate_file_header', return_value=True):
            with patch.object(video_security_validator, '_scan_video_content', return_value=False):
                is_safe, message = await video_security_validator.validate_video_security(
                    '/fake/video.mp4', metadata
                )
        
        assert is_safe is True
        assert 'validation passed' in message.lower()

    @pytest.mark.asyncio
    async def test_validate_video_security_file_too_large(self, video_security_validator):
        """Test video security validation with oversized file."""
        metadata = {
            'file_size': 1024 * 1024 * 1024,  # 1GB (too large)
            'duration': 60,
            'width': 1920,
            'height': 1080,
            'video_codec': 'h264',
            'bitrate': 2000,
            'format_name': 'mp4'
        }
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/video.mp4', metadata
        )
        
        assert is_safe is False
        assert 'too large' in message.lower()

    @pytest.mark.asyncio
    async def test_validate_video_security_blocked_codec(self, video_security_validator):
        """Test video security validation with blocked codec."""
        metadata = {
            'file_size': 10 * 1024 * 1024,
            'duration': 60,
            'width': 1920,
            'height': 1080,
            'video_codec': 'rv40',  # Blocked codec
            'bitrate': 2000,
            'format_name': 'mp4'
        }
        
        is_safe, message = await video_security_validator.validate_video_security(
            '/fake/video.mp4', metadata
        )
        
        assert is_safe is False
        assert 'blocked' in message.lower()
        assert 'rv40' in message.lower()

    @pytest.mark.asyncio
    async def test_validate_file_header_success(self, video_security_validator):
        """Test file header validation success."""
        # Mock MP4 file header
        mp4_header = b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom' + b'\x00' * 1000
        
        with patch('builtins.open', mock_open(read_data=mp4_header)):
            result = await video_security_validator._validate_file_header('/fake/video.mp4')
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_file_header_invalid(self, video_security_validator):
        """Test file header validation with invalid header."""
        # Mock invalid file header
        invalid_header = b'INVALID_HEADER' + b'\x00' * 1000
        
        with patch('builtins.open', mock_open(read_data=invalid_header)):
            result = await video_security_validator._validate_file_header('/fake/video.mp4')
        
        assert result is False

    @pytest.mark.asyncio
    async def test_scan_video_content_clean(self, video_security_validator):
        """Test video content scanning with clean content."""
        # Mock clean video content
        clean_content = b'\x00\x01\x02\x03' * 1000
        
        with patch('os.path.getsize', return_value=len(clean_content)):
            with patch('builtins.open', mock_open(read_data=clean_content)):
                result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is False  # No malicious content found

    @pytest.mark.asyncio
    async def test_scan_video_content_malicious(self, video_security_validator):
        """Test video content scanning with malicious patterns."""
        # Mock content with malicious pattern (use exact pattern from validator)
        malicious_content = b'clean content' + b'<?php' + b'more clean content'
        
        # Mock the file reading behavior more precisely
        mock_file = Mock()
        
        def mock_read(size=None):
            """Mock read that returns malicious content."""
            return malicious_content[:size] if size else malicious_content
        
        def mock_seek(offset, whence=0):
            """Mock seek behavior."""
            pass
            
        mock_file.read = mock_read
        mock_file.seek = mock_seek
        
        with patch('os.path.getsize', return_value=len(malicious_content)):
            with patch('builtins.open', return_value=mock_file):
                result = await video_security_validator._scan_video_content('/fake/video.mp4')
        
        assert result is True  # Malicious content found

    def test_validate_container_format(self, video_security_validator):
        """Test container format validation."""
        # Test allowed formats
        assert video_security_validator._validate_container_format({'format_name': 'mp4'}) is True
        assert video_security_validator._validate_container_format({'format_name': 'webm'}) is True
        assert video_security_validator._validate_container_format({'format_name': 'quicktime'}) is True
        
        # Test disallowed formats
        assert video_security_validator._validate_container_format({'format_name': 'unknown_format'}) is False
        assert video_security_validator._validate_container_format({}) is False

    def test_calculate_file_hash(self, video_security_validator):
        """Test file hash calculation."""
        test_content = b'test video content for hashing'
        
        with patch('builtins.open', mock_open(read_data=test_content)):
            hash_result = video_security_validator.calculate_file_hash('/fake/video.mp4')
        
        assert len(hash_result) == 64  # SHA-256 hash length
        assert hash_result  # Should not be empty


def mock_open(read_data=b''):
    """Helper function to mock file opening with binary data."""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)


# Test configuration

@pytest.mark.asyncio
class TestVideoProcessorIntegration:
    """Integration tests for video processor components."""

    @pytest.mark.asyncio
    async def test_full_video_processing_pipeline(self, video_processor, video_security_validator):
        """Test complete video processing pipeline."""
        # This would be an integration test with actual video files
        # For unit testing, we mock the components
        
        metadata = {
            'file_size': 50 * 1024 * 1024,
            'duration': 120,
            'width': 1280,
            'height': 720,
            'video_codec': 'h264',
            'audio_codec': 'aac',
            'bitrate': 2000,
            'format_name': 'mp4'
        }
        
        # Mock all external dependencies
        with patch.object(video_security_validator, '_validate_file_header', return_value=True), \
             patch.object(video_security_validator, '_scan_video_content', return_value=False), \
             patch.object(video_processor, 'analyze_video', return_value=metadata), \
             patch.object(video_processor, 'generate_thumbnail', return_value=True):
            
            # Test security validation
            is_safe, message = await video_security_validator.validate_video_security(
                '/fake/video.mp4', metadata
            )
            assert is_safe is True
            
            # Test video analysis
            analysis_result = await video_processor.analyze_video('/fake/video.mp4')
            assert analysis_result['video_codec'] == 'h264'
            
            # Test thumbnail generation
            thumbnail_result = await video_processor.generate_thumbnail(
                '/fake/video.mp4', '/fake/thumb.jpg'
            )
            assert thumbnail_result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])