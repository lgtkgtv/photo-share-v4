#!/usr/bin/env python3
"""
Comprehensive Test Runner with Advanced Reporting and Security Compliance.

This script orchestrates complete test execution across all categories with
detailed logging, multi-format reporting, and security compliance validation.
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

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


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
    COMPLIANCE = "compliance"
    INFRASTRUCTURE = "infrastructure"


class SecurityStandard(Enum):
    """Security compliance standards."""
    OWASP = "owasp"
    GDPR = "gdpr"
    SOC2 = "soc2"
    NIST = "nist"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"


@dataclass
class TestResult:
    """Test execution result."""
    category: str
    name: str
    status: str  # passed, failed, skipped, error
    duration: float
    start_time: datetime
    end_time: datetime
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str
    coverage: Optional[float] = None
    security_score: Optional[float] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    compliance_status: Optional[Dict[str, bool]] = None


@dataclass
class TestSession:
    """Complete test session information."""
    session_id: str
    stage: TestStage
    start_time: datetime
    end_time: Optional[datetime]
    total_duration: Optional[float]
    categories_run: List[str]
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    overall_coverage: Optional[float]
    security_compliance_score: Optional[float]
    results: List[TestResult]


class TestLogger:
    """Enhanced logging for test execution."""
    
    def __init__(self, log_dir: Path, session_id: str):
        self.log_dir = log_dir
        self.session_id = session_id
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup loggers
        self.setup_loggers()
    
    def setup_loggers(self):
        """Setup multiple specialized loggers."""
        
        # Main test logger
        self.test_logger = logging.getLogger(f"test_runner_{self.session_id}")
        self.test_logger.setLevel(logging.DEBUG)
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(
            self.log_dir / f"test_execution_{self.session_id}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(simple_formatter)
        
        self.test_logger.addHandler(file_handler)
        self.test_logger.addHandler(console_handler)
        
        # Security audit logger
        self.security_logger = logging.getLogger(f"security_audit_{self.session_id}")
        self.security_logger.setLevel(logging.INFO)
        
        security_handler = logging.FileHandler(
            self.log_dir / f"security_audit_{self.session_id}.log"
        )
        security_handler.setFormatter(detailed_formatter)
        self.security_logger.addHandler(security_handler)
        
        # Performance logger
        self.performance_logger = logging.getLogger(f"performance_{self.session_id}")
        self.performance_logger.setLevel(logging.INFO)
        
        perf_handler = logging.FileHandler(
            self.log_dir / f"performance_metrics_{self.session_id}.log"
        )
        perf_handler.setFormatter(detailed_formatter)
        self.performance_logger.addHandler(perf_handler)
    
    def log_test_start(self, category: str, test_name: str, command: List[str]):
        """Log test execution start."""
        self.test_logger.info(f"Starting {category} test: {test_name}")
        self.test_logger.debug(f"Command: {' '.join(command)}")
    
    def log_test_result(self, result: TestResult):
        """Log test execution result."""
        level = logging.INFO if result.status == "passed" else logging.ERROR
        self.test_logger.log(
            level,
            f"{result.category} test '{result.name}' {result.status} "
            f"in {result.duration:.2f}s"
        )
        
        if result.stderr:
            self.test_logger.error(f"Errors: {result.stderr[:500]}...")
        
        if result.coverage:
            self.test_logger.info(f"Coverage: {result.coverage:.1f}%")
        
        if result.security_score:
            self.security_logger.info(
                f"Security score for {result.name}: {result.security_score:.1f}%"
            )
        
        if result.performance_metrics:
            self.performance_logger.info(
                f"Performance metrics for {result.name}: {result.performance_metrics}"
            )


class ReportGenerator:
    """Multi-format test report generator."""
    
    def __init__(self, output_dir: Path, session: TestSession):
        self.output_dir = output_dir
        self.session = session
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(self) -> Path:
        """Generate JSON test report."""
        report_data = {
            "session": asdict(self.session),
            "summary": {
                "total_tests": self.session.total_tests,
                "passed": self.session.passed_tests,
                "failed": self.session.failed_tests,
                "skipped": self.session.skipped_tests,
                "success_rate": (self.session.passed_tests / max(self.session.total_tests, 1)) * 100,
                "total_duration": self.session.total_duration,
                "coverage": self.session.overall_coverage,
                "security_score": self.session.security_compliance_score
            },
            "results": [asdict(result) for result in self.session.results],
            "categories": {
                category: {
                    "tests": len([r for r in self.session.results if r.category == category]),
                    "passed": len([r for r in self.session.results if r.category == category and r.status == "passed"]),
                    "failed": len([r for r in self.session.results if r.category == category and r.status == "failed"])
                }
                for category in self.session.categories_run
            }
        }
        
        report_file = self.output_dir / f"test_report_{self.session.session_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        return report_file
    
    def generate_html_report(self) -> Path:
        """Generate HTML test report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {self.session.session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric.success {{ background: #d4edda; }}
        .metric.warning {{ background: #fff3cd; }}
        .metric.danger {{ background: #f8d7da; }}
        .results-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .results-table th, .results-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .results-table th {{ background: #f2f2f2; }}
        .status-passed {{ color: #28a745; font-weight: bold; }}
        .status-failed {{ color: #dc3545; font-weight: bold; }}
        .status-skipped {{ color: #6c757d; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Execution Report</h1>
        <p><strong>Session ID:</strong> {self.session.session_id}</p>
        <p><strong>Stage:</strong> {self.session.stage.value}</p>
        <p><strong>Execution Time:</strong> {self.session.start_time} - {self.session.end_time}</p>
        <p><strong>Duration:</strong> {self.session.total_duration:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <div class="metric {'success' if self.session.failed_tests == 0 else 'danger'}">
            <h3>{self.session.passed_tests}/{self.session.total_tests}</h3>
            <p>Tests Passed</p>
        </div>
        <div class="metric {'success' if self.session.overall_coverage and self.session.overall_coverage >= 90 else 'warning'}">
            <h3>{self.session.overall_coverage or 0:.1f}%</h3>
            <p>Code Coverage</p>
        </div>
        <div class="metric {'success' if self.session.security_compliance_score and self.session.security_compliance_score >= 95 else 'warning'}">
            <h3>{self.session.security_compliance_score or 0:.1f}%</h3>
            <p>Security Score</p>
        </div>
        <div class="metric">
            <h3>{self.session.total_duration:.1f}s</h3>
            <p>Total Duration</p>
        </div>
    </div>
    
    <h2>Test Results by Category</h2>
    <table class="results-table">
        <thead>
            <tr>
                <th>Category</th>
                <th>Test Name</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Coverage</th>
                <th>Security Score</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for result in self.session.results:
            status_class = f"status-{result.status}"
            coverage_display = f"{result.coverage:.1f}%" if result.coverage else "N/A"
            security_display = f"{result.security_score:.1f}%" if result.security_score else "N/A"
            
            html_content += f"""
            <tr>
                <td>{result.category}</td>
                <td>{result.name}</td>
                <td class="{status_class}">{result.status.upper()}</td>
                <td>{result.duration:.2f}s</td>
                <td>{coverage_display}</td>
                <td>{security_display}</td>
            </tr>
"""
        
        html_content += """
        </tbody>
    </table>
    
    <h2>Failed Tests</h2>
"""
        
        failed_results = [r for r in self.session.results if r.status == "failed"]
        if failed_results:
            html_content += '<ul>'
            for result in failed_results:
                html_content += f"""
                <li>
                    <strong>{result.category} - {result.name}</strong><br>
                    <pre style="background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto;">{result.stderr[:500]}...</pre>
                </li>
"""
            html_content += '</ul>'
        else:
            html_content += '<p style="color: #28a745;">No failed tests! 🎉</p>'
        
        html_content += """
</body>
</html>
"""
        
        report_file = self.output_dir / f"test_report_{self.session.session_id}.html"
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        return report_file
    
    def generate_compliance_report(self) -> Path:
        """Generate security compliance report."""
        compliance_data = {
            "report_metadata": {
                "session_id": self.session.session_id,
                "generation_time": datetime.now(timezone.utc).isoformat(),
                "stage": self.session.stage.value,
                "overall_security_score": self.session.security_compliance_score
            },
            "owasp_top_10": {
                f"A{i:02d}": {
                    "tested": any(f"A{i:02d}" in r.name for r in self.session.results),
                    "passed": any(f"A{i:02d}" in r.name and r.status == "passed" for r in self.session.results),
                    "score": next((r.security_score for r in self.session.results if f"A{i:02d}" in r.name), None)
                }
                for i in range(1, 11)
            },
            "gdpr_compliance": {
                requirement: {
                    "tested": any("GDPR" in r.name and requirement.lower() in r.name.lower() for r in self.session.results),
                    "compliant": any("GDPR" in r.name and requirement.lower() in r.name.lower() and r.status == "passed" for r in self.session.results)
                }
                for requirement in ["Right_to_Access", "Data_Minimization", "Data_Protection_by_Design"]
            },
            "security_tests": [
                {
                    "name": result.name,
                    "category": result.category,
                    "status": result.status,
                    "security_score": result.security_score,
                    "compliance_status": result.compliance_status
                }
                for result in self.session.results
                if result.category == "security"
            ],
            "recommendations": []
        }
        
        # Add recommendations based on failed tests
        for result in self.session.results:
            if result.status == "failed" and result.category == "security":
                compliance_data["recommendations"].append({
                    "test": result.name,
                    "issue": "Security test failed",
                    "recommendation": f"Review and fix issues in {result.name}",
                    "severity": "high" if "critical" in result.name.lower() else "medium"
                })
        
        report_file = self.output_dir / f"compliance_report_{self.session.session_id}.json"
        with open(report_file, 'w') as f:
            json.dump(compliance_data, f, indent=2, default=str)
        
        return report_file


class ComprehensiveTestRunner:
    """Advanced test runner with comprehensive reporting."""
    
    def __init__(self, stage: TestStage, output_dir: Path = None):
        self.stage = stage
        self.session_id = f"{stage.value}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        self.output_dir = output_dir or Path("test_reports")
        
        # Setup logging
        self.log_dir = self.output_dir / "logs"
        self.logger = TestLogger(self.log_dir, self.session_id)
        
        # Initialize session
        self.session = TestSession(
            session_id=self.session_id,
            stage=stage,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            total_duration=None,
            categories_run=[],
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            overall_coverage=None,
            security_compliance_score=None,
            results=[]
        )
        
        self.logger.test_logger.info(f"Starting test session {self.session_id} for stage {stage.value}")
    
    def run_test_category(self, category: TestCategory, extra_args: List[str] = None) -> TestResult:
        """Run tests for a specific category."""
        extra_args = extra_args or []
        
        # Define test commands for each category
        commands = {
            TestCategory.UNIT: ["python", "-m", "pytest", "tests/unit/", "-v"],
            TestCategory.INTEGRATION: ["python", "-m", "pytest", "tests/integration/", "-v"],
            TestCategory.API: ["python", "-m", "pytest", "tests/api/", "-v"],
            TestCategory.SECURITY: ["python", "-m", "pytest", "tests/security/", "-v", "-m", "security"],
            TestCategory.PERFORMANCE: ["python", "-m", "pytest", "tests/", "-v", "-m", "performance"],
            TestCategory.E2E: ["python", "-m", "pytest", "tests/e2e/", "-v"],
            TestCategory.COMPLIANCE: ["python", "-m", "pytest", "tests/", "-v", "-m", "compliance"],
            TestCategory.INFRASTRUCTURE: ["python", "-m", "pytest", "tests/infrastructure/", "-v"]
        }
        
        command = commands.get(category, ["echo", f"No command defined for {category.value}"])
        command.extend(extra_args)
        
        # Add coverage if appropriate
        if category in [TestCategory.UNIT, TestCategory.INTEGRATION, TestCategory.API]:
            command.extend(["--cov=services/photoshare", "--cov-append", "--cov-report=term"])
        
        test_name = f"{category.value}_tests"
        
        self.logger.log_test_start(category.value, test_name, command)
        
        start_time = datetime.now(timezone.utc)
        
        try:
            result = subprocess.run(
                command,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Determine status
            if result.returncode == 0:
                status = "passed"
            elif "SKIPPED" in result.stdout and "FAILED" not in result.stdout:
                status = "skipped"
            else:
                status = "failed"
            
            # Extract metrics from output
            coverage = self._extract_coverage(result.stdout)
            security_score = self._extract_security_score(result.stdout)
            performance_metrics = self._extract_performance_metrics(result.stdout)
            compliance_status = self._extract_compliance_status(result.stdout)
            
            test_result = TestResult(
                category=category.value,
                name=test_name,
                status=status,
                duration=duration,
                start_time=start_time,
                end_time=end_time,
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                coverage=coverage,
                security_score=security_score,
                performance_metrics=performance_metrics,
                compliance_status=compliance_status
            )
            
            self.logger.log_test_result(test_result)
            return test_result
            
        except subprocess.TimeoutExpired:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            test_result = TestResult(
                category=category.value,
                name=test_name,
                status="failed",
                duration=duration,
                start_time=start_time,
                end_time=end_time,
                command=command,
                exit_code=-1,
                stdout="",
                stderr="Test execution timed out after 30 minutes",
                coverage=None,
                security_score=None,
                performance_metrics=None,
                compliance_status=None
            )
            
            self.logger.log_test_result(test_result)
            return test_result
    
    def _extract_coverage(self, output: str) -> Optional[float]:
        """Extract coverage percentage from pytest output."""
        import re
        coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
        if coverage_match:
            return float(coverage_match.group(1))
        return None
    
    def _extract_security_score(self, output: str) -> Optional[float]:
        """Extract security compliance score from output."""
        import re
        score_match = re.search(r'Security compliance score[:\s]+(\d+\.?\d*)%', output)
        if score_match:
            return float(score_match.group(1))
        return None
    
    def _extract_performance_metrics(self, output: str) -> Optional[Dict[str, Any]]:
        """Extract performance metrics from output."""
        # This would parse performance test output
        # Implementation depends on specific performance test format
        return None
    
    def _extract_compliance_status(self, output: str) -> Optional[Dict[str, bool]]:
        """Extract compliance status from output."""
        # This would parse compliance test results
        # Implementation depends on specific compliance test format
        return None
    
    def run_comprehensive_suite(self, 
                               categories: List[TestCategory],
                               security_standards: List[SecurityStandard] = None,
                               coverage_threshold: float = 90.0,
                               security_threshold: float = 95.0) -> TestSession:
        """Run comprehensive test suite."""
        
        self.session.categories_run = [cat.value for cat in categories]
        
        for category in categories:
            extra_args = []
            
            # Add security-specific arguments
            if category == TestCategory.SECURITY and security_standards:
                for standard in security_standards:
                    extra_args.extend(["-m", standard.value])
            
            # Add coverage threshold for appropriate categories
            if category in [TestCategory.UNIT, TestCategory.INTEGRATION]:
                extra_args.extend([f"--cov-fail-under={coverage_threshold}"])
            
            result = self.run_test_category(category, extra_args)
            self.session.results.append(result)
            
            # Update session statistics
            self.session.total_tests += 1
            if result.status == "passed":
                self.session.passed_tests += 1
            elif result.status == "failed":
                self.session.failed_tests += 1
            else:
                self.session.skipped_tests += 1
        
        # Finalize session
        self.session.end_time = datetime.now(timezone.utc)
        self.session.total_duration = (self.session.end_time - self.session.start_time).total_seconds()
        
        # Calculate overall metrics
        coverages = [r.coverage for r in self.session.results if r.coverage is not None]
        if coverages:
            self.session.overall_coverage = sum(coverages) / len(coverages)
        
        security_scores = [r.security_score for r in self.session.results if r.security_score is not None]
        if security_scores:
            self.session.security_compliance_score = sum(security_scores) / len(security_scores)
        
        self.logger.test_logger.info(f"Test session completed: {self.session.passed_tests}/{self.session.total_tests} passed")
        
        return self.session
    
    def generate_reports(self, formats: List[str] = None) -> Dict[str, Path]:
        """Generate test reports in specified formats."""
        formats = formats or ["json", "html", "compliance"]
        
        reporter = ReportGenerator(self.output_dir / "reports", self.session)
        reports = {}
        
        if "json" in formats:
            reports["json"] = reporter.generate_json_report()
            self.logger.test_logger.info(f"JSON report generated: {reports['json']}")
        
        if "html" in formats:
            reports["html"] = reporter.generate_html_report()
            self.logger.test_logger.info(f"HTML report generated: {reports['html']}")
        
        if "compliance" in formats:
            reports["compliance"] = reporter.generate_compliance_report()
            self.logger.test_logger.info(f"Compliance report generated: {reports['compliance']}")
        
        return reports


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner with advanced reporting and security compliance"
    )
    
    parser.add_argument(
        "--stage",
        choices=[stage.value for stage in TestStage],
        default=TestStage.DEVELOPMENT.value,
        help="Test execution stage"
    )
    
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=[cat.value for cat in TestCategory],
        default=["unit", "integration", "security"],
        help="Test categories to run"
    )
    
    parser.add_argument(
        "--security-standards",
        nargs="*",
        choices=[std.value for std in SecurityStandard],
        default=["owasp", "gdpr"],
        help="Security standards to validate"
    )
    
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=90.0,
        help="Code coverage threshold percentage"
    )
    
    parser.add_argument(
        "--security-threshold",
        type=float,
        default=95.0,
        help="Security compliance threshold percentage"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test_reports"),
        help="Output directory for reports and logs"
    )
    
    parser.add_argument(
        "--report-formats",
        nargs="+",
        choices=["json", "html", "compliance", "all"],
        default=["json", "html"],
        help="Report formats to generate"
    )
    
    parser.add_argument(
        "--quick-security",
        action="store_true",
        help="Run only quick security tests"
    )
    
    args = parser.parse_args()
    
    # Convert string arguments to enums
    stage = TestStage(args.stage)
    categories = [TestCategory(cat) for cat in args.categories]
    security_standards = [SecurityStandard(std) for std in args.security_standards] if args.security_standards else []
    
    if "all" in args.report_formats:
        report_formats = ["json", "html", "compliance"]
    else:
        report_formats = args.report_formats
    
    # Initialize and run tests
    runner = ComprehensiveTestRunner(stage, args.output_dir)
    
    print(f"🚀 Starting comprehensive test execution")
    print(f"   Stage: {stage.value}")
    print(f"   Categories: {', '.join([cat.value for cat in categories])}")
    print(f"   Security Standards: {', '.join([std.value for std in security_standards])}")
    print(f"   Coverage Threshold: {args.coverage_threshold}%")
    print(f"   Security Threshold: {args.security_threshold}%")
    print(f"   Output Directory: {args.output_dir}")
    print()
    
    # Run tests
    session = runner.run_comprehensive_suite(
        categories=categories,
        security_standards=security_standards,
        coverage_threshold=args.coverage_threshold,
        security_threshold=args.security_threshold
    )
    
    # Generate reports
    print(f"📊 Generating reports...")
    reports = runner.generate_reports(report_formats)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Session ID: {session.session_id}")
    print(f"Total Duration: {session.total_duration:.2f}s")
    print(f"Tests Run: {session.total_tests}")
    print(f"Passed: {session.passed_tests}")
    print(f"Failed: {session.failed_tests}")
    print(f"Skipped: {session.skipped_tests}")
    print(f"Success Rate: {(session.passed_tests/max(session.total_tests,1))*100:.1f}%")
    
    if session.overall_coverage:
        print(f"Code Coverage: {session.overall_coverage:.1f}%")
    
    if session.security_compliance_score:
        print(f"Security Score: {session.security_compliance_score:.1f}%")
    
    print(f"\nReports Generated:")
    for report_type, report_path in reports.items():
        print(f"  {report_type.upper()}: {report_path}")
    
    print(f"\nLogs Available:")
    print(f"  Execution Log: {runner.log_dir}/test_execution_{session.session_id}.log")
    print(f"  Security Audit: {runner.log_dir}/security_audit_{session.session_id}.log")
    print(f"  Performance: {runner.log_dir}/performance_metrics_{session.session_id}.log")
    
    # Exit with appropriate code
    exit_code = 0 if session.failed_tests == 0 else 1
    
    if session.overall_coverage and session.overall_coverage < args.coverage_threshold:
        print(f"\n❌ Coverage {session.overall_coverage:.1f}% below threshold {args.coverage_threshold}%")
        exit_code = 1
    
    if session.security_compliance_score and session.security_compliance_score < args.security_threshold:
        print(f"\n❌ Security score {session.security_compliance_score:.1f}% below threshold {args.security_threshold}%")
        exit_code = 1
    
    if exit_code == 0:
        print(f"\n✅ All tests passed and thresholds met!")
    else:
        print(f"\n❌ Some tests failed or thresholds not met.")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()