"""Operation mode handlers (review, dry-run, quick-update).

This module provides handlers for different execution modes:
- Review mode: Display proposed changes without execution
- Dry-run mode: Simulate execution without making changes
- Quick-update mode: Fast incremental updates
- Prompt update action: Interactive prompt for update decisions
- Handle update post-processing: Post-update summary and archiving
"""

from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from claude_mpm.core.enums import OperationResult
from claude_mpm.services.project.archive_manager import ArchiveManager
from claude_mpm.services.project.documentation_manager import DocumentationManager
from claude_mpm.services.project.enhanced_analyzer import EnhancedProjectAnalyzer
from claude_mpm.services.project.project_organizer import ProjectOrganizer
from claude_mpm.utils.display_helper import DisplayHelper

# Import display and git_activity functions from sibling modules
from . import display, git_activity

__all__ = [
    "handle_update_post_processing",
    "prompt_update_action",
    "run_dry_run_mode",
    "run_quick_update_mode",
    "run_review_mode",
]


def prompt_update_action(console: Console) -> str:
    """
    Prompt user for update action when CLAUDE.md already exists.

    Args:
        console: Rich Console instance for displaying prompts

    Returns:
        Action string: "update", "recreate", "review", or "cancel"
    """
    console.print("\n[bold]How would you like to proceed?[/bold]\n")

    choices = {
        "1": ("update", "Update existing CLAUDE.md (preserves custom content)"),
        "2": ("recreate", "Recreate CLAUDE.md from scratch"),
        "3": ("review", "Review project state without changes"),
        "4": ("cancel", "Cancel operation"),
    }

    for key, (_, desc) in choices.items():
        console.print(f"  [{key}] {desc}")

    choice = Prompt.ask("\nSelect option", choices=list(choices.keys()), default="1")
    return choices[choice][0]


def run_review_mode(
    console: Console,
    display_helper: DisplayHelper,
    organizer: ProjectOrganizer,
    doc_manager: DocumentationManager,
    analyzer: EnhancedProjectAnalyzer,
) -> Dict[str, Any]:
    """
    Run review mode to analyze project without changes.

    Args:
        console: Rich Console instance for output
        display_helper: DisplayHelper for formatted displays
        organizer: ProjectOrganizer service instance
        doc_manager: DocumentationManager service instance
        analyzer: EnhancedProjectAnalyzer service instance

    Returns:
        Dict containing review results with status, mode, and analysis data
    """
    console.print("\n[bold cyan]🔍 Project Review Mode[/bold cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Analyze project structure
        task = progress.add_task("[cyan]Analyzing project structure...", total=None)
        structure_report = organizer.verify_structure()
        progress.update(task, description="[green]✓ Structure analysis complete")

        # Analyze documentation
        task = progress.add_task("[cyan]Analyzing documentation...", total=None)
        doc_analysis = doc_manager.analyze_existing_content()
        progress.update(task, description="[green]✓ Documentation analysis complete")

        # Analyze git history
        if analyzer.is_git_repo:
            task = progress.add_task("[cyan]Analyzing git history...", total=None)
            git_analysis = analyzer.analyze_git_history()
            progress.update(task, description="[green]✓ Git analysis complete")
        else:
            git_analysis = None

        # Detect project state
        task = progress.add_task("[cyan]Detecting project state...", total=None)
        project_state = analyzer.detect_project_state()
        progress.update(task, description="[green]✓ State detection complete")

    # Display comprehensive report
    display.display_review_report(
        display_helper,
        console,
        structure_report,
        doc_analysis,
        git_analysis,
        project_state,
    )

    return {
        "status": OperationResult.SUCCESS,
        "mode": "review",
        "structure_report": structure_report,
        "documentation_analysis": doc_analysis,
        "git_analysis": git_analysis,
        "project_state": project_state,
    }


def run_quick_update_mode(
    console: Console,
    display_helper: DisplayHelper,
    project_path: Path,
    analyzer: EnhancedProjectAnalyzer,
    doc_manager: DocumentationManager,
    archive_manager: ArchiveManager,
    days: int = 30,
    non_interactive: bool = False,
    export: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run quick update mode - lightweight update based on recent git activity.

    Args:
        console: Rich Console instance for output
        display_helper: DisplayHelper for formatted displays
        project_path: Path to the project directory
        analyzer: EnhancedProjectAnalyzer service instance
        doc_manager: DocumentationManager service instance
        archive_manager: ArchiveManager service instance
        days: Number of days of git history to analyze
        non_interactive: If True, display report only without prompting
        export: Path to export report (or "auto" for default location)

    Returns:
        Dict containing quick update results with status, mode, and activity report
    """
    console.print("\n[bold cyan]⚡ Quick Update Mode[/bold cyan]\n")
    console.print(
        f"[dim]Analyzing recent git activity ({days} days) for lightweight documentation update...[/dim]\n"
    )

    if not analyzer.is_git_repo:
        console.print(
            "[yellow]⚠️  Not a git repository. Quick update requires git.[/yellow]"
        )
        console.print(
            "[dim]Tip: Use `/mpm-init --review` for non-git projects.[/dim]\n"
        )
        return {
            "status": OperationResult.ERROR,
            "message": "Quick update requires a git repository",
        }

    claude_md = project_path / "CLAUDE.md"
    if not claude_md.exists():
        console.print(
            "[yellow]⚠️  CLAUDE.md not found. Quick update requires existing documentation.[/yellow]"
        )
        console.print(
            "[dim]Tip: Use `/mpm-init` to create initial documentation.[/dim]\n"
        )
        return {
            "status": OperationResult.ERROR,
            "message": "Quick update requires existing CLAUDE.md",
        }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Analyze git history
        task = progress.add_task(
            f"[cyan]Analyzing git history ({days} days)...", total=None
        )
        git_analysis = analyzer.analyze_git_history(days_back=days)
        progress.update(task, description="[green]✓ Git analysis complete")

        # Analyze current documentation
        task = progress.add_task("[cyan]Checking documentation status...", total=None)
        doc_analysis = doc_manager.analyze_existing_content()
        progress.update(task, description="[green]✓ Documentation analyzed")

    # Generate activity report
    activity_report = git_activity.generate_activity_report(
        git_analysis, doc_analysis, days
    )

    # Display the report
    display.display_activity_report(display_helper, activity_report)

    # Export report if requested
    if export:
        export_path = git_activity.export_activity_report(
            project_path, activity_report, export
        )
        console.print(f"\n[green]✅ Report exported to: {export_path}[/green]")

    # Handle non-interactive mode
    if non_interactive:
        console.print(
            "\n[cyan]ℹ️  Non-interactive mode: Report displayed, no changes made.[/cyan]"
        )
        return {
            "status": OperationResult.SUCCESS,
            "mode": "quick_update",
            "activity_report": activity_report,
            "changes_made": False,
            "non_interactive": True,
        }

    # Offer to append activity notes to CLAUDE.md
    console.print("\n[bold]Update Options:[/bold]")
    console.print("  [1] Append activity summary to CLAUDE.md")
    console.print("  [2] Display report only (no changes)")
    console.print("  [3] Cancel")

    choice = Prompt.ask("\nSelect option", choices=["1", "2", "3"], default="2")

    if choice == "1":
        # Append activity notes
        git_activity.append_activity_notes(claude_md, activity_report)
        console.print("\n[green]✅ Activity notes appended to CLAUDE.md[/green]")

        # Archive the update
        archive_manager.auto_archive_before_update(
            claude_md, update_reason="Quick update - recent activity summary"
        )

        return {
            "status": OperationResult.SUCCESS,
            "mode": "quick_update",
            "activity_report": activity_report,
            "changes_made": True,
        }
    if choice == "2":
        console.print("\n[cyan]Report generated - no changes made[/cyan]")
        return {
            "status": OperationResult.SUCCESS,
            "mode": "quick_update",
            "activity_report": activity_report,
            "changes_made": False,
        }
    console.print("\n[yellow]Quick update cancelled[/yellow]")
    return {
        "status": OperationResult.CANCELLED,
        "message": "Quick update cancelled",
    }


def run_dry_run_mode(
    console: Console,
    organizer: ProjectOrganizer,
    doc_manager: DocumentationManager,
    organize_files: bool,
    has_existing: bool,
) -> Dict[str, Any]:
    """
    Run dry-run mode to show what would be done without making changes.

    Args:
        console: Rich Console instance for output
        organizer: ProjectOrganizer service instance
        doc_manager: DocumentationManager service instance
        organize_files: Whether file organization would be performed
        has_existing: Whether CLAUDE.md already exists

    Returns:
        Dict containing dry-run results with status, mode, and planned actions
    """
    console.print("\n[bold cyan]🔍 Dry Run Mode - Preview Changes[/bold cyan]\n")

    actions_planned = []

    # Check what organization would do
    if organize_files:
        console.print("[bold]📁 File Organization Analysis:[/bold]")

        # Get structure validation without making changes
        validation = organizer.validate_structure()
        if validation.get("issues"):
            console.print("  [yellow]Files that would be organized:[/yellow]")
            for issue in validation["issues"][:10]:
                actions_planned.append(
                    f"Organize: {issue.get('description', 'Unknown')}"
                )
                console.print(f"    • {issue.get('description', 'Unknown')}")
        else:
            console.print("  ✅ Project structure is already well-organized")

    # Check what documentation updates would occur
    if has_existing:
        console.print("\n[bold]📚 Documentation Updates:[/bold]")
        doc_analysis = doc_manager.analyze_existing_content()

        if not doc_analysis.get("has_priority_markers"):
            actions_planned.append("Add priority markers (🔴🟡🟢⚪)")
            console.print("  • Add priority markers (🔴🟡🟢⚪)")

        if doc_analysis.get("outdated_patterns"):
            actions_planned.append("Update outdated patterns")
            console.print("  • Update outdated patterns")

        if not doc_analysis.get("has_priority_index"):
            actions_planned.append("Add priority index section")
            console.print("  • Add priority index section")

        # Archive would be created
        actions_planned.append("Archive current CLAUDE.md to docs/_archive/")
        console.print("  • Archive current CLAUDE.md to docs/_archive/")
    else:
        console.print("\n[bold]📚 Documentation Creation:[/bold]")
        actions_planned.append("Create new CLAUDE.md with priority structure")
        console.print("  • Create new CLAUDE.md with priority structure")

    # General improvements
    console.print("\n[bold]🔧 General Improvements:[/bold]")
    actions_planned.extend(
        [
            "Update/create .gitignore if needed",
            "Verify project structure compliance",
            "Add memory system initialization",
            "Set up single-path workflows",
        ]
    )
    for action in actions_planned[-4:]:
        console.print(f"  • {action}")

    console.print(
        f"\n[bold cyan]Summary: {len(actions_planned)} actions would be performed[/bold cyan]"
    )
    console.print("\n[dim]Run without --dry-run to execute these changes.[/dim]\n")

    return {
        "status": OperationResult.SUCCESS,
        "mode": "dry_run",
        "actions_planned": actions_planned,
        "message": "Dry run completed - no changes made",
    }


def handle_update_post_processing(
    console: Console,
    project_path: Path,
    doc_manager: DocumentationManager,
    archive_manager: ArchiveManager,
) -> None:
    """
    Handle post-processing after successful update.

    Generates and displays update summary comparing with archived version.

    Args:
        console: Rich Console instance for output
        project_path: Path to the project directory
        doc_manager: DocumentationManager service instance
        archive_manager: ArchiveManager service instance
    """
    # Generate update report
    if doc_manager.has_existing_documentation():
        latest_archive = archive_manager.get_latest_archive("CLAUDE.md")
        if latest_archive:
            comparison = archive_manager.compare_with_archive(
                project_path / "CLAUDE.md", latest_archive.name
            )

            if not comparison.get("identical"):
                console.print("\n[bold cyan]📊 Update Summary[/bold cyan]")
                console.print(f"  Lines changed: {comparison.get('lines_added', 0):+d}")
                console.print(
                    f"  Size change: {comparison.get('size_change', 0):+,} characters"
                )
                console.print(f"  Previous version: {latest_archive.name}")
