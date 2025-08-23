#!/usr/bin/env python3
"""
PhotoShare Test Suite Runner
============================

Unified test runner for all test categories with:
- Code coverage tracking
- Test categorization and reporting
- HTML report generation
- Integration with CI/CD systems
"""

import os
import sys
import subprocess
import argparse
import json
import time
from datetime import datetime
from pathlib import Path


class PhotoShareTestRunner:
    """Main test runner for PhotoShare test suite."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_root = Path(__file__).parent
        self.reports_dir = self.test_root / "reports"
        self.coverage_dir = self.test_root / "coverage"
        
        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)
        self.coverage_dir.mkdir(exist_ok=True)
        
        self.test_categories = {
            "unit": {
                "path": "tests/unit",
                "description": "Unit tests for individual components",
                "markers": "unit"
            },
            "integration": {
                "path": "tests/integration", 
                "description": "Integration tests for service communication",
                "markers": "integration"
            },
            "functional": {
                "path": "tests/functional",
                "description": "End-to-end functional workflow tests",
                "markers": "functional"
            },
            "security": {
                "path": "tests/security",
                "description": "Security and RBAC testing",
                "markers": "security"
            },
            "security_compliance": {
                "path": "tests/security",
                "description": "Security compliance and standards",
                "markers": "security_compliance"
            }
        }
        
    def run_command(self, cmd, capture_output=True):
        """Run a shell command and return result."""
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=capture_output,
                text=True,
                cwd=self.project_root
            )
            return result
        except Exception as e:
            print(f"Error running command '{cmd}': {e}")
            return None
    
    def check_services_running(self):
        """Check if required services are running."""
        print("🔍 Checking service availability...")
        
        services = {
            "Auth Service": "http://localhost:8001/health",
            "App Service": "http://localhost:8000/health"
        }
        
        import requests
        
        all_healthy = True
        for service_name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {service_name}: Healthy")
                else:
                    print(f"❌ {service_name}: Unhealthy ({response.status_code})")
                    all_healthy = False
            except Exception as e:
                print(f"❌ {service_name}: Not accessible ({e})")
                all_healthy = False
        
        return all_healthy
    
    def install_test_dependencies(self):
        """Install required testing dependencies."""
        print("📦 Installing test dependencies...")
        
        test_deps = [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0", 
            "pytest-html>=3.1.0",
            "pytest-json-report>=1.5.0",
            "pytest-asyncio>=0.21.0",
            "coverage>=7.0.0",
            "requests>=2.28.0",
            "PyJWT>=2.6.0",
            "Pillow>=9.0.0"
        ]
        
        for dep in test_deps:
            result = self.run_command(f"pip install {dep}")
            if result and result.returncode != 0:
                print(f"⚠️  Warning: Could not install {dep}")
    
    def run_test_category(self, category, verbose=True, coverage=True):
        """Run tests for a specific category."""
        if category not in self.test_categories:
            print(f"❌ Unknown test category: {category}")
            return False
            
        cat_info = self.test_categories[category]
        print(f"\n🧪 Running {category.upper()} tests: {cat_info['description']}")
        print("=" * 60)
        
        # Build pytest command
        cmd_parts = ["python", "-m", "pytest"]
        
        # Add path
        cmd_parts.append(cat_info["path"])
        
        # Add markers
        if "markers" in cat_info:
            cmd_parts.extend(["-m", cat_info["markers"]])
        
        # Add verbosity
        if verbose:
            cmd_parts.append("-v")
        
        # Add coverage
        if coverage:
            cmd_parts.extend([
                "--cov=services",
                f"--cov-report=html:{self.coverage_dir}/{category}_coverage_html",
                f"--cov-report=json:{self.coverage_dir}/{category}_coverage.json",
                "--cov-report=term-missing"
            ])
        
        # Add HTML report
        timestamp = int(time.time())
        html_report = self.reports_dir / f"{category}_report_{timestamp}.html"
        cmd_parts.extend(["--html", str(html_report), "--self-contained-html"])
        
        # Add JSON report
        json_report = self.reports_dir / f"{category}_report_{timestamp}.json"
        cmd_parts.extend(["--json-report", f"--json-report-file={json_report}"])
        
        # Add other options
        cmd_parts.extend([
            "--tb=short",
            "--strict-markers",
            "--disable-warnings"
        ])
        
        cmd = " ".join(cmd_parts)
        print(f"Running: {cmd}")
        
        # Run tests
        result = self.run_command(cmd, capture_output=False)
        
        success = result and result.returncode == 0
        
        if success:
            print(f"✅ {category.upper()} tests completed successfully")
        else:
            print(f"❌ {category.upper()} tests failed")
            
        return success
    
    def run_all_tests(self, categories=None, coverage=True, verbose=True):
        """Run all test categories."""
        if categories is None:
            categories = list(self.test_categories.keys())
            
        print("🚀 PhotoShare Test Suite")
        print("=" * 60)
        print(f"Categories to run: {', '.join(categories)}")
        print(f"Coverage enabled: {coverage}")
        print(f"Verbose output: {verbose}")
        
        # Install dependencies
        self.install_test_dependencies()
        
        # Check services
        if not self.check_services_running():
            print("\n⚠️  Warning: Not all services are running. Some tests may fail.")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("❌ Test run cancelled")
                return False
        
        start_time = time.time()
        results = {}
        
        # Run each category
        for category in categories:
            if category in self.test_categories:
                results[category] = self.run_test_category(category, verbose, coverage)
            else:
                print(f"⚠️  Skipping unknown category: {category}")
                results[category] = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate summary
        self.generate_summary_report(results, duration)
        
        # Return overall success
        return all(results.values())
    
    def generate_summary_report(self, results, duration):
        """Generate comprehensive test summary report."""
        print("\n" + "=" * 60)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for success in results.values() if success)
        total = len(results)
        
        print(f"Test Categories: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {total - passed} ❌")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        print(f"Total Duration: {duration:.2f} seconds")
        
        print("\n📋 Category Results:")
        for category, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            description = self.test_categories.get(category, {}).get("description", "Unknown")
            print(f"  {status} {category.upper()}: {description}")
        
        # Generate JSON summary
        summary_data = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "total_categories": total,
            "passed_categories": passed,
            "failed_categories": total - passed,
            "success_rate": (passed/total)*100,
            "results": results,
            "test_categories": self.test_categories
        }
        
        summary_file = self.reports_dir / f"test_summary_{int(time.time())}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        print(f"\n📄 Reports generated in: {self.reports_dir}")
        print(f"📊 Coverage reports in: {self.coverage_dir}")
        print(f"📋 Summary report: {summary_file}")
        
        if passed == total:
            print("\n🎉 ALL TEST CATEGORIES PASSED!")
            print("✅ PhotoShare is ready for deployment!")
        else:
            print(f"\n⚠️  {total - passed} test categories failed")
            print("❌ Review failed tests before deployment")
    
    def generate_coverage_report(self):
        """Generate combined coverage report."""
        print("\n📊 Generating combined coverage report...")
        
        # Combine coverage data from all test runs
        coverage_files = list(self.coverage_dir.glob("*_coverage.json"))
        
        if not coverage_files:
            print("⚠️  No coverage data found")
            return
        
        # Use coverage package to generate combined report
        cmd = f"coverage combine {' '.join(str(f) for f in coverage_files)}"
        self.run_command(cmd)
        
        # Generate HTML report
        html_report = self.coverage_dir / "combined_coverage_html"
        cmd = f"coverage html -d {html_report}"
        self.run_command(cmd)
        
        # Generate text report
        result = self.run_command("coverage report --show-missing")
        if result:
            print("\n📈 Coverage Summary:")
            print(result.stdout)
        
        print(f"📊 Combined coverage report: {html_report}/index.html")
    
    def clean_old_reports(self, days=7):
        """Clean up old test reports and coverage data."""
        print(f"🧹 Cleaning reports older than {days} days...")
        
        import time
        cutoff_time = time.time() - (days * 24 * 3600)
        
        cleaned_count = 0
        for report_file in self.reports_dir.iterdir():
            if report_file.is_file() and report_file.stat().st_mtime < cutoff_time:
                report_file.unlink()
                cleaned_count += 1
        
        for cov_file in self.coverage_dir.iterdir():
            if cov_file.is_file() and cov_file.stat().st_mtime < cutoff_time:
                if cov_file.is_dir():
                    import shutil
                    shutil.rmtree(cov_file)
                else:
                    cov_file.unlink()
                cleaned_count += 1
        
        print(f"🧹 Cleaned {cleaned_count} old files")


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="PhotoShare Test Suite Runner")
    
    parser.add_argument(
        "--categories", 
        nargs="*",
        choices=["unit", "integration", "functional", "security", "security_compliance"],
        help="Test categories to run (default: all)"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable code coverage tracking"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true", 
        help="Reduce output verbosity"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean old reports before running"
    )
    
    parser.add_argument(
        "--coverage-only",
        action="store_true",
        help="Generate combined coverage report only"
    )
    
    args = parser.parse_args()
    
    runner = PhotoShareTestRunner()
    
    if args.clean:
        runner.clean_old_reports()
    
    if args.coverage_only:
        runner.generate_coverage_report()
        return
    
    # Run tests
    success = runner.run_all_tests(
        categories=args.categories,
        coverage=not args.no_coverage,
        verbose=not args.quiet
    )
    
    # Generate combined coverage report if coverage was enabled
    if not args.no_coverage:
        runner.generate_coverage_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()