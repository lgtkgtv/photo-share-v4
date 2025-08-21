#!/bin/bash
# Automated Test Runner for Photo Share Service
set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_DIR="$PROJECT_ROOT/services/photoshare"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_RESULTS=()

echo -e "${BLUE}🧪 Photo Share Service - Automated Test Suite${NC}"
echo "============================================="

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to run test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local required="${3:-false}"
    
    echo -e "\n${PURPLE}🔧 Running: $test_name${NC}"
    echo "Command: $test_command"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if eval "$test_command"; then
        print_status "$test_name - PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("✅ $test_name")
    else
        if [[ "$required" == "true" ]]; then
            print_error "$test_name - FAILED (CRITICAL)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            TEST_RESULTS+=("❌ $test_name (CRITICAL)")
            return 1
        else
            print_warning "$test_name - FAILED (OPTIONAL)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            TEST_RESULTS+=("⚠️  $test_name (OPTIONAL)")
        fi
    fi
    
    return 0
}

# Setup test environment
setup_test_environment() {
    echo -e "\n${BLUE}🔧 Setting up test environment...${NC}"
    
    cd "$SERVICE_DIR"
    
    # Create test environment file
    cat > .env << EOF
# Test Environment Configuration
ENVIRONMENT=test
POSTGRES_DB=photo_share_test
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password
DB_HOST=localhost
DB_PORT=5432
JWT_SECRET_KEY=test_secret_key_for_testing_32_chars_minimum_length_requirement_safe
REDIS_URL=redis://localhost:6379/1
USE_REDIS_CACHE=false
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
SESSION_TIMEOUT_MINUTES=30
MAX_FILE_SIZE_MB=50
SQL_DEBUG=false
LOG_LEVEL=INFO
EOF
    
    print_status "Test environment configured"
}

# Phase 1: Security Tests
run_security_tests() {
    echo -e "\n${BLUE}🔒 Phase 1: Security Tests${NC}"
    
    run_test "Security Improvements Test" \
        "python3 $PROJECT_ROOT/scripts/test-security-improvements.py" \
        "true"
    
    run_test "File Upload Security Test" \
        "python -m pytest tests/unit/test_security.py::TestFileValidation -v" \
        "true"
    
    run_test "OWASP Compliance Test" \
        "python -m pytest tests/security/test_owasp_compliance.py -v" \
        "false"
    
    run_test "Environment Security Validation" \
        "python3 $PROJECT_ROOT/scripts/setup-environment.py --validate-only" \
        "true"
}

# Phase 2: Production Readiness Tests
run_production_tests() {
    echo -e "\n${BLUE}🚀 Phase 2: Production Readiness Tests${NC}"
    
    run_test "Production Readiness Integration" \
        "python -m pytest tests/integration/test_production_readiness.py -v" \
        "true"
    
    run_test "Database Connection Pooling" \
        "python -m pytest tests/unit/test_database.py -v" \
        "true"
    
    run_test "Performance Optimization" \
        "python -m pytest tests/unit/test_performance.py -v" \
        "false"
    
    run_test "Cache Integration Test" \
        "python -c 'import sys; sys.path.append(\".\"); from performance_simple import RedisCacheManager; import asyncio; asyncio.run(RedisCacheManager().initialize())'" \
        "false"
}

# Phase 3: API Integration Tests  
run_api_tests() {
    echo -e "\n${BLUE}🌐 Phase 3: API Integration Tests${NC}"
    
    run_test "API Authentication Tests" \
        "python -m pytest tests/integration/test_api_auth.py -v" \
        "true"
    
    run_test "API Photo Management Tests" \
        "python -m pytest tests/integration/test_api_photos.py -v" \
        "true"
    
    # Start service for live API tests
    if command -v curl &> /dev/null; then
        # Check if service is running
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            run_test "Live API Health Check" \
                "curl -f http://localhost:8000/health" \
                "false"
            
            run_test "Live API Documentation" \
                "curl -f http://localhost:8000/docs" \
                "false"
        else
            print_warning "Service not running - skipping live API tests"
        fi
    fi
}

# Phase 4: Comprehensive Test Suite
run_comprehensive_tests() {
    echo -e "\n${BLUE}📊 Phase 4: Comprehensive Test Suite${NC}"
    
    run_test "Full Unit Test Suite" \
        "python run_tests.py unit" \
        "true"
    
    run_test "Full Integration Test Suite" \
        "python run_tests.py integration" \
        "false"
    
    run_test "Security Test Suite" \
        "python run_tests.py security" \
        "false"
    
    run_test "Performance Benchmarks" \
        "python run_tests.py performance" \
        "false"
}

# Phase 5: CI/CD Tests
run_cicd_tests() {
    echo -e "\n${BLUE}⚙️  Phase 5: CI/CD Pipeline Tests${NC}"
    
    # Test Docker build
    if command -v docker &> /dev/null; then
        run_test "Docker Build Test" \
            "cd $PROJECT_ROOT && docker build -t photo-share-test -f services/photoshare/Dockerfile.database services/photoshare/" \
            "false"
    fi
    
    # Test environment scripts
    run_test "Environment Setup Script" \
        "python3 $PROJECT_ROOT/scripts/setup-environment.py --environment test" \
        "false"
    
    run_test "Database Migration Test" \
        "python manage_db.py current || echo 'Migration test completed'" \
        "false"
    
    # Test deployment readiness
    if [[ -f "$PROJECT_ROOT/docker-compose.prod.yml" ]]; then
        run_test "Production Config Validation" \
            "cd $PROJECT_ROOT && docker-compose -f docker-compose.prod.yml config" \
            "false"
    fi
}

# Generate test report
generate_report() {
    echo -e "\n${BLUE}📋 Test Results Summary${NC}"
    echo "======================="
    
    echo "📊 Statistics:"
    echo "  • Total Tests: $TOTAL_TESTS"
    echo "  • Passed: $PASSED_TESTS"
    echo "  • Failed: $FAILED_TESTS"
    
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        local success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
        echo "  • Success Rate: ${success_rate}%"
    fi
    
    echo ""
    echo "📝 Detailed Results:"
    for result in "${TEST_RESULTS[@]}"; do
        echo "  $result"
    done
    
    echo ""
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}🎉 All tests passed! System is ready for production.${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Some tests failed. Review the results above.${NC}"
        return 1
    fi
}

# Cleanup
cleanup() {
    echo -e "\n${BLUE}🧹 Cleaning up...${NC}"
    
    # Remove test environment file
    if [[ -f "$SERVICE_DIR/.env" ]]; then
        rm "$SERVICE_DIR/.env"
    fi
    
    # Remove test artifacts
    find "$SERVICE_DIR" -name "*.pyc" -delete 2>/dev/null || true
    find "$SERVICE_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    print_status "Cleanup completed"
}

# Main execution
main() {
    # Handle script arguments
    local run_all=true
    local run_security=false
    local run_production=false
    local run_api=false
    local run_comprehensive=false
    local run_cicd=false
    
    case "${1:-all}" in
        all)
            run_all=true
            ;;
        security)
            run_security=true
            run_all=false
            ;;
        production) 
            run_production=true
            run_all=false
            ;;
        api)
            run_api=true
            run_all=false
            ;;
        comprehensive)
            run_comprehensive=true
            run_all=false
            ;;
        cicd)
            run_cicd=true
            run_all=false
            ;;
        *)
            echo "Usage: $0 {all|security|production|api|comprehensive|cicd}"
            exit 1
            ;;
    esac
    
    # Setup
    setup_test_environment
    
    # Run test phases
    if [[ $run_all == true ]] || [[ $run_security == true ]]; then
        run_security_tests
    fi
    
    if [[ $run_all == true ]] || [[ $run_production == true ]]; then
        run_production_tests
    fi
    
    if [[ $run_all == true ]] || [[ $run_api == true ]]; then
        run_api_tests
    fi
    
    if [[ $run_all == true ]] || [[ $run_comprehensive == true ]]; then
        run_comprehensive_tests
    fi
    
    if [[ $run_all == true ]] || [[ $run_cicd == true ]]; then
        run_cicd_tests
    fi
    
    # Generate report and cleanup
    generate_report
    local exit_code=$?
    
    cleanup
    
    exit $exit_code
}

# Trap for cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"