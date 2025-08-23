#!/bin/bash
# Web Application Firewall (WAF) Testing Script
# ============================================

set -e

echo "🛡️  Testing PhotoShare WAF Protection"
echo "===================================="

# Configuration
SERVICE_URL="http://localhost:8000"
TEST_COUNT=0
PASS_COUNT=0

# Test function
test_waf() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local payload="$4"
    local expected_status="$5"
    local description="$6"
    
    TEST_COUNT=$((TEST_COUNT + 1))
    
    echo ""
    echo "📋 Test ${TEST_COUNT}: ${test_name}"
    echo "   Description: ${description}"
    
    # Make request
    if [[ "$method" == "POST" ]]; then
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$SERVICE_URL$endpoint" 2>/dev/null || echo "HTTP_STATUS:000")
    else
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
            "$SERVICE_URL$endpoint" 2>/dev/null || echo "HTTP_STATUS:000")
    fi
    
    # Extract status code
    status_code=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    body=$(echo "$response" | head -n -1)
    
    # Check result
    if [[ "$status_code" == "$expected_status" ]]; then
        echo "   ✅ PASS - Status: $status_code (expected $expected_status)"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "   ❌ FAIL - Status: $status_code (expected $expected_status)"
        if [[ ! -z "$body" ]]; then
            echo "   Response: $body" | cut -c 1-100
        fi
    fi
}

# Check if service is running
echo ""
echo "🔍 1. Checking if PhotoShare service is running..."
if curl -s "$SERVICE_URL/health" > /dev/null 2>&1; then
    echo "✅ PhotoShare service is running"
else
    echo "❌ PhotoShare service is not running"
    echo "   Please start the service with: docker compose up"
    exit 1
fi

echo ""
echo "🧪 Starting WAF Security Tests..."
echo "================================="

# Test 1: Normal request should pass
test_waf "Normal Request" "GET" "/health" "" "200" "Normal health check should pass"

# Test 2: SQL Injection in query parameter
test_waf "SQL Injection - Query Param" "GET" "/api/photos?id=1' OR '1'='1" "" "403" "SQL injection in query parameter should be blocked"

# Test 3: SQL Injection in URL path
test_waf "SQL Injection - URL Path" "GET" "/api/photos/1' UNION SELECT * FROM users--" "" "403" "SQL injection in URL path should be blocked"

# Test 4: XSS attempt in query parameter
test_waf "XSS Attack" "GET" "/api/photos?search=<script>alert('xss')</script>" "" "403" "XSS script in query should be blocked"

# Test 5: Path traversal attempt
test_waf "Path Traversal" "GET" "/api/photos/../../../etc/passwd" "" "403" "Path traversal should be blocked"

# Test 6: Command injection attempt
test_waf "Command Injection" "GET" "/api/photos?cmd=ls;cat /etc/passwd" "" "403" "Command injection should be blocked"

# Test 7: Honeypot path access
test_waf "Honeypot Access" "GET" "/admin" "" "403" "Access to honeypot path should be blocked"

# Test 8: Another honeypot path
test_waf "Honeypot Access 2" "GET" "/.env" "" "403" "Access to .env file should be blocked"

# Test 9: SQL injection in POST body
test_waf "SQL Injection - POST Body" "POST" "/api/photos/upload" '{"title": "test"; DROP TABLE photos; --"}' "403" "SQL injection in POST body should be blocked"

# Test 10: XSS in POST body
test_waf "XSS - POST Body" "POST" "/api/users/register" '{"email": "test@test.com", "password": "<script>alert(1)</script>"}' "403" "XSS in POST body should be blocked"

# Test 11: Rate limiting simulation (commented out as it's time-intensive)
# echo ""
# echo "⏱️  Testing rate limiting (this may take time)..."
# for i in {1..105}; do
#     curl -s "$SERVICE_URL/health" > /dev/null &
# done
# wait
# test_waf "Rate Limiting" "GET" "/health" "" "429" "Rate limit should be enforced after 100 requests"

# Test 12: Normal API access (should still work)
test_waf "Normal API Access" "GET" "/docs" "" "200" "Normal API documentation access should work"

echo ""
echo "🔍 Testing WAF with malicious User-Agent strings..."

# Test with malicious user agents
curl -s -H "User-Agent: sqlmap/1.0" "$SERVICE_URL/health" | grep -q "blocked" && echo "✅ Malicious User-Agent blocked" || echo "❌ Malicious User-Agent not blocked"

echo ""
echo "📊 WAF Test Results Summary"
echo "=========================="
echo "   Total Tests: $TEST_COUNT"
echo "   Passed: $PASS_COUNT"
echo "   Failed: $((TEST_COUNT - PASS_COUNT))"

if [[ $PASS_COUNT -eq $TEST_COUNT ]]; then
    echo "   🎉 ALL TESTS PASSED!"
    echo "   ✅ WAF protection is working correctly"
else
    echo "   ⚠️  Some tests failed"
    echo "   🔧 Review WAF configuration"
fi

# Success rate
success_rate=$(( (PASS_COUNT * 100) / TEST_COUNT ))
echo "   Success Rate: ${success_rate}%"

echo ""
echo "🔧 Manual Testing Commands:"
echo "=========================="
echo "# Test SQL injection manually:"
echo "curl '$SERVICE_URL/api/photos?id=1%27%20OR%20%271%27=%271'"
echo ""
echo "# Test XSS manually:"  
echo "curl '$SERVICE_URL/api/photos?search=%3Cscript%3Ealert%281%29%3C%2Fscript%3E'"
echo ""
echo "# Test path traversal manually:"
echo "curl '$SERVICE_URL/api/photos/../../../etc/passwd'"
echo ""
echo "# Test with malicious user agent:"
echo "curl -H 'User-Agent: sqlmap/1.0' '$SERVICE_URL/health'"
echo ""
echo "# Check WAF statistics (requires authentication):"
echo "curl -H 'Authorization: Bearer YOUR_TOKEN' '$SERVICE_URL/api/security/waf-status'"

exit $((TEST_COUNT - PASS_COUNT))