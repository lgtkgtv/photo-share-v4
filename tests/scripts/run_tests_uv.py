#!/usr/bin/env python3
"""
UV-Based Comprehensive Test Runner for Photo Share Service.

This script manages test execution using UV-managed Python environment
with proper artifact organization in the tests/ directory.
"""

import os
import sys
import json
import time
import subprocess
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# Test execution paths
TESTS_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = TESTS_ROOT.parent
UV_ENV_PATH = TESTS_ROOT / "env"
REPORTS_DIR = TESTS_ROOT / "reports"
COVERAGE_DIR = TESTS_ROOT / "coverage"
SECURITY_REPORTS_DIR = TESTS_ROOT / "security_reports"
SSL_CERTS_DIR = TESTS_ROOT / "ssl_certs"

# Ensure directories exist
for dir_path in [REPORTS_DIR, COVERAGE_DIR, SECURITY_REPORTS_DIR, SSL_CERTS_DIR]:
    dir_path.mkdir(exist_ok=True)


class TestStage(Enum):
    """Test execution stages."""
    DEVELOPMENT = "development"
    CI = "ci"
    STAGING = "staging" 
    PRODUCTION = "production"


class TestCategory(Enum):
    """Test categories."""
    UNIT = "unit"
    INTEGRATION = "integration"
    API = "api"
    SECURITY = "security"
    PERFORMANCE = "performance"
    E2E = "e2e"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class TestResult:
    """Individual test result."""
    category: str
    name: str
    status: str
    duration: float
    start_time: str
    end_time: str
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str
    coverage: Optional[float] = None
    security_score: Optional[float] = None
    performance_metrics: Optional[Dict] = None
    compliance_status: Optional[Dict] = None


@dataclass
class TestSession:
    """Complete test session."""
    session_id: str
    stage: str
    start_time: str
    end_time: str
    total_duration: float
    categories_run: List[str]
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    overall_coverage: Optional[float]
    security_compliance_score: Optional[float]
    results: List[TestResult]


class UVTestRunner:
    """UV-based test runner with comprehensive reporting."""

    def __init__(self, stage: TestStage = TestStage.DEVELOPMENT):
        self.stage = stage
        self.session_id = f"{stage.value}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.start_time = datetime.now(timezone.utc)
        self.results: List[TestResult] = []
        
        # Setup logging
        self._setup_logging()
        
        # Environment setup
        self.uv_python = str(UV_ENV_PATH / "bin" / "python")
        self.uv_pytest = str(UV_ENV_PATH / "bin" / "pytest")
        
        self.logger.info(f"Starting test session {self.session_id} for stage {stage.value}")
        self.logger.info(f"UV Python: {self.uv_python}")

    def _setup_logging(self):
        """Setup logging configuration."""
        log_file = REPORTS_DIR / f"test_execution_{self.session_id}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _run_command(self, command: List[str], timeout: int = 300, cwd: Optional[Path] = None) -> TestResult:
        """Execute a command and capture results."""
        start_time = datetime.now(timezone.utc)
        
        # Set environment variables for testing
        env = os.environ.copy()
        env.update({
            'PYTHONPATH': str(PROJECT_ROOT),
            'ENVIRONMENT': 'test',
            'ENV_FILE': str(TESTS_ROOT / '.env.test')
        })
        
        try:
            self.logger.info(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or PROJECT_ROOT,
                env=env
            )
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            return TestResult(
                category="",
                name="",
                status="passed" if result.returncode == 0 else "failed",
                duration=duration,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
            
        except subprocess.TimeoutExpired as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            return TestResult(
                category="",
                name="",
                status="timeout",
                duration=duration,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout}s"
            )
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            return TestResult(
                category="",
                name="",
                status="error",
                duration=duration,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                command=command,
                exit_code=-2,
                stdout="",
                stderr=str(e)
            )

    def run_unit_tests(self) -> TestResult:
        """Run unit tests."""
        self.logger.info("Starting unit tests")
        
        command = [
            self.uv_python, "-m", "pytest",
            "tests/unit/",
            "-v",
            f"--cov=services/photoshare",
            f"--cov-report=html:{COVERAGE_DIR}/unit_html",
            f"--cov-report=xml:{COVERAGE_DIR}/unit_coverage.xml",
            f"--cov-report=term"
        ]
        
        result = self._run_command(command)
        result.category = "unit"
        result.name = "unit_tests"
        
        if result.status == "passed":
            self.logger.info(f"Unit tests completed successfully in {result.duration:.2f}s")
        else:
            self.logger.error(f"Unit tests failed in {result.duration:.2f}s")
        
        return result

    def run_integration_tests(self) -> TestResult:
        """Run integration tests."""
        self.logger.info("Starting integration tests")
        
        command = [
            self.uv_python, "-m", "pytest",
            "tests/integration/",
            "-v",
            f"--cov=services/photoshare",
            f"--cov-append",
            f"--cov-report=html:{COVERAGE_DIR}/integration_html",
            f"--cov-report=xml:{COVERAGE_DIR}/integration_coverage.xml",
        ]
        
        result = self._run_command(command)
        result.category = "integration"
        result.name = "integration_tests"
        
        if result.status == "passed":
            self.logger.info(f"Integration tests completed successfully in {result.duration:.2f}s")
        else:
            self.logger.error(f"Integration tests failed in {result.duration:.2f}s")
        
        return result

    def run_api_tests(self) -> TestResult:
        """Run API tests."""
        self.logger.info("Starting API tests")
        
        command = [
            self.uv_python, "-m", "pytest",
            "tests/api/",
            "-v",
        ]
        
        result = self._run_command(command)
        result.category = "api"
        result.name = "api_tests"
        
        if result.status == "passed":
            self.logger.info(f"API tests completed successfully in {result.duration:.2f}s")
        else:
            self.logger.error(f"API tests failed in {result.duration:.2f}s")
        
        return result

    def run_security_tests(self) -> TestResult:
        """Run security tests."""
        self.logger.info("Starting security tests")
        
        command = [
            self.uv_python, "-m", "pytest",
            "tests/security/",
            "-v",
        ]
        
        result = self._run_command(command)
        result.category = "security"
        result.name = "security_tests"
        
        if result.status == "passed":
            self.logger.info(f"Security tests completed successfully in {result.duration:.2f}s")
        else:
            self.logger.error(f"Security tests failed in {result.duration:.2f}s")
        
        return result

    def run_e2e_tests(self) -> TestResult:
        """Run end-to-end tests."""
        self.logger.info("Starting E2E tests")
        
        command = [
            self.uv_python, "-m", "pytest",
            "tests/e2e/",
            "-v",
        ]
        
        result = self._run_command(command)
        result.category = "e2e"
        result.name = "e2e_tests"
        
        if result.status == "passed":
            self.logger.info(f"E2E tests completed successfully in {result.duration:.2f}s")
        else:
            self.logger.error(f"E2E tests failed in {result.duration:.2f}s")
        
        return result

    def run_performance_tests(self) -> TestResult:
        """Run performance tests."""
        self.logger.info("Starting performance tests")
        
        command = [
            self.uv_python, "-m", "pytest",
            "tests/performance/",
            "-v",
        ]
        
        result = self._run_command(command)
        result.category = "performance" 
        result.name = "performance_tests"
        
        if result.status == "passed":
            self.logger.info(f"Performance tests completed successfully in {result.duration:.2f}s")
        else:
            self.logger.error(f"Performance tests failed in {result.duration:.2f}s")
        
        return result

    def run_infrastructure_tests(self) -> TestResult:
        """Run infrastructure tests."""
        self.logger.info("Starting infrastructure tests")
        
        command = [
            self.uv_python, "-m", "pytest",
            "tests/infrastructure/",
            "-v",
        ]
        
        result = self._run_command(command)
        result.category = "infrastructure"
        result.name = "infrastructure_tests"
        
        if result.status == "passed":
            self.logger.info(f"Infrastructure tests completed successfully in {result.duration:.2f}s")
        else:
            self.logger.error(f"Infrastructure tests failed in {result.duration:.2f}s")
        
        return result

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - self.start_time).total_seconds()
        
        # Calculate summary statistics
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == "passed"])
        failed_tests = len([r for r in self.results if r.status == "failed"])
        skipped_tests = len([r for r in self.results if r.status == "skipped"])
        
        session = TestSession(
            session_id=self.session_id,
            stage=self.stage.value,
            start_time=self.start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_duration=total_duration,
            categories_run=[r.category for r in self.results],
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            overall_coverage=None,
            security_compliance_score=None,
            results=self.results
        )
        
        # Generate JSON report
        json_report = {
            "session": asdict(session),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "total_duration": total_duration,
                "coverage": None,
                "security_score": None
            },
            "results": [asdict(result) for result in self.results],
            "categories": {
                category: {
                    "tests": len([r for r in self.results if r.category == category]),
                    "passed": len([r for r in self.results if r.category == category and r.status == "passed"]),
                    "failed": len([r for r in self.results if r.category == category and r.status == "failed"])
                }
                for category in set(r.category for r in self.results)
            }
        }
        
        # Save JSON report
        json_file = REPORTS_DIR / f"comprehensive_test_report_{self.session_id}.json"
        with open(json_file, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        self.logger.info(f"Comprehensive report saved to {json_file}")
        return json_report

    def run_all_tests(self, categories: List[str] = None) -> Dict[str, Any]:
        """Run all or specified test categories."""
        if categories is None:
            categories = ["unit", "integration", "api", "security", "e2e", "performance", "infrastructure"]
        
        # Test execution mapping
        test_runners = {
            "unit": self.run_unit_tests,
            "integration": self.run_integration_tests,
            "api": self.run_api_tests,
            "security": self.run_security_tests,
            "e2e": self.run_e2e_tests,
            "performance": self.run_performance_tests,
            "infrastructure": self.run_infrastructure_tests
        }
        
        self.logger.info(f"Running test categories: {categories}")
        
        for category in categories:
            if category in test_runners:
                result = test_runners[category]()
                self.results.append(result)
                
                if result.status != "passed":
                    self.logger.error(f"{category} tests failed: {result.stderr}")
            else:
                self.logger.warning(f"Unknown test category: {category}")
        
        return self.generate_comprehensive_report()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="UV-Based Comprehensive Test Runner")
    parser.add_argument("--stage", choices=["development", "ci", "staging", "production"], 
                       default="development", help="Test execution stage")
    parser.add_argument("--categories", nargs="+", 
                       choices=["unit", "integration", "api", "security", "e2e", "performance", "infrastructure"],
                       default=None, help="Test categories to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Verify UV environment exists
    if not UV_ENV_PATH.exists():
        print(f"❌ UV environment not found at {UV_ENV_PATH}")
        print("Run: cd tests && uv venv env --python 3.11")
        sys.exit(1)
    
    stage = TestStage(args.stage)
    runner = UVTestRunner(stage=stage)
    
    try:
        report = runner.run_all_tests(categories=args.categories)
        
        # Print summary
        summary = report["summary"]
        print("\n" + "=" * 60)
        print("TEST EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Session ID: {runner.session_id}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print(f"Tests Run: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"\nReports Generated:")
        print(f"  JSON: tests/reports/comprehensive_test_report_{runner.session_id}.json")
        
        # Exit with appropriate code
        sys.exit(0 if summary['failed'] == 0 else 1)
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()