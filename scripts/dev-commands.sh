#!/bin/bash
# PhotoShare Development Commands
# ==============================
# Common development tasks using uv

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(echo $1 | sed 's/./-/g')"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if uv virtual environment is active
if [[ "$VIRTUAL_ENV" != *".venv"* ]]; then
    print_warning "Virtual environment not active. Run: source .venv/bin/activate"
fi

case "$1" in
    "test")
        print_header "Running Tests with uv"
        uv run pytest tests/ -v
        ;;
    "test-coverage")
        print_header "Running Tests with Coverage"
        uv run pytest --cov=services --cov-report=html --cov-report=term
        print_success "Coverage report generated in htmlcov/"
        ;;
    "format")
        print_header "Formatting Code with Black"
        uv run black services/ tests/ tools/ --line-length 88
        uv run isort services/ tests/ tools/ --profile black
        print_success "Code formatted"
        ;;
    "lint")
        print_header "Running Type Checking and Linting"
        uv run mypy services/
        print_success "Type checking complete"
        ;;
    "security")
        print_header "Security Analysis"
        uv run bandit -r services/ -f json -o security-report.json
        uv run safety check --json --output safety-report.json
        print_success "Security analysis complete"
        ;;
    "install")
        print_header "Installing Dependencies"
        uv sync --extra all
        print_success "All dependencies installed"
        ;;
    "add")
        if [ -z "$2" ]; then
            print_error "Usage: $0 add <package-name>"
            exit 1
        fi
        print_header "Adding Package: $2"
        uv add "$2"
        print_success "Package $2 added"
        ;;
    "add-dev")
        if [ -z "$2" ]; then
            print_error "Usage: $0 add-dev <package-name>"
            exit 1
        fi
        print_header "Adding Development Package: $2"
        uv add --group dev "$2"
        print_success "Development package $2 added"
        ;;
    "update")
        print_header "Updating Dependencies"
        uv sync --upgrade
        print_success "Dependencies updated"
        ;;
    "clean")
        print_header "Cleaning Environment"
        rm -rf .venv/
        uv venv
        uv sync --extra all
        print_success "Environment cleaned and recreated"
        ;;
    "services")
        print_header "Starting Services"
        docker compose -f docker-compose.separated.yml up -d
        print_success "Services started"
        ;;
    "services-stop")
        print_header "Stopping Services"
        docker compose -f docker-compose.separated.yml down
        print_success "Services stopped"
        ;;
    "api-test")
        print_header "Running API Integration Tests"
        bash api-integration-tests/test-auth-flow.sh
        bash api-integration-tests/test-photo-upload.sh
        print_success "API tests complete"
        ;;
    *)
        print_header "PhotoShare Development Commands"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Available commands:"
        echo "  test            Run pytest tests"
        echo "  test-coverage   Run tests with coverage report"
        echo "  format          Format code with Black and isort"
        echo "  lint            Run type checking with mypy"
        echo "  security        Run security analysis (bandit, safety)"
        echo "  install         Install all dependencies"
        echo "  add <package>   Add new dependency"
        echo "  add-dev <pkg>   Add development dependency"
        echo "  update          Update all dependencies"
        echo "  clean           Clean and recreate environment"
        echo "  services        Start Docker services"
        echo "  services-stop   Stop Docker services"
        echo "  api-test        Run API integration tests"
        echo ""
        echo "⚠️  Always use uv commands for Python package management!"
        ;;
esac