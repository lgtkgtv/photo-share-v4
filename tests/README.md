# Photo Share Social Media Platform - Test Suite

This directory contains the comprehensive test suite for the photo sharing social media platform, covering all implemented features from Phase 1 through Phase 3.

## 📁 Directory Structure

```
tests/
├── README.md                          # This file - test execution guide
├── conftest.py                        # Global test configuration and fixtures
├── pytest.ini                        # Pytest configuration
├── unit/                              # Unit tests
│   ├── test_basic.py                  # Basic functionality tests
│   ├── test_database.py               # Database operations
│   ├── test_security.py               # Security components
│   └── test_performance.py            # Performance optimization
├── integration/                       # Integration tests
│   ├── test_api_auth.py               # Authentication workflows
│   ├── test_api_photos.py             # Photo management
│   ├── test_api_social.py             # Social features
│   ├── test_api_albums.py             # Album management
│   ├── test_api_profiles.py           # User profiles
│   ├── test_api_notifications.py      # Notification system
│   ├── test_api_sharing.py            # Photo sharing
│   └── test_production_readiness.py   # Production features
├── security/                          # Security tests
│   ├── test_owasp_compliance.py       # OWASP Top 10
│   ├── test_gdpr_compliance.py        # GDPR compliance
│   ├── test_fuzz_testing.py           # Fuzzing tests
│   └── test_penetration_testing.py    # Penetration tests
├── api/                              # API endpoint tests
│   ├── test_auth_flow.py              # Authentication API
│   ├── test_photo_upload.py           # Photo upload API
│   ├── test_social_features.py        # Social API
│   ├── test_album_management.py       # Album API
│   ├── test_notification_system.py    # Notification API
│   └── test_sharing_system.py         # Sharing API
└── scripts/                          # Test automation
    └── run_all_tests.py               # Master test runner
```

## 🚀 Quick Start

### Prerequisites

1. **Python Environment**: Python 3.8+ with virtual environment
2. **Dependencies**: Install test dependencies
   ```bash
   pip install -r tests/requirements.txt
   ```
3. **Service**: Ensure the photo sharing service is running
   ```bash
   docker compose up --build
   ```

### Running Tests

#### Quick Test Suite (Recommended for development)
```bash
# Run core tests (unit + integration)
python tests/scripts/run_all_tests.py --quick

# Or manually
pytest tests/unit/ tests/integration/ -v
```

#### Full Test Suite
```bash
# Run all tests with coverage
python tests/scripts/run_all_tests.py

# Or manually
pytest tests/ --cov=services/photoshare --cov-report=html
```

#### Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only  
pytest tests/integration/ -v

# API tests only
pytest tests/api/ -v

# Security tests only
pytest tests/security/ -v

# Performance tests only
pytest tests/ -m performance

# Feature-specific tests
pytest tests/ -m social        # Social media features
pytest tests/ -m albums        # Album management
pytest tests/ -m profiles      # User profiles
pytest tests/ -m notifications # Notifications
pytest tests/ -m sharing       # Photo sharing
```

## 🎯 Test Categories

### Unit Tests (`tests/unit/`)
Test individual components in isolation:
- Database models and operations
- Security utilities (JWT, hashing, validation)
- Performance optimization components
- Basic service functionality

### Integration Tests (`tests/integration/`)
Test API endpoints and workflows:
- Authentication and user management
- Photo upload and management
- Social features (likes, comments, follows)
- Album creation and organization
- User profile management
- Notification system
- Photo sharing functionality

### API Tests (`tests/api/`)
Comprehensive API endpoint testing:
- Complete authentication flows
- Photo upload and download
- Social interaction workflows
- Album management operations
- Notification delivery and management
- Secure sharing with tokens and passwords

### Security Tests (`tests/security/`)
Security-focused validation:
- OWASP Top 10 compliance
- GDPR privacy requirements
- Input validation and sanitization
- File upload security
- Authentication and authorization

## 📊 Test Markers

Tests are categorized using pytest markers:

```python
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.security      # Security tests
@pytest.mark.performance   # Performance tests
@pytest.mark.auth          # Authentication required
@pytest.mark.social        # Social media features
@pytest.mark.albums        # Album management
@pytest.mark.profiles      # User profiles
@pytest.mark.notifications # Notification system
@pytest.mark.sharing       # Photo sharing
@pytest.mark.slow          # Long-running tests
```

## 🔧 Configuration

### Test Environment
Tests use isolated test configuration:
- **Database**: In-memory SQLite for fast execution
- **Authentication**: Test JWT secrets
- **File Storage**: Mocked file operations
- **External Services**: Mocked dependencies

### Coverage Targets
- **Overall Coverage**: >90%
- **Critical Components**: 100% (auth, security)
- **Feature Components**: >85% (social, albums, profiles)
- **Performance Components**: >75%

### Test Data
- **Fixtures**: Defined in `conftest.py`
- **Sample Data**: Test users, photos, albums
- **Mock Services**: File storage, external APIs

## 📈 Performance Benchmarks

Tests validate performance requirements:
- **API Response Time**: <200ms (95th percentile)
- **Database Queries**: <50ms (average)
- **Photo Upload**: <5s per image
- **Authentication**: <2s login flow
- **Search Operations**: <100ms

## 🐛 Debugging Tests

### Verbose Output
```bash
pytest tests/ -v -s --tb=long
```

### Specific Test Debugging
```bash
# Run single test with debugging
pytest tests/unit/test_basic.py::TestBasicSetup::test_environment_setup -v -s

# Run with pdb debugging
pytest tests/ --pdb
```

### Coverage Analysis
```bash
# Generate HTML coverage report
pytest tests/ --cov=services/photoshare --cov-report=html

# View report
open tests/coverage_html/index.html
```

## 🔄 Continuous Integration

### Pre-commit Tests (Fast - ~2 minutes)
```bash
pytest tests/unit/ -v --tb=short
pytest tests/integration/test_api_auth.py -v
```

### Pull Request Tests (Comprehensive - ~15 minutes)
```bash
python tests/scripts/run_all_tests.py --types unit integration api security
```

### Nightly Tests (Full Suite - ~45 minutes)
```bash
python tests/scripts/run_all_tests.py --types all
pytest tests/ --cov=services/photoshare --cov-fail-under=90
```

## 📝 Test Development Guidelines

### Writing New Tests

1. **Follow Naming Convention**: `test_<feature>_<scenario>.py`
2. **Use Appropriate Markers**: Mark tests with relevant pytest markers
3. **Leverage Fixtures**: Use existing fixtures from `conftest.py`
4. **Test Both Success and Failure**: Include positive and negative test cases
5. **Performance Awareness**: Add performance assertions for critical paths

### Test Structure
```python
@pytest.mark.integration
@pytest.mark.social
class TestSocialFeatures:
    """Test social media functionality."""
    
    async def test_like_photo_workflow(self, async_test_client, auth_headers, test_photo):
        """Test complete like/unlike workflow."""
        # Test implementation
        pass
```

### Assertion Guidelines
- Use descriptive assertion messages
- Test specific error conditions
- Verify response structure and content
- Include performance assertions where relevant

## 🚨 Troubleshooting

### Common Issues

**Test Database Connection**
```bash
# Ensure test environment variables are set
export ENVIRONMENT=test
export JWT_SECRET_KEY=test-secret-key
```

**Import Errors**
```bash
# Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Service Not Running**
```bash
# Start the photo sharing service
docker compose up --build
```

### Environment Reset
```bash
# Clean test artifacts
rm -rf tests/coverage_html/
rm -f tests/coverage.xml
rm -f tests/.coverage

# Reset test database
docker compose down -v
docker compose up --build
```

## 📚 Related Documentation

- **[Comprehensive Test Plan](../COMPREHENSIVE_TEST_PLAN.md)**: Detailed testing strategy
- **[CLAUDE.md](../CLAUDE.md)**: Development guidance and project overview
- **[API Documentation](http://localhost:8000/docs)**: Interactive API documentation
- **[Service Configuration](../services/photoshare/)**: Service implementation details

## 🎉 Success Metrics

The test suite validates:
- ✅ **100% Core Functionality**: Authentication, photo management, security
- ✅ **90%+ Feature Coverage**: Social features, albums, profiles, notifications, sharing
- ✅ **Security Compliance**: OWASP Top 10, GDPR requirements
- ✅ **Performance Standards**: Response times, throughput, scalability
- ✅ **Production Readiness**: Error handling, monitoring, logging

---

*This test suite ensures the photo sharing social media platform meets enterprise-grade quality, security, and performance standards.*