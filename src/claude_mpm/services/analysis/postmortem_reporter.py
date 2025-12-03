#!/usr/bin/env python3
"""
Postmortem Reporter
===================

Formats postmortem analysis reports in various output formats (terminal, JSON, markdown).

WHY: Different consumption contexts require different formats. Terminal output
needs to be concise and visually organized, JSON is for machine processing,
and markdown is for documentation.

DESIGN DECISION: Follows the same pattern as DoctorReporter for consistency.
"""

import json
import sys
from typing import Optional, TextIO

from claude_mpm.core.logging_utils import get_logger

from .postmortem_service import (
    ActionType,
    ErrorAnalysis,
    ErrorCategory,
    ImprovementAction,
    PostmortemReport,
)

logger = get_logger(__name__)


class PostmortemReporter:
    """Reporter for postmortem analysis results.

    WHY: Provides consistent, well-formatted output across different formats
    with color support and clear visual hierarchy.
    """

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
    }

    # Emoji/symbol mapping
    SYMBOLS = {
        "error": "❌",
        "success": "✓",
        "warning": "⚠️",
        "info": "ℹ️",
        "script": "🔧",
        "skill": "📚",
        "agent": "🤖",
        "user": "💡",
        "chart": "📊",
        "summary": "📈",
    }

    def __init__(
        self,
        use_color: bool = True,
        verbose: bool = False,
        output: Optional[TextIO] = None,
    ):
        """Initialize reporter.

        Args:
            use_color: Enable colored output
            verbose: Include detailed information
            output: Output stream (defaults to stdout)
        """
        self.use_color = use_color and sys.stdout.isatty()
        self.verbose = verbose
        self.output = output or sys.stdout

    def report(self, report: PostmortemReport, format: str = "terminal") -> None:
        """Generate report in specified format.

        Args:
            report: Postmortem report to format
            format: Output format (terminal/json/markdown)
        """
        if format == "json":
            self._report_json(report)
        elif format == "markdown":
            self._report_markdown(report)
        else:
            self._report_terminal(report)

    def _report_terminal(self, report: PostmortemReport) -> None:
        """Generate terminal-formatted report.

        Args:
            report: Postmortem report
        """
        # Header
        self._print_header(report)

        # Error breakdown by category
        self._print_error_categories(report)

        # Actions by type
        self._print_actions(report)

        # Summary
        self._print_summary(report)

    def _print_header(self, report: PostmortemReport) -> None:
        """Print report header.

        Args:
            report: Postmortem report
        """
        self._print_colored(
            f"\n{self.SYMBOLS['chart']} Session Postmortem Analysis",
            "bold",
        )
        self._print("═" * 50)
        self._print()

        # Session info
        self._print(f"Session: {report.session_id}")

        # Duration
        minutes = int(report.duration_seconds // 60)
        seconds = int(report.duration_seconds % 60)
        duration_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
        if seconds > 0:
            duration_str += f", {seconds} second{'s' if seconds != 1 else ''}"
        self._print(f"Duration: {duration_str}")

        # Error count with color
        error_color = "red" if report.total_errors > 0 else "green"
        self._print_colored(
            f"Errors Found: {report.total_errors}",
            error_color if report.total_errors > 0 else "green",
        )
        self._print()

    def _print_error_categories(self, report: PostmortemReport) -> None:
        """Print errors grouped by category.

        Args:
            report: Postmortem report
        """
        categories = [
            (ErrorCategory.SCRIPT, "script", "Script Errors"),
            (ErrorCategory.SKILL, "skill", "Skill Errors"),
            (ErrorCategory.AGENT, "agent", "Agent Improvements"),
            (ErrorCategory.USER_CODE, "user", "User Code Suggestions"),
        ]

        for category, symbol_key, title in categories:
            analyses = report.get_analyses_by_category(category)
            count = len(analyses)

            # Section header
            self._print_colored(
                f"{self.SYMBOLS[symbol_key]} {title} ({count})",
                "bold",
            )
            self._print("─" * 50)

            if count == 0:
                self._print_colored("No issues detected\n", "green")
                continue

            # Print each error
            for i, analysis in enumerate(analyses, 1):
                self._print_error_analysis(analysis, i)

            self._print()

    def _print_error_analysis(self, analysis: ErrorAnalysis, index: int) -> None:
        """Print single error analysis.

        Args:
            analysis: Error analysis
            index: Error index number
        """
        # Error header with file
        file_str = str(analysis.affected_file) if analysis.affected_file else "Unknown"
        self._print(f"{index}. {file_str}")

        # Root cause
        self._print(f"   Root Cause: {analysis.root_cause}")

        # Fix suggestion
        self._print(f"   Fix: {analysis.fix_suggestion}")

        # Priority indicator
        priority_colors = {
            "critical": "red",
            "high": "yellow",
            "medium": "cyan",
            "low": "reset",
        }
        priority_color = priority_colors.get(analysis.priority, "reset")
        self._print_colored(f"   Priority: {analysis.priority}", priority_color)

        # Status
        if analysis.failure_event.fixed:
            self._print_colored(f"   Status: Fixed {self.SYMBOLS['success']}", "green")
        else:
            self._print("   Status: Unfixed")

        # Verbose details
        if self.verbose:
            self._print(
                f"   Error Type: {analysis.metadata.get('error_type', 'unknown')}"
            )
            self._print(f"   Tool: {analysis.metadata.get('tool', 'unknown')}")

        self._print()

    def _print_actions(self, report: PostmortemReport) -> None:
        """Print improvement actions grouped by type.

        Args:
            report: Postmortem report
        """
        self._print_colored(
            f"{self.SYMBOLS['info']} Improvement Actions",
            "bold",
        )
        self._print("═" * 50)
        self._print()

        # Group actions by type
        action_groups = [
            (ActionType.AUTO_FIX, "Auto-Fix Actions"),
            (ActionType.UPDATE_FILE, "File Update Actions"),
            (ActionType.CREATE_PR, "PR Creation Actions"),
            (ActionType.SUGGEST, "Suggestions"),
        ]

        for action_type, title in action_groups:
            actions = report.get_actions_by_type(action_type)
            if not actions:
                continue

            self._print_colored(f"{title} ({len(actions)})", "cyan")
            self._print()

            for i, action in enumerate(actions, 1):
                self._print_action(action, i)

            self._print()

    def _print_action(self, action: ImprovementAction, index: int) -> None:
        """Print single improvement action.

        Args:
            action: Improvement action
            index: Action index number
        """
        # Status indicator
        status_indicators = {
            "pending": f"{self.SYMBOLS['info']} Pending",
            "completed": f"{self.SYMBOLS['success']} Completed",
            "failed": f"{self.SYMBOLS['error']} Failed",
        }
        status_str = status_indicators.get(action.status, action.status)

        self._print(f"{index}. {action.description}")
        self._print(f"   Status: {status_str}")

        # Action-specific details
        if action.action_type == ActionType.AUTO_FIX and action.commands:
            self._print("   Commands:")
            for cmd in action.commands:
                self._print(f"     • {cmd}")

        if action.action_type == ActionType.CREATE_PR:
            if action.pr_branch:
                self._print(f"   Branch: {action.pr_branch}")
            if self.verbose and action.pr_title:
                self._print(f"   PR Title: {action.pr_title}")

        if action.error_message:
            self._print_colored(f"   Error: {action.error_message}", "red")

        self._print()

    def _print_summary(self, report: PostmortemReport) -> None:
        """Print summary statistics.

        Args:
            report: Postmortem report
        """
        self._print_colored(
            f"{self.SYMBOLS['summary']} Summary",
            "bold",
        )
        self._print("─" * 50)

        stats = report.stats

        # Error breakdown
        self._print(f"Total Errors: {stats['total_errors']}")
        self._print(f"  • Script Errors: {stats['script_errors']}")
        self._print(f"  • Skill Errors: {stats['skill_errors']}")
        self._print(f"  • Agent Issues: {stats['agent_errors']}")
        self._print(f"  • User Code Issues: {stats['user_code_errors']}")
        self._print()

        # Priority breakdown
        self._print("Priority Breakdown:")
        self._print_colored(f"  • Critical: {stats['critical_priority']}", "red")
        self._print_colored(f"  • High: {stats['high_priority']}", "yellow")
        self._print()

        # Actions
        self._print(f"Total Actions: {stats['total_actions']}")
        self._print(f"  • Auto-fixable: {stats['auto_fixable']}")
        self._print(f"  • PR Actions: {stats['pr_actions']}")
        self._print()

    def _report_json(self, report: PostmortemReport) -> None:
        """Generate JSON-formatted report.

        Args:
            report: Postmortem report
        """
        # Convert report to dict
        report_dict = {
            "session_id": report.session_id,
            "start_time": report.start_time.isoformat(),
            "duration_seconds": report.duration_seconds,
            "total_errors": report.total_errors,
            "stats": report.stats,
            "analyses": [
                {
                    "category": a.category.value,
                    "root_cause": a.root_cause,
                    "affected_file": str(a.affected_file) if a.affected_file else None,
                    "action_type": a.action_type.value,
                    "fix_suggestion": a.fix_suggestion,
                    "priority": a.priority,
                    "auto_fixable": a.auto_fixable,
                    "fixed": a.failure_event.fixed,
                    "error_message": a.failure_event.error_message,
                    "metadata": a.metadata,
                }
                for a in report.analyses
            ],
            "actions": [
                {
                    "action_type": a.action_type.value,
                    "description": a.description,
                    "status": a.status,
                    "commands": a.commands,
                    "pr_branch": a.pr_branch,
                    "pr_title": a.pr_title,
                    "error_message": a.error_message,
                }
                for a in report.actions
            ],
        }

        json.dump(report_dict, self.output, indent=2)
        self.output.write("\n")

    def _report_markdown(self, report: PostmortemReport) -> None:
        """Generate markdown-formatted report.

        Args:
            report: Postmortem report
        """
        # Header
        self._print("# Session Postmortem Analysis\n")
        self._print(f"**Session:** {report.session_id}  ")

        minutes = int(report.duration_seconds // 60)
        self._print(f"**Duration:** {minutes} minutes  ")
        self._print(f"**Errors Found:** {report.total_errors}\n")

        # Error categories
        self._print("## Error Analysis\n")

        categories = [
            (ErrorCategory.SCRIPT, "Script Errors"),
            (ErrorCategory.SKILL, "Skill Errors"),
            (ErrorCategory.AGENT, "Agent Improvements"),
            (ErrorCategory.USER_CODE, "User Code Suggestions"),
        ]

        for category, title in categories:
            analyses = report.get_analyses_by_category(category)
            self._print(f"### {title} ({len(analyses)})\n")

            if not analyses:
                self._print("No issues detected.\n")
                continue

            for i, analysis in enumerate(analyses, 1):
                self._print(f"{i}. **{analysis.affected_file or 'Unknown'}**")
                self._print(f"   - **Root Cause:** {analysis.root_cause}")
                self._print(f"   - **Fix:** {analysis.fix_suggestion}")
                self._print(f"   - **Priority:** {analysis.priority}")
                status = "Fixed ✓" if analysis.failure_event.fixed else "Unfixed"
                self._print(f"   - **Status:** {status}\n")

        # Actions
        self._print("## Improvement Actions\n")

        action_groups = [
            (ActionType.AUTO_FIX, "Auto-Fix Actions"),
            (ActionType.UPDATE_FILE, "File Update Actions"),
            (ActionType.CREATE_PR, "PR Creation Actions"),
            (ActionType.SUGGEST, "Suggestions"),
        ]

        for action_type, title in action_groups:
            actions = report.get_actions_by_type(action_type)
            if not actions:
                continue

            self._print(f"### {title} ({len(actions)})\n")

            for i, action in enumerate(actions, 1):
                self._print(f"{i}. {action.description}")
                self._print(f"   - **Status:** {action.status}")

                if action.commands:
                    self._print("   - **Commands:**")
                    for cmd in action.commands:
                        self._print(f"     - `{cmd}`")

                if action.pr_branch:
                    self._print(f"   - **Branch:** `{action.pr_branch}`")

                self._print()

        # Summary
        self._print("## Summary\n")
        stats = report.stats

        self._print(f"- **Total Errors:** {stats['total_errors']}")
        self._print(f"  - Script Errors: {stats['script_errors']}")
        self._print(f"  - Skill Errors: {stats['skill_errors']}")
        self._print(f"  - Agent Issues: {stats['agent_errors']}")
        self._print(f"  - User Code Issues: {stats['user_code_errors']}")
        self._print(f"- **Critical Priority:** {stats['critical_priority']}")
        self._print(f"- **High Priority:** {stats['high_priority']}")
        self._print(f"- **Total Actions:** {stats['total_actions']}")
        self._print(f"- **Auto-fixable:** {stats['auto_fixable']}")
        self._print(f"- **PR Actions:** {stats['pr_actions']}\n")

    def _print(self, text: str = "") -> None:
        """Print text to output.

        Args:
            text: Text to print
        """
        print(text, file=self.output)

    def _print_colored(self, text: str, color: str) -> None:
        """Print colored text (if colors enabled).

        Args:
            text: Text to print
            color: Color name
        """
        if self.use_color and color in self.COLORS:
            print(f"{self.COLORS[color]}{text}{self.COLORS['reset']}", file=self.output)
        else:
            print(text, file=self.output)
