#!/usr/bin/env python3
"""
Command-line interface for Claude MPM log cleanup.

This script provides a comprehensive interface for managing and cleaning up
Claude MPM logs with various options for age-based cleanup, compression,
and statistics reporting.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.utils.log_cleanup import LogCleanupConfig, LogCleanupUtility


def format_size(size_mb: float) -> str:
    """Format size in MB to human-readable string."""
    if size_mb < 1024:
        return f"{size_mb:.2f} MB"
    if size_mb < 1024 * 1024:
        return f"{size_mb / 1024:.2f} GB"
    return f"{size_mb / (1024 * 1024):.2f} TB"


def print_statistics(stats: dict, title: str = "Log Directory Statistics"):
    """Print formatted statistics."""
    print(f"\n{title}")
    print("=" * 60)

    print(f"Total size: {format_size(stats['total_size_mb'])}")
    print(f"Session count: {stats['session_count']}")
    print(f"Log file count: {stats['log_count']}")
    print(f"Archive count: {stats['archive_count']}")

    if stats.get("oldest_session"):
        print(
            f"\nOldest session: {stats['oldest_session']['name']} "
            f"({stats['oldest_session']['age_days']} days old)"
        )

    if stats.get("oldest_log"):
        print(
            f"Oldest log: {stats['oldest_log']['name']} "
            f"({stats['oldest_log']['age_days']} days old)"
        )

    if stats.get("directory_sizes"):
        print("\nDirectory sizes:")
        for name, size in stats["directory_sizes"].items():
            print(f"  {name:12} : {format_size(size):>12}")


def print_cleanup_summary(summary: dict):
    """Print cleanup operation summary."""
    print(f"\n{'DRY RUN' if summary['mode'] == 'DRY RUN' else 'CLEANUP'} SUMMARY")
    print("=" * 60)

    ops = summary["operations"]

    # Items removed
    if ops["sessions_removed"] > 0:
        print(f"Sessions removed: {ops['sessions_removed']}")
    if ops["archives_removed"] > 0:
        print(f"Archives removed: {ops['archives_removed']}")
    if ops["logs_removed"] > 0:
        print(f"Logs removed: {ops['logs_removed']}")
    if ops.get("files_compressed", 0) > 0:
        print(f"Files compressed: {ops['files_compressed']}")
    if ops["empty_dirs_removed"] > 0:
        print(f"Empty directories removed: {ops['empty_dirs_removed']}")

    # Space impact
    total_impact = summary["total_space_impact_mb"]
    if total_impact > 0:
        print(f"\nTotal space freed/saved: {format_size(total_impact)}")
        if ops["space_freed_mb"] > 0:
            print(f"  - Space freed: {format_size(ops['space_freed_mb'])}")
        if ops.get("space_saved_mb", 0) > 0:
            print(
                f"  - Space saved by compression: {format_size(ops['space_saved_mb'])}"
            )

    # Errors
    if ops["errors"]:
        print(f"\n⚠️  Encountered {len(ops['errors'])} errors:")
        for error in ops["errors"][:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(ops["errors"]) > 5:
            print(f"  ... and {len(ops['errors']) - 5} more")

    # Size change
    if summary["mode"] != "DRY RUN":
        initial = summary["initial_stats"]["total_size_mb"]
        final = summary["final_stats"]["total_size_mb"]
        reduction = initial - final
        if reduction > 0:
            percent = (reduction / initial) * 100
            print(
                f"\nSize reduction: {format_size(initial)} → {format_size(final)} "
                f"(-{percent:.1f}%)"
            )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive log cleanup utility for Claude MPM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show statistics only
  %(prog)s --stats

  # Dry run - see what would be cleaned
  %(prog)s --dry-run

  # Clean sessions older than 7 days
  %(prog)s --session-dirs --max-age-days 7

  # Clean archived logs older than 30 days
  %(prog)s --archived-logs --max-age-days 30

  # Full cleanup with custom thresholds
  %(prog)s --all --session-days 7 --archive-days 30 --log-days 14

  # Compress logs older than 7 days
  %(prog)s --compress --compress-days 7

  # Show verbose output
  %(prog)s --all --verbose
""",
    )

    # General options
    parser.add_argument(
        "--logs-dir", type=Path, help="Base log directory (default: .claude-mpm/logs)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress non-error output"
    )

    # Operations
    ops_group = parser.add_argument_group("operations")

    ops_group.add_argument(
        "--all", action="store_true", help="Perform all cleanup operations"
    )

    ops_group.add_argument(
        "--session-dirs", action="store_true", help="Clean old session directories"
    )

    ops_group.add_argument(
        "--archived-logs",
        action="store_true",
        help="Clean old archived log files (.gz, .zip, etc.)",
    )

    ops_group.add_argument(
        "--old-logs", action="store_true", help="Clean old log files"
    )

    ops_group.add_argument(
        "--empty-dirs", action="store_true", help="Remove empty directories"
    )

    ops_group.add_argument(
        "--compress", action="store_true", help="Compress old log files"
    )

    ops_group.add_argument("--stats", action="store_true", help="Show statistics only")

    # Age thresholds
    age_group = parser.add_argument_group("age thresholds")

    age_group.add_argument(
        "--max-age-days",
        type=int,
        help="General max age in days (applies to selected operations)",
    )

    age_group.add_argument(
        "--session-days",
        type=int,
        default=LogCleanupConfig.DEFAULT_SESSION_MAX_AGE_DAYS,
        help=f"Max age for session directories (default: {LogCleanupConfig.DEFAULT_SESSION_MAX_AGE_DAYS})",
    )

    age_group.add_argument(
        "--archive-days",
        type=int,
        default=LogCleanupConfig.DEFAULT_ARCHIVED_MAX_AGE_DAYS,
        help=f"Max age for archived files (default: {LogCleanupConfig.DEFAULT_ARCHIVED_MAX_AGE_DAYS})",
    )

    age_group.add_argument(
        "--log-days",
        type=int,
        default=LogCleanupConfig.DEFAULT_LOG_MAX_AGE_DAYS,
        help=f"Max age for log files (default: {LogCleanupConfig.DEFAULT_LOG_MAX_AGE_DAYS})",
    )

    age_group.add_argument(
        "--compress-days",
        type=int,
        default=7,
        help="Compress files older than this many days (default: 7)",
    )

    # Output options
    output_group = parser.add_argument_group("output options")

    output_group.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    output_group.add_argument("--output", "-o", type=Path, help="Write results to file")

    args = parser.parse_args()

    # Setup logging
    log_level = "ERROR" if args.quiet else ("DEBUG" if args.verbose else "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level), format="%(levelname)s: %(message)s"
    )

    # Determine log directory
    if args.logs_dir:
        base_log_dir = args.logs_dir
    else:
        base_log_dir = Path.cwd() / ".claude-mpm" / "logs"

    if not base_log_dir.exists():
        print(f"Error: Log directory not found: {base_log_dir}", file=sys.stderr)
        return 1

    # Create cleaner instance
    cleaner = LogCleanupUtility(base_log_dir)

    # Apply --max-age-days if specified
    if args.max_age_days:
        if args.session_dirs or args.all:
            args.session_days = args.max_age_days
        if args.archived_logs or args.all:
            args.archive_days = args.max_age_days
        if args.old_logs or args.all:
            args.log_days = args.max_age_days

    # Determine what to do
    any_operation = any(
        [
            args.all,
            args.session_dirs,
            args.archived_logs,
            args.old_logs,
            args.empty_dirs,
            args.compress,
        ]
    )

    # Default to stats if nothing specified
    if not any_operation and not args.stats:
        args.stats = True

    result = {}

    # Show initial statistics
    if args.stats or (any_operation and not args.quiet):
        stats = cleaner.get_statistics()
        if not args.json:
            print_statistics(stats, "Initial Statistics")
        result["initial_stats"] = stats

    # Perform operations
    if any_operation:
        if args.all:
            # Full cleanup
            summary = cleaner.perform_full_cleanup(
                session_max_age_days=args.session_days,
                archive_max_age_days=args.archive_days,
                log_max_age_days=args.log_days,
                compress_age_days=args.compress_days if args.compress else None,
                dry_run=args.dry_run,
            )
            result["summary"] = summary

            if not args.json and not args.quiet:
                print_cleanup_summary(summary)

        else:
            # Individual operations
            operations = {}

            if args.session_dirs:
                removed, space = cleaner.cleanup_old_sessions(
                    args.session_days, args.dry_run
                )
                operations["sessions"] = {"removed": removed, "space_mb": space}
                if not args.quiet and not args.json:
                    print(
                        f"\nSessions: Removed {removed} directories, "
                        f"freed {format_size(space)}"
                    )

            if args.archived_logs:
                removed, space = cleaner.cleanup_archived_logs(
                    args.archive_days, args.dry_run
                )
                operations["archives"] = {"removed": removed, "space_mb": space}
                if not args.quiet and not args.json:
                    print(
                        f"Archives: Removed {removed} files, "
                        f"freed {format_size(space)}"
                    )

            if args.old_logs:
                removed, space = cleaner.cleanup_old_logs(args.log_days, args.dry_run)
                operations["logs"] = {"removed": removed, "space_mb": space}
                if not args.quiet and not args.json:
                    print(f"Logs: Removed {removed} files, freed {format_size(space)}")

            if args.compress:
                compressed, saved = cleaner.compress_old_logs(
                    args.compress_days, args.dry_run
                )
                operations["compress"] = {"compressed": compressed, "saved_mb": saved}
                if not args.quiet and not args.json:
                    print(
                        f"Compression: Compressed {compressed} files, "
                        f"saved {format_size(saved)}"
                    )

            if args.empty_dirs:
                removed = cleaner.cleanup_empty_directories(args.dry_run)
                operations["empty_dirs"] = {"removed": removed}
                if not args.quiet and not args.json:
                    print(f"Empty dirs: Removed {removed} directories")

            result["operations"] = operations

        # Show final statistics
        if not args.dry_run and not args.quiet:
            final_stats = cleaner.get_statistics()
            if not args.json:
                print_statistics(final_stats, "\nFinal Statistics")
            result["final_stats"] = final_stats

    # Output results
    if args.json:
        output = json.dumps(result, indent=2, default=str)
        if args.output:
            args.output.write_text(output)
            if not args.quiet:
                print(f"Results written to {args.output}")
        else:
            print(output)
    elif args.output:
        # Write text summary to file
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            if "initial_stats" in result:
                print_statistics(result["initial_stats"], "Initial Statistics")
            if "summary" in result:
                print_cleanup_summary(result["summary"])
            elif "operations" in result:
                for op_name, op_result in result["operations"].items():
                    print(f"{op_name}: {op_result}")
            if "final_stats" in result:
                print_statistics(result["final_stats"], "Final Statistics")

        args.output.write_text(buffer.getvalue())
        if not args.quiet:
            print(f"Results written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
