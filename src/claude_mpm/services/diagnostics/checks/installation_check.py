"""
Check claude-mpm installation health.

WHY: Verify that claude-mpm is properly installed with correct Python version,
dependencies, and installation method.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
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
            if any(r.status == ValidationSeverity.ERROR for r in sub_results):
                status = ValidationSeverity.ERROR
                message = "Installation has critical issues"
            elif any(r.status == ValidationSeverity.WARNING for r in sub_results):
                status = ValidationSeverity.WARNING
                message = "Installation has minor issues"
            else:
                status = OperationResult.SUCCESS
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
                status=ValidationSeverity.ERROR,
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
                status=ValidationSeverity.ERROR,
                message=f"Python {version_info.major}.{version_info.minor} is below minimum required {min_version[0]}.{min_version[1]}",
                details={"version": version},
                fix_description="Upgrade Python to 3.9 or higher",
            )
        if version_info < recommended_version:
            return DiagnosticResult(
                category="Python Version",
                status=ValidationSeverity.WARNING,
                message=f"Python {version_info.major}.{version_info.minor} works but {recommended_version[0]}.{recommended_version[1]}+ is recommended",
                details={"version": version},
            )
        return DiagnosticResult(
            category="Python Version",
            status=OperationResult.SUCCESS,
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
                status=OperationResult.SUCCESS,
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
                status=ValidationSeverity.WARNING,
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

        # 2. Check for container environment
        container_type = self._detect_container_environment()
        if container_type:
            details["container_type"] = container_type
            methods_found.append("container")

        # 3. Check if we're in a virtual environment
        in_venv = hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

        # 4. Check if running from pipx environment
        # Pipx creates venvs in specific locations
        is_pipx_venv = False
        if in_venv and (".local/pipx/venvs" in exe_path or "pipx/venvs" in exe_path):
            is_pipx_venv = True
            methods_found.append("pipx")
            details["pipx_venv"] = sys.prefix
            # Get pipx metadata if available
            pipx_metadata = self._get_pipx_metadata()
            if pipx_metadata:
                details["pipx_metadata"] = pipx_metadata
        elif in_venv:
            # Regular virtual environment (not pipx)
            methods_found.append("venv")
            details["venv_path"] = sys.prefix

        # 5. Check if running from source (development mode)
        claude_mpm_path = Path(__file__).parent.parent.parent.parent.parent
        if (claude_mpm_path / "pyproject.toml").exists() and (
            claude_mpm_path / ".git"
        ).exists():
            methods_found.append("development")
            details["source_path"] = str(claude_mpm_path)

        # 6. Check Homebrew Python
        if not in_venv and "/opt/homebrew" in exe_path:
            methods_found.append("homebrew")
            details["homebrew_python"] = exe_path
        elif not in_venv and "/usr/local" in exe_path and sys.platform == "darwin":
            # Older homebrew location
            methods_found.append("homebrew")
            details["homebrew_python"] = exe_path

        # 7. Check for system Python
        if (
            not in_venv
            and not methods_found
            and ("/usr/bin/python" in exe_path or "/usr/local/bin/python" in exe_path)
        ):
            methods_found.append("system")
            details["system_python"] = exe_path

        # 8. Additional check for pipx if not detected via venv
        if "pipx" not in methods_found:
            pipx_check = self._check_pipx_installation_status()
            if pipx_check and not is_pipx_venv:
                # Pipx is installed but we're not running from it
                details["pipx_installed"] = True
                details["pipx_not_active"] = (
                    "claude-mpm is installed via pipx but not currently running from pipx environment"
                )

        # 9. Check pip installation status
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
                status=ValidationSeverity.WARNING,
                message="Installation method unknown",
                details=details,
            )

        # Container environments are special
        if "container" in methods_found:
            container_msg = (
                f"Running in {details.get('container_type', 'container')} environment"
            )
            if "pipx" in methods_found:
                container_msg += " with pipx"
            elif "venv" in methods_found:
                container_msg += " with virtual environment"
            return DiagnosticResult(
                category="Installation Method",
                status=OperationResult.SUCCESS,
                message=container_msg,
                details=details,
            )

        # Pipx is the recommended method
        if "pipx" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=OperationResult.SUCCESS,
                message="Running from pipx environment (recommended)",
                details=details,
            )

        # Development in venv is also good
        if "venv" in methods_found and "development" in methods_found:
            venv_name = Path(sys.prefix).name
            return DiagnosticResult(
                category="Installation Method",
                status=OperationResult.SUCCESS,
                message=f"Development mode in virtual environment '{venv_name}'",
                details=details,
            )

        # Regular venv is fine
        if "venv" in methods_found:
            venv_name = Path(sys.prefix).name
            return DiagnosticResult(
                category="Installation Method",
                status=OperationResult.SUCCESS,
                message=f"Virtual environment '{venv_name}'",
                details=details,
            )

        # Development with homebrew/system Python
        if "development" in methods_found and "homebrew" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=OperationResult.SUCCESS,
                message="Development mode with Homebrew Python",
                details=details,
            )

        if "development" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=OperationResult.SUCCESS,
                message="Development mode",
                details=details,
            )

        # Homebrew Python (not ideal but common)
        if "homebrew" in methods_found:
            msg = "Homebrew Python"
            if details.get("pipx_installed"):
                msg += " (pipx is installed but not active - consider using 'pipx run claude-mpm')"
                status = ValidationSeverity.WARNING
            else:
                status = OperationResult.SUCCESS
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
                status=ValidationSeverity.WARNING,
                message="System pip installation (consider using pipx or venv instead)",
                details=details,
                fix_description="Consider reinstalling with pipx for isolated environment",
            )

        # System Python
        if "system" in methods_found:
            return DiagnosticResult(
                category="Installation Method",
                status=ValidationSeverity.WARNING,
                message="System Python (consider using pipx or venv)",
                details=details,
            )

        # Fallback for any other combination
        return DiagnosticResult(
            category="Installation Method",
            status=OperationResult.SUCCESS,
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
                status=ValidationSeverity.ERROR,
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
                status=ValidationSeverity.WARNING,
                message=f"Missing optional dependencies: {', '.join(warnings)}",
                details={
                    "optional_missing": warnings,
                    "status": OperationResult.PARTIAL,
                    "installed": installed,
                    "python_executable": sys.executable,
                    "in_venv": in_venv,
                },
            )
        return DiagnosticResult(
            category="Dependencies",
            status=OperationResult.SUCCESS,
            message="All dependencies installed",
            details={
                "status": OperationResult.COMPLETED,
                "installed": installed,
                "python_executable": sys.executable,
                "in_venv": in_venv,
            },
        )

    def _detect_container_environment(self) -> Optional[str]:
        """Detect if running in a container environment."""
        # Check for Docker
        if Path("/.dockerenv").exists():
            return "Docker"

        # Check for Kubernetes
        if Path("/var/run/secrets/kubernetes.io").exists():
            return "Kubernetes"

        # Check cgroup for container indicators
        try:
            with Path("/proc/1/cgroup").open() as f:
                cgroup = f.read()
                if "docker" in cgroup:
                    return "Docker"
                if "kubepods" in cgroup:
                    return "Kubernetes"
                if "containerd" in cgroup:
                    return "containerd"
                if "lxc" in cgroup:
                    return "LXC"
        except (FileNotFoundError, PermissionError):
            pass

        # Check environment variables
        if os.environ.get("CONTAINER"):
            return os.environ.get("CONTAINER_ENGINE", "Container")

        # Check for Podman
        if Path("/run/.containerenv").exists():
            return "Podman"

        # Check for WSL
        if Path("/proc/sys/fs/binfmt_misc/WSLInterop").exists():
            return "WSL"

        return None

    def _get_pipx_metadata(self) -> Optional[dict]:
        """Get pipx metadata for the current installation."""
        try:
            import json

            result = subprocess.run(
                ["pipx", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                venvs = data.get("venvs", {})
                if "claude-mpm" in venvs:
                    return {
                        "version": venvs["claude-mpm"]
                        .get("metadata", {})
                        .get("main_package", {})
                        .get("package_version"),
                        "python": venvs["claude-mpm"]
                        .get("metadata", {})
                        .get("python_version"),
                    }
        except Exception:
            pass
        return None

    def _check_pipx_installation_status(self) -> bool:
        """Check if claude-mpm is installed via pipx."""
        try:
            result = subprocess.run(
                ["pipx", "list"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return "claude-mpm" in result.stdout
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
