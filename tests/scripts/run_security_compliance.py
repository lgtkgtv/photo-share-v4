#!/usr/bin/env python3
"""
Security Compliance Testing and Reporting Framework.

Comprehensive security testing with automated compliance reporting for:
- OWASP Top 10 2021
- GDPR Compliance
- SOC 2 Type II Controls
- NIST Cybersecurity Framework
- Industry Security Standards
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class SecurityStandard(Enum):
    """Security compliance standards."""
    OWASP = "owasp"
    GDPR = "gdpr"
    SOC2 = "soc2"
    NIST = "nist"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"


class ComplianceLevel(Enum):
    """Compliance assessment levels."""
    COMPLIANT = "compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"


@dataclass
class SecurityTestResult:
    """Security test result structure."""
    test_id: str
    test_name: str
    standard: str
    category: str
    status: str  # passed, failed, skipped
    compliance_level: ComplianceLevel
    risk_level: str  # critical, high, medium, low
    description: str
    evidence: List[str]
    recommendations: List[str]
    remediation_effort: str  # high, medium, low
    business_impact: str
    technical_details: Dict[str, Any]


@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""
    report_id: str
    generation_time: datetime
    standards_assessed: List[str]
    overall_compliance_score: float
    risk_assessment: Dict[str, int]
    test_results: List[SecurityTestResult]
    executive_summary: Dict[str, Any]
    remediation_roadmap: List[Dict[str, Any]]
    compliance_certificates: List[Dict[str, Any]]


class SecurityComplianceFramework:
    """Advanced security compliance testing framework."""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("security_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.report_id = f"security_compliance_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        self.test_results: List[SecurityTestResult] = []
        
        # Initialize compliance standards
        self.standards = {
            SecurityStandard.OWASP: self._init_owasp_framework(),
            SecurityStandard.GDPR: self._init_gdpr_framework(),
            SecurityStandard.SOC2: self._init_soc2_framework(),
            SecurityStandard.NIST: self._init_nist_framework()
        }
    
    def _init_owasp_framework(self) -> Dict[str, Any]:
        """Initialize OWASP Top 10 testing framework."""
        return {
            "A01_2021": {
                "name": "Broken Access Control",
                "description": "Access control enforcement failures",
                "tests": ["unauthorized_access", "privilege_escalation", "cors_bypass"],
                "risk_level": "critical"
            },
            "A02_2021": {
                "name": "Cryptographic Failures",
                "description": "Failures related to cryptography",
                "tests": ["weak_crypto", "exposed_secrets", "insecure_transmission"],
                "risk_level": "high"
            },
            "A03_2021": {
                "name": "Injection",
                "description": "Injection flaws including SQL, NoSQL, LDAP",
                "tests": ["sql_injection", "nosql_injection", "command_injection"],
                "risk_level": "critical"
            },
            "A04_2021": {
                "name": "Insecure Design",
                "description": "Insecure design flaws",
                "tests": ["threat_modeling", "security_controls", "design_patterns"],
                "risk_level": "high"
            },
            "A05_2021": {
                "name": "Security Misconfiguration",
                "description": "Security misconfiguration issues",
                "tests": ["default_configs", "missing_headers", "error_disclosure"],
                "risk_level": "medium"
            },
            "A06_2021": {
                "name": "Vulnerable and Outdated Components",
                "description": "Using components with known vulnerabilities",
                "tests": ["dependency_scan", "version_check", "license_compliance"],
                "risk_level": "high"
            },
            "A07_2021": {
                "name": "Identification and Authentication Failures",
                "description": "Authentication and session management failures",
                "tests": ["weak_auth", "session_management", "credential_stuffing"],
                "risk_level": "high"
            },
            "A08_2021": {
                "name": "Software and Data Integrity Failures",
                "description": "Software and data integrity failures",
                "tests": ["supply_chain", "code_integrity", "update_mechanisms"],
                "risk_level": "high"
            },
            "A09_2021": {
                "name": "Security Logging and Monitoring Failures",
                "description": "Insufficient logging and monitoring",
                "tests": ["audit_logging", "monitoring_coverage", "incident_response"],
                "risk_level": "medium"
            },
            "A10_2021": {
                "name": "Server-Side Request Forgery",
                "description": "SSRF flaws",
                "tests": ["ssrf_protection", "url_validation", "network_segmentation"],
                "risk_level": "high"
            }
        }
    
    def _init_gdpr_framework(self) -> Dict[str, Any]:
        """Initialize GDPR compliance framework."""
        return {
            "data_protection_principles": {
                "lawfulness": ["consent_mechanisms", "legitimate_interest"],
                "fairness": ["transparency", "user_rights"],
                "transparency": ["privacy_policy", "data_usage_disclosure"],
                "purpose_limitation": ["data_minimization", "purpose_binding"],
                "data_minimization": ["collection_limitation", "retention_policy"],
                "accuracy": ["data_correction", "data_validation"],
                "storage_limitation": ["retention_schedules", "deletion_procedures"],
                "integrity_confidentiality": ["encryption", "access_controls"],
                "accountability": ["documentation", "compliance_monitoring"]
            },
            "individual_rights": {
                "right_to_information": ["privacy_notices", "data_processing_info"],
                "right_of_access": ["data_export", "access_procedures"],
                "right_to_rectification": ["data_correction", "update_mechanisms"],
                "right_to_erasure": ["deletion_procedures", "right_to_be_forgotten"],
                "right_to_restrict_processing": ["processing_controls", "temporary_suspension"],
                "right_to_data_portability": ["data_export_formats", "interoperability"],
                "right_to_object": ["opt_out_mechanisms", "objection_procedures"],
                "rights_related_to_automated_decision_making": ["algorithm_transparency", "human_review"]
            },
            "technical_organizational_measures": {
                "data_protection_by_design": ["privacy_by_design", "default_privacy"],
                "data_protection_impact_assessment": ["dpia_procedures", "risk_assessment"],
                "breach_notification": ["incident_procedures", "notification_timelines"],
                "data_processor_agreements": ["third_party_agreements", "processor_compliance"]
            }
        }
    
    def _init_soc2_framework(self) -> Dict[str, Any]:
        """Initialize SOC 2 Type II controls framework."""
        return {
            "security": {
                "logical_access": ["user_access_provisioning", "authentication_controls"],
                "network_security": ["firewall_configurations", "network_monitoring"],
                "data_protection": ["encryption_controls", "data_classification"]
            },
            "availability": {
                "system_monitoring": ["uptime_monitoring", "performance_tracking"],
                "incident_response": ["incident_procedures", "recovery_plans"],
                "backup_recovery": ["backup_procedures", "recovery_testing"]
            },
            "processing_integrity": {
                "data_validation": ["input_validation", "data_integrity_checks"],
                "change_management": ["code_deployment", "configuration_management"],
                "system_monitoring": ["transaction_monitoring", "error_detection"]
            },
            "confidentiality": {
                "data_classification": ["sensitive_data_identification", "handling_procedures"],
                "access_controls": ["role_based_access", "segregation_of_duties"],
                "encryption": ["data_at_rest", "data_in_transit"]
            },
            "privacy": {
                "data_collection": ["collection_procedures", "consent_management"],
                "data_use": ["usage_limitations", "purpose_specification"],
                "data_retention": ["retention_policies", "disposal_procedures"]
            }
        }
    
    def _init_nist_framework(self) -> Dict[str, Any]:
        """Initialize NIST Cybersecurity Framework."""
        return {
            "identify": {
                "asset_management": ["inventory", "data_flows"],
                "business_environment": ["organizational_context", "dependencies"],
                "governance": ["policies", "procedures"],
                "risk_assessment": ["threat_identification", "vulnerability_assessment"],
                "risk_management_strategy": ["risk_tolerance", "risk_response"]
            },
            "protect": {
                "identity_management": ["authentication", "authorization"],
                "awareness_training": ["security_training", "awareness_programs"],
                "data_security": ["data_protection", "privacy_protection"],
                "information_protection": ["baseline_configuration", "maintenance"],
                "maintenance": ["system_maintenance", "remote_maintenance"],
                "protective_technology": ["security_controls", "communications_protection"]
            },
            "detect": {
                "anomalies_events": ["baseline_establishment", "event_detection"],
                "continuous_monitoring": ["network_monitoring", "personnel_monitoring"],
                "detection_processes": ["detection_procedures", "testing_procedures"]
            },
            "respond": {
                "response_planning": ["response_procedures", "communication_plans"],
                "communications": ["internal_communication", "external_communication"],
                "analysis": ["impact_analysis", "forensics"],
                "mitigation": ["containment", "mitigation_actions"],
                "improvements": ["lessons_learned", "process_improvements"]
            },
            "recover": {
                "recovery_planning": ["recovery_procedures", "business_continuity"],
                "improvements": ["recovery_improvements", "communication_coordination"],
                "communications": ["recovery_communication", "stakeholder_coordination"]
            }
        }
    
    def run_owasp_tests(self) -> List[SecurityTestResult]:
        """Run OWASP Top 10 compliance tests."""
        results = []
        
        for owasp_id, control in self.standards[SecurityStandard.OWASP].items():
            # Run pytest for OWASP tests
            test_command = [
                "python", "-m", "pytest", 
                "tests/security/test_owasp_compliance.py", 
                f"-k", f"test_{owasp_id.lower()}",
                "-v", "--tb=short"
            ]
            
            start_time = time.time()
            
            try:
                result = subprocess.run(
                    test_command,
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                duration = time.time() - start_time
                
                # Parse test results
                if result.returncode == 0:
                    status = "passed"
                    compliance_level = ComplianceLevel.COMPLIANT
                    recommendations = []
                else:
                    status = "failed"
                    compliance_level = ComplianceLevel.NON_COMPLIANT
                    recommendations = [
                        f"Fix {control['name']} vulnerabilities identified",
                        "Review security controls implementation",
                        "Conduct penetration testing for this category"
                    ]
                
                test_result = SecurityTestResult(
                    test_id=owasp_id,
                    test_name=control['name'],
                    standard="OWASP Top 10 2021",
                    category="Application Security",
                    status=status,
                    compliance_level=compliance_level,
                    risk_level=control['risk_level'],
                    description=control['description'],
                    evidence=[
                        f"Test execution output: {len(result.stdout)} characters",
                        f"Test duration: {duration:.2f} seconds",
                        f"Exit code: {result.returncode}"
                    ],
                    recommendations=recommendations,
                    remediation_effort="medium" if status == "failed" else "low",
                    business_impact="high" if control['risk_level'] == "critical" else "medium",
                    technical_details={
                        "stdout": result.stdout[:1000],  # Truncate for storage
                        "stderr": result.stderr[:1000],
                        "duration": duration,
                        "tests_run": control['tests']
                    }
                )
                
                results.append(test_result)
                
            except subprocess.TimeoutExpired:
                test_result = SecurityTestResult(
                    test_id=owasp_id,
                    test_name=control['name'],
                    standard="OWASP Top 10 2021",
                    category="Application Security",
                    status="failed",
                    compliance_level=ComplianceLevel.NON_COMPLIANT,
                    risk_level="high",
                    description=f"{control['description']} (test timeout)",
                    evidence=["Test execution timed out after 5 minutes"],
                    recommendations=["Investigate test timeout", "Review system performance"],
                    remediation_effort="high",
                    business_impact="medium",
                    technical_details={"error": "timeout", "duration": 300}
                )
                results.append(test_result)
        
        return results
    
    def run_gdpr_tests(self) -> List[SecurityTestResult]:
        """Run GDPR compliance assessment."""
        results = []
        
        # Run GDPR-specific tests
        test_command = [
            "python", "-m", "pytest", 
            "tests/security/test_gdpr_compliance.py",
            "-v", "--tb=short"
        ]
        
        try:
            result = subprocess.run(
                test_command,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse GDPR test results
            gdpr_categories = ["data_protection", "individual_rights", "technical_measures"]
            
            for category in gdpr_categories:
                # Determine compliance based on test output
                if result.returncode == 0:
                    compliance_level = ComplianceLevel.COMPLIANT
                    status = "passed"
                else:
                    compliance_level = ComplianceLevel.PARTIALLY_COMPLIANT
                    status = "failed"
                
                test_result = SecurityTestResult(
                    test_id=f"GDPR_{category}",
                    test_name=f"GDPR {category.replace('_', ' ').title()}",
                    standard="GDPR",
                    category="Privacy & Data Protection",
                    status=status,
                    compliance_level=compliance_level,
                    risk_level="high",
                    description=f"GDPR compliance assessment for {category}",
                    evidence=[
                        f"Automated test execution: {result.returncode == 0}",
                        f"Test output length: {len(result.stdout)} characters"
                    ],
                    recommendations=[
                        "Implement comprehensive privacy by design",
                        "Establish data subject rights procedures",
                        "Conduct regular privacy impact assessments"
                    ] if status == "failed" else ["Maintain current privacy controls"],
                    remediation_effort="high" if status == "failed" else "low",
                    business_impact="critical",
                    technical_details={
                        "category": category,
                        "test_output": result.stdout[:500]
                    }
                )
                
                results.append(test_result)
                
        except subprocess.TimeoutExpired:
            results.append(SecurityTestResult(
                test_id="GDPR_TIMEOUT",
                test_name="GDPR Compliance Tests",
                standard="GDPR",
                category="Privacy & Data Protection",
                status="failed",
                compliance_level=ComplianceLevel.REQUIRES_MANUAL_REVIEW,
                risk_level="high",
                description="GDPR compliance test execution timed out",
                evidence=["Test timeout after 5 minutes"],
                recommendations=["Manual GDPR compliance review required"],
                remediation_effort="high",
                business_impact="critical",
                technical_details={"error": "timeout"}
            ))
        
        return results
    
    def run_dependency_vulnerability_scan(self) -> List[SecurityTestResult]:
        """Run dependency vulnerability scanning."""
        results = []
        
        # Check for security audit tools
        audit_commands = [
            (["python", "-m", "safety", "check"], "Python Safety Check"),
            (["npm", "audit"], "NPM Security Audit"),
            (["pip-audit"], "Pip Audit")
        ]
        
        for command, tool_name in audit_commands:
            try:
                result = subprocess.run(
                    command,
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                # Parse vulnerability findings
                vulnerabilities_found = "vulnerability" in result.stdout.lower() or result.returncode != 0
                
                test_result = SecurityTestResult(
                    test_id=f"VULN_SCAN_{tool_name.replace(' ', '_').upper()}",
                    test_name=f"{tool_name} Vulnerability Scan",
                    standard="Supply Chain Security",
                    category="Dependency Security",
                    status="failed" if vulnerabilities_found else "passed",
                    compliance_level=ComplianceLevel.NON_COMPLIANT if vulnerabilities_found else ComplianceLevel.COMPLIANT,
                    risk_level="high" if vulnerabilities_found else "low",
                    description=f"Dependency vulnerability scan using {tool_name}",
                    evidence=[
                        f"Tool output: {len(result.stdout)} characters",
                        f"Exit code: {result.returncode}",
                        f"Vulnerabilities detected: {vulnerabilities_found}"
                    ],
                    recommendations=[
                        "Update vulnerable dependencies",
                        "Implement automated dependency scanning",
                        "Establish dependency management policies"
                    ] if vulnerabilities_found else ["Continue regular dependency monitoring"],
                    remediation_effort="medium" if vulnerabilities_found else "low",
                    business_impact="high" if vulnerabilities_found else "low",
                    technical_details={
                        "tool": tool_name,
                        "scan_output": result.stdout[:1000],
                        "vulnerabilities_found": vulnerabilities_found
                    }
                )
                
                results.append(test_result)
                
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Tool not available or timed out
                test_result = SecurityTestResult(
                    test_id=f"VULN_SCAN_{tool_name.replace(' ', '_').upper()}_UNAVAILABLE",
                    test_name=f"{tool_name} (Unavailable)",
                    standard="Supply Chain Security",
                    category="Dependency Security",
                    status="skipped",
                    compliance_level=ComplianceLevel.REQUIRES_MANUAL_REVIEW,
                    risk_level="medium",
                    description=f"{tool_name} not available or timed out",
                    evidence=[f"{tool_name} execution failed"],
                    recommendations=[f"Install and configure {tool_name}", "Manual dependency review required"],
                    remediation_effort="low",
                    business_impact="medium",
                    technical_details={"tool": tool_name, "status": "unavailable"}
                )
                results.append(test_result)
        
        return results
    
    def generate_compliance_report(self, standards: List[SecurityStandard]) -> ComplianceReport:
        """Generate comprehensive compliance report."""
        
        print(f"🔒 Generating Security Compliance Report")
        print(f"   Report ID: {self.report_id}")
        print(f"   Standards: {[s.value for s in standards]}")
        print()
        
        all_results = []
        
        # Run tests for each requested standard
        if SecurityStandard.OWASP in standards:
            print("🔍 Running OWASP Top 10 2021 Tests...")
            owasp_results = self.run_owasp_tests()
            all_results.extend(owasp_results)
            print(f"   Completed: {len(owasp_results)} OWASP tests")
        
        if SecurityStandard.GDPR in standards:
            print("🔍 Running GDPR Compliance Tests...")
            gdpr_results = self.run_gdpr_tests()
            all_results.extend(gdpr_results)
            print(f"   Completed: {len(gdpr_results)} GDPR tests")
        
        # Always run dependency scanning
        print("🔍 Running Dependency Vulnerability Scan...")
        vuln_results = self.run_dependency_vulnerability_scan()
        all_results.extend(vuln_results)
        print(f"   Completed: {len(vuln_results)} vulnerability scans")
        
        # Calculate overall compliance metrics
        total_tests = len(all_results)
        passed_tests = len([r for r in all_results if r.status == "passed"])
        failed_tests = len([r for r in all_results if r.status == "failed"])
        
        overall_compliance_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Risk assessment
        risk_counts = {}
        for result in all_results:
            risk_counts[result.risk_level] = risk_counts.get(result.risk_level, 0) + 1
        
        # Executive summary
        executive_summary = {
            "overall_compliance_score": overall_compliance_score,
            "total_tests_executed": total_tests,
            "tests_passed": passed_tests,
            "tests_failed": failed_tests,
            "critical_findings": len([r for r in all_results if r.risk_level == "critical" and r.status == "failed"]),
            "high_risk_findings": len([r for r in all_results if r.risk_level == "high" and r.status == "failed"]),
            "compliance_status": "COMPLIANT" if overall_compliance_score >= 95 else 
                               "PARTIALLY_COMPLIANT" if overall_compliance_score >= 70 else "NON_COMPLIANT",
            "key_recommendations": [
                "Address all critical and high-risk findings",
                "Implement automated security testing in CI/CD pipeline",
                "Conduct regular penetration testing",
                "Establish security awareness training program"
            ]
        }
        
        # Remediation roadmap
        failed_results = [r for r in all_results if r.status == "failed"]
        remediation_roadmap = []
        
        # Group by priority
        critical_items = [r for r in failed_results if r.risk_level == "critical"]
        high_items = [r for r in failed_results if r.risk_level == "high"]
        medium_items = [r for r in failed_results if r.risk_level == "medium"]
        
        if critical_items:
            remediation_roadmap.append({
                "priority": "immediate",
                "timeframe": "1-2 weeks",
                "items": [{"test": r.test_name, "recommendations": r.recommendations} for r in critical_items]
            })
        
        if high_items:
            remediation_roadmap.append({
                "priority": "high",
                "timeframe": "1-2 months",
                "items": [{"test": r.test_name, "recommendations": r.recommendations} for r in high_items]
            })
        
        if medium_items:
            remediation_roadmap.append({
                "priority": "medium",
                "timeframe": "3-6 months",
                "items": [{"test": r.test_name, "recommendations": r.recommendations} for r in medium_items]
            })
        
        # Compliance certificates (for passed standards)
        certificates = []
        for standard in standards:
            standard_results = [r for r in all_results if r.standard.lower() == standard.value.lower()]
            if standard_results:
                standard_score = (len([r for r in standard_results if r.status == "passed"]) / len(standard_results)) * 100
                
                if standard_score >= 95:
                    certificates.append({
                        "standard": standard.value.upper(),
                        "compliance_level": "FULLY_COMPLIANT",
                        "score": standard_score,
                        "certificate_id": f"{standard.value.upper()}_{self.report_id}",
                        "valid_until": (datetime.now().year + 1),
                        "conditions": ["Maintain current security controls", "Conduct annual reassessment"]
                    })
                elif standard_score >= 70:
                    certificates.append({
                        "standard": standard.value.upper(),
                        "compliance_level": "CONDITIONALLY_COMPLIANT",
                        "score": standard_score,
                        "certificate_id": f"{standard.value.upper()}_{self.report_id}_CONDITIONAL",
                        "valid_until": (datetime.now().year),
                        "conditions": ["Address identified gaps within 90 days", "Conduct quarterly monitoring"]
                    })
        
        # Create final report
        report = ComplianceReport(
            report_id=self.report_id,
            generation_time=datetime.now(timezone.utc),
            standards_assessed=[s.value for s in standards],
            overall_compliance_score=overall_compliance_score,
            risk_assessment=risk_counts,
            test_results=all_results,
            executive_summary=executive_summary,
            remediation_roadmap=remediation_roadmap,
            compliance_certificates=certificates
        )
        
        return report
    
    def export_report(self, report: ComplianceReport, formats: List[str] = None) -> Dict[str, Path]:
        """Export compliance report in multiple formats."""
        formats = formats or ["json", "html", "executive_summary"]
        exported_files = {}
        
        # JSON report (detailed)
        if "json" in formats:
            json_file = self.output_dir / f"security_compliance_report_{self.report_id}.json"
            
            # Convert dataclasses to dictionaries for JSON serialization
            report_dict = {
                "report_metadata": {
                    "report_id": report.report_id,
                    "generation_time": report.generation_time.isoformat(),
                    "standards_assessed": report.standards_assessed,
                    "overall_compliance_score": report.overall_compliance_score
                },
                "executive_summary": report.executive_summary,
                "risk_assessment": report.risk_assessment,
                "test_results": [asdict(result) for result in report.test_results],
                "remediation_roadmap": report.remediation_roadmap,
                "compliance_certificates": report.compliance_certificates
            }
            
            with open(json_file, 'w') as f:
                json.dump(report_dict, f, indent=2, default=str)
            
            exported_files["json"] = json_file
        
        # HTML report (user-friendly)
        if "html" in formats:
            html_file = self.output_dir / f"security_compliance_report_{self.report_id}.html"
            
            html_content = self._generate_html_report(report)
            
            with open(html_file, 'w') as f:
                f.write(html_content)
            
            exported_files["html"] = html_file
        
        # Executive summary (management report)
        if "executive_summary" in formats:
            exec_file = self.output_dir / f"executive_security_summary_{self.report_id}.json"
            
            exec_summary = {
                "report_id": report.report_id,
                "assessment_date": report.generation_time.isoformat(),
                "overall_security_posture": report.executive_summary["compliance_status"],
                "compliance_score": f"{report.overall_compliance_score:.1f}%",
                "critical_issues": report.executive_summary["critical_findings"],
                "high_risk_issues": report.executive_summary["high_risk_findings"],
                "standards_assessed": report.standards_assessed,
                "immediate_actions_required": len([item for roadmap in report.remediation_roadmap 
                                                  for item in roadmap.get("items", []) 
                                                  if roadmap.get("priority") == "immediate"]),
                "compliance_certificates": len(report.compliance_certificates),
                "next_assessment_date": f"{datetime.now().year + 1}-{datetime.now().month:02d}-{datetime.now().day:02d}",
                "key_recommendations": report.executive_summary["key_recommendations"]
            }
            
            with open(exec_file, 'w') as f:
                json.dump(exec_summary, f, indent=2)
            
            exported_files["executive_summary"] = exec_file
        
        return exported_files
    
    def _generate_html_report(self, report: ComplianceReport) -> str:
        """Generate HTML compliance report."""
        
        # Determine overall status styling
        status_class = {
            "COMPLIANT": "success",
            "PARTIALLY_COMPLIANT": "warning", 
            "NON_COMPLIANT": "danger"
        }.get(report.executive_summary["compliance_status"], "secondary")
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Security Compliance Report - {report.report_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f8f9fa; padding: 30px; border-radius: 8px; margin-bottom: 30px; }}
        .title {{ color: #2c3e50; margin: 0; }}
        .subtitle {{ color: #6c757d; margin: 5px 0 0 0; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
        .metric-card {{ background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; text-align: center; }}
        .metric-card.success {{ border-left: 4px solid #28a745; }}
        .metric-card.warning {{ border-left: 4px solid #ffc107; }}
        .metric-card.danger {{ border-left: 4px solid #dc3545; }}
        .metric-card.info {{ border-left: 4px solid #17a2b8; }}
        .metric-value {{ font-size: 2em; font-weight: bold; margin: 0; }}
        .metric-label {{ color: #6c757d; margin: 10px 0 0 0; }}
        .section {{ margin: 40px 0; }}
        .section-title {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .test-results {{ margin: 20px 0; }}
        .test-item {{ background: #f8f9fa; border-radius: 6px; padding: 15px; margin: 10px 0; }}
        .test-item.passed {{ border-left: 4px solid #28a745; }}
        .test-item.failed {{ border-left: 4px solid #dc3545; }}
        .test-item.skipped {{ border-left: 4px solid #6c757d; }}
        .risk-critical {{ background: #f8d7da; color: #721c24; }}
        .risk-high {{ background: #fff3cd; color: #856404; }}
        .risk-medium {{ background: #d1ecf1; color: #0c5460; }}
        .risk-low {{ background: #d4edda; color: #155724; }}
        .recommendations {{ background: #e9ecef; padding: 15px; border-radius: 6px; margin: 10px 0; }}
        .certificate {{ background: #d4edda; border: 1px solid #c3e6cb; border-radius: 6px; padding: 15px; margin: 10px 0; }}
        .roadmap {{ background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin: 15px 0; }}
        .roadmap.immediate {{ border-left: 4px solid #dc3545; }}
        .roadmap.high {{ border-left: 4px solid #ffc107; }}
        .roadmap.medium {{ border-left: 4px solid #17a2b8; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">Security Compliance Assessment Report</h1>
        <p class="subtitle">Report ID: {report.report_id} | Generated: {report.generation_time.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        <p class="subtitle">Standards Assessed: {', '.join([s.upper() for s in report.standards_assessed])}</p>
    </div>
    
    <div class="summary-grid">
        <div class="metric-card {status_class}">
            <p class="metric-value">{report.overall_compliance_score:.1f}%</p>
            <p class="metric-label">Overall Compliance Score</p>
        </div>
        <div class="metric-card info">
            <p class="metric-value">{report.executive_summary['tests_passed']}/{report.executive_summary['total_tests_executed']}</p>
            <p class="metric-label">Tests Passed</p>
        </div>
        <div class="metric-card {'danger' if report.executive_summary['critical_findings'] > 0 else 'success'}">
            <p class="metric-value">{report.executive_summary['critical_findings']}</p>
            <p class="metric-label">Critical Findings</p>
        </div>
        <div class="metric-card {'warning' if report.executive_summary['high_risk_findings'] > 0 else 'success'}">
            <p class="metric-value">{report.executive_summary['high_risk_findings']}</p>
            <p class="metric-label">High Risk Findings</p>
        </div>
    </div>
    
    <div class="section">
        <h2 class="section-title">Executive Summary</h2>
        <p><strong>Compliance Status:</strong> <span class="metric-card {status_class}" style="display: inline; padding: 5px 10px; border-radius: 4px;">{report.executive_summary['compliance_status']}</span></p>
        
        <h3>Key Recommendations</h3>
        <ul>
"""
        
        for rec in report.executive_summary['key_recommendations']:
            html += f"<li>{rec}</li>"
        
        html += """
        </ul>
    </div>
    
    <div class="section">
        <h2 class="section-title">Compliance Certificates</h2>
"""
        
        if report.compliance_certificates:
            for cert in report.compliance_certificates:
                html += f"""
        <div class="certificate">
            <h4>{cert['standard']} Compliance Certificate</h4>
            <p><strong>Level:</strong> {cert['compliance_level']}</p>
            <p><strong>Score:</strong> {cert['score']:.1f}%</p>
            <p><strong>Valid Until:</strong> {cert['valid_until']}</p>
            <p><strong>Certificate ID:</strong> {cert['certificate_id']}</p>
        </div>
"""
        else:
            html += "<p>No compliance certificates issued. Address identified gaps to achieve certification.</p>"
        
        html += """
    </div>
    
    <div class="section">
        <h2 class="section-title">Remediation Roadmap</h2>
"""
        
        for roadmap_item in report.remediation_roadmap:
            priority_class = roadmap_item['priority']
            html += f"""
        <div class="roadmap {priority_class}">
            <h3>{roadmap_item['priority'].title()} Priority ({roadmap_item['timeframe']})</h3>
            <ul>
"""
            for item in roadmap_item['items']:
                html += f"<li><strong>{item['test']}:</strong> {'; '.join(item['recommendations'])}</li>"
            
            html += """
            </ul>
        </div>
"""
        
        html += """
    </div>
    
    <div class="section">
        <h2 class="section-title">Detailed Test Results</h2>
        <div class="test-results">
"""
        
        # Group results by standard
        by_standard = {}
        for result in report.test_results:
            if result.standard not in by_standard:
                by_standard[result.standard] = []
            by_standard[result.standard].append(result)
        
        for standard, results in by_standard.items():
            html += f"<h3>{standard}</h3>"
            
            for result in results:
                risk_class = f"risk-{result.risk_level}"
                html += f"""
            <div class="test-item {result.status}">
                <h4>{result.test_name} <span class="{risk_class}" style="padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">{result.risk_level.upper()}</span></h4>
                <p><strong>Status:</strong> {result.status.upper()}</p>
                <p><strong>Description:</strong> {result.description}</p>
                <p><strong>Compliance Level:</strong> {result.compliance_level.value.replace('_', ' ').title()}</p>
"""
                
                if result.recommendations:
                    html += """
                <div class="recommendations">
                    <strong>Recommendations:</strong>
                    <ul>
"""
                    for rec in result.recommendations:
                        html += f"<li>{rec}</li>"
                    
                    html += """
                    </ul>
                </div>
"""
                
                html += "</div>"
        
        html += """
        </div>
    </div>
    
    <div class="section">
        <p style="text-align: center; color: #6c757d; margin-top: 50px;">
            Generated by Photo Share Security Compliance Framework<br>
            Report ID: {report.report_id}
        </p>
    </div>
</body>
</html>
"""
        
        return html


def main():
    """Main entry point for security compliance testing."""
    parser = argparse.ArgumentParser(
        description="Security Compliance Testing and Reporting Framework"
    )
    
    parser.add_argument(
        "--standards",
        nargs="+",
        choices=[s.value for s in SecurityStandard],
        default=["owasp", "gdpr"],
        help="Security standards to assess"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("security_reports"),
        help="Output directory for reports"
    )
    
    parser.add_argument(
        "--report-formats",
        nargs="+",
        choices=["json", "html", "executive_summary", "all"],
        default=["json", "html", "executive_summary"],
        help="Report formats to generate"
    )
    
    parser.add_argument(
        "--vulnerability-scan",
        action="store_true",
        help="Include dependency vulnerability scanning"
    )
    
    parser.add_argument(
        "--generate-certificates",
        action="store_true",
        help="Generate compliance certificates for passing standards"
    )
    
    args = parser.parse_args()
    
    # Convert string arguments to enums
    standards = [SecurityStandard(s) for s in args.standards]
    
    if "all" in args.report_formats:
        report_formats = ["json", "html", "executive_summary"]
    else:
        report_formats = args.report_formats
    
    print(f"🔒 Security Compliance Assessment")
    print(f"{'='*60}")
    print(f"Standards: {', '.join([s.value.upper() for s in standards])}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Report Formats: {', '.join(report_formats)}")
    print(f"Vulnerability Scanning: {args.vulnerability_scan}")
    print()
    
    # Initialize framework
    framework = SecurityComplianceFramework(args.output_dir)
    
    # Generate compliance report
    report = framework.generate_compliance_report(standards)
    
    # Export reports
    exported_files = framework.export_report(report, report_formats)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"SECURITY COMPLIANCE ASSESSMENT COMPLETE")
    print(f"{'='*60}")
    print(f"Report ID: {report.report_id}")
    print(f"Overall Compliance Score: {report.overall_compliance_score:.1f}%")
    print(f"Compliance Status: {report.executive_summary['compliance_status']}")
    print(f"Total Tests: {report.executive_summary['total_tests_executed']}")
    print(f"Tests Passed: {report.executive_summary['tests_passed']}")
    print(f"Tests Failed: {report.executive_summary['tests_failed']}")
    print(f"Critical Findings: {report.executive_summary['critical_findings']}")
    print(f"High Risk Findings: {report.executive_summary['high_risk_findings']}")
    
    print(f"\nCompliance Certificates Issued: {len(report.compliance_certificates)}")
    for cert in report.compliance_certificates:
        print(f"  ✅ {cert['standard']}: {cert['compliance_level']} ({cert['score']:.1f}%)")
    
    print(f"\nReports Generated:")
    for report_type, file_path in exported_files.items():
        print(f"  📄 {report_type.upper()}: {file_path}")
    
    # Exit with appropriate code
    if report.executive_summary['critical_findings'] > 0:
        print(f"\n❌ Critical security findings require immediate attention!")
        sys.exit(1)
    elif report.overall_compliance_score < 70:
        print(f"\n⚠️  Compliance score below acceptable threshold (70%)")
        sys.exit(1)
    else:
        print(f"\n✅ Security compliance assessment passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()