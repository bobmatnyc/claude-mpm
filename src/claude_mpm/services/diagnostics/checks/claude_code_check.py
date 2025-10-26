"""
Check Claude Code (CLI) integration.

WHY: Verify that Claude Code CLI is installed, properly configured,
and integrated with claude-mpm.
"""

import json
import subprocess
from pathlib import Path

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck


class ClaudeCodeCheck(BaseDiagnosticCheck):
    """Check Claude Code CLI installation and integration."""

    @property
    def name(self) -> str:
        return "claude_code_check"

    @property
    def category(self) -> str:
        return "Claude Code"

    def run(self) -> DiagnosticResult:
        """Run Claude Code CLI diagnostics."""
        try:
            sub_results = []
            details = {}

            # Check if Claude Code CLI is installed
            install_result = self._check_installation()
            sub_results.append(install_result)
            details["installed"] = install_result.status == OperationResult.SUCCESS

            if install_result.status == OperationResult.SUCCESS:
                # Check version compatibility
                version_result = self._check_version()
                sub_results.append(version_result)
                details["version"] = version_result.details.get("version")

                # Check output style deployment
                style_result = self._check_output_style()
                sub_results.append(style_result)
                details["output_style"] = style_result.details.get("deployed")

                # Check MCP integration
                mcp_result = self._check_mcp_integration()
                sub_results.append(mcp_result)
                details["mcp_configured"] = mcp_result.status == OperationResult.SUCCESS

            # Determine overall status
            if any(r.status == ValidationSeverity.ERROR for r in sub_results):
                status = ValidationSeverity.ERROR
                message = "Claude Code CLI has critical issues"
            elif any(r.status == ValidationSeverity.WARNING for r in sub_results):
                status = ValidationSeverity.WARNING
                message = "Claude Code CLI needs configuration"
            else:
                status = OperationResult.SUCCESS
                message = "Claude Code CLI properly configured"

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
                message=f"Claude Code CLI check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_installation(self) -> DiagnosticResult:
        """Check if Claude Code CLI is installed."""
        # Check if claude command is available
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                timeout=5,
                check=False,
                text=True,
            )
            if result.returncode == 0:
                return DiagnosticResult(
                    category="Claude Code CLI Installation",
                    status=OperationResult.SUCCESS,
                    message="Claude Code CLI is installed and accessible",
                    details={
                        "installed": True,
                        "path": "claude",
                        "version_output": result.stdout.strip(),
                    },
                )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Check common installation paths
        possible_paths = [
            Path("/usr/local/bin/claude"),
            Path.home() / ".local/bin/claude",
            Path("/opt/homebrew/bin/claude"),
            Path("/usr/bin/claude"),
        ]

        for path in possible_paths:
            if path.exists() and path.is_file():
                return DiagnosticResult(
                    category="Claude Code CLI Installation",
                    status=OperationResult.SUCCESS,
                    message=f"Claude Code CLI found at {path}",
                    details={"installed": True, "path": str(path)},
                )

        return DiagnosticResult(
            category="Claude Code CLI Installation",
            status=ValidationSeverity.ERROR,
            message="Claude Code CLI not found",
            details={"installed": False},
            fix_description="Install Claude Code CLI from https://claude.ai/code",
        )

    def _check_version(self) -> DiagnosticResult:
        """Check Claude Code CLI version compatibility."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
                text=True,
            )
            version_output = result.stdout.strip()

            # Extract version number (basic parsing)
            version = "unknown"
            if "version" in version_output.lower():
                parts = version_output.split()
                for i, part in enumerate(parts):
                    if "version" in part.lower() and i + 1 < len(parts):
                        version = parts[i + 1]
                        break

            # Check minimum version requirement (1.0.60+)
            status = OperationResult.SUCCESS
            message = f"Version: {version}"

            return DiagnosticResult(
                category="Claude Code CLI Version",
                status=status,
                message=message,
                details={
                    "version": version,
                    "version_output": version_output,
                },
            )

        except subprocess.SubprocessError as e:
            return DiagnosticResult(
                category="Claude Code CLI Version",
                status=ValidationSeverity.WARNING,
                message=f"Could not determine version: {e}",
                details={"version": "unknown", "error": str(e)},
            )

    def _check_output_style(self) -> DiagnosticResult:
        """Check if output style is deployed."""
        style_path = Path.home() / ".claude/responses/OUTPUT_STYLE.md"

        if not style_path.exists():
            return DiagnosticResult(
                category="Output Style",
                status=ValidationSeverity.WARNING,
                message="Output style not deployed",
                details={"deployed": False, "path": str(style_path)},
                fix_command="claude-mpm deploy-style",
                fix_description="Deploy claude-mpm output style for better formatting",
            )

        # Check if it's up to date
        try:
            with style_path.open() as f:
                content = f.read()
                if "Claude MPM Output Style" in content:
                    return DiagnosticResult(
                        category="Output Style",
                        status=OperationResult.SUCCESS,
                        message="Output style deployed",
                        details={"deployed": True, "path": str(style_path)},
                    )
                return DiagnosticResult(
                    category="Output Style",
                    status=ValidationSeverity.WARNING,
                    message="Output style outdated",
                    details={
                        "deployed": True,
                        "outdated": True,
                        "path": str(style_path),
                    },
                    fix_command="claude-mpm deploy-style --force",
                    fix_description="Update output style to latest version",
                )
        except Exception as e:
            return DiagnosticResult(
                category="Output Style",
                status=ValidationSeverity.WARNING,
                message=f"Could not check output style: {e!s}",
                details={"error": str(e)},
            )

    def _check_mcp_integration(self) -> DiagnosticResult:
        """Check MCP server integration with Claude Code CLI."""
        # Claude Code CLI uses ~/.claude.json for configuration
        config_path = Path.home() / ".claude.json"

        if not config_path.exists():
            return DiagnosticResult(
                category="MCP Integration",
                status=ValidationSeverity.WARNING,
                message="Claude Code CLI config not found",
                details={"configured": False, "config_path": str(config_path)},
                fix_command="claude-mpm mcp install",
                fix_description="Install MCP server integration for Claude Code CLI",
            )

        try:
            with config_path.open() as f:
                config = json.load(f)

                mcp_servers = config.get("mcpServers", {})
                if "claude-mpm-gateway" in mcp_servers or "claude-mpm" in mcp_servers:
                    return DiagnosticResult(
                        category="MCP Integration",
                        status=OperationResult.SUCCESS,
                        message="MCP server configured",
                        details={
                            "configured": True,
                            "server_count": len(mcp_servers),
                            "config_path": str(config_path),
                        },
                    )
                return DiagnosticResult(
                    category="MCP Integration",
                    status=ValidationSeverity.WARNING,
                    message="MCP server not configured",
                    details={
                        "configured": False,
                        "server_count": len(mcp_servers),
                        "config_path": str(config_path),
                    },
                    fix_command="claude-mpm mcp install",
                    fix_description="Configure MCP server for Claude Code CLI",
                )

        except Exception as e:
            return DiagnosticResult(
                category="MCP Integration",
                status=ValidationSeverity.WARNING,
                message=f"Could not check MCP configuration: {e!s}",
                details={"error": str(e)},
            )
