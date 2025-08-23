# PhotoShare Test Suite Documentation
# ====================================

Comprehensive testing framework for PhotoShare application with proper categorization, coverage tracking, and security compliance testing.

## 📁 Test Structure

```
tests/
├── conftest.py                    # Global test configuration and fixtures
├── pytest.ini                    # Pytest configuration and coverage settings
├── run_tests.py                  # Unified test runner with coverage
├── run_security_tests.py         # Dedicated security test runner
├── README.md                     # This documentation
│
├── unit/                         # Unit tests for individual components
│   ├── auth-service/             # Auth service unit tests
│   ├── photoshare/              # Photo service unit tests  
│   └── shared/                  # Shared utilities unit tests
│
├── integration/                  # Service-to-service integration tests
│   ├── test_service_communication.py
│   ├── test_jwt_validation.py
│   └── test_separated_architecture.py
│
├── functional/                   # End-to-end functional workflow tests
│   └── test_user_workflows.py
│
├── security/                     # Security and compliance testing
│   ├── test_rbac_security.py
│   └── test_security_compliance.py
│
├── reports/                      # Test reports and results
│   ├── security/                 # Security test reports
│   └── [timestamped reports]
│
└── coverage/                     # Code coverage reports
    ├── html/                     # HTML coverage reports
    ├── coverage.json            # JSON coverage data
    └── coverage.xml             # XML coverage for CI/CD
```

## 🧪 Test Categories

### Unit Tests
- **Location**: `tests/unit/`
- **Purpose**: Test individual components in isolation
- **Marker**: `@pytest.mark.unit`
- **Coverage**: Individual functions and classes

### Integration Tests  
- **Location**: `tests/integration/`
- **Purpose**: Test service-to-service communication
- **Marker**: `@pytest.mark.integration`
- **Requires**: Running services (auth-service, photo-service)

### Functional Tests
- **Location**: `tests/functional/`
- **Purpose**: End-to-end user workflow testing
- **Marker**: `@pytest.mark.functional`
- **Coverage**: Complete user journeys

### Security Tests
- **Location**: `tests/security/`
- **Purpose**: Security vulnerability and compliance testing
- **Markers**: `@pytest.mark.security`, `@pytest.mark.security_compliance`
- **Coverage**: OWASP compliance, RBAC, authentication security

## 🚀 Running Tests

### Quick Start

```bash
# Run all tests with coverage
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --categories unit integration

# Run security tests only
python tests/run_security_tests.py

# Run quick security check
python tests/run_security_tests.py --quick
```

### Individual Categories

```bash
# Unit tests only
pytest tests/unit/ -v -m unit

# Integration tests (requires running services)
pytest tests/integration/ -v -m integration  

# Functional tests (requires running services)
pytest tests/functional/ -v -m functional

# Security tests
pytest tests/security/ -v -m security

# Security compliance
pytest tests/security/ -v -m security_compliance
```

### Coverage Tracking

```bash
# Generate coverage report
pytest --cov=services --cov-report=html:tests/coverage/html

# View coverage in browser
open tests/coverage/html/index.html

# Coverage with specific threshold
pytest --cov=services --cov-fail-under=70
```

## 📊 Test Reports

### Automated Reporting

All test runs generate:
- **HTML Reports**: Detailed test results with pass/fail status
- **JSON Reports**: Machine-readable test data for CI/CD
- **Coverage Reports**: Code coverage analysis in HTML/JSON/XML
- **Security Reports**: Security assessment and compliance status

### Report Locations

- **Test Reports**: `tests/reports/`
- **Coverage Reports**: `tests/coverage/`
- **Security Reports**: `tests/reports/security/`

## 🔒 Security Testing

### Security Test Runner

```bash
# Full security assessment
python tests/run_security_tests.py

# Quick security check (critical tests only)  
python tests/run_security_tests.py --quick

# Static analysis only
python tests/run_security_tests.py --static-only
```

### Security Test Coverage

- **RBAC Testing**: Role-based access control validation
- **Authentication Security**: JWT validation, session management
- **OWASP Compliance**: Top 10 security risk mitigation
- **Input Validation**: SQL injection, XSS prevention
- **Authorization**: Permission boundary enforcement
- **Static Analysis**: Code security scanning with Bandit
- **Dependency Scanning**: Vulnerability detection with Safety

## 📈 Coverage Tracking

### Coverage Targets

- **Overall Coverage**: 70% minimum
- **Critical Functions**: 80%+ coverage required
- **Security Functions**: 90%+ coverage required

### Complex Functions Requiring Attention

The following high-complexity functions require comprehensive testing:

1. **AuthenticationService._get_user_roles_and_permissions**
   - Priority: Critical
   - Target Coverage: 80%+
   - Complexity: High

2. **AuthenticatedUser.has_permission**
   - Priority: Critical  
   - Target Coverage: 90%+
   - Complexity: Medium

3. **AuthenticationService._assign_default_role**
   - Priority: High
   - Target Coverage: 85%+
   - Complexity: Medium

4. **upload_photo (main.py)**
   - Priority: Critical
   - Target Coverage: 75%+
   - Complexity: High

## ⚙️ Configuration

### Pytest Configuration

Configuration is managed in `tests/pytest.ini`:
- Test discovery patterns
- Coverage settings and thresholds
- Test markers and categorization
- Report generation options

### Test Fixtures

Global fixtures in `tests/conftest.py`:
- Service availability checking
- Authentication helpers
- Test data generation
- Mock services for unit testing

## 🎯 Test Markers

Use markers to categorize and run specific test types:

```python
@pytest.mark.unit
def test_individual_function():
    pass

@pytest.mark.integration
@pytest.mark.requires_auth
def test_service_communication():
    pass

@pytest.mark.security
@pytest.mark.rbac
def test_permission_enforcement():
    pass

@pytest.mark.functional
@pytest.mark.slow
def test_complete_workflow():
    pass
```

### Available Markers

- `unit` - Unit tests
- `integration` - Integration tests
- `functional` - Functional tests
- `security` - Security tests
- `security_compliance` - Compliance tests
- `slow` - Long-running tests
- `network` - Tests requiring network access
- `database` - Tests requiring database
- `auth` - Authentication-related tests
- `rbac` - Role-based access control tests
- `photos` - Photo functionality tests
- `performance` - Performance tests

## 📋 Prerequisites

### For All Tests
```bash
pip install pytest pytest-cov pytest-html pytest-json-report requests PyJWT Pillow
```

### For Security Tests
```bash
pip install bandit safety semgrep
```

### For Integration/Functional Tests

Services must be running:
```bash
# Start services
docker compose -f docker-compose.separated.yml up -d

# Verify services
curl http://localhost:8001/health
curl http://localhost:8000/health
```

## 🔧 CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run PhotoShare Test Suite
  run: |
    python tests/run_tests.py --categories unit integration functional
    
- name: Run Security Tests
  run: |
    python tests/run_security_tests.py --quick
    
- name: Upload Coverage Reports
  uses: codecov/codecov-action@v3
  with:
    files: tests/coverage/coverage.xml
```

### Coverage Reporting

Generated reports support popular CI/CD platforms:
- **Codecov**: XML coverage reports
- **Coveralls**: JSON coverage data
- **SonarQube**: XML and JSON reports
- **GitHub Actions**: HTML reports as artifacts

## 📝 Writing New Tests

### Test File Naming

- Unit tests: `test_component_name.py`
- Integration tests: `test_service_integration.py`
- Functional tests: `test_workflow_name.py`
- Security tests: `test_security_aspect.py`

### Test Function Naming

```python
def test_function_behavior():          # Unit test
def test_service_communication():      # Integration test
def test_user_registration_workflow(): # Functional test
def test_rbac_permission_enforcement(): # Security test
```

### Test Structure Template

```python
import pytest

class TestComponentName:
    """Test suite for ComponentName functionality."""
    
    @pytest.mark.unit
    def test_basic_functionality(self):
        """Test basic component behavior."""
        # Arrange
        input_data = "test"
        
        # Act
        result = component_function(input_data)
        
        # Assert
        assert result == expected_output
    
    @pytest.mark.integration
    @pytest.mark.requires_auth
    def test_service_integration(self, auth_headers):
        """Test integration with external services."""
        # Test implementation
        pass
```

## 🚨 Troubleshooting

### Common Issues

1. **Services Not Running**
   ```
   Error: Required services not available
   Solution: Start services with docker compose
   ```

2. **Coverage Below Threshold**
   ```
   Error: Coverage 65% is below 70% threshold
   Solution: Add tests for uncovered functions
   ```

3. **Security Test Failures**
   ```
   Error: Critical security test failed
   Solution: Review security implementation
   ```

### Debug Commands

```bash
# Check service health
curl http://localhost:8001/health
curl http://localhost:8000/health

# Run single test with verbose output
pytest tests/path/to/test.py::test_name -v -s

# Run tests without coverage (faster)
pytest tests/ --no-cov

# Clean test cache
pytest --cache-clear
```

## 📖 Further Reading

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Python Security Best Practices](https://bandit.readthedocs.io/)

---

**Note**: This test suite is designed to ensure PhotoShare meets production-quality standards for functionality, security, and reliability. All tests should pass before deployment to production environments.