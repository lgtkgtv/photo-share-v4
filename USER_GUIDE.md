# PhotoShare Complete User Guide
# =============================

**Welcome to PhotoShare!** This comprehensive guide will help you understand, set up, develop, test, and deploy the PhotoShare application. Whether you're a new developer, DevOps engineer, or just exploring the codebase, this guide has everything you need.

## 📖 Table of Contents

1. [Project Overview](#-project-overview)
2. [Architecture Deep Dive](#-architecture-deep-dive)  
3. [Project Structure](#-project-structure)
4. [Environment Configuration](#-environment-configuration)
5. [Docker Compose Explained](#-docker-compose-explained)
6. [Development Setup](#-development-setup)
7. [Testing Framework](#-testing-framework)
8. [Security & Compliance](#-security--compliance)
9. [Production Deployment](#-production-deployment)
10. [Troubleshooting](#-troubleshooting)

---

## 🎯 Project Overview

PhotoShare is a **production-ready photo sharing platform** built with modern microservices architecture, featuring comprehensive security, scalability, and enterprise-grade features.

### What PhotoShare Does
- 📷 **Photo Management**: Upload, organize, and share high-quality photos
- 👥 **User Management**: Secure registration, authentication, and role-based access
- 🔐 **Enterprise Security**: SSO, 2FA, RBAC, and JWT-based authentication
- 📱 **API-First Design**: RESTful APIs ready for web, mobile, and third-party integrations
- 🎛️ **Admin Controls**: User management, content moderation, and system monitoring

### Key Features
- **Separated Microservices**: Independent auth and photo services
- **Database Isolation**: Separate databases for security and performance
- **Role-Based Access Control**: Fine-grained permissions system
- **Email Verification**: Secure user onboarding flow
- **JWT Security**: Industry-standard token authentication
- **Production Ready**: SSL, monitoring, scaling, and backup capabilities

---

## 🏗️ Architecture Deep Dive

PhotoShare uses a **separated microservices architecture** designed for security, scalability, and maintainability.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PhotoShare Platform                      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐
│  Frontend/Web   │    │   Mobile App    │    │  API Clients │
│  (Port 3000)    │    │                 │    │              │
└─────────────────┘    └─────────────────┘    └──────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │      NGINX          │
                    │  (Load Balancer)    │
                    │   Ports 80/443      │
                    └─────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                                │
                ▼                                ▼
    ┌─────────────────────┐            ┌─────────────────────┐
    │   Auth Service      │◄──────────►│  Photo Service      │
    │   Port: 8001        │            │  Port: 8000         │
    │                     │            │                     │
    │ • User Registration │            │ • Photo Upload      │
    │ • Email Verification│            │ • Photo Management  │
    │ • JWT Authentication│            │ • File Storage      │
    │ • SSO Integration   │            │ • Album Management  │
    │ • 2FA Management    │            │ • Permission Check  │
    │ • RBAC System       │            │ • Public API        │
    └─────────────────────┘            └─────────────────────┘
                │                                │
                ▼                                ▼
    ┌─────────────────────┐            ┌─────────────────────┐
    │   Auth Database     │            │  Photo Database     │
    │   Port: 5433        │            │  Port: 5432         │
    │                     │            │                     │
    │ • users             │            │ • photos            │
    │ • roles             │            │ • albums            │
    │ • permissions       │            │ • file_metadata     │
    │ • sessions          │            │ • sharing_tokens    │
    │ • email_verifications│            │ • analytics        │
    │ • sso_accounts      │            │                     │
    └─────────────────────┘            └─────────────────────┘
```

### Service Communication Flow

```mermaid
sequenceDiagram
    participant User
    participant Auth
    participant Photo
    participant AuthDB
    participant PhotoDB

    User->>Auth: Register/Login
    Auth->>AuthDB: Store user data
    Auth-->>User: JWT Token
    
    User->>Photo: Upload photo (with JWT)
    Photo->>Auth: Validate JWT & get permissions
    Auth-->>Photo: User info & permissions
    Photo->>PhotoDB: Store photo metadata
    Photo-->>User: Upload confirmation
```

### Why Separated Architecture?

1. **Security Isolation**: Authentication logic completely separated from application logic
2. **Independent Scaling**: Scale auth and photo services independently based on load
3. **Database Security**: Complete data isolation between user data and application data
4. **Development Efficiency**: Teams can work on services independently
5. **Technology Flexibility**: Different services can use different tech stacks if needed
6. **Fault Tolerance**: If one service fails, others can continue operating

---

## 📁 Project Structure

```
photo-share-consul/
│
├── 📋 Documentation & Configuration
│   ├── README.md                    # Project overview
│   ├── USER_GUIDE.md               # This comprehensive guide
│   ├── PRODUCTION_DEPLOYMENT.md    # Production deployment guide
│   ├── CLAUDE.md                   # Development guidelines
│   └── AUTHENTICATION_THREAT_MODEL.md
│
├── 🐳 Docker Configuration
│   ├── docker-compose.separated.yml     # Development environment
│   ├── docker-compose.production.yml    # Production environment
│   ├── deploy-production.sh            # Production deployment script
│   └── production-maintenance.sh       # Production management tools
│
├── ⚙️ Services (Microservices)
│   ├── auth-service/                   # Authentication microservice
│   │   ├── main.py                     # FastAPI application entry
│   │   ├── auth_service.py            # Authentication logic
│   │   ├── auth_database.py           # Auth database models
│   │   ├── sso_providers.py           # SSO integrations
│   │   ├── two_factor_auth.py         # 2FA implementation
│   │   ├── security.py                # Security utilities
│   │   ├── setup_rbac.py              # Role-based access setup
│   │   ├── Dockerfile                 # Development container
│   │   ├── Dockerfile.production      # Production container
│   │   └── requirements.txt           # Python dependencies
│   │
│   ├── photoshare/                    # Photo service
│   │   ├── main.py                    # FastAPI application entry
│   │   ├── app_database.py           # Photo database models
│   │   ├── auth_integration.py        # Auth service integration
│   │   ├── file_storage.py           # File handling
│   │   ├── image_processing.py        # Image processing
│   │   ├── monitoring.py             # Metrics and monitoring
│   │   ├── performance_simple.py     # Performance optimization
│   │   ├── error_handling.py         # Error management
│   │   ├── Dockerfile.production     # Production container
│   │   ├── storage/                  # File storage directory
│   │   └── requirements.txt          # Python dependencies
│   │
│   └── shared/                       # Shared utilities
│       └── security.py               # Common security functions
│
├── 🧪 Testing Framework
│   ├── tests/
│   │   ├── run_tests.py             # Unified test runner
│   │   ├── run_security_tests.py    # Security test runner
│   │   ├── README.md                # Testing documentation
│   │   ├── conftest.py              # Test configuration
│   │   ├── pytest.ini               # Pytest settings
│   │   ├── unit/                    # Unit tests
│   │   ├── integration/             # Integration tests
│   │   ├── functional/              # End-to-end tests
│   │   ├── security/                # Security & compliance tests
│   │   ├── reports/                 # Test reports
│   │   └── coverage/                # Coverage reports
│   │
│   └── scripts/api-tests/           # Manual API testing scripts
│       ├── test-auth-flow.sh
│       ├── test-email-verification.sh
│       └── test-photo-upload.sh
│
├── 🔧 Configuration & Infrastructure
│   ├── config/
│   │   └── nginx.prod.conf          # NGINX production config
│   ├── monitoring/                  # Monitoring stack config
│   │   ├── prometheus.yml
│   │   ├── grafana/
│   │   └── alertmanager.yml
│   ├── ssl/                         # SSL certificates
│   └── tools/                       # Development tools
│       ├── sbom-agent/              # Software Bill of Materials
│       └── shared/                  # Shared utilities
│
└── 📜 Scripts & Utilities
    ├── scripts/
    │   ├── generate-jwt-secrets.py
    │   ├── validate-config.py
    │   └── setup-environment.py
    └── pyproject.toml               # Python project config
```

### Key Modules Explained

#### Authentication Service (`services/auth-service/`)
- **`auth_service.py`**: Core authentication logic, user management, JWT handling
- **`auth_database.py`**: User models, roles, permissions, sessions
- **`sso_providers.py`**: Google, Microsoft, Okta, Auth0 integrations
- **`two_factor_auth.py`**: TOTP, SMS, backup codes, hardware keys
- **`security.py`**: Rate limiting, input validation, security middleware
- **`setup_rbac.py`**: Role-based access control initialization

#### Photo Service (`services/photoshare/`)
- **`main.py`**: Photo management APIs, upload/download endpoints
- **`auth_integration.py`**: JWT validation, permission checking
- **`file_storage.py`**: File handling, storage management
- **`image_processing.py`**: Thumbnail generation, EXIF processing
- **`app_database.py`**: Photo models, albums, metadata
- **`monitoring.py`**: Prometheus metrics, health checks

---

## ⚙️ Environment Configuration

PhotoShare uses **3 separate environment files** to configure the microservices architecture, providing security isolation and deployment flexibility.

### Environment Files Structure

```
photo-share-consul/
├── .env.auth-service          # Authentication service configuration
├── .env.application           # Photo service configuration
├── .env.production.template   # Production deployment template
└── .env.production           # Production config (you create this)
```

## 🔐 Environment File Details

### 1. `.env.auth-service` - Authentication Service Configuration
**Used by:** Dedicated authentication microservice  
**Purpose:** Handles user authentication, SSO, 2FA, and RBAC

**Key Configuration Areas:**

#### Authentication Database (Isolated)
```bash
# Separate PostgreSQL for user accounts, roles, sessions
AUTH_DB_HOST=auth-db
AUTH_DB_PORT=5432
AUTH_POSTGRES_USER=auth_user
AUTH_POSTGRES_PASSWORD=auth_secure_password_here
AUTH_POSTGRES_DB=photo_share_auth
AUTH_DATABASE_URL=postgresql+asyncpg://auth_user:auth_secure_password_here@auth-db:5432/photo_share_auth
```

#### JWT Configuration
```bash
# Token signing and validation (must match application service)
JWT_SECRET_KEY=your-very-secure-jwt-secret-key-minimum-256-bits
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
JWT_AUDIENCE=photoshare-app
JWT_ISSUER=photoshare-auth
```

#### SSO Provider Integration
```bash
# Google OAuth 2.0 / OIDC
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Microsoft Azure AD / OIDC
MICROSOFT_CLIENT_ID=your-azure-client-id
MICROSOFT_CLIENT_SECRET=your-azure-client-secret
MICROSOFT_TENANT_ID=common

# Okta, Auth0, Generic OIDC providers also supported
```

#### Two-Factor Authentication
```bash
# 2FA encryption and SMS providers
TWOFA_ENCRYPTION_KEY=fFmtPX__r7bVd2TJemS3QPmSaJ00mEoq6nUjsyEQF9I=
SMS_PROVIDER=twilio
SMS_PROVIDER_API_KEY=your-twilio-api-key
SMS_FROM_NUMBER=+1234567890

# WebAuthn hardware key support
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_NAME=PhotoShare
```

### 2. `.env.application` - Photo Service Configuration
**Used by:** Main photo sharing application service  
**Purpose:** Handles photo uploads, storage, and business logic

**Key Configuration Areas:**

#### Application Database (Isolated)
```bash
# Separate PostgreSQL for photos, metadata, albums
APP_DB_HOST=app-db
APP_DB_PORT=5432
APP_POSTGRES_USER=app_user
APP_POSTGRES_PASSWORD=app_secure_password_here
APP_POSTGRES_DB=photo_share_app
APP_DATABASE_URL=postgresql+asyncpg://app_user:app_secure_password_here@app-db:5432/photo_share_app
```

#### Authentication Service Integration
```bash
# Service-to-service communication
AUTH_SERVICE_URL=http://auth-service:8000
JWT_SECRET_KEY=your-very-secure-jwt-secret-key-minimum-256-bits  # Must match auth service
AUTH_SERVICE_API_KEY=your-secure-service-to-service-api-key
```

#### File Storage & Processing
```bash
# Local and cloud storage configuration
STORAGE_PATH=/app/storage
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_TYPES=image/jpeg,image/jpg,image/png,image/gif,image/bmp,image/webp

# Thumbnail generation
GENERATE_THUMBNAILS=true
THUMBNAIL_SIZES=150x150,300x300,800x600
THUMBNAIL_QUALITY=85

# Cloud storage providers (AWS S3, Azure Blob, GCS)
CLOUD_STORAGE_ENABLED=false
CLOUD_STORAGE_PROVIDER=aws_s3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
```

#### Performance & Caching
```bash
# Redis cache configuration
CACHE_ENABLED=true
CACHE_PROVIDER=redis
REDIS_HOST=redis-cache
REDIS_PORT=6379
CACHE_TTL_USER_DATA=300
CACHE_TTL_PHOTO_METADATA=600

# Database connection pooling
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=0
DB_POOL_RECYCLE=3600
```

#### Application Features
```bash
# Photo processing features
ENABLE_AUTO_ORIENTATION=true
ENABLE_EXIF_EXTRACTION=true
ENABLE_GPS_EXTRACTION=true
STRIP_EXIF_ON_PUBLIC_PHOTOS=true

# Social and content features
ENABLE_COMMENTS=true
ENABLE_PHOTO_SHARING=true
ENABLE_PUBLIC_GALLERIES=true
ENABLE_ANALYTICS=true

# Content moderation
ENABLE_CONTENT_MODERATION=true
CONTENT_MODERATION_PROVIDER=aws_rekognition
```

### 3. `.env.production.template` - Production Template
**Used by:** Production deployment  
**Purpose:** Template for creating actual `.env.production` file

```bash
# Production Environment Configuration Template
# Copy to .env.production and configure with your values
# DO NOT commit .env.production to version control!

ENVIRONMENT=production
LOG_LEVEL=info

# CRITICAL: Generate secure keys for production!
JWT_SECRET_KEY=your-very-secure-256-bit-jwt-secret-key-here-change-in-production
AUTH_DB_PASSWORD=secure-auth-db-password-change-in-production
APP_DB_PASSWORD=secure-app-db-password-change-in-production
REDIS_PASSWORD=secure-redis-password-change-in-production

# Production domain and SSL
DOMAIN=yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SSL_CERTIFICATE_PATH=/etc/nginx/ssl/fullchain.pem
SSL_CERTIFICATE_KEY_PATH=/etc/nginx/ssl/privkey.pem

# Production email configuration
SMTP_HOST=smtp.your-email-provider.com
SMTP_PORT=587
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=your-smtp-password

# Security and monitoring
SECURITY_HEADERS_ENABLED=true
HSTS_MAX_AGE=31536000
ENABLE_METRICS=true
BACKUP_ENABLED=true
```

## 🛡️ Why Separate Environment Files?

### Security Through Isolation
- **Database Separation**: Auth service cannot access photo data; photo service cannot access credentials
- **Principle of Least Privilege**: Each service only has access to its required configuration
- **Credential Compartmentalization**: If one service is compromised, other service secrets remain protected

### Microservices Architecture Benefits
- **Independent Configuration**: Services can be configured and scaled independently
- **Development Flexibility**: Run services separately or together based on development needs
- **Feature Isolation**: Disable features per service without affecting others

### Deployment Scenarios
- **Development**: Use `.env.auth-service` and `.env.application` with dev-friendly settings
- **Testing**: Override specific settings for test environments
- **Production**: Use `.env.production` with production-grade security settings
- **Staging**: Create environment-specific files as needed

### Configuration Management Flow

1. **Docker Compose** reads appropriate environment files based on compose file used
2. **Services** receive only their relevant environment variables
3. **Application Code** uses environment variables for runtime configuration
4. **Security boundaries** maintained through file separation

### Best Practices

**⚠️ Security Warning**: Never commit production environment files to version control!

```bash
# Add to .gitignore
.env.production
.env.local
.env.*.local
```

**🔑 JWT Secret Sharing**: Auth and application services must share the same `JWT_SECRET_KEY` for token validation to work.

**🗄️ Database Isolation**: Always use separate databases and credentials for auth vs application services.

**📝 Documentation**: Keep environment file documentation updated when adding new configuration options.

---

## 🐳 Docker Compose Explained

PhotoShare provides two Docker Compose configurations optimized for different use cases.

### `docker-compose.separated.yml` - Development Environment

**Purpose**: Local development, testing, and debugging

```yaml
# Optimized for developer productivity
services:
  auth-service:
    build: ./services/auth-service
    ports:
      - "8001:8000"                    # Direct port access
    volumes:
      - ./services/auth-service:/app   # Live code mounting
    env_file:
      - .env.auth-service             # Development config
    networks:
      - auth-network
      - app-network                   # Cross-network for testing
```

**Key Features**:
- **Live Code Mounting**: Changes reflect immediately
- **Direct Port Access**: Each service on different ports
- **Debug-Friendly**: Detailed logging, easy debugging
- **Fast Startup**: Minimal resource overhead
- **Cross-Network Communication**: Services can talk to each other for testing

**When to Use**:
- 👨‍💻 Local development
- 🐛 Debugging issues
- 🧪 Testing new features
- 📚 Learning the codebase

### `docker-compose.production.yml` - Production Environment

**Purpose**: Production deployment with enterprise features

```yaml
# Optimized for production reliability
services:
  auth-service:
    build:
      context: ./services/auth-service
      dockerfile: Dockerfile.production  # Production optimized
    deploy:
      replicas: 2                       # High availability
      resources:
        limits:
          memory: 512M                  # Resource limits
          cpus: '0.5'
    environment:
      - ENVIRONMENT=production
    networks:
      - auth-network                    # Strict isolation
    restart: unless-stopped
    healthcheck:                        # Comprehensive health checks
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

**Key Features**:
- **Production Dockerfiles**: Multi-stage builds, security hardening
- **Resource Management**: CPU/memory limits and reservations
- **High Availability**: Multiple replicas, auto-restart
- **Security**: Network isolation, non-root containers
- **Monitoring**: Health checks, metrics collection
- **SSL/TLS**: HTTPS termination, certificate management
- **Load Balancing**: NGINX reverse proxy with rate limiting

**When to Use**:
- 🌍 Production deployment
- 🏗️ Staging environments
- 🧪 Load testing
- 👥 User acceptance testing

### Architecture Comparison

| Aspect | Development (Separated) | Production |
|--------|------------------------|------------|
| **Goal** | Developer Productivity | Reliability & Security |
| **Services** | 2 services, 2 databases | 2+ services, 2 databases, NGINX, Redis |
| **Networking** | Permissive (easy debugging) | Strict isolation |
| **Storage** | Local volumes | Persistent volumes |
| **Security** | Basic (HTTP, weak secrets) | Enterprise (HTTPS, strong secrets) |
| **Monitoring** | Logs only | Metrics + Logs + Alerts |
| **Scaling** | Single instance | Horizontal scaling |
| **Startup Time** | ~30 seconds | ~2-3 minutes |

---

## 🚀 Development Setup

Get PhotoShare running on your local machine in minutes!

### Prerequisites

```bash
# Required software
- Docker 20.10+
- Docker Compose 2.0+
- Git
- Python 3.8+ (for testing)
- Node.js 16+ (if building frontend)

# System requirements
- 8GB RAM recommended
- 10GB free disk space
- macOS, Linux, or Windows with WSL2
```

### Quick Start (5 Minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/photo-share-consul.git
cd photo-share-consul

# 2. Start development environment
docker compose -f docker-compose.separated.yml up --build

# 3. Wait for services to be ready (watch the logs)
# You'll see: ✅ Authentication service initialized successfully

# 4. Test the services
curl http://localhost:8001/health  # Auth service
curl http://localhost:8000/health  # Photo service

# 5. Access the API documentation
# Auth API: http://localhost:8001/docs
# Photo API: http://localhost:8000/docs
```

### Development Workflow

#### Starting Services
```bash
# Start all services
docker compose -f docker-compose.separated.yml up

# Start in background
docker compose -f docker-compose.separated.yml up -d

# View logs
docker compose -f docker-compose.separated.yml logs -f

# Stop services
docker compose -f docker-compose.separated.yml down
```

#### Making Code Changes

1. **Edit code** in `services/auth-service/` or `services/photoshare/`
2. **Save changes** - they're automatically reflected (live mounting)
3. **Test changes** using the API endpoints or test scripts
4. **View logs** to debug any issues

#### Database Management
```bash
# Access auth database
docker compose -f docker-compose.separated.yml exec auth-db psql -U auth_user -d auth_service

# Access photo database
docker compose -f docker-compose.separated.yml exec app-db psql -U photo_user -d photo_share

# Reset databases (WARNING: Deletes all data)
docker compose -f docker-compose.separated.yml down -v
docker compose -f docker-compose.separated.yml up --build
```

#### Common Development Tasks

**User Registration & Verification:**
```bash
# Register a user
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@example.com", "password": "DevPassword123!", "first_name": "Dev", "last_name": "User"}'

# Get verification token from logs or database
# Verify email
curl http://localhost:8001/api/auth/verify-email/YOUR_VERIFICATION_TOKEN
```

**Photo Upload:**
```bash
# First, get a JWT token by logging in
# Then upload a photo
curl -X POST http://localhost:8000/api/photos/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/photo.jpg" \
  -F "title=My Test Photo" \
  -F "description=Testing photo upload"
```

### Development Tips

1. **Use the API docs**: Visit `/docs` endpoints for interactive API testing
2. **Monitor logs**: Keep logs open to see what's happening
3. **Database inspection**: Use database clients to examine data
4. **Test scripts**: Use scripts in `scripts/api-tests/` for common workflows
5. **Environment variables**: Modify `.env.*` files for configuration changes

---

## 🧪 Testing Framework

PhotoShare includes a comprehensive testing framework with multiple test categories and automated reporting.

### Test Architecture

```
tests/
├── run_tests.py              # 🚀 Unified test runner
├── run_security_tests.py     # 🔒 Security-focused test runner
├── conftest.py               # ⚙️ Global test configuration
├── pytest.ini               # 📋 Pytest configuration
│
├── unit/                     # 🔬 Unit Tests (Component Isolation)
│   ├── auth-service/         # Auth service components
│   ├── photoshare/          # Photo service components
│   └── shared/              # Shared utilities
│
├── integration/              # 🔗 Integration Tests (Service Communication)
│   ├── test_service_communication.py
│   ├── test_jwt_validation.py
│   └── test_separated_architecture.py
│
├── functional/               # 🎯 Functional Tests (End-to-End Workflows)
│   └── test_user_workflows.py
│
├── security/                 # 🛡️ Security Tests (Compliance & Vulnerabilities)
│   ├── test_rbac_security.py
│   └── test_security_compliance.py
│
├── reports/                  # 📊 Test Reports
└── coverage/                 # 📈 Coverage Reports
```

### Running Tests

#### Quick Test Commands

```bash
# Run all tests with coverage
python tests/run_tests.py

# Run specific categories
python tests/run_tests.py --categories unit integration

# Run security tests
python tests/run_security_tests.py

# Quick security check
python tests/run_security_tests.py --quick
```

#### Individual Test Categories

```bash
# Unit tests (fast, no external dependencies)
pytest tests/unit/ -v

# Integration tests (requires running services)
pytest tests/integration/ -v

# Functional tests (end-to-end workflows)
pytest tests/functional/ -v

# Security tests (vulnerability scanning)
pytest tests/security/ -v
```

#### Coverage Analysis

```bash
# Generate HTML coverage report
pytest --cov=services --cov-report=html:tests/coverage/html

# View coverage in browser
open tests/coverage/html/index.html

# Coverage with threshold enforcement
pytest --cov=services --cov-fail-under=70
```

### Test Categories Explained

#### 🔬 Unit Tests
- **Purpose**: Test individual functions and classes in isolation
- **Speed**: Very fast (< 1 second per test)
- **Dependencies**: None (uses mocks)
- **Example**: Testing JWT token validation logic

#### 🔗 Integration Tests  
- **Purpose**: Test service-to-service communication
- **Requirements**: Running auth and photo services
- **Example**: Auth service validates JWT, photo service accepts it

#### 🎯 Functional Tests
- **Purpose**: End-to-end user workflows
- **Requirements**: Full system running
- **Example**: User registers → verifies email → uploads photo

#### 🛡️ Security Tests
- **Purpose**: Security vulnerabilities and compliance
- **Coverage**: OWASP Top 10, RBAC, authentication security
- **Tools**: Static analysis (Bandit), dependency scanning (Safety)

### Test Reporting

All test runs generate:
- **HTML Reports**: Visual test results with pass/fail details
- **JSON Reports**: Machine-readable data for CI/CD pipelines
- **Coverage Reports**: Code coverage analysis with line-by-line details
- **Security Reports**: Vulnerability assessments and compliance status

### Developer Testing Workflow

```bash
# 1. Start services for integration/functional tests
docker compose -f docker-compose.separated.yml up -d

# 2. Run quick unit tests during development
pytest tests/unit/ -v

# 3. Run integration tests before committing
pytest tests/integration/ -v

# 4. Run full test suite before pull requests
python tests/run_tests.py

# 5. Run security checks before deployment
python tests/run_security_tests.py
```

---

## 🔒 Security & Compliance

PhotoShare implements enterprise-grade security with comprehensive compliance testing.

### Security Architecture

```
🛡️ Multi-Layer Security Architecture
┌─────────────────────────────────────────────────┐
│                Frontend                         │
│  • HTTPS Only                                   │
│  • CSP Headers                                  │  
│  • XSS Protection                               │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              NGINX (Reverse Proxy)              │
│  • SSL Termination                              │
│  • Rate Limiting                                │
│  • Security Headers                             │  
│  • DDoS Protection                              │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┼─────────┐
        │                   │
        ▼                   ▼
┌─────────────────┐   ┌─────────────────┐
│  Auth Service   │   │  Photo Service  │
│  • JWT Auth     │   │  • Permission   │
│  • 2FA/MFA      │   │    Validation   │
│  • Rate Limit   │   │  • Input Valid  │
│  • Input Valid  │   │  • File Checks  │
│  • RBAC         │   │  • Rate Limit   │
└─────────────────┘   └─────────────────┘
        │                   │
        ▼                   ▼
┌─────────────────┐   ┌─────────────────┐
│   Auth Database │   │  Photo Database │
│  • Encryption   │   │  • Encryption   │
│  • Access Logs  │   │  • Access Logs  │
│  • Isolation    │   │  • Isolation    │
└─────────────────┘   └─────────────────┘
```

### Security Features

#### 🔐 Authentication Security
- **JWT Tokens**: Industry-standard with secure secrets
- **Session Management**: Secure session handling and invalidation
- **Password Security**: bcrypt hashing with salt
- **Email Verification**: Required for account activation
- **Rate Limiting**: Prevents brute force attacks

#### 👥 Authorization (RBAC)
- **Role-Based Access**: 5-tier role system (user → superadmin)
- **Granular Permissions**: 21+ permissions with resource:action format
- **Permission Inheritance**: Hierarchical role permissions
- **Cross-Service Validation**: Auth service validates all permissions

#### 🛡️ Input Security
- **SQL Injection Prevention**: Parameterized queries, ORM protection
- **XSS Protection**: Input sanitization, output encoding
- **File Upload Security**: Type validation, size limits, content scanning
- **CSRF Protection**: Token-based request validation

#### 🌐 Network Security
- **HTTPS Enforcement**: TLS 1.2+ with strong cipher suites
- **CORS Configuration**: Restricted origins for API access
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Network Isolation**: Separate networks for different services

### RBAC (Role-Based Access Control) System

#### Default Roles & Permissions

```
🎭 Role Hierarchy (Level 0 → Level 4)
├── user (Level 0)
│   ├── photos:create, photos:read, photos:update, photos:delete
│   ├── users:read, users:update, users:delete
│   └── system:health
│
├── premium (Level 1)
│   ├── All user permissions +
│   └── system:metrics
│
├── moderator (Level 2)  
│   ├── photos:*, photos:read_all, photos:update_all
│   ├── users:*, users:update_all
│   ├── admin:content
│   └── system:health, system:metrics
│
├── admin (Level 3)
│   ├── photos:manage, users:manage
│   ├── admin:*
│   └── system:health, system:metrics, system:logs
│
└── superadmin (Level 4)
    └── *:* (All permissions)
```

#### Permission Format
- **Resource:Action**: `photos:create`, `users:manage`
- **Wildcards**: `photos:*`, `*:manage`, `*:*`
- **Service Integration**: Photo service checks permissions via auth service

### Security Compliance Testing

#### OWASP Top 10 Compliance

PhotoShare includes automated tests for all OWASP Top 10 security risks:

1. **A01: Injection** - SQL injection, NoSQL injection, command injection tests
2. **A02: Broken Authentication** - Session management, password policy tests
3. **A03: Sensitive Data Exposure** - Encryption, data leakage tests
4. **A04: XML External Entities** - Not applicable (JSON API)
5. **A05: Broken Access Control** - Authorization, privilege escalation tests
6. **A06: Security Misconfiguration** - Configuration security tests
7. **A07: Cross-Site Scripting** - XSS prevention tests
8. **A08: Insecure Deserialization** - Input validation tests
9. **A09: Vulnerable Components** - Dependency scanning with Safety
10. **A10: Insufficient Logging** - Audit logging tests

#### Security Test Suite

```bash
# Full security assessment
python tests/run_security_tests.py

# Quick critical security check
python tests/run_security_tests.py --quick

# Static security analysis
python tests/run_security_tests.py --static-only
```

**Security Tests Include:**
- **Static Analysis**: Bandit code scanning for security issues
- **Dependency Scanning**: Safety checks for vulnerable packages
- **Dynamic Testing**: Runtime security vulnerability testing
- **RBAC Testing**: Permission boundary and escalation tests
- **Authentication Testing**: JWT security and session management
- **Input Validation**: SQL injection, XSS, and other injection tests

#### Compliance Reports

Security tests generate comprehensive reports:
- **Security Assessment Report**: Overall security score and recommendations
- **Vulnerability Report**: Detailed findings with severity levels
- **Compliance Matrix**: OWASP compliance status
- **Remediation Guide**: Step-by-step fix recommendations

### Production Security Checklist

Before deploying to production:

- [ ] **SSL/TLS**: Valid certificates installed and HTTPS enforced
- [ ] **Secrets Management**: Strong passwords and JWT secrets configured
- [ ] **Database Security**: Encryption at rest and in transit enabled
- [ ] **Network Security**: Firewall configured, unnecessary ports closed
- [ ] **Monitoring**: Security event logging and alerting enabled
- [ ] **Backup Security**: Encrypted backups with secure storage
- [ ] **Access Control**: Administrative access properly restricted
- [ ] **Update Process**: Security update procedure established
- [ ] **Incident Response**: Security incident response plan ready
- [ ] **Compliance Testing**: All security tests passing

---

## 🌍 Production Deployment

PhotoShare includes a comprehensive production deployment system with automation, monitoring, and maintenance tools.

### Production Architecture

```
Internet
    │
    ▼
┌─────────────────┐
│   Load Balancer │ (Optional: AWS ALB, CloudFlare)
│   DNS/CDN       │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│      NGINX      │ ◄── SSL Termination, Rate Limiting
│   Reverse Proxy │     Security Headers, Caching
└─────────┬───────┘
          │
    ┌─────┼─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│ Auth    │ │ Photo   │ ◄── Horizontal Scaling
│ Service │ │ Service │     Multiple Replicas  
│ x2      │ │ x4      │     Auto-restart
└─────────┘ └─────────┘
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│ Auth DB │ │Photo DB │ ◄── Persistent Storage
│ Primary │ │ Primary │     Backup Strategy
└─────────┘ └─────────┘
    │           │
    └─────┬─────┘
          ▼
    ┌─────────┐
    │  Redis  │ ◄── Session Storage
    │ (Cache) │     Rate Limiting
    └─────────┘
```

### Quick Production Deployment

```bash
# 1. Clone and configure
git clone https://github.com/your-org/photo-share-consul.git
cd photo-share-consul

# 2. Configure production environment
cp .env.production.template .env.production
# Edit .env.production with your production values

# 3. Set up SSL certificates (if using HTTPS)
mkdir -p config/ssl
# Copy your SSL certificates to config/ssl/

# 4. Deploy with automation script
./deploy-production.sh

# 5. Verify deployment
curl https://yourdomain.com/health
```

### Production Configuration

#### Environment Variables (`.env.production`)

```bash
# CRITICAL: Change these values for production!
JWT_SECRET_KEY=your-super-secure-256-bit-jwt-secret
AUTH_DB_PASSWORD=ultra-secure-auth-password
APP_DB_PASSWORD=ultra-secure-app-password
REDIS_PASSWORD=secure-redis-password

# Domain and SSL
DOMAIN=yourdomain.com
PROTOCOL=https
ALLOWED_ORIGINS=https://yourdomain.com

# Security
RATE_LIMIT_ENABLED=true
SECURITY_HEADERS_ENABLED=true
HSTS_MAX_AGE=31536000

# Email (for verification emails)
SMTP_HOST=smtp.your-provider.com
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=your-smtp-password

# Monitoring
ENABLE_METRICS=true
BACKUP_ENABLED=true
```

#### SSL/TLS Setup

**Option 1: Let's Encrypt (Recommended)**
```bash
# Install certbot
sudo apt install certbot

# Get certificates
certbot certonly --standalone -d yourdomain.com

# Copy certificates
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem config/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem config/ssl/
```

**Option 2: Custom Certificates**
```bash
# Copy your certificates
cp your-certificate.pem config/ssl/fullchain.pem
cp your-private-key.pem config/ssl/privkey.pem
```

### Production Management

PhotoShare includes comprehensive production management tools:

#### Production Maintenance Script

```bash
# Service status and monitoring
./production-maintenance.sh status
./production-maintenance.sh health
./production-maintenance.sh monitor

# Service management
./production-maintenance.sh restart
./production-maintenance.sh scale photo-share-app 6
./production-maintenance.sh logs auth-service

# Backup and maintenance
./production-maintenance.sh backup
./production-maintenance.sh update
./production-maintenance.sh cleanup
```

#### Monitoring & Alerting

Production deployment includes:
- **Prometheus**: Metrics collection from all services
- **Grafana**: Visual dashboards for monitoring
- **Alert Manager**: Automated alerting for issues
- **Log Aggregation**: Centralized log collection
- **Health Checks**: Automated service health monitoring

#### Backup Strategy

```bash
# Automated daily backups
./production-maintenance.sh backup

# Backup includes:
# - Database dumps (auth + photo data)
# - Photo file storage
# - Configuration files
# - SSL certificates
```

#### Scaling Services

```bash
# Scale based on load
./production-maintenance.sh scale auth-service 3
./production-maintenance.sh scale photo-share-app 8

# Monitor resource usage
./production-maintenance.sh monitor
```

### Production Security

#### Network Security
- **Firewall**: Only ports 80, 443, and SSH open
- **VPN**: Administrative access via VPN only
- **Network Segmentation**: Services isolated in Docker networks
- **DDoS Protection**: Rate limiting and connection limits

#### Data Security
- **Encryption at Rest**: Database encryption enabled
- **Encryption in Transit**: HTTPS/TLS for all connections
- **Backup Encryption**: Encrypted backup storage
- **Key Management**: Secure secret management

#### Access Control
- **Service Accounts**: Non-root containers
- **Database Access**: Restricted database users
- **Administrative Access**: SSH key authentication only
- **Audit Logging**: All administrative actions logged

### High Availability Setup

For mission-critical deployments:

#### Multi-Node Setup
```bash
# Primary node (with database)
./deploy-production.sh --mode primary

# Secondary nodes (app services only)  
./deploy-production.sh --mode secondary --primary-db primary-node-ip
```

#### Database Replication
```bash
# Set up database replication
./production-maintenance.sh setup-replication
```

#### Load Balancing
```bash
# Configure load balancer
# Point to multiple PhotoShare instances
# Health check endpoints: /health
```

---

## 🚨 Troubleshooting

Common issues and their solutions when working with PhotoShare.

### Development Issues

#### Services Won't Start
```bash
# Check if ports are in use
netstat -tulpn | grep :8000
netstat -tulpn | grep :8001

# Kill processes using ports
sudo kill -9 $(lsof -t -i:8000)
sudo kill -9 $(lsof -t -i:8001)

# Restart Docker
sudo systemctl restart docker
docker compose -f docker-compose.separated.yml up --build
```

#### Database Connection Issues
```bash
# Check database logs
docker compose -f docker-compose.separated.yml logs auth-db
docker compose -f docker-compose.separated.yml logs app-db

# Reset databases (WARNING: Deletes data)
docker compose -f docker-compose.separated.yml down -v
docker compose -f docker-compose.separated.yml up --build

# Manual database connection test
docker compose -f docker-compose.separated.yml exec auth-db psql -U auth_user -d auth_service
```

#### JWT Token Issues
```bash
# Check JWT configuration in logs
docker compose -f docker-compose.separated.yml logs auth-service | grep JWT

# Verify JWT secret consistency between services
grep JWT_SECRET .env.auth-service
grep JWT_SECRET .env.photoshare

# Test JWT token generation
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123!"}'
```

### Testing Issues

#### Tests Failing Due to Services
```bash
# Ensure services are running before tests
docker compose -f docker-compose.separated.yml up -d

# Wait for services to be ready
curl -f http://localhost:8001/health
curl -f http://localhost:8000/health

# Run tests with verbose output
python tests/run_tests.py --categories integration --no-coverage
```

#### Coverage Below Threshold
```bash
# Identify uncovered code
pytest --cov=services --cov-report=html:tests/coverage/html
open tests/coverage/html/index.html

# Run tests without coverage requirement
pytest tests/ --no-cov

# Check specific module coverage
pytest tests/unit/auth-service/ --cov=services.auth-service
```

### Production Issues

#### SSL Certificate Problems
```bash
# Check certificate validity
openssl x509 -in config/ssl/fullchain.pem -text -noout

# Test certificate chain
openssl verify -CAfile config/ssl/fullchain.pem config/ssl/fullchain.pem

# Renew Let's Encrypt certificates
certbot renew --dry-run
```

#### Performance Issues
```bash
# Check resource usage
./production-maintenance.sh monitor

# Scale services if needed
./production-maintenance.sh scale photo-share-app 6

# Check database performance
./production-maintenance.sh logs app-db | grep "slow query"
```

#### Service Discovery Issues
```bash
# Check service connectivity
docker compose -f docker-compose.production.yml exec photo-share-app curl auth-service:8000/health

# Restart services with fresh network
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.production.yml up -d
```

### Security Issues

#### Failed Security Tests
```bash
# Run security tests with detailed output
python tests/run_security_tests.py --quick

# Check for vulnerable dependencies
pip list --outdated
safety check

# Review security configuration
python tests/run_security_tests.py --static-only
```

### Getting Help

#### Debug Information Collection
```bash
# Collect system information
docker version
docker compose version
curl -s http://localhost:8001/health | jq .
curl -s http://localhost:8000/health | jq .

# Collect service logs
docker compose -f docker-compose.separated.yml logs > debug-logs.txt

# Run diagnostic tests
python tests/run_tests.py --categories integration > test-output.txt
```

#### Common Log Locations
- **Service logs**: `docker compose logs`
- **Test reports**: `tests/reports/`
- **Coverage reports**: `tests/coverage/html/index.html`
- **Security reports**: `tests/reports/security/`
- **Production logs**: `/var/log/photoshare/` (in production)

---

## 🎉 Conclusion

Congratulations! You now have a comprehensive understanding of PhotoShare. Here's what you've learned:

✅ **Project Understanding**: Modern microservices photo sharing platform  
✅ **Architecture Knowledge**: Separated services with security-first design  
✅ **Development Setup**: Local development environment ready in minutes  
✅ **Testing Framework**: Comprehensive testing with security compliance  
✅ **Production Deployment**: Enterprise-ready deployment with monitoring  
✅ **Security Implementation**: OWASP-compliant with RBAC and comprehensive protection  

### Next Steps

1. **Start Development**: Set up your local environment and explore the APIs
2. **Run Tests**: Execute the test suite to understand the system behavior  
3. **Security Review**: Run security tests to understand the compliance framework
4. **Production Planning**: Review the production deployment guide for your infrastructure
5. **Contribute**: Follow the testing and security guidelines for contributions

### Key Resources

- **API Documentation**: http://localhost:8001/docs (Auth), http://localhost:8000/docs (Photos)
- **Test Suite**: `python tests/run_tests.py`
- **Security Tests**: `python tests/run_security_tests.py`
- **Production Guide**: `PRODUCTION_DEPLOYMENT.md`
- **Development Guide**: `CLAUDE.md`

### Support

- **Testing Issues**: Check `tests/README.md`
- **Deployment Issues**: Review `PRODUCTION_DEPLOYMENT.md`  
- **Security Questions**: Run security compliance tests
- **Architecture Questions**: Review this guide's architecture section

---

**Welcome to PhotoShare!** 🎉 You're ready to build, test, and deploy a production-ready photo sharing platform with enterprise-grade security and scalability.