# Testing & Deployment Guide
**Version**: 2.3.0-monitoring  
**Updated**: August 23, 2025  

## Overview

Comprehensive guide for testing, validation, and deployment of the Photo Share Service. Covers all test suites, code coverage, security certifications, and deployment procedures.

## Quick Start Commands

### 🚀 Essential Commands

```bash
# 1. Complete Development Setup
./scripts/setup-environment.py && docker compose up --build

# 2. Run All Tests with Coverage  
python3 tests/scripts/run_tests_uv.py

# 3. Security Compliance Validation
python3 tests/scripts/run_security_compliance.py --generate-certificates

# 4. Production Readiness Check
./scripts/run-automated-tests.sh && python3 scripts/validate-config.py --env .env
```

## Testing Framework Architecture

### Test Categories & Scripts

| Test Category | Script | Purpose | Duration |
|---------------|--------|---------|----------|
| **Unit Tests** | `tests/scripts/run_tests_uv.py --categories unit` | Individual component testing | ~30s |
| **Integration Tests** | `tests/scripts/run_tests_uv.py --categories integration` | Service interaction testing | ~2min |
| **API Tests** | `scripts/api-tests/*.sh` | Endpoint validation | ~1min |
| **Security Tests** | `tests/scripts/run_security_compliance.py` | Security validation | ~3min |
| **E2E Tests** | `tests/scripts/run_tests_uv.py --categories e2e` | Complete user workflows | ~5min |
| **Performance Tests** | `tests/scripts/run_tests_uv.py --categories performance` | Load testing | ~10min |

### Test Orchestration Scripts

#### 1. Primary Test Runner (UV-Based)
**File**: `tests/scripts/run_tests_uv.py`  
**Environment**: Uses `tests/.env.test`  
**Features**: 
- UV-managed Python 3.11.9 environment
- Comprehensive reporting (JSON, HTML, Coverage)
- Category-based test execution
- Performance metrics collection

```bash
# Run specific test categories
python3 tests/scripts/run_tests_uv.py --categories unit integration
python3 tests/scripts/run_tests_uv.py --categories security
python3 tests/scripts/run_tests_uv.py --categories performance

# Run all tests with verbose output
python3 tests/scripts/run_tests_uv.py --verbose

# Production environment testing
python3 tests/scripts/run_tests_uv.py --stage production
```

#### 2. Comprehensive Test Runner
**File**: `tests/scripts/run_comprehensive_tests.py`  
**Features**:
- Multi-environment testing
- Advanced reporting with recommendations
- Security threshold validation
- Performance benchmarking

```bash
# Development testing
python3 tests/scripts/run_comprehensive_tests.py

# CI/CD pipeline testing
python3 tests/scripts/run_comprehensive_tests.py --stage ci --categories unit integration security

# Production validation
python3 tests/scripts/run_comprehensive_tests.py --stage production --security-threshold 95
```

#### 3. Security Compliance Testing
**File**: `tests/scripts/run_security_compliance.py`  
**Features**:
- OWASP compliance validation
- GDPR compliance testing  
- SSL certificate generation and validation
- Penetration testing simulation

```bash
# Generate SSL certificates and run security tests
python3 tests/scripts/run_security_compliance.py --generate-certificates

# Security audit with detailed reporting
python3 tests/scripts/run_security_audit.py

# Compliance validation only
python3 tests/scripts/run_security_compliance.py --compliance-only
```

## Environment-Specific Testing

### 1. Local Development Testing
**Environment**: Uses `tests/.env.test`  
**Database**: In-memory SQLite + Test PostgreSQL  
**Services**: Mock services for external dependencies

```bash
# Setup test environment
cd tests && source env/bin/activate

# Unit tests (fastest)
python3 scripts/run_tests_uv.py --categories unit

# Integration tests  
python3 scripts/run_tests_uv.py --categories integration

# All tests with coverage
python3 scripts/run_tests_uv.py
```

### 2. Docker Service Integration Testing
**Environment**: Uses `.env` with running services  
**Database**: Real PostgreSQL via Docker  
**Services**: Full service stack

```bash
# Start all services
docker compose up --build -d

# Wait for services to be ready
sleep 10

# Run API tests against running services
bash scripts/api-tests/test-auth-flow.sh
bash scripts/api-tests/test-email-verification.sh  
bash scripts/api-tests/test-photo-upload.sh

# Full system validation
./scripts/run-automated-tests.sh
```

### 3. Production Environment Testing
**Environment**: Uses production `.env` configuration  
**Database**: Production PostgreSQL instance  
**Services**: Production service configuration

```bash
# Validate production configuration
python3 scripts/validate-config.py --env .env

# Production readiness tests
python3 tests/scripts/run_tests_uv.py --stage production

# Security compliance for production
python3 tests/scripts/run_security_compliance.py --production
```

## Code Coverage & Quality

### Coverage Collection
All test scripts automatically collect code coverage:

```bash
# Coverage reports are generated in:
tests/coverage/html/          # HTML coverage report  
tests/coverage/coverage.xml   # XML coverage for CI/CD
tests/reports/               # Test execution reports
```

### Coverage Thresholds
- **Unit Tests**: 90% minimum coverage
- **Integration Tests**: 85% minimum coverage  
- **Overall Project**: 80% minimum coverage

### Quality Gates
```bash
# Check coverage thresholds
python3 scripts/validate-config.py --check-coverage

# Code quality validation  
python3 -m flake8 services/photoshare/
python3 -m mypy services/photoshare/
```

## Security Certifications & Compliance

### Security Testing Framework

#### OWASP Compliance Testing
```bash
# OWASP Top 10 validation
python3 tests/scripts/run_security_compliance.py --owasp

# Detailed OWASP report
python3 tests/security/test_owasp_compliance.py
```

#### GDPR Compliance Testing  
```bash
# GDPR compliance validation
python3 tests/scripts/run_security_compliance.py --gdpr

# Data protection testing
python3 tests/security/test_gdpr_compliance.py
```

#### Penetration Testing
```bash
# Automated penetration tests
python3 tests/security/test_penetration_testing.py

# Fuzz testing
python3 tests/security/test_fuzz_testing.py
```

#### SSL/TLS Certificate Management
```bash
# Generate test certificates
python3 tests/scripts/run_security_compliance.py --generate-certificates

# Certificate validation
python3 scripts/validate-config.py --check-ssl
```

### Security Reporting
Security tests generate comprehensive reports:

```bash
# Security reports location
tests/security_reports/       # Detailed security analysis
tests/ssl_certs/             # Generated certificates
```

## Performance Testing & Benchmarking

### Load Testing
```bash
# Performance test suite
python3 tests/scripts/run_tests_uv.py --categories performance

# Specific load testing
python3 tests/performance/test_load_testing.py

# Benchmark against baseline
python3 scripts/benchmark-performance.py
```

### Performance Metrics
- **API Response Time**: < 200ms (95th percentile)
- **Database Query Time**: < 50ms average
- **File Upload**: < 5s for 10MB files
- **Concurrent Users**: 1000+ simultaneous connections

## Deployment Workflows

### 1. Development Deployment
```bash
# Local development setup
git clone <repository>
cp .env.example .env
# Edit .env with development values
python3 scripts/generate-jwt-secrets.py --update-env .env
docker compose up --build
```

### 2. Staging Deployment
```bash
# Staging environment validation
python3 scripts/validate-config.py --env .env.staging
python3 tests/scripts/run_comprehensive_tests.py --stage staging
./scripts/deploy-staging.sh
```

### 3. Production Deployment
```bash
# Pre-deployment validation
python3 scripts/validate-config.py --env .env.production --production
python3 tests/scripts/run_security_compliance.py --production

# Production deployment
./scripts/deploy-production.sh

# Post-deployment validation
bash scripts/api-tests/test-auth-flow.sh
python3 scripts/health-check.py --production
```

## Continuous Integration Scripts

### CI/CD Pipeline Integration
```bash
# CI test execution (fast)
python3 tests/scripts/run_tests_uv.py --categories unit integration --stage ci

# Security gate (required for merge)
python3 tests/scripts/run_security_compliance.py --ci

# Performance regression testing  
python3 tests/performance/test_load_testing.py --baseline
```

### GitHub Actions / CI Integration
```yaml
# Example CI configuration
- name: Run Test Suite
  run: |
    python3 tests/scripts/run_tests_uv.py --categories unit integration
    python3 tests/scripts/run_security_compliance.py --ci

- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: tests/coverage/coverage.xml
```

## Troubleshooting Testing Issues

### Common Issues & Solutions

#### 1. Environment Setup Issues
```bash
# Python environment problems
cd tests && rm -rf env && uv venv env --python 3.11
source env/bin/activate && uv pip install -r requirements.txt

# Database connection issues
docker compose up db -d && sleep 5
python3 -c "from database import engine; print('DB connection OK')"
```

#### 2. Test Execution Failures  
```bash
# Clear test artifacts
rm -rf tests/reports/* tests/coverage/*

# Restart with clean environment
docker compose down && docker system prune -f
docker compose up --build -d
```

#### 3. Security Test Issues
```bash
# Regenerate certificates
rm -rf tests/ssl_certs/*
python3 tests/scripts/run_security_compliance.py --generate-certificates

# Reset security configurations if needed
cp tests/.env.test tests/.env.test.backup
```

### Debug Mode Testing
```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run tests with verbose output
python3 tests/scripts/run_tests_uv.py --verbose --debug
```

## Test Reports & Artifacts

### Generated Reports
```bash
tests/reports/                    # Test execution reports
├── comprehensive_test_report_*.json    # Detailed test results
├── unit_tests_report.html             # HTML test report
└── test_execution_*.log               # Execution logs

tests/coverage/                   # Code coverage reports  
├── html/                        # HTML coverage report
├── coverage.xml                 # XML coverage (CI/CD)
└── unit_coverage.xml           # Unit test coverage

tests/security_reports/          # Security analysis
├── security_compliance_*.json   # Compliance results
├── owasp_compliance_*.html     # OWASP analysis
└── penetration_test_*.json     # Penetration test results
```

### Report Analysis
```bash
# Open HTML coverage report
open tests/coverage/html/index.html

# View security compliance report  
open tests/security_reports/security_compliance_*.html

# Analyze test performance
python3 scripts/analyze-test-performance.py tests/reports/
```

## Summary

The testing framework provides:

- ✅ **7 Test Categories** with comprehensive coverage
- ✅ **Multiple Test Environments** (development, staging, production)
- ✅ **Security Compliance** (OWASP, GDPR, SSL/TLS)
- ✅ **Performance Validation** with benchmarking
- ✅ **CI/CD Integration** ready scripts
- ✅ **Comprehensive Reporting** in multiple formats

**Key Scripts for Daily Use**:
- `python3 tests/scripts/run_tests_uv.py` - Primary test runner
- `bash scripts/api-tests/*.sh` - API validation
- `python3 tests/scripts/run_security_compliance.py` - Security validation
- `./scripts/run-automated-tests.sh` - Full system check