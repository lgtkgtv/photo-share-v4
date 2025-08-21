# 🧪 Photo Share Service - Comprehensive Test Plan

**Version**: 2.3.0-monitoring  
**Service**: Photo Sharing Service with Email Verification  
**Last Updated**: August 20, 2025 - 11:55 AM PST  

## 🎯 Test Objectives

This test plan validates the complete functionality of the Photo Share Service, ensuring all components work correctly in both development and production environments.

## 📋 Test Categories

### 1. **Health & Status Tests**
Verify basic service health and API availability.

### 2. **Authentication & Authorization Tests**
Test user registration, email verification, login, JWT token handling, and protected endpoint access.

### 3. **Photo Management Tests**
Validate photo upload, retrieval, listing, and metadata operations.

### 4. **Security Tests**
Verify security controls, rate limiting, input validation, and file security.

### 5. **Performance & Monitoring Tests**
Test caching, query optimization, and metrics collection.

### 6. **Database Integration Tests**
Validate database operations, transactions, and data integrity.

---

## 🚀 Quick Validation Tests (5-10 minutes)

These tests provide rapid verification that the service is functioning correctly.

### Test Set A: Service Health
```bash
# 1. Health Check
curl -f http://localhost:8000/health
# Expected: {"status":"healthy","timestamp":"..."}

# 2. API Info
curl -s http://localhost:8000/api/ | jq .
# Expected: Service info with version and endpoints

# 3. Documentation Access
curl -f http://localhost:8000/docs
# Expected: HTTP 200 (Swagger UI available)
```

### Test Set B: Authentication Flow
```bash
# Run the automated authentication test
bash scripts/api-tests/test-auth-flow.sh

# Expected Output:
# ✓ User Registration: test-XXXXX@example.com
# ✓ User Login: JWT token obtained
# ✓ Protected Endpoint: /api/users/me
# ✓ Photo List Access: /api/photos/
# ✓ Public Photos Access: /api/photos/public
# 🎉 All authentication tests PASSED!
```

### Test Set C: Email Verification Flow
```bash
# Run the automated email verification test
bash scripts/api-tests/test-email-verification.sh

# Expected Output:
# ✓ User registered successfully (ID: X, Unverified)
# ✓ Verification email requested successfully
# ✓ Email verified successfully
# ✓ Login successful with verified user
# ✓ Protected endpoint access successful
# ✓ Duplicate request handling
# 🎉 All email verification tests PASSED!
```

### Test Set D: Photo Upload Flow
```bash
# Run the automated photo upload test
bash scripts/api-tests/test-photo-upload.sh

# Expected Output:
# ✓ Authentication successful
# ✓ Test image created
# ✓ Photo upload successful
# ✓ Photo details retrieval successful
# ✓ Photo listing successful
# ✓ Cleanup completed
```

---

## 🔬 Comprehensive Test Suite (15-30 minutes)

### Manual API Testing

#### 1. User Registration, Email Verification & Login
```bash
# Register a new user (creates unverified user)
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manual-test@example.com",
    "password": "TestPassword123!"
  }'

# Request email verification
VERIFICATION_RESPONSE=$(curl -X POST http://localhost:8000/api/users/request-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "manual-test@example.com"}')

# Extract verification link from response and visit it
# Example: curl http://localhost:8000/api/users/verify/YOUR_SECRET

# Login after verification
LOGIN_RESPONSE=$(curl -X POST http://localhost:8000/api/users/login \
  -F "username=manual-test@example.com" \
  -F "password=TestPassword123!")

# Extract token (manual step - copy from response)
export AUTH_TOKEN="your-jwt-token-here"
```

#### 2. Protected Endpoint Access
```bash
# Get user info
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:8000/api/users/me

# List user photos
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:8000/api/photos/
```

#### 3. Photo Upload & Management
```bash
# Create test image
echo -e '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9' > test-image.jpg

# Upload photo with metadata
curl -X POST http://localhost:8000/api/photos/upload \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "file=@test-image.jpg" \
  -F "title=Manual Test Photo" \
  -F "description=Testing photo upload manually" \
  -F "is_public=true"

# Get photo by ID (use ID from upload response)
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:8000/api/photos/1

# Download photo file
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  -o downloaded-photo.jpg \
  http://localhost:8000/api/photos/1/download

# Get photo URLs
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:8000/api/photos/1/url
```

#### 4. Public Content Access
```bash
# List public photos (no auth required)
curl http://localhost:8000/api/photos/public

# Access public photo metadata
curl http://localhost:8000/api/photos/1
```

#### 5. Platform Monitoring
```bash
# Service statistics
curl http://localhost:8000/api/platform/stats

# Security status
curl http://localhost:8000/api/platform/security

# Performance metrics
curl http://localhost:8000/api/platform/performance

# Prometheus metrics
curl http://localhost:8000/metrics
```

---

## 🔒 Security Validation Tests

### Rate Limiting Test
```bash
# Test rate limiting (should trigger after multiple rapid requests)
for i in {1..20}; do
  curl -w "Response %{http_code}\n" http://localhost:8000/health
done
# Expected: Some requests return 429 (Too Many Requests)
```

### Input Validation Test
```bash
# Test invalid registration data
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email": "invalid-email", "password": "123"}'
# Expected: 422 Validation Error

# Test malicious file upload
echo "not-an-image" > malicious.txt
curl -X POST http://localhost:8000/api/photos/upload \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "file=@malicious.txt"
# Expected: 400 Bad Request (file validation failure)
```

### Authentication Security Test
```bash
# Test invalid token
curl -H "Authorization: Bearer invalid-token" \
  http://localhost:8000/api/users/me
# Expected: 401 Unauthorized

# Test missing token
curl http://localhost:8000/api/users/me
# Expected: 401 Unauthorized

# Test unverified user login attempt
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email": "unverified@example.com", "password": "Test123!"}'

curl -X POST http://localhost:8000/api/users/login \
  -F "username=unverified@example.com" \
  -F "password=Test123!"
# Expected: Login should work (user verification is separate from login)

# Test expired verification link
# (Manual test - verification links expire after 24 hours)
```

---

## 🧪 Automated Test Suite

### Unit Tests
```bash
cd services/photoshare
python3 run_tests.py unit --verbose

# Expected: All unit tests pass
# Tests cover: database models, security components, core functionality
```

### Integration Tests
```bash
python3 run_tests.py integration --verbose

# Expected: All integration tests pass  
# Tests cover: API endpoints, database integration, auth flow
```

### Security Tests
```bash
python3 run_tests.py security --verbose

# Expected: Security tests pass
# Tests cover: OWASP compliance, penetration testing, fuzz testing
```

### Performance Tests
```bash
python3 run_tests.py performance --verbose

# Expected: Performance benchmarks meet targets
# Tests cover: caching, query optimization, response times
```

### Complete Test Suite
```bash
python3 run_tests.py all --verbose

# Expected: All test categories pass with coverage report
```

---

## 📊 Expected Results & Success Criteria

### ✅ Success Indicators

1. **Health Tests**: All endpoints return appropriate HTTP status codes
2. **Authentication**: JWT tokens issued and validated correctly
3. **Email Verification**: Verification emails generated and processed correctly
4. **Photo Operations**: Upload, retrieval, and metadata operations work
5. **Security**: Rate limiting and input validation active
6. **Database**: All CRUD operations complete successfully
7. **Performance**: Response times < 200ms for simple operations
8. **Monitoring**: Metrics collected and exposed via /metrics

### ❌ Failure Indicators

1. **Service Unavailable**: Health endpoint returns non-200 status
2. **Auth Failures**: Cannot obtain or validate JWT tokens
3. **Email Verification Failures**: Cannot generate or process verification links
4. **Upload Failures**: Cannot upload or retrieve photos
5. **Security Bypassed**: Rate limiting or validation not working
6. **Database Errors**: Connection or query failures
7. **Performance Issues**: Response times > 1000ms consistently

---

## 🔧 Troubleshooting Guide

### Common Issues & Solutions

#### Service Won't Start
```bash
# Check Docker containers
docker compose ps

# Check service logs
docker compose logs backend

# Restart service
docker compose down && docker compose up --build
```

#### Database Connection Issues
```bash
# Verify database is running
docker compose ps platform-db

# Check database logs
docker compose logs platform-db

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up --build
```

#### JWT Token Issues
```bash
# Regenerate JWT secrets
python3 scripts/generate-jwt-secrets.py --update-env .env

# Validate configuration
python3 scripts/validate-config.py --env .env
```

#### File Upload Issues
```bash
# Check file storage directory exists and is writable
ls -la /tmp/photo_storage/

# Check file size limits in configuration
grep -i "max.*size" services/photoshare/main_database.py
```

---

## 📈 Performance Benchmarks

### Expected Performance Targets

| Operation | Target Response Time | Success Rate |
|-----------|---------------------|--------------|
| Health Check | < 50ms | 100% |
| User Registration | < 200ms | 100% |
| Email Verification Request | < 150ms | 100% |
| Email Verification Process | < 100ms | 100% |
| User Login | < 150ms | 100% |
| Photo Upload (1MB) | < 1000ms | 100% |
| Photo Retrieval | < 100ms | 100% |
| Photo Listing | < 200ms | 100% |
| Metrics Collection | < 100ms | 100% |

### Load Testing (Optional)
```bash
# Use curl in loop for basic load testing
for i in {1..100}; do
  (curl -s http://localhost:8000/health > /dev/null &)
done
wait

# Monitor metrics during load
curl -s http://localhost:8000/metrics | grep -E "(request_duration|request_count)"
```

---

## 🚨 Emergency Procedures

### Service Recovery
1. **Immediate**: Check service health and restart if needed
2. **Database**: Verify database connectivity and integrity  
3. **Logs**: Examine error logs for root cause analysis
4. **Rollback**: Restore from last known good configuration if needed

### Data Integrity Verification
```bash
# Check database connectivity
docker compose exec platform-db psql -U postgres -d photo_share -c "\dt"

# Verify user count
docker compose exec platform-db psql -U postgres -d photo_share -c "SELECT COUNT(*) FROM users;"

# Verify photo count  
docker compose exec platform-db psql -U postgres -d photo_share -c "SELECT COUNT(*) FROM photos;"
```

---

## 📝 Test Report Template

```
# Test Execution Report

**Date**: [Date]
**Tester**: [Name]  
**Environment**: [Development/Staging/Production]
**Service Version**: 2.3.0-monitoring

## Test Results Summary
- ✅ Health Tests: [PASS/FAIL]
- ✅ Authentication Tests: [PASS/FAIL]  
- ✅ Photo Management Tests: [PASS/FAIL]
- ✅ Security Tests: [PASS/FAIL]
- ✅ Performance Tests: [PASS/FAIL]

## Issues Found
[List any issues discovered during testing]

## Recommendations
[Any recommendations for improvements]

## Sign-off
Service is ready for [development/staging/production] use.
```

---

## 🎯 Conclusion

This test plan provides comprehensive validation of the Photo Share Service across all functional areas. The combination of automated scripts and manual procedures ensures thorough testing while maintaining efficiency for regular validation cycles.

**Quick Start**: Run `bash scripts/api-tests/test-auth-flow.sh`, `bash scripts/api-tests/test-email-verification.sh`, and `bash scripts/api-tests/test-photo-upload.sh` for immediate service validation.

**Full Validation**: Execute all test categories in sequence for complete service verification.

**Continuous Monitoring**: Use the /metrics endpoint for ongoing service health monitoring.