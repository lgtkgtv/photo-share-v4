#!/usr/bin/env python3
"""
Security Tools Filename Manager
===============================

Provides standardized filename generation for all security tools outputs
including logs, reports, SBOMs, and analysis results with consistent
UTC timestamps and structured naming conventions.

Filename Format:
{TIMESTAMP}_{TARGET}_{SCANNER}_{TYPE}_{VERSION}.{EXTENSION}

Components:
- TIMESTAMP: YYYYMMDD_HHMMSS in UTC (e.g., 20250817_120530)
- TARGET: Scanned system/app identifier (e.g., WebServer_Production, PhotoShare_Backend)
- SCANNER: Tool name (e.g., SBOMAgent, VulnScanner, SecurityAuditor)
- TYPE: Output type (e.g., Report, Log, SBOM, Analysis)
- VERSION: Iteration/version number (e.g., v001, iteration001)
- EXTENSION: File format (e.g., json, html, pdf, log)

Examples:
- 20250817_120530_PhotoShare_SBOMAgent_Report_v001.html
- 20250817_120530_WebServer_VulnScanner_Log_iteration001.json
- 20250817_120530_ERP_App_SecurityAuditor_SBOM_v001.spdx
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class OutputType(Enum):
    """Standard output types for security tools."""
    REPORT = "Report"
    LOG = "Log"
    SBOM = "SBOM"
    ANALYSIS = "Analysis"
    VULNERABILITY_SCAN = "VulnScan"
    REMEDIATION = "Remediation"
    PROGRESSIVE = "Progressive"
    SUMMARY = "Summary"
    BACKUP = "Backup"
    CONFIG = "Config"
    METADATA = "Metadata"


class ScannerType(Enum):
    """Standard scanner/tool identifiers."""
    SBOM_AGENT = "SBOMAgent"
    VULN_SCANNER = "VulnScanner"
    SECURITY_AUDITOR = "SecurityAuditor"
    COMPLIANCE_CHECKER = "ComplianceChecker"
    REMEDIATION_ENGINE = "RemediationEngine"
    MONITORING_AGENT = "MonitoringAgent"
    CI_CD_SCANNER = "CICDScanner"


class FileFormat(Enum):
    """Standard file formats."""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    XML = "xml"
    CSV = "csv"
    TXT = "txt"
    LOG = "log"
    SPDX = "spdx"
    CYCLONEDX = "cyclonedx"
    SARIF = "sarif"
    MARKDOWN = "md"
    YAML = "yml"


@dataclass
class FilenameComponents:
    """Components for standardized filename generation."""
    timestamp: str
    target: str
    scanner: str
    output_type: str
    version: str
    extension: str
    
    def to_filename(self) -> str:
        """Generate standardized filename from components."""
        # Sanitize components
        safe_target = self._sanitize_component(self.target)
        safe_scanner = self._sanitize_component(self.scanner)
        safe_type = self._sanitize_component(self.output_type)
        safe_version = self._sanitize_component(self.version)
        
        return f"{self.timestamp}_{safe_target}_{safe_scanner}_{safe_type}_{safe_version}.{self.extension}"
    
    def _sanitize_component(self, component: str) -> str:
        """Sanitize filename component to remove invalid characters."""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\-.]', '_', component)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        return sanitized.strip('_')


class FilenameManager:
    """Manages standardized filename generation for security tools."""
    
    def __init__(self, target_system: str = None, default_scanner: str = None):
        """
        Initialize filename manager.
        
        Args:
            target_system: Default target system identifier
            default_scanner: Default scanner/tool identifier
        """
        self.target_system = target_system or "Unknown_System"
        self.default_scanner = default_scanner or "SecurityTool"
        self._version_counters = {}  # Track version numbers per target/scanner/type combo
    
    def generate_filename(self, 
                         output_type: OutputType,
                         file_format: FileFormat,
                         target: str = None,
                         scanner: ScannerType = None,
                         version: str = None,
                         custom_suffix: str = None) -> str:
        """
        Generate standardized filename.
        
        Args:
            output_type: Type of output (Report, Log, etc.)
            file_format: File format/extension
            target: Target system override
            scanner: Scanner type override
            version: Version string override
            custom_suffix: Additional suffix to append
            
        Returns:
            Standardized filename string
        """
        # Generate UTC timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Use provided values or defaults
        target_name = target or self.target_system
        scanner_name = scanner.value if scanner else self.default_scanner
        type_name = output_type.value
        
        # Generate version if not provided
        if version is None:
            version = self._get_next_version(target_name, scanner_name, type_name)
        
        # Add custom suffix if provided
        if custom_suffix:
            type_name = f"{type_name}_{custom_suffix}"
        
        # Create components
        components = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=scanner_name,
            output_type=type_name,
            version=version,
            extension=file_format.value
        )
        
        return components.to_filename()
    
    def generate_progressive_filenames(self,
                                     target: str = None,
                                     scanner: ScannerType = None,
                                     iteration: int = None) -> Dict[str, str]:
        """
        Generate related filenames for progressive analysis.
        
        Returns:
            Dictionary of filename types to filenames
        """
        target_name = target or self.target_system
        scanner_name = scanner or ScannerType.SBOM_AGENT
        
        # Use iteration number or auto-increment
        if iteration is None:
            iteration = self._get_next_iteration(target_name, scanner_name.value)
        
        iteration_str = f"iteration{iteration:03d}"
        
        # Generate related filenames with same timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        filenames = {}
        
        # Before analysis
        filenames['before_analysis'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=scanner_name.value,
            output_type="Analysis_Before",
            version=iteration_str,
            extension=FileFormat.JSON.value
        ).to_filename()
        
        # After analysis
        filenames['after_analysis'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=scanner_name.value,
            output_type="Analysis_After",
            version=iteration_str,
            extension=FileFormat.JSON.value
        ).to_filename()
        
        # Progressive report
        filenames['progressive_report'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=scanner_name.value,
            output_type="Progressive_Report",
            version=iteration_str,
            extension=FileFormat.HTML.value
        ).to_filename()
        
        # Remediation log
        filenames['remediation_log'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=scanner_name.value,
            output_type="Remediation_Log",
            version=iteration_str,
            extension=FileFormat.JSON.value
        ).to_filename()
        
        return filenames
    
    def generate_sbom_filenames(self,
                               target: str = None,
                               version: str = None) -> Dict[str, str]:
        """
        Generate standardized SBOM filenames for all formats.
        
        Returns:
            Dictionary of SBOM format names to filenames
        """
        target_name = target or self.target_system
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        if version is None:
            version = self._get_next_version(target_name, ScannerType.SBOM_AGENT.value, "SBOM")
        
        sbom_files = {}
        
        # Universal SBOM (JSON)
        sbom_files['universal'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=ScannerType.SBOM_AGENT.value,
            output_type="SBOM_Universal",
            version=version,
            extension=FileFormat.JSON.value
        ).to_filename()
        
        # SPDX format
        sbom_files['spdx'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=ScannerType.SBOM_AGENT.value,
            output_type="SBOM_SPDX",
            version=version,
            extension=FileFormat.SPDX.value
        ).to_filename()
        
        # CycloneDX format
        sbom_files['cyclonedx'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=ScannerType.SBOM_AGENT.value,
            output_type="SBOM_CycloneDX",
            version=version,
            extension=FileFormat.CYCLONEDX.value
        ).to_filename()
        
        return sbom_files
    
    def generate_vulnerability_filenames(self,
                                       target: str = None,
                                       scan_type: str = "Comprehensive") -> Dict[str, str]:
        """
        Generate vulnerability scan related filenames.
        
        Args:
            target: Target system name
            scan_type: Type of vulnerability scan
            
        Returns:
            Dictionary of vulnerability file types to filenames
        """
        target_name = target or self.target_system
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version = self._get_next_version(target_name, ScannerType.VULN_SCANNER.value, scan_type)
        
        vuln_files = {}
        
        # Main vulnerability report
        vuln_files['report'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=ScannerType.VULN_SCANNER.value,
            output_type=f"VulnScan_{scan_type}",
            version=version,
            extension=FileFormat.JSON.value
        ).to_filename()
        
        # SARIF format for CI/CD integration
        vuln_files['sarif'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=ScannerType.VULN_SCANNER.value,
            output_type=f"VulnScan_{scan_type}_SARIF",
            version=version,
            extension=FileFormat.SARIF.value
        ).to_filename()
        
        # HTML dashboard
        vuln_files['dashboard'] = FilenameComponents(
            timestamp=timestamp,
            target=target_name,
            scanner=ScannerType.VULN_SCANNER.value,
            output_type=f"VulnScan_{scan_type}_Dashboard",
            version=version,
            extension=FileFormat.HTML.value
        ).to_filename()
        
        return vuln_files
    
    def parse_filename(self, filename: str) -> Optional[Dict[str, str]]:
        """
        Parse standardized filename back into components.
        
        Args:
            filename: Standardized filename to parse
            
        Returns:
            Dictionary with parsed components or None if not standard format
        """
        # Remove extension
        name_part = Path(filename).stem
        extension = Path(filename).suffix.lstrip('.')
        
        # Pattern: TIMESTAMP_TARGET_SCANNER_TYPE_VERSION
        pattern = r'^(\d{8}_\d{6})_(.+?)_(.+?)_(.+?)_(.+?)$'
        match = re.match(pattern, name_part)
        
        if not match:
            return None
        
        return {
            'timestamp': match.group(1),
            'target': match.group(2),
            'scanner': match.group(3),
            'output_type': match.group(4),
            'version': match.group(5),
            'extension': extension,
            'full_filename': filename
        }
    
    def get_latest_file(self, directory: Path, 
                       target: str = None,
                       scanner: str = None,
                       output_type: str = None) -> Optional[Path]:
        """
        Find the latest file matching criteria in directory.
        
        Args:
            directory: Directory to search
            target: Target system filter
            scanner: Scanner type filter
            output_type: Output type filter
            
        Returns:
            Path to latest matching file or None
        """
        matching_files = []
        
        for file_path in directory.glob("*.{json,html,pdf,log,spdx,cyclonedx,sarif}"):
            parsed = self.parse_filename(file_path.name)
            if not parsed:
                continue
            
            # Apply filters
            if target and target not in parsed['target']:
                continue
            if scanner and scanner not in parsed['scanner']:
                continue
            if output_type and output_type not in parsed['output_type']:
                continue
            
            matching_files.append((parsed['timestamp'], file_path))
        
        if not matching_files:
            return None
        
        # Sort by timestamp and return latest
        matching_files.sort(key=lambda x: x[0], reverse=True)
        return matching_files[0][1]
    
    def _get_next_version(self, target: str, scanner: str, output_type: str) -> str:
        """Get next version number for target/scanner/type combination."""
        key = f"{target}_{scanner}_{output_type}"
        
        if key not in self._version_counters:
            self._version_counters[key] = 1
        else:
            self._version_counters[key] += 1
        
        return f"v{self._version_counters[key]:03d}"
    
    def _get_next_iteration(self, target: str, scanner: str) -> int:
        """Get next iteration number for progressive analysis."""
        key = f"{target}_{scanner}_iteration"
        
        if key not in self._version_counters:
            self._version_counters[key] = 1
        else:
            self._version_counters[key] += 1
        
        return self._version_counters[key]
    
    def create_output_directory(self, base_dir: Path, 
                               target: str = None,
                               scanner: str = None,
                               date_subdir: bool = True) -> Path:
        """
        Create organized output directory structure.
        
        Args:
            base_dir: Base output directory
            target: Target system name
            scanner: Scanner name
            date_subdir: Whether to create date-based subdirectory
            
        Returns:
            Path to created output directory
        """
        target_name = target or self.target_system
        scanner_name = scanner or self.default_scanner
        
        # Create directory structure: base_dir/target/scanner/[date]/
        output_dir = base_dir / target_name / scanner_name
        
        if date_subdir:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            output_dir = output_dir / date_str
        
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir


def main():
    """Test filename manager functionality."""
    # Test filename generation
    manager = FilenameManager(target_system="PhotoShare_Backend", default_scanner="SBOMAgent")
    
    print("🔧 Testing Filename Manager")
    print("=" * 50)
    
    # Test basic filename generation
    basic_filename = manager.generate_filename(
        output_type=OutputType.REPORT,
        file_format=FileFormat.HTML,
        scanner=ScannerType.SBOM_AGENT
    )
    print(f"Basic filename: {basic_filename}")
    
    # Test progressive analysis filenames
    progressive_files = manager.generate_progressive_filenames(
        target="WebServer_Production",
        scanner=ScannerType.VULN_SCANNER
    )
    print(f"\nProgressive analysis files:")
    for file_type, filename in progressive_files.items():
        print(f"  {file_type}: {filename}")
    
    # Test SBOM filenames
    sbom_files = manager.generate_sbom_filenames(target="ERP_Application")
    print(f"\nSBOM files:")
    for format_type, filename in sbom_files.items():
        print(f"  {format_type}: {filename}")
    
    # Test filename parsing
    parsed = manager.parse_filename(basic_filename)
    print(f"\nParsed filename components:")
    for key, value in parsed.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Filename manager testing completed")


if __name__ == "__main__":
    main()