"""
Display Helper for Rich Console Output.

WHY: Centralizes display formatting logic to reduce code duplication
across CLI commands. Provides reusable components for tables, panels,
reports, and structured output.
"""

from typing import Any, Dict, List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class DisplayHelper:
    """Centralized display formatting for Rich console output."""

    def __init__(self, console: Console):
        """Initialize display helper with console instance."""
        self.console = console

    def display_separator(self, char: str = "=", width: int = 60) -> None:
        """Display a separator line."""
        self.console.print(char * width)

    def display_header(self, title: str, width: int = 60) -> None:
        """Display a formatted header with separators."""
        self.display_separator(width=width)
        self.console.print(f"[bold]{title}[/bold]")
        self.display_separator(width=width)
        self.console.print()

    def display_section_title(self, title: str, emoji: str = "") -> None:
        """Display a section title with optional emoji."""
        if emoji:
            self.console.print(f"[bold cyan]{emoji} {title}[/bold cyan]")
        else:
            self.console.print(f"[bold cyan]{title}[/bold cyan]")

    def display_key_value_table(
        self,
        title: str,
        data: Dict[str, Any],
        key_style: str = "cyan",
        value_style: str = "white",
    ) -> None:
        """Display a two-column key-value table."""
        table = Table(title=title, show_header=True)
        table.add_column("Property", style=key_style)
        table.add_column("Value", style=value_style)

        for key, value in data.items():
            # Handle various value types
            if isinstance(value, bool):
                display_value = "✓" if value else "✗"
            elif isinstance(value, int) and key.lower().find("size") >= 0:
                display_value = f"{value:,} characters"
            else:
                display_value = str(value)
            table.add_row(key, display_value)

        self.console.print(table)

    def display_list_section(
        self, title: str, items: List[str], max_items: int = 10, color: str = "white"
    ) -> None:
        """Display a titled list of items."""
        self.console.print(f"\n[bold cyan]{title}[/bold cyan]")
        for item in items[:max_items]:
            self.console.print(f"  [{color}]{item}[/{color}]")

    def display_warning_list(self, title: str, items: List[str]) -> None:
        """Display a list of warning items."""
        self.console.print(f"\n[yellow]{title}[/yellow]")
        for item in items:
            self.console.print(f"  • {item}")

    def display_info_list(self, title: str, items: List[str]) -> None:
        """Display a list of info items."""
        self.console.print(f"\n[blue]{title}[/blue]")
        for item in items[:5]:
            self.console.print(f"  • {item}")

    def display_metric_row(
        self, label: str, value: Any, indent: int = 2, warning: bool = False
    ) -> None:
        """Display a single metric row with label and value."""
        indent_str = " " * indent
        if warning:
            self.console.print(f"{indent_str}[yellow]{label}: {value}[/yellow]")
        else:
            self.console.print(f"{indent_str}{label}: {value}")

    def display_metrics_section(
        self, title: str, metrics: Dict[str, Any], emoji: str = ""
    ) -> None:
        """Display a section with multiple metrics."""
        self.display_section_title(title, emoji)
        for label, value in metrics.items():
            self.display_metric_row(label, value)

    def display_report_section(
        self,
        title: str,
        data: Dict[str, Any],
        emoji: str = "",
        show_warnings: bool = True,
    ) -> None:
        """Display a generic report section with data and optional warnings."""
        self.display_section_title(title, emoji)

        for key, value in data.items():
            if isinstance(value, dict):
                # Handle nested dictionaries
                self.console.print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    self.console.print(f"    {sub_key}: {sub_value}")
            elif isinstance(value, list):
                # Handle lists
                self.console.print(f"  {key}:")
                for item in value[:5]:  # Limit to first 5 items
                    if isinstance(item, dict):
                        # Handle dict items in list
                        desc = item.get("description") or str(item)
                        prefix = "⚠️  " if show_warnings else "•"
                        self.console.print(f"    {prefix} {desc}")
                    else:
                        self.console.print(f"    • {item}")
            else:
                # Simple key-value
                self.console.print(f"  {key}: {value}")

    def display_recommendations(self, recommendations: List[str]) -> None:
        """Display a recommendations section."""
        if recommendations:
            self.display_section_title("💡 Recommendations")
            for rec in recommendations[:5]:
                self.console.print(f"  → {rec}")

    def display_documentation_status(
        self, analysis: Dict, title: str = "Current CLAUDE.md Status"
    ) -> None:
        """Display documentation status table."""
        data = {
            "Size": analysis.get("size", 0),
            "Lines": analysis.get("lines", 0),
            "Sections": len(analysis.get("sections", [])),
            "Has Priority Index": analysis.get("has_priority_index", False),
            "Has Priority Markers": analysis.get("has_priority_markers", False),
        }

        if analysis.get("last_modified"):
            data["Last Modified"] = analysis["last_modified"]

        self.display_key_value_table(title, data)

        # Display warnings if present
        if analysis.get("outdated_patterns"):
            self.display_warning_list(
                "⚠️  Outdated patterns detected:", analysis["outdated_patterns"]
            )

        # Display custom sections if present
        if analysis.get("custom_sections"):
            self.display_info_list(
                "[INFO]️  Custom sections found:", analysis["custom_sections"]
            )

    def display_activity_summary(
        self, summary: Dict, period: str = "Last 30 days"
    ) -> None:
        """Display activity summary metrics."""
        metrics = {
            "Total commits": summary.get("total_commits", 0),
            "Active contributors": summary.get("total_authors", 0),
            "Files modified": summary.get("files_changed", 0),
            "Current branch": summary.get("current_branch", "unknown"),
        }

        self.display_metrics_section(
            f"📊 Activity Overview ({period.lower()})", metrics
        )

        if summary.get("has_uncommitted"):
            self.display_metric_row(
                "⚠️  Uncommitted changes",
                f"{summary.get('uncommitted_count', 0)} files",
                warning=True,
            )

    def display_commit_list(
        self, commits: List[Dict], title: str = "📝 Recent Commits (last 10)"
    ) -> None:
        """Display a list of commits."""
        if commits:
            self.display_section_title(title)
            for commit in commits[:10]:
                msg = commit.get("message", "")[:60]
                hash_val = commit.get("hash", "")
                author = commit.get("author", "")
                self.console.print(f"  [{hash_val}] {msg} - {author}")

    def display_file_change_list(
        self, files: List[Tuple[str, int]], title: str = "🔥 Most Changed Files"
    ) -> None:
        """Display a list of changed files with change counts."""
        if files:
            self.display_section_title(title)
            for file_path, changes in files[:10]:
                self.console.print(f"  {file_path}: {changes} changes")

    def display_branch_list(
        self,
        branches: List[str],
        current_branch: str,
        title: str = "🌿 Active Branches",
    ) -> None:
        """Display a list of branches with current branch marked."""
        if branches:
            self.display_section_title(title)
            for branch in branches:
                marker = "→" if branch == current_branch else " "
                self.console.print(f"  {marker} {branch}")

    def display_success_panel(
        self,
        title: str,
        content: str,
        border_style: str = "green",
    ) -> None:
        """Display a success panel with content."""
        self.console.print(Panel(content, title=title, border_style=border_style))

    def display_info_panel(
        self,
        title: str,
        content: str,
        border_style: str = "cyan",
    ) -> None:
        """Display an info panel with content."""
        self.console.print(Panel(content, title=title, border_style=border_style))

    def display_files_list(
        self, title: str, files: List[str], prefix: str = "•"
    ) -> None:
        """Display a list of files."""
        if files:
            self.console.print(f"[bold]{title}[/bold]")
            for file in files:
                self.console.print(f"  {prefix} {file}")
            self.console.print()

    def display_next_steps(self, steps: List[str]) -> None:
        """Display next steps list."""
        if steps:
            self.console.print("[bold]Next Steps:[/bold]")
            for step in steps:
                self.console.print(f"  → {step}")
            self.console.print()
