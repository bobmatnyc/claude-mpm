#!/usr/bin/env python3
"""
Cleanup utility for Claude MPM logs.

This script helps maintain the logs directory by:
- Removing empty session directories
- Optionally archiving old logs
- Providing statistics on log usage
"""

import argparse
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def get_directory_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    for file in path.rglob("*"):
        if file.is_file():
            total += file.stat().st_size
    return total


def format_bytes(size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def cleanup_empty_sessions(logs_dir: Path, dry_run: bool = True) -> int:
    """Remove empty session directories.

    Args:
        logs_dir: Path to .claude-mpm/logs directory
        dry_run: If True, only show what would be deleted

    Returns:
        Number of directories cleaned
    """
    sessions_dir = logs_dir / "sessions"
    if not sessions_dir.exists():
        print(f"Sessions directory not found: {sessions_dir}")
        return 0

    empty_dirs = []
    for session_dir in sessions_dir.iterdir():
        if session_dir.is_dir():
            # Check if directory is empty or only has empty files
            files = list(session_dir.iterdir())
            if not files or all(f.stat().st_size == 0 for f in files if f.is_file()):
                empty_dirs.append(session_dir)

    if not empty_dirs:
        print("No empty session directories found.")
        return 0

    print(f"Found {len(empty_dirs)} empty session directories:")
    for dir_path in empty_dirs:
        print(f"  - {dir_path.name}")

    if dry_run:
        print("\nDry run mode - no files deleted. Use --execute to actually delete.")
    else:
        print("\nDeleting empty directories...")
        for dir_path in empty_dirs:
            shutil.rmtree(dir_path)
            print(f"  ✓ Deleted {dir_path.name}")

    return len(empty_dirs)


def archive_old_logs(logs_dir: Path, days: int = 7, dry_run: bool = True) -> int:
    """Archive logs older than specified days.

    Args:
        logs_dir: Path to .claude-mpm/logs directory
        days: Archive logs older than this many days
        dry_run: If True, only show what would be archived

    Returns:
        Number of files archived
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    archive_dir = logs_dir / "archive" / datetime.now().strftime("%Y%m%d")

    files_to_archive = []

    # Check all log files
    for log_file in logs_dir.rglob("*.jsonl"):
        if "archive" in str(log_file):
            continue

        # Try to parse date from filename
        try:
            if log_file.parent.name.startswith("202"):  # Session directory
                date_str = log_file.parent.name.split("_")[0]
                file_date = datetime.strptime(date_str, "%Y%m%d")
            elif log_file.stem.startswith("202"):  # Daily log file
                date_str = log_file.stem
                file_date = datetime.strptime(date_str, "%Y%m%d")
            else:
                continue

            if file_date < cutoff_date:
                files_to_archive.append(log_file)
        except:
            continue

    if not files_to_archive:
        print(f"No log files older than {days} days found.")
        return 0

    print(f"Found {len(files_to_archive)} files older than {days} days:")
    total_size = sum(f.stat().st_size for f in files_to_archive)
    print(f"Total size: {format_bytes(total_size)}")

    if dry_run:
        print("\nDry run mode - no files archived. Use --execute to actually archive.")
    else:
        print(f"\nArchiving to {archive_dir}...")
        archive_dir.mkdir(parents=True, exist_ok=True)

        for file_path in files_to_archive:
            # Maintain directory structure in archive
            rel_path = file_path.relative_to(logs_dir)
            dest_path = archive_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(file_path), str(dest_path))
            print(f"  ✓ Archived {rel_path}")

    return len(files_to_archive)


def show_statistics(logs_dir: Path):
    """Show statistics about log usage."""
    if not logs_dir.exists():
        print(f"Logs directory not found: {logs_dir}")
        return

    print("Claude MPM Log Statistics")
    print("=" * 50)

    # Overall size
    total_size = get_directory_size(logs_dir)
    print(f"Total log size: {format_bytes(total_size)}")

    # Session statistics
    sessions_dir = logs_dir / "sessions"
    if sessions_dir.exists():
        all_sessions = list(sessions_dir.iterdir())
        empty_sessions = [
            s for s in all_sessions if s.is_dir() and not any(s.iterdir())
        ]
        print(f"\nSessions:")
        print(f"  Total: {len(all_sessions)}")
        print(f"  Empty: {len(empty_sessions)}")
        print(f"  Active: {len(all_sessions) - len(empty_sessions)}")

    # Agent statistics
    stats_file = logs_dir.parent / "stats" / "agent_stats.json"
    if stats_file.exists():
        with open(stats_file) as f:
            stats = json.load(f)

        print("\nAgent Usage (all time):")
        total_calls = 0
        total_tokens = 0

        for date, data in stats.items():
            total_calls += data.get("total_calls", 0)
            total_tokens += data.get("total_tokens", 0)

        print(f"  Total calls: {total_calls}")
        print(f"  Total tokens: {total_tokens:,}")

        # Recent agent breakdown
        recent_date = max(stats.keys())
        if "by_agent" in stats[recent_date]:
            print(f"\nRecent agent activity ({recent_date}):")
            for agent, agent_stats in stats[recent_date]["by_agent"].items():
                print(
                    f"  {agent}: {agent_stats['calls']} calls, {agent_stats['tokens']:,} tokens"
                )

    # Directory sizes
    print("\nDirectory sizes:")
    for subdir in ["system", "agents", "sessions", "archive"]:
        path = logs_dir / subdir
        if path.exists():
            size = get_directory_size(path)
            print(f"  {subdir}: {format_bytes(size)}")


def main():
    parser = argparse.ArgumentParser(description="Cleanup and manage Claude MPM logs")

    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=Path.cwd() / ".claude-mpm" / "logs",
        help="Path to logs directory (default: ./.claude-mpm/logs)",
    )

    parser.add_argument(
        "--clean-empty", action="store_true", help="Remove empty session directories"
    )

    parser.add_argument(
        "--archive", type=int, metavar="DAYS", help="Archive logs older than DAYS"
    )

    parser.add_argument("--stats", action="store_true", help="Show log statistics")

    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform operations (default is dry run)",
    )

    args = parser.parse_args()

    if not any([args.clean_empty, args.archive, args.stats]):
        # Default to showing stats
        args.stats = True

    if args.stats:
        show_statistics(args.logs_dir.parent)  # Pass .claude-mpm dir
        print()

    if args.clean_empty:
        print("Cleaning empty session directories...")
        cleaned = cleanup_empty_sessions(args.logs_dir, dry_run=not args.execute)
        print(f"\nCleaned {cleaned} directories.\n")

    if args.archive:
        print(f"Archiving logs older than {args.archive} days...")
        archived = archive_old_logs(
            args.logs_dir, days=args.archive, dry_run=not args.execute
        )
        print(f"\nArchived {archived} files.\n")


if __name__ == "__main__":
    main()
