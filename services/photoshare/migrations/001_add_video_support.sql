-- Database Migration: Add Video Support to PhotoShare
-- =====================================================
-- Migration: 001_add_video_support
-- Date: August 23, 2025
-- Description: Transform photos table to media table with video support
-- Estimated time: < 1 minute for typical datasets

BEGIN;

-- 1. Rename table for broader media support
ALTER TABLE photos RENAME TO media;

-- 2. Add video-specific columns
ALTER TABLE media ADD COLUMN media_type VARCHAR(10) NOT NULL DEFAULT 'photo';
ALTER TABLE media ADD COLUMN duration INTEGER; -- Video duration in seconds
ALTER TABLE media ADD COLUMN video_codec VARCHAR(20); -- H.264, H.265, VP9, AV1
ALTER TABLE media ADD COLUMN audio_codec VARCHAR(20); -- AAC, MP3, Opus
ALTER TABLE media ADD COLUMN resolution VARCHAR(20); -- 1080p, 720p, 4K
ALTER TABLE media ADD COLUMN framerate DECIMAL(5,2); -- 30.0, 60.0 fps
ALTER TABLE media ADD COLUMN bitrate INTEGER; -- Video bitrate in kbps
ALTER TABLE media ADD COLUMN thumbnail_path VARCHAR(500); -- Video thumbnail storage
ALTER TABLE media ADD COLUMN processing_status VARCHAR(20) DEFAULT 'completed'; -- pending, processing, completed, failed
ALTER TABLE media ADD COLUMN transcoded_variants JSON; -- Different quality variants

-- 3. Create indexes for efficient queries
CREATE INDEX idx_media_type ON media(media_type);
CREATE INDEX idx_processing_status ON media(processing_status);
CREATE INDEX idx_duration ON media(duration) WHERE media_type = 'video';
CREATE INDEX idx_resolution ON media(resolution) WHERE media_type = 'video';

-- 4. Update existing records to be photos (for backward compatibility)
UPDATE media SET media_type = 'photo' WHERE media_type = 'photo';

-- 5. Add constraints for data integrity
ALTER TABLE media ADD CONSTRAINT check_media_type 
    CHECK (media_type IN ('photo', 'video'));

ALTER TABLE media ADD CONSTRAINT check_processing_status 
    CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'));

-- Ensure video-specific fields are consistent
ALTER TABLE media ADD CONSTRAINT check_video_duration 
    CHECK (
        (media_type = 'photo' AND duration IS NULL) OR 
        (media_type = 'video' AND duration >= 0)
    );

-- 6. Update sequences and permissions if needed
-- (Assuming standard PostgreSQL setup)

COMMIT;

-- Verification queries (optional - run after migration)
-- SELECT media_type, COUNT(*) FROM media GROUP BY media_type;
-- SELECT * FROM media WHERE media_type = 'video' LIMIT 5;