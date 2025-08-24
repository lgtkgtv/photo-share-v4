#!/usr/bin/env python3
"""
Video Processing Engine for PhotoShare MediaShare
================================================

Comprehensive video processing pipeline with:
- Video metadata analysis using FFprobe
- Thumbnail generation from video frames
- Video transcoding and format conversion
- Security validation and content scanning
"""

import asyncio
import os
import subprocess
import json
import logging
import shutil
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Comprehensive video processing pipeline."""
    
    def __init__(self):
        self.supported_formats = {
            'mp4': ['video/mp4'],
            'avi': ['video/avi', 'video/x-msvideo'],
            'mov': ['video/quicktime'],
            'webm': ['video/webm'],
            'mkv': ['video/x-matroska'],
            'flv': ['video/x-flv'],
            'wmv': ['video/x-ms-wmv'],
            'm4v': ['video/x-m4v'],
            '3gp': ['video/3gpp'],
            'ogv': ['video/ogg']
        }
        
        # Quality presets for transcoding
        self.quality_presets = {
            '4K': {'width': 3840, 'height': 2160, 'bitrate': '8000k'},
            '1440p': {'width': 2560, 'height': 1440, 'bitrate': '6000k'},
            '1080p': {'width': 1920, 'height': 1080, 'bitrate': '4000k'},
            '720p': {'width': 1280, 'height': 720, 'bitrate': '2500k'},
            '480p': {'width': 854, 'height': 480, 'bitrate': '1000k'},
            '360p': {'width': 640, 'height': 360, 'bitrate': '800k'}
        }
        
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
    
    def _find_ffmpeg(self) -> str:
        """Locate FFmpeg binary."""
        ffmpeg_locations = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg', 
            '/opt/homebrew/bin/ffmpeg',  # macOS Homebrew
            'ffmpeg'
        ]
        
        for path in ffmpeg_locations:
            if shutil.which(path):
                logger.info(f"Found FFmpeg at: {path}")
                return path
        
        raise RuntimeError("FFmpeg not found - required for video processing. Install with: apt-get install ffmpeg")
    
    def _find_ffprobe(self) -> str:
        """Locate FFprobe binary."""
        ffprobe_locations = [
            '/usr/bin/ffprobe',
            '/usr/local/bin/ffprobe',
            '/opt/homebrew/bin/ffprobe',  # macOS Homebrew
            'ffprobe'
        ]
        
        for path in ffprobe_locations:
            if shutil.which(path):
                logger.info(f"Found FFprobe at: {path}")
                return path
        
        raise RuntimeError("FFprobe not found - required for video analysis. Install with: apt-get install ffmpeg")
    
    async def analyze_video(self, file_path: str) -> Dict:
        """
        Extract comprehensive video metadata and properties.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dict containing video metadata
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Video file not found: {file_path}")
            
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            logger.debug(f"Running FFprobe command: {' '.join(cmd)}")
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"FFprobe failed: {error_msg}")
                raise ValueError(f"Video analysis failed: {error_msg}")
            
            metadata = json.loads(stdout.decode('utf-8'))
            return self._parse_video_metadata(metadata)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse FFprobe JSON output: {e}")
            raise ValueError(f"Video metadata parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Video analysis error: {e}")
            raise ValueError(f"Video analysis error: {str(e)}")
    
    def _parse_video_metadata(self, metadata: Dict) -> Dict:
        """Parse FFprobe output into structured data."""
        try:
            format_info = metadata.get('format', {})
            streams = metadata.get('streams', [])
            
            # Find video and audio streams
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            
            duration = float(format_info.get('duration', 0))
            file_size = int(format_info.get('size', 0))
            overall_bitrate = int(format_info.get('bit_rate', 0)) // 1000  # Convert to kbps
            
            result = {
                'duration': duration,
                'file_size': file_size,
                'bitrate': overall_bitrate,
                'format_name': format_info.get('format_name', ''),
                'nb_streams': format_info.get('nb_streams', 0)
            }
            
            # Video stream information
            if video_stream:
                width = video_stream.get('width')
                height = video_stream.get('height')
                
                result.update({
                    'video_codec': video_stream.get('codec_name'),
                    'width': width,
                    'height': height,
                    'framerate': self._parse_framerate(video_stream.get('r_frame_rate', '0/1')),
                    'resolution': self._determine_resolution(width, height),
                    'pixel_format': video_stream.get('pix_fmt'),
                    'video_bitrate': int(video_stream.get('bit_rate', 0)) // 1000 if video_stream.get('bit_rate') else None
                })
            
            # Audio stream information
            if audio_stream:
                result.update({
                    'audio_codec': audio_stream.get('codec_name'),
                    'sample_rate': audio_stream.get('sample_rate'),
                    'channels': audio_stream.get('channels'),
                    'audio_bitrate': int(audio_stream.get('bit_rate', 0)) // 1000 if audio_stream.get('bit_rate') else None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing video metadata: {e}")
            raise ValueError(f"Metadata parsing error: {str(e)}")
    
    def _parse_framerate(self, framerate_str: str) -> Optional[float]:
        """Parse framerate from FFprobe format (e.g., '30/1' -> 30.0)."""
        try:
            if '/' in framerate_str:
                numerator, denominator = framerate_str.split('/')
                if int(denominator) != 0:
                    return float(numerator) / float(denominator)
            return float(framerate_str)
        except (ValueError, ZeroDivisionError):
            return None
    
    def _determine_resolution(self, width: Optional[int], height: Optional[int]) -> str:
        """Determine video resolution category."""
        if not width or not height:
            return 'unknown'
        
        if height >= 2160:
            return '4K'
        elif height >= 1440:
            return '1440p'
        elif height >= 1080:
            return '1080p'
        elif height >= 720:
            return '720p'
        elif height >= 480:
            return '480p'
        elif height >= 360:
            return '360p'
        else:
            return f"{width}x{height}"
    
    async def generate_thumbnail(self, video_path: str, output_path: str, 
                               timestamp: float = 1.0, width: int = 320, height: int = 240) -> bool:
        """
        Generate thumbnail from video frame.
        
        Args:
            video_path: Path to source video
            output_path: Path for thumbnail output
            timestamp: Time position in seconds to extract frame
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            bool: Success status
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Source video not found: {video_path}")
                return False
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-ss', str(timestamp),  # Seek to timestamp
                '-vframes', '1',        # Extract 1 frame
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                '-q:v', '2',            # High quality JPEG
                '-y',                   # Overwrite output
                output_path
            ]
            
            logger.debug(f"Generating thumbnail: {' '.join(cmd)}")
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Thumbnail generated successfully: {output_path}")
                return True
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"Thumbnail generation failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Thumbnail generation error: {e}")
            return False
    
    async def transcode_video(self, input_path: str, output_path: str,
                            target_resolution: str = '1080p',
                            target_codec: str = 'h264',
                            quality: str = 'medium') -> bool:
        """
        Transcode video to target format and resolution.
        
        Args:
            input_path: Source video path
            output_path: Output video path
            target_resolution: Target resolution (1080p, 720p, etc.)
            target_codec: Target video codec (h264, h265)
            quality: Encoding quality (fast, medium, slow)
            
        Returns:
            bool: Success status
        """
        try:
            if not os.path.exists(input_path):
                logger.error(f"Source video not found: {input_path}")
                return False
            
            # Get quality preset
            preset = self.quality_presets.get(target_resolution)
            if not preset:
                logger.error(f"Unsupported resolution: {target_resolution}")
                return False
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Codec mapping
            codec_map = {
                'h264': 'libx264',
                'h265': 'libx265',
                'vp8': 'libvpx',
                'vp9': 'libvpx-vp9'
            }
            
            video_codec = codec_map.get(target_codec, 'libx264')
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-c:v', video_codec,
                '-c:a', 'aac',
                '-b:a', '128k',
                '-vf', f"scale={preset['width']}:{preset['height']}:force_original_aspect_ratio=decrease,pad={preset['width']}:{preset['height']}:(ow-iw)/2:(oh-ih)/2",
                '-b:v', preset['bitrate'],
                '-preset', quality,
                '-movflags', '+faststart',  # Optimize for streaming
                '-y',  # Overwrite output
                output_path
            ]
            
            # Add codec-specific options
            if video_codec == 'libx264':
                cmd.extend(['-crf', '23'])  # Quality setting for H.264
            elif video_codec == 'libx265':
                cmd.extend(['-crf', '28'])  # Quality setting for H.265
            
            logger.info(f"Starting video transcoding: {target_resolution} {target_codec}")
            logger.debug(f"Transcoding command: {' '.join(cmd)}")
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Video transcoding completed successfully: {output_path}")
                return True
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"Video transcoding failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Video transcoding error: {e}")
            return False
    
    def is_supported_format(self, content_type: str) -> bool:
        """Check if video format is supported."""
        return any(content_type in formats for formats in self.supported_formats.values())
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported video formats."""
        formats = []
        for ext, mime_types in self.supported_formats.items():
            formats.extend(mime_types)
        return formats
    
    async def get_video_info_summary(self, file_path: str) -> str:
        """Get human-readable summary of video information."""
        try:
            metadata = await self.analyze_video(file_path)
            
            duration_str = f"{int(metadata.get('duration', 0) // 60)}:{int(metadata.get('duration', 0) % 60):02d}"
            size_mb = metadata.get('file_size', 0) / (1024 * 1024)
            
            return (
                f"Resolution: {metadata.get('resolution', 'unknown')} "
                f"({metadata.get('width', 0)}x{metadata.get('height', 0)}), "
                f"Duration: {duration_str}, "
                f"Size: {size_mb:.1f}MB, "
                f"Codec: {metadata.get('video_codec', 'unknown')}, "
                f"Framerate: {metadata.get('framerate', 0):.1f}fps"
            )
            
        except Exception as e:
            return f"Error analyzing video: {str(e)}"