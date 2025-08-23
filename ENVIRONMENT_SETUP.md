# Environment Configuration Guide
**Version**: 2.3.0-monitoring  
**Updated**: August 23, 2025  

## Overview

This guide explains the environment configuration strategy for the Photo Share Service, covering development, testing, and production environments with their respective `.env` files.

## Environment Strategy

### Current Environment Files

| File | Purpose | When Used | Required |
|------|---------|-----------|----------|
| `.env.example` | Template and documentation | Reference/Setup | ✅ Keep |
| `.env` | Development/Production runtime | Docker services | ✅ Keep |
| `tests/.env.test` | Unit and integration testing | Test execution | ✅ Keep |

### Removed Files
- `.env.backup` - ❌ Removed (redundant backup)

## Environment Configuration Details

### 1. Development/Production Environment (`.env`)

**File Location**: `/project-root/.env`  
**Used By**: 
- Docker Compose services
- Main application runtime
- Production deployments

**Key Configuration Areas**:

#### Database Configuration
```bash
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=photo_share
DB_HOST=db                    # Docker service name
DB_PORT=5432
```

#### Security Configuration  
```bash
# JWT Authentication
SECRET_KEY=MyVeryStrongSecretKeyForPhotoSharingApp2024AbCdEfGhIjKlMnOp
JWT_SECRET_KEY=AnotherVeryStrongJWTSecretKeyForAuthentication2024AbCdEfGhIj
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true
```

#### Service Integration
```bash
# Platform Services (if using microservices)
PLATFORM_AUTH_URL=http://platform-auth:8001
PLATFORM_STORAGE_URL=http://platform-storage:8002
SERVICE_REGISTRY_URL=http://consul:8500
```

### 2. Testing Environment (`tests/.env.test`)

**File Location**: `/project-root/tests/.env.test`  
**Used By**:
- Unit tests (pytest execution)
- Integration tests
- Security compliance testing
- Test orchestration scripts

**Key Differences from Production**:

#### Database Configuration (Test-Specific)
```bash
ENVIRONMENT=test
DEBUG=false
DB_HOST=localhost             # Direct connection, not Docker
DB_PORT=5433                  # Different port to avoid conflicts
POSTGRES_DB=photo_share_test  # Separate test database
```

#### Security (Relaxed for Testing)
```bash
JWT_SECRET_KEY=test_jwt_secret_key_for_testing_only_not_for_production
BCRYPT_ROUNDS=4               # Faster for tests
RATE_LIMIT_PER_MINUTE=1000    # Higher limits for test execution
SESSION_TIMEOUT_MINUTES=60    # Longer for test stability
```

#### File Storage (Test Isolation)
```bash
UPLOAD_DIR=tests/test_data/uploads  # Isolated test uploads
MAX_FILE_SIZE=10485760              # 10MB limit for tests
```

#### Mock Services (No External Dependencies)
```bash
SMTP_HOST=localhost           # Mock SMTP for email tests
SMTP_TLS=false               # Simplified for testing
FROM_EMAIL=test@photo-share.com
```

## Environment Usage Scenarios

### 1. Development Setup
```bash
# Copy template and customize
cp .env.example .env

# Generate secure secrets
python3 scripts/generate-jwt-secrets.py --update-env .env

# Start development services
docker compose up --build
```

### 2. Unit Testing
```bash
# Tests automatically use tests/.env.test
cd tests
source env/bin/activate
python3 scripts/run_tests_uv.py --categories unit
```

### 3. Integration Testing with Services
```bash
# Start test database
docker compose up db -d

# Run integration tests (uses tests/.env.test)
python3 tests/scripts/run_tests_uv.py --categories integration
```

### 4. Full System Testing
```bash
# Start all services with production .env
docker compose up --build -d

# Run API tests against running services
bash scripts/api-tests/test-auth-flow.sh
bash scripts/api-tests/test-email-verification.sh
bash scripts/api-tests/test-photo-upload.sh
```

### 5. Security Testing
```bash
# Uses tests/.env.test for security configurations
python3 tests/scripts/run_security_compliance.py --generate-certificates
python3 tests/scripts/run_security_audit.py
```

## Environment-Specific Behaviors

### Database Connections

#### Development/Production (`.env`)
- Uses Docker network service names (`db`, `redis-cache`)
- Persistent data volumes
- Production-grade connection pooling

#### Testing (`tests/.env.test`)  
- Direct localhost connections
- In-memory SQLite for unit tests
- Separate test database for integration tests
- Automatic cleanup after test runs

### Security Configurations

#### Production (`.env`)
- Strong JWT secrets (32+ characters)
- Higher bcrypt rounds (12+)
- Strict rate limiting
- Production CORS origins

#### Testing (`tests/.env.test`)
- Predictable test secrets
- Fast bcrypt rounds (4)
- Relaxed rate limiting
- Open CORS for test clients

### File Storage

#### Production (`.env`)
- Persistent volume mounts
- Production storage paths
- Integration with platform storage services

#### Testing (`tests/.env.test`)
- Temporary test directories
- Automatic cleanup
- Mock platform storage

## Environment Variable Priority

1. **Environment Variables** (highest priority)
2. **Docker Compose environment section**
3. **`.env` file** (development/production)
4. **`tests/.env.test`** (testing only)
5. **Application defaults** (lowest priority)

## Security Best Practices

### Production Environment
```bash
# Generate strong secrets
python3 scripts/generate-jwt-secrets.py --update-env .env

# Validate configuration
python3 scripts/validate-config.py --env .env

# Never commit .env files
# .env is in .gitignore
```

### Testing Environment  
```bash
# Use predictable but secure test secrets
# Lower security for test performance
# Isolated test data and services
```

## Troubleshooting Environment Issues

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check if using correct DB_HOST for environment
   # Development: db (Docker service)
   # Testing: localhost (direct connection)
   ```

2. **JWT Token Invalid**
   ```bash
   # Ensure JWT_SECRET_KEY is set and consistent
   # Check JWT_ALGORITHM matches application expectation
   ```

3. **CORS Errors**
   ```bash
   # Verify ALLOWED_ORIGINS includes your frontend URL
   # Check CORS_ALLOW_CREDENTIALS setting
   ```

4. **File Upload Failures**
   ```bash
   # Check UPLOAD_DIR exists and is writable
   # Verify MAX_FILE_SIZE and ALLOWED_EXTENSIONS
   ```

### Environment Validation Commands

```bash
# Validate production environment
python3 scripts/validate-config.py --env .env

# Validate test environment  
python3 scripts/validate-config.py --env tests/.env.test

# Test database connectivity
docker compose exec backend python -c "from database import engine; print('DB OK')"

# Test Redis connectivity (if using)
docker compose exec backend python -c "import redis; r=redis.Redis(); print('Redis OK')"
```

## Migration Guide

### From Multiple .env Files to Streamlined Setup

**Before**: Multiple scattered .env files  
**After**: Two focused environment files

**Migration Steps**:
1. ✅ Consolidated to `.env` (production/development)
2. ✅ Specialized `tests/.env.test` for testing
3. ✅ Removed redundant `.env.backup`
4. ✅ Updated `.gitignore` to protect secrets
5. ✅ Created `.env.example` as template

### Environment File Recommendations

**Keep These Files**:
- ✅ `.env.example` - Template and documentation
- ✅ `.env` - Main application configuration  
- ✅ `tests/.env.test` - Testing configuration

**Remove These Files**:
- ❌ `.env.backup` - Redundant backup
- ❌ `.env.development` - Merged with `.env`
- ❌ `.env.production` - Same as `.env` with different values
- ❌ Multiple environment-specific files

## Summary

The streamlined environment strategy uses:

1. **`.env`** - Single file for development and production (values differ)
2. **`tests/.env.test`** - Specialized testing configuration  
3. **`.env.example`** - Template and documentation

This approach minimizes complexity while providing clear separation between runtime and testing environments. The configuration supports all testing scenarios from unit tests to full system integration testing.