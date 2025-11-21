"""Git analysis and activity tracking functions.

This module provides utilities for analyzing git repository activity,
including commit analysis, file change tracking, and contributor statistics.
"""

import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from claude_mpm.core.enums import OperationResult

from . import prompts

console = Console()

__all__ = [
    "append_activity_notes",
    "catchup",
    "export_activity_report",
    "generate_activity_report",
    "handle_context",
]


def catchup(project_path: Path) -> Dict[str, Any]:
    """Get recent commit history for PM context.

    Args:
        project_path: Path to the project directory

    Returns:
        Dict containing commit history and contributor stats
    """
    try:
        # Get last 25 commits from all branches with author info
        result = subprocess.run(
            ["git", "log", "--all", "--format=%h|%an|%ai|%s", "-25"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(project_path),
        )

        commits = []
        authors = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|", 3)
            if len(parts) == 4:
                hash_val, author, date_str, message = parts

                # Parse date
                try:
                    dt = datetime.fromisoformat(date_str.replace(" ", "T", 1))
                    date_display = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_display = date_str[:16]

                commits.append(
                    {
                        "hash": hash_val,
                        "author": author,
                        "date": date_display,
                        "message": message,
                    }
                )
                authors.append(author)

        # Calculate contributor stats
        author_counts = Counter(authors)

        return {
            "commits": commits,
            "total_commits": len(commits),
            "contributors": dict(author_counts),
            "contributor_count": len(author_counts),
        }

    except Exception as e:
        console.print(f"[yellow]Could not retrieve commit history: {e}[/yellow]")
        return {
            "commits": [],
            "total_commits": 0,
            "contributors": {},
            "contributor_count": 0,
            "error": str(e),
        }


def generate_activity_report(
    git_analysis: Dict, doc_analysis: Dict, days: int = 30
) -> Dict:
    """Generate activity report from git analysis and documentation status.

    Args:
        git_analysis: Git repository analysis data
        doc_analysis: Documentation analysis data
        days: Number of days to analyze (default: 30)

    Returns:
        Dict containing comprehensive activity report
    """
    report = {
        "period": f"Last {days} days",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {},
        "recommendations": [],
    }

    # Git activity summary
    if git_analysis.get("git_available"):
        recent_commits = git_analysis.get("recent_commits", [])
        changed_files = git_analysis.get("changed_files", {})
        authors = git_analysis.get("authors", {})
        branch_info = git_analysis.get("branch_info", {})

        report["summary"] = {
            "total_commits": len(recent_commits),
            "total_authors": authors.get("total_authors", 0),
            "files_changed": changed_files.get("total_files", 0),
            "current_branch": branch_info.get("current_branch", "unknown"),
            "has_uncommitted": branch_info.get("has_uncommitted_changes", False),
            "uncommitted_count": branch_info.get("uncommitted_files", 0),
        }

        # Recent commits (last 10)
        report["recent_commits"] = recent_commits[:10]

        # Most changed files
        most_changed = changed_files.get("most_changed", {})
        report["hot_files"] = list(most_changed.items())[:10]

        # Active branches
        branches = branch_info.get("branches", [])
        report["active_branches"] = [
            b for b in branches if not b.startswith("remotes/")
        ][:5]

        # Generate recommendations
        if len(recent_commits) > 20:
            report["recommendations"].append(
                "High activity detected - consider updating architecture docs"
            )

        if changed_files.get("total_files", 0) > 50:
            report["recommendations"].append(
                "Many files changed - review CLAUDE.md for accuracy"
            )

        if branch_info.get("has_uncommitted_changes"):
            report["recommendations"].append(
                "Uncommitted changes detected - commit before updating docs"
            )

        # Check for documentation changes
        doc_changes = git_analysis.get("documentation_changes", {})
        if not doc_changes.get("has_recent_doc_changes"):
            report["recommendations"].append(
                "No recent doc updates - CLAUDE.md may be outdated"
            )

    # Documentation freshness
    if doc_analysis.get("exists"):
        report["doc_status"] = {
            "size": doc_analysis.get("size", 0),
            "lines": doc_analysis.get("lines", 0),
            "has_priority_index": doc_analysis.get("has_priority_index", False),
            "has_priority_markers": doc_analysis.get("has_priority_markers", False),
            "last_modified": doc_analysis.get("last_modified", "unknown"),
        }

        if not doc_analysis.get("has_priority_markers"):
            report["recommendations"].append(
                "Add priority markers (🔴🟡🟢⚪) to CLAUDE.md"
            )

    return report


def export_activity_report(project_path: Path, report: Dict, export_path: str) -> Path:
    """Export activity report to a markdown file.

    Args:
        project_path: Path to the project directory
        report: Activity report data
        export_path: Path to export file ("auto" or specific path)

    Returns:
        Path to the exported file
    """
    # Determine export path
    if export_path == "auto":
        # Generate default path with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        reports_dir = project_path / "docs" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        file_path = reports_dir / f"activity-report-{timestamp}.md"
    else:
        # Use provided path
        file_path = Path(export_path)
        if not file_path.is_absolute():
            file_path = project_path / file_path
        # Create parent directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate markdown content
    summary = report.get("summary", {})
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    content = f"""# Activity Report

**Generated**: {timestamp}
**Analysis Period**: {report.get("period", "Last 30 days")}

## Summary

- **Total Commits**: {summary.get("total_commits", 0)}
- **Active Contributors**: {summary.get("total_authors", 0)}
- **Files Modified**: {summary.get("files_changed", 0)}
- **Current Branch**: {summary.get("current_branch", "unknown")}
"""

    if summary.get("has_uncommitted"):
        content += f"- **⚠️  Uncommitted Changes**: {summary.get('uncommitted_count', 0)} files\n"

    # Recent commits
    recent_commits = report.get("recent_commits", [])
    if recent_commits:
        content += "\n## Recent Commits\n\n"
        for commit in recent_commits[:10]:
            content += (
                f"- `{commit['hash']}` {commit['message']} - {commit['author']}\n"
            )

    # Hot files
    hot_files = report.get("hot_files", [])
    if hot_files:
        content += "\n## Most Changed Files\n\n"
        for hot_file_path, changes in hot_files[:10]:
            content += f"- `{hot_file_path}`: {changes} changes\n"

    # Active branches
    branches = report.get("active_branches", [])
    if branches:
        content += "\n## Active Branches\n\n"
        for branch in branches:
            marker = "→" if branch == summary.get("current_branch") else " "
            content += f"{marker} {branch}\n"

    # Documentation status
    doc_status = report.get("doc_status", {})
    if doc_status:
        content += "\n## CLAUDE.md Status\n\n"
        content += f"- **Size**: {doc_status.get('size', 0):,} characters\n"
        content += f"- **Lines**: {doc_status.get('lines', 0)}\n"
        content += f"- **Priority Markers**: {'✓' if doc_status.get('has_priority_markers') else '✗'}\n"
        content += (
            f"- **Last Modified**: {doc_status.get('last_modified', 'unknown')}\n"
        )

    # Recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        content += "\n## Recommendations\n\n"
        for rec in recommendations:
            content += f"- {rec}\n"

    content += (
        "\n---\n\n*Generated by Claude MPM `/mpm-init --quick-update --export`*\n"
    )

    # Write to file
    file_path.write_text(content, encoding="utf-8")

    return file_path


def append_activity_notes(claude_md_path: Path, report: Dict) -> None:
    """Append activity notes to CLAUDE.md.

    Args:
        claude_md_path: Path to CLAUDE.md file
        report: Activity report data
    """
    # Generate activity summary section
    summary = report.get("summary", {})
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    activity_section = f"""

---

## 📈 Recent Activity Summary

**Last Updated**: {timestamp}
**Analysis Period**: {report.get("period", "Last 30 days")}

### Activity Metrics
- **Commits**: {summary.get("total_commits", 0)}
- **Contributors**: {summary.get("total_authors", 0)}
- **Files Changed**: {summary.get("files_changed", 0)}
- **Current Branch**: {summary.get("current_branch", "unknown")}
"""

    if summary.get("has_uncommitted"):
        activity_section += f"- **⚠️  Uncommitted Changes**: {summary.get('uncommitted_count', 0)} files\n"

    # Add recent commits
    recent_commits = report.get("recent_commits", [])
    if recent_commits:
        activity_section += "\n### Recent Commits\n"
        for commit in recent_commits[:5]:
            activity_section += (
                f"- `{commit['hash']}` {commit['message'][:60]} ({commit['author']})\n"
            )

    # Add hot files
    hot_files = report.get("hot_files", [])
    if hot_files:
        activity_section += "\n### Most Active Files\n"
        for file_path, changes in hot_files[:5]:
            activity_section += f"- `{file_path}`: {changes} changes\n"

    # Add recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        activity_section += "\n### 💡 Recommendations\n"
        for rec in recommendations:
            activity_section += f"- {rec}\n"

    activity_section += "\n---\n"

    # Append to file
    with open(claude_md_path, "a", encoding="utf-8") as f:
        f.write(activity_section)


def handle_context(
    project_path: Path,
    session_id: Optional[str] = None,
    list_sessions: bool = False,
    days: int = 7,
) -> Dict[str, Any]:
    """Provide intelligent context for resuming work based on git history.

    Analyzes recent commits to identify:
    - Active work streams (what was being worked on)
    - Intent and motivation (why this work)
    - Risks and blockers
    - Recommended next actions

    This delegates to Research agent for deep analysis.

    Args:
        project_path: Path to the project directory
        session_id: Unused parameter (for compatibility)
        list_sessions: Unused parameter (for compatibility)
        days: Number of days of git history to analyze (default: 7)

    Returns:
        Dict containing context result
    """
    from claude_mpm.utils.git_analyzer import analyze_recent_activity

    # 1. Analyze git history with adaptive window
    console.print(f"\n🔍 Analyzing last {days} days of git history...\n")
    git_analysis = analyze_recent_activity(
        repo_path=str(project_path), days=days, max_commits=50, min_commits=25
    )

    # Show adaptive behavior to user
    if git_analysis.get("adaptive_mode"):
        console.print(
            f"[cyan]ℹ️  Note: Analyzed {git_analysis.get('actual_time_span', 'extended period')} "
            f"to get meaningful context[/cyan]"
        )
        if git_analysis.get("reason"):
            console.print(f"[dim]    Reason: {git_analysis['reason']}[/dim]\n")
        else:
            console.print()

    if git_analysis.get("error"):
        console.print(
            f"[yellow]⚠️  Could not analyze git history: {git_analysis['error']}[/yellow]"
        )
        console.print(
            "[dim]Ensure this is a git repository with commit history.[/dim]\n"
        )
        return {
            "status": OperationResult.ERROR,
            "message": git_analysis["error"],
        }

    if not git_analysis.get("has_activity"):
        console.print(
            f"[yellow]⚠️  No git activity found in the last {days} days.[/yellow]"
        )
        console.print("[dim]Try increasing the --days parameter.[/dim]\n")
        return {
            "status": OperationResult.ERROR,
            "message": f"No git activity in last {days} days",
        }

    # 2. Build Research delegation prompt
    research_prompt = prompts.build_research_context_prompt(git_analysis, days)

    # 3. Display prompt for PM to delegate
    console.print("\n" + "=" * 80)
    console.print("📋 DELEGATE TO RESEARCH AGENT:")
    console.print("=" * 80 + "\n")
    console.print(research_prompt)
    console.print("\n" + "=" * 80 + "\n")

    return {
        "status": OperationResult.CONTEXT_READY,
        "git_analysis": git_analysis,
        "research_prompt": research_prompt,
        "recommendation": "PM should delegate this prompt to Research agent",
    }
