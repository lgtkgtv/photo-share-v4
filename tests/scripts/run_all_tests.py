#!/usr/bin/env python3
"""
Master test runner for Photo Share Social Media Platform.

Executes comprehensive test suite including:
- Unit tests
- Integration tests  
- API endpoint tests
- Security tests
- Performance tests
- End-to-end tests
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Comprehensive test runner for the photo sharing platform."""
    
    def __init__(self, verbose: bool = False, coverage: bool = True):
        self.verbose = verbose
        self.coverage = coverage
        self.results = {}
        self.start_time = time.time()
        
    def run_command(self, command: List[str], description: str) -> Dict[str, Any]:
        """Run a command and capture results."""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(command)}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if self.verbose or result.returncode != 0:
                print("STDOUT:")
                print(result.stdout)
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr)
            
            success = result.returncode == 0
            status = "PASSED" if success else "FAILED"
            
            print(f"\nResult: {status} (Duration: {duration:.2f}s)")
            
            return {
                "description": description,
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "success": success
            }
            
        except Exception as e:
            print(f"Error running command: {e}")
            return {
                "description": description,
                "command": command,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0,
                "success": False
            }
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests."""
        command = ["python", "-m", "pytest", "tests/unit/", "-v"]
        if self.coverage:
            command.extend(["--cov=services/photoshare", "--cov-append"])
        
        return self.run_command(command, "Unit Tests")
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        command = ["python", "-m", "pytest", "tests/integration/", "-v"]
        if self.coverage:
            command.extend(["--cov=services/photoshare", "--cov-append"])
            
        return self.run_command(command, "Integration Tests")
    
    def run_api_tests(self) -> Dict[str, Any]:
        """Run API tests."""
        command = ["python", "-m", "pytest", "tests/api/", "-v"]
        if self.coverage:
            command.extend(["--cov=services/photoshare", "--cov-append"])
            
        return self.run_command(command, "API Tests")
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests."""
        command = ["python", "-m", "pytest", "tests/security/", "-v", "-m", "security"]
        if self.coverage:
            command.extend(["--cov=services/photoshare", "--cov-append"])
            
        return self.run_command(command, "Security Tests")
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        command = ["python", "-m", "pytest", "tests/", "-v", "-m", "performance"]
        if self.coverage:
            command.extend(["--cov=services/photoshare", "--cov-append"])
            
        return self.run_command(command, "Performance Tests")
    
    def run_feature_tests(self) -> Dict[str, Any]:
        """Run feature-specific tests."""
        features = ["social", "albums", "profiles", "notifications", "sharing"]
        all_results = []
        
        for feature in features:
            command = ["python", "-m", "pytest", "tests/", "-v", "-m", feature]
            if self.coverage:
                command.extend(["--cov=services/photoshare", "--cov-append"])
            
            result = self.run_command(command, f"Feature Tests: {feature}")
            all_results.append(result)
        
        # Combine results
        total_duration = sum(r["duration"] for r in all_results)
        all_success = all(r["success"] for r in all_results)
        
        return {
            "description": "Feature Tests (All Features)",
            "results": all_results,
            "duration": total_duration,
            "success": all_success
        }
    
    def generate_coverage_report(self) -> Dict[str, Any]:
        """Generate coverage report."""
        if not self.coverage:
            return {"description": "Coverage Report", "success": True, "skipped": True}
        
        command = ["python", "-m", "pytest", "--cov-report=html:tests/coverage_html", 
                  "--cov-report=term", "--cov-report=xml:tests/coverage.xml"]
        
        return self.run_command(command, "Coverage Report Generation")
    
    def run_linting(self) -> Dict[str, Any]:
        """Run code linting."""
        # Try different linters that might be available
        linters = [
            (["python", "-m", "flake8", "services/photoshare"], "Flake8 Linting"),
            (["python", "-m", "pylint", "services/photoshare"], "Pylint"),
            (["python", "-m", "black", "--check", "services/photoshare"], "Black Format Check")
        ]
        
        results = []
        for command, description in linters:
            try:
                result = self.run_command(command, description)
                results.append(result)
            except FileNotFoundError:
                print(f"Skipping {description} - tool not available")
        
        if not results:
            return {"description": "Code Linting", "success": True, "skipped": True}
        
        # Return combined results
        all_success = all(r["success"] for r in results)
        return {
            "description": "Code Linting",
            "results": results,
            "success": all_success
        }
    
    def print_summary(self):
        """Print test execution summary."""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("TEST EXECUTION SUMMARY")
        print("="*80)
        
        passed = 0
        failed = 0
        
        for test_type, result in self.results.items():
            if result.get("skipped"):
                status = "SKIPPED"
            elif result["success"]:
                status = "PASSED"
                passed += 1
            else:
                status = "FAILED"
                failed += 1
            
            duration = result.get("duration", 0)
            print(f"{test_type:<25} {status:<10} ({duration:.2f}s)")
        
        print("-" * 80)
        print(f"Total Tests: {passed + failed}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/(passed+failed)*100) if (passed+failed) > 0 else 0:.1f}%")
        print(f"Total Duration: {total_time:.2f}s")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for test_type, result in self.results.items():
                if not result["success"] and not result.get("skipped"):
                    print(f"  - {test_type}")
                    if result.get("stderr"):
                        print(f"    Error: {result['stderr'][:200]}...")
        
        print("="*80)
    
    def run_all(self, test_types: List[str] = None):
        """Run all specified test types."""
        if test_types is None:
            test_types = ["unit", "integration", "api", "security", "performance", "features"]
        
        print("Starting comprehensive test suite for Photo Share Social Media Platform")
        print(f"Test types: {', '.join(test_types)}")
        print(f"Coverage enabled: {self.coverage}")
        print(f"Verbose output: {self.verbose}")
        
        # Run tests based on specified types
        if "unit" in test_types:
            self.results["Unit Tests"] = self.run_unit_tests()
        
        if "integration" in test_types:
            self.results["Integration Tests"] = self.run_integration_tests()
        
        if "api" in test_types:
            self.results["API Tests"] = self.run_api_tests()
        
        if "security" in test_types:
            self.results["Security Tests"] = self.run_security_tests()
        
        if "performance" in test_types:
            self.results["Performance Tests"] = self.run_performance_tests()
        
        if "features" in test_types:
            self.results["Feature Tests"] = self.run_feature_tests()
        
        if "linting" in test_types:
            self.results["Code Linting"] = self.run_linting()
        
        # Generate coverage report
        if self.coverage:
            self.results["Coverage Report"] = self.generate_coverage_report()
        
        # Print summary
        self.print_summary()
        
        # Return overall success
        failed_tests = [name for name, result in self.results.items() 
                       if not result["success"] and not result.get("skipped")]
        
        if failed_tests:
            print(f"\nOverall result: FAILED ({len(failed_tests)} test suites failed)")
            return False
        else:
            print("\nOverall result: PASSED (All test suites passed)")
            return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive test suite for Photo Share Social Media Platform"
    )
    
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["unit", "integration", "api", "security", "performance", "features", "linting", "all"],
        default=["all"],
        help="Test types to run"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test suite (unit + integration only)"
    )
    
    args = parser.parse_args()
    
    # Handle special options
    if args.quick:
        test_types = ["unit", "integration"]
    elif "all" in args.types:
        test_types = ["unit", "integration", "api", "security", "performance", "features"]
    else:
        test_types = args.types
    
    # Create and run test runner
    runner = TestRunner(
        verbose=args.verbose,
        coverage=not args.no_coverage
    )
    
    success = runner.run_all(test_types)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()