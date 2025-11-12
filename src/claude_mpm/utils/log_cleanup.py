"""
Comprehensive log cleanup utility for Claude MPM.

This module provides automated log cleanup with both size and age-based policies,
including session directory cleanup, archived log removal, and rotation management.
"""

import gzip
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class LogCleanupConfig:
    """Configuration for log cleanup operations."""

    # Default retention periods (in days)
    DEFAULT_SESSION_MAX_AGE_DAYS = 7
    DEFAULT_ARCHIVED_MAX_AGE_DAYS = 30
    DEFAULT_LOG_MAX_AGE_DAYS = 14
    DEFAULT_PROMPT_MAX_AGE_DAYS = 7

    # Size thresholds
    DEFAULT_MAX_LOG_SIZE_MB = 5
    DEFAULT_MAX_TOTAL_SIZE_GB = 1

    # File patterns
    LOG_PATTERNS = {
        "mpm": "mpm_*.log",
        "startup": "startup-*.log",
        "system": "system_*.log",
        "agent": "agent_*.log",
    }

    ARCHIVE_EXTENSIONS = [".gz", ".zip", ".tar", ".bz2"]


class LogCleanupUtility:
    """
    Comprehensive log cleanup utility with age and size-based policies.

    Features:
    - Age-based cleanup for session directories
    - Cleanup of old archived logs (.gz files)
    - Size-based rotation trigger
    - Dry-run mode for testing
    - Detailed statistics reporting
    - Error handling for locked/permission issues
    """

    def __init__(self, base_log_dir: Optional[Path] = None):
        """
        Initialize the log cleanup utility.

        Args:
            base_log_dir: Base directory for logs (default: .claude-mpm/logs)
        """
        if base_log_dir is None:
            base_log_dir = Path.cwd() / ".claude-mpm" / "logs"

        self.base_log_dir = Path(base_log_dir)
        self.stats = {
            "sessions_removed": 0,
            "archives_removed": 0,
            "logs_removed": 0,
            "space_freed_mb": 0.0,
            "errors": [],
        }

    def cleanup_old_sessions(
        self,
        max_age_days: int = LogCleanupConfig.DEFAULT_SESSION_MAX_AGE_DAYS,
        dry_run: bool = False,
    ) -> Tuple[int, float]:
        """
        Remove session directories older than specified days.

        Args:
            max_age_days: Maximum age in days for session directories
            dry_run: If True, only report what would be deleted

        Returns:
            Tuple of (directories removed, space freed in MB)
        """
        sessions_dir = self.base_log_dir / "sessions"
        if not sessions_dir.exists():
            logger.info(f"Sessions directory not found: {sessions_dir}")
            return 0, 0.0

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        removed_count = 0
        total_size = 0.0

        logger.info(
            f"Scanning for session directories older than {max_age_days} days..."
        )

        try:
            for session_dir in sessions_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                try:
                    # Check directory modification time
                    mtime = datetime.fromtimestamp(
                        session_dir.stat().st_mtime, tz=timezone.utc
                    )

                    if mtime < cutoff_time:
                        # Calculate directory size
                        dir_size = self._get_directory_size(session_dir)
                        total_size += dir_size

                        if dry_run:
                            logger.info(
                                f"[DRY RUN] Would remove session: {session_dir.name} "
                                f"(age: {(datetime.now(timezone.utc) - mtime).days} days, "
                                f"size: {dir_size:.2f} MB)"
                            )
                        else:
                            shutil.rmtree(session_dir)
                            logger.info(
                                f"Removed session: {session_dir.name} "
                                f"(age: {(datetime.now(timezone.utc) - mtime).days} days, "
                                f"size: {dir_size:.2f} MB)"
                            )

                        removed_count += 1

                except (PermissionError, OSError) as e:
                    error_msg = f"Could not remove {session_dir.name}: {e}"
                    logger.warning(error_msg)
                    self.stats["errors"].append(error_msg)

        except Exception as e:
            logger.error(f"Error scanning sessions directory: {e}")
            self.stats["errors"].append(str(e))

        self.stats["sessions_removed"] += removed_count
        self.stats["space_freed_mb"] += total_size

        return removed_count, total_size

    def cleanup_archived_logs(
        self,
        max_age_days: int = LogCleanupConfig.DEFAULT_ARCHIVED_MAX_AGE_DAYS,
        dry_run: bool = False,
    ) -> Tuple[int, float]:
        """
        Remove archived log files older than specified days.

        Args:
            max_age_days: Maximum age in days for archived files
            dry_run: If True, only report what would be deleted

        Returns:
            Tuple of (files removed, space freed in MB)
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        removed_count = 0
        total_size = 0.0

        logger.info(f"Scanning for archived files older than {max_age_days} days...")

        # Search for archived files in all subdirectories
        for ext in LogCleanupConfig.ARCHIVE_EXTENSIONS:
            for archive_file in self.base_log_dir.rglob(f"*{ext}"):
                try:
                    mtime = datetime.fromtimestamp(
                        archive_file.stat().st_mtime, tz=timezone.utc
                    )

                    if mtime < cutoff_time:
                        file_size = archive_file.stat().st_size / (1024 * 1024)  # MB
                        total_size += file_size

                        if dry_run:
                            logger.info(
                                f"[DRY RUN] Would remove archive: {archive_file.name} "
                                f"(age: {(datetime.now(timezone.utc) - mtime).days} days, "
                                f"size: {file_size:.2f} MB)"
                            )
                        else:
                            archive_file.unlink()
                            logger.info(
                                f"Removed archive: {archive_file.name} "
                                f"(age: {(datetime.now(timezone.utc) - mtime).days} days, "
                                f"size: {file_size:.2f} MB)"
                            )

                        removed_count += 1

                except (PermissionError, OSError) as e:
                    error_msg = f"Could not remove {archive_file.name}: {e}"
                    logger.warning(error_msg)
                    self.stats["errors"].append(error_msg)

        self.stats["archives_removed"] += removed_count
        self.stats["space_freed_mb"] += total_size

        return removed_count, total_size

    def cleanup_old_logs(
        self,
        max_age_days: int = LogCleanupConfig.DEFAULT_LOG_MAX_AGE_DAYS,
        dry_run: bool = False,
        log_type: Optional[str] = None,
    ) -> Tuple[int, float]:
        """
        Remove old log files based on age.

        Args:
            max_age_days: Maximum age in days for log files
            dry_run: If True, only report what would be deleted
            log_type: Specific log type to clean (mpm, startup, etc.) or None for all

        Returns:
            Tuple of (files removed, space freed in MB)
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        removed_count = 0
        total_size = 0.0

        patterns = (
            [LogCleanupConfig.LOG_PATTERNS.get(log_type)]
            if log_type
            else LogCleanupConfig.LOG_PATTERNS.values()
        )

        logger.info(f"Scanning for log files older than {max_age_days} days...")

        for pattern in patterns:
            for subdir in ["mpm", "startup", "system", "agents"]:
                log_dir = self.base_log_dir / subdir
                if not log_dir.exists():
                    continue

                for log_file in log_dir.glob(pattern):
                    try:
                        mtime = datetime.fromtimestamp(
                            log_file.stat().st_mtime, tz=timezone.utc
                        )

                        if mtime < cutoff_time:
                            file_size = log_file.stat().st_size / (1024 * 1024)  # MB
                            total_size += file_size

                            if dry_run:
                                logger.info(
                                    f"[DRY RUN] Would remove log: {log_file.name} "
                                    f"(age: {(datetime.now(timezone.utc) - mtime).days} days, "
                                    f"size: {file_size:.2f} MB)"
                                )
                            else:
                                log_file.unlink()
                                logger.info(
                                    f"Removed log: {log_file.name} "
                                    f"(age: {(datetime.now(timezone.utc) - mtime).days} days, "
                                    f"size: {file_size:.2f} MB)"
                                )

                            removed_count += 1

                    except (PermissionError, OSError) as e:
                        error_msg = f"Could not remove {log_file.name}: {e}"
                        logger.warning(error_msg)
                        self.stats["errors"].append(error_msg)

        self.stats["logs_removed"] += removed_count
        self.stats["space_freed_mb"] += total_size

        return removed_count, total_size

    def cleanup_empty_directories(self, dry_run: bool = False) -> int:
        """
        Remove empty directories in the log tree.

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Number of directories removed
        """
        removed_count = 0

        # Walk bottom-up to remove empty parent directories
        for root, _dirs, _files in os.walk(self.base_log_dir, topdown=False):
            root_path = Path(root)

            # Skip the base log directory itself
            if root_path == self.base_log_dir:
                continue

            try:
                # Check if directory is empty
                if not any(root_path.iterdir()):
                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would remove empty directory: {root_path}"
                        )
                    else:
                        root_path.rmdir()
                        logger.info(f"Removed empty directory: {root_path}")
                    removed_count += 1

            except (PermissionError, OSError) as e:
                error_msg = f"Could not remove directory {root_path}: {e}"
                logger.debug(error_msg)  # Debug level since this is common

        return removed_count

    def compress_old_logs(
        self, age_days: int = 7, dry_run: bool = False
    ) -> Tuple[int, float]:
        """
        Compress log files older than specified days.

        Args:
            age_days: Compress files older than this many days
            dry_run: If True, only report what would be compressed

        Returns:
            Tuple of (files compressed, space saved in MB)
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=age_days)
        compressed_count = 0
        space_saved = 0.0

        for log_file in self.base_log_dir.rglob("*.log"):
            # Skip already compressed files
            if log_file.suffix in LogCleanupConfig.ARCHIVE_EXTENSIONS:
                continue

            try:
                mtime = datetime.fromtimestamp(
                    log_file.stat().st_mtime, tz=timezone.utc
                )

                if mtime < cutoff_time:
                    original_size = log_file.stat().st_size / (1024 * 1024)  # MB
                    compressed_path = log_file.with_suffix(".log.gz")

                    if dry_run:
                        # Estimate compression ratio (typically 80-90% for logs)
                        estimated_saved = original_size * 0.85
                        logger.info(
                            f"[DRY RUN] Would compress: {log_file.name} "
                            f"(size: {original_size:.2f} MB, "
                            f"estimated savings: {estimated_saved:.2f} MB)"
                        )
                        space_saved += estimated_saved
                    else:
                        # Actually compress the file
                        with log_file.open("rb") as f_in:
                            with gzip.open(
                                compressed_path, "wb", compresslevel=9
                            ) as f_out:
                                shutil.copyfileobj(f_in, f_out)

                        compressed_size = compressed_path.stat().st_size / (1024 * 1024)
                        saved = original_size - compressed_size
                        space_saved += saved

                        # Remove original file
                        log_file.unlink()

                        logger.info(
                            f"Compressed: {log_file.name} "
                            f"({original_size:.2f} MB → {compressed_size:.2f} MB, "
                            f"saved: {saved:.2f} MB)"
                        )

                    compressed_count += 1

            except Exception as e:
                error_msg = f"Could not compress {log_file.name}: {e}"
                logger.warning(error_msg)
                self.stats["errors"].append(error_msg)

        return compressed_count, space_saved

    def get_statistics(self) -> Dict:
        """
        Get current statistics about the log directory.

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_size_mb": 0.0,
            "session_count": 0,
            "archive_count": 0,
            "log_count": 0,
            "oldest_session": None,
            "oldest_log": None,
            "directory_sizes": {},
        }

        # Calculate total size
        stats["total_size_mb"] = self._get_directory_size(self.base_log_dir)

        # Count sessions
        sessions_dir = self.base_log_dir / "sessions"
        if sessions_dir.exists():
            sessions = list(sessions_dir.iterdir())
            stats["session_count"] = len([s for s in sessions if s.is_dir()])

            # Find oldest session
            if sessions:
                oldest = min(sessions, key=lambda p: p.stat().st_mtime)
                stats["oldest_session"] = {
                    "name": oldest.name,
                    "age_days": (
                        datetime.now(timezone.utc)
                        - datetime.fromtimestamp(
                            oldest.stat().st_mtime, tz=timezone.utc
                        )
                    ).days,
                }

        # Count archives
        for ext in LogCleanupConfig.ARCHIVE_EXTENSIONS:
            stats["archive_count"] += len(list(self.base_log_dir.rglob(f"*{ext}")))

        # Count logs (excluding symlinks)
        stats["log_count"] = len(
            [p for p in self.base_log_dir.rglob("*.log") if not p.is_symlink()]
        )

        # Find oldest log (excluding symlinks)
        all_logs = [p for p in self.base_log_dir.rglob("*.log") if not p.is_symlink()]
        if all_logs:
            oldest_log = min(all_logs, key=lambda p: p.stat().st_mtime)
            stats["oldest_log"] = {
                "name": oldest_log.name,
                "path": str(oldest_log.relative_to(self.base_log_dir)),
                "age_days": (
                    datetime.now(timezone.utc)
                    - datetime.fromtimestamp(
                        oldest_log.stat().st_mtime, tz=timezone.utc
                    )
                ).days,
            }

        # Calculate directory sizes
        for subdir in ["sessions", "mpm", "startup", "system", "agents", "prompts"]:
            dir_path = self.base_log_dir / subdir
            if dir_path.exists():
                stats["directory_sizes"][subdir] = self._get_directory_size(dir_path)

        return stats

    def perform_full_cleanup(
        self,
        session_max_age_days: int = LogCleanupConfig.DEFAULT_SESSION_MAX_AGE_DAYS,
        archive_max_age_days: int = LogCleanupConfig.DEFAULT_ARCHIVED_MAX_AGE_DAYS,
        log_max_age_days: int = LogCleanupConfig.DEFAULT_LOG_MAX_AGE_DAYS,
        compress_age_days: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict:
        """
        Perform a complete cleanup operation.

        Args:
            session_max_age_days: Maximum age for session directories
            archive_max_age_days: Maximum age for archived files
            log_max_age_days: Maximum age for log files
            compress_age_days: Age threshold for compression (None to skip)
            dry_run: If True, only report what would be done

        Returns:
            Summary statistics dictionary
        """
        mode = "[DRY RUN] " if dry_run else ""
        logger.info(f"{mode}Starting comprehensive log cleanup...")

        # Get initial statistics
        initial_stats = self.get_statistics()

        # Reset stats
        self.stats = {
            "sessions_removed": 0,
            "archives_removed": 0,
            "logs_removed": 0,
            "files_compressed": 0,
            "empty_dirs_removed": 0,
            "space_freed_mb": 0.0,
            "space_saved_mb": 0.0,
            "errors": [],
        }

        # Cleanup operations
        _sessions_removed, _sessions_space = self.cleanup_old_sessions(
            session_max_age_days, dry_run
        )

        _archives_removed, _archives_space = self.cleanup_archived_logs(
            archive_max_age_days, dry_run
        )

        _logs_removed, _logs_space = self.cleanup_old_logs(log_max_age_days, dry_run)

        # Optional compression
        if compress_age_days is not None:
            compressed, space_saved = self.compress_old_logs(compress_age_days, dry_run)
            self.stats["files_compressed"] = compressed
            self.stats["space_saved_mb"] = space_saved

        # Cleanup empty directories
        empty_removed = self.cleanup_empty_directories(dry_run)
        self.stats["empty_dirs_removed"] = empty_removed

        # Get final statistics
        final_stats = self.get_statistics() if not dry_run else initial_stats

        # Prepare summary
        summary = {
            "mode": "DRY RUN" if dry_run else "EXECUTED",
            "initial_stats": initial_stats,
            "final_stats": final_stats,
            "operations": self.stats,
            "total_removed": (
                self.stats["sessions_removed"]
                + self.stats["archives_removed"]
                + self.stats["logs_removed"]
            ),
            "total_space_impact_mb": (
                self.stats["space_freed_mb"] + self.stats.get("space_saved_mb", 0)
            ),
        }

        # Log summary
        logger.info(
            f"{mode}Cleanup complete: "
            f"Removed {summary['total_removed']} items, "
            f"freed {self.stats['space_freed_mb']:.2f} MB"
        )

        if self.stats.get("files_compressed"):
            logger.info(
                f"Compressed {self.stats['files_compressed']} files, "
                f"saved {self.stats['space_saved_mb']:.2f} MB"
            )

        if self.stats["errors"]:
            logger.warning(
                f"Encountered {len(self.stats['errors'])} errors during cleanup"
            )

        return summary

    def _get_directory_size(self, path: Path) -> float:
        """
        Calculate total size of a directory in MB.

        Args:
            path: Directory path

        Returns:
            Size in megabytes
        """
        total_size = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception as e:
            logger.debug(f"Error calculating size for {path}: {e}")

        return total_size / (1024 * 1024)  # Convert to MB


def run_cleanup_on_startup(
    base_log_dir: Optional[Path] = None, config: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Run automatic cleanup on application startup.

    This function is designed to be called during application initialization
    to perform routine log maintenance.

    Args:
        base_log_dir: Base directory for logs
        config: Optional configuration dictionary

    Returns:
        Cleanup summary or None if disabled
    """
    # Check if cleanup is enabled
    if config and not config.get("auto_cleanup_enabled", True):
        logger.debug("Automatic log cleanup is disabled")
        return None

    try:
        cleaner = LogCleanupUtility(base_log_dir)

        # Use configuration or defaults
        session_days = config.get("session_retention_days", 7) if config else 7
        archive_days = config.get("archive_retention_days", 30) if config else 30
        log_days = config.get("log_retention_days", 14) if config else 14

        # Run cleanup (not dry-run)
        summary = cleaner.perform_full_cleanup(
            session_max_age_days=session_days,
            archive_max_age_days=archive_days,
            log_max_age_days=log_days,
            compress_age_days=None,  # Don't compress on startup
            dry_run=False,
        )

        logger.info(
            f"Startup cleanup completed: "
            f"Removed {summary['total_removed']} items, "
            f"freed {summary['total_space_impact_mb']:.2f} MB"
        )

        return summary

    except Exception as e:
        logger.error(f"Error during startup cleanup: {e}")
        return None
