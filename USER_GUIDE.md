# PhotoShare Complete User Guide
# =============================

**Welcome to PhotoShare!** This comprehensive guide will help you understand, set up, develop, test, and deploy the PhotoShare separated microservices platform. Whether you're a new developer, DevOps engineer, or just exploring the codebase, this guide has everything you need.

**Version**: 2.4.0-separated-auth  
**Last Updated**: August 24, 2025  
**Status**: Production Ready - Zero Known Vulnerabilities

---

## 📖 Table of Contents

1. [🎯 Project Overview](#-project-overview)
2. [🏗️ Architecture Deep Dive](#️-architecture-deep-dive)  
3. [📁 Project Structure](#-project-structure)
4. [⚙️ Environment Configuration](#️-environment-configuration)
5. [🐳 Docker Compose Explained](#-docker-compose-explained)
6. [🛠️ Development Setup](#️-development-setup)
7. [🧪 Testing Framework](#-testing-framework)
8. [🔐 Security & Compliance](#-security--compliance)
9. [🚀 Production Deployment](#-production-deployment)
10. [🔧 Troubleshooting](#-troubleshooting)
11. [📚 API Reference](#-api-reference)
12. [🎓 Advanced Usage](#-advanced-usage)

---

## 🎯 Project Overview

PhotoShare is a **production-ready photo sharing platform** built with modern microservices architecture, featuring comprehensive security, scalability, and enterprise-grade features with completely separated authentication and application services.

### What PhotoShare Does
- 📷 **Photo Management**: Upload, organize, and share high-quality photos with metadata
- 👥 **User Management**: Secure registration, authentication, and role-based access control
- 🔐 **Enterprise Security**: SSO, 2FA, RBAC, and JWT-based authentication with dedicated auth service
- 📱 **API-First Design**: RESTful APIs ready for web, mobile, and third-party integrations
- 🎛️ **Admin Controls**: User management, content moderation, and comprehensive system monitoring
- 🛡️ **Security Focus**: Complete service separation with defense-in-depth security architecture

### Key Features & Capabilities

#### Separated Microservices Architecture
- **Authentication Service** (Port 8001): Dedicated user auth, SSO, 2FA, RBAC
- **Application Service** (Port 8000): Photo management, file storage, sharing features
- **Database Isolation**: Complete separation of auth and application data
- **Inter-Service Security**: JWT-based service-to-service authentication

#### Advanced Security Features
- Multi-factor authentication (TOTP, SMS, backup codes)
- Single Sign-On (SSO) with multiple provider support
- Role-based access control with granular permissions
- Real-time security monitoring and threat detection
- Comprehensive audit trails and tamper-proof logging
- Automated security scanning and vulnerability management

#### Enterprise-Grade Capabilities
- High availability with auto-scaling support
- Comprehensive monitoring with Prometheus and Grafana
- Automated backup and disaster recovery
- GDPR compliance and data protection
- Performance optimization with intelligent caching
- Container security and vulnerability scanning

---

## 🏗️ Architecture Deep Dive

### System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PhotoShare Platform                            │
├─────────────────────┬───────────────────────┬─────────────────────┤
│   Auth Service      │   Application Service │   Infrastructure    │
│   (Port 8001)       │   (Port 8000)        │                     │
├─────────────────────┼───────────────────────┼─────────────────────┤
│ • User Registration │ • Photo Upload        │ • NGINX Proxy       │
│ • JWT Management    │ • File Processing     │ • SSL/TLS           │
│ • SSO Integration   │ • Album Organization  │ • Rate Limiting     │
│ • 2FA Systems       │ • Sharing Controls    │ • Load Balancing    │
│ • RBAC Management   │ • Search Features     │ • WAF Protection    │
│ • Session Security  │ • Analytics           │ • Monitoring        │
├─────────────────────┼───────────────────────┼─────────────────────┤
│   Auth Database     │   App Database        │   Shared Services   │
│   (Port 5433)       │   (Port 5432)        │                     │
│ • users             │ • photos              │ • Redis Cache       │
│ • sessions          │ • albums              │ • Prometheus        │
│ • roles             │ • comments            │ • Grafana           │
│ • permissions       │ • shares              │ • Log Aggregation   │
│ • 2fa_devices       │ • analytics           │ • Backup Systems    │
│ • sso_accounts      │ • metadata            │                     │
└─────────────────────┴───────────────────────┴─────────────────────┘
```

### Service Responsibilities

#### Authentication Service (auth-service)
**Primary Functions:**
- User account lifecycle management
- Authentication and authorization  
- JWT token generation and validation
- Multi-factor authentication (2FA)
- Single Sign-On (SSO) provider integration
- Role-based access control (RBAC)
- Session management and security

**Security Features:**
- Secure password hashing with BCrypt
- JWT token signing and verification
- Rate limiting and brute force protection
- Account lockout and security monitoring
- Audit logging for all auth events

#### Application Service (photo-share-app)
**Primary Functions:**
- Photo upload and storage management
- Image processing and thumbnail generation
- Album creation and organization
- Photo sharing and permissions
- Search and discovery features
- Performance optimization and caching

**Integration Features:**
- JWT token validation with auth service
- User authorization verification
- File security scanning and validation
- Performance metrics and monitoring
- Inter-service communication security

### Data Flow Architecture

```
1. User Authentication Flow:
   Browser → NGINX → Auth Service → Auth Database
                  ↓
             JWT Token Generated
                  ↓
   Browser ← NGINX ← Auth Service

2. Photo Upload Flow:
   Browser → NGINX → App Service → Auth Service (token validation)
                  ↓                      ↓
            File Storage            Auth Database
                  ↓
            App Database (metadata)

3. Inter-Service Communication:
   App Service ←→ Auth Service (JWT validation)
        ↓               ↓
   App Database    Auth Database
```

---

## 📁 Project Structure

### Directory Organization

```
photo-share-consul/
├── 📋 Configuration Files
│   ├── docker-compose.separated.yml      # Main deployment configuration
│   ├── .env.auth-service                 # Auth service environment variables
│   ├── .env.application                  # Application service environment  
│   └── CLAUDE.md                         # Development guidance
│
├── 🔐 Security & Documentation
│   ├── THREAT_MODEL.md                   # Comprehensive threat model
│   ├── WEBAPP_ADMIN_SECURITY_GUIDE.md    # Security operations guide
│   ├── USER_GUIDE.md                     # This comprehensive guide
│   └── README.md                         # Quick start documentation
│
├── 🏗️ Services Directory
│   ├── auth-service/                     # Authentication microservice
│   │   ├── main.py                       # FastAPI auth service entry point
│   │   ├── auth_database.py              # User database and models
│   │   ├── auth_service.py               # Authentication endpoints
│   │   ├── sso_providers.py              # SSO integration (Google, GitHub, etc.)
│   │   ├── two_factor_auth.py            # 2FA implementation
│   │   ├── setup_rbac.py                 # Role and permission setup
│   │   ├── requirements.txt              # Python dependencies
│   │   ├── Dockerfile                    # Container configuration
│   │   └── init-auth-db.sql              # Database initialization
│   │
│   ├── photoshare/                       # Application microservice
│   │   ├── main.py                       # FastAPI app service entry point
│   │   ├── app_database.py               # Application database models
│   │   ├── auth_integration.py           # Auth service integration
│   │   ├── file_storage.py               # Photo storage management
│   │   ├── image_processing.py           # Image processing and thumbnails
│   │   ├── security_monitoring.py        # Security monitoring system
│   │   ├── performance_simple.py         # Caching and optimization
│   │   ├── requirements.txt              # Python dependencies
│   │   ├── Dockerfile.separated          # Container configuration
│   │   └── init-app-db.sql              # Database initialization
│   │
│   └── shared/                          # Shared utilities and libraries
│       └── security.py                  # Common security functions
│
├── 🧪 Testing Infrastructure
│   ├── tests/                           # Comprehensive test suite
│   │   ├── unit/                        # Unit tests for individual components
│   │   ├── integration/                 # Service integration tests
│   │   ├── functional/                  # End-to-end workflow tests
│   │   └── security/                    # Security compliance tests
│   │
│   ├── api-integration-tests/           # API workflow validation
│   │   ├── test-auth-flow.sh            # Authentication workflow testing
│   │   ├── test-email-verification.sh   # Email verification testing
│   │   └── test-photo-upload.sh         # Photo management testing
│   │
│   └── operational-security-validation/ # Production security validation
│       ├── test-security-improvements.py # Complete security validation
│       └── [additional security validators]
│
├── 🚀 Deployment & Operations
│   ├── deployment-and-setup-tools/      # Production deployment automation
│   │   ├── deploy-production.sh         # Zero-downtime deployment
│   │   ├── setup-environment.py         # Environment initialization
│   │   ├── generate-jwt-secrets.py      # Cryptographic key generation
│   │   └── security-scan-containers.py  # Container security scanning
│   │
│   ├── monitoring/                      # Monitoring configuration
│   │   ├── prometheus.yml               # Metrics collection config
│   │   ├── grafana/                     # Dashboard configurations
│   │   └── alerts/                      # Alert rules and notifications
│   │
│   └── nginx/                           # Reverse proxy configuration
│       ├── nginx.conf                   # Main NGINX configuration
│       └── ssl/                         # SSL certificate storage
│
└── 🗄️ Data & Storage
    ├── vault-like-secure-storage/       # Cryptographic key vault
    │   ├── jwt_secrets.json             # JWT signing keys
    │   ├── inter_service/               # Service-to-service certificates
    │   └── sessions/                    # Session encryption keys
    │
    └── tamper-proof-audit-storage/      # Audit trail integrity
        └── audit_trail.db               # Tamper-proof audit database
```

### Key File Descriptions

#### Configuration Files
- **`docker-compose.separated.yml`**: Main orchestration file for all services
- **`.env.auth-service`**: Authentication service environment variables and secrets
- **`.env.application`**: Application service environment variables and configuration

#### Service Implementation
- **`services/auth-service/main.py`**: Authentication service FastAPI application
- **`services/photoshare/main.py`**: Photo sharing service FastAPI application
- **`services/auth-service/auth_service.py`**: Core authentication logic and endpoints
- **`services/photoshare/auth_integration.py`**: Integration with authentication service

#### Security & Monitoring
- **`THREAT_MODEL.md`**: Complete security threat analysis and mitigations
- **`WEBAPP_ADMIN_SECURITY_GUIDE.md`**: Operational security procedures
- **`services/photoshare/security_monitoring.py`**: Real-time security monitoring

---

## ⚙️ Environment Configuration

### Required Environment Files

#### Authentication Service Configuration (`.env.auth-service`)
```bash
# Database Configuration
POSTGRES_USER=auth_user
POSTGRES_PASSWORD=your_secure_auth_password_here
POSTGRES_DB=photo_share_auth
DB_HOST=auth-db
DB_PORT=5432

# JWT Configuration
JWT_SECRET_KEY=your_super_secure_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_AUDIENCE=photoshare-app
JWT_ISSUER=photoshare-auth

# 2FA Configuration
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890
TOTP_ISSUER=PhotoShare

# SSO Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Security Configuration
RATE_LIMIT_PER_MINUTE=60
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION=1800
SECURITY_EMAIL_FROM=security@yourdomain.com
```

#### Application Service Configuration (`.env.application`)
```bash
# Database Configuration
POSTGRES_USER=app_user
POSTGRES_PASSWORD=your_secure_app_password_here
POSTGRES_DB=photo_share_app
DB_HOST=app-db
DB_PORT=5432

# Auth Service Integration
AUTH_SERVICE_URL=http://auth-service:8000
JWT_SECRET_KEY=your_super_secure_jwt_secret_key_here  # Must match auth service
JWT_ALGORITHM=HS256
JWT_AUDIENCE=photoshare-app
JWT_ISSUER=photoshare-auth

# File Storage Configuration
UPLOAD_DIR=/app/storage
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,webp
ENABLE_VIRUS_SCANNING=true

# Performance Configuration
CACHE_TYPE=redis
REDIS_URL=redis://redis-cache:6379/0
CACHE_TIMEOUT=3600

# Security Configuration
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
RATE_LIMIT_PER_MINUTE=100
ENABLE_SECURITY_MONITORING=true

# Monitoring Configuration
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
LOG_LEVEL=INFO
```

### Environment Setup Script
```bash
#!/bin/bash
# setup-environment.sh - Complete environment setup

echo "🔧 Setting up PhotoShare environment..."

# 1. Generate secure JWT secrets
python3 deployment-and-setup-tools/generate-jwt-secrets.py

# 2. Create environment files from templates
cp .env.auth-service.template .env.auth-service
cp .env.application.template .env.application

# 3. Generate database passwords
AUTH_DB_PASS=$(openssl rand -base64 32)
APP_DB_PASS=$(openssl rand -base64 32)

# 4. Update environment files with generated values
sed -i "s/your_secure_auth_password_here/$AUTH_DB_PASS/g" .env.auth-service
sed -i "s/your_secure_app_password_here/$APP_DB_PASS/g" .env.application

# 5. Set proper file permissions
chmod 600 .env.auth-service .env.application

echo "✅ Environment setup complete!"
echo "🔒 Please review and update .env.auth-service and .env.application with your specific configuration"
```

---

## 🐳 Docker Compose Explained

### Service Architecture in Docker

The `docker-compose.separated.yml` file defines our complete microservices architecture:

#### Core Services

```yaml
services:
  # Authentication Service & Database
  auth-service:
    build: ./services/auth-service
    ports: ["8001:8000"]
    environment:
      - ENVIRONMENT=production
    depends_on:
      auth-db: {condition: service_healthy}
    
  auth-db:
    image: postgres:15-alpine
    ports: ["5433:5432"]
    environment:
      - POSTGRES_USER=auth_user
      - POSTGRES_PASSWORD=auth_secure_password_here
      - POSTGRES_DB=photo_share_auth
    
  # Application Service & Database  
  photo-share-app:
    build: 
      context: ./services/photoshare
      dockerfile: Dockerfile.separated
    ports: ["8000:8000"]
    environment:
      - AUTH_SERVICE_URL=http://auth-service:8000
    depends_on:
      app-db: {condition: service_healthy}
      auth-service: {condition: service_healthy}
    
  app-db:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    environment:
      - POSTGRES_USER=app_user
      - POSTGRES_PASSWORD=app_secure_password_here
      - POSTGRES_DB=photo_share_app
```

#### Infrastructure Services

```yaml
  # Reverse Proxy (Optional)
  nginx-proxy:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    profiles: ["proxy"]
    
  # Monitoring Stack (Optional)
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    profiles: ["monitoring"]
    
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    profiles: ["monitoring"]
    
  redis-cache:
    image: redis:7-alpine
    ports: ["6379:6379"]
    profiles: ["monitoring"]
```

### Service Startup Options

#### Basic Services (Auth + App)
```bash
# Start core services only
docker compose -f docker-compose.separated.yml up -d

# View logs
docker compose -f docker-compose.separated.yml logs -f
```

#### With Monitoring Stack
```bash
# Start with Prometheus and Grafana
docker compose -f docker-compose.separated.yml --profile monitoring up -d

# Access Grafana at http://localhost:3000 (admin/admin123)
# Access Prometheus at http://localhost:9090
```

#### With Reverse Proxy
```bash
# Start with NGINX reverse proxy
docker compose -f docker-compose.separated.yml --profile proxy up -d
```

#### Full Production Stack
```bash
# Start everything
docker compose -f docker-compose.separated.yml --profile monitoring --profile proxy up -d
```

---

## 🛠️ Development Setup

### Prerequisites

#### System Requirements
- **Docker**: Version 20.0+ with Docker Compose V2
- **Python**: Version 3.11+ (for local development)
- **Node.js**: Version 18+ (for frontend development)
- **Git**: Latest version
- **curl/jq**: For API testing

#### Hardware Recommendations
- **CPU**: 4+ cores (8+ recommended for full stack)
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 20GB free space
- **Network**: Broadband internet for Docker image downloads

### Quick Start Development Setup

#### 1. Repository Setup
```bash
# Clone the repository
git clone <your-repo-url> photo-share-consul
cd photo-share-consul

# Verify project structure
ls -la
# Should see: services/, docker-compose.separated.yml, CLAUDE.md, etc.
```

#### 2. Environment Configuration
```bash
# Generate JWT secrets and environment files
bash deployment-and-setup-tools/setup-environment.sh

# Review and customize environment files
nano .env.auth-service
nano .env.application
```

#### 3. First-Time Startup
```bash
# Build and start all services
docker compose -f docker-compose.separated.yml up --build -d

# Wait for services to be healthy (may take 2-3 minutes)
docker compose -f docker-compose.separated.yml ps

# All services should show "(healthy)" status
```

#### 4. Verify Installation
```bash
# Test authentication service
curl -s http://localhost:8001/health | jq '.'

# Test application service  
curl -s http://localhost:8000/health | jq '.'

# Both should return {"status": "healthy"}
```

### Development Workflow

#### 1. Code Development
```bash
# Make changes to service code
# Example: Edit services/auth-service/auth_service.py

# Rebuild specific service
docker compose -f docker-compose.separated.yml build auth-service

# Restart service to apply changes
docker compose -f docker-compose.separated.yml restart auth-service
```

#### 2. Database Development
```bash
# Access auth database
docker compose -f docker-compose.separated.yml exec auth-db \
  psql -U auth_user -d photo_share_auth

# Access app database
docker compose -f docker-compose.separated.yml exec app-db \
  psql -U app_user -d photo_share_app

# View database schemas
\dt  # List tables
\d users  # Describe users table
```

#### 3. Live Development with Volume Mounts
```bash
# For active development, mount code directories
# Add to docker-compose.override.yml:
version: '3.8'
services:
  auth-service:
    volumes:
      - ./services/auth-service:/app
  photo-share-app:
    volumes:
      - ./services/photoshare:/app
```

#### 4. Debugging and Logs
```bash
# View service logs
docker compose -f docker-compose.separated.yml logs -f auth-service
docker compose -f docker-compose.separated.yml logs -f photo-share-app

# Debug specific container
docker compose -f docker-compose.separated.yml exec auth-service /bin/bash

# Monitor resource usage
docker stats
```

---

## 🧪 Testing Framework

### Testing Architecture

PhotoShare includes comprehensive testing at multiple levels:

#### 1. Unit Tests (Individual Components)
- **Location**: `tests/unit/`
- **Purpose**: Test individual functions and classes
- **Framework**: pytest with extensive fixtures

```bash
# Run unit tests
cd tests/
python -m pytest unit/ -v

# Run with coverage
python -m pytest unit/ --cov=../services --cov-report=html
```

#### 2. Integration Tests (Service Communication)
- **Location**: `tests/integration/`
- **Purpose**: Test service-to-service communication
- **Framework**: pytest with Docker containers

```bash
# Run integration tests
python -m pytest integration/ -v

# Test specific integration
python -m pytest integration/test_auth_integration.py -v
```

#### 3. Functional Tests (End-to-End Workflows)
- **Location**: `tests/functional/`
- **Purpose**: Test complete user workflows
- **Framework**: pytest with API clients

```bash
# Run functional tests
python -m pytest functional/ -v --tb=short

# Test photo upload workflow
python -m pytest functional/test_photo_workflow.py -v
```

#### 4. Security Tests (Security Compliance)
- **Location**: `tests/security/`
- **Purpose**: Validate security controls and compliance
- **Framework**: Custom security test suite

```bash
# Run security compliance tests
python -m pytest security/ -v

# Run specific security test
python operational-security-validation/test-security-improvements.py
```

### API Integration Testing

#### Authentication Flow Testing
```bash
# Test complete auth flow
bash api-integration-tests/test-auth-flow.sh

# Sample output:
# ✅ User registration successful
# ✅ Email verification working
# ✅ User login successful
# ✅ JWT token validation working
# ✅ Protected endpoint access successful
```

#### Photo Upload Testing
```bash
# Test photo management workflow
bash api-integration-tests/test-photo-upload.sh

# Sample output:
# ✅ Photo upload successful
# ✅ Photo metadata stored
# ✅ Thumbnail generation working
# ✅ Photo access controls working
# ✅ Photo sharing successful
```

### Performance Testing

#### Load Testing Setup
```bash
# Install testing tools
pip install locust pytest-benchmark

# Run performance tests
cd tests/performance/
locust -f locustfile.py --host=http://localhost:8000
```

#### Security Performance Testing
```bash
# Test rate limiting
bash tests/security/test-rate-limiting.sh

# Test authentication performance
python tests/performance/test-auth-performance.py
```

---

## 🔐 Security & Compliance

### Security Architecture Overview

PhotoShare implements a **defense-in-depth** security strategy with multiple layers of protection:

#### Layer 1: Network Security
- **NGINX Reverse Proxy**: SSL/TLS termination, rate limiting
- **Service Isolation**: Separated networks for auth and app services
- **Firewall Rules**: Restricted port access and IP filtering

#### Layer 2: Application Security
- **Input Validation**: Comprehensive sanitization and validation
- **Authentication**: Multi-factor authentication with TOTP and SMS
- **Authorization**: Role-based access control (RBAC) with granular permissions
- **Session Security**: Secure JWT tokens with short expiration

#### Layer 3: Data Security
- **Encryption at Rest**: Database encryption and encrypted file storage
- **Encryption in Transit**: TLS 1.3 for all communications
- **Data Isolation**: Complete separation of authentication and application data
- **Backup Security**: Encrypted backups with integrity verification

#### Layer 4: Monitoring & Response
- **Real-time Monitoring**: Security event detection and alerting
- **Audit Logging**: Tamper-proof audit trails for all actions
- **Incident Response**: Automated threat detection and response
- **Compliance Reporting**: GDPR, SOC 2, and other regulatory compliance

### Security Features Implementation

#### Multi-Factor Authentication (2FA)
```python
# Enable 2FA for user
POST http://localhost:8001/api/auth/2fa/enable
{
  "method": "totp",
  "backup_codes": true
}

# Verify 2FA code
POST http://localhost:8001/api/auth/2fa/verify
{
  "code": "123456",
  "method": "totp"
}
```

#### Role-Based Access Control (RBAC)
```python
# Assign role to user
POST http://localhost:8001/api/auth/users/{user_id}/assign-role
{
  "role": "moderator"
}

# Check user permissions
GET http://localhost:8001/api/auth/users/{user_id}/permissions
```

#### Security Monitoring
```python
# Check security status
GET http://localhost:8000/api/platform/security

# View security events
GET http://localhost:8000/api/security/events

# Security metrics
GET http://localhost:8000/api/security/metrics
```

### Compliance Features

#### GDPR Compliance
```bash
# User data export (Right to Data Portability)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8001/api/auth/users/$USER_ID/export-data

# User data deletion (Right to be Forgotten)
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8001/api/auth/users/$USER_ID/gdpr-delete
```

#### Audit Compliance
```bash
# Generate compliance report
curl -s http://localhost:8000/api/security/compliance-report | jq '.'

# Access audit trail
curl -s http://localhost:8000/api/security/audit-trail | jq '.'
```

---

## 🚀 Production Deployment

### Production Checklist

#### Pre-Deployment Security Review
- [ ] **Environment Variables**: All secrets properly configured
- [ ] **SSL Certificates**: Valid certificates installed and tested
- [ ] **Database Security**: Strong passwords, encrypted connections
- [ ] **Network Security**: Firewall rules and access controls configured
- [ ] **Monitoring**: All monitoring systems operational
- [ ] **Backup Systems**: Automated backups configured and tested

#### Production Environment Setup
```bash
# 1. Clone production repository
git clone <production-repo> photoshare-production
cd photoshare-production

# 2. Configure production environment
cp .env.auth-service.production .env.auth-service
cp .env.application.production .env.application

# 3. Generate production secrets
bash deployment-and-setup-tools/generate-jwt-secrets.py --production

# 4. Configure SSL certificates
mkdir -p nginx/ssl/
# Copy your SSL certificates to nginx/ssl/

# 5. Configure monitoring
bash deployment-and-setup-tools/setup-monitoring.sh
```

#### Production Deployment Script
```bash
#!/bin/bash
# deploy-production.sh - Zero-downtime production deployment

echo "🚀 Starting PhotoShare production deployment..."

# 1. Pre-deployment validation
echo "Validating configuration..."
docker compose -f docker-compose.separated.yml config --quiet
if [ $? -ne 0 ]; then
    echo "❌ Configuration validation failed"
    exit 1
fi

# 2. Security scan
echo "Scanning containers for vulnerabilities..."
python deployment-and-setup-tools/security-scan-containers.py

# 3. Database backup
echo "Creating pre-deployment backup..."
bash deployment-and-setup-tools/backup-databases.py

# 4. Deploy with zero downtime
echo "Deploying services..."
docker compose -f docker-compose.separated.yml up --build -d

# 5. Health check verification
echo "Verifying deployment health..."
sleep 60
curl -f http://localhost:8001/health && curl -f http://localhost:8000/health

if [ $? -eq 0 ]; then
    echo "✅ Production deployment successful!"
else
    echo "❌ Deployment health check failed"
    # Rollback procedures would go here
    exit 1
fi

# 6. Post-deployment verification
echo "Running post-deployment tests..."
bash api-integration-tests/test-auth-flow.sh
bash api-integration-tests/test-photo-upload.sh

echo "🎉 PhotoShare production deployment complete!"
```

### Production Monitoring Setup

#### Prometheus Configuration
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'auth-service'
    static_configs:
      - targets: ['auth-service:8000']
    metrics_path: '/metrics'
    
  - job_name: 'photo-service'
    static_configs:
      - targets: ['photo-share-app:8000']
    metrics_path: '/metrics'
```

#### Grafana Dashboard Setup
```bash
# Start monitoring stack
docker compose -f docker-compose.separated.yml --profile monitoring up -d

# Import PhotoShare dashboards
curl -X POST http://admin:admin123@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/photoshare-dashboard.json
```

#### Security Monitoring Alerts
```yaml
# monitoring/alerts/security-alerts.yml
groups:
  - name: security
    rules:
      - alert: HighFailedLoginRate
        expr: rate(failed_login_attempts[5m]) > 10
        labels:
          severity: warning
        annotations:
          summary: High failed login rate detected
          
      - alert: SuspiciousFileUpload
        expr: rate(blocked_uploads[5m]) > 5
        labels:
          severity: critical
        annotations:
          summary: Suspicious file upload activity detected
```

---

## 🔧 Troubleshooting

### Common Issues & Solutions

#### Issue 1: Service Startup Failures
**Symptoms**: Containers failing to start, health checks failing
**Diagnosis**:
```bash
# Check service status
docker compose -f docker-compose.separated.yml ps

# View startup logs
docker compose -f docker-compose.separated.yml logs auth-service
docker compose -f docker-compose.separated.yml logs photo-share-app
```
**Solution**:
```bash
# Restart with fresh containers
docker compose -f docker-compose.separated.yml down
docker compose -f docker-compose.separated.yml up --build -d
```

#### Issue 2: JWT Token Validation Errors
**Symptoms**: "Invalid token" errors, authentication failures
**Diagnosis**:
```bash
# Check JWT configuration matching
grep JWT_SECRET .env.auth-service
grep JWT_SECRET .env.application

# Verify token format
echo $JWT_TOKEN | cut -d. -f2 | base64 -d | jq '.'
```
**Solution**:
```bash
# Ensure JWT secrets match between services
# Restart services after fixing configuration
docker compose -f docker-compose.separated.yml restart auth-service photo-share-app
```

#### Issue 3: Database Connection Problems
**Symptoms**: Database connection refused, authentication failures
**Diagnosis**:
```bash
# Test database connectivity
docker exec photoshare-auth-db pg_isready -U auth_user
docker exec photoshare-app-db pg_isready -U app_user

# Check database logs
docker compose -f docker-compose.separated.yml logs auth-db
docker compose -f docker-compose.separated.yml logs app-db
```
**Solution**:
```bash
# Restart database containers
docker compose -f docker-compose.separated.yml restart auth-db app-db
sleep 30
docker compose -f docker-compose.separated.yml restart auth-service photo-share-app
```

### Performance Issues

#### Issue: Slow API Response Times
**Diagnosis**:
```bash
# Check service performance metrics
curl -s http://localhost:8000/api/platform/performance | jq '.'

# Monitor resource usage
docker stats --no-stream

# Check for memory/CPU constraints
docker compose -f docker-compose.separated.yml logs | grep -i "memory\|cpu"
```

**Solution**:
```bash
# Enable Redis caching
docker compose -f docker-compose.separated.yml --profile monitoring up -d

# Optimize database queries
# Review slow query logs in database
```

### Security Issues

#### Issue: Unusual Authentication Patterns
**Diagnosis**:
```bash
# Check security monitoring
curl -s http://localhost:8000/api/security/threats | jq '.'

# Review failed login patterns
curl -s http://localhost:8001/api/security/failed-logins | jq '.'
```

**Solution**:
```bash
# Implement additional rate limiting
curl -X POST http://localhost:8001/api/security/emergency-rate-limit \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"ip_ranges": ["suspicious.ip.*"], "duration": 3600}'
```

### Development Debugging

#### Debug Mode Setup
```yaml
# docker-compose.override.yml for development
version: '3.8'
services:
  auth-service:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./services/auth-service:/app
      
  photo-share-app:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./services/photoshare:/app
```

#### Interactive Debugging
```bash
# Access running container for debugging
docker compose -f docker-compose.separated.yml exec auth-service /bin/bash

# Run Python debugger
docker compose -f docker-compose.separated.yml exec auth-service \
  python -m pdb main.py

# Check service internals
docker compose -f docker-compose.separated.yml exec photo-share-app \
  python -c "from auth_integration import AuthIntegration; print(AuthIntegration().health_check())"
```

---

## 📚 API Reference

### Authentication Service API (Port 8001)

#### User Management Endpoints

##### User Registration
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe"
}

Response: 201 Created
{
  "id": 1,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_verified": false,
  "roles": ["user"],
  "permissions": []
}
```

##### User Login
```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecurePassword123!

Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "roles": ["user"]
  }
}
```

#### 2FA Management Endpoints

##### Enable 2FA
```http
POST /api/auth/2fa/enable
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "method": "totp"
}

Response: 200 OK
{
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "secret": "JBSWY3DPEHPK3PXP",
  "backup_codes": ["12345678", "87654321", ...]
}
```

##### Verify 2FA
```http
POST /api/auth/2fa/verify
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "code": "123456",
  "method": "totp"
}

Response: 200 OK
{
  "verified": true,
  "message": "2FA verification successful"
}
```

#### SSO Integration Endpoints

##### Available SSO Providers
```http
GET /api/auth/sso/providers

Response: 200 OK
{
  "providers": [
    {
      "name": "google",
      "display_name": "Google",
      "available": true,
      "login_url": "/api/auth/sso/login/google"
    },
    {
      "name": "github", 
      "display_name": "GitHub",
      "available": true,
      "login_url": "/api/auth/sso/login/github"
    }
  ]
}
```

### Application Service API (Port 8000)

#### Photo Management Endpoints

##### Upload Photo
```http
POST /api/photos/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: (binary photo file)
title: "My awesome photo"
description: "A beautiful sunset"
is_public: true

Response: 201 Created
{
  "id": 1,
  "filename": "photo_20250824_123456.jpg",
  "title": "My awesome photo",
  "description": "A beautiful sunset",
  "content_type": "image/jpeg",
  "file_size": 2048576,
  "is_public": true,
  "upload_date": "2025-08-24T12:34:56Z",
  "thumbnail_url": "/api/photos/1/thumbnail"
}
```

##### List Photos
```http
GET /api/photos/
Authorization: Bearer {access_token}
Query Parameters:
  - page: 1 (optional)
  - limit: 20 (optional)
  - public_only: false (optional)

Response: 200 OK
{
  "photos": [
    {
      "id": 1,
      "filename": "photo_20250824_123456.jpg", 
      "title": "My awesome photo",
      "content_type": "image/jpeg",
      "is_public": true,
      "upload_date": "2025-08-24T12:34:56Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

##### Get Photo Details
```http
GET /api/photos/{photo_id}
Authorization: Bearer {access_token}

Response: 200 OK
{
  "id": 1,
  "filename": "photo_20250824_123456.jpg",
  "title": "My awesome photo", 
  "description": "A beautiful sunset",
  "content_type": "image/jpeg",
  "file_size": 2048576,
  "is_public": true,
  "upload_date": "2025-08-24T12:34:56Z",
  "metadata": {
    "camera": "Canon EOS R5",
    "iso": 100,
    "aperture": "f/8.0",
    "shutter_speed": "1/125"
  }
}
```

##### Download Photo
```http
GET /api/photos/{photo_id}/download
Authorization: Bearer {access_token} (if private photo)

Response: 200 OK
Content-Type: image/jpeg
(Binary image data)
```

#### System Health Endpoints

##### Health Check
```http
GET /health

Response: 200 OK
{
  "status": "healthy",
  "service": "photoshare-app-service", 
  "version": "2.4.0",
  "database": "healthy",
  "auth_service": "healthy"
}
```

##### Platform Statistics
```http
GET /api/platform/stats
Authorization: Bearer {access_token}

Response: 200 OK
{
  "total_users": 1234,
  "total_photos": 5678,
  "storage_used_mb": 15360,
  "auth_service_status": "healthy",
  "database_status": "healthy",
  "uptime_seconds": 86400
}
```

### Security API Endpoints

#### Security Status
```http
GET /api/platform/security
Authorization: Bearer {admin_token}

Response: 200 OK
{
  "security_status": "secure",
  "threat_level": "low",
  "active_threats": 0,
  "security_events_24h": 12,
  "failed_logins_24h": 3,
  "blocked_uploads_24h": 0
}
```

#### Security Events
```http
GET /api/security/events
Authorization: Bearer {admin_token}
Query Parameters:
  - hours: 24 (optional)
  - severity: all|low|medium|high|critical (optional)

Response: 200 OK
{
  "events": [
    {
      "id": "evt_123456",
      "timestamp": "2025-08-24T12:34:56Z",
      "severity": "medium",
      "type": "failed_login",
      "source_ip": "192.168.1.100",
      "description": "Multiple failed login attempts"
    }
  ],
  "total": 1
}
```

---

## 🎓 Advanced Usage

### Custom Development Scenarios

#### Adding New Authentication Providers
```python
# services/auth-service/sso_providers.py

class CustomSSOProvider(BaseSSOProvider):
    def __init__(self):
        self.provider_name = "custom_provider"
        self.client_id = os.getenv("CUSTOM_CLIENT_ID")
        self.client_secret = os.getenv("CUSTOM_CLIENT_SECRET")
    
    async def authenticate(self, auth_code: str) -> dict:
        # Implementation for custom authentication
        pass
    
    def get_authorization_url(self) -> str:
        # Return authorization URL
        pass

# Register the provider
sso_manager.register_provider("custom", CustomSSOProvider())
```

#### Custom Permission System
```python
# services/auth-service/setup_rbac.py

async def setup_custom_permissions():
    permissions = [
        {"name": "custom_permission", "description": "Custom functionality access"},
        {"name": "advanced_features", "description": "Advanced features access"}
    ]
    
    for perm in permissions:
        await create_permission(perm["name"], perm["description"])

# Add custom role
async def setup_custom_roles():
    await create_role("premium_user", "Premium user with advanced features")
    await assign_permission_to_role("premium_user", "advanced_features")
```

#### Custom Security Monitoring
```python
# services/photoshare/security_monitoring.py

class CustomSecurityMonitor(SecurityMonitor):
    def __init__(self):
        super().__init__()
        self.custom_rules = []
    
    def add_custom_rule(self, rule_func):
        """Add custom security detection rule"""
        self.custom_rules.append(rule_func)
    
    def _check_custom_threats(self):
        """Check for custom security threats"""
        for rule in self.custom_rules:
            try:
                threats = rule(self.recent_events)
                for threat in threats:
                    self.log_incident(threat)
            except Exception as e:
                logger.error(f"Custom rule error: {e}")

# Usage
security_monitor.add_custom_rule(detect_unusual_upload_patterns)
security_monitor.add_custom_rule(detect_api_abuse)
```

### Integration Examples

#### Frontend Integration (React)
```javascript
// PhotoShare React integration example

import { PhotoShareClient } from './photoshare-client';

const client = new PhotoShareClient({
  authServiceUrl: 'http://localhost:8001',
  appServiceUrl: 'http://localhost:8000'
});

// Authentication
const loginUser = async (email, password) => {
  try {
    const response = await client.auth.login(email, password);
    localStorage.setItem('token', response.access_token);
    return response.user;
  } catch (error) {
    console.error('Login failed:', error);
  }
};

// Photo upload
const uploadPhoto = async (file, metadata) => {
  const token = localStorage.getItem('token');
  try {
    const response = await client.photos.upload(file, metadata, token);
    return response;
  } catch (error) {
    console.error('Upload failed:', error);
  }
};

// 2FA setup
const enable2FA = async () => {
  const token = localStorage.getItem('token');
  const response = await client.auth.enable2FA(token);
  
  // Display QR code for TOTP setup
  document.getElementById('qr-code').src = response.qr_code;
  return response.secret;
};
```

#### Mobile Integration (React Native)
```javascript
// PhotoShare React Native integration

import { PhotoShareMobile } from '@photoshare/mobile-sdk';

const photoshare = new PhotoShareMobile({
  authServiceUrl: 'https://your-auth-service.com',
  appServiceUrl: 'https://your-app-service.com'
});

// Biometric authentication
const loginWithBiometrics = async () => {
  const biometricAuth = await photoshare.auth.checkBiometricSupport();
  if (biometricAuth.available) {
    const result = await photoshare.auth.loginWithBiometric();
    return result;
  }
};

// Photo capture and upload
const captureAndUpload = async () => {
  const photo = await photoshare.camera.capture({
    quality: 0.8,
    maxWidth: 1920,
    maxHeight: 1080
  });
  
  const upload = await photoshare.photos.upload(photo, {
    title: 'Mobile capture',
    auto_process: true,
    location: await photoshare.location.getCurrentLocation()
  });
  
  return upload;
};
```

#### Third-Party API Integration
```python
# External service integration example

from services.photoshare.integrations import ExternalAPIIntegration

class CloudStorageIntegration(ExternalAPIIntegration):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cloudstorge.com/v1"
    
    async def backup_photo(self, photo_id: int, photo_data: bytes):
        """Backup photo to external cloud storage"""
        backup_url = f"{self.base_url}/backup"
        
        response = await self.make_secure_request(
            method="POST",
            url=backup_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            files={"photo": photo_data},
            data={"photo_id": photo_id}
        )
        
        return response.json()
    
    async def sync_user_data(self, user_id: int):
        """Sync user data with external system"""
        sync_url = f"{self.base_url}/users/{user_id}/sync"
        
        user_data = await self.get_user_export_data(user_id)
        response = await self.make_secure_request(
            method="PUT",
            url=sync_url,
            json=user_data,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        return response.status_code == 200

# Register integration
cloud_storage = CloudStorageIntegration(api_key=os.getenv("CLOUD_STORAGE_API_KEY"))
await integration_manager.register("cloud_storage", cloud_storage)
```

### Advanced Security Configuration

#### Custom JWT Configuration
```python
# services/auth-service/jwt_manager.py

class AdvancedJWTManager:
    def __init__(self):
        self.algorithms = ["RS256", "ES256", "HS256"]  # Multiple algorithm support
        self.private_key = self.load_private_key()
        self.public_key = self.load_public_key()
    
    def create_custom_token(self, user_data: dict, custom_claims: dict = None):
        """Create JWT with custom claims"""
        payload = {
            "sub": user_data["uuid"],
            "user_id": user_data["id"],
            "email": user_data["email"],
            "roles": user_data["roles"],
            "permissions": user_data["permissions"],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "aud": "photoshare-app",
            "iss": "photoshare-auth"
        }
        
        if custom_claims:
            payload.update(custom_claims)
        
        return jwt.encode(
            payload, 
            self.private_key, 
            algorithm="RS256",
            headers={"kid": self.get_key_id()}
        )
    
    def validate_advanced_token(self, token: str, required_permissions: list = None):
        """Advanced token validation with permission checking"""
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=self.algorithms,
                audience="photoshare-app",
                issuer="photoshare-auth"
            )
            
            if required_permissions:
                user_permissions = payload.get("permissions", [])
                if not all(perm in user_permissions for perm in required_permissions):
                    raise PermissionError("Insufficient permissions")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
```

---

**🎉 Congratulations!** You now have comprehensive knowledge of the PhotoShare platform. This guide covers everything from basic setup to advanced customization. For additional support, refer to the security guides, API documentation, and troubleshooting sections.

**📞 Need Help?** 
- Check the troubleshooting section first
- Review the security guides for security-related questions  
- Consult the API reference for integration questions
- Refer to the threat model for security architecture questions

**🚀 Happy coding with PhotoShare!**