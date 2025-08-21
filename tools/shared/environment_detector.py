#!/usr/bin/env python3
"""
Environment Detection and Validation System
============================================

Provides fail-safe environment detection and validation for security tools.
Ensures tools can run without polluting target application environments.

Key Features:
- Virtual environment detection
- System dependency validation  
- Isolation verification
- Helpful setup guidance
- Cross-platform compatibility
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import importlib.util


class EnvironmentDetector:
    """Comprehensive environment detection and validation system."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.platform = platform.system()
        self.python_version = sys.version_info
        self.working_dir = Path.cwd()
        self.validation_results = {}
        
    def check_complete_environment(self) -> Dict[str, Any]:
        """Run comprehensive environment validation."""
        if self.verbose:
            print("🔍 Running comprehensive environment validation...")
            
        results = {
            "python_environment": self.check_python_environment(),
            "system_dependencies": self.check_system_dependencies(),
            "isolation_status": self.check_isolation_safety(),
            "permissions": self.check_permissions(),
            "network_access": self.check_network_access(),
            "platform_compatibility": self.check_platform_compatibility()
        }
        
        # Overall status
        results["overall_status"] = self._determine_overall_status(results)
        results["recommendations"] = self._generate_recommendations(results)
        
        if self.verbose:
            self._print_validation_summary(results)
            
        return results
    
    def check_python_environment(self) -> Dict[str, Any]:
        """Detect and validate Python environment setup."""
        result = {
            "python_version": f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}",
            "python_executable": sys.executable,
            "virtual_environment": self._detect_virtual_environment(),
            "package_management": self._check_package_managers(),
            "required_packages": self._check_required_packages(),
            "isolation_score": 0,
            "recommendations": []
        }
        
        # Calculate isolation score
        if result["virtual_environment"]["detected"]:
            result["isolation_score"] += 40
        if result["package_management"]["pip_available"]:
            result["isolation_score"] += 20
        if self.python_version >= (3, 9):
            result["isolation_score"] += 20
        if result["virtual_environment"]["isolated"]:
            result["isolation_score"] += 20
            
        # Generate recommendations
        if result["isolation_score"] < 60:
            result["recommendations"].append("Consider using virtual environment for better isolation")
        if self.python_version < (3, 9):
            result["recommendations"].append("Python 3.9+ recommended for optimal compatibility")
            
        return result
    
    def _detect_virtual_environment(self) -> Dict[str, Any]:
        """Detect virtual environment configuration."""
        venv_info = {
            "detected": False,
            "type": None,
            "path": None,
            "isolated": False,
            "name": None
        }
        
        # Check for virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            venv_info["detected"] = True
            venv_info["path"] = sys.prefix
            venv_info["isolated"] = True
            
            # Determine virtual environment type
            if os.environ.get('VIRTUAL_ENV'):
                venv_info["type"] = "virtualenv"
                venv_info["name"] = os.path.basename(os.environ['VIRTUAL_ENV'])
            elif os.environ.get('CONDA_DEFAULT_ENV'):
                venv_info["type"] = "conda"
                venv_info["name"] = os.environ['CONDA_DEFAULT_ENV']
            else:
                venv_info["type"] = "unknown"
                
        # Check for Poetry
        if Path(self.working_dir / "pyproject.toml").exists():
            try:
                import toml
                with open(self.working_dir / "pyproject.toml") as f:
                    pyproject = toml.load(f)
                if "tool" in pyproject and "poetry" in pyproject["tool"]:
                    venv_info["type"] = "poetry"
            except ImportError:
                pass
                
        return venv_info
    
    def _check_package_managers(self) -> Dict[str, bool]:
        """Check availability of package managers."""
        managers = {
            "pip_available": self._command_available("pip"),
            "pip3_available": self._command_available("pip3"),
            "pipx_available": self._command_available("pipx"),
            "poetry_available": self._command_available("poetry"),
            "conda_available": self._command_available("conda")
        }
        return managers
    
    def _check_required_packages(self) -> Dict[str, Any]:
        """Check if required packages are available."""
        required_packages = [
            "requests", "pydantic", "click", "rich", "jinja2", "pyyaml"
        ]
        
        package_status = {}
        missing_packages = []
        
        for package in required_packages:
            try:
                spec = importlib.util.find_spec(package)
                if spec is not None:
                    # Try to get version
                    try:
                        module = importlib.import_module(package)
                        version = getattr(module, '__version__', 'unknown')
                    except:
                        version = 'available'
                    package_status[package] = {"available": True, "version": version}
                else:
                    package_status[package] = {"available": False, "version": None}
                    missing_packages.append(package)
            except ImportError:
                package_status[package] = {"available": False, "version": None}
                missing_packages.append(package)
        
        return {
            "packages": package_status,
            "missing": missing_packages,
            "all_available": len(missing_packages) == 0
        }
    
    def check_system_dependencies(self) -> Dict[str, Any]:
        """Check system-level dependencies."""
        dependencies = {
            "git": self._check_git(),
            "docker": self._check_docker(),
            "package_managers": self._check_system_package_managers(),
            "development_tools": self._check_development_tools()
        }
        
        dependencies["overall_score"] = self._calculate_dependency_score(dependencies)
        return dependencies
    
    def _check_git(self) -> Dict[str, Any]:
        """Check Git installation and configuration."""
        git_info = {
            "available": self._command_available("git"),
            "version": None,
            "configured": False,
            "user_name": None,
            "user_email": None
        }
        
        if git_info["available"]:
            try:
                # Get Git version
                result = subprocess.run(["git", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    git_info["version"] = result.stdout.strip()
                
                # Check Git configuration
                result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    git_info["user_name"] = result.stdout.strip()
                    git_info["configured"] = True
                
                result = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    git_info["user_email"] = result.stdout.strip()
                    
            except Exception as e:
                git_info["error"] = str(e)
                
        return git_info
    
    def _check_docker(self) -> Dict[str, Any]:
        """Check Docker installation and accessibility."""
        docker_info = {
            "available": self._command_available("docker"),
            "version": None,
            "daemon_running": False,
            "user_access": False,
            "compose_available": False
        }
        
        if docker_info["available"]:
            try:
                # Get Docker version
                result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    docker_info["version"] = result.stdout.strip()
                
                # Check if Docker daemon is running
                result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    docker_info["daemon_running"] = True
                    docker_info["user_access"] = True
                
                # Check Docker Compose
                for cmd in ["docker-compose", "docker compose"]:
                    if self._command_available(cmd.split()[0]):
                        try:
                            subprocess.run(cmd.split() + ["--version"], 
                                         capture_output=True, text=True, timeout=5)
                            docker_info["compose_available"] = True
                            break
                        except:
                            continue
                            
            except subprocess.TimeoutExpired:
                docker_info["daemon_running"] = False
            except Exception as e:
                docker_info["error"] = str(e)
                
        return docker_info
    
    def _check_system_package_managers(self) -> Dict[str, bool]:
        """Check availability of system package managers."""
        managers = {}
        
        if self.platform == "Linux":
            managers.update({
                "apt": self._command_available("apt"),
                "yum": self._command_available("yum"),
                "dnf": self._command_available("dnf"),
                "apk": self._command_available("apk"),
                "snap": self._command_available("snap")
            })
        elif self.platform == "Darwin":  # macOS
            managers.update({
                "brew": self._command_available("brew"),
                "port": self._command_available("port")
            })
        elif self.platform == "Windows":
            managers.update({
                "choco": self._command_available("choco"),
                "winget": self._command_available("winget")
            })
            
        return managers
    
    def _check_development_tools(self) -> Dict[str, Any]:
        """Check availability of development tools."""
        tools = {}
        
        # Language-specific tools
        for tool in ["npm", "node", "mvn", "gradle", "go", "cargo", "ruby", "gem"]:
            tools[tool] = {
                "available": self._command_available(tool),
                "version": self._get_tool_version(tool) if self._command_available(tool) else None
            }
            
        return tools
    
    def check_isolation_safety(self) -> Dict[str, Any]:
        """Verify tool isolation capabilities."""
        isolation = {
            "working_directory": str(self.working_dir),
            "temp_directory_writable": self._check_temp_access(),
            "home_directory_isolation": self._check_home_isolation(),
            "system_paths_protected": self._check_system_path_protection(),
            "environment_pollution_risk": self._assess_pollution_risk(),
            "isolation_score": 0
        }
        
        # Calculate isolation score
        if isolation["temp_directory_writable"]:
            isolation["isolation_score"] += 25
        if isolation["home_directory_isolation"]:
            isolation["isolation_score"] += 25
        if isolation["system_paths_protected"]:
            isolation["isolation_score"] += 25
        if not isolation["environment_pollution_risk"]:
            isolation["isolation_score"] += 25
            
        return isolation
    
    def _check_temp_access(self) -> bool:
        """Check if temporary directory is writable."""
        import tempfile
        try:
            with tempfile.TemporaryFile() as f:
                f.write(b"test")
            return True
        except:
            return False
    
    def _check_home_isolation(self) -> bool:
        """Check if home directory is properly isolated."""
        # This is a basic check - in a real environment, you'd want more sophisticated checks
        home_dir = Path.home()
        return not str(self.working_dir).startswith(str(home_dir / ".local"))
    
    def _check_system_path_protection(self) -> bool:
        """Check if system paths are protected from modification."""
        protected_paths = ["/usr", "/etc", "/bin", "/sbin", "/lib", "/lib64"]
        
        if self.platform == "Windows":
            protected_paths = ["C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"]
            
        # Check if any protected paths are writable (which would be concerning)
        for path_str in protected_paths:
            path = Path(path_str)
            if path.exists() and os.access(path, os.W_OK):
                return False
                
        return True
    
    def _assess_pollution_risk(self) -> bool:
        """Assess risk of environment pollution."""
        risk_factors = []
        
        # Check if running as root/admin
        if os.geteuid() == 0 if hasattr(os, 'geteuid') else False:
            risk_factors.append("running_as_root")
            
        # Check if in system Python
        if sys.prefix == sys.base_prefix and not hasattr(sys, 'real_prefix'):
            risk_factors.append("system_python")
            
        # Check if tools directory is in system path
        tools_dir = Path(__file__).parent.parent
        for path in sys.path:
            if str(tools_dir) in path:
                risk_factors.append("tools_in_syspath")
                break
                
        return len(risk_factors) > 0
    
    def check_permissions(self) -> Dict[str, Any]:
        """Check required permissions."""
        permissions = {
            "read_access": True,  # Assume true if we can run this
            "write_access": self._check_write_permissions(),
            "execute_access": self._check_execute_permissions(),
            "network_access": None  # Will be set by network check
        }
        return permissions
    
    def _check_write_permissions(self) -> bool:
        """Check write permissions for tool operations."""
        try:
            test_file = self.working_dir / ".tools_write_test"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except:
            return False
    
    def _check_execute_permissions(self) -> bool:
        """Check execute permissions for tool operations."""
        try:
            # Try to execute a simple command
            subprocess.run([sys.executable, "-c", "print('test')"], 
                         capture_output=True, timeout=5)
            return True
        except:
            return False
    
    def check_network_access(self) -> Dict[str, Any]:
        """Check network connectivity for vulnerability databases."""
        network = {
            "internet_available": False,
            "osv_database_accessible": False,
            "github_accessible": False,
            "pypi_accessible": False,
            "proxy_detected": False
        }
        
        # Check basic internet connectivity
        try:
            import urllib.request
            urllib.request.urlopen("https://8.8.8.8", timeout=5)
            network["internet_available"] = True
        except:
            pass
        
        if network["internet_available"]:
            # Check specific services
            test_urls = {
                "osv_database_accessible": "https://api.osv.dev/v1/query",
                "github_accessible": "https://api.github.com",
                "pypi_accessible": "https://pypi.org/simple/"
            }
            
            for key, url in test_urls.items():
                try:
                    urllib.request.urlopen(url, timeout=10)
                    network[key] = True
                except:
                    pass
        
        # Check for proxy configuration
        proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]
        for var in proxy_vars:
            if os.environ.get(var):
                network["proxy_detected"] = True
                break
                
        return network
    
    def check_platform_compatibility(self) -> Dict[str, Any]:
        """Check platform-specific compatibility."""
        compatibility = {
            "platform": self.platform,
            "architecture": platform.machine(),
            "python_implementation": platform.python_implementation(),
            "supported": True,
            "limitations": [],
            "recommendations": []
        }
        
        # Platform-specific checks
        if self.platform == "Windows":
            compatibility["limitations"].append("Some Unix-specific tools may not work")
            compatibility["recommendations"].append("Consider using WSL for full compatibility")
        elif self.platform == "Darwin":
            if platform.machine() == "arm64":
                compatibility["recommendations"].append("Apple Silicon detected - ensure container compatibility")
        
        # Python implementation checks
        if compatibility["python_implementation"] != "CPython":
            compatibility["limitations"].append(f"Non-CPython implementation: {compatibility['python_implementation']}")
            
        return compatibility
    
    def _command_available(self, command: str) -> bool:
        """Check if a command is available in PATH."""
        return shutil.which(command) is not None
    
    def _get_tool_version(self, tool: str) -> Optional[str]:
        """Get version of a tool if available."""
        version_flags = ["--version", "-v", "-V", "version"]
        
        for flag in version_flags:
            try:
                result = subprocess.run([tool, flag], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip().split('\n')[0]
            except:
                continue
                
        return None
    
    def _calculate_dependency_score(self, dependencies: Dict[str, Any]) -> int:
        """Calculate overall dependency satisfaction score."""
        score = 0
        
        if dependencies["git"]["available"]:
            score += 25
        if dependencies["docker"]["available"]:
            score += 25
        if any(dependencies["package_managers"].values()):
            score += 25
        if len([t for t in dependencies["development_tools"].values() if t["available"]]) >= 2:
            score += 25
            
        return score
    
    def _determine_overall_status(self, results: Dict[str, Any]) -> str:
        """Determine overall environment status."""
        scores = []
        
        if "isolation_score" in results["python_environment"]:
            scores.append(results["python_environment"]["isolation_score"])
        if "overall_score" in results["system_dependencies"]:
            scores.append(results["system_dependencies"]["overall_score"])
        if "isolation_score" in results["isolation_status"]:
            scores.append(results["isolation_status"]["isolation_score"])
            
        if not scores:
            return "unknown"
            
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 80:
            return "excellent"
        elif avg_score >= 60:
            return "good"
        elif avg_score >= 40:
            return "acceptable"
        else:
            return "needs_improvement"
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Python environment recommendations
        if results["python_environment"]["isolation_score"] < 60:
            recommendations.append("🐍 Set up a virtual environment for better isolation")
            
        # System dependencies recommendations  
        if not results["system_dependencies"]["docker"]["available"]:
            recommendations.append("🐳 Install Docker for containerized tool execution")
            
        if not results["system_dependencies"]["git"]["available"]:
            recommendations.append("📦 Install Git for repository analysis")
            
        # Network recommendations
        if not results["network_access"]["internet_available"]:
            recommendations.append("🌐 Ensure internet connectivity for vulnerability scanning")
            
        # Isolation recommendations
        if results["isolation_status"]["environment_pollution_risk"]:
            recommendations.append("🔒 Use containerized execution to prevent environment pollution")
            
        return recommendations
    
    def _print_validation_summary(self, results: Dict[str, Any]) -> None:
        """Print a comprehensive validation summary."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        # Overall status
        status = results["overall_status"]
        status_colors = {
            "excellent": "green",
            "good": "yellow", 
            "acceptable": "orange",
            "needs_improvement": "red"
        }
        
        console.print(f"\n🔍 Environment Validation Complete")
        console.print(f"Overall Status: [{status_colors.get(status, 'white')}]{status.upper()}[/{status_colors.get(status, 'white')}]\n")
        
        # Create summary table
        table = Table(title="Environment Summary")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="green")
        
        # Python environment
        py_env = results["python_environment"]
        py_status = "✅ Ready" if py_env["isolation_score"] >= 60 else "⚠️ Needs attention"
        table.add_row("Python Environment", py_status, f"v{py_env['python_version']}, Score: {py_env['isolation_score']}")
        
        # System dependencies
        sys_deps = results["system_dependencies"]
        sys_status = "✅ Ready" if sys_deps["overall_score"] >= 60 else "⚠️ Missing tools"
        table.add_row("System Dependencies", sys_status, f"Score: {sys_deps['overall_score']}")
        
        # Isolation
        isolation = results["isolation_status"]
        iso_status = "✅ Safe" if isolation["isolation_score"] >= 60 else "⚠️ Risk detected"
        table.add_row("Isolation Safety", iso_status, f"Score: {isolation['isolation_score']}")
        
        # Network
        network = results["network_access"]
        net_status = "✅ Connected" if network["internet_available"] else "❌ Offline"
        table.add_row("Network Access", net_status, "Required for vulnerability scanning")
        
        console.print(table)
        
        # Recommendations
        if results["recommendations"]:
            console.print("\n📋 Recommendations:")
            for rec in results["recommendations"]:
                console.print(f"  • {rec}")
                
        console.print()


def main():
    """Main function for environment validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Tools Environment Validator")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    parser.add_argument("--output", "-o", help="Save results to file")
    
    args = parser.parse_args()
    
    detector = EnvironmentDetector(verbose=not args.quiet)
    results = detector.check_complete_environment()
    
    if args.json:
        output = json.dumps(results, indent=2, default=str)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
        else:
            print(output)
    elif args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"✅ Results saved to {args.output}")


if __name__ == "__main__":
    main()