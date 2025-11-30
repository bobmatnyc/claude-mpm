"""
Reporter for formatting and displaying diagnostic results.

WHY: Provide clear, actionable output from diagnostic checks with proper
formatting for terminal display and JSON export.
"""

import json
import sys

from claude_mpm.core.enums import OperationResult, ValidationSeverity

from .models import DiagnosticResult, DiagnosticSummary


class DoctorReporter:
    """Format and display diagnostic results.

    WHY: Consistent, user-friendly output that clearly shows system health
    status and provides actionable fixes for any issues.
    """

    # Status symbols and colors
    STATUS_SYMBOLS = {
        OperationResult.SUCCESS: "✅",
        ValidationSeverity.WARNING: "⚠️ ",
        ValidationSeverity.ERROR: "❌",
        OperationResult.SKIPPED: "⏭️ ",
    }

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "gray": "\033[90m",
    }

    def __init__(self, use_color: bool = True, verbose: bool = False):
        """Initialize reporter.

        Args:
            use_color: Whether to use ANSI color codes
            verbose: Whether to include detailed information
        """
        self.use_color = use_color and sys.stdout.isatty()
        self.verbose = verbose

    def report(self, summary: DiagnosticSummary, format: str = "terminal"):
        """Generate and output diagnostic report.

        Args:
            summary: DiagnosticSummary with all results
            format: Output format ("terminal", "json", "markdown")
        """
        if format == "json":
            self._report_json(summary)
        elif format == "markdown":
            self._report_markdown(summary)
        else:
            self._report_terminal(summary)

    def _report_terminal(self, summary: DiagnosticSummary):
        """Generate terminal-formatted report."""
        # Header
        self._print_header()

        # Results by category
        for result in summary.results:
            self._print_result(result)

        # Summary
        self._print_summary(summary)

        # Fix suggestions
        self._print_fixes(summary)

    def _print_header(self):
        """Print report header."""
        print()
        print(self._color("Claude MPM Doctor Report", "bold"))
        print("=" * 40)
        print()

    def _print_result(self, result: DiagnosticResult, indent: int = 0):
        """Print a single diagnostic result."""
        indent_str = "  " * indent

        # Status symbol and category
        symbol = self.STATUS_SYMBOLS.get(result.status, "?")
        color = self._get_status_color(result.status)

        # Main result line
        line = f"{indent_str}{symbol} {result.category}: "

        if result.status == OperationResult.SUCCESS:
            line += self._color("OK", color)
        elif result.status == ValidationSeverity.WARNING:
            line += self._color("Warning", color)
        elif result.status == ValidationSeverity.ERROR:
            line += self._color("Error", color)
        else:
            line += self._color("Skipped", color)

        print(line)

        # Message
        message_indent = "   " + indent_str
        print(f"{message_indent}{result.message}")

        # Details (in verbose mode)
        if self.verbose and result.details:
            for key, value in result.details.items():
                if key not in ["error", "issues"]:  # Skip complex fields
                    print(f"{message_indent}{self._color(key, 'gray')}: {value}")

        # Fix suggestion
        if result.fix_command:
            fix_indent = "   " + indent_str
            print(
                f"{fix_indent}{self._color('→ Fix:', 'blue')} Run '{result.fix_command}'"
            )
            if result.fix_description:
                print(f"{fix_indent}  {self._color(result.fix_description, 'gray')}")

        # Sub-results (in verbose mode)
        if self.verbose and result.sub_results:
            for sub_result in result.sub_results:
                self._print_result(sub_result, indent + 1)

        if indent == 0:
            print()  # Extra line between top-level results

    def _print_summary(self, summary: DiagnosticSummary):
        """Print summary statistics."""
        print(self._color("─" * 40, "gray"))

        status_line = "Summary: "
        parts = []

        if summary.ok_count > 0:
            parts.append(self._color(f"{summary.ok_count} OK", "green"))
        if summary.warning_count > 0:
            parts.append(
                self._color(
                    f"{summary.warning_count} Warning{'s' if summary.warning_count != 1 else ''}",
                    "yellow",
                )
            )
        if summary.error_count > 0:
            parts.append(
                self._color(
                    f"{summary.error_count} Error{'s' if summary.error_count != 1 else ''}",
                    "red",
                )
            )
        if summary.skipped_count > 0:
            parts.append(self._color(f"{summary.skipped_count} Skipped", "gray"))

        status_line += " | ".join(parts)
        print(status_line)

        # Overall health
        overall = summary.overall_status
        if overall == OperationResult.SUCCESS:
            print(self._color("\n✅ System is healthy!", "green"))
        elif overall == ValidationSeverity.WARNING:
            print(
                self._color(
                    "\n⚠️  System has minor issues that should be addressed.", "yellow"
                )
            )
        else:
            print(
                self._color(
                    "\n❌ System has critical issues that need immediate attention!",
                    "red",
                )
            )

    def _print_fixes(self, summary: DiagnosticSummary):
        """Print consolidated fix suggestions."""
        fixes = []

        for result in summary.results:
            if result.fix_command and result.has_issues:
                fixes.append(
                    (result.category, result.fix_command, result.fix_description)
                )

        if fixes:
            print()
            print(self._color("Suggested Fixes:", "bold"))
            print(self._color("─" * 40, "gray"))

            for i, (category, command, description) in enumerate(fixes, 1):
                print(f"{i}. {category}:")
                print(f"   {self._color(command, 'blue')}")
                if description:
                    print(f"   {self._color(description, 'gray')}")
                print()

            if self.verbose:
                print(
                    self._color(
                        "Run 'claude-mpm doctor --fix' to attempt automatic fixes",
                        "gray",
                    )
                )
            else:
                print(
                    self._color(
                        "Run 'claude-mpm doctor --verbose' for more details", "gray"
                    )
                )

    def _report_json(self, summary: DiagnosticSummary):
        """Generate JSON-formatted report."""
        output = summary.to_dict()

        # Add metadata
        output["metadata"] = {
            "tool": "claude-mpm doctor",
            "version": self._get_version(),
            "verbose": self.verbose,
        }

        # Add fix suggestions
        fixes = []
        for result in summary.results:
            if result.fix_command and result.has_issues:
                fixes.append(
                    {
                        "category": result.category,
                        "command": result.fix_command,
                        "description": result.fix_description,
                    }
                )
        output["fixes"] = fixes

        print(json.dumps(output, indent=2))

    def _report_markdown(self, summary: DiagnosticSummary):
        """Generate comprehensive Markdown-formatted report."""
        import datetime
        import platform
        import sys

        # Header with timestamp and system info
        print("# Claude MPM Doctor Report")
        print()
        now = datetime.datetime.now(datetime.timezone.utc)
        print(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(
            f"**System:** {platform.system()} {platform.release()} ({platform.machine()})"
        )
        print(f"**Python:** {sys.version.split()[0]}")
        print(f"**claude-mpm:** {self._get_version()}")

        # Get current working directory for context
        from pathlib import Path

        cwd = Path.cwd()
        print(f"**Working Directory:** {cwd}")

        print()
        print("---")
        print()

        # System Overview
        print("## System Overview\n")
        self._print_system_overview_markdown(summary)
        print()

        # Summary Statistics
        print("## Summary Statistics\n")
        print("| Status | Count | Percentage |")
        print("|--------|-------|------------|")
        total = (
            summary.ok_count
            + summary.warning_count
            + summary.error_count
            + summary.skipped_count
        )
        if total > 0:
            print(
                f"| ✅ OK | {summary.ok_count} | {summary.ok_count * 100 // total}% |"
            )
            print(
                f"| ⚠️  Warning | {summary.warning_count} | {summary.warning_count * 100 // total}% |"
            )
            print(
                f"| ❌ Error | {summary.error_count} | {summary.error_count * 100 // total}% |"
            )
            print(
                f"| ⏭️  Skipped | {summary.skipped_count} | {summary.skipped_count * 100 // total}% |"
            )
        print()

        # Overall Health Status
        overall = summary.overall_status
        if overall == OperationResult.SUCCESS:
            print("### 🎉 Overall Status: **Healthy**")
            print("Your Claude MPM installation is functioning properly.\n")
        elif overall == ValidationSeverity.WARNING:
            print("### ⚠️ Overall Status: **Needs Attention**")
            print("Your installation has minor issues that should be addressed.\n")
        else:
            print("### ❌ Overall Status: **Critical Issues**")
            print(
                "Your installation has critical issues that need immediate attention.\n"
            )

        # MCP Services Status (if available)
        self._print_mcp_services_markdown(summary)

        # Installation Details
        self._print_installation_details_markdown(summary)

        # Detailed Diagnostic Results
        print("## Detailed Diagnostic Results\n")
        for result in summary.results:
            self._print_result_markdown(result)

        # Recommendations Section
        self._print_recommendations_markdown(summary)

        # Fixes Section
        fixes = [
            (r.category, r.fix_command, r.fix_description)
            for r in summary.results
            if r.fix_command and r.has_issues
        ]

        if fixes:
            print("## 🔧 Suggested Fixes\n")
            print("Run these commands to fix identified issues:\n")
            print("```bash")
            for category, command, description in fixes:
                print(f"# Fix: {category}")
                if description:
                    print(f"# {description}")
                print(command)
                print()
            print("```")
            print()

        # Footer with generation metadata
        print("---")
        print()
        print("## Report Metadata")
        print()
        print("- **Tool:** `claude-mpm doctor`")
        print(f"- **Version:** {self._get_version()}")
        print(f"- **Generated:** {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        if self.verbose:
            print("- **Verbose Mode:** Enabled")
        print()
        print("---")
        print()
        print("🤖 *Generated with [Claude Code](https://claude.com/claude-code)*")
        print()
        print(
            "*For more information, run `claude-mpm doctor --verbose` or visit the [documentation](https://github.com/bobmatnyc/claude-mpm).*"
        )

    def _color(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_color:
            return text

        color_code = self.COLORS.get(color, "")
        reset_code = self.COLORS["reset"]
        return f"{color_code}{text}{reset_code}"

    def _get_status_color(self, status) -> str:
        """Get color for a status."""
        color_map = {
            OperationResult.SUCCESS: "green",
            ValidationSeverity.WARNING: "yellow",
            ValidationSeverity.ERROR: "red",
            OperationResult.SKIPPED: "gray",
        }
        return color_map.get(status, "reset")

    def _get_version(self) -> str:
        """Get claude-mpm version."""
        try:
            from ..version_service import VersionService

            service = VersionService()
            return service.get_version()
        except Exception:
            return "unknown"

    def _print_system_overview_markdown(self, summary: DiagnosticSummary):
        """Print system overview in markdown format."""
        import platform
        import sys

        print("| Component | Value |")
        print("|-----------|-------|")
        print(f"| Platform | {platform.system()} {platform.release()} |")
        print(f"| Python Version | {sys.version.split()[0]} |")

        # Extract key details from results
        for result in summary.results:
            if result.category == "Installation":
                if result.details.get("claude_mpm_version"):
                    print(
                        f"| Claude MPM Version | {result.details['claude_mpm_version']} |"
                    )
                if result.details.get("installation_method"):
                    print(
                        f"| Installation Method | {result.details['installation_method']} |"
                    )
            elif result.category == "Claude Code":
                if result.details.get("version"):
                    print(f"| Claude Code (CLI) | {result.details['version']} |")

    def _print_mcp_services_markdown(self, summary: DiagnosticSummary):
        """Print MCP services status table in markdown."""
        # Find MCP Services result
        mcp_services_result = None
        for result in summary.results:
            if result.category == "MCP Services":
                mcp_services_result = result
                break

        if not mcp_services_result or not mcp_services_result.details.get("services"):
            return

        print("## MCP Services Status\n")
        print("| Service | Installed | Accessible | Version | Status |")
        print("|---------|-----------|------------|---------|--------|")

        services = mcp_services_result.details.get("services", {})
        for service_name, service_info in services.items():
            installed = "✅" if service_info.get("installed") else "❌"
            accessible = "✅" if service_info.get("accessible") else "❌"
            version = service_info.get("version")
            if version:
                version = str(version)[:20]  # Truncate long versions
            else:
                version = "N/A"
            status = service_info.get("status", "unknown")

            # Map status to emoji
            if status == "ok":
                status_emoji = "✅"
            elif status == "warning":
                status_emoji = "⚠️"
            elif status == "error":
                status_emoji = "❌"
            else:
                status_emoji = "❓"

            print(
                f"| {service_name} | {installed} | {accessible} | {version} | {status_emoji} |"
            )
        print()

    def _print_installation_details_markdown(self, summary: DiagnosticSummary):
        """Print installation details in markdown."""
        # Find installation result
        install_result = None
        for result in summary.results:
            if result.category == "Installation":
                install_result = result
                break

        if not install_result:
            return

        print("## Installation Details\n")

        # Print sub-results if available
        if install_result.sub_results and self.verbose:
            for sub in install_result.sub_results:
                if sub.category == "Python Version":
                    print("### Python Environment")
                    print(f"- **Version:** {sub.message}")
                elif sub.category == "Installation Method":
                    print("### Installation Method")
                    print(f"- **Method:** {sub.message}")
                    if sub.details.get("container_type"):
                        print(f"- **Container:** {sub.details['container_type']}")
                    if sub.details.get("pipx_metadata"):
                        metadata = sub.details["pipx_metadata"]
                        if metadata.get("version"):
                            print(f"- **Pipx Version:** {metadata['version']}")
                elif sub.category == "Dependencies":
                    print("### Dependencies")
                    print(f"- **Status:** {sub.message}")
                    if sub.details.get("installed"):
                        print(
                            f"- **Installed Packages:** {len(sub.details['installed'])}"
                        )
            print()

    def _print_result_markdown(self, result: DiagnosticResult):
        """Print a single result in markdown format."""
        symbol = self.STATUS_SYMBOLS.get(result.status, "?")
        print(f"### {symbol} {result.category}\n")

        # Status badge
        status_badge_map = {
            OperationResult.SUCCESS: "![OK](https://img.shields.io/badge/status-OK-green)",
            ValidationSeverity.WARNING: "![Warning](https://img.shields.io/badge/status-Warning-yellow)",
            ValidationSeverity.ERROR: "![Error](https://img.shields.io/badge/status-Error-red)",
            OperationResult.SKIPPED: "![Skipped](https://img.shields.io/badge/status-Skipped-gray)",
        }
        status_badge = status_badge_map.get(result.status, "")

        print(f"{status_badge}")
        print(f"\n**Message:** {result.message}\n")

        if result.fix_command:
            print("**Fix Available:**")
            print("```bash")
            print(result.fix_command)
            print("```")
            if result.fix_description:
                print(f"*{result.fix_description}*\n")

        if self.verbose and result.details:
            print("<details>")
            print("<summary>Details</summary>\n")
            print("```json")
            import json

            print(json.dumps(result.details, indent=2, default=str))
            print("```")
            print("</details>\n")

    def _print_recommendations_markdown(self, summary: DiagnosticSummary):
        """Print recommendations based on diagnostic results."""
        recommendations = []

        # Analyze results for recommendations

        # Check specific conditions
        for result in summary.results:
            if (
                result.category == "Installation"
                and result.status != OperationResult.SUCCESS
            ):
                if "pipx" not in str(result.details.get("installation_method", "")):
                    recommendations.append(
                        "Consider using pipx for isolated installation: `pipx install claude-mpm`"
                    )

            if result.category == "MCP Services":
                services = result.details.get("services", {})
                missing = [
                    s for s, info in services.items() if not info.get("installed")
                ]
                if missing:
                    recommendations.append(
                        f"Install missing MCP services for enhanced features: {', '.join(missing)}"
                    )

            if (
                result.category == "Claude Code"
                and result.status == ValidationSeverity.WARNING
            ):
                recommendations.append(
                    "Update Claude Code (CLI) to the latest version for best compatibility"
                )

        if recommendations:
            print("## 📋 Recommendations\n")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
            print()
