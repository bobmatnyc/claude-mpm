"""
Check claude-mpm installation health.

WHY: Verify that claude-mpm is properly installed with correct Python version,
dependencies, and installation method.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from ..models import DiagnosticResult, DiagnosticStatus
from .base_check import BaseDiagnosticCheck


class InstallationCheck(BaseDiagnosticCheck):
    """Check claude-mpm installation and dependencies."""
    
    @property
    def name(self) -> str:
        return "installation_check"
    
    @property
    def category(self) -> str:
        return "Installation"
    
    def run(self) -> DiagnosticResult:
        """Run installation diagnostics."""
        try:
            details = {}
            sub_results = []
            
            # Check Python version
            python_result = self._check_python_version()
            sub_results.append(python_result)
            details["python_version"] = python_result.details.get("version")
            
            # Check claude-mpm version
            version_result = self._check_claude_mpm_version()
            sub_results.append(version_result)
            details["claude_mpm_version"] = version_result.details.get("version")
            details["build_number"] = version_result.details.get("build_number")
            
            # Check installation method
            method_result = self._check_installation_method()
            sub_results.append(method_result)
            details["installation_method"] = method_result.details.get("method")
            
            # Check critical dependencies
            deps_result = self._check_dependencies()
            sub_results.append(deps_result)
            details["dependencies"] = deps_result.details.get("status")
            
            # Determine overall status
            if any(r.status == DiagnosticStatus.ERROR for r in sub_results):
                status = DiagnosticStatus.ERROR
                message = "Installation has critical issues"
            elif any(r.status == DiagnosticStatus.WARNING for r in sub_results):
                status = DiagnosticStatus.WARNING
                message = "Installation has minor issues"
            else:
                status = DiagnosticStatus.OK
                message = "Installation is healthy"
            
            return DiagnosticResult(
                category=self.category,
                status=status,
                message=message,
                details=details,
                sub_results=sub_results if self.verbose else []
            )
            
        except Exception as e:
            return DiagnosticResult(
                category=self.category,
                status=DiagnosticStatus.ERROR,
                message=f"Installation check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    def _check_python_version(self) -> DiagnosticResult:
        """Check Python version compatibility."""
        version = sys.version
        version_info = sys.version_info
        
        min_version = (3, 9)
        recommended_version = (3, 11)
        
        if version_info < min_version:
            return DiagnosticResult(
                category="Python Version",
                status=DiagnosticStatus.ERROR,
                message=f"Python {version_info.major}.{version_info.minor} is below minimum required {min_version[0]}.{min_version[1]}",
                details={"version": version},
                fix_description="Upgrade Python to 3.9 or higher"
            )
        elif version_info < recommended_version:
            return DiagnosticResult(
                category="Python Version",
                status=DiagnosticStatus.WARNING,
                message=f"Python {version_info.major}.{version_info.minor} works but {recommended_version[0]}.{recommended_version[1]}+ is recommended",
                details={"version": version}
            )
        else:
            return DiagnosticResult(
                category="Python Version",
                status=DiagnosticStatus.OK,
                message=f"Python {version_info.major}.{version_info.minor}.{version_info.micro}",
                details={"version": version}
            )
    
    def _check_claude_mpm_version(self) -> DiagnosticResult:
        """Check claude-mpm version."""
        try:
            from ....services.version_service import VersionService
            
            service = VersionService()
            version = service.get_version()
            semantic_version = service.get_semantic_version()
            build_number = service.get_build_number()
            
            return DiagnosticResult(
                category="Claude MPM Version",
                status=DiagnosticStatus.OK,
                message=f"Version: {version}",
                details={
                    "version": semantic_version,
                    "build_number": build_number,
                    "display_version": version
                }
            )
        except Exception as e:
            return DiagnosticResult(
                category="Claude MPM Version",
                status=DiagnosticStatus.WARNING,
                message="Could not determine version",
                details={"error": str(e)}
            )
    
    def _check_installation_method(self) -> DiagnosticResult:
        """Detect how claude-mpm was installed."""
        methods_found = []
        
        # Check for pipx
        try:
            result = subprocess.run(
                ["pipx", "list"], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if "claude-mpm" in result.stdout:
                methods_found.append("pipx")
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Check for pip installation
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "claude-mpm"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                methods_found.append("pip")
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Check for development installation
        claude_mpm_path = Path(__file__).parent.parent.parent.parent.parent
        if (claude_mpm_path / "pyproject.toml").exists():
            if (claude_mpm_path / ".git").exists():
                methods_found.append("development")
        
        if not methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.WARNING,
                message="Installation method unknown",
                details={"method": "unknown"}
            )
        elif "pipx" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.OK,
                message="Installed via pipx (recommended)",
                details={"method": "pipx", "all_methods": methods_found}
            )
        elif "development" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.OK,
                message="Development installation",
                details={"method": "development", "all_methods": methods_found}
            )
        else:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.OK,
                message=f"Installed via {methods_found[0]}",
                details={"method": methods_found[0], "all_methods": methods_found}
            )
    
    def _check_dependencies(self) -> DiagnosticResult:
        """Check critical dependencies."""
        missing = []
        warnings = []
        
        critical_packages = [
            "aiohttp",
            "click", 
            "pyyaml",
            "python-socketio",
            "aiofiles"
        ]
        
        for package in critical_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)
        
        # Check optional but recommended packages
        optional_packages = ["rich", "tabulate"]
        for package in optional_packages:
            try:
                __import__(package)
            except ImportError:
                warnings.append(package)
        
        if missing:
            return DiagnosticResult(
                category="Dependencies",
                status=DiagnosticStatus.ERROR,
                message=f"Missing critical dependencies: {', '.join(missing)}",
                details={"missing": missing, "optional_missing": warnings},
                fix_command="pip install -e .",
                fix_description="Reinstall claude-mpm with dependencies"
            )
        elif warnings:
            return DiagnosticResult(
                category="Dependencies",
                status=DiagnosticStatus.WARNING,
                message=f"Missing optional dependencies: {', '.join(warnings)}",
                details={"optional_missing": warnings, "status": "partial"}
            )
        else:
            return DiagnosticResult(
                category="Dependencies",
                status=DiagnosticStatus.OK,
                message="All dependencies installed",
                details={"status": "complete"}
            )