"""
MCP Service Verifier
====================

Comprehensive verification system for MCP services that checks installation,
configuration, and runtime functionality. Provides detailed diagnostics and
automated fixes for common issues.
"""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.logger import get_logger


class ServiceStatus(Enum):
    """MCP service health status levels."""

    WORKING = "✅"  # Fully operational
    MISCONFIGURED = "⚠️"  # Installed but configuration issues
    NOT_INSTALLED = "❌"  # Not installed at all
    PERMISSION_DENIED = "🔒"  # Permissions issue
    VERSION_MISMATCH = "🔄"  # Needs upgrade
    UNKNOWN = "❓"  # Unknown status


@dataclass
class ServiceDiagnostic:
    """Detailed diagnostic information for a service."""

    name: str
    status: ServiceStatus
    message: str
    installed_path: Optional[str] = None
    configured_command: Optional[str] = None
    fix_command: Optional[str] = None
    details: Optional[Dict] = None


class MCPServiceVerifier:
    """
    Comprehensive MCP service verification and auto-fix system.

    This verifier performs deep health checks on MCP services including:
    - Installation verification (pipx, uvx, system)
    - Configuration validation in ~/.claude.json
    - Permission checks on executables
    - Command format verification
    - Runtime functionality testing
    - Auto-fix capabilities for common issues
    """

    # Known MCP services and their requirements
    SERVICE_REQUIREMENTS = {
        "mcp-vector-search": {
            "pipx_package": "mcp-vector-search",
            "test_args": ["--version"],
            "required_args": ["-m", "mcp_vector_search.mcp.server"],
            "needs_project_path": True,
        },
        "mcp-browser": {
            "pipx_package": "mcp-browser",
            "test_args": ["--version"],
            "required_args": ["mcp"],
            "env_vars": {"MCP_BROWSER_HOME": "~/.mcp-browser"},
        },
        "mcp-ticketer": {
            "pipx_package": "mcp-ticketer",
            "test_args": ["--version"],
            "required_args": ["mcp"],
        },
        "kuzu-memory": {
            "pipx_package": "kuzu-memory",
            "test_args": ["--help"],  # kuzu-memory uses --help not --version
            "required_args": ["mcp", "serve"],  # Modern format
            "min_version": "1.1.0",  # Minimum version for MCP support
            "version_check_pattern": [
                "mcp",
                "serve",
                "claude",
            ],  # Pattern to check in help
        },
    }

    def __init__(self):
        """Initialize the MCP service verifier."""
        self.logger = get_logger(__name__)
        self.project_root = Path.cwd()
        self.claude_config_path = Path.home() / ".claude.json"
        self.diagnostics: Dict[str, ServiceDiagnostic] = {}

    def verify_all_services(
        self, auto_fix: bool = False
    ) -> Dict[str, ServiceDiagnostic]:
        """
        Perform comprehensive verification of all MCP services.

        Args:
            auto_fix: Whether to attempt automatic fixes for issues

        Returns:
            Dictionary mapping service names to diagnostic results
        """
        self.logger.info("Starting MCP service verification...")

        for service_name in self.SERVICE_REQUIREMENTS:
            diagnostic = self._verify_service(service_name)
            self.diagnostics[service_name] = diagnostic

            # Attempt auto-fix if requested and fixable
            if (
                auto_fix
                and diagnostic.fix_command
                and diagnostic.status != ServiceStatus.WORKING
            ):
                self._attempt_auto_fix(service_name, diagnostic)
                # Re-verify after fix
                self.diagnostics[service_name] = self._verify_service(service_name)

        return self.diagnostics

    def _verify_service(self, service_name: str) -> ServiceDiagnostic:
        """
        Perform deep verification of a single MCP service.

        Args:
            service_name: Name of the service to verify

        Returns:
            Diagnostic result for the service
        """
        requirements = self.SERVICE_REQUIREMENTS[service_name]

        # Step 1: Check if service is installed
        installed_path = self._find_service_installation(service_name)

        if not installed_path:
            return ServiceDiagnostic(
                name=service_name,
                status=ServiceStatus.NOT_INSTALLED,
                message=f"{service_name} is not installed",
                fix_command=f"pipx install {requirements['pipx_package']}",
            )

        # Step 2: Check executable permissions
        if not self._check_permissions(installed_path):
            return ServiceDiagnostic(
                name=service_name,
                status=ServiceStatus.PERMISSION_DENIED,
                message=f"Permission denied for {service_name}",
                installed_path=installed_path,
                fix_command=f"chmod +x {installed_path}",
            )

        # Step 3: Test basic functionality
        if not self._test_service_functionality(service_name, installed_path):
            # Check if it's a version issue for kuzu-memory
            if service_name == "kuzu-memory":
                version_info = self._check_kuzu_version(installed_path)
                if not version_info["has_mcp_support"]:
                    return ServiceDiagnostic(
                        name=service_name,
                        status=ServiceStatus.VERSION_MISMATCH,
                        message="kuzu-memory needs upgrade to v1.1.0+ for MCP support",
                        installed_path=installed_path,
                        fix_command="pipx upgrade kuzu-memory",
                        details=version_info,
                    )

            return ServiceDiagnostic(
                name=service_name,
                status=ServiceStatus.MISCONFIGURED,
                message=f"{service_name} installed but not functioning",
                installed_path=installed_path,
                fix_command=f"pipx reinstall {requirements['pipx_package']}",
            )

        # Step 4: Verify configuration in ~/.claude.json
        config_status = self._verify_configuration(service_name, installed_path)

        if not config_status["configured"]:
            return ServiceDiagnostic(
                name=service_name,
                status=ServiceStatus.MISCONFIGURED,
                message=f"{service_name} not configured in ~/.claude.json",
                installed_path=installed_path,
                configured_command=None,
                fix_command="Run 'claude-mpm configure' to update configuration",
            )

        if not config_status["correct"]:
            return ServiceDiagnostic(
                name=service_name,
                status=ServiceStatus.MISCONFIGURED,
                message=f"{service_name} configuration needs update",
                installed_path=installed_path,
                configured_command=config_status.get("command"),
                fix_command="Run 'claude-mpm configure' to fix configuration",
                details={"config_issue": config_status.get("issue")},
            )

        # Step 5: Test actual MCP command execution
        if not self._test_mcp_command(
            service_name, config_status.get("command"), config_status.get("args", [])
        ):
            return ServiceDiagnostic(
                name=service_name,
                status=ServiceStatus.MISCONFIGURED,
                message=f"{service_name} command format issue",
                installed_path=installed_path,
                configured_command=config_status.get("command"),
                fix_command="Run 'claude-mpm configure' to update command format",
                details={
                    "command": config_status.get("command"),
                    "args": config_status.get("args"),
                },
            )

        # All checks passed!
        return ServiceDiagnostic(
            name=service_name,
            status=ServiceStatus.WORKING,
            message=f"{service_name} is fully operational",
            installed_path=installed_path,
            configured_command=config_status.get("command"),
        )

    def _find_service_installation(self, service_name: str) -> Optional[str]:
        """
        Find where a service is installed.

        Checks in order:
        1. pipx installation
        2. uvx installation
        3. System PATH
        4. User pip installation

        Args:
            service_name: Name of the service

        Returns:
            Path to the service executable or None
        """
        # Check pipx
        pipx_path = (
            Path.home()
            / ".local"
            / "pipx"
            / "venvs"
            / service_name
            / "bin"
            / service_name
        )
        if pipx_path.exists():
            return str(pipx_path)

        # Special case for mcp-vector-search (uses Python interpreter)
        if service_name == "mcp-vector-search":
            pipx_python = pipx_path.parent / "python"
            if pipx_python.exists():
                return str(pipx_python)

        # Check system PATH
        system_path = shutil.which(service_name)
        if system_path:
            return system_path

        # Check user pip installation
        user_bin = Path.home() / ".local" / "bin" / service_name
        if user_bin.exists():
            return str(user_bin)

        return None

    def _check_permissions(self, path: str) -> bool:
        """
        Check if a file has execute permissions.

        Args:
            path: Path to the executable

        Returns:
            True if executable, False otherwise
        """
        try:
            return os.access(path, os.X_OK)
        except Exception as e:
            self.logger.debug(f"Permission check failed for {path}: {e}")
            return False

    def _test_service_functionality(self, service_name: str, path: str) -> bool:
        """
        Test if a service can execute basic commands.

        Args:
            service_name: Name of the service
            path: Path to the executable

        Returns:
            True if service is functional, False otherwise
        """
        requirements = self.SERVICE_REQUIREMENTS[service_name]
        test_args = requirements.get("test_args", ["--help"])

        try:
            # First try direct execution
            result = subprocess.run(
                [path, *test_args],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            output = (result.stdout + result.stderr).lower()

            # Check for success indicators
            if result.returncode == 0:
                return True

            # Some tools return non-zero but still work
            if any(
                word in output
                for word in ["version", "usage", "help", service_name.lower()]
            ) and not any(
                error in output
                for error in ["error", "not found", "traceback", "no module"]
            ):
                return True

            # Try pipx run as fallback
            if shutil.which("pipx"):
                result = subprocess.run(
                    ["pipx", "run", service_name, *test_args],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                if result.returncode == 0 or "version" in result.stdout.lower():
                    return True

        except subprocess.TimeoutExpired:
            self.logger.warning(
                f"Service {service_name} timed out during functionality test"
            )
        except Exception as e:
            self.logger.debug(f"Functionality test failed for {service_name}: {e}")

        return False

    def _check_kuzu_version(self, path: str) -> Dict:
        """
        Check kuzu-memory version and MCP support.

        Args:
            path: Path to kuzu-memory executable

        Returns:
            Dictionary with version information
        """
        version_info = {
            "has_mcp_support": False,
            "version": "unknown",
            "command_format": None,
        }

        try:
            # Check help output for MCP support
            result = subprocess.run(
                [path, "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            help_text = (result.stdout + result.stderr).lower()

            # Check for modern "mcp serve" command
            if "mcp serve" in help_text or (
                "mcp" in help_text and "serve" in help_text
            ):
                version_info["has_mcp_support"] = True
                version_info["command_format"] = "mcp serve"
            # Check for legacy "serve" only
            elif "serve" in help_text and "mcp" not in help_text:
                version_info["has_mcp_support"] = False
                version_info["command_format"] = "serve"

            # Try to extract version
            version_result = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if version_result.returncode == 0:
                version_info["version"] = version_result.stdout.strip()

        except Exception as e:
            self.logger.debug(f"Failed to check kuzu-memory version: {e}")

        return version_info

    def _verify_configuration(self, service_name: str, installed_path: str) -> Dict:
        """
        Verify service configuration in ~/.claude.json.

        Args:
            service_name: Name of the service
            installed_path: Path where service is installed

        Returns:
            Dictionary with configuration status
        """
        project_key = str(self.project_root)

        if not self.claude_config_path.exists():
            return {"configured": False, "correct": False}

        try:
            with self.claude_config_path.open() as f:
                config = json.load(f)

            # Check if project is configured
            if "projects" not in config or project_key not in config["projects"]:
                return {"configured": False, "correct": False}

            project_config = config["projects"][project_key]
            mcp_servers = project_config.get("mcpServers", {})

            # Check if service is configured
            if service_name not in mcp_servers:
                return {"configured": False, "correct": False}

            service_config = mcp_servers[service_name]
            command = service_config.get("command", "")
            args = service_config.get("args", [])

            # Validate command configuration
            requirements = self.SERVICE_REQUIREMENTS[service_name]
            required_args = requirements.get("required_args", [])

            # Check if using pipx run or direct execution
            if command == "pipx" and args and args[0] == "run":
                # pipx run format
                if service_name not in args:
                    return {
                        "configured": True,
                        "correct": False,
                        "command": command,
                        "args": args,
                        "issue": "Service name missing in pipx run command",
                    }
                # Check required args are present
                for req_arg in required_args:
                    if req_arg not in args[2:]:  # Skip "run" and service name
                        return {
                            "configured": True,
                            "correct": False,
                            "command": command,
                            "args": args,
                            "issue": f"Missing required argument: {req_arg}",
                        }
            elif command == "uvx" and args and args[0] == service_name:
                # uvx format - similar validation
                for req_arg in required_args:
                    if req_arg not in args[1:]:
                        return {
                            "configured": True,
                            "correct": False,
                            "command": command,
                            "args": args,
                            "issue": f"Missing required argument: {req_arg}",
                        }
            else:
                # Direct execution - command should be a valid path
                if (
                    not Path(command).exists()
                    and command != installed_path
                    and not shutil.which(command)
                ):
                    # Command path does not exist and cannot be found
                    return {
                        "configured": True,
                        "correct": False,
                        "command": command,
                        "args": args,
                        "issue": f"Command path does not exist: {command}",
                    }

                # Check required args
                for req_arg in required_args:
                    if req_arg not in args:
                        return {
                            "configured": True,
                            "correct": False,
                            "command": command,
                            "args": args,
                            "issue": f"Missing required argument: {req_arg}",
                        }

            # Special validation for kuzu-memory command format
            if service_name == "kuzu-memory":
                # Should use "mcp serve" format for modern versions
                if args and "serve" in args and "mcp" not in args:
                    return {
                        "configured": True,
                        "correct": False,
                        "command": command,
                        "args": args,
                        "issue": "Using legacy 'serve' format, should use 'mcp serve'",
                    }

            return {
                "configured": True,
                "correct": True,
                "command": command,
                "args": args,
            }

        except Exception as e:
            self.logger.error(f"Failed to verify configuration: {e}")
            return {"configured": False, "correct": False, "error": str(e)}

    def _test_mcp_command(
        self, service_name: str, command: str, args: List[str]
    ) -> bool:
        """
        Test if the configured MCP command actually works.

        Args:
            service_name: Name of the service
            command: Configured command
            args: Configured arguments

        Returns:
            True if command executes successfully
        """
        if not command:
            return False

        try:
            # Build test command - add --help to test without side effects
            test_cmd = [command, *args[:2]] if args else [command]  # Include base args
            test_cmd.append("--help")

            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                cwd=str(self.project_root),  # Run in project context
            )

            # Check for success or expected output
            output = (result.stdout + result.stderr).lower()
            if result.returncode == 0:
                return True

            # Check for expected patterns
            if service_name == "kuzu-memory" and "mcp" in output and "serve" in output:
                return True
            if service_name in output or "usage" in output or "help" in output:
                if not any(
                    error in output for error in ["error", "not found", "traceback"]
                ):
                    return True

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Command test timed out for {service_name}")
        except Exception as e:
            self.logger.debug(f"Command test failed for {service_name}: {e}")

        return False

    def _attempt_auto_fix(
        self, service_name: str, diagnostic: ServiceDiagnostic
    ) -> bool:
        """
        Attempt to automatically fix a service issue.

        Args:
            service_name: Name of the service
            diagnostic: Current diagnostic information

        Returns:
            True if fix was successful
        """
        if not diagnostic.fix_command:
            return False

        self.logger.info(
            f"Attempting auto-fix for {service_name}: {diagnostic.fix_command}"
        )

        try:
            # Handle different types of fix commands
            if diagnostic.fix_command.startswith("pipx "):
                # Execute pipx command
                cmd_parts = diagnostic.fix_command.split()
                result = subprocess.run(
                    cmd_parts, capture_output=True, text=True, timeout=120, check=False
                )
                return result.returncode == 0

            if diagnostic.fix_command.startswith("chmod "):
                # Fix permissions
                path = diagnostic.fix_command.replace("chmod +x ", "")
                Path(path).chmod(0o755)
                return True

            if "claude-mpm configure" in diagnostic.fix_command:
                # Check if services are available (read-only)
                from .mcp_config_manager import MCPConfigManager

                manager = MCPConfigManager()
                available, message = manager.check_mcp_services_available()
                if not available:
                    # Cannot auto-fix - user must install services manually
                    self.logger.warning(f"Cannot auto-fix: {message}")
                return available

        except Exception as e:
            self.logger.error(f"Auto-fix failed for {service_name}: {e}")

        return False

    def print_diagnostics(
        self, diagnostics: Optional[Dict[str, ServiceDiagnostic]] = None
    ) -> None:
        """
        Print formatted diagnostic results to console.

        Args:
            diagnostics: Diagnostic results to print (uses self.diagnostics if None)
        """
        if diagnostics is None:
            diagnostics = self.diagnostics

        if not diagnostics:
            print("\n📋 No services verified yet")
            return

        print("\n" + "=" * 60)
        print("📋 MCP Service Verification Report")
        print("=" * 60)

        # Group by status
        working = []
        issues = []

        for _name, diag in diagnostics.items():
            if diag.status == ServiceStatus.WORKING:
                working.append(diag)
            else:
                issues.append(diag)

        # Print working services
        if working:
            print("\n✅ Fully Operational Services:")
            for diag in working:
                print(f"  • {diag.name}: {diag.message}")
                if diag.configured_command:
                    print(f"    Command: {diag.configured_command}")

        # Print services with issues
        if issues:
            print("\n⚠️ Services Requiring Attention:")
            for diag in issues:
                print(f"\n  {diag.status.value} {diag.name}:")
                print(f"    Issue: {diag.message}")
                if diag.installed_path:
                    print(f"    Path: {diag.installed_path}")
                if diag.fix_command:
                    print(f"    Fix: {diag.fix_command}")
                if diag.details:
                    print(f"    Details: {json.dumps(diag.details, indent=6)}")

        # Summary
        print("\n" + "=" * 60)
        print(f"Summary: {len(working)}/{len(diagnostics)} services operational")

        if issues:
            print("\n💡 Quick Fix Commands:")
            seen_fixes = set()
            for diag in issues:
                if diag.fix_command and diag.fix_command not in seen_fixes:
                    print(f"  {diag.fix_command}")
                    seen_fixes.add(diag.fix_command)

            print("\nOr run: claude-mpm verify --fix")

        print("=" * 60 + "\n")


def verify_mcp_services_on_startup() -> Tuple[bool, str]:
    """
    Quick verification check for MCP services during startup.

    This is a lightweight check that runs during CLI initialization
    to warn users of potential issues without blocking startup.

    Returns:
        Tuple of (all_working, summary_message)
    """
    verifier = MCPServiceVerifier()
    get_logger(__name__)

    # Do quick checks only (don't block startup)
    issues = []
    for service_name in MCPServiceVerifier.SERVICE_REQUIREMENTS:
        path = verifier._find_service_installation(service_name)
        if not path:
            issues.append(f"{service_name} not installed")
        elif not verifier._check_permissions(path):
            issues.append(f"{service_name} permission issue")

    if issues:
        message = f"MCP service issues detected: {', '.join(issues)}. Run 'claude-mpm verify' for details."
        return False, message

    return True, "All MCP services appear operational"
