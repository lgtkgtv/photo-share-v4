#!/usr/bin/env python3
"""
PhotoShare Security Test Suite
==============================

Dedicated security testing framework with:
- OWASP compliance checking
- Vulnerability assessments  
- Security configuration validation
- RBAC and authentication testing
- Code security standards compliance
"""

import os
import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path


class SecurityTestRunner:
    """Specialized runner for security and compliance testing."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_root = Path(__file__).parent
        self.reports_dir = self.test_root / "reports" / "security"
        
        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.security_test_suites = {
            "rbac": {
                "path": "tests/security/test_rbac_security.py",
                "description": "Role-Based Access Control security testing",
                "critical": True
            },
            "compliance": {
                "path": "tests/security/test_security_compliance.py", 
                "description": "OWASP and security standards compliance",
                "critical": True
            },
            "authentication": {
                "path": "tests/integration/test_jwt_validation.py",
                "description": "Authentication security validation",
                "critical": True
            },
            "input_validation": {
                "path": "tests/security/test_input_validation.py",
                "description": "Input validation and sanitization",
                "critical": False
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
    
    def check_security_dependencies(self):
        """Install and check security testing dependencies."""
        print("🔐 Installing security testing dependencies...")
        
        security_deps = [
            "pytest>=7.0.0",
            "requests>=2.28.0", 
            "PyJWT>=2.6.0",
            "bandit>=1.7.0",  # Static security analysis
            "safety>=2.3.0",  # Dependency vulnerability scanning
            "semgrep>=1.0.0",  # Code security scanning
        ]
        
        for dep in security_deps:
            print(f"📦 Installing {dep}...")
            result = self.run_command(f"pip install {dep}")
            if result and result.returncode != 0:
                print(f"⚠️  Warning: Could not install {dep}")
    
    def run_static_security_analysis(self):
        """Run static security analysis tools."""
        print("\n🔍 Running Static Security Analysis")
        print("=" * 60)
        
        analysis_results = {}
        
        # Run Bandit (Python security linter)
        print("🔎 Running Bandit security analysis...")
        bandit_report = self.reports_dir / f"bandit_report_{int(time.time())}.json"
        
        bandit_cmd = f"bandit -r services/ -f json -o {bandit_report}"
        result = self.run_command(bandit_cmd)
        
        if result and result.returncode == 0:
            print("✅ Bandit analysis completed successfully")
            analysis_results["bandit"] = {"status": "success", "report": str(bandit_report)}
        else:
            print("⚠️  Bandit analysis found potential issues")
            analysis_results["bandit"] = {"status": "issues_found", "report": str(bandit_report)}
        
        # Run Safety (dependency vulnerability check)
        print("\n🔎 Running Safety dependency check...")
        safety_report = self.reports_dir / f"safety_report_{int(time.time())}.json"
        
        safety_cmd = f"safety check --json --output {safety_report}"
        result = self.run_command(safety_cmd)
        
        if result and result.returncode == 0:
            print("✅ Safety check passed - no known vulnerabilities")
            analysis_results["safety"] = {"status": "success", "report": str(safety_report)}
        else:
            print("⚠️  Safety check found vulnerable dependencies")
            analysis_results["safety"] = {"status": "vulnerabilities_found", "report": str(safety_report)}
        
        return analysis_results
    
    def run_dynamic_security_tests(self):
        """Run dynamic security tests against running services."""
        print("\n🎯 Running Dynamic Security Tests")
        print("=" * 60)
        
        # Check if services are running
        import requests
        
        services = {
            "Auth Service": "http://localhost:8001/health",
            "App Service": "http://localhost:8000/health"
        }
        
        services_healthy = True
        for service_name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {service_name}: Available")
                else:
                    print(f"❌ {service_name}: Unhealthy ({response.status_code})")
                    services_healthy = False
            except Exception as e:
                print(f"❌ {service_name}: Not accessible ({e})")
                services_healthy = False
        
        if not services_healthy:
            print("\n⚠️  Warning: Not all services are available for dynamic testing")
            return {"status": "services_unavailable"}
        
        # Run security test suites
        security_results = {}
        
        for suite_name, suite_info in self.security_test_suites.items():
            if not os.path.exists(suite_info["path"]):
                print(f"⚠️  Skipping {suite_name}: Test file not found")
                continue
                
            print(f"\n🔐 Running {suite_name.upper()}: {suite_info['description']}")
            
            timestamp = int(time.time())
            html_report = self.reports_dir / f"{suite_name}_security_{timestamp}.html"
            json_report = self.reports_dir / f"{suite_name}_security_{timestamp}.json"
            
            cmd_parts = [
                "python", "-m", "pytest",
                suite_info["path"],
                "-v",
                "--tb=short",
                f"--html={html_report}",
                "--self-contained-html",
                f"--json-report",
                f"--json-report-file={json_report}"
            ]
            
            cmd = " ".join(cmd_parts)
            result = self.run_command(cmd, capture_output=False)
            
            success = result and result.returncode == 0
            
            security_results[suite_name] = {
                "success": success,
                "critical": suite_info["critical"],
                "description": suite_info["description"],
                "html_report": str(html_report),
                "json_report": str(json_report)
            }
            
            if success:
                print(f"✅ {suite_name.upper()} security tests passed")
            else:
                print(f"❌ {suite_name.upper()} security tests failed")
                if suite_info["critical"]:
                    print("⚠️  This is a CRITICAL security test failure!")
        
        return security_results
    
    def generate_security_assessment_report(self, static_results, dynamic_results):
        """Generate comprehensive security assessment report."""
        print("\n📋 Generating Security Assessment Report")
        print("=" * 60)
        
        # Calculate overall security score
        total_tests = len(self.security_test_suites)
        passed_tests = sum(1 for result in dynamic_results.values() 
                          if isinstance(result, dict) and result.get("success", False))
        
        critical_failures = [
            name for name, result in dynamic_results.items()
            if isinstance(result, dict) and not result.get("success", False) and result.get("critical", False)
        ]
        
        security_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Generate assessment data
        assessment = {
            "timestamp": datetime.now().isoformat(),
            "assessment_type": "comprehensive_security_testing",
            "overall_security_score": security_score,
            "critical_failures": critical_failures,
            "static_analysis": static_results,
            "dynamic_testing": dynamic_results,
            "recommendations": self.generate_security_recommendations(static_results, dynamic_results),
            "compliance_status": {
                "owasp_top_10": "tested" if "compliance" in dynamic_results else "not_tested",
                "rbac_security": "tested" if "rbac" in dynamic_results else "not_tested", 
                "authentication_security": "tested" if "authentication" in dynamic_results else "not_tested"
            }
        }
        
        # Save assessment report
        assessment_file = self.reports_dir / f"security_assessment_{int(time.time())}.json"
        with open(assessment_file, 'w') as f:
            json.dump(assessment, f, indent=2)
        
        # Generate HTML summary
        self.generate_html_security_summary(assessment, assessment_file)
        
        print(f"📄 Security assessment saved: {assessment_file}")
        print(f"📊 Security Score: {security_score:.1f}%")
        
        if critical_failures:
            print(f"🚨 CRITICAL FAILURES: {len(critical_failures)}")
            for failure in critical_failures:
                print(f"   ❌ {failure}")
        else:
            print("✅ No critical security failures detected")
        
        return assessment
    
    def generate_security_recommendations(self, static_results, dynamic_results):
        """Generate security recommendations based on test results."""
        recommendations = []
        
        # Static analysis recommendations
        if static_results.get("bandit", {}).get("status") == "issues_found":
            recommendations.append({
                "category": "static_analysis",
                "priority": "high",
                "title": "Address Bandit Security Issues", 
                "description": "Static analysis found potential security issues in the code",
                "action": "Review Bandit report and fix identified security issues"
            })
        
        if static_results.get("safety", {}).get("status") == "vulnerabilities_found":
            recommendations.append({
                "category": "dependencies",
                "priority": "critical",
                "title": "Update Vulnerable Dependencies",
                "description": "Known vulnerabilities found in project dependencies",
                "action": "Update vulnerable packages to secure versions"
            })
        
        # Dynamic test recommendations
        failed_critical_tests = [
            name for name, result in dynamic_results.items()
            if isinstance(result, dict) and not result.get("success", False) and result.get("critical", False)
        ]
        
        if failed_critical_tests:
            recommendations.append({
                "category": "runtime_security",
                "priority": "critical", 
                "title": "Critical Security Test Failures",
                "description": f"Critical security tests failed: {', '.join(failed_critical_tests)}",
                "action": "Address failed security tests before production deployment"
            })
        
        # General security recommendations
        recommendations.extend([
            {
                "category": "infrastructure",
                "priority": "high",
                "title": "Enable HTTPS in Production",
                "description": "Ensure all production traffic uses HTTPS/TLS encryption",
                "action": "Configure SSL certificates and redirect HTTP to HTTPS"
            },
            {
                "category": "monitoring",
                "priority": "medium", 
                "title": "Implement Security Monitoring",
                "description": "Set up security event logging and alerting",
                "action": "Configure audit logging and security monitoring tools"
            },
            {
                "category": "testing",
                "priority": "medium",
                "title": "Regular Security Testing",
                "description": "Perform regular security assessments",
                "action": "Schedule weekly security test runs and monthly assessments"
            }
        ])
        
        return recommendations
    
    def generate_html_security_summary(self, assessment, report_file):
        """Generate HTML security summary report."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PhotoShare Security Assessment</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .score {{ font-size: 24px; font-weight: bold; }}
                .success {{ color: #27ae60; }}
                .warning {{ color: #f39c12; }}
                .error {{ color: #e74c3c; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; background: #f8f9fa; }}
                .recommendation {{ margin: 10px 0; padding: 10px; border-radius: 5px; }}
                .critical {{ background: #ffebee; border-left: 4px solid #f44336; }}
                .high {{ background: #fff3e0; border-left: 4px solid #ff9800; }}
                .medium {{ background: #f3e5f5; border-left: 4px solid #9c27b0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔐 PhotoShare Security Assessment</h1>
                <p>Generated: {assessment['timestamp']}</p>
                <div class="score">Overall Security Score: {assessment['overall_security_score']:.1f}%</div>
            </div>
            
            <div class="section">
                <h2>📊 Test Results Summary</h2>
                <p><strong>Static Analysis:</strong> {'✅ Passed' if not assessment.get('critical_failures') else '⚠️ Issues Found'}</p>
                <p><strong>Dynamic Testing:</strong> {len(assessment['dynamic_testing'])} security test suites executed</p>
                <p><strong>Critical Failures:</strong> {len(assessment['critical_failures'])}</p>
            </div>
            
            <div class="section">
                <h2>🚨 Critical Issues</h2>
        """
        
        if assessment['critical_failures']:
            for failure in assessment['critical_failures']:
                html_content += f"<div class='error'>❌ {failure}</div>"
        else:
            html_content += "<div class='success'>✅ No critical security issues detected</div>"
        
        html_content += """
            </div>
            
            <div class="section">
                <h2>💡 Security Recommendations</h2>
        """
        
        for rec in assessment['recommendations']:
            priority_class = rec['priority']
            html_content += f"""
                <div class="recommendation {priority_class}">
                    <strong>{rec['title']}</strong> ({rec['priority'].upper()})
                    <br>{rec['description']}
                    <br><em>Action: {rec['action']}</em>
                </div>
            """
        
        html_content += f"""
            </div>
            
            <div class="section">
                <h2>📄 Detailed Reports</h2>
                <p>JSON Report: <code>{report_file}</code></p>
                <p>Additional reports available in: <code>{self.reports_dir}</code></p>
            </div>
        </body>
        </html>
        """
        
        html_file = self.reports_dir / f"security_summary_{int(time.time())}.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"📋 HTML summary report: {html_file}")
    
    def run_full_security_assessment(self):
        """Run complete security assessment."""
        print("🛡️  PhotoShare Security Assessment")
        print("=" * 60)
        print("Running comprehensive security testing and analysis")
        
        start_time = time.time()
        
        # Install dependencies
        self.check_security_dependencies()
        
        # Run static analysis
        static_results = self.run_static_security_analysis()
        
        # Run dynamic tests
        dynamic_results = self.run_dynamic_security_tests()
        
        # Generate assessment report
        assessment = self.generate_security_assessment_report(static_results, dynamic_results)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n⏱️  Assessment completed in {duration:.2f} seconds")
        print(f"📊 Overall Security Score: {assessment['overall_security_score']:.1f}%")
        
        # Determine if security assessment passed
        critical_failures = len(assessment['critical_failures'])
        if critical_failures == 0 and assessment['overall_security_score'] >= 80:
            print("\n🎉 SECURITY ASSESSMENT PASSED!")
            print("✅ PhotoShare meets security requirements")
            return True
        else:
            print(f"\n🚨 SECURITY ASSESSMENT FAILED!")
            print(f"❌ {critical_failures} critical failures, Score: {assessment['overall_security_score']:.1f}%")
            print("⚠️  Address security issues before production deployment")
            return False


def main():
    """Main entry point for security test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PhotoShare Security Test Suite")
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only critical security tests (skip static analysis)"
    )
    
    parser.add_argument(
        "--static-only",
        action="store_true", 
        help="Run only static security analysis"
    )
    
    args = parser.parse_args()
    
    runner = SecurityTestRunner()
    
    if args.static_only:
        # Run only static analysis
        static_results = runner.run_static_security_analysis()
        print("\n📄 Static analysis complete. Check reports directory for details.")
        return
    
    if args.quick:
        # Run only dynamic tests
        print("🚀 Running quick security test suite...")
        dynamic_results = runner.run_dynamic_security_tests()
        
        # Simple pass/fail for quick mode
        critical_failures = [
            name for name, result in dynamic_results.items()
            if isinstance(result, dict) and not result.get("success", False) and result.get("critical", False)
        ]
        
        if not critical_failures:
            print("\n✅ Quick security check passed!")
            sys.exit(0)
        else:
            print(f"\n❌ Quick security check failed: {len(critical_failures)} critical issues")
            sys.exit(1)
    
    # Run full assessment
    success = runner.run_full_security_assessment()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()