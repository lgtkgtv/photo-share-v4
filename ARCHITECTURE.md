# Photo Share Service - Architecture Documentation
**Version**: 2.3.0-monitoring  
**Updated**: August 23, 2025  
**Architecture**: Single-Service FastAPI Application  

## 🏗️ Architecture Overview

The Photo Share Service implements a **production-ready single-service architecture** built with FastAPI and PostgreSQL, designed for high performance, security, and maintainability.

### Design Principles

1. **Simplicity**: Single FastAPI service eliminates microservice complexity
2. **Security First**: JWT authentication, input validation, comprehensive security testing
3. **Performance**: Memory caching, query optimization, async operations throughout
4. **Observability**: Prometheus metrics, comprehensive monitoring, health checks
5. **Testability**: Comprehensive test suite across 7 categories

---

## 📁 Project Structure

```
photo-share-consul/
├── services/photoshare/           # 🚀 Main Application
│   ├── main_database.py          # FastAPI app entry point
│   ├── database.py               # PostgreSQL models & repositories
│   ├── security.py               # Security framework (rate limiting, validation)
│   ├── monitoring.py             # Prometheus metrics integration
│   ├── performance_simple.py     # Caching & optimization  
│   ├── error_handling.py         # Error management
│   ├── file_storage.py          # File operations
│   ├── service_discovery.py      # Service registry integration
│   ├── requirements_fixed.txt    # Production dependencies
│   └── requirements_test.txt     # Testing dependencies
│
├── tests/                        # 🧪 Testing Suite
│   ├── env/                      # UV-managed Python 3.11.9 environment
│   ├── scripts/                  # Test orchestration scripts
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests (4 types)
│   ├── security/                 # Security compliance tests  
│   ├── performance/              # Load and performance tests
│   ├── api/                      # API endpoint validation
│   ├── e2e/                      # End-to-end user journey tests
│   ├── infrastructure/           # Container and deployment tests
│   ├── reports/                  # Test execution reports
│   ├── coverage/                 # Code coverage reports
│   └── security_reports/         # Security compliance reports
│
├── scripts/                      # 🔧 Utility Scripts
│   ├── api-tests/               # Shell-based API testing
│   ├── generate-jwt-secrets.py  # Security key generation
│   ├── validate-config.py       # Configuration validation
│   └── deploy-production.sh     # Production deployment
│
├── docker-compose.yml           # 🐳 Service orchestration
├── .env.example                 # Environment configuration template
├── tests/.env.test             # Testing environment configuration
└── CLAUDE.md                   # Development guidance
```

## 🚀 Core Application Architecture

### FastAPI Service Layer (`services/photoshare/`)

#### Application Entry Point
**File**: `main_database.py`
- FastAPI application initialization
- Middleware configuration (CORS, security, monitoring)
- Route registration and API documentation
- Health check endpoints
- Prometheus metrics integration

#### Data Layer  
**File**: `database.py`
- **Models**: User, Photo, Session, Role, Permission (RBAC)
- **Repositories**: UserRepository, PhotoRepository, SessionRepository
- **Database**: PostgreSQL with async SQLAlchemy ORM
- **Features**: Email verification, JWT session management

#### Security Framework
**File**: `security.py`
- **Rate Limiting**: Advanced rate limiting with multiple strategies
- **Input Validation**: Email validation, password strength, file security
- **JWT Security**: Token management and revocation
- **Security Audit**: Event logging and monitoring
- **OWASP Compliance**: Security headers, input sanitization

#### Performance Optimization  
**File**: `performance_simple.py`
- **Memory Caching**: High-performance in-memory cache manager
- **Query Optimization**: Database query monitoring and optimization
- **Resource Management**: Memory usage tracking and optimization
- **Performance Analytics**: Cache hit rates, query performance metrics

#### Monitoring & Observability
**File**: `monitoring.py`  
- **Prometheus Integration**: Request metrics, database metrics, error tracking
- **Monitoring Middleware**: Automatic request/response monitoring
- **Health Dashboards**: System status and performance dashboards
- **Alerting**: Performance threshold monitoring

### API Endpoints

#### Core Endpoints
```
GET  /health                     # Service health check
GET  /api/                      # API information  
GET  /docs                      # Swagger documentation
GET  /metrics                   # Prometheus metrics
```

#### User Management
```
POST /api/users/register        # User registration (creates unverified user)
POST /api/users/request-verification  # Request email verification  
GET  /api/users/verify/{secret} # Email verification with secret link
POST /api/users/login           # User login (returns JWT)
GET  /api/users/me             # Current user info (requires auth)
```

#### Photo Management  
```
POST /api/photos/upload         # Upload photo (requires auth)
GET  /api/photos/              # List user's photos (requires auth)
GET  /api/photos/public        # List public photos
GET  /api/photos/{id}          # Get photo metadata
GET  /api/photos/{id}/download # Download photo file
GET  /api/photos/{id}/url      # Get photo URLs
```

#### Platform & Monitoring
```
GET  /api/platform/stats       # Service statistics
GET  /api/platform/security    # Security status  
GET  /api/platform/performance # Performance metrics
```

## 🗄️ Database Architecture

### PostgreSQL Schema

#### Core Tables
```sql
-- User Management
users (id, email, password_hash, is_verified, is_active, created_at)
email_verifications (id, email, secret, created_at, expires_at)
sessions (id, user_id, token, is_active, created_at, expires_at)

-- Photo Management  
photos (id, user_id, filename, content_type, file_size, title, description, is_public)

-- RBAC (Role-Based Access Control)
roles (id, name, description, is_active)
permissions (id, name, resource, action, description)  
role_permissions (id, role_id, permission_id)
user_roles (id, user_id, role_id)
```

#### Repository Pattern
- **UserRepository**: User CRUD, authentication, verification
- **PhotoRepository**: Photo CRUD, public/private photo management  
- **SessionRepository**: JWT session management, token validation
- **EmailVerificationRepository**: Email verification workflow
- **RoleRepository**: RBAC role management

### Database Features
- **Async Operations**: All database operations use async SQLAlchemy
- **Connection Pooling**: Production-grade connection management
- **Query Optimization**: Monitored and optimized database queries
- **Migration Support**: Alembic database migrations
- **Test Isolation**: Separate test database with SQLite for unit tests

## 🧪 Testing Architecture

### Test Framework

#### Test Categories
| Category | Purpose | Implementation |
|----------|---------|---------------|
| **Unit Tests** | Core component testing | Individual function/class testing |
| **Integration Tests** | Service interaction testing | 4 integration approaches |
| **Security Tests** | Security validation | OWASP, GDPR compliance |  
| **Performance Tests** | Load and performance validation | Benchmarking and stress testing |
| **API Tests** | Endpoint validation | API contract and response testing |
| **E2E Tests** | User journey validation | Complete workflow testing |
| **Infrastructure** | Container testing | Docker and deployment validation |

#### Testing Environment
- **Python Environment**: UV-managed Python 3.11.9  
- **Test Isolation**: Separate test database and configuration
- **Mock Services**: External service mocking for reliable testing
- **Coverage Reporting**: HTML, XML, and terminal coverage reports
- **CI/CD Ready**: Automated test execution for continuous integration

#### Integration Test Types

##### 1. Mock-Based Integration Tests
- Mocked database operations for fast execution
- Complete API endpoint coverage  
- Error handling validation

##### 2. Component Integration Tests  
- Individual service component testing
- Real database operations with SQLite in-memory
- Security, file storage, monitoring integration

##### 3. Contract Testing
- API contract validation framework
- Response schema compliance  
- Backward compatibility testing

##### 4. Full Integration Tests
- End-to-end workflows with real databases
- Complete user registration → verification → photo management
- Concurrent operations testing

## 🔒 Security Architecture

### Multi-Layer Security

#### Authentication & Authorization
- **JWT Authentication**: Secure token-based authentication
- **Email Verification**: Required email verification with 24-hour expiration
- **Session Management**: JWT session tracking with invalidation
- **Role-Based Access Control (RBAC)**: Flexible permission system

#### Security Middleware
- **Rate Limiting**: Advanced rate limiting with IP blocking
- **Input Validation**: Comprehensive input sanitization
- **CORS Configuration**: Secure cross-origin request handling
- **Security Headers**: OWASP-compliant security headers

#### File Security  
- **Upload Validation**: File type, size, and content validation
- **Malware Scanning**: File content security scanning
- **Secure Storage**: Isolated file storage with access controls

#### Security Testing
- **OWASP Compliance**: OWASP Top 10 vulnerability testing
- **GDPR Compliance**: Data protection compliance validation
- **Penetration Testing**: Automated security testing
- **SSL/TLS**: Certificate generation and validation

## 🚀 Performance Architecture

### Caching Strategy
- **Memory Caching**: High-performance in-memory cache
- **Redis Fallback**: Optional Redis integration for scaling  
- **Cache Analytics**: Cache hit rates and performance monitoring
- **Query Caching**: Database query result caching

### Performance Optimization
- **Async Operations**: Fully asynchronous request handling
- **Database Optimization**: Query monitoring and optimization
- **Resource Management**: Memory and CPU usage tracking
- **Performance Monitoring**: Real-time performance metrics

### Scalability Design
- **Connection Pooling**: Database connection optimization
- **Horizontal Scaling**: Service can be horizontally scaled
- **Load Testing**: Performance validation under load
- **Resource Monitoring**: System resource tracking

## 📊 Monitoring & Observability  

### Prometheus Integration
- **Request Metrics**: HTTP request tracking and timing
- **Database Metrics**: Query performance and connection monitoring  
- **Business Metrics**: User registration, photo uploads
- **Error Metrics**: Error rates and types tracking
- **Infrastructure Metrics**: System resources and health

### Health Monitoring
- **Health Checks**: Comprehensive service health validation
- **Dependency Monitoring**: Database, Redis, external service health
- **Performance Dashboards**: Real-time system status
- **Alerting**: Performance threshold alerts

### Logging & Diagnostics
- **Structured Logging**: JSON-formatted application logs
- **Error Tracking**: Detailed error logging and tracking  
- **Performance Profiling**: Application performance analysis
- **Audit Logging**: Security event logging

## 🐳 Deployment Architecture

### Docker Configuration
```yaml
services:
  backend:          # Main FastAPI application
  db:              # PostgreSQL database  
  redis:           # Redis cache (optional)
  prometheus:      # Metrics collection
  grafana:         # Monitoring dashboards
```

### Environment Management
- **Development**: `.env` with development configurations
- **Testing**: `tests/.env.test` with test-specific settings
- **Production**: `.env` with production security configurations

### Service Integration  
- **Platform Services**: Integration with external platform services
- **Service Discovery**: Consul integration for service registry
- **Load Balancing**: Ready for load balancer integration
- **Health Checks**: Docker health check integration

## 🔧 Development Workflow

### Setup & Development
```bash
# Environment setup
cp .env.example .env
python3 scripts/generate-jwt-secrets.py --update-env .env
docker compose up --build

# Testing
python3 tests/scripts/run_tests_uv.py
bash scripts/api-tests/test-auth-flow.sh

# Security validation  
python3 tests/scripts/run_security_compliance.py --generate-certificates
```

### Code Quality
- **Code Coverage**: Comprehensive coverage requirement with detailed reporting
- **Static Analysis**: Type checking, linting, security scanning
- **Security Compliance**: OWASP and GDPR compliance testing
- **Performance Testing**: Load testing and benchmarking

## 📈 Production Readiness

### Production Features
- ✅ **Architecture**: Production-ready single service design
- ✅ **Security**: Comprehensive security implementation  
- ✅ **Testing**: Comprehensive test suite across 7 categories
- ✅ **Monitoring**: Full Prometheus integration
- ✅ **Performance**: Memory caching and optimization
- ✅ **Documentation**: Complete operational documentation

### Production Deployment Ready
- **JWT Authentication** with email verification
- **Role-Based Access Control** (RBAC)
- **File Upload and Management** with security validation
- **Performance Optimization** with intelligent caching
- **Comprehensive Monitoring** with Prometheus
- **Security Compliance** testing (OWASP, GDPR)
- **Load Testing** and performance validation

### Scalability Considerations
- **Horizontal Scaling**: Service can be scaled horizontally
- **Database Scaling**: PostgreSQL read replicas ready
- **Caching Strategy**: Memory + Redis for high performance  
- **Load Balancing**: Ready for load balancer integration

## 🎯 Architecture Strengths

1. **Simplicity**: Single service eliminates microservice complexity
2. **Security**: Multi-layer security with comprehensive testing
3. **Performance**: Async operations with intelligent caching
4. **Observability**: Full monitoring and metrics integration  
5. **Testability**: Comprehensive test suite with multiple test types
6. **Maintainability**: Clean code structure with clear separation of concerns
7. **Production-Ready**: All components designed for production deployment

The architecture successfully balances simplicity with enterprise-grade features, providing a robust foundation for a production photo sharing service.