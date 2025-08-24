"""
Video Processing Package for PhotoShare MediaShare
==================================================

Comprehensive video processing capabilities including:
- Video format validation and analysis
- FFmpeg-based video transcoding
- Thumbnail generation from video frames
- Video streaming utilities
- Security validation for video content
"""

from .video_processor import VideoProcessor
from .video_security import VideoSecurityValidator

__all__ = ['VideoProcessor', 'VideoSecurityValidator']