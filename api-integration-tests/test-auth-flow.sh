#!/bin/bash

# Authentication Flow Test Script
# Tests user registration, login, and authenticated endpoint access

set -e

# Configuration
BASE_URL="http://localhost:8000"
TEST_EMAIL="test-$(date +%s)@example.com"
TEST_PASSWORD="TestPassword123"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Testing Authentication Flow ===${NC}"
echo -e "${BLUE}Test Email: $TEST_EMAIL${NC}"
echo ""

# Step 1: Register User
echo -e "${GREEN}Step 1: Registering user...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")

echo "Registration Response: $REGISTER_RESPONSE"

if echo "$REGISTER_RESPONSE" | jq -e '.email' > /dev/null; then
    echo -e "${GREEN}✓ User registration successful${NC}"
    USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.id')
    echo -e "${GREEN}  User ID: $USER_ID${NC}"
else
    echo -e "${RED}✗ User registration failed${NC}"
    exit 1
fi

# Step 2: Login User
echo -e "${GREEN}Step 2: Logging in user...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/login" \
  -F "username=$TEST_EMAIL" \
  -F "password=$TEST_PASSWORD")

echo "Login Response: $LOGIN_RESPONSE"

if echo "$LOGIN_RESPONSE" | jq -e '.access_token' > /dev/null; then
    echo -e "${GREEN}✓ User login successful${NC}"
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
    TOKEN_TYPE=$(echo "$LOGIN_RESPONSE" | jq -r '.token_type')
    echo -e "${GREEN}  Token Type: $TOKEN_TYPE${NC}"
    echo -e "${GREEN}  Access Token: ${ACCESS_TOKEN:0:50}...${NC}"
else
    echo -e "${RED}✗ User login failed${NC}"
    exit 1
fi

# Step 3: Test Protected Endpoint
echo -e "${GREEN}Step 3: Testing protected endpoint access...${NC}"
USER_INFO=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$BASE_URL/api/users/me")

echo "User Info Response: $USER_INFO"

if echo "$USER_INFO" | jq -e '.email' > /dev/null; then
    echo -e "${GREEN}✓ Protected endpoint access successful${NC}"
    RETURNED_EMAIL=$(echo "$USER_INFO" | jq -r '.email')
    if [ "$RETURNED_EMAIL" = "$TEST_EMAIL" ]; then
        echo -e "${GREEN}  ✓ Email matches: $RETURNED_EMAIL${NC}"
    else
        echo -e "${RED}  ✗ Email mismatch: expected $TEST_EMAIL, got $RETURNED_EMAIL${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Protected endpoint access failed${NC}"
    exit 1
fi

# Step 4: Test Photo List (should be empty for new user)
echo -e "${GREEN}Step 4: Testing photo list access...${NC}"
PHOTOS_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$BASE_URL/api/photos/")

echo "Photos Response: $PHOTOS_RESPONSE"

if echo "$PHOTOS_RESPONSE" | jq -e '. | length' > /dev/null; then
    PHOTO_COUNT=$(echo "$PHOTOS_RESPONSE" | jq '. | length')
    echo -e "${GREEN}✓ Photo list access successful${NC}"
    echo -e "${GREEN}  Photo count: $PHOTO_COUNT${NC}"
else
    echo -e "${RED}✗ Photo list access failed${NC}"
    exit 1
fi

# Step 5: Test Public Photos
echo -e "${GREEN}Step 5: Testing public photos access...${NC}"
PUBLIC_PHOTOS=$(curl -s "$BASE_URL/api/photos/public")

if echo "$PUBLIC_PHOTOS" | jq -e '. | length' > /dev/null; then
    PUBLIC_COUNT=$(echo "$PUBLIC_PHOTOS" | jq '. | length')
    echo -e "${GREEN}✓ Public photos access successful${NC}"
    echo -e "${GREEN}  Public photo count: $PUBLIC_COUNT${NC}"
else
    echo -e "${RED}✗ Public photos access failed${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${BLUE}=== Authentication Flow Test Summary ===${NC}"
echo -e "${GREEN}✓ User Registration: $TEST_EMAIL${NC}"
echo -e "${GREEN}✓ User Login: JWT token obtained${NC}"
echo -e "${GREEN}✓ Protected Endpoint: /api/users/me${NC}"
echo -e "${GREEN}✓ Photo List Access: /api/photos/${NC}"
echo -e "${GREEN}✓ Public Photos Access: /api/photos/public${NC}"
echo ""
echo -e "${GREEN}🎉 All authentication tests PASSED!${NC}"
echo ""
echo -e "${BLUE}To use this token for further testing:${NC}"
echo "export AUTH_TOKEN=\"$ACCESS_TOKEN\""
echo "curl -H \"Authorization: Bearer \$AUTH_TOKEN\" $BASE_URL/api/users/me"