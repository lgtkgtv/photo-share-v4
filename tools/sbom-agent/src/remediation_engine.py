#!/usr/bin/env python3
"""
SBOM Agent Remediation Engine
=============================

Intelligent automated remediation system for security vulnerabilities.
Provides safe, tested, and reversible security fixes across multiple ecosystems.

Features:
- Package version updates with dependency resolution
- Configuration security hardening
- Automated testing and validation
- Backup and rollback capabilities
- Conflict resolution and compatibility checking
"""

import os
import sys
import json
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

# Import filename manager
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))
from filename_manager import FilenameManager, OutputType, ScannerType, FileFormat


class RemediationEngine:
    """Automated security remediation engine."""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.backup_dir = self.project_path / ".security-backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize filename manager for remediation activities
        target_name = self.project_path.name
        self.filename_manager = FilenameManager(
            target_system=target_name,
            default_scanner=ScannerType.REMEDIATION_ENGINE.value
        )
    
    def generate_remediation_plan(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive remediation plan for vulnerabilities."""
        print("🔧 Analyzing vulnerabilities and generating remediation plan...")
        
        actions = []
        
        # Group vulnerabilities by package
        package_vulns = {}
        for vuln in vulnerabilities:
            package = vuln.get("package", "unknown")
            if package not in package_vulns:
                package_vulns[package] = []
            package_vulns[package].append(vuln)
        
        # Generate remediation actions for each package
        for package, vulns in package_vulns.items():
            action = self._plan_package_remediation(package, vulns)
            if action:
                actions.append(action)
        
        # Sort by priority (critical first)
        actions.sort(key=lambda x: self._get_priority_score(x["priority"]), reverse=True)
        
        plan = {
            "plan_id": str(uuid.uuid4()),
            "generated_at": datetime.now().isoformat(),
            "total_vulnerabilities": len(vulnerabilities),
            "total_actions": len(actions),
            "estimated_time_minutes": sum(action.get("estimated_time", 5) for action in actions),
            "actions": actions,
            "summary": {
                "package_updates": len([a for a in actions if a["type"] == "package_update"]),
                "config_changes": len([a for a in actions if a["type"] == "config_change"]),
                "manual_actions": len([a for a in actions if a["type"] == "manual"])
            }
        }
        
        return plan
    
    def apply_remediation(self, vulnerability: Dict[str, Any], auto_fix: bool = False, 
                         create_backup: bool = True) -> Optional[Dict[str, Any]]:
        """Apply remediation for a single vulnerability."""
        package = vulnerability.get("package")
        ecosystem = vulnerability.get("ecosystem", "").lower()
        
        if not package:
            return None
        
        print(f"🔧 Remediating {package} ({ecosystem})")
        
        try:
            # Create backup if requested
            backup_id = None
            if create_backup:
                backup_id = self._create_backup(package)
            
            # Apply ecosystem-specific remediation
            if ecosystem == "pypi":
                result = self._remediate_python_package(vulnerability, auto_fix)
            elif ecosystem == "npm":
                result = self._remediate_npm_package(vulnerability, auto_fix)
            elif ecosystem == "maven":
                result = self._remediate_maven_package(vulnerability, auto_fix)
            else:
                result = self._remediate_generic_package(vulnerability, auto_fix)
            
            if result:
                result["backup_id"] = backup_id
                result["timestamp"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            return {
                "type": "remediation_error",
                "package": package,
                "description": f"Failed to remediate {package}",
                "error": str(e),
                "success": False
            }
    
    def test_project(self) -> bool:
        """Test project after remediation to ensure functionality."""
        print("🧪 Testing project after remediation...")
        
        # Try common test commands
        test_commands = [
            ["python", "-m", "pytest", "--tb=short"],
            ["npm", "test"],
            ["mvn", "test"],
            ["cargo", "test"],
            ["go", "test", "./..."]
        ]
        
        for cmd in test_commands:
            if self._command_available(cmd[0]):
                try:
                    result = subprocess.run(
                        cmd, 
                        cwd=self.project_path, 
                        capture_output=True, 
                        text=True, 
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        print(f"✅ Tests passed with {cmd[0]}")
                        return True
                    else:
                        print(f"❌ Tests failed with {cmd[0]}: {result.stderr[:200]}")
                        
                except Exception as e:
                    print(f"⚠️ Test command {cmd[0]} failed: {e}")
        
        print("⚠️ No suitable test framework found or all tests failed")
        return False
    
    def rollback_remediation(self, backup_id: str) -> bool:
        """Rollback remediation using backup."""
        try:
            backup_path = self.backup_dir / backup_id
            if not backup_path.exists():
                print(f"❌ Backup {backup_id} not found")
                return False
            
            print(f"🔄 Rolling back using backup {backup_id}")
            
            # Restore files from backup
            for item in backup_path.iterdir():
                target = self.project_path / item.name
                if item.is_file():
                    shutil.copy2(item, target)
                elif item.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(item, target)
            
            print("✅ Rollback completed")
            return True
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False
    
    def _plan_package_remediation(self, package: str, vulnerabilities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Plan remediation for a specific package."""
        if not vulnerabilities:
            return None
        
        # Get the highest severity
        severities = [v.get("severity", "low") for v in vulnerabilities]
        priority = "critical" if "critical" in severities else "high" if "high" in severities else "medium"
        
        # Get current and target versions
        current_version = vulnerabilities[0].get("version", "unknown")
        ecosystem = vulnerabilities[0].get("ecosystem", "unknown")
        
        # Suggest fix based on ecosystem
        if ecosystem.lower() == "pypi":
            suggested_version = self._suggest_python_version(package, vulnerabilities)
        elif ecosystem.lower() == "npm":
            suggested_version = self._suggest_npm_version(package, vulnerabilities)
        else:
            suggested_version = "latest"
        
        action = {
            "id": str(uuid.uuid4()),
            "type": "package_update",
            "package": package,
            "ecosystem": ecosystem,
            "priority": priority,
            "description": f"Update {package} from {current_version} to {suggested_version}",
            "current_version": current_version,
            "target_version": suggested_version,
            "vulnerability_count": len(vulnerabilities),
            "vulnerability_ids": [v.get("vulnerability_id") for v in vulnerabilities],
            "estimated_time": 3,
            "risk_level": "low" if priority == "low" else "medium",
            "requires_testing": True
        }
        
        return action
    
    def _remediate_python_package(self, vulnerability: Dict[str, Any], auto_fix: bool) -> Dict[str, Any]:
        """Remediate Python package vulnerability."""
        package = vulnerability.get("package")
        current_version = vulnerability.get("version")
        
        # Find requirements file
        req_files = ["requirements.txt", "requirements-dev.txt", "requirements_fixed.txt"]
        target_file = None
        
        for req_file in req_files:
            file_path = self.project_path / req_file
            if file_path.exists():
                with open(file_path, 'r') as f:
                    if package in f.read():
                        target_file = file_path
                        break
        
        if not target_file:
            return {
                "type": "package_update",
                "package": package,
                "description": f"Could not find {package} in requirements files",
                "success": False,
                "error": "Package not found in requirements files"
            }
        
        # Suggest updated version
        suggested_version = self._suggest_python_version(package, [vulnerability])
        
        if not auto_fix:
            return {
                "type": "package_update",
                "package": package,
                "description": f"Would update {package} from {current_version} to {suggested_version}",
                "success": False,
                "requires_manual_action": True
            }
        
        try:
            # Update requirements file
            with open(target_file, 'r') as f:
                content = f.read()
            
            # Replace version specification
            import re
            pattern = rf"{re.escape(package)}==[\d\.]+"
            replacement = f"{package}=={suggested_version}"
            
            updated_content = re.sub(pattern, replacement, content)
            
            with open(target_file, 'w') as f:
                f.write(updated_content)
            
            # Try to install updated package
            result = subprocess.run(
                ["pip", "install", f"{package}=={suggested_version}"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            success = result.returncode == 0
            
            return {
                "type": "package_update",
                "package": package,
                "description": f"Updated {package} from {current_version} to {suggested_version}",
                "from_version": current_version,
                "to_version": suggested_version,
                "success": success,
                "file_modified": str(target_file),
                "install_output": result.stdout if success else result.stderr
            }
            
        except Exception as e:
            return {
                "type": "package_update",
                "package": package,
                "description": f"Failed to update {package}",
                "success": False,
                "error": str(e)
            }
    
    def _remediate_npm_package(self, vulnerability: Dict[str, Any], auto_fix: bool) -> Dict[str, Any]:
        """Remediate npm package vulnerability."""
        package = vulnerability.get("package")
        current_version = vulnerability.get("version")
        
        package_json = self.project_path / "package.json"
        if not package_json.exists():
            return {
                "type": "package_update",
                "package": package,
                "description": "No package.json found",
                "success": False,
                "error": "package.json not found"
            }
        
        suggested_version = self._suggest_npm_version(package, [vulnerability])
        
        if not auto_fix:
            return {
                "type": "package_update",
                "package": package,
                "description": f"Would update {package} from {current_version} to {suggested_version}",
                "success": False,
                "requires_manual_action": True
            }
        
        try:
            # Use npm update
            result = subprocess.run(
                ["npm", "install", f"{package}@{suggested_version}"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            success = result.returncode == 0
            
            return {
                "type": "package_update",
                "package": package,
                "description": f"Updated {package} from {current_version} to {suggested_version}",
                "from_version": current_version,
                "to_version": suggested_version,
                "success": success,
                "install_output": result.stdout if success else result.stderr
            }
            
        except Exception as e:
            return {
                "type": "package_update",
                "package": package,
                "description": f"Failed to update {package}",
                "success": False,
                "error": str(e)
            }
    
    def _remediate_maven_package(self, vulnerability: Dict[str, Any], auto_fix: bool) -> Dict[str, Any]:
        """Remediate Maven package vulnerability."""
        package = vulnerability.get("package")
        
        return {
            "type": "package_update",
            "package": package,
            "description": f"Maven remediation not yet implemented for {package}",
            "success": False,
            "requires_manual_action": True
        }
    
    def _remediate_generic_package(self, vulnerability: Dict[str, Any], auto_fix: bool) -> Dict[str, Any]:
        """Generic remediation for unknown ecosystems."""
        package = vulnerability.get("package")
        ecosystem = vulnerability.get("ecosystem", "unknown")
        
        return {
            "type": "manual",
            "package": package,
            "description": f"Manual remediation required for {package} ({ecosystem})",
            "success": False,
            "requires_manual_action": True,
            "recommendations": [
                f"Check {ecosystem} documentation for {package} updates",
                f"Review vulnerability details: {vulnerability.get('vulnerability_id')}",
                "Consider alternative packages if no fix available"
            ]
        }
    
    def _suggest_python_version(self, package: str, vulnerabilities: List[Dict[str, Any]]) -> str:
        """Suggest safe Python package version."""
        # Simplified version suggestion - in practice would use vulnerability databases
        version_map = {
            "jinja2": "3.1.6",
            "flask": "2.3.3",
            "requests": "2.31.0",
            "pyyaml": "6.0.1",
            "pillow": "10.0.1",
            "django": "4.2.7",
            "werkzeug": "2.3.7"
        }
        
        return version_map.get(package.lower(), "latest")
    
    def _suggest_npm_version(self, package: str, vulnerabilities: List[Dict[str, Any]]) -> str:
        """Suggest safe npm package version."""
        # Simplified version suggestion
        version_map = {
            "lodash": "4.17.21",
            "moment": "2.29.4",
            "handlebars": "4.7.8",
            "jquery": "3.7.1",
            "react": "18.2.0",
            "express": "4.18.2"
        }
        
        return version_map.get(package.lower(), "latest")
    
    def _create_backup(self, package: str) -> str:
        """Create backup of relevant files before remediation using standardized filenames."""
        # Generate standardized backup filename
        backup_filename = self.filename_manager.generate_filename(
            output_type=OutputType.BACKUP,
            file_format=FileFormat.JSON,
            scanner=ScannerType.REMEDIATION_ENGINE,
            custom_suffix=f"Package_{package}"
        )
        
        # Use the timestamp portion as backup ID for directory naming
        backup_id = backup_filename.split('_')[0:2]  # Get YYYYMMDD_HHMMSS
        backup_id = '_'.join(backup_id) + f"_{package}_{uuid.uuid4().hex[:8]}"
        
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(exist_ok=True)
        
        # Backup key files that might be modified
        files_to_backup = [
            "requirements.txt",
            "requirements-dev.txt", 
            "requirements_fixed.txt",
            "package.json",
            "package-lock.json",
            "pom.xml",
            "Cargo.toml",
            "go.mod"
        ]
        
        for filename in files_to_backup:
            source_file = self.project_path / filename
            if source_file.exists():
                shutil.copy2(source_file, backup_path / filename)
        
        # Create backup metadata with standardized filename
        metadata = {
            "backup_id": backup_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "package": package,
            "files_backed_up": [f for f in files_to_backup if (self.project_path / f).exists()],
            "backup_filename": backup_filename,
            "target_system": self.filename_manager.target_system,
            "scanner": ScannerType.REMEDIATION_ENGINE.value
        }
        
        # Use standardized filename for metadata
        metadata_filename = self.filename_manager.generate_filename(
            output_type=OutputType.METADATA,
            file_format=FileFormat.JSON,
            scanner=ScannerType.REMEDIATION_ENGINE,
            custom_suffix=f"Backup_{package}"
        )
        
        with open(backup_path / metadata_filename, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"💾 Created backup: {backup_id}")
        return backup_id
    
    def _get_priority_score(self, priority: str) -> int:
        """Convert priority to numeric score for sorting."""
        priority_map = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priority_map.get(priority.lower(), 0)
    
    def _command_available(self, command: str) -> bool:
        """Check if command is available in PATH."""
        return shutil.which(command) is not None


def main():
    """Command-line interface for remediation engine testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SBOM Agent Remediation Engine")
    parser.add_argument("project_path", help="Path to project")
    parser.add_argument("--test-remediation", help="Test remediation for package")
    parser.add_argument("--rollback", help="Rollback using backup ID")
    
    args = parser.parse_args()
    
    engine = RemediationEngine(Path(args.project_path))
    
    if args.test_remediation:
        # Create test vulnerability
        test_vuln = {
            "package": args.test_remediation,
            "version": "1.0.0",
            "ecosystem": "PyPI",
            "vulnerability_id": "TEST-001",
            "severity": "high"
        }
        
        result = engine.apply_remediation(test_vuln, auto_fix=True)
        print(json.dumps(result, indent=2))
    
    elif args.rollback:
        success = engine.rollback_remediation(args.rollback)
        print(f"Rollback {'successful' if success else 'failed'}")
    
    else:
        print("Use --test-remediation or --rollback options")


if __name__ == "__main__":
    main()