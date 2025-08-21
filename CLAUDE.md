# CLAUDE.md

**Version**: 2.3.0-monitoring  
**Last Updated**: August 20, 2025 - 11:45 AM PST  
**Purpose**: Development guidance for AI assistants and developers working on the codebase

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A production-ready Photo Sharing Service built with FastAPI and PostgreSQL. This is a single-service application with comprehensive security, performance optimization, monitoring capabilities, and **email verification system**.

## Current Architecture

- **Service**: Single FastAPI application (`services/photoshare/main_database.py`)
- **Database**: PostgreSQL with async SQLAlchemy ORM
- **Version**: 2.3.0-monitoring
- **Security**: JWT authentication, email verification, rate limiting, input validation
- **Performance**: Memory caching, query optimization
- **Monitoring**: Prometheus metrics integration

## Project Structure

```
photo-share-3/
├── .env                           # Configuration (JWT secrets, DB credentials)
├── docker-compose.yml             # Single service deployment
├── services/photoshare/           # Main application
│   ├── main_database.py          # FastAPI service (entry point)
│   ├── database.py               # PostgreSQL models & repositories
│   ├── security.py               # Security framework (rate limiting, validation)
│   ├── monitoring.py             # Prometheus metrics
│   ├── performance_simple.py     # Caching & optimization  
│   ├── error_handling.py         # Error management
│   ├── file_storage.py           # File operations
│   ├── service_discovery.py      # Service registry integration
│   ├── Dockerfile.database       # Container configuration
│   ├── requirements_fixed.txt    # Python dependencies
│   ├── requirements_test.txt     # Test dependencies
│   ├── pytest.ini               # Test configuration
│   ├── run_tests.py              # Test runner
│   └── tests/                    # Test suite
│       ├── conftest.py
│       ├── unit/                 # Unit tests
│       ├── integration/          # Integration tests
│       └── security/             # Security tests
├── tools/                        # Development and analysis tools
│   ├── docker-compose.tools.yml  # Tools container configuration
│   ├── requirements.txt          # Tools dependencies
│   ├── sbom-agent/               # Software Bill of Materials generator
│   │   ├── src/                  # SBOM generation engine
│   │   ├── tests/                # Vulnerability test datasets
│   │   └── docs/                 # Integration guides
│   └── shared/                   # Shared utilities
│       ├── environment_detector.py # Environment detection
│       ├── filename_manager.py   # File naming standards
│       └── version_manager.py    # Version management
├── scripts/                      # Utilities
│   ├── api-tests/                # API testing scripts
│   │   ├── test-auth-flow.sh     # Authentication flow tests
│   │   ├── test-email-verification.sh # Email verification tests
│   │   └── test-photo-upload.sh  # Photo upload tests
│   ├── generate-jwt-secrets.py   # JWT secret generator
│   └── validate-config.py        # Configuration validation
```

## Key Features

- **User Management**: Registration, email verification, login, JWT authentication
- **Photo Management**: Upload, metadata storage, public/private photos
- **Security**: Email verification system, rate limiting, input validation, file security checks
- **Performance**: Memory caching, query optimization
- **Monitoring**: Health checks, metrics, performance tracking
- **Platform Integration**: Service discovery, external storage support

## Database Schema

- **users**: User accounts (id, email, password_hash, is_verified, is_active)
- **photos**: Photo metadata (id, user_id, filename, content_type, file_size, title, description, is_public)
- **sessions**: JWT session tracking (id, user_id, token, is_active)
- **email_verifications**: Email verification records (id, email, secret, created_at, expires_at)

## API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /api/` - API information
- `GET /docs` - Swagger documentation

### User Management
- `POST /api/users/register` - User registration (creates unverified user)
- `POST /api/users/request-verification` - Request email verification
- `GET /api/users/verify/{secret}` - Verify email with secret link
- `POST /api/users/login` - User login (returns JWT)
- `GET /api/users/me` - Get current user info (requires auth)

### Photo Management
- `POST /api/photos/upload` - Upload photo (requires auth)
- `GET /api/photos/` - List user's photos (requires auth)
- `GET /api/photos/public` - List public photos
- `GET /api/photos/{id}` - Get photo metadata
- `GET /api/photos/{id}/download` - Download photo file
- `GET /api/photos/{id}/url` - Get photo URLs

### Platform & Monitoring
- `GET /api/platform/stats` - Service statistics
- `GET /api/platform/security` - Security status
- `GET /api/platform/performance` - Performance metrics
- `GET /metrics` - Prometheus metrics

## Development Commands

### Setup and Running
```bash
# Start the service
docker compose up --build

# View logs
docker compose logs -f

# Stop service
docker compose down
```

### Development Tools
```bash
# Start development tools (SBOM generator, etc.)
docker compose -f tools/docker-compose.tools.yml up --build

# Generate Software Bill of Materials
cd tools/sbom-agent && python src/cli.py

# Environment detection and validation
python tools/shared/environment_detector.py
```

### Testing
```bash
# Test authentication flow
bash scripts/api-tests/test-auth-flow.sh

# Test email verification flow
bash scripts/api-tests/test-email-verification.sh

# Generate JWT secrets
python3 scripts/generate-jwt-secrets.py --update-env .env

# Validate configuration
python3 scripts/validate-config.py --env .env
```

### Database Operations
```bash
# Access PostgreSQL directly
docker compose exec platform-db psql -U postgres -d photo_share

# Reset database (removes all data)
docker compose down -v
docker compose up --build
```

## Key Environment Variables

Required in `.env` file:
- `JWT_SECRET_KEY`: Secure JWT signing key (generate with script)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Database credentials
- `DB_HOST`, `DB_PORT`: Database connection details
- `ALLOWED_ORIGINS`: CORS origins for frontend integration

## Important Notes

- **Security**: Users require email verification after registration (24-hour expiration)
- **Authentication**: Uses JWT tokens with 30-minute expiration
- **File Storage**: Local storage with platform storage integration
- **Performance**: Memory-based caching with Redis fallback support
- **Monitoring**: Comprehensive metrics for requests, database, security events

## Testing the Service

```bash
# Check service health
curl http://localhost:8000/health

# Register a user (unverified)
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123!"}'

# Request email verification
curl -X POST http://localhost:8000/api/users/request-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Verify email (use the verification_link from response)
curl http://localhost:8000/api/users/verify/YOUR_SECRET

# Login and get token (after verification)
curl -X POST http://localhost:8000/api/users/login \
  -F "username=test@example.com" \
  -F "password=TestPassword123!"

# Use token for authenticated endpoints
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/users/me
```

This is a production-ready service with comprehensive security, performance optimization, and monitoring capabilities.

## Important Notes

- **Clean Architecture**: The project maintains a clean structure with the current single-service application in `services/photoshare/`
- **Development Focus**: All development should use the current service structure - no legacy files remain
- **Testing**: Use the comprehensive test scripts in `scripts/api-tests/` to verify service functionality:
  - `bash scripts/api-tests/test-auth-flow.sh` - Authentication flow
  - `bash scripts/api-tests/test-email-verification.sh` - Email verification
  - `bash scripts/api-tests/test-photo-upload.sh` - Photo management