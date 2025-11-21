#!/usr/bin/env python3
"""
Test the Enhanced Archive Manager Documentation Review Features
===============================================================

This script demonstrates the enhanced ArchiveManager capabilities including:
- Documentation review with Git history analysis
- Outdated content detection
- README and CHANGELOG synchronization
- Intelligent archival with metadata

Usage:
    python scripts/test_archive_manager.py [command]

Commands:
    review     - Review all documentation for outdated content
    sync       - Sync versions between CLAUDE.md, README.md, and CHANGELOG.md
    auto       - Auto-detect and archive outdated documentation (dry run)
    archive    - Archive a specific file with metadata
    restore    - Restore from archive with change review
    report     - Generate comprehensive archive report
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from claude_mpm.services.project.archive_manager import ArchiveManager

console = Console()


def test_documentation_review(project_path: Path):
    """Test documentation review with Git history analysis."""
    console.print("\n[bold cyan]Testing Documentation Review[/bold cyan]\n")

    manager = ArchiveManager(project_path)

    # Perform comprehensive review
    console.print("[yellow]Reviewing documentation files...[/yellow]")
    review = manager.review_documentation(check_git=True)

    # Display formatted summary
    manager.display_review_summary(review)

    # Save review report
    report_file = project_path / "tmp" / "doc_review_report.json"
    report_file.parent.mkdir(exist_ok=True)
    report_file.write_text(json.dumps(review, indent=2))
    console.print(f"\n[green]Full report saved to: {report_file}[/green]")

    return review


def test_sync_documentation(project_path: Path):
    """Test synchronization between documentation files."""
    console.print("\n[bold cyan]Testing Documentation Synchronization[/bold cyan]\n")

    manager = ArchiveManager(project_path)

    # Check current state
    console.print("[yellow]Checking documentation synchronization...[/yellow]")
    review = manager.review_documentation(check_git=False)

    if review["synchronization_issues"]:
        console.print("\n[bold red]Synchronization Issues Found:[/bold red]")
        for issue in review["synchronization_issues"]:
            console.print(f"  • {issue['type']}: {issue['details']}")

        # Attempt sync
        console.print("\n[yellow]Attempting to sync documentation...[/yellow]")
        sync_result = manager.sync_with_readme_and_changelog()

        if sync_result["synced"]:
            console.print("\n[green]Synchronization successful:[/green]")
            for change in sync_result["changes"]:
                console.print(f"  ✓ {change}")
        else:
            console.print("[yellow]No synchronization needed.[/yellow]")

        if sync_result["errors"]:
            console.print("\n[red]Errors during sync:[/red]")
            for error in sync_result["errors"]:
                console.print(f"  ✗ {error}")
    else:
        console.print("[green]Documentation is already synchronized![/green]")


def test_auto_archive(project_path: Path, dry_run: bool = True):
    """Test auto-detection and archival of outdated documentation."""
    console.print("\n[bold cyan]Testing Auto-Archive Detection[/bold cyan]\n")

    manager = ArchiveManager(project_path)

    # Run auto-detection
    mode = "dry run" if dry_run else "live"
    console.print(f"[yellow]Running auto-detection ({mode})...[/yellow]")
    result = manager.auto_detect_and_archive_outdated(dry_run=dry_run)

    # Display results
    console.print(f"\n[cyan]Files reviewed: {len(result['reviewed_files'])}[/cyan]")

    if result["archived_files"]:
        console.print("\n[green]Files archived:[/green]")
        for item in result["archived_files"]:
            console.print(f"  • {item['file']}")
            for reason in item["reason"]:
                console.print(f"    - {reason}")

    if result["skipped_files"]:
        console.print("\n[yellow]Files that would be archived:[/yellow]")
        for item in result["skipped_files"]:
            console.print(f"  • {item['file']}")
            for reason in item["reason"]:
                console.print(f"    - {reason}")

    if not result["archived_files"] and not result["skipped_files"]:
        console.print("[green]No outdated documentation detected![/green]")


def test_archive_with_metadata(project_path: Path):
    """Test archiving a file with detailed metadata."""
    console.print("\n[bold cyan]Testing Archive with Metadata[/bold cyan]\n")

    manager = ArchiveManager(project_path)

    # Archive CLAUDE.md as example
    claude_path = project_path / "CLAUDE.md"
    if not claude_path.exists():
        console.print("[red]CLAUDE.md not found![/red]")
        return

    # Get Git history for the file
    git_history = manager.get_file_git_history(claude_path, limit=3)

    # Create detailed metadata
    metadata = {
        "test_archive": True,
        "git_history": git_history,
        "review_status": "Test archive for demonstration",
        "archive_type": "manual_test",
    }

    console.print("[yellow]Archiving CLAUDE.md with metadata...[/yellow]")
    archive_path = manager.archive_file(
        claude_path,
        reason="Test archive with enhanced metadata",
        metadata=metadata,
    )

    if archive_path:
        console.print(f"[green]✓ Archived to: {archive_path}[/green]")

        # Read and display metadata
        meta_file = Path(str(archive_path) + ".meta.json")
        if meta_file.exists():
            meta_data = json.loads(meta_file.read_text())
            console.print("\n[cyan]Archive Metadata:[/cyan]")
            console.print(
                Panel(Syntax(json.dumps(meta_data, indent=2), "json", theme="monokai"))
            )
    else:
        console.print("[red]Archive failed![/red]")


def test_restore_with_review(project_path: Path):
    """Test restoration from archive with change review."""
    console.print("\n[bold cyan]Testing Archive Restoration with Review[/bold cyan]\n")

    manager = ArchiveManager(project_path)

    # List available archives
    archives = manager.list_archives("CLAUDE.md", include_metadata=True)

    if not archives:
        console.print("[yellow]No archives found for CLAUDE.md[/yellow]")
        return

    console.print("[cyan]Available archives:[/cyan]")
    for i, archive in enumerate(archives[:5], 1):
        console.print(f"  {i}. {archive['name']} ({archive['modified']})")
        if archive.get("metadata") and archive["metadata"].get("reason"):
            console.print(f"     Reason: {archive['metadata']['reason']}")

    # Use the most recent archive for restoration demo
    latest_archive = archives[0]["name"]

    console.print(f"\n[yellow]Generating diff for: {latest_archive}[/yellow]")
    diff_report = manager.generate_documentation_diff_report(
        project_path / "CLAUDE.md",
        manager.archive_path / latest_archive,
    )

    if diff_report.startswith("Error"):
        console.print(f"[red]{diff_report}[/red]")
    else:
        # Display diff summary
        diff_lines = diff_report.splitlines()
        additions = len([l for l in diff_lines if l.startswith("+")])
        deletions = len([l for l in diff_lines if l.startswith("-")])

        console.print(f"[green]+ {additions} additions[/green]")
        console.print(f"[red]- {deletions} deletions[/red]")

        # Show first few lines of diff
        if diff_lines:
            console.print("\n[cyan]Diff preview (first 20 lines):[/cyan]")
            for line in diff_lines[:20]:
                if line.startswith("+"):
                    console.print(f"[green]{line}[/green]")
                elif line.startswith("-"):
                    console.print(f"[red]{line}[/red]")
                else:
                    console.print(line)


def test_comprehensive_report(project_path: Path):
    """Generate comprehensive archive report."""
    console.print("\n[bold cyan]Generating Comprehensive Archive Report[/bold cyan]\n")

    manager = ArchiveManager(project_path)

    # Generate report
    report = manager.create_archive_report()

    console.print(
        Panel.fit(
            f"""[bold]Archive Statistics[/bold]

📁 Archive Directory: {report["archive_directory"]}
📊 Total Archives: {report["total_archives"]}
💾 Total Size: {report["total_size"]:,} bytes
🗜️ Compressed: {report["compressed_count"]}
📅 Oldest: {report["oldest_archive"] or "None"}
🆕 Newest: {report["newest_archive"] or "None"}
""",
            title="Archive Summary",
            border_style="cyan",
        )
    )

    if report["files_tracked"]:
        console.print("\n[cyan]Files Being Tracked:[/cyan]")
        for filename, info in report["files_tracked"].items():
            console.print(f"  • {filename}")
            console.print(
                f"    Versions: {info['count']}, Size: {info['total_size']:,} bytes"
            )


def main():
    """Main test runner."""
    project_path = Path.cwd()

    # Check if we're in a git repo
    if not (project_path / ".git").exists():
        console.print(
            "[red]Warning: Not in a git repository. Git features will be limited.[/red]"
        )

    # Parse command
    command = sys.argv[1] if len(sys.argv) > 1 else "review"

    commands = {
        "review": lambda: test_documentation_review(project_path),
        "sync": lambda: test_sync_documentation(project_path),
        "auto": lambda: test_auto_archive(project_path, dry_run=True),
        "auto-live": lambda: test_auto_archive(project_path, dry_run=False),
        "archive": lambda: test_archive_with_metadata(project_path),
        "restore": lambda: test_restore_with_review(project_path),
        "report": lambda: test_comprehensive_report(project_path),
    }

    if command in commands:
        console.print("\n[bold magenta]Claude MPM Archive Manager Test[/bold magenta]")
        console.print(f"[dim]Testing: {command}[/dim]\n")
        commands[command]()
        console.print("\n[green]✓ Test completed successfully![/green]")
    else:
        console.print("[red]Invalid command![/red]")
        console.print(__doc__)
        console.print("\nAvailable commands:")
        for cmd in commands:
            console.print(f"  • {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
