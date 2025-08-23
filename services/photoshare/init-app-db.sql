-- Application Database Initialization Script  
-- =====================================================
-- This script initializes the application database for photo sharing functionality

-- Create database extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Set timezone
SET timezone = 'UTC';

-- Create custom types for application
DO $$ BEGIN
    CREATE TYPE photo_status AS ENUM ('processing', 'active', 'archived', 'deleted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE share_type AS ENUM ('public', 'private', 'link_only', 'password_protected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE comment_status AS ENUM ('pending', 'approved', 'flagged', 'deleted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE analytics_event_type AS ENUM (
        'photo_view', 'photo_download', 'photo_share', 'photo_like', 
        'album_view', 'search_performed', 'comment_added'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant permissions to application user
GRANT USAGE ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Set default permissions for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;

-- Create full-text search configuration for photo search
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS photo_search (COPY = english);

-- Tables will be created by SQLAlchemy models
-- Performance indexes will be created by the application

COMMENT ON DATABASE photo_share_app IS 'PhotoShare Application Service Database - Photo and content management';