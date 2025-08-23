-- Authentication Database Initialization Script
-- =====================================================
-- This script initializes the authentication database for the separated architecture

-- Create database extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone
SET timezone = 'UTC';

-- Create custom types for authentication
DO $$ BEGIN
    CREATE TYPE user_status AS ENUM ('active', 'inactive', 'locked', 'pending_verification');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN  
    CREATE TYPE session_status AS ENUM ('active', 'expired', 'revoked');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE audit_event_type AS ENUM (
        'user_registered', 'user_verified', 'user_login', 'user_logout', 
        'password_changed', '2fa_enabled', '2fa_disabled', 'sso_login',
        'account_locked', 'account_unlocked', 'permission_granted', 'permission_revoked'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create performance indexes after table creation
-- This will be handled by the SQLAlchemy models

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant permissions to application user
GRANT USAGE ON SCHEMA public TO auth_user;
GRANT CREATE ON SCHEMA public TO auth_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO auth_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO auth_user;

-- Set default permissions for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO auth_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO auth_user;

-- Create initial admin role (will be managed by the application)
-- Tables will be created by SQLAlchemy migrations

COMMENT ON DATABASE photo_share_auth IS 'PhotoShare Authentication Service Database - Separated Architecture';