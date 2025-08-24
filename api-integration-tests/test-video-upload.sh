#!/bin/bash
#
# Video Upload and Streaming Test Script
# =====================================
#
# Tests the complete video upload and streaming workflow:
# 1. User registration and authentication
# 2. Video file upload with validation
# 3. Video metadata retrieval
# 4. Video thumbnail generation
# 5. Video streaming with range requests
#
# Requirements:
# - PhotoShare service running on localhost:8000
# - FFmpeg installed for video processing
# - Sample video file for testing
#

set -e

# Configuration
AUTH_URL="http://localhost:8001"
APP_URL="http://localhost:8000"
TEST_EMAIL="video-test@example.com"
TEST_PASSWORD="VideoTest123!"
TEST_VIDEO_FILE="${1:-sample_video.mp4}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_service() {
    log_info "Checking PhotoShare services health..."
    if curl -s "$APP_URL/health" | grep -q "healthy"; then
        log_success "App service is running"
    else
        log_error "App service is not available"
        exit 1
    fi
    
    if curl -s "$AUTH_URL/health" | grep -q "healthy"; then
        log_success "Auth service is running"
    else
        log_error "Auth service is not available"
        exit 1
    fi
}

create_test_video() {
    if [ ! -f "$TEST_VIDEO_FILE" ]; then
        log_info "Creating test video file..."
        if command -v ffmpeg &> /dev/null; then
            # Create a 10-second test video with audio
            ffmpeg -f lavfi -i testsrc2=duration=10:size=1280x720:rate=30 \
                   -f lavfi -i sine=frequency=1000:duration=10 \
                   -c:v libx264 -preset fast -c:a aac \
                   -y "$TEST_VIDEO_FILE" 2>/dev/null
            log_success "Test video created: $TEST_VIDEO_FILE"
        else
            log_error "FFmpeg not found. Please provide a test video file or install FFmpeg."
            exit 1
        fi
    else
        log_info "Using existing video file: $TEST_VIDEO_FILE"
    fi
}

register_user() {
    log_info "Registering test user..."
    
    REGISTER_RESPONSE=$(curl -s -X POST "$AUTH_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")
    
    if echo "$REGISTER_RESPONSE" | grep -q "user_id\|already exists"; then
        log_success "User registration completed"
    else
        log_warning "Registration response: $REGISTER_RESPONSE"
    fi
}

verify_user() {
    log_info "Requesting email verification..."
    
    VERIFY_REQUEST_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/request-verification" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"$TEST_EMAIL\"}")
    
    # Extract verification link (this would normally be sent via email)
    VERIFICATION_SECRET=$(echo "$VERIFY_REQUEST_RESPONSE" | grep -o 'verify/[^"]*' | sed 's/verify\///')
    
    if [ -n "$VERIFICATION_SECRET" ]; then
        log_info "Verifying user account..."
        curl -s "$BASE_URL/api/users/verify/$VERIFICATION_SECRET" > /dev/null
        log_success "User account verified"
    else
        log_warning "Could not extract verification secret"
    fi
}

login_user() {
    log_info "Logging in user..."
    
    LOGIN_RESPONSE=$(curl -s -X POST "$AUTH_URL/api/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$TEST_EMAIL&password=$TEST_PASSWORD")
    
    JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$JWT_TOKEN" ]; then
        log_success "User login successful"
        echo "$JWT_TOKEN"
    else
        log_error "Login failed: $LOGIN_RESPONSE"
        exit 1
    fi
}

upload_video() {
    local token=$1
    log_info "Uploading video file..."
    
    UPLOAD_RESPONSE=$(curl -s -X POST "$APP_URL/api/media/upload" \
        -H "Authorization: Bearer $token" \
        -F "file=@$TEST_VIDEO_FILE" \
        -F "title=Test Video Upload" \
        -F "description=Automated test video upload" \
        -F "is_public=true")
    
    MEDIA_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"media_id":[0-9]*' | cut -d':' -f2)
    
    if [ -n "$MEDIA_ID" ]; then
        log_success "Video uploaded successfully (Media ID: $MEDIA_ID)"
        echo "$MEDIA_ID"
    else
        log_error "Video upload failed: $UPLOAD_RESPONSE"
        exit 1
    fi
}

get_video_metadata() {
    local token=$1
    local media_id=$2
    log_info "Retrieving video metadata..."
    
    METADATA_RESPONSE=$(curl -s -H "Authorization: Bearer $token" \
        "$APP_URL/api/media/$media_id")
    
    if echo "$METADATA_RESPONSE" | grep -q '"media_type":"video"'; then
        log_success "Video metadata retrieved"
        
        # Extract key metadata
        DURATION=$(echo "$METADATA_RESPONSE" | grep -o '"duration":[0-9.]*' | cut -d':' -f2)
        WIDTH=$(echo "$METADATA_RESPONSE" | grep -o '"width":[0-9]*' | cut -d':' -f2)
        HEIGHT=$(echo "$METADATA_RESPONSE" | grep -o '"height":[0-9]*' | cut -d':' -f2)
        VIDEO_CODEC=$(echo "$METADATA_RESPONSE" | grep -o '"video_codec":"[^"]*"' | cut -d'"' -f4)
        
        log_info "Video details: ${WIDTH}x${HEIGHT}, ${DURATION}s, codec: $VIDEO_CODEC"
    else
        log_error "Failed to retrieve video metadata: $METADATA_RESPONSE"
        exit 1
    fi
}

test_video_thumbnail() {
    local media_id=$1
    log_info "Testing video thumbnail generation..."
    
    THUMBNAIL_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        "$APP_URL/api/media/$media_id/thumbnail")
    
    if [ "$THUMBNAIL_RESPONSE" = "200" ]; then
        log_success "Video thumbnail is available"
    else
        log_warning "Video thumbnail not available (HTTP $THUMBNAIL_RESPONSE)"
    fi
}

test_video_streaming() {
    local media_id=$1
    log_info "Testing video streaming..."
    
    # Test full video request
    STREAM_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        "$APP_URL/api/media/$media_id/stream")
    
    if [ "$STREAM_RESPONSE" = "200" ]; then
        log_success "Video streaming works (full file)"
    else
        log_error "Video streaming failed (HTTP $STREAM_RESPONSE)"
        return 1
    fi
    
    # Test range request
    RANGE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Range: bytes=0-1023" \
        "$APP_URL/api/media/$media_id/stream")
    
    if [ "$RANGE_RESPONSE" = "206" ]; then
        log_success "Video range requests work (HTTP 206 Partial Content)"
    else
        log_warning "Video range requests not working properly (HTTP $RANGE_RESPONSE)"
    fi
}

cleanup() {
    log_info "Cleaning up test files..."
    if [ -f "$TEST_VIDEO_FILE" ] && [ "$1" = "created" ]; then
        rm -f "$TEST_VIDEO_FILE"
        log_success "Test video file removed"
    fi
}

# Main execution
main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Video Upload and Streaming Test${NC}"
    echo -e "${BLUE}================================${NC}"
    
    # Check prerequisites
    check_service
    
    VIDEO_CREATED=""
    if [ ! -f "$TEST_VIDEO_FILE" ]; then
        create_test_video
        VIDEO_CREATED="created"
    fi
    
    # Authentication flow
    register_user
    # Skip verification for test - login directly
    JWT_TOKEN=$(login_user)
    
    # Video operations
    MEDIA_ID=$(upload_video "$JWT_TOKEN")
    get_video_metadata "$JWT_TOKEN" "$MEDIA_ID"
    test_video_thumbnail "$MEDIA_ID"
    test_video_streaming "$MEDIA_ID"
    
    # Cleanup
    cleanup "$VIDEO_CREATED"
    
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}All video tests completed successfully!${NC}"
    echo -e "${GREEN}================================${NC}"
}

# Error handling
trap 'log_error "Test failed at line $LINENO"' ERR

# Run main function
main "$@"