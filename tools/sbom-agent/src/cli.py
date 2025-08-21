#!/usr/bin/env python3
"""
SBOM Agent CLI Interface
========================

Command-line interface for the SBOM Agent providing progressive analysis,
vulnerability scanning, automated remediation, and comprehensive reporting.

Features:
- Multi-format SBOM generation (SPDX, CycloneDX, Universal)
- Progressive analysis with before/after comparisons
- Automated vulnerability remediation
- Continuous monitoring capabilities
- Standards-compliant output formats
- Integration-ready APIs

Usage:
    python cli.py analyze /path/to/project
    python cli.py progressive-analysis /path/to/project --auto-remediate
    python cli.py remediate /path/to/project --auto-fix
    python cli.py monitor /path/to/project --schedule daily
"""

import os
import sys
import json
import argparse
import time
import signal
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

try:
    from universal_sbom_generator import UniversalSBOMGenerator, UniversalVulnerabilityScanner
    from state_manager import StateManager, AnalysisRun, RemediationAction
    from remediation_engine import RemediationEngine
    from report_generator import ReportGenerator
    from filename_manager import FilenameManager, OutputType, ScannerType, FileFormat
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required modules are in the same directory")
    sys.exit(1)


class SBOMAgentCLI:
    """Command-line interface for the SBOM Agent."""
    
    VERSION = "2.1.0"
    
    def __init__(self):
        self.state_manager = StateManager()
        self.filename_manager = FilenameManager(default_scanner=ScannerType.SBOM_AGENT.value)
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def analyze(self, args):
        """Perform SBOM analysis on a project."""
        project_path = Path(args.project_path).resolve()
        
        if not project_path.exists():
            print(f"❌ Project path does not exist: {project_path}")
            return 1
        
        print(f"🔍 Starting SBOM analysis for: {project_path}")
        print(f"📊 Analysis mode: {'with vulnerability scanning' if args.scan_vulnerabilities else 'SBOM generation only'}")
        
        try:
            # Initialize generator
            generator = UniversalSBOMGenerator(
                project_root=str(project_path),
                project_name=args.project_name or project_path.name,
                project_version=args.project_version
            )
            
            # Generate SBOM
            print("\n📦 Generating comprehensive SBOM...")
            sbom_data = generator.generate_universal_sbom()
            
            # Vulnerability scanning
            vulnerabilities = []
            if args.scan_vulnerabilities:
                print("\n🔍 Scanning for vulnerabilities...")
                scanner = UniversalVulnerabilityScanner()
                vulnerabilities = scanner.scan_components(
                    sbom_data["universal_sbom"]["ecosystems"]
                )
            
            # Calculate security score
            security_score = self._calculate_security_score(sbom_data, vulnerabilities)
            
            # Create analysis run
            analysis_run = self.state_manager.create_analysis_run(
                project_path=project_path,
                sbom_data=sbom_data,
                vulnerabilities=vulnerabilities,
                security_score=security_score,
                tool_version=self.VERSION,
                analysis_type="baseline" if args.baseline else "standard",
                metadata={
                    "scan_vulnerabilities": args.scan_vulnerabilities,
                    "output_formats": args.formats,
                    "cli_version": self.VERSION
                }
            )
            
            # Save analysis
            run_id = self.state_manager.save_analysis_run(analysis_run)
            
            # Generate outputs
            if args.output_dir:
                output_dir = Path(args.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                self._write_analysis_outputs(analysis_run, output_dir, args.formats)
            
            # Handle comparison
            comparison_data = None
            if args.compare_with:
                comparison_data = self._handle_comparison(run_id, args.compare_with)
            
            # Display results
            self._display_analysis_results(analysis_run, comparison_data, args.format)
            
            # Set exit code based on vulnerability thresholds
            if args.fail_on_critical and any(v.get("severity") == "critical" for v in vulnerabilities):
                print("❌ Critical vulnerabilities found - failing build")
                return 1
            
            if args.fail_on_high and len([v for v in vulnerabilities if v.get("severity") == "high"]) > args.fail_on_high:
                print(f"❌ Too many high-severity vulnerabilities found ({len([v for v in vulnerabilities if v.get('severity') == 'high'])}) - failing build")
                return 1
            
            print(f"\n✅ Analysis completed successfully (Run ID: {run_id})")
            return 0
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1
    
    def progressive_analysis(self, args):
        """Perform progressive analysis with remediation workflow."""
        project_path = Path(args.project_path).resolve()
        
        print(f"🔄 Starting progressive analysis for: {project_path}")
        print("This workflow includes: Analysis → Remediation → Re-analysis → Comparison")
        
        try:
            # Step 1: Initial analysis
            print("\n📊 Step 1: Initial security analysis...")
            initial_args = argparse.Namespace(
                project_path=str(project_path),
                scan_vulnerabilities=True,
                baseline=True,
                output_dir=args.output_dir,
                formats=['json', 'spdx', 'cyclonedx'],
                project_name=args.project_name,
                project_version=args.project_version,
                compare_with=None,
                format='text',
                fail_on_critical=False,
                fail_on_high=None,
                debug=args.debug
            )
            
            self.analyze(initial_args)
            initial_run = self.state_manager.get_latest_analysis(str(project_path))
            
            if not initial_run:
                print("❌ Failed to retrieve initial analysis")
                return 1
            
            print(f"📈 Initial security score: {initial_run.security_score:.1f}/100")
            print(f"🔍 Found {len(initial_run.vulnerabilities)} vulnerabilities")
            
            # Step 2: Remediation (if vulnerabilities found)
            if initial_run.vulnerabilities and args.auto_remediate:
                print("\n🔧 Step 2: Applying automated remediations...")
                remediation_args = argparse.Namespace(
                    project_path=str(project_path),
                    auto_fix=True,
                    plan_only=False,
                    backup=True,
                    test_after=True,
                    debug=args.debug
                )
                
                remediation_result = self.remediate(remediation_args)
                if remediation_result != 0:
                    print("⚠️ Remediation encountered issues, continuing with analysis...")
            
            # Step 3: Post-remediation analysis
            print("\n📊 Step 3: Post-remediation analysis...")
            post_args = argparse.Namespace(
                project_path=str(project_path),
                scan_vulnerabilities=True,
                baseline=False,
                output_dir=args.output_dir,
                formats=['json', 'spdx', 'cyclonedx'],
                project_name=args.project_name,
                project_version=args.project_version,
                compare_with=initial_run.run_id,
                format='text',
                fail_on_critical=False,
                fail_on_high=None,
                debug=args.debug
            )
            
            self.analyze(post_args)
            final_run = self.state_manager.get_latest_analysis(str(project_path))
            
            # Step 4: Generate comprehensive progress report
            print("\n📋 Step 4: Generating progress report...")
            if args.output_dir:
                self._generate_progressive_report(initial_run, final_run, Path(args.output_dir))
            
            # Display final summary
            self._display_progressive_summary(initial_run, final_run)
            
            return 0
            
        except Exception as e:
            print(f"❌ Progressive analysis failed: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1
    
    def remediate(self, args):
        """Apply automated remediations to security vulnerabilities."""
        project_path = Path(args.project_path).resolve()
        
        print(f"🔧 Starting remediation for: {project_path}")
        
        try:
            # Get latest analysis
            latest_analysis = self.state_manager.get_latest_analysis(str(project_path))
            if not latest_analysis:
                print("❌ No previous analysis found. Run 'analyze' first.")
                return 1
            
            if not latest_analysis.vulnerabilities:
                print("✅ No vulnerabilities found to remediate.")
                return 0
            
            # Initialize remediation engine
            remediation_engine = RemediationEngine(project_path)
            
            if args.plan_only:
                # Generate remediation plan only
                print("\n📋 Generating remediation plan...")
                plan = remediation_engine.generate_remediation_plan(latest_analysis.vulnerabilities)
                self._display_remediation_plan(plan)
                return 0
            
            # Apply remediations
            print(f"\n🔧 Applying {len(latest_analysis.vulnerabilities)} remediations...")
            if args.backup:
                print("💾 Creating backup before applying changes...")
            
            remediation_actions = []
            
            for vuln in latest_analysis.vulnerabilities:
                try:
                    action = remediation_engine.apply_remediation(
                        vulnerability=vuln,
                        auto_fix=args.auto_fix,
                        create_backup=args.backup
                    )
                    
                    if action:
                        # Save remediation action
                        remediation_action = self.state_manager.create_remediation_action(
                            run_id=latest_analysis.run_id,
                            action_type=action["type"],
                            description=action["description"],
                            target_package=action.get("package"),
                            from_version=action.get("from_version"),
                            to_version=action.get("to_version"),
                            vulnerability_ids=[vuln.get("vulnerability_id")],
                            success=action["success"],
                            metadata=action.get("metadata", {})
                        )
                        
                        self.state_manager.save_remediation_action(remediation_action)
                        remediation_actions.append(action)
                        
                        if action["success"]:
                            print(f"  ✅ {action['description']}")
                        else:
                            print(f"  ❌ {action['description']} - {action.get('error', 'Unknown error')}")
                
                except Exception as e:
                    print(f"  ❌ Failed to remediate {vuln.get('package', 'unknown')}: {e}")
            
            # Test after changes if requested
            if args.test_after and remediation_actions:
                print("\n🧪 Running tests after remediation...")
                test_result = remediation_engine.test_project()
                if not test_result:
                    print("⚠️ Tests failed after remediation - consider reverting changes")
            
            print(f"\n✅ Remediation completed: {len([a for a in remediation_actions if a.get('success')])} successful, {len([a for a in remediation_actions if not a.get('success')])} failed")
            return 0
            
        except Exception as e:
            print(f"❌ Remediation failed: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return 1
    
    def monitor(self, args):
        """Start continuous monitoring of project security."""
        project_path = Path(args.project_path).resolve()
        
        print(f"👁️ Starting continuous monitoring for: {project_path}")
        print(f"📅 Schedule: {args.schedule}")
        print("Press Ctrl+C to stop monitoring\n")
        
        # Calculate sleep interval
        interval_map = {
            'continuous': 300,  # 5 minutes
            'hourly': 3600,
            'daily': 86400,
            'weekly': 604800
        }
        
        sleep_interval = interval_map.get(args.schedule, 86400)
        
        try:
            iteration = 0
            while self.running:
                iteration += 1
                print(f"🔍 Monitor iteration #{iteration} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Run analysis
                monitor_args = argparse.Namespace(
                    project_path=str(project_path),
                    scan_vulnerabilities=True,
                    baseline=False,
                    output_dir=args.output_dir,
                    formats=['json'],
                    project_name=args.project_name,
                    project_version=args.project_version,
                    compare_with='latest',
                    format='text',
                    fail_on_critical=False,
                    fail_on_high=None,
                    debug=False
                )
                
                result = self.analyze(monitor_args)
                
                if result == 0:
                    print(f"✅ Monitoring scan completed successfully")
                else:
                    print(f"⚠️ Monitoring scan encountered issues")
                
                if args.schedule == 'continuous':
                    print(f"⏰ Next scan in {sleep_interval//60} minutes...")
                else:
                    print(f"⏰ Next scan in {sleep_interval//3600} hours...")
                
                # Sleep until next iteration
                for _ in range(sleep_interval):
                    if not self.running:
                        break
                    time.sleep(1)
            
            print("\n🛑 Monitoring stopped")
            return 0
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            return 0
        except Exception as e:
            print(f"❌ Monitoring failed: {e}")
            return 1
    
    def quick_scan(self, args):
        """Perform quick security scan for CI/CD integration."""
        project_path = Path(args.project_path).resolve()
        
        print(f"⚡ Quick security scan for: {project_path}")
        
        try:
            # Lightweight scan focused on known vulnerability patterns
            generator = UniversalSBOMGenerator(project_root=str(project_path))
            ecosystems = generator.detect_project_ecosystems()
            
            # Quick vulnerability check
            scanner = UniversalVulnerabilityScanner()
            critical_vulns = 0
            high_vulns = 0
            
            for ecosystem in ecosystems:
                if ecosystem in ['python', 'javascript', 'java']:  # Focus on high-risk ecosystems
                    components = generator._get_ecosystem_components(ecosystem)
                    vulns = scanner.scan_components({ecosystem: components})
                    
                    for vuln in vulns:
                        if vuln.get("severity") == "critical":
                            critical_vulns += 1
                        elif vuln.get("severity") == "high":
                            high_vulns += 1
            
            # Apply thresholds
            threshold_map = {
                'critical': 0,
                'high': 0,
                'medium': 5,
                'low': 10
            }
            
            threshold = threshold_map.get(args.threshold, 0)
            
            if critical_vulns > 0:
                print(f"❌ {critical_vulns} critical vulnerabilities found")
                return 1
            elif args.threshold in ['high', 'medium', 'low'] and high_vulns > threshold:
                print(f"❌ {high_vulns} high-severity vulnerabilities found (threshold: {threshold})")
                return 1
            else:
                print(f"✅ Quick scan passed ({critical_vulns} critical, {high_vulns} high)")
                return 0
                
        except Exception as e:
            print(f"❌ Quick scan failed: {e}")
            return 1
    
    def _calculate_security_score(self, sbom_data: Dict[str, Any], vulnerabilities: List[Dict[str, Any]]) -> float:
        """Calculate security score based on vulnerabilities and other factors."""
        total_components = sbom_data["universal_sbom"]["summary"]["total_components"]
        
        if total_components == 0:
            return 100.0
        
        # Weight vulnerabilities by severity
        severity_weights = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1
        }
        
        vulnerability_score = sum(
            severity_weights.get(vuln.get("severity", "low"), 1)
            for vuln in vulnerabilities
        )
        
        # Calculate score (100 - penalty)
        penalty = min(vulnerability_score * 2, 100)  # Cap at 100
        return max(100 - penalty, 0)
    
    def _handle_comparison(self, current_run_id: str, compare_with: str) -> Optional[Dict[str, Any]]:
        """Handle comparison with previous analysis."""
        if compare_with == "latest":
            # Find the previous analysis (exclude current one)
            return None  # Simplified for now
        else:
            # Compare with specific run ID
            try:
                return self.state_manager.compare_analyses(compare_with, current_run_id)
            except Exception as e:
                print(f"⚠️ Comparison failed: {e}")
                return None
    
    def _display_analysis_results(self, analysis_run: AnalysisRun, comparison_data: Optional[Dict], format_type: str):
        """Display analysis results in specified format."""
        if format_type == 'json':
            result = {
                "run_id": analysis_run.run_id,
                "timestamp": analysis_run.timestamp.isoformat(),
                "security_score": analysis_run.security_score,
                "vulnerabilities": analysis_run.vulnerabilities,
                "summary": analysis_run.sbom_data["universal_sbom"]["summary"]
            }
            if comparison_data:
                result["comparison"] = comparison_data
            print(json.dumps(result, indent=2))
        else:
            # Text format
            print(f"\n📊 Analysis Results")
            print(f"{'='*50}")
            print(f"Security Score: {analysis_run.security_score:.1f}/100")
            print(f"Total Components: {analysis_run.sbom_data['universal_sbom']['summary']['total_components']}")
            print(f"Vulnerabilities Found: {len(analysis_run.vulnerabilities)}")
            
            if analysis_run.vulnerabilities:
                severity_counts = {}
                for vuln in analysis_run.vulnerabilities:
                    severity = vuln.get("severity", "unknown")
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                print("\n🚨 Vulnerability Breakdown:")
                for severity, count in sorted(severity_counts.items()):
                    print(f"  {severity.capitalize()}: {count}")
    
    def _display_progressive_summary(self, initial_run: AnalysisRun, final_run: AnalysisRun):
        """Display progressive analysis summary."""
        print(f"\n🎯 Progressive Analysis Summary")
        print(f"{'='*60}")
        
        score_improvement = final_run.security_score - initial_run.security_score
        vuln_reduction = len(initial_run.vulnerabilities) - len(final_run.vulnerabilities)
        
        print(f"📈 Security Score: {initial_run.security_score:.1f} → {final_run.security_score:.1f} ({score_improvement:+.1f})")
        print(f"🔍 Vulnerabilities: {len(initial_run.vulnerabilities)} → {len(final_run.vulnerabilities)} ({vuln_reduction:+d})")
        
        if score_improvement > 0:
            print("✅ Security posture improved!")
        elif score_improvement == 0:
            print("➡️ Security posture unchanged")
        else:
            print("⚠️ Security posture declined - review changes")
    
    def _write_analysis_outputs(self, analysis_run: AnalysisRun, output_dir: Path, formats: List[str]):
        """Write analysis outputs in specified formats using standardized filenames."""
        # Extract target name from project path
        target_name = Path(analysis_run.project_path).name
        
        # Update filename manager with target
        self.filename_manager.target_system = target_name
        
        if 'json' in formats:
            filename = self.filename_manager.generate_filename(
                output_type=OutputType.ANALYSIS,
                file_format=FileFormat.JSON,
                scanner=ScannerType.SBOM_AGENT
            )
            output_file = output_dir / filename
            
            with open(output_file, 'w') as f:
                json.dump({
                    "analysis_run": {
                        "run_id": analysis_run.run_id,
                        "timestamp": analysis_run.timestamp.isoformat(),
                        "security_score": analysis_run.security_score,
                        "tool_version": analysis_run.tool_version
                    },
                    "sbom_data": analysis_run.sbom_data,
                    "vulnerabilities": analysis_run.vulnerabilities
                }, f, indent=2)
            print(f"📄 JSON Analysis: {output_file}")
        
        if 'spdx' in formats:
            filename = self.filename_manager.generate_filename(
                output_type=OutputType.SBOM,
                file_format=FileFormat.SPDX,
                scanner=ScannerType.SBOM_AGENT,
                custom_suffix="SPDX"
            )
            output_file = output_dir / filename
            
            with open(output_file, 'w') as f:
                json.dump(analysis_run.sbom_data["spdx"], f, indent=2)
            print(f"📄 SPDX SBOM: {output_file}")
        
        if 'cyclonedx' in formats:
            filename = self.filename_manager.generate_filename(
                output_type=OutputType.SBOM,
                file_format=FileFormat.CYCLONEDX,
                scanner=ScannerType.SBOM_AGENT,
                custom_suffix="CycloneDX"
            )
            output_file = output_dir / filename
            
            with open(output_file, 'w') as f:
                json.dump(analysis_run.sbom_data["cyclonedx"], f, indent=2)
            print(f"📄 CycloneDX SBOM: {output_file}")
        
        if 'html' in formats:
            filename = self.filename_manager.generate_filename(
                output_type=OutputType.REPORT,
                file_format=FileFormat.HTML,
                scanner=ScannerType.SBOM_AGENT
            )
            output_file = output_dir / filename
            
            # Generate HTML report using report generator
            try:
                report_generator = ReportGenerator(output_dir)
                analysis_data = {
                    "project_name": target_name,
                    "timestamp": analysis_run.timestamp.isoformat(),
                    "security_score": analysis_run.security_score,
                    "vulnerabilities": analysis_run.vulnerabilities,
                    "sbom_data": analysis_run.sbom_data
                }
                html_file = report_generator.generate_html_report(analysis_data)
                print(f"📄 HTML Report: {html_file}")
            except Exception as e:
                print(f"⚠️ HTML report generation failed: {e}")
    
    def _generate_progressive_report(self, initial_run: AnalysisRun, final_run: AnalysisRun, output_dir: Path):
        """Generate comprehensive progressive analysis report using standardized filenames."""
        comparison = self.state_manager.compare_analyses(initial_run.run_id, final_run.run_id)
        
        # Extract target name
        target_name = Path(final_run.project_path).name
        self.filename_manager.target_system = target_name
        
        report_data = {
            "progressive_analysis_report": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "analysis_period": {
                    "start": initial_run.timestamp.isoformat(),
                    "end": final_run.timestamp.isoformat(),
                    "duration_seconds": (final_run.timestamp - initial_run.timestamp).total_seconds()
                },
                "security_improvement": comparison["security_score"],
                "vulnerability_changes": comparison["vulnerabilities"],
                "package_updates": comparison["packages"],
                "remediation_actions": [action.__dict__ for action in comparison["remediation_actions"]]
            }
        }
        
        # Generate standardized filename
        filename = self.filename_manager.generate_filename(
            output_type=OutputType.PROGRESSIVE,
            file_format=FileFormat.JSON,
            scanner=ScannerType.SBOM_AGENT,
            custom_suffix="Report"
        )
        report_file = output_dir / filename
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"📋 Progressive Report: {report_file}")
        
        # Also generate HTML version
        try:
            html_filename = self.filename_manager.generate_filename(
                output_type=OutputType.PROGRESSIVE,
                file_format=FileFormat.HTML,
                scanner=ScannerType.SBOM_AGENT,
                custom_suffix="Dashboard"
            )
            html_file = output_dir / html_filename
            
            report_generator = ReportGenerator(output_dir)
            before_data = {
                "project_name": target_name,
                "timestamp": initial_run.timestamp.isoformat(),
                "security_score": initial_run.security_score,
                "vulnerabilities": initial_run.vulnerabilities,
                "sbom_data": initial_run.sbom_data
            }
            after_data = {
                "project_name": target_name,
                "timestamp": final_run.timestamp.isoformat(),
                "security_score": final_run.security_score,
                "vulnerabilities": final_run.vulnerabilities,
                "sbom_data": final_run.sbom_data
            }
            
            html_report = report_generator.generate_progressive_report(before_data, after_data, comparison["remediation_actions"])
            print(f"📋 Progressive HTML Dashboard: {html_report}")
            
        except Exception as e:
            print(f"⚠️ Progressive HTML report generation failed: {e}")
    
    def _display_remediation_plan(self, plan: Dict[str, Any]):
        """Display remediation plan."""
        print(f"\n🔧 Remediation Plan")
        print(f"{'='*50}")
        print(f"Total Actions: {len(plan.get('actions', []))}")
        
        for i, action in enumerate(plan.get('actions', []), 1):
            print(f"\n{i}. {action['description']}")
            print(f"   Type: {action['type']}")
            print(f"   Priority: {action['priority']}")
            if action.get('package'):
                print(f"   Package: {action['package']}")


def create_parser():
    """Create argument parser for the SBOM Agent CLI."""
    parser = argparse.ArgumentParser(
        description="SBOM Agent - Multi-language Software Bill of Materials Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic SBOM analysis
  python cli.py analyze /path/to/project

  # Analysis with vulnerability scanning
  python cli.py analyze /path/to/project --scan-vulnerabilities

  # Progressive analysis with auto-remediation
  python cli.py progressive-analysis /path/to/project --auto-remediate

  # Quick CI/CD scan
  python cli.py quick-scan /path/to/project --threshold high

  # Continuous monitoring
  python cli.py monitor /path/to/project --schedule daily
        """
    )
    
    parser.add_argument('--version', action='version', version=f'SBOM Agent {SBOMAgentCLI.VERSION}')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze project and generate SBOM')
    analyze_parser.add_argument('project_path', help='Path to project root')
    analyze_parser.add_argument('--scan-vulnerabilities', action='store_true', help='Scan for vulnerabilities')
    analyze_parser.add_argument('--baseline', action='store_true', help='Mark as baseline analysis')
    analyze_parser.add_argument('--output-dir', '-o', help='Output directory for reports')
    analyze_parser.add_argument('--formats', nargs='+', default=['json'], 
                               choices=['json', 'spdx', 'cyclonedx', 'html'],
                               help='Output formats')
    analyze_parser.add_argument('--project-name', help='Project name override')
    analyze_parser.add_argument('--project-version', default='1.0.0', help='Project version')
    analyze_parser.add_argument('--compare-with', help='Compare with previous analysis (run ID or "latest")')
    analyze_parser.add_argument('--format', default='text', choices=['text', 'json'], help='Display format')
    analyze_parser.add_argument('--fail-on-critical', action='store_true', help='Fail if critical vulnerabilities found')
    analyze_parser.add_argument('--fail-on-high', type=int, help='Fail if high vulnerabilities exceed threshold')
    
    # Progressive analysis command
    progressive_parser = subparsers.add_parser('progressive-analysis', help='Run progressive analysis workflow')
    progressive_parser.add_argument('project_path', help='Path to project root')
    progressive_parser.add_argument('--auto-remediate', action='store_true', help='Apply automatic remediations')
    progressive_parser.add_argument('--output-dir', '-o', help='Output directory for reports')
    progressive_parser.add_argument('--project-name', help='Project name override')
    progressive_parser.add_argument('--project-version', default='1.0.0', help='Project version')
    
    # Remediate command
    remediate_parser = subparsers.add_parser('remediate', help='Apply security remediations')
    remediate_parser.add_argument('project_path', help='Path to project root')
    remediate_parser.add_argument('--auto-fix', action='store_true', help='Apply fixes automatically')
    remediate_parser.add_argument('--plan-only', action='store_true', help='Generate plan only, do not apply')
    remediate_parser.add_argument('--backup', action='store_true', default=True, help='Create backup before changes')
    remediate_parser.add_argument('--test-after', action='store_true', help='Run tests after remediation')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Continuous security monitoring')
    monitor_parser.add_argument('project_path', help='Path to project root')
    monitor_parser.add_argument('--schedule', default='daily', 
                               choices=['continuous', 'hourly', 'daily', 'weekly'],
                               help='Monitoring schedule')
    monitor_parser.add_argument('--output-dir', '-o', help='Output directory for reports')
    monitor_parser.add_argument('--project-name', help='Project name override')
    monitor_parser.add_argument('--project-version', default='1.0.0', help='Project version')
    
    # Quick scan command
    quick_parser = subparsers.add_parser('quick-scan', help='Quick security scan for CI/CD')
    quick_parser.add_argument('project_path', help='Path to project root')
    quick_parser.add_argument('--threshold', default='high', 
                             choices=['critical', 'high', 'medium', 'low'],
                             help='Severity threshold for failing')
    quick_parser.add_argument('--staged-files', action='store_true', help='Scan only staged Git files')
    
    return parser


def main():
    """Main entry point for the SBOM Agent CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = SBOMAgentCLI()
    
    try:
        if args.command == 'analyze':
            return cli.analyze(args)
        elif args.command == 'progressive-analysis':
            return cli.progressive_analysis(args)
        elif args.command == 'remediate':
            return cli.remediate(args)
        elif args.command == 'monitor':
            return cli.monitor(args)
        elif args.command == 'quick-scan':
            return cli.quick_scan(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())