# API Integration Tests

**Purpose**: End-to-end API functionality validation

These tests validate the complete API workflows by making actual HTTP requests to the running PhotoShare service. They test the integration between different API endpoints and verify that the complete user workflows function correctly.

## API Test Suites

### Authentication and User Management
- `test-auth-flow.sh` - Complete authentication workflow testing
  - User registration
  - Email verification
  - Login and token validation
  - Protected endpoint access

### User Workflows
- `test-email-verification.sh` - Email verification system testing
  - Verification request
  - Token validation
  - Expiration handling

### Photo Management
- `test-photo-upload.sh` - Photo upload and management testing
  - File upload validation
  - Metadata extraction
  - Security scanning
  - Download functionality

## Usage

### Prerequisites
```bash
# Ensure the PhotoShare service is running
docker compose up --build

# Wait for service to be ready
curl -f http://localhost:8000/health || echo "Service not ready"
```

### Run All Integration Tests
```bash
# Run complete integration test suite
bash api-integration-tests/test-auth-flow.sh
bash api-integration-tests/test-email-verification.sh
bash api-integration-tests/test-photo-upload.sh
```

### Individual Test Execution
```bash
# Test specific functionality
bash api-integration-tests/test-auth-flow.sh
```

## Test Environment

These tests are designed to run against:
- **Development**: Local Docker Compose environment
- **Staging**: Staging environment for pre-production validation
- **Production**: Limited safe tests for production health checks

## Key Differences from Other Test Types

| Test Type | Purpose | Environment | When to Run |
|-----------|---------|-------------|-------------|
| Unit Tests (`/tests/unit`) | Code component testing | Isolated/Mocked | During development |
| Integration Tests (`/tests/integration`) | Service integration | Test environment | Before deployment |
| API Integration Tests (this directory) | End-to-end workflows | Running service | After deployment |
| Operational Validation (`/operational-security-validation`) | Security system health | Production | Daily operations |

## Adding New API Tests

When adding new API endpoints or workflows:

1. Create test scripts following the naming pattern: `test-{feature-name}.sh`
2. Include both positive and negative test cases
3. Validate all response codes and data formats
4. Test error handling and edge cases
5. Clean up test data after execution

### Test Script Template
```bash
#!/bin/bash
# test-new-feature.sh

set -e

echo "🧪 Testing New Feature API..."

# Test setup
BASE_URL="http://localhost:8000"
TEST_USER="test@example.com"

# Test cases
echo "✅ Test case 1: ..."
# API calls and validation

echo "✅ Test case 2: ..."
# More test cases

echo "🎉 All New Feature API tests passed!"
```