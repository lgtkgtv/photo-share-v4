#!/usr/bin/env python3
"""
Version Management System for Security Tools
=============================================

Provides version tracking, compatibility checking, and update management
for the security tools ecosystem.
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import semantic_version


class ToolVersion:
    """Represents a tool version with semantic versioning support."""
    
    def __init__(self, version_string: str, tool_name: str = None):
        self.version_string = version_string
        self.tool_name = tool_name
        try:
            self.semantic_version = semantic_version.Version(version_string)
        except ValueError:
            # Fallback for non-semantic versions
            self.semantic_version = None
            
    def __str__(self) -> str:
        return self.version_string
        
    def __repr__(self) -> str:
        return f"ToolVersion('{self.version_string}', tool='{self.tool_name}')"
        
    def is_compatible_with(self, other: 'ToolVersion') -> bool:
        """Check if this version is compatible with another version."""
        if not self.semantic_version or not other.semantic_version:
            return self.version_string == other.version_string
            
        # Compatible if major version matches and minor version is >= required
        return (self.semantic_version.major == other.semantic_version.major and
                self.semantic_version >= other.semantic_version)
    
    def is_newer_than(self, other: 'ToolVersion') -> bool:
        """Check if this version is newer than another version."""
        if not self.semantic_version or not other.semantic_version:
            return False
            
        return self.semantic_version > other.semantic_version


class VersionManager:
    """Manages versions across the security tools ecosystem."""
    
    def __init__(self, tools_root: Path = None):
        self.tools_root = tools_root or Path(__file__).parent.parent
        self.ecosystem_version = self._load_ecosystem_version()
        self.tool_versions = self._load_tool_versions()
        
    def _load_ecosystem_version(self) -> ToolVersion:
        """Load the ecosystem version."""
        version_file = self.tools_root / "VERSION"
        if version_file.exists():
            version_string = version_file.read_text().strip()
            return ToolVersion(version_string, "ecosystem")
        return ToolVersion("0.0.0", "ecosystem")
    
    def _load_tool_versions(self) -> Dict[str, ToolVersion]:
        """Load versions for all tools in the ecosystem."""
        versions = {}
        
        # Tool directories
        tool_dirs = [
            "sbom-agent",
            "security-scanner-agent", 
            "cicd-integration-agent"
        ]
        
        for tool_dir in tool_dirs:
            tool_path = self.tools_root / tool_dir
            version_file = tool_path / "VERSION"
            
            if version_file.exists():
                version_string = version_file.read_text().strip()
                versions[tool_dir] = ToolVersion(version_string, tool_dir)
            else:
                versions[tool_dir] = ToolVersion("0.0.0", tool_dir)
                
        return versions
    
    def get_tool_version(self, tool_name: str) -> Optional[ToolVersion]:
        """Get version for a specific tool."""
        return self.tool_versions.get(tool_name)
    
    def get_ecosystem_version(self) -> ToolVersion:
        """Get the overall ecosystem version."""
        return self.ecosystem_version
    
    def check_tool_compatibility(self, tool_name: str, required_version: str) -> Tuple[bool, str]:
        """Check if a tool meets version requirements."""
        current_version = self.get_tool_version(tool_name)
        if not current_version:
            return False, f"Tool '{tool_name}' not found"
            
        required = ToolVersion(required_version)
        if current_version.is_compatible_with(required):
            return True, f"Tool '{tool_name}' v{current_version} is compatible"
        else:
            return False, f"Tool '{tool_name}' v{current_version} is incompatible with required v{required_version}"
    
    def check_ecosystem_compatibility(self, required_ecosystem_version: str) -> Tuple[bool, str]:
        """Check if ecosystem meets version requirements."""
        required = ToolVersion(required_ecosystem_version)
        if self.ecosystem_version.is_compatible_with(required):
            return True, f"Ecosystem v{self.ecosystem_version} is compatible"
        else:
            return False, f"Ecosystem v{self.ecosystem_version} is incompatible with required v{required_ecosystem_version}"
    
    def generate_version_report(self) -> Dict[str, any]:
        """Generate comprehensive version report."""
        report = {
            "ecosystem": {
                "version": str(self.ecosystem_version),
                "generated_at": datetime.now().isoformat()
            },
            "tools": {},
            "compatibility": {},
            "recommendations": []
        }
        
        # Tool versions
        for tool_name, version in self.tool_versions.items():
            report["tools"][tool_name] = {
                "version": str(version),
                "semantic_version_supported": version.semantic_version is not None
            }
        
        # Compatibility matrix (simplified)
        min_versions = {
            "sbom-agent": "2.0.0",
            "security-scanner-agent": "1.0.0", 
            "cicd-integration-agent": "1.0.0"
        }
        
        for tool_name, min_version in min_versions.items():
            compatible, message = self.check_tool_compatibility(tool_name, min_version)
            report["compatibility"][tool_name] = {
                "compatible": compatible,
                "message": message,
                "minimum_required": min_version
            }
            
            if not compatible:
                report["recommendations"].append(f"Update {tool_name} to v{min_version} or later")
        
        return report
    
    def update_tool_version(self, tool_name: str, new_version: str) -> bool:
        """Update version for a specific tool."""
        tool_path = self.tools_root / tool_name / "VERSION"
        
        try:
            # Validate version format
            ToolVersion(new_version)
            
            # Write new version
            tool_path.write_text(new_version)
            
            # Update internal tracking
            self.tool_versions[tool_name] = ToolVersion(new_version, tool_name)
            
            return True
        except Exception as e:
            print(f"Failed to update {tool_name} version: {e}")
            return False
    
    def update_ecosystem_version(self, new_version: str) -> bool:
        """Update the ecosystem version."""
        version_file = self.tools_root / "VERSION"
        
        try:
            # Validate version format
            ToolVersion(new_version)
            
            # Write new version
            version_file.write_text(new_version)
            
            # Update internal tracking
            self.ecosystem_version = ToolVersion(new_version, "ecosystem")
            
            return True
        except Exception as e:
            print(f"Failed to update ecosystem version: {e}")
            return False
    
    def get_update_recommendations(self) -> List[str]:
        """Get recommendations for version updates."""
        recommendations = []
        
        # Check for tools that might need updates
        current_versions = {
            "sbom-agent": "2.1.0",
            "security-scanner-agent": "1.5.0",
            "cicd-integration-agent": "1.2.0"
        }
        
        for tool_name, expected_version in current_versions.items():
            current = self.get_tool_version(tool_name)
            expected = ToolVersion(expected_version)
            
            if current and not current.is_compatible_with(expected):
                if current.is_newer_than(expected):
                    recommendations.append(f"✅ {tool_name} v{current} is ahead of expected v{expected_version}")
                else:
                    recommendations.append(f"⚠️ {tool_name} v{current} should be updated to v{expected_version}")
        
        return recommendations
    
    def export_versions(self, output_file: Path) -> None:
        """Export version information to a file."""
        report = self.generate_version_report()
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)


def main():
    """Command-line interface for version management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Tools Version Manager")
    parser.add_argument("--report", action="store_true", help="Generate version report")
    parser.add_argument("--check", help="Check compatibility for specific tool")
    parser.add_argument("--update", nargs=2, metavar=("TOOL", "VERSION"), help="Update tool version")
    parser.add_argument("--export", help="Export version info to file")
    
    args = parser.parse_args()
    
    version_manager = VersionManager()
    
    if args.report:
        report = version_manager.generate_version_report()
        print(json.dumps(report, indent=2))
        
    elif args.check:
        version = version_manager.get_tool_version(args.check)
        if version:
            print(f"{args.check}: v{version}")
        else:
            print(f"Tool '{args.check}' not found")
            
    elif args.update:
        tool, new_version = args.update
        if version_manager.update_tool_version(tool, new_version):
            print(f"✅ Updated {tool} to v{new_version}")
        else:
            print(f"❌ Failed to update {tool}")
            
    elif args.export:
        version_manager.export_versions(Path(args.export))
        print(f"✅ Version info exported to {args.export}")
        
    else:
        # Default: show current versions
        print("🔒 Security Tools Ecosystem Versions")
        print("=" * 40)
        print(f"Ecosystem: v{version_manager.get_ecosystem_version()}")
        
        for tool_name, version in version_manager.tool_versions.items():
            print(f"{tool_name}: v{version}")
            
        recommendations = version_manager.get_update_recommendations()
        if recommendations:
            print("\n📋 Recommendations:")
            for rec in recommendations:
                print(f"  {rec}")


if __name__ == "__main__":
    main()