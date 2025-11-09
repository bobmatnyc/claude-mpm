"""
Display functions for MPM-Init command.

This module contains pure functions for displaying various reports and status
information. All functions accept DisplayHelper as a parameter and have no
side effects beyond console output.
"""

from typing import Any, Dict, Optional

from claude_mpm.utils.display_helper import DisplayHelper

__all__ = [
    "display_activity_report",
    "display_catchup",
    "display_documentation_status",
    "display_results",
    "display_review_report",
    "show_initialization_plan",
    "show_update_plan",
]


def display_documentation_status(
    display: DisplayHelper, analysis: Dict[str, Any]
) -> None:
    """
    Display current documentation status.

    Args:
        display: DisplayHelper instance for rendering
        analysis: Documentation analysis data from DocumentationManager
    """
    display.display_documentation_status(analysis)


def display_review_report(
    display: DisplayHelper,
    console: Any,
    structure: Dict[str, Any],
    docs: Dict[str, Any],
    git: Optional[Dict[str, Any]],
    state: Dict[str, Any],
) -> None:
    """
    Display comprehensive review report.

    Args:
        display: DisplayHelper instance for rendering
        console: Rich Console instance
        structure: Project structure report from ProjectOrganizer
        docs: Documentation analysis from DocumentationManager
        git: Git analysis from EnhancedProjectAnalyzer (optional)
        state: Project state from EnhancedProjectAnalyzer
    """
    display.display_header("PROJECT REVIEW REPORT")

    # Project State
    state_data = {"Phase": state.get("phase", "unknown")}
    if state.get("indicators"):
        state_data["Indicators"] = state["indicators"][:5]
    display.display_report_section("📊 Project State", state_data)

    # Structure Report
    structure_data = {
        "Existing directories": len(structure.get("exists", [])),
        "Missing directories": len(structure.get("missing", [])),
    }
    if structure.get("issues"):
        structure_data["Issues found"] = len(structure["issues"])
        structure_data["Issues"] = structure["issues"][:3]
    display.display_report_section("📁 Project Structure", structure_data)

    # Documentation Report
    display.display_section_title("📚 Documentation Status")
    if docs.get("exists"):
        console.print(f"  CLAUDE.md: Found ({docs.get('size', 0):,} chars)")
        console.print(f"  Sections: {len(docs.get('sections', []))}")
        console.print(
            f"  Priority markers: {'Yes' if docs.get('has_priority_markers') else 'No'}"
        )
    else:
        console.print("  CLAUDE.md: Not found")

    # Git Analysis
    if git and git.get("git_available"):
        git_metrics = {
            "Commits": len(git.get("recent_commits", [])),
            "Authors": git.get("authors", {}).get("total_authors", 0),
            "Changed files": git.get("changed_files", {}).get("total_files", 0),
        }

        if git.get("branch_info"):
            branch_info = git["branch_info"]
            git_metrics["Current branch"] = branch_info.get("current_branch", "unknown")

        display.display_metrics_section("📈 Recent Activity (30 days)", git_metrics)

        if git.get("branch_info", {}).get("has_uncommitted_changes"):
            display.display_metric_row(
                "⚠️  Uncommitted changes",
                f"{git['branch_info'].get('uncommitted_files', 0)} files",
                warning=True,
            )

    # Recommendations
    if state.get("recommendations"):
        display.display_recommendations(state["recommendations"])

    display.display_separator()


def display_catchup(display: DisplayHelper, console: Any, data: Dict[str, Any]) -> None:
    """
    Display catchup information to console.

    Args:
        display: DisplayHelper instance for rendering
        console: Rich Console instance
        data: Commit history data from _catchup()
    """
    from rich.panel import Panel
    from rich.table import Table

    if data.get("error"):
        console.print(
            Panel(
                "[yellow]Not a git repository or no commits found[/yellow]",
                title="⚠️ Catchup Status",
                border_style="yellow",
            )
        )
        return

    # Display contributor summary
    if data["contributors"]:
        console.print("\n[bold cyan]👥 Active Contributors[/bold cyan]")
        for author, count in sorted(
            data["contributors"].items(), key=lambda x: x[1], reverse=True
        ):
            console.print(
                f"  • [green]{author}[/green]: {count} commit{'s' if count != 1 else ''}"
            )

    # Display commit history table
    if data["commits"]:
        console.print(
            f"\n[bold cyan]📝 Last {data['total_commits']} Commits[/bold cyan]"
        )

        table = Table(show_header=True, header_style="bold magenta", border_style="dim")
        table.add_column("#", style="dim", width=3)
        table.add_column("Hash", style="yellow", width=8)
        table.add_column("Author", style="green", width=20)
        table.add_column("Date", style="cyan", width=16)
        table.add_column("Message", style="white")

        for idx, commit in enumerate(data["commits"], 1):
            # Truncate message if too long
            msg = commit["message"]
            if len(msg) > 80:
                msg = msg[:77] + "..."

            # Truncate author if too long
            author = commit["author"]
            if len(author) > 18:
                author = author[:18] + "..."

            table.add_row(str(idx), commit["hash"], author, commit["date"], msg)

        console.print(table)

    # Display PM recommendations
    console.print("\n[bold cyan]💡 PM Recommendations[/bold cyan]")
    console.print(
        f"  • Total activity: {data['total_commits']} commits from {data['contributor_count']} contributor{'s' if data['contributor_count'] != 1 else ''}"
    )
    console.print("  • Review commit messages for recent project context")
    console.print("  • Identify development patterns and focus areas")
    console.print("  • Use this context to inform current work priorities\n")


def display_activity_report(display: DisplayHelper, report: Dict[str, Any]) -> None:
    """
    Display the activity report in a formatted manner.

    Args:
        display: DisplayHelper instance for rendering
        report: Activity report data from _generate_activity_report()
    """
    display.display_header("RECENT ACTIVITY SUMMARY")

    summary = report.get("summary", {})
    period = report.get("period", "Last 30 days")

    # Summary statistics
    display.display_activity_summary(summary, period)

    # Recent commits
    recent_commits = report.get("recent_commits", [])
    if recent_commits:
        display.display_commit_list(recent_commits)

    # Hot files
    hot_files = report.get("hot_files", [])
    if hot_files:
        display.display_file_change_list(hot_files)

    # Active branches
    branches = report.get("active_branches", [])
    current_branch = summary.get("current_branch", "unknown")
    if branches:
        display.display_branch_list(branches, current_branch)

    # Documentation status
    doc_status = report.get("doc_status", {})
    if doc_status:
        doc_metrics = {
            "Size": f"{doc_status.get('size', 0):,} characters",
            "Lines": doc_status.get("lines", 0),
            "Priority markers": (
                "✓" if doc_status.get("has_priority_markers") else "✗"
            ),
            "Last modified": doc_status.get("last_modified", "unknown"),
        }
        display.display_metrics_section("📚 CLAUDE.md Status", doc_metrics)

    # Recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        display.display_recommendations(recommendations)

    display.display_separator()


def display_results(
    display: DisplayHelper, console: Any, result: Dict[str, Any], verbose: bool
) -> None:
    """
    Display initialization results.

    Args:
        display: DisplayHelper instance for rendering
        console: Rich Console instance
        result: Result dictionary from initialization process
        verbose: Whether to show verbose output
    """
    from claude_mpm.core.enums import OperationResult

    if result["status"] == OperationResult.SUCCESS:
        console.print("\n[green]✅ Project Initialization Complete![/green]\n")

        # Display files created
        if result.get("files_created"):
            display.display_files_list("Files Created:", result["files_created"])

        # Display files updated
        if result.get("files_updated"):
            display.display_files_list("Files Updated:", result["files_updated"])

        # Display next steps
        if result.get("next_steps"):
            display.display_next_steps(result["next_steps"])

        # Display success panel
        success_content = (
            "[green]Your project is now optimized for Claude Code and Claude MPM![/green]\n\n"
            "Key files:\n"
            "• [cyan]CLAUDE.md[/cyan] - Main documentation for AI agents\n"
            "  - Organized with priority rankings (🔴🟡🟢⚪)\n"
            "  - Instructions ranked by importance for AI understanding\n"
            "  - Holistic documentation review completed\n"
            "• [cyan].claude-mpm/[/cyan] - Configuration and memories\n"
            "• [cyan]CODE_STRUCTURE.md[/cyan] - AST-derived architecture documentation (if enabled)\n\n"
            "[dim]Run 'claude-mpm run' to start using the optimized setup[/dim]"
        )
        display.display_success_panel("Success", success_content)


def show_update_plan(console: Any, ast_analysis: bool, preserve_custom: bool) -> None:
    """
    Show update mode plan.

    Args:
        console: Rich Console instance
        ast_analysis: Whether AST analysis is enabled
        preserve_custom: Whether to preserve custom sections
    """
    from rich.panel import Panel

    console.print(
        Panel(
            "[bold cyan]🔄 Claude MPM Documentation Update[/bold cyan]\n\n"
            "This will update your existing CLAUDE.md with:\n"
            "• Smart merging of new and existing content\n"
            + ("• Preservation of custom sections\n" if preserve_custom else "")
            + "• Priority-based reorganization (🔴🟡🟢⚪)\n"
            "• Updated single-path workflows\n"
            "• Refreshed tool configurations\n"
            + ("• AST analysis for enhanced documentation\n" if ast_analysis else "")
            + "• Automatic archival of previous version\n"
            + "• Holistic review and optimization\n"
            + "\n[dim]Previous version will be archived in docs/_archive/[/dim]",
            title="Update Mode",
            border_style="blue",
        )
    )


def show_initialization_plan(console: Any, ast_analysis: bool) -> None:
    """
    Show standard initialization plan.

    Args:
        console: Rich Console instance
        ast_analysis: Whether AST analysis is enabled
    """
    from rich.panel import Panel

    console.print(
        Panel(
            "[bold cyan]🤖👥 Claude MPM Project Initialization[/bold cyan]\n\n"
            "This will set up your project with:\n"
            "• Clear CLAUDE.md documentation for AI agents\n"
            "• Single-path workflows (ONE way to do ANYTHING)\n"
            "• Optimized project structure\n"
            "• Tool configurations (linting, formatting, testing)\n"
            "• GitHub workflows and CI/CD setup\n"
            "• Memory system initialization\n"
            + (
                "• AST analysis for comprehensive code documentation\n"
                if ast_analysis
                else ""
            )
            + "• Holistic CLAUDE.md organization with ranked instructions\n"
            + "• Priority-based content structure (🔴🟡🟢⚪)\n"
            + "\n[dim]Powered by Agentic Coder Optimizer Agent[/dim]",
            title="MPM-Init",
            border_style="cyan",
        )
    )
