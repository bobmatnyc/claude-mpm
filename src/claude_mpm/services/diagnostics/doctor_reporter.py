"""
Reporter for formatting and displaying diagnostic results.

WHY: Provide clear, actionable output from diagnostic checks with proper
formatting for terminal display and JSON export.
"""

import json
import sys

from .models import DiagnosticResult, DiagnosticStatus, DiagnosticSummary


class DoctorReporter:
    """Format and display diagnostic results.

    WHY: Consistent, user-friendly output that clearly shows system health
    status and provides actionable fixes for any issues.
    """

    # Status symbols and colors
    STATUS_SYMBOLS = {
        DiagnosticStatus.OK: "✅",
        DiagnosticStatus.WARNING: "⚠️ ",
        DiagnosticStatus.ERROR: "❌",
        DiagnosticStatus.SKIPPED: "⏭️ ",
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

        if result.status == DiagnosticStatus.OK:
            line += self._color("OK", color)
        elif result.status == DiagnosticStatus.WARNING:
            line += self._color("Warning", color)
        elif result.status == DiagnosticStatus.ERROR:
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
        if overall == DiagnosticStatus.OK:
            print(self._color("\n✅ System is healthy!", "green"))
        elif overall == DiagnosticStatus.WARNING:
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
        """Generate Markdown-formatted report."""
        print("# Claude MPM Doctor Report\n")

        # Summary table
        print("## Summary\n")
        print("| Status | Count |")
        print("|--------|-------|")
        print(f"| ✅ OK | {summary.ok_count} |")
        print(f"| ⚠️  Warning | {summary.warning_count} |")
        print(f"| ❌ Error | {summary.error_count} |")
        print(f"| ⏭️  Skipped | {summary.skipped_count} |")
        print()

        # Detailed results
        print("## Diagnostic Results\n")

        for result in summary.results:
            symbol = self.STATUS_SYMBOLS.get(result.status, "?")
            print(f"### {symbol} {result.category}\n")
            print(f"**Status:** {result.status.value}")
            print(f"**Message:** {result.message}\n")

            if result.fix_command:
                print(f"**Fix:** `{result.fix_command}`")
                if result.fix_description:
                    print(f"_{result.fix_description}_\n")

            if self.verbose and result.details:
                print("**Details:**")
                for key, value in result.details.items():
                    print(f"- {key}: {value}")
                print()

        # Fixes section
        fixes = [
            (r.category, r.fix_command, r.fix_description)
            for r in summary.results
            if r.fix_command and r.has_issues
        ]

        if fixes:
            print("## Suggested Fixes\n")
            for category, command, description in fixes:
                print(f"- **{category}:** `{command}`")
                if description:
                    print(f"  - {description}")
            print()

    def _color(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_color:
            return text

        color_code = self.COLORS.get(color, "")
        reset_code = self.COLORS["reset"]
        return f"{color_code}{text}{reset_code}"

    def _get_status_color(self, status: DiagnosticStatus) -> str:
        """Get color for a status."""
        color_map = {
            DiagnosticStatus.OK: "green",
            DiagnosticStatus.WARNING: "yellow",
            DiagnosticStatus.ERROR: "red",
            DiagnosticStatus.SKIPPED: "gray",
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
