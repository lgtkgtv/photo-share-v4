# Photo Share Service
**Version**: 2.3.0-monitoring  
**Architecture**: Production-Ready Single-Service FastAPI Application  
**Status**: ✅ **Production Ready**  

A comprehensive photo sharing service with JWT authentication, email verification, role-based access control, and enterprise-grade security features.

---

## 🚀 Quick Start

### Prerequisites
- **Python**: 3.11+ (managed via UV)
- **Docker**: Latest version with Docker Compose
- **Git**: For cloning the repository

### Setup & Launch
```bash
# 1. Clone and setup environment
git clone <repository-url>
cd photo-share-consul
cp .env.example .env

# 2. Generate secure secrets
python3 scripts/generate-jwt-secrets.py --update-env .env

# 3. Start services
docker compose up --build

# 4. Verify deployment
curl http://localhost:8000/health
```

**Service Available**: http://localhost:8000  
**API Documentation**: http://localhost:8000/docs  
**Metrics**: http://localhost:8000/metrics  

---

## 📋 Project Overview

### Architecture
- **Single-Service Design**: FastAPI application with PostgreSQL
- **Security-First**: JWT authentication, email verification, RBAC
- **Performance Optimized**: Memory caching, async operations
- **Production-Ready**: Comprehensive monitoring and testing

### Key Features
✅ **User Management**: Registration, email verification, JWT authentication  
✅ **Photo Management**: Upload, storage, public/private sharing  
✅ **Security**: Rate limiting, input validation, OWASP compliance  
✅ **Performance**: Memory caching, query optimization  
✅ **Monitoring**: Prometheus metrics, health checks  
✅ **Testing**: Comprehensive test suite across 7 categories  

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System architecture and design |
| **[ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md)** | Environment configuration guide |
| **[TESTING_DEPLOYMENT_GUIDE.md](TESTING_DEPLOYMENT_GUIDE.md)** | Testing and deployment procedures |
| **[PRODUCTION_READINESS.md](PRODUCTION_READINESS.md)** | Production deployment checklist |
| **[CLAUDE.md](CLAUDE.md)** | Developer guidance |

---

## 🧪 Testing

### Test Framework
- **Test Environment**: UV-managed Python 3.11.9
- **Test Categories**: 7 comprehensive test categories
- **Coverage**: HTML, XML, and terminal reporting

### Running Tests

#### Essential Test Commands
```bash
# Complete test suite with coverage
python3 tests/scripts/run_tests_uv.py

# Specific test categories  
python3 tests/scripts/run_tests_uv.py --categories unit integration security
```

#### API Testing (requires running services)
```bash
bash scripts/api-tests/test-auth-flow.sh
bash scripts/api-tests/test-email-verification.sh
bash scripts/api-tests/test-photo-upload.sh
```

#### Security Validation
```bash
# Security compliance validation (OWASP, GDPR, SSL)
python3 tests/scripts/run_security_compliance.py --generate-certificates

# Complete security audit
python3 tests/scripts/run_security_audit.py
```

---

## 🔧 Development

### Environment Configuration

#### Development Environment
- **File**: `.env` (copy from `.env.example`)
- **Database**: PostgreSQL via Docker
- **Purpose**: Development and production runtime

#### Testing Environment  
- **File**: `tests/.env.test` (automatically used during testing)
- **Database**: In-memory SQLite + test PostgreSQL
- **Purpose**: Automated testing

### Development Workflow
```bash
# Setup development environment
cp .env.example .env
python3 scripts/generate-jwt-secrets.py --update-env .env

# Start development services
docker compose up --build

# Run tests during development
python3 tests/scripts/run_tests_uv.py --categories unit integration

# Validate configuration
python3 scripts/validate-config.py --env .env
```

---

## 🔒 Security

### Security Features
- **JWT Authentication**: Secure token-based authentication
- **Email Verification**: Required with 24-hour expiration  
- **Role-Based Access Control**: Flexible RBAC system
- **Rate Limiting**: Advanced DDoS protection
- **Input Validation**: Comprehensive sanitization
- **File Security**: Upload validation and scanning
- **Compliance**: OWASP and GDPR compliant

### Security Validation
```bash
# Complete security test suite
python3 tests/scripts/run_security_compliance.py --generate-certificates
python3 tests/scripts/run_security_audit.py
```

---

## ⚡ Performance

### Performance Features
- **Memory Caching**: High-performance in-memory cache
- **Query Optimization**: Database query monitoring and optimization
- **Async Operations**: Fully asynchronous request handling
- **Resource Management**: Intelligent memory and CPU usage

### Performance Testing
```bash
# Performance and load testing
python3 tests/scripts/run_tests_uv.py --categories performance
python3 tests/performance/test_load_testing.py
```

---

## 📊 Monitoring

### Monitoring Features
- **Prometheus Integration**: Comprehensive metrics collection
- **Health Checks**: Service and dependency monitoring
- **Performance Dashboards**: Real-time system status
- **Error Tracking**: Detailed error monitoring and alerting
- **Security Monitoring**: Security event tracking and analysis

### Monitoring Endpoints
- **Health**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **System Status**: `GET /api/platform/stats`
- **Performance**: `GET /api/platform/performance`

### Access Monitoring Dashboards
```bash
# Start monitoring services
docker compose up prometheus grafana -d

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

---

## 🚀 Production Deployment

### Pre-Deployment Validation
```bash
# 1. Configuration validation
python3 scripts/validate-config.py --env .env --production

# 2. Security validation
python3 tests/scripts/run_security_compliance.py --production

# 3. Complete test suite
python3 tests/scripts/run_tests_uv.py

# 4. Performance validation
python3 tests/performance/test_load_testing.py
```

### Production Deployment
```bash
# Deploy to production
./scripts/deploy-production.sh

# Post-deployment validation
bash scripts/api-tests/test-auth-flow.sh
python3 scripts/health-check.py --production
```

### Production Requirements
- **Environment**: Production `.env` with secure secrets
- **Database**: PostgreSQL with persistent storage
- **Monitoring**: Prometheus and Grafana for observability
- **Security**: SSL certificates and secure configurations

---

## 🆘 Troubleshooting

### Common Issues & Solutions

#### Environment Setup
```bash
# Database connection issues
docker compose up db -d && sleep 5
python3 -c "from database import engine; print('DB Connection: OK')"

# Generate new JWT secrets
python3 scripts/generate-jwt-secrets.py --update-env .env

# Fix permissions
chmod +x scripts/*.sh
```

#### Service Issues
```bash
# Service health check
curl http://localhost:8000/health

# Clean restart
docker compose down && docker system prune -f
docker compose up --build
```

#### Testing Issues
```bash
# Clean test environment
rm -rf tests/reports/* tests/coverage/*
cd tests && rm -rf env && uv venv env --python 3.11
source env/bin/activate && uv pip install -r ../services/photoshare/requirements_test.txt
```

### Support Resources
- **Test Reports**: `tests/reports/` directory
- **Coverage Reports**: `tests/coverage/html/index.html`
- **Security Reports**: `tests/security_reports/` directory  
- **Documentation**: All `.md` files in project root

---

## 🤝 Contributing

### Development Process
1. Fork and clone the repository
2. Setup development environment using instructions above
3. Make changes and test thoroughly
4. Ensure all tests pass and security requirements are met
5. Submit pull request with clear description

### Code Quality Standards
- **Tests**: All new features must include tests
- **Security**: Must pass security compliance tests  
- **Performance**: Must meet performance benchmarks
- **Documentation**: Update relevant documentation

---

## 📄 License

This project implements a comprehensive photo sharing service with enterprise-grade security and performance features.

---

## 🎯 Current Status

**Architecture**: Production-ready single-service FastAPI application  
**Security**: Enterprise-grade with full OWASP and GDPR compliance  
**Testing**: Comprehensive test suite with multiple categories  
**Documentation**: Complete setup, deployment, and operational guides  
**Performance**: Optimized with caching and async operations  
**Monitoring**: Full observability with Prometheus and Grafana  

**Ready for**: Production deployment with enterprise security and performance requirements.