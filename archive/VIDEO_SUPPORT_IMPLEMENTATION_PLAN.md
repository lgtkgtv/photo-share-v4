# Video Support Implementation Plan

**Enhancement**: Transform PhotoShare to MediaShare (Photos + Videos)  
**Phase**: 1 of 3 (Video Support → Object Storage → Deduplication)  
**Date**: August 23, 2025  
**Estimated Time**: 2-3 weeks

## 🎯 **Overview**

Transform PhotoShare from a photo-only service into a comprehensive media platform supporting both photos and videos with:
- Multiple video format support (MP4, AVI, MOV, WebM, MKV)
- Video transcoding and compression
- Thumbnail generation from video frames
- Video streaming capabilities
- Enhanced security validation for video content

## 🏗️ **Architecture Changes**

### **Database Schema Evolution**

#### **Current: Photo-Only Model**
```sql
CREATE TABLE photos (
    id SERIAL PRIMARY KEY,
    user_uuid VARCHAR(36) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    width INTEGER,
    height INTEGER,
    -- photo-specific fields
);
```

#### **Target: Unified Media Model**
```sql
-- Rename table for broader scope
ALTER TABLE photos RENAME TO media;

-- Add video-specific fields
ALTER TABLE media ADD COLUMN media_type VARCHAR(10) NOT NULL DEFAULT 'photo'; -- 'photo', 'video'
ALTER TABLE media ADD COLUMN duration INTEGER; -- Video duration in seconds
ALTER TABLE media ADD COLUMN video_codec VARCHAR(20); -- H.264, H.265, VP9, AV1
ALTER TABLE media ADD COLUMN audio_codec VARCHAR(20); -- AAC, MP3, Opus
ALTER TABLE media ADD COLUMN resolution VARCHAR(20); -- 1080p, 720p, 4K
ALTER TABLE media ADD COLUMN framerate DECIMAL(5,2); -- 30.0, 60.0 fps
ALTER TABLE media ADD COLUMN bitrate INTEGER; -- Video bitrate in kbps
ALTER TABLE media ADD COLUMN thumbnail_path VARCHAR(500); -- Video thumbnail storage
ALTER TABLE media ADD COLUMN processing_status VARCHAR(20) DEFAULT 'completed'; -- pending, processing, completed, failed
ALTER TABLE media ADD COLUMN transcoded_variants JSON; -- Different quality variants

-- Update constraints and indexes
CREATE INDEX idx_media_type ON media(media_type);
CREATE INDEX idx_processing_status ON media(processing_status);
CREATE INDEX idx_duration ON media(duration) WHERE media_type = 'video';
```

### **Service Architecture**

#### **New Video Processing Service**
```
services/photoshare/
├── video_processing/
│   ├── __init__.py
│   ├── video_processor.py       # Main video processing coordinator
│   ├── video_transcoder.py      # FFmpeg integration
│   ├── thumbnail_generator.py   # Video thumbnail extraction
│   ├── format_validator.py      # Video format validation
│   ├── streaming_server.py      # Video streaming utilities
│   └── codec_analyzer.py        # Video/audio codec detection
```

## 📋 **Implementation Steps**

### **Step 1: Database Schema Migration** (Day 1-2)

#### **Migration Script: `001_add_video_support.sql`**
```sql
-- Create migration script
BEGIN;

-- Rename table
ALTER TABLE photos RENAME TO media;

-- Add video-specific columns
ALTER TABLE media ADD COLUMN media_type VARCHAR(10) NOT NULL DEFAULT 'photo';
ALTER TABLE media ADD COLUMN duration INTEGER;
ALTER TABLE media ADD COLUMN video_codec VARCHAR(20);
ALTER TABLE media ADD COLUMN audio_codec VARCHAR(20);
ALTER TABLE media ADD COLUMN resolution VARCHAR(20);
ALTER TABLE media ADD COLUMN framerate DECIMAL(5,2);
ALTER TABLE media ADD COLUMN bitrate INTEGER;
ALTER TABLE media ADD COLUMN thumbnail_path VARCHAR(500);
ALTER TABLE media ADD COLUMN processing_status VARCHAR(20) DEFAULT 'completed';
ALTER TABLE media ADD COLUMN transcoded_variants JSON;

-- Create indexes
CREATE INDEX idx_media_type ON media(media_type);
CREATE INDEX idx_processing_status ON media(processing_status);
CREATE INDEX idx_duration ON media(duration) WHERE media_type = 'video';

-- Update existing records to be photos
UPDATE media SET media_type = 'photo' WHERE media_type IS NULL;

COMMIT;
```

#### **Database Model Updates**
```python
# Update app_database.py
class Media(AppBase):  # Renamed from Photo
    """Media metadata for photos and videos."""
    __tablename__ = "media"
    
    # Existing fields...
    
    # New video-specific fields
    media_type = Column(String(10), nullable=False, default='photo', index=True)
    duration = Column(Integer, nullable=True)  # seconds
    video_codec = Column(String(20), nullable=True)
    audio_codec = Column(String(20), nullable=True)
    resolution = Column(String(20), nullable=True)
    framerate = Column(Numeric(5,2), nullable=True)
    bitrate = Column(Integer, nullable=True)  # kbps
    thumbnail_path = Column(String(500), nullable=True)
    processing_status = Column(String(20), default='completed', index=True)
    transcoded_variants = Column(JSON, nullable=True)
    
    @property
    def is_video(self) -> bool:
        return self.media_type == 'video'
    
    @property
    def is_photo(self) -> bool:
        return self.media_type == 'photo'
```

### **Step 2: Video Processing Framework** (Day 3-5)

#### **Core Video Processor**
```python
# services/photoshare/video_processing/video_processor.py
import asyncio
import os
import subprocess
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

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
            'm4v': ['video/x-m4v']
        }
        self.ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> str:
        """Locate FFmpeg binary."""
        for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', 'ffmpeg']:
            if subprocess.run(['which', path], capture_output=True).returncode == 0:
                return path
        raise RuntimeError("FFmpeg not found - required for video processing")
    
    async def analyze_video(self, file_path: str) -> Dict:
        """Extract video metadata and properties."""
        cmd = [
            self.ffmpeg_path, '-i', file_path,
            '-f', 'null', '-',
            '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams'
        ]
        
        try:
            result = await asyncio.create_subprocess_exec(
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise ValueError(f"Video analysis failed: {stderr.decode()}")
            
            metadata = json.loads(stdout.decode())
            return self._parse_video_metadata(metadata)
            
        except Exception as e:
            raise ValueError(f"Video analysis error: {str(e)}")
    
    def _parse_video_metadata(self, metadata: Dict) -> Dict:
        """Parse FFprobe output into structured data."""
        format_info = metadata.get('format', {})
        streams = metadata.get('streams', [])
        
        video_stream = next((s for s in streams if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in streams if s['codec_type'] == 'audio'), None)
        
        return {
            'duration': float(format_info.get('duration', 0)),
            'file_size': int(format_info.get('size', 0)),
            'bitrate': int(format_info.get('bit_rate', 0)),
            'video_codec': video_stream.get('codec_name') if video_stream else None,
            'audio_codec': audio_stream.get('codec_name') if audio_stream else None,
            'width': video_stream.get('width') if video_stream else None,
            'height': video_stream.get('height') if video_stream else None,
            'framerate': eval(video_stream.get('r_frame_rate', '0/1')) if video_stream else None,
            'resolution': self._determine_resolution(
                video_stream.get('width'),
                video_stream.get('height')
            ) if video_stream else None
        }
    
    def _determine_resolution(self, width: int, height: int) -> str:
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
        else:
            return f"{width}x{height}"
    
    async def generate_thumbnail(self, video_path: str, output_path: str, 
                               timestamp: float = 1.0) -> bool:
        """Generate thumbnail from video frame."""
        try:
            cmd = [
                self.ffmpeg_path, '-i', video_path,
                '-ss', str(timestamp),
                '-vframes', '1',
                '-q:v', '2',  # High quality
                '-y',  # Overwrite output
                output_path
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            return result.returncode == 0
            
        except Exception as e:
            print(f"Thumbnail generation error: {e}")
            return False
    
    async def transcode_video(self, input_path: str, output_path: str,
                            target_resolution: str = '1080p',
                            target_codec: str = 'h264') -> bool:
        """Transcode video to target format and resolution."""
        try:
            # Resolution mapping
            resolution_map = {
                '4K': '3840:2160',
                '1440p': '2560:1440', 
                '1080p': '1920:1080',
                '720p': '1280:720',
                '480p': '854:480'
            }
            
            scale = resolution_map.get(target_resolution, '1920:1080')
            
            cmd = [
                self.ffmpeg_path, '-i', input_path,
                '-c:v', 'libx264' if target_codec == 'h264' else target_codec,
                '-c:a', 'aac',
                '-b:a', '128k',
                '-vf', f'scale={scale}',
                '-preset', 'medium',
                '-crf', '23',  # Quality setting
                '-y',  # Overwrite output
                output_path
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            return result.returncode == 0
            
        except Exception as e:
            print(f"Transcoding error: {e}")
            return False
```

#### **Video Upload Security Enhancement**
```python
# Update upload_security.py
class VideoSecurityValidator:
    """Enhanced security validation for video files."""
    
    def __init__(self):
        self.max_video_size = 500 * 1024 * 1024  # 500MB
        self.max_duration = 3600  # 1 hour
        self.allowed_codecs = {
            'video': ['h264', 'h265', 'vp8', 'vp9', 'av1'],
            'audio': ['aac', 'mp3', 'opus', 'vorbis']
        }
    
    async def validate_video_security(self, file_path: str, 
                                    metadata: Dict) -> Tuple[bool, str]:
        """Comprehensive video security validation."""
        try:
            # 1. File size check
            if metadata.get('file_size', 0) > self.max_video_size:
                return False, "Video file too large"
            
            # 2. Duration check
            if metadata.get('duration', 0) > self.max_duration:
                return False, "Video duration too long"
            
            # 3. Codec validation
            video_codec = metadata.get('video_codec', '').lower()
            audio_codec = metadata.get('audio_codec', '').lower()
            
            if video_codec and video_codec not in self.allowed_codecs['video']:
                return False, f"Unsupported video codec: {video_codec}"
            
            if audio_codec and audio_codec not in self.allowed_codecs['audio']:
                return False, f"Unsupported audio codec: {audio_codec}"
            
            # 4. Content scanning (basic)
            if await self._scan_video_content(file_path):
                return False, "Potentially malicious video content detected"
            
            return True, "Video validation passed"
            
        except Exception as e:
            return False, f"Video validation error: {str(e)}"
    
    async def _scan_video_content(self, file_path: str) -> bool:
        """Basic video content scanning for malicious patterns."""
        try:
            # Check file header for malicious patterns
            with open(file_path, 'rb') as f:
                header = f.read(1024)
            
            # Look for suspicious patterns
            malicious_patterns = [
                b'<?php',  # PHP code in video
                b'<script',  # JavaScript in video
                b'eval(',   # Code evaluation
                b'system(',  # System calls
            ]
            
            for pattern in malicious_patterns:
                if pattern in header:
                    return True
            
            return False
            
        except Exception:
            return True  # Err on the side of caution
```

### **Step 3: API Endpoints Enhancement** (Day 6-8)

#### **Updated Media Upload Endpoint**
```python
# Update main.py
from video_processing.video_processor import VideoProcessor
from video_processing.video_security import VideoSecurityValidator

video_processor = VideoProcessor()
video_security = VideoSecurityValidator()

@app.post("/api/media/upload")
async def upload_media(
    file: UploadFile = File(...),
    title: str = Form(None),
    description: str = Form(None),
    is_public: bool = Form(False),
    current_user: AuthenticatedUser = Depends(get_current_user),
    app_db: AppDatabaseManager = Depends(get_app_db_manager)
):
    """
    Upload photo or video with comprehensive processing.
    
    Supports:
    - Photos: JPEG, PNG, GIF, WebP
    - Videos: MP4, AVI, MOV, WebM, MKV
    """
    
    try:
        # 1. Determine media type
        media_type = 'video' if file.content_type.startswith('video/') else 'photo'
        
        # 2. Basic validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # 3. WAF validation
        waf_result = await validate_file_upload_waf(file.filename, await file.read())
        if not waf_result.is_safe:
            raise HTTPException(status_code=400, detail=f"Security check failed: {waf_result.reason}")
        
        # Reset file pointer
        await file.seek(0)
        
        # 4. Save temporary file
        temp_file_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            content = await file.read()
            temp_file.write(content)
        
        try:
            # 5. Process based on media type
            if media_type == 'video':
                return await process_video_upload(
                    temp_file_path, file, title, description, 
                    is_public, current_user, app_db
                )
            else:
                return await process_photo_upload(
                    temp_file_path, file, title, description,
                    is_public, current_user, app_db
                )
        
        finally:
            # Cleanup temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        await log_security_event(
            severity=AlertSeverity.MEDIUM,
            threat_type=ThreatType.UPLOAD_SECURITY,
            source_ip=request.client.host,
            user_id=current_user.user_uuid,
            description=f"Media upload failed: {str(e)}"
        )
        raise HTTPException(status_code=500, detail="Media upload failed")

async def process_video_upload(temp_file_path: str, file: UploadFile,
                             title: str, description: str, is_public: bool,
                             current_user: AuthenticatedUser,
                             app_db: AppDatabaseManager):
    """Process video upload with transcoding and thumbnail generation."""
    
    # 1. Analyze video metadata
    video_metadata = await video_processor.analyze_video(temp_file_path)
    
    # 2. Security validation
    is_safe, security_message = await video_security.validate_video_security(
        temp_file_path, video_metadata
    )
    
    if not is_safe:
        raise HTTPException(status_code=400, detail=security_message)
    
    # 3. Generate unique filename
    file_extension = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # 4. Store original video
    storage_path = await file_storage.store_file(content, unique_filename)
    
    # 5. Generate thumbnail
    thumbnail_filename = f"{uuid.uuid4()}_thumb.jpg"
    thumbnail_path = f"/tmp/{thumbnail_filename}"
    
    thumbnail_success = await video_processor.generate_thumbnail(
        temp_file_path, thumbnail_path, timestamp=min(1.0, video_metadata['duration'] / 4)
    )
    
    thumbnail_storage_path = None
    if thumbnail_success:
        with open(thumbnail_path, 'rb') as thumb_file:
            thumbnail_content = thumb_file.read()
        thumbnail_storage_path = await file_storage.store_file(
            thumbnail_content, thumbnail_filename
        )
        os.remove(thumbnail_path)
    
    # 6. Create media record
    media_record = Media(
        user_uuid=current_user.user_uuid,
        user_email=current_user.email,
        filename=unique_filename,
        original_filename=file.filename,
        content_type=file.content_type,
        file_size=len(content),
        storage_path=storage_path,
        media_type='video',
        title=title,
        description=description,
        is_public=is_public,
        duration=int(video_metadata.get('duration', 0)),
        video_codec=video_metadata.get('video_codec'),
        audio_codec=video_metadata.get('audio_codec'),
        resolution=video_metadata.get('resolution'),
        framerate=video_metadata.get('framerate'),
        bitrate=video_metadata.get('bitrate'),
        width=video_metadata.get('width'),
        height=video_metadata.get('height'),
        thumbnail_path=thumbnail_storage_path,
        processing_status='completed'
    )
    
    # 7. Save to database
    async with app_db.get_session() as session:
        session.add(media_record)
        await session.commit()
        await session.refresh(media_record)
    
    # 8. Log audit event
    if AUDIT_TRAIL_AVAILABLE:
        await log_audit(
            action="video_upload",
            resource_type="media",
            resource_id=str(media_record.id),
            user_id=current_user.user_uuid,
            details={
                "filename": file.filename,
                "duration": video_metadata.get('duration'),
                "resolution": video_metadata.get('resolution'),
                "file_size": len(content)
            }
        )
    
    return {
        "id": media_record.id,
        "message": "Video uploaded and processed successfully",
        "media_type": "video",
        "duration": video_metadata.get('duration'),
        "resolution": video_metadata.get('resolution'),
        "thumbnail_available": thumbnail_success,
        "processing_status": "completed"
    }
```

#### **Video Streaming Endpoints**
```python
# New streaming endpoints
@app.get("/api/media/{media_id}/stream")
async def stream_video(
    media_id: int,
    range: Optional[str] = Header(None),
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
    app_db: AppDatabaseManager = Depends(get_app_db_manager)
):
    """Stream video with range support for progressive download."""
    
    # Get media record
    async with app_db.get_session() as session:
        result = await session.execute(
            select(Media).where(Media.id == media_id)
        )
        media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if media.media_type != 'video':
        raise HTTPException(status_code=400, detail="Not a video file")
    
    # Check access permissions
    if not media.is_public and (not current_user or current_user.user_uuid != media.user_uuid):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get file path
    file_path = await file_storage.get_file_path(media.storage_path)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Handle range requests for video streaming
    file_size = os.path.getsize(file_path)
    
    if range:
        # Parse range header
        range_match = re.match(r'bytes=(\d+)-(\d*)', range)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            
            if start >= file_size or end >= file_size:
                raise HTTPException(status_code=416, detail="Range not satisfiable")
            
            # Stream partial content
            def generate_chunk():
                with open(file_path, 'rb') as f:
                    f.seek(start)
                    remaining = end - start + 1
                    while remaining > 0:
                        chunk_size = min(8192, remaining)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
            
            headers = {
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(end - start + 1),
                'Content-Type': media.content_type
            }
            
            return StreamingResponse(
                generate_chunk(),
                status_code=206,
                headers=headers
            )
    
    # Stream full video
    def generate_full():
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
    
    headers = {
        'Content-Length': str(file_size),
        'Accept-Ranges': 'bytes',
        'Content-Type': media.content_type
    }
    
    return StreamingResponse(generate_full(), headers=headers)

@app.get("/api/media/{media_id}/thumbnail")
async def get_video_thumbnail(
    media_id: int,
    current_user: Optional[AuthenticatedUser] = Depends(get_current_user_optional),
    app_db: AppDatabaseManager = Depends(get_app_db_manager)
):
    """Get video thumbnail image."""
    
    # Get media record
    async with app_db.get_session() as session:
        result = await session.execute(
            select(Media).where(Media.id == media_id)
        )
        media = result.scalar_one_or_none()
    
    if not media or media.media_type != 'video':
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check access permissions
    if not media.is_public and (not current_user or current_user.user_uuid != media.user_uuid):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not media.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    
    # Get thumbnail file
    thumbnail_path = await file_storage.get_file_path(media.thumbnail_path)
    
    if not os.path.exists(thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail file not found")
    
    return FileResponse(
        thumbnail_path,
        media_type="image/jpeg",
        filename=f"thumbnail_{media_id}.jpg"
    )
```

### **Step 4: Testing & Validation** (Day 9-10)

#### **Video Upload Test Script**
```bash
# api-integration-tests/test-video-upload.sh
#!/bin/bash

echo "🎬 Testing Video Upload and Processing"
echo "======================================"

BASE_URL="http://localhost:8000"
TEST_EMAIL="videotest@example.com"
TEST_PASSWORD="VideoTest123!"

# 1. Register and login
echo "📝 Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")

echo "🔑 Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/login" \
  -F "username=$TEST_EMAIL" \
  -F "password=$TEST_PASSWORD")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ]; then
    echo "❌ Login failed"
    exit 1
fi

echo "✅ Authentication successful"

# 2. Test video upload
echo "🎬 Testing video upload..."

# Create a small test video (requires ffmpeg)
ffmpeg -f lavfi -i testsrc=duration=5:size=320x240:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=5 \
       -c:v libx264 -c:a aac -shortest test_video.mp4

UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/media/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_video.mp4" \
  -F "title=Test Video Upload" \
  -F "description=Testing video processing pipeline" \
  -F "is_public=false")

echo "Upload Response: $UPLOAD_RESPONSE"

VIDEO_ID=$(echo $UPLOAD_RESPONSE | jq -r '.id')

if [ "$VIDEO_ID" = "null" ]; then
    echo "❌ Video upload failed"
    exit 1
fi

echo "✅ Video uploaded successfully (ID: $VIDEO_ID)"

# 3. Test video streaming
echo "🎥 Testing video streaming..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "$BASE_URL/api/media/$VIDEO_ID/stream" \
     --output streamed_video.mp4

if [ -f "streamed_video.mp4" ]; then
    echo "✅ Video streaming successful"
else
    echo "❌ Video streaming failed"
fi

# 4. Test thumbnail generation
echo "🖼️ Testing thumbnail generation..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "$BASE_URL/api/media/$VIDEO_ID/thumbnail" \
     --output video_thumbnail.jpg

if [ -f "video_thumbnail.jpg" ]; then
    echo "✅ Thumbnail generation successful"
else
    echo "❌ Thumbnail generation failed"
fi

# 5. Test media listing
echo "📋 Testing media listing..."
MEDIA_LIST=$(curl -s -H "Authorization: Bearer $TOKEN" \
                  "$BASE_URL/api/media/")

echo "Media List: $MEDIA_LIST"

# Cleanup
rm -f test_video.mp4 streamed_video.mp4 video_thumbnail.jpg

echo "🎉 Video support testing completed!"
```

## 📊 **Success Metrics**

- ✅ Support for 5+ video formats (MP4, AVI, MOV, WebM, MKV)
- ✅ Video upload and processing < 30 seconds for typical files
- ✅ Thumbnail generation success rate > 95%
- ✅ Video streaming with range request support
- ✅ Security validation preventing malicious video uploads
- ✅ Database migration completed without data loss

## 🔗 **Next Phase Integration**

This video support implementation prepares for:
- **Object Storage**: Videos will be stored in scalable cloud storage
- **Deduplication**: Video content-addressable storage with user metadata
- **Advanced Features**: Video transcoding, multiple quality variants

## 📋 **Dependencies**

### **System Requirements**
```bash
# Install FFmpeg for video processing
apt-get update && apt-get install -y ffmpeg

# Python dependencies
pip install python-multipart asyncio-subprocess
```

### **Container Updates**
```dockerfile
# Update Dockerfile
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# ... rest of Dockerfile
```

This implementation transforms PhotoShare into a comprehensive media platform while maintaining all existing security features and adding video-specific security validations.