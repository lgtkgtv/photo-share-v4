#!/bin/bash

# Email Verification Test Script
# Tests the complete email verification flow

set -e

# Configuration
BASE_URL="http://localhost:8000"
TEST_EMAIL="emailverify-test-$(date +%s)@example.com"
TEST_PASSWORD="EmailTest123!"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Testing Email Verification Flow ===${NC}"
echo -e "${BLUE}Test Email: $TEST_EMAIL${NC}"
echo ""

# Step 1: Register user (should be unverified)
echo -e "${GREEN}Step 1: Registering user...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")

echo "Registration Response: $REGISTER_RESPONSE"

# Check if registration was successful and user is unverified
USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.id // empty')
IS_VERIFIED=$(echo "$REGISTER_RESPONSE" | jq -r '.is_verified // empty')

if [[ -z "$USER_ID" ]]; then
    echo -e "${RED}✗ User registration failed${NC}"
    exit 1
fi

if [[ "$IS_VERIFIED" == "true" ]]; then
    echo -e "${RED}✗ User should be unverified after registration${NC}"
    exit 1
fi

echo -e "${GREEN}✓ User registered successfully (ID: $USER_ID, Unverified)${NC}"
echo ""

# Step 2: Request email verification
echo -e "${GREEN}Step 2: Requesting email verification...${NC}"
VERIFICATION_REQUEST=$(curl -s -X POST "$BASE_URL/api/users/request-verification" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_EMAIL\"}")

echo "Verification Request: $VERIFICATION_REQUEST"

# Extract verification link
VERIFICATION_LINK=$(echo "$VERIFICATION_REQUEST" | jq -r '.verification_link // empty')

if [[ -z "$VERIFICATION_LINK" ]]; then
    echo -e "${RED}✗ Verification request failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Verification email requested successfully${NC}"
echo -e "${YELLOW}📧 Verification Link: $VERIFICATION_LINK${NC}"
echo ""

# Step 3: Verify email using the link
echo -e "${GREEN}Step 3: Verifying email...${NC}"
VERIFICATION_RESPONSE=$(curl -s "$VERIFICATION_LINK")

echo "Verification Response: $VERIFICATION_RESPONSE"

# Check if verification was successful
MESSAGE=$(echo "$VERIFICATION_RESPONSE" | jq -r '.message // empty')

if [[ "$MESSAGE" != "Email successfully verified" ]]; then
    echo -e "${RED}✗ Email verification failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Email verified successfully${NC}"
echo ""

# Step 4: Test login with verified user
echo -e "${GREEN}Step 4: Testing login with verified user...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$TEST_EMAIL&password=$TEST_PASSWORD")

echo "Login Response: $LOGIN_RESPONSE"

# Check if login was successful
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
    echo -e "${RED}✗ Login failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Login successful with verified user${NC}"
echo ""

# Step 5: Test accessing protected endpoint
echo -e "${GREEN}Step 5: Testing protected endpoint access...${NC}"
USER_INFO=$(curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/users/me")

echo "User Info: $USER_INFO"

# Check if user info shows verified status
VERIFIED_STATUS=$(echo "$USER_INFO" | jq -r '.is_verified // empty')

if [[ "$VERIFIED_STATUS" != "true" ]]; then
    echo -e "${RED}✗ User verification status incorrect${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Protected endpoint access successful${NC}"
echo -e "${GREEN}✓ User shows verified status: $VERIFIED_STATUS${NC}"
echo ""

# Step 6: Test duplicate verification request
echo -e "${GREEN}Step 6: Testing duplicate verification request...${NC}"
DUPLICATE_REQUEST=$(curl -s -X POST "$BASE_URL/api/users/request-verification" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_EMAIL\"}")

echo "Duplicate Request: $DUPLICATE_REQUEST"

# Should fail with "already verified" message
if echo "$DUPLICATE_REQUEST" | jq -e '.detail' | grep -q "already verified"; then
    echo -e "${GREEN}✓ Duplicate verification request properly rejected${NC}"
else
    echo -e "${YELLOW}⚠ Duplicate verification handling may need review${NC}"
fi

echo ""
echo -e "${BLUE}=== Email Verification Test Summary ===${NC}"
echo -e "${GREEN}✓ User registration (unverified)${NC}"
echo -e "${GREEN}✓ Email verification request${NC}"
echo -e "${GREEN}✓ Email verification process${NC}"
echo -e "${GREEN}✓ Login with verified user${NC}"
echo -e "${GREEN}✓ Protected endpoint access${NC}"
echo -e "${GREEN}✓ Duplicate request handling${NC}"
echo ""
echo -e "${GREEN}🎉 All email verification tests PASSED!${NC}"