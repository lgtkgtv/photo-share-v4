#!/usr/bin/env python3
"""
Video Security Validation for PhotoShare MediaShare
===================================================

Enhanced security validation for video files including:
- File size and duration limits
- Codec validation and allowlisting
- Content scanning for malicious patterns
- Video-specific threat detection
"""

import os
import logging
import hashlib
from typing import Dict, List, Tuple, Optional
import re

logger = logging.getLogger(__name__)

class VideoSecurityValidator:
    """Enhanced security validation for video files."""
    
    def __init__(self):
        # Security limits
        self.max_video_size = 500 * 1024 * 1024  # 500MB default
        self.max_duration = 3600  # 1 hour in seconds
        self.min_duration = 0.1   # 100ms minimum
        self.max_bitrate = 50000  # 50Mbps maximum
        self.max_resolution = {'width': 7680, 'height': 4320}  # 8K max
        
        # Allowed codecs (security whitelist)
        self.allowed_codecs = {
            'video': {
                'h264', 'h265', 'vp8', 'vp9', 'av1',  # Modern codecs
                'mpeg4', 'theora'  # Legacy but common
            },
            'audio': {
                'aac', 'mp3', 'opus', 'vorbis',  # Common audio codecs
                'flac', 'pcm'  # Uncompressed/lossless
            }
        }
        
        # Blocked/dangerous codecs
        self.blocked_codecs = {
            'video': {
                'rv40',  # RealVideo (known security issues)
                'indeo5',  # Intel Indeo (deprecated, security issues)
            },
            'audio': {
                'cook',  # RealAudio COOK (known issues)
            }
        }
        
        # Malicious pattern detection
        self.malicious_patterns = [
            # Code injection patterns
            b'<?php', b'<script', b'eval(', b'system(',
            b'exec(', b'shell_exec(', b'passthru(',
            # Buffer overflow patterns
            b'A' * 1000,  # Long sequences that might indicate buffer overflow attempts
            # Known exploit signatures
            b'\x90' * 100,  # NOP sleds
            b'\xcc' * 50,   # Debugger interrupts
        ]
        
        # File header validation
        self.valid_video_headers = {
            # MP4/MOV containers
            b'ftyp': 4,      # MP4 container
            b'moov': 4,      # QuickTime/MOV
            # AVI container
            b'RIFF': 0,      # AVI file
            # WebM/Matroska
            b'\x1a\x45\xdf\xa3': 0,  # EBML header for WebM/MKV
            # Other common formats
            b'FLV': 0,       # Flash Video
        }
    
    async def validate_video_security(self, file_path: str, 
                                    metadata: Dict) -> Tuple[bool, str]:
        """
        Comprehensive video security validation.
        
        Args:
            file_path: Path to video file
            metadata: Video metadata from VideoProcessor
            
        Returns:
            Tuple[bool, str]: (is_safe, reason/message)
        """
        try:
            # 1. File size validation
            file_size = metadata.get('file_size', 0)
            if file_size > self.max_video_size:
                return False, f"Video file too large: {file_size / (1024*1024):.1f}MB (max: {self.max_video_size / (1024*1024):.1f}MB)"
            
            if file_size < 1024:  # Less than 1KB is suspicious
                return False, "Video file too small to be valid"
            
            # 2. Duration validation
            duration = metadata.get('duration', 0)
            if duration > self.max_duration:
                return False, f"Video too long: {duration/60:.1f} minutes (max: {self.max_duration/60:.1f} minutes)"
            
            if duration < self.min_duration:
                return False, f"Video too short: {duration:.2f}s (min: {self.min_duration:.2f}s)"
            
            # 3. Resolution validation
            width = metadata.get('width', 0)
            height = metadata.get('height', 0)
            
            if width > self.max_resolution['width'] or height > self.max_resolution['height']:
                return False, f"Resolution too high: {width}x{height} (max: {self.max_resolution['width']}x{self.max_resolution['height']})"
            
            # 4. Codec validation
            video_codec = metadata.get('video_codec', '').lower()
            audio_codec = metadata.get('audio_codec', '').lower()
            
            # Check for blocked codecs first
            if video_codec in self.blocked_codecs['video']:
                return False, f"Blocked video codec detected: {video_codec}"
            
            if audio_codec and audio_codec in self.blocked_codecs['audio']:
                return False, f"Blocked audio codec detected: {audio_codec}"
            
            # Check if codecs are in allowed list
            if video_codec and video_codec not in self.allowed_codecs['video']:
                return False, f"Unsupported video codec: {video_codec}"
            
            if audio_codec and audio_codec not in self.allowed_codecs['audio']:
                return False, f"Unsupported audio codec: {audio_codec}"
            
            # 5. Bitrate validation (prevent bandwidth abuse)
            bitrate = metadata.get('bitrate', 0)
            if bitrate > self.max_bitrate:
                return False, f"Bitrate too high: {bitrate}kbps (max: {self.max_bitrate}kbps)"
            
            # 6. File header validation
            if not await self._validate_file_header(file_path):
                return False, "Invalid or corrupted video file header"
            
            # 7. Content scanning for malicious patterns
            if await self._scan_video_content(file_path):
                return False, "Potentially malicious content detected in video file"
            
            # 8. Container format validation
            if not self._validate_container_format(metadata):
                return False, "Unsupported or suspicious container format"
            
            logger.info(f"Video security validation passed: {os.path.basename(file_path)}")
            return True, "Video validation passed"
            
        except Exception as e:
            logger.error(f"Video security validation error: {e}")
            return False, f"Video validation error: {str(e)}"
    
    async def _validate_file_header(self, file_path: str) -> bool:
        """Validate video file header to ensure it's a legitimate video file."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # Read first 1KB
            
            # Check for known video file signatures
            for signature, offset in self.valid_video_headers.items():
                if header[offset:offset+len(signature)] == signature:
                    return True
            
            # Additional checks for common video formats
            # AVI files have RIFF header followed by AVI identifier
            if header.startswith(b'RIFF') and b'AVI ' in header[:20]:
                return True
            
            # MP4 files have various ftyp signatures
            if b'ftyp' in header[:20] and any(brand in header[:50] for brand in [b'mp41', b'mp42', b'isom', b'avc1']):
                return True
            
            logger.warning(f"Unknown video file header: {header[:20].hex()}")
            return False
            
        except Exception as e:
            logger.error(f"File header validation error: {e}")
            return False
    
    async def _scan_video_content(self, file_path: str) -> bool:
        """
        Scan video file for malicious patterns.
        
        Returns:
            bool: True if malicious content found
        """
        try:
            # Scan first and last chunks of the file for embedded threats
            file_size = os.path.getsize(file_path)
            chunk_size = min(64 * 1024, file_size // 10)  # 64KB or 10% of file
            
            with open(file_path, 'rb') as f:
                # Scan beginning
                header_chunk = f.read(chunk_size)
                
                # Scan end
                if file_size > chunk_size:
                    f.seek(-chunk_size, 2)  # Seek from end
                    footer_chunk = f.read(chunk_size)
                else:
                    footer_chunk = b''
                
                # Scan middle (for larger files)
                middle_chunk = b''
                if file_size > chunk_size * 3:
                    f.seek(file_size // 2)
                    middle_chunk = f.read(min(chunk_size, 32768))
            
            # Check all chunks for malicious patterns
            chunks = [header_chunk, footer_chunk, middle_chunk]
            
            for chunk in chunks:
                if not chunk:
                    continue
                    
                for pattern in self.malicious_patterns:
                    if pattern in chunk:
                        logger.warning(f"Malicious pattern detected: {pattern[:20]}")
                        return True
                
                # Check for suspicious strings that might indicate embedded scripts
                suspicious_strings = [
                    b'javascript:', b'vbscript:', b'data:text/html',
                    b'<iframe', b'<object', b'<embed',
                    b'onload=', b'onerror=', b'onclick='
                ]
                
                for sus_string in suspicious_strings:
                    if sus_string in chunk.lower():
                        logger.warning(f"Suspicious string detected: {sus_string}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Content scanning error: {e}")
            return True  # Err on the side of caution
    
    def _validate_container_format(self, metadata: Dict) -> bool:
        """Validate video container format for known secure formats."""
        try:
            format_name = metadata.get('format_name', '').lower()
            
            # List of allowed container formats
            allowed_formats = {
                'mp4', 'mov', 'avi', 'webm', 'matroska',
                'quicktime', 'flv', 'ogg', '3gp'
            }
            
            # Check if any allowed format is present in the format name
            return any(allowed_format in format_name for allowed_format in allowed_formats)
            
        except Exception as e:
            logger.error(f"Container format validation error: {e}")
            return False
    
    def get_security_config(self) -> Dict:
        """Get current security configuration for admin/debugging purposes."""
        return {
            'max_video_size_mb': self.max_video_size // (1024 * 1024),
            'max_duration_minutes': self.max_duration // 60,
            'max_resolution': self.max_resolution,
            'max_bitrate_kbps': self.max_bitrate,
            'allowed_video_codecs': list(self.allowed_codecs['video']),
            'allowed_audio_codecs': list(self.allowed_codecs['audio']),
            'blocked_video_codecs': list(self.blocked_codecs['video']),
            'blocked_audio_codecs': list(self.blocked_codecs['audio'])
        }
    
    def update_security_limits(self, 
                             max_size_mb: Optional[int] = None,
                             max_duration_minutes: Optional[int] = None,
                             max_bitrate_kbps: Optional[int] = None) -> None:
        """Update security limits (for admin configuration)."""
        if max_size_mb is not None:
            self.max_video_size = max_size_mb * 1024 * 1024
            logger.info(f"Updated max video size: {max_size_mb}MB")
        
        if max_duration_minutes is not None:
            self.max_duration = max_duration_minutes * 60
            logger.info(f"Updated max duration: {max_duration_minutes} minutes")
        
        if max_bitrate_kbps is not None:
            self.max_bitrate = max_bitrate_kbps
            logger.info(f"Updated max bitrate: {max_bitrate_kbps}kbps")
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash for file integrity verification."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"File hash calculation error: {e}")
            return ""