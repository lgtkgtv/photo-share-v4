#!/usr/bin/env python3
"""
Test runner script for the photo sharing service.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description=""):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description or command}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=False)
    if result.returncode != 0:
        print(f"❌ Command failed: {command}")
        return False
    return True


def install_test_dependencies():
    """Install test dependencies."""
    print("📦 Installing test dependencies...")
    return run_command(
        "pip install -r requirements_test.txt",
        "Installing test dependencies"
    )


def run_unit_tests(coverage=True, verbose=False):
    """Run unit tests."""
    print("🧪 Running unit tests...")
    
    cmd = "python -m pytest tests/unit/"
    if coverage:
        cmd += " --cov=. --cov-report=term-missing"
    if verbose:
        cmd += " -v"
    cmd += " -m unit"
    
    return run_command(cmd, "Unit tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    print("🔗 Running integration tests...")
    
    cmd = "python -m pytest tests/integration/"
    if verbose:
        cmd += " -v"
    cmd += " -m integration"
    
    return run_command(cmd, "Integration tests")


def run_security_tests(verbose=False):
    """Run security tests."""
    print("🛡️ Running security tests...")
    
    cmd = "python -m pytest tests/"
    if verbose:
        cmd += " -v"
    cmd += " -m security"
    
    return run_command(cmd, "Security tests")


def run_performance_tests(verbose=False):
    """Run performance tests."""
    print("⚡ Running performance tests...")
    
    cmd = "python -m pytest tests/"
    if verbose:
        cmd += " -v"
    cmd += " -m performance --benchmark-only"
    
    return run_command(cmd, "Performance tests")


def run_all_tests(coverage=True, verbose=False):
    """Run all tests."""
    print("🎯 Running all tests...")
    
    cmd = "python -m pytest tests/"
    if coverage:
        cmd += " --cov=. --cov-report=term-missing --cov-report=html"
    if verbose:
        cmd += " -v"
    
    return run_command(cmd, "All tests")


def run_test_type(test_type, coverage=True, verbose=False):
    """Run specific type of tests."""
    if test_type == "unit":
        return run_unit_tests(coverage, verbose)
    elif test_type == "integration":
        return run_integration_tests(verbose)
    elif test_type == "security":
        return run_security_tests(verbose)
    elif test_type == "performance":
        return run_performance_tests(verbose)
    elif test_type == "all":
        return run_all_tests(coverage, verbose)
    else:
        print(f"❌ Unknown test type: {test_type}")
        return False


def generate_test_report():
    """Generate test coverage report."""
    print("📊 Generating test coverage report...")
    
    if not Path("htmlcov").exists():
        print("⚠️ No coverage data found. Run tests with coverage first.")
        return False
    
    print("📁 Coverage report generated in htmlcov/ directory")
    print("🌐 Open htmlcov/index.html in your browser to view the report")
    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test runner for photo sharing service")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "security", "performance", "all"],
        nargs="?",
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies before running tests"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only generate coverage report (don't run tests)"
    )
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
    
    print("🚀 Photo Sharing Service Test Runner")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python version: {sys.version}")
    
    success = True
    
    try:
        if args.report_only:
            success = generate_test_report()
        else:
            # Install dependencies if requested
            if args.install_deps:
                success = install_test_dependencies()
                if not success:
                    return 1
            
            # Run tests
            coverage = not args.no_coverage
            success = run_test_type(args.test_type, coverage, args.verbose)
            
            # Generate report if coverage was enabled
            if success and coverage and args.test_type in ["unit", "all"]:
                generate_test_report()
    
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        return 1
    
    if success:
        print("\n✅ Tests completed successfully!")
        return 0
    else:
        print("\n❌ Tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())