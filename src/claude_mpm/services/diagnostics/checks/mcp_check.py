"""
Check MCP (Model Context Protocol) server status.

WHY: Verify that the MCP gateway is properly installed, configured,
and functioning for enhanced Claude Code capabilities.
"""

import json
import subprocess
from pathlib import Path

from claude_mpm.core.enums import OperationResult, ServiceState, ValidationSeverity

from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck


class MCPCheck(BaseDiagnosticCheck):
    """Check MCP server installation and configuration."""

    @property
    def name(self) -> str:
        return "mcp_check"

    @property
    def category(self) -> str:
        return "MCP Server"

    def run(self) -> DiagnosticResult:
        """Run MCP diagnostics."""
        try:
            sub_results = []
            details = {}

            # Check if MCP is installed
            install_result = self._check_installation()
            sub_results.append(install_result)
            details["installed"] = install_result.status == OperationResult.SUCCESS

            if install_result.status == OperationResult.SUCCESS:
                # Check MCP configuration
                config_result = self._check_configuration()
                sub_results.append(config_result)
                details["configured"] = config_result.status == OperationResult.SUCCESS

                # Check MCP server status
                status_result = self._check_server_status()
                sub_results.append(status_result)
                details["running"] = status_result.details.get("running", False)

                # Verify startup
                startup_result = self._check_startup_verification()
                sub_results.append(startup_result)

            # Determine overall status
            if any(r.status == ValidationSeverity.ERROR for r in sub_results):
                status = ValidationSeverity.ERROR
                message = "MCP server has critical issues"
            elif not details.get("installed", False):
                status = ValidationSeverity.WARNING
                message = "MCP server not installed"
            elif any(r.status == ValidationSeverity.WARNING for r in sub_results):
                status = ValidationSeverity.WARNING
                message = "MCP server needs configuration"
            else:
                status = OperationResult.SUCCESS
                message = "MCP server properly configured"

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
                message=f"MCP check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_installation(self) -> DiagnosticResult:
        """Check if MCP server is installed."""
        # Check for MCP binary
        mcp_paths = [
            Path("/usr/local/bin/claude-mpm-mcp"),
            Path.home() / ".local/bin/claude-mpm-mcp",
            Path("/opt/claude-mpm/bin/claude-mpm-mcp"),
        ]

        for mcp_path in mcp_paths:
            if mcp_path.exists():
                return DiagnosticResult(
                    category="MCP Installation",
                    status=OperationResult.SUCCESS,
                    message="MCP server installed",
                    details={"path": str(mcp_path), "installed": True},
                )

        # Check if it's available via command
        try:
            result = subprocess.run(
                ["which", "claude-mpm-mcp"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                return DiagnosticResult(
                    category="MCP Installation",
                    status=OperationResult.SUCCESS,
                    message="MCP server installed",
                    details={"path": path, "installed": True},
                )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return DiagnosticResult(
            category="MCP Installation",
            status=ValidationSeverity.WARNING,
            message="MCP server not installed",
            details={"installed": False},
            fix_command="claude-mpm mcp install",
            fix_description="Install MCP server for enhanced capabilities",
        )

    def _check_configuration(self) -> DiagnosticResult:
        """Check MCP configuration in Claude Code."""
        config_paths = [
            Path.home() / ".config/claude/claude_desktop_config.json",
            Path.home()
            / "Library/Application Support/Claude/claude_desktop_config.json",
            Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json",
        ]

        config_path = None
        for path in config_paths:
            if path.exists():
                config_path = path
                break

        if not config_path:
            return DiagnosticResult(
                category="MCP Configuration",
                status=ValidationSeverity.WARNING,
                message="Claude Code config not found",
                details={"configured": False},
                fix_command="claude-mpm mcp config",
                fix_description="Configure MCP server in Claude Code",
            )

        try:
            with config_path.open() as f:
                config = json.load(f)

                mcp_servers = config.get("mcpServers", {})
                gateway = mcp_servers.get("claude-mpm-gateway", {})

                if not gateway:
                    return DiagnosticResult(
                        category="MCP Configuration",
                        status=ValidationSeverity.WARNING,
                        message="MCP gateway not configured",
                        details={"configured": False, "config_path": str(config_path)},
                        fix_command="claude-mpm mcp config",
                        fix_description="Add MCP gateway to Claude Code configuration",
                    )

                # Check configuration validity
                command = gateway.get("command")
                if not command:
                    return DiagnosticResult(
                        category="MCP Configuration",
                        status=ValidationSeverity.ERROR,
                        message="MCP gateway misconfigured (no command)",
                        details={
                            "configured": True,
                            "valid": False,
                            "config_path": str(config_path),
                        },
                        fix_command="claude-mpm mcp config --force",
                        fix_description="Fix MCP gateway configuration",
                    )

                return DiagnosticResult(
                    category="MCP Configuration",
                    status=OperationResult.SUCCESS,
                    message="MCP gateway configured",
                    details={
                        "configured": True,
                        "command": command,
                        "config_path": str(config_path),
                    },
                )

        except json.JSONDecodeError as e:
            return DiagnosticResult(
                category="MCP Configuration",
                status=ValidationSeverity.ERROR,
                message="Invalid JSON in config file",
                details={"error": str(e), "config_path": str(config_path)},
                fix_description="Fix JSON syntax in Claude Code config",
            )
        except Exception as e:
            return DiagnosticResult(
                category="MCP Configuration",
                status=ValidationSeverity.WARNING,
                message=f"Could not check configuration: {e!s}",
                details={"error": str(e)},
            )

    def _check_server_status(self) -> DiagnosticResult:
        """Check if MCP server is running."""
        try:
            # Try to connect to the MCP server
            result = subprocess.run(
                ["claude-mpm", "mcp", "status"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if result.returncode == 0:
                if ServiceState.RUNNING.value in result.stdout.lower():
                    return DiagnosticResult(
                        category="MCP Server Status",
                        status=OperationResult.SUCCESS,
                        message="MCP server is running",
                        details={"running": True, "state": ServiceState.RUNNING},
                    )
                return DiagnosticResult(
                    category="MCP Server Status",
                    status=ValidationSeverity.WARNING,
                    message="MCP server not running",
                    details={"running": False, "state": ServiceState.STOPPED},
                    fix_command="claude-mpm mcp start",
                    fix_description="Start the MCP server",
                )
            return DiagnosticResult(
                category="MCP Server Status",
                status=ValidationSeverity.WARNING,
                message="Could not determine server status",
                details={
                    "running": "unknown",
                    "state": ServiceState.UNKNOWN,
                    "error": result.stderr,
                },
            )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                category="MCP Server Status",
                status=ValidationSeverity.WARNING,
                message="Server status check timed out",
                details={
                    "running": "unknown",
                    "state": ServiceState.UNKNOWN,
                    "error": "timeout",
                },
            )
        except Exception as e:
            return DiagnosticResult(
                category="MCP Server Status",
                status=ValidationSeverity.WARNING,
                message=f"Could not check server status: {e!s}",
                details={
                    "running": "unknown",
                    "state": ServiceState.UNKNOWN,
                    "error": str(e),
                },
            )

    def _check_startup_verification(self) -> DiagnosticResult:
        """Run MCP startup verification."""
        try:
            from ....services.mcp_gateway.core.startup_verification import (
                MCPGatewayStartupVerifier,
            )

            verifier = MCPGatewayStartupVerifier()
            issues = verifier.verify_startup()

            if not issues:
                return DiagnosticResult(
                    category="MCP Startup Verification",
                    status=OperationResult.SUCCESS,
                    message="Startup verification passed",
                    details={"issues": []},
                )

            # Categorize issues by severity
            errors = [
                i for i in issues if "error" in i.lower() or "critical" in i.lower()
            ]
            warnings = [i for i in issues if i not in errors]

            if errors:
                return DiagnosticResult(
                    category="MCP Startup Verification",
                    status=ValidationSeverity.ERROR,
                    message=f"{len(errors)} critical issue(s) found",
                    details={"errors": errors, "warnings": warnings},
                )
            if warnings:
                return DiagnosticResult(
                    category="MCP Startup Verification",
                    status=ValidationSeverity.WARNING,
                    message=f"{len(warnings)} warning(s) found",
                    details={"warnings": warnings},
                )
            return DiagnosticResult(
                category="MCP Startup Verification",
                status=OperationResult.SUCCESS,
                message="Startup verification passed",
                details={"issues": []},
            )

        except Exception as e:
            return DiagnosticResult(
                category="MCP Startup Verification",
                status=ValidationSeverity.WARNING,
                message=f"Could not verify startup: {e!s}",
                details={"error": str(e)},
            )
