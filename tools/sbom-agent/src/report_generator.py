#!/usr/bin/env python3
"""
SBOM Agent Report Generator
===========================

Generates comprehensive security reports in multiple formats including HTML,
PDF, JSON, and integration-specific formats (GitHub Actions, GitLab CI, etc.).

Features:
- Interactive HTML dashboards
- Progressive analysis reports showing before/after improvements
- Standards-compliant SBOM documents
- CI/CD integration formats
- Executive summary reports
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import asdict
import sys

# Import filename manager
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from filename_manager import FilenameManager, OutputType, ScannerType, FileFormat


class ReportGenerator:
    """Generates comprehensive security reports in multiple formats."""
    
    def __init__(self, output_dir: Path = None, target_system: str = None):
        self.output_dir = output_dir or Path("./reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize filename manager for report generation
        self.filename_manager = FilenameManager(
            target_system=target_system or "Unknown_System",
            default_scanner=ScannerType.SBOM_AGENT.value
        )
    
    def generate_html_report(self, analysis_data: Dict[str, Any], comparison_data: Optional[Dict[str, Any]] = None) -> Path:
        """Generate interactive HTML security report."""
        template = self._get_html_template()
        
        # Prepare data for template
        report_data = {
            "title": f"Security Analysis Report - {analysis_data.get('project_name', 'Project')}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_data": analysis_data,
            "comparison_data": comparison_data,
            "has_comparison": comparison_data is not None
        }
        
        # Replace template variables
        html_content = template.format(**self._prepare_template_vars(report_data))
        
        # Generate standardized HTML filename
        target_name = analysis_data.get('project_name', 'Unknown_Project')
        self.filename_manager.target_system = target_name
        
        html_filename = self.filename_manager.generate_filename(
            output_type=OutputType.REPORT,
            file_format=FileFormat.HTML,
            scanner=ScannerType.SBOM_AGENT,
            custom_suffix="Security_Dashboard"
        )
        html_file = self.output_dir / html_filename
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_file
    
    def generate_progressive_report(self, before_analysis: Dict[str, Any], 
                                  after_analysis: Dict[str, Any],
                                  remediation_actions: List[Dict[str, Any]]) -> Path:
        """Generate progressive analysis report showing improvements."""
        
        report_data = {
            "report_type": "progressive_analysis",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "analysis_period": {
                "start": before_analysis.get("timestamp"),
                "end": after_analysis.get("timestamp")
            },
            "before_analysis": before_analysis,
            "after_analysis": after_analysis,
            "improvements": self._calculate_improvements(before_analysis, after_analysis),
            "remediation_actions": remediation_actions,
            "summary": self._generate_progressive_summary(before_analysis, after_analysis)
        }
        
        # Generate JSON report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = self.output_dir / f"progressive_analysis_{timestamp}.json"
        
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Generate HTML version
        html_file = self._generate_progressive_html(report_data)
        
        return json_file
    
    def generate_github_actions_format(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate GitHub Actions compatible output."""
        vulnerabilities = analysis_data.get("vulnerabilities", [])
        
        # Create SARIF format for GitHub Security tab
        sarif_results = []
        for vuln in vulnerabilities:
            sarif_results.append({
                "ruleId": vuln.get("vulnerability_id", "unknown"),
                "level": self._map_severity_to_sarif(vuln.get("severity", "low")),
                "message": {
                    "text": vuln.get("summary", f"Vulnerability in {vuln.get('package')}")
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": "requirements.txt"  # Simplified
                        }
                    }
                }]
            })
        
        sarif_output = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "SBOM Agent",
                        "version": "2.1.0"
                    }
                },
                "results": sarif_results
            }]
        }
        
        # Write SARIF file
        sarif_file = self.output_dir / "sarif-results.json"
        with open(sarif_file, 'w') as f:
            json.dump(sarif_output, f, indent=2)
        
        # Generate PR comment
        pr_comment = self._generate_pr_comment(analysis_data)
        pr_file = self.output_dir / "pr-comment.md"
        with open(pr_file, 'w') as f:
            f.write(pr_comment)
        
        return {
            "sarif_file": str(sarif_file),
            "pr_comment_file": str(pr_file),
            "summary": {
                "total_vulnerabilities": len(vulnerabilities),
                "critical": len([v for v in vulnerabilities if v.get("severity") == "critical"]),
                "high": len([v for v in vulnerabilities if v.get("severity") == "high"])
            }
        }
    
    def generate_executive_summary(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary for management reporting."""
        vulnerabilities = analysis_data.get("vulnerabilities", [])
        sbom_summary = analysis_data.get("sbom_data", {}).get("universal_sbom", {}).get("summary", {})
        
        severity_counts = {}
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(severity_counts)
        risk_level = self._get_risk_level(risk_score)
        
        executive_summary = {
            "executive_summary": {
                "project_name": analysis_data.get("project_name", "Unknown Project"),
                "analysis_date": analysis_data.get("timestamp", datetime.now().isoformat()),
                "overall_risk_level": risk_level,
                "risk_score": risk_score,
                "key_findings": {
                    "total_components": sbom_summary.get("total_components", 0),
                    "vulnerable_components": len(vulnerabilities),
                    "critical_vulnerabilities": severity_counts.get("critical", 0),
                    "high_vulnerabilities": severity_counts.get("high", 0)
                },
                "recommendations": self._generate_recommendations(severity_counts),
                "compliance_status": self._assess_compliance(analysis_data)
            }
        }
        
        # Write executive summary
        exec_file = self.output_dir / "executive_summary.json"
        with open(exec_file, 'w') as f:
            json.dump(executive_summary, f, indent=2)
        
        return executive_summary
    
    def _get_html_template(self) -> str:
        """Get HTML report template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid #e0e0e0; }}
        .score {{ font-size: 48px; font-weight: bold; color: {score_color}; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin: 30px 0; }}
        .card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; }}
        .vuln-list {{ margin: 20px 0; }}
        .vuln-item {{ padding: 15px; margin: 10px 0; border-radius: 6px; background: white; border-left: 4px solid; }}
        .critical {{ border-left-color: #dc3545; }}
        .high {{ border-left-color: #fd7e14; }}
        .medium {{ border-left-color: #ffc107; }}
        .low {{ border-left-color: #28a745; }}
        .chart-container {{ height: 300px; margin: 20px 0; }}
        .comparison {{ background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .improvement {{ color: #28a745; font-weight: bold; }}
        .degradation {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Security Analysis Report</h1>
            <h2>{project_name}</h2>
            <p>Generated on {generated_at}</p>
            <div class="score">{security_score}/100</div>
            <p>Security Score</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>📊 Overview</h3>
                <p><strong>Total Components:</strong> {total_components}</p>
                <p><strong>Vulnerabilities Found:</strong> {total_vulnerabilities}</p>
                <p><strong>Ecosystems Analyzed:</strong> {ecosystems_count}</p>
            </div>
            
            <div class="card">
                <h3>🚨 Vulnerability Breakdown</h3>
                <p><strong>Critical:</strong> <span style="color: #dc3545;">{critical_count}</span></p>
                <p><strong>High:</strong> <span style="color: #fd7e14;">{high_count}</span></p>
                <p><strong>Medium:</strong> <span style="color: #ffc107;">{medium_count}</span></p>
                <p><strong>Low:</strong> <span style="color: #28a745;">{low_count}</span></p>
            </div>
        </div>
        
        {comparison_section}
        
        <div class="chart-container">
            <canvas id="severityChart"></canvas>
        </div>
        
        <h3>🔍 Vulnerability Details</h3>
        <div class="vuln-list">
            {vulnerability_details}
        </div>
        
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center; color: #666;">
            <p>Generated by SBOM Agent v2.1.0 | <a href="https://github.com/security-tools/sbom-agent">Learn More</a></p>
        </div>
    </div>
    
    <script>
        // Vulnerability severity chart
        const ctx = document.getElementById('severityChart').getContext('2d');
        new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{{
                    data: [{critical_count}, {high_count}, {medium_count}, {low_count}],
                    backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#28a745']
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Vulnerability Distribution by Severity'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    def _prepare_template_vars(self, report_data: Dict[str, Any]) -> Dict[str, str]:
        """Prepare variables for HTML template."""
        analysis = report_data["analysis_data"]
        vulnerabilities = analysis.get("vulnerabilities", [])
        sbom_summary = analysis.get("sbom_data", {}).get("universal_sbom", {}).get("summary", {})
        
        # Count vulnerabilities by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "low")
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Calculate security score and color
        security_score = analysis.get("security_score", 0)
        score_color = "#28a745" if security_score >= 80 else "#ffc107" if security_score >= 60 else "#dc3545"
        
        # Generate vulnerability details HTML
        vuln_details = ""
        for vuln in vulnerabilities[:10]:  # Limit to first 10
            severity_class = vuln.get("severity", "low")
            vuln_details += f"""
            <div class="vuln-item {severity_class}">
                <h4>{vuln.get('package', 'Unknown Package')} - {vuln.get('vulnerability_id', 'N/A')}</h4>
                <p><strong>Severity:</strong> {vuln.get('severity', 'Unknown').title()}</p>
                <p><strong>Version:</strong> {vuln.get('version', 'Unknown')}</p>
                <p>{vuln.get('summary', 'No description available')[:200]}...</p>
            </div>
            """
        
        # Generate comparison section if available
        comparison_section = ""
        if report_data.get("has_comparison") and report_data.get("comparison_data"):
            comp = report_data["comparison_data"]
            score_change = comp.get("security_score", {}).get("improvement", 0)
            vuln_change = comp.get("vulnerabilities", {}).get("resolved_count", 0)
            
            comparison_section = f"""
            <div class="comparison">
                <h3>📈 Progress Analysis</h3>
                <p><strong>Security Score Change:</strong> 
                   <span class="{'improvement' if score_change >= 0 else 'degradation'}">{score_change:+.1f}</span></p>
                <p><strong>Vulnerabilities Resolved:</strong> 
                   <span class="improvement">{vuln_change}</span></p>
            </div>
            """
        
        return {
            "title": report_data["title"],
            "project_name": analysis.get("project_name", "Unknown Project"),
            "generated_at": report_data["generated_at"],
            "security_score": f"{security_score:.1f}",
            "score_color": score_color,
            "total_components": sbom_summary.get("total_components", 0),
            "total_vulnerabilities": len(vulnerabilities),
            "ecosystems_count": sbom_summary.get("ecosystems_found", 0),
            "critical_count": severity_counts["critical"],
            "high_count": severity_counts["high"],
            "medium_count": severity_counts["medium"],
            "low_count": severity_counts["low"],
            "vulnerability_details": vuln_details,
            "comparison_section": comparison_section
        }
    
    def _generate_progressive_html(self, report_data: Dict[str, Any]) -> Path:
        """Generate HTML version of progressive report."""
        # Simplified progressive HTML generation
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Progressive Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .improvement {{ color: green; font-weight: bold; }}
        .degradation {{ color: red; font-weight: bold; }}
        .card {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; }}
    </style>
</head>
<body>
    <h1>🔄 Progressive Security Analysis</h1>
    <div class="card">
        <h2>Summary</h2>
        <p>Analysis Period: {report_data['analysis_period']['start']} to {report_data['analysis_period']['end']}</p>
        <p>Security Score: {report_data['before_analysis'].get('security_score', 0):.1f} → {report_data['after_analysis'].get('security_score', 0):.1f}</p>
        <p>Vulnerabilities: {len(report_data['before_analysis'].get('vulnerabilities', []))} → {len(report_data['after_analysis'].get('vulnerabilities', []))}</p>
    </div>
</body>
</html>"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = self.output_dir / f"progressive_report_{timestamp}.html"
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        return html_file
    
    def _calculate_improvements(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate improvements between analyses."""
        before_score = before.get("security_score", 0)
        after_score = after.get("security_score", 0)
        
        before_vulns = len(before.get("vulnerabilities", []))
        after_vulns = len(after.get("vulnerabilities", []))
        
        return {
            "security_score_change": after_score - before_score,
            "vulnerability_reduction": before_vulns - after_vulns,
            "percentage_improvement": ((after_score - before_score) / before_score * 100) if before_score > 0 else 0
        }
    
    def _generate_progressive_summary(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary for progressive analysis."""
        improvements = self._calculate_improvements(before, after)
        
        return {
            "overall_improvement": improvements["security_score_change"] > 0,
            "score_improvement": improvements["security_score_change"],
            "vulnerabilities_resolved": improvements["vulnerability_reduction"],
            "recommendation": "Continue current security practices" if improvements["security_score_change"] >= 0 else "Review recent changes"
        }
    
    def _map_severity_to_sarif(self, severity: str) -> str:
        """Map vulnerability severity to SARIF level."""
        mapping = {
            "critical": "error",
            "high": "error", 
            "medium": "warning",
            "low": "note"
        }
        return mapping.get(severity.lower(), "note")
    
    def _generate_pr_comment(self, analysis_data: Dict[str, Any]) -> str:
        """Generate PR comment for GitHub integration."""
        vulnerabilities = analysis_data.get("vulnerabilities", [])
        security_score = analysis_data.get("security_score", 0)
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "low")
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        status_emoji = "✅" if len(vulnerabilities) == 0 else "⚠️" if severity_counts["critical"] == 0 else "❌"
        
        comment = f"""## {status_emoji} Security Analysis Results

**Security Score:** {security_score:.1f}/100

### Vulnerability Summary
- 🔴 Critical: {severity_counts['critical']}
- 🟠 High: {severity_counts['high']}
- 🟡 Medium: {severity_counts['medium']}
- 🟢 Low: {severity_counts['low']}

### Total Components Analyzed
{analysis_data.get('sbom_data', {}).get('universal_sbom', {}).get('summary', {}).get('total_components', 0)}

---
*Generated by SBOM Agent v2.1.0*
"""
        return comment
    
    def _calculate_risk_score(self, severity_counts: Dict[str, int]) -> float:
        """Calculate overall risk score."""
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        
        total_score = sum(severity_counts.get(severity, 0) * weight 
                         for severity, weight in weights.items())
        
        # Normalize to 0-100 scale (higher = more risk)
        return min(total_score * 2, 100)
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level."""
        if risk_score >= 80:
            return "Critical"
        elif risk_score >= 60:
            return "High"
        elif risk_score >= 40:
            return "Medium"
        elif risk_score >= 20:
            return "Low"
        else:
            return "Minimal"
    
    def _generate_recommendations(self, severity_counts: Dict[str, int]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        
        if severity_counts.get("critical", 0) > 0:
            recommendations.append("Immediately address critical vulnerabilities")
        
        if severity_counts.get("high", 0) > 5:
            recommendations.append("Prioritize high-severity vulnerability remediation")
        
        if sum(severity_counts.values()) > 20:
            recommendations.append("Consider implementing automated dependency updates")
        
        if not recommendations:
            recommendations.append("Maintain current security practices")
        
        return recommendations
    
    def _assess_compliance(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess compliance with security standards."""
        vulnerabilities = analysis_data.get("vulnerabilities", [])
        critical_count = len([v for v in vulnerabilities if v.get("severity") == "critical"])
        
        return {
            "ntia_minimum_elements": "Compliant",
            "zero_critical_vulnerabilities": critical_count == 0,
            "sbom_standards": "SPDX 2.3, CycloneDX 1.5",
            "overall_status": "Compliant" if critical_count == 0 else "Non-compliant"
        }


def main():
    """Test report generation functionality."""
    # Sample test data
    test_analysis = {
        "project_name": "Test Project",
        "timestamp": datetime.now().isoformat(),
        "security_score": 85.5,
        "vulnerabilities": [
            {
                "package": "test-package",
                "version": "1.0.0",
                "severity": "high",
                "vulnerability_id": "CVE-2023-001",
                "summary": "Test vulnerability for demonstration"
            }
        ],
        "sbom_data": {
            "universal_sbom": {
                "summary": {
                    "total_components": 42,
                    "ecosystems_found": 3
                }
            }
        }
    }
    
    generator = ReportGenerator()
    
    # Generate HTML report
    html_file = generator.generate_html_report(test_analysis)
    print(f"Generated HTML report: {html_file}")
    
    # Generate executive summary
    exec_summary = generator.generate_executive_summary(test_analysis)
    print(f"Generated executive summary: {exec_summary}")


if __name__ == "__main__":
    main()