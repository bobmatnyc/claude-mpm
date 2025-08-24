"""
Check Claude Desktop integration.

WHY: Verify that Claude Desktop is installed, properly configured,
and integrated with claude-mpm.
"""

import json
import subprocess
from pathlib import Path

from ..models import DiagnosticResult, DiagnosticStatus
from .base_check import BaseDiagnosticCheck


class ClaudeDesktopCheck(BaseDiagnosticCheck):
    """Check Claude Desktop installation and integration."""

    @property
    def name(self) -> str:
        return "claude_desktop_check"

    @property
    def category(self) -> str:
        return "Claude Desktop"

    def run(self) -> DiagnosticResult:
        """Run Claude Desktop diagnostics."""
        try:
            sub_results = []
            details = {}

            # Check if Claude Desktop is installed
            install_result = self._check_installation()
            sub_results.append(install_result)
            details["installed"] = install_result.status == DiagnosticStatus.OK

            if install_result.status == DiagnosticStatus.OK:
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
                details["mcp_configured"] = mcp_result.status == DiagnosticStatus.OK

            # Determine overall status
            if any(r.status == DiagnosticStatus.ERROR for r in sub_results):
                status = DiagnosticStatus.ERROR
                message = "Claude Desktop has critical issues"
            elif any(r.status == DiagnosticStatus.WARNING for r in sub_results):
                status = DiagnosticStatus.WARNING
                message = "Claude Desktop needs configuration"
            else:
                status = DiagnosticStatus.OK
                message = "Claude Desktop properly configured"

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
                message=f"Claude Desktop check failed: {e!s}",
                details={"error": str(e)},
            )

    def _check_installation(self) -> DiagnosticResult:
        """Check if Claude Desktop is installed."""
        # Check common installation paths
        mac_path = Path("/Applications/Claude.app")
        linux_paths = [
            Path.home() / ".local/share/applications/claude.desktop",
            Path("/usr/share/applications/claude.desktop"),
            Path("/opt/Claude"),
        ]
        windows_paths = [
            Path("C:/Program Files/Claude/Claude.exe"),
            Path.home() / "AppData/Local/Claude/Claude.exe",
        ]

        # Check for Claude process
        try:
            result = subprocess.run(
                ["pgrep", "-f", "Claude"], capture_output=True, timeout=2, check=False
            )
            if result.returncode == 0:
                return DiagnosticResult(
                    category="Claude Desktop Installation",
                    status=DiagnosticStatus.OK,
                    message="Claude Desktop is running",
                    details={"running": True},
                )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Check installation paths
        if mac_path.exists():
            return DiagnosticResult(
                category="Claude Desktop Installation",
                status=DiagnosticStatus.OK,
                message="Claude Desktop installed (macOS)",
                details={"path": str(mac_path), "platform": "macos"},
            )

        for path in linux_paths:
            if path.exists():
                return DiagnosticResult(
                    category="Claude Desktop Installation",
                    status=DiagnosticStatus.OK,
                    message="Claude Desktop installed (Linux)",
                    details={"path": str(path), "platform": "linux"},
                )

        for path in windows_paths:
            if path.exists():
                return DiagnosticResult(
                    category="Claude Desktop Installation",
                    status=DiagnosticStatus.OK,
                    message="Claude Desktop installed (Windows)",
                    details={"path": str(path), "platform": "windows"},
                )

        return DiagnosticResult(
            category="Claude Desktop Installation",
            status=DiagnosticStatus.WARNING,
            message="Claude Desktop not found",
            details={"installed": False},
            fix_description="Install Claude Desktop from https://claude.ai/download",
        )

    def _check_version(self) -> DiagnosticResult:
        """Check Claude Desktop version compatibility."""
        # Try to get version from config file
        config_paths = [
            Path.home() / "Library/Application Support/Claude/config.json",  # macOS
            Path.home() / ".config/Claude/config.json",  # Linux
            Path.home() / "AppData/Roaming/Claude/config.json",  # Windows
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)
                        version = config.get("version", "unknown")

                        # Simple version check (would need real version comparison logic)
                        return DiagnosticResult(
                            category="Claude Desktop Version",
                            status=DiagnosticStatus.OK,
                            message=f"Version: {version}",
                            details={
                                "version": version,
                                "config_path": str(config_path),
                            },
                        )
                except Exception:
                    pass

        return DiagnosticResult(
            category="Claude Desktop Version",
            status=DiagnosticStatus.WARNING,
            message="Could not determine version",
            details={"version": "unknown"},
        )

    def _check_output_style(self) -> DiagnosticResult:
        """Check if output style is deployed."""
        style_path = Path.home() / ".claude/responses/OUTPUT_STYLE.md"

        if not style_path.exists():
            return DiagnosticResult(
                category="Output Style",
                status=DiagnosticStatus.WARNING,
                message="Output style not deployed",
                details={"deployed": False, "path": str(style_path)},
                fix_command="claude-mpm deploy-style",
                fix_description="Deploy claude-mpm output style for better formatting",
            )

        # Check if it's up to date
        try:
            with open(style_path) as f:
                content = f.read()
                if "Claude MPM Output Style" in content:
                    return DiagnosticResult(
                        category="Output Style",
                        status=DiagnosticStatus.OK,
                        message="Output style deployed",
                        details={"deployed": True, "path": str(style_path)},
                    )
                return DiagnosticResult(
                    category="Output Style",
                    status=DiagnosticStatus.WARNING,
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
                status=DiagnosticStatus.WARNING,
                message=f"Could not check output style: {e!s}",
                details={"error": str(e)},
            )

    def _check_mcp_integration(self) -> DiagnosticResult:
        """Check MCP server integration with Claude Desktop."""
        config_path = Path.home() / ".config/claude/claude_desktop_config.json"

        if not config_path.exists():
            # Try alternate paths
            alt_paths = [
                Path.home()
                / "Library/Application Support/Claude/claude_desktop_config.json",
                Path.home() / "AppData/Roaming/Claude/claude_desktop_config.json",
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    config_path = alt_path
                    break
            else:
                return DiagnosticResult(
                    category="MCP Integration",
                    status=DiagnosticStatus.WARNING,
                    message="Claude Desktop config not found",
                    details={"configured": False},
                    fix_command="claude-mpm mcp install",
                    fix_description="Install MCP server integration",
                )

        try:
            with open(config_path) as f:
                config = json.load(f)

                mcp_servers = config.get("mcpServers", {})
                if "claude-mpm-gateway" in mcp_servers:
                    return DiagnosticResult(
                        category="MCP Integration",
                        status=DiagnosticStatus.OK,
                        message="MCP server configured",
                        details={
                            "configured": True,
                            "server_count": len(mcp_servers),
                            "config_path": str(config_path),
                        },
                    )
                return DiagnosticResult(
                    category="MCP Integration",
                    status=DiagnosticStatus.WARNING,
                    message="MCP server not configured",
                    details={
                        "configured": False,
                        "server_count": len(mcp_servers),
                        "config_path": str(config_path),
                    },
                    fix_command="claude-mpm mcp install",
                    fix_description="Configure MCP server for Claude Desktop",
                )

        except Exception as e:
            return DiagnosticResult(
                category="MCP Integration",
                status=DiagnosticStatus.WARNING,
                message=f"Could not check MCP configuration: {e!s}",
                details={"error": str(e)},
            )
