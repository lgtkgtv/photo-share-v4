#!/usr/bin/env python3
"""
Container Security Scanner
=========================

Scans Docker containers for security vulnerabilities and misconfigurations.
"""

import subprocess
import json
import sys
import os
from datetime import datetime


def run_command(cmd):
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


class ContainerSecurityScanner:
    """Container security scanner."""
    
    def __init__(self):
        self.report = {
            "scan_time": datetime.now().isoformat(),
            "findings": [],
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "passed": 0}
        }
    
    def add_finding(self, severity, title, description, recommendation=""):
        """Add a security finding."""
        finding = {
            "severity": severity,
            "title": title,
            "description": description,
            "recommendation": recommendation
        }
        self.report["findings"].append(finding)
        self.report["summary"][severity.lower()] += 1
    
    def scan_dockerfile_security(self, dockerfile_path):
        """Scan Dockerfile for security issues."""
        print(f"🔍 Scanning Dockerfile: {dockerfile_path}")
        
        if not os.path.exists(dockerfile_path):
            self.add_finding("HIGH", "Missing Dockerfile", f"Dockerfile not found: {dockerfile_path}")
            return
        
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Check for non-root user
        if "USER " not in content or "USER root" in content:
            self.add_finding("HIGH", "Running as root", 
                           "Container runs as root user, increasing attack surface",
                           "Add 'USER <non-root-user>' to Dockerfile")
        else:
            self.add_finding("PASSED", "Non-root user", "Container runs as non-root user")
        
        # Check for COPY with --chown
        if "COPY " in content and "--chown=" not in content:
            self.add_finding("MEDIUM", "File ownership not set", 
                           "COPY commands don't set proper ownership",
                           "Use COPY --chown=user:group")
        
        # Check for package updates
        if "apt-get update" in content and "apt-get upgrade" not in content:
            self.add_finding("MEDIUM", "No security updates", 
                           "Package updates not installed",
                           "Add 'apt-get upgrade -y' after apt-get update")
        
        # Check for cleanup
        if "apt-get" in content and "rm -rf /var/lib/apt/lists/*" not in content:
            self.add_finding("LOW", "Package cache not cleaned", 
                           "APT cache not cleaned, increasing image size",
                           "Add 'rm -rf /var/lib/apt/lists/*' after package installation")
        
        # Check for HEALTHCHECK
        if "HEALTHCHECK" not in content:
            self.add_finding("LOW", "No health check", 
                           "Container has no health check defined",
                           "Add HEALTHCHECK instruction to Dockerfile")
        else:
            self.add_finding("PASSED", "Health check defined", "Container has health check")
    
    def scan_compose_security(self, compose_path):
        """Scan Docker Compose for security configurations."""
        print(f"🔍 Scanning Docker Compose: {compose_path}")
        
        if not os.path.exists(compose_path):
            self.add_finding("HIGH", "Missing Compose file", f"Compose file not found: {compose_path}")
            return
        
        with open(compose_path, 'r') as f:
            content = f.read()
        
        # Check for security_opt
        if "security_opt:" not in content:
            self.add_finding("HIGH", "No security options", 
                           "No security options configured in Docker Compose",
                           "Add security_opt with no-new-privileges:true")
        else:
            self.add_finding("PASSED", "Security options configured", "Security options found in compose file")
        
        # Check for read_only
        if "read_only: true" not in content:
            self.add_finding("MEDIUM", "Containers not read-only", 
                           "Containers are not configured as read-only",
                           "Add 'read_only: true' to service definitions")
        
        # Check for capabilities drop
        if "cap_drop:" not in content:
            self.add_finding("HIGH", "No capability dropping", 
                           "Linux capabilities not dropped",
                           "Add 'cap_drop: [ALL]' and selectively add needed capabilities")
        
        # Check for resource limits
        if "deploy:" not in content or "resources:" not in content:
            self.add_finding("MEDIUM", "No resource limits", 
                           "No resource limits configured",
                           "Add deploy.resources.limits to prevent resource exhaustion")
        else:
            self.add_finding("PASSED", "Resource limits configured", "Resource limits found")
    
    def scan_runtime_security(self):
        """Scan running containers for security issues."""
        print("🔍 Scanning running containers...")
        
        # Get running containers
        code, stdout, stderr = run_command("docker ps --format '{{.Names}}' 2>/dev/null")
        if code != 0:
            self.add_finding("LOW", "Docker not accessible", "Cannot access Docker daemon")
            return
        
        containers = [line.strip() for line in stdout.splitlines() if line.strip()]
        
        if not containers:
            self.add_finding("LOW", "No running containers", "No containers currently running")
            return
        
        for container in containers:
            self.scan_container_runtime(container)
    
    def scan_container_runtime(self, container_name):
        """Scan individual container runtime security."""
        print(f"  🐳 Scanning container: {container_name}")
        
        # Check if running as root
        code, stdout, stderr = run_command(f"docker exec {container_name} whoami 2>/dev/null")
        if code == 0 and "root" in stdout:
            self.add_finding("HIGH", f"Container {container_name} runs as root", 
                           f"Container {container_name} is running as root user",
                           "Configure container to run as non-root user")
        
        # Check for privileged mode
        code, stdout, stderr = run_command(f"docker inspect {container_name} --format '{{{{.HostConfig.Privileged}}}}' 2>/dev/null")
        if code == 0 and "true" in stdout:
            self.add_finding("CRITICAL", f"Privileged container: {container_name}", 
                           f"Container {container_name} is running in privileged mode",
                           "Remove privileged mode and use specific capabilities instead")
        
        # Check for host network mode
        code, stdout, stderr = run_command(f"docker inspect {container_name} --format '{{{{.HostConfig.NetworkMode}}}}' 2>/dev/null")
        if code == 0 and "host" in stdout:
            self.add_finding("HIGH", f"Host network mode: {container_name}", 
                           f"Container {container_name} uses host network mode",
                           "Use bridge network mode for better isolation")
    
    def check_security_tools(self):
        """Check if security scanning tools are available."""
        print("🔍 Checking security tools availability...")
        
        tools = {
            "trivy": "Vulnerability scanner for containers",
            "hadolint": "Dockerfile linter",
            "docker-bench-security": "Docker security benchmark"
        }
        
        for tool, description in tools.items():
            code, stdout, stderr = run_command(f"which {tool}")
            if code != 0:
                self.add_finding("LOW", f"Security tool not available: {tool}", 
                               f"{description} not installed",
                               f"Install {tool} for enhanced security scanning")
    
    def run_trivy_scan(self, image_name):
        """Run Trivy vulnerability scan if available."""
        code, stdout, stderr = run_command("which trivy")
        if code != 0:
            return
        
        print(f"🔍 Running Trivy scan on {image_name}...")
        code, stdout, stderr = run_command(f"trivy image --format json --quiet {image_name} 2>/dev/null")
        
        if code == 0 and stdout:
            try:
                trivy_results = json.loads(stdout)
                vulnerabilities = []
                
                for result in trivy_results.get("Results", []):
                    for vuln in result.get("Vulnerabilities", []):
                        vulnerabilities.append(vuln)
                
                critical = len([v for v in vulnerabilities if v.get("Severity") == "CRITICAL"])
                high = len([v for v in vulnerabilities if v.get("Severity") == "HIGH"])
                
                if critical > 0:
                    self.add_finding("CRITICAL", f"Critical vulnerabilities in {image_name}", 
                                   f"Found {critical} critical vulnerabilities",
                                   "Update base image and dependencies")
                elif high > 0:
                    self.add_finding("HIGH", f"High severity vulnerabilities in {image_name}", 
                                   f"Found {high} high severity vulnerabilities",
                                   "Update base image and dependencies")
                else:
                    self.add_finding("PASSED", f"No critical vulnerabilities in {image_name}", 
                                   "No critical or high severity vulnerabilities found")
                                   
            except json.JSONDecodeError:
                pass
    
    def generate_report(self):
        """Generate security scan report."""
        print("\n" + "="*70)
        print("🛡️  CONTAINER SECURITY SCAN REPORT")
        print("="*70)
        
        summary = self.report["summary"]
        total_issues = summary["critical"] + summary["high"] + summary["medium"] + summary["low"]
        
        print(f"📊 SUMMARY:")
        print(f"   🔴 Critical: {summary['critical']}")
        print(f"   🟠 High:     {summary['high']}")
        print(f"   🟡 Medium:   {summary['medium']}")
        print(f"   🔵 Low:      {summary['low']}")
        print(f"   ✅ Passed:   {summary['passed']}")
        print(f"   📊 Total Issues: {total_issues}")
        
        if total_issues == 0:
            print("\n🎉 No security issues found!")
            return 0
        
        print(f"\n🔍 DETAILED FINDINGS ({len(self.report['findings'])} items):")
        print("-" * 70)
        
        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "PASSED": 4}
        findings = sorted(self.report["findings"], key=lambda x: severity_order.get(x["severity"], 999))
        
        for i, finding in enumerate(findings, 1):
            severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵", "PASSED": "✅"}
            icon = severity_icon.get(finding["severity"], "❓")
            
            print(f"{i:2}. {icon} {finding['severity']}: {finding['title']}")
            print(f"     {finding['description']}")
            if finding.get("recommendation"):
                print(f"     💡 {finding['recommendation']}")
            print()
        
        # Return exit code based on severity
        if summary["critical"] > 0:
            return 2
        elif summary["high"] > 0:
            return 1
        else:
            return 0


def main():
    """Main function."""
    print("🛡️  PhotoShare Container Security Scanner")
    print("==========================================\n")
    
    scanner = ContainerSecurityScanner()
    
    # Scan Dockerfiles
    dockerfiles = [
        "services/auth-service/Dockerfile.production",
        "services/photoshare/Dockerfile.production"
    ]
    
    for dockerfile in dockerfiles:
        scanner.scan_dockerfile_security(dockerfile)
    
    # Scan Docker Compose files
    compose_files = [
        "docker-compose.production.yml",
        "docker-compose.separated.yml"
    ]
    
    for compose_file in compose_files:
        if os.path.exists(compose_file):
            scanner.scan_compose_security(compose_file)
    
    # Scan runtime security
    scanner.scan_runtime_security()
    
    # Check security tools
    scanner.check_security_tools()
    
    # Run Trivy scans if available
    images = ["python:3.11-slim", "postgres:15-alpine"]
    for image in images:
        scanner.run_trivy_scan(image)
    
    # Generate report
    exit_code = scanner.generate_report()
    
    # Save detailed report
    report_file = f"security-scan-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(scanner.report, f, indent=2)
    
    print(f"📄 Detailed report saved to: {report_file}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())