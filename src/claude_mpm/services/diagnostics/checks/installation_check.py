"""
Check claude-mpm installation health.

WHY: Verify that claude-mpm is properly installed with correct Python version,
dependencies, and installation method.
"""

import subprocess
import sys
from pathlib import Path

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
                sub_results=sub_results if self.verbose else [],
            )

        except Exception as e:
            return DiagnosticResult(
                category=self.category,
                status=DiagnosticStatus.ERROR,
                message=f"Installation check failed: {e!s}",
                details={"error": str(e)},
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
                fix_description="Upgrade Python to 3.9 or higher",
            )
        if version_info < recommended_version:
            return DiagnosticResult(
                category="Python Version",
                status=DiagnosticStatus.WARNING,
                message=f"Python {version_info.major}.{version_info.minor} works but {recommended_version[0]}.{recommended_version[1]}+ is recommended",
                details={"version": version},
            )
        return DiagnosticResult(
            category="Python Version",
            status=DiagnosticStatus.OK,
            message=f"Python {version_info.major}.{version_info.minor}.{version_info.micro}",
            details={"version": version},
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
                    "display_version": version,
                },
            )
        except Exception as e:
            return DiagnosticResult(
                category="Claude MPM Version",
                status=DiagnosticStatus.WARNING,
                message="Could not determine version",
                details={"error": str(e)},
            )

    def _check_installation_method(self) -> DiagnosticResult:
        """Detect how claude-mpm was installed."""
        methods_found = []
        details = {}

        # 1. Check the actual execution context
        exe_path = sys.executable
        details["python_executable"] = exe_path

        # 2. Check if we're in a virtual environment
        in_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

        # 3. Check if running from pipx environment
        # Pipx creates venvs in specific locations
        is_pipx_venv = False
        if in_venv and (".local/pipx/venvs" in exe_path or "pipx/venvs" in exe_path):
            is_pipx_venv = True
            methods_found.append("pipx")
            details["pipx_venv"] = sys.prefix
        elif in_venv:
            # Regular virtual environment (not pipx)
            methods_found.append("venv")
            details["venv_path"] = sys.prefix

        # 4. Check if running from source (development mode)
        claude_mpm_path = Path(__file__).parent.parent.parent.parent.parent
        if (claude_mpm_path / "pyproject.toml").exists():
            if (claude_mpm_path / ".git").exists():
                methods_found.append("development")
                details["source_path"] = str(claude_mpm_path)

        # 5. Check Homebrew Python
        if not in_venv and "/opt/homebrew" in exe_path:
            methods_found.append("homebrew")
            details["homebrew_python"] = exe_path
        elif not in_venv and "/usr/local" in exe_path and sys.platform == "darwin":
            # Older homebrew location
            methods_found.append("homebrew")
            details["homebrew_python"] = exe_path

        # 6. Check for system Python
        if not in_venv and not methods_found:
            if "/usr/bin/python" in exe_path or "/usr/local/bin/python" in exe_path:
                methods_found.append("system")
                details["system_python"] = exe_path

        # 7. Additional check for pipx if not detected via venv
        if "pipx" not in methods_found:
            try:
                result = subprocess.run(
                    ["pipx", "list"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if "claude-mpm" in result.stdout:
                    if not is_pipx_venv:
                        # Pipx is installed but we're not running from it
                        details["pipx_installed"] = True
                        details["pipx_not_active"] = (
                            "claude-mpm is installed via pipx but not currently running from pipx environment"
                        )
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

        # 8. Check pip installation status
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "claude-mpm"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                # Parse installation location from pip show
                for line in result.stdout.split("\n"):
                    if line.startswith("Location:"):
                        location = line.split(":", 1)[1].strip()
                        details["pip_location"] = location

                        # Determine if it's editable install
                        if "Editable project location:" in result.stdout:
                            if "development" not in methods_found:
                                methods_found.append("development")
                            details["editable_install"] = True
                        elif not in_venv and not is_pipx_venv:
                            methods_found.append("pip")
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Build comprehensive details
        details["methods_detected"] = methods_found

        # Generate appropriate status and message based on what we found
        if not methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.WARNING,
                message="Installation method unknown",
                details=details,
            )

        # Pipx is the recommended method
        if "pipx" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.OK,
                message="Running from pipx environment (recommended)",
                details=details,
            )

        # Development in venv is also good
        if "venv" in methods_found and "development" in methods_found:
            venv_name = Path(sys.prefix).name
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.OK,
                message=f"Development mode in virtual environment '{venv_name}'",
                details=details,
            )

        # Regular venv is fine
        if "venv" in methods_found:
            venv_name = Path(sys.prefix).name
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.OK,
                message=f"Virtual environment '{venv_name}'",
                details=details,
            )

        # Development with homebrew/system Python
        if "development" in methods_found and "homebrew" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.OK,
                message="Development mode with Homebrew Python",
                details=details,
            )

        if "development" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.OK,
                message="Development mode",
                details=details,
            )

        # Homebrew Python (not ideal but common)
        if "homebrew" in methods_found:
            msg = "Homebrew Python"
            if details.get("pipx_installed"):
                msg += " (pipx is installed but not active - consider using 'pipx run claude-mpm')"
                status = DiagnosticStatus.WARNING
            else:
                status = DiagnosticStatus.OK
            return DiagnosticResult(
                category="Installation Method",
                status=status,
                message=msg,
                details=details,
            )

        # System pip installation (not recommended)
        if "pip" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.WARNING,
                message="System pip installation (consider using pipx or venv instead)",
                details=details,
                fix_description="Consider reinstalling with pipx for isolated environment",
            )

        # System Python
        if "system" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=DiagnosticStatus.WARNING,
                message="System Python (consider using pipx or venv)",
                details=details,
            )

        # Fallback for any other combination
        return DiagnosticResult(
            category="Installation Method",
            status=DiagnosticStatus.OK,
            message=f"Installed via {', '.join(methods_found)}",
            details=details,
        )

    def _check_dependencies(self) -> DiagnosticResult:
        """Check critical dependencies."""
        missing = []
        warnings = []
        installed = []

        # Check if we're in a virtual environment
        in_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

        # Map package names to their import names
        critical_packages = {
            "aiohttp": "aiohttp",
            "click": "click",
            "pyyaml": "yaml",  # pyyaml is imported as yaml
            "python-socketio": "socketio",  # python-socketio is imported as socketio
            "aiofiles": "aiofiles",
        }

        for package, import_name in critical_packages.items():
            try:
                __import__(import_name)
                installed.append(package)
            except ImportError:
                missing.append(package)

        # Check optional but recommended packages
        optional_packages = ["rich", "tabulate"]
        for package in optional_packages:
            try:
                __import__(package)
                installed.append(f"{package} (optional)")
            except ImportError:
                warnings.append(package)

        # Provide context-aware fix instructions
        if missing:
            if in_venv:
                fix_cmd = f"{sys.executable} -m pip install -e ."
                fix_desc = f"Install dependencies in virtual environment: {sys.prefix}"
            else:
                fix_cmd = "pip install -e ."
                fix_desc = "Reinstall claude-mpm with dependencies (consider using a virtual environment)"

            return DiagnosticResult(
                category="Dependencies",
                status=DiagnosticStatus.ERROR,
                message=f"Missing critical dependencies: {', '.join(missing)}",
                details={
                    "missing": missing,
                    "optional_missing": warnings,
                    "installed": installed,
                    "python_executable": sys.executable,
                    "in_venv": in_venv,
                },
                fix_command=fix_cmd,
                fix_description=fix_desc,
            )
        if warnings:
            return DiagnosticResult(
                category="Dependencies",
                status=DiagnosticStatus.WARNING,
                message=f"Missing optional dependencies: {', '.join(warnings)}",
                details={
                    "optional_missing": warnings,
                    "status": "partial",
                    "installed": installed,
                    "python_executable": sys.executable,
                    "in_venv": in_venv,
                },
            )
        return DiagnosticResult(
            category="Dependencies",
            status=DiagnosticStatus.OK,
            message="All dependencies installed",
            details={
                "status": "complete",
                "installed": installed,
                "python_executable": sys.executable,
                "in_venv": in_venv,
            },
        )
