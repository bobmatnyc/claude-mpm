"""
Unified log management with async operations and time-based retention.

WHY: This module consolidates all logging functionality across the codebase,
providing a single source of truth for log management with async operations,
time-based retention, and prompt logging capabilities.

DESIGN DECISIONS:
- Time-based retention (48 hours default) instead of count-based
- Async fire-and-forget pattern for non-blocking operations
- Queue-based writing inspired by AsyncSessionLogger
- Unified cleanup function to replace duplicate implementations
- Prompt logging for system and agent prompts
- Configurable retention periods for different log types
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Full, Queue
from threading import Lock, Thread
from typing import Any, Dict, Optional

from claude_mpm.core.logging_utils import get_logger

from ..core.config import Config
from ..core.constants import SystemLimits

logger = get_logger(__name__)

# Import cleanup utility for automatic cleanup
try:
    from ..utils.log_cleanup import run_cleanup_on_startup
except ImportError:
    run_cleanup_on_startup = None


class LogManager:
    """
    Unified log management with async operations and time-based retention.

    Features:
    - Async fire-and-forget logging operations
    - Time-based retention (48 hours default)
    - Prompt logging for system and agent prompts
    - Consolidated cleanup functions
    - Queue-based async writing for performance
    - Configurable retention periods
    """

    # Default retention periods (in hours)
    DEFAULT_RETENTION_HOURS = 48
    DEFAULT_STARTUP_RETENTION_HOURS = 48
    DEFAULT_MPM_RETENTION_HOURS = 48
    DEFAULT_PROMPT_RETENTION_HOURS = 168  # 7 days for prompts
    DEFAULT_SESSION_RETENTION_HOURS = 168  # 7 days for sessions

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the LogManager with configuration.

        Args:
            config: Configuration instance (creates new if not provided)
        """
        self.config = config or Config()
        self._setup_logging_config()

        # Queue for async operations
        self.write_queue: Queue = Queue(maxsize=SystemLimits.MAX_QUEUE_SIZE)
        self.cleanup_queue: Queue = Queue(maxsize=100)

        # Thread management
        self._write_thread: Optional[Thread] = None
        self._cleanup_thread: Optional[Thread] = None
        self._shutdown = False
        self._lock = Lock()

        # Cache for directory paths
        self._dir_cache: Dict[str, Path] = {}

        # Start background threads
        self._start_background_threads()

        # Run automatic cleanup on startup if enabled
        self._run_startup_cleanup()

    def _setup_logging_config(self):
        """Load and setup logging configuration from config."""
        logging_config = self.config.get("logging", {})
        response_config = self.config.get("response_logging", {})

        # Get retention periods from config with defaults
        self.retention_hours = {
            "default": logging_config.get(
                "retention_hours", self.DEFAULT_RETENTION_HOURS
            ),
            "startup": logging_config.get(
                "startup_retention_hours", self.DEFAULT_STARTUP_RETENTION_HOURS
            ),
            "mpm": logging_config.get(
                "mpm_retention_hours", self.DEFAULT_MPM_RETENTION_HOURS
            ),
            "prompts": logging_config.get(
                "prompt_retention_hours", self.DEFAULT_PROMPT_RETENTION_HOURS
            ),
            "sessions": response_config.get(
                "session_retention_hours", self.DEFAULT_SESSION_RETENTION_HOURS
            ),
        }

        # Base directories
        self.base_log_dir = Path(
            logging_config.get("base_directory", ".claude-mpm/logs")
        )
        if not self.base_log_dir.is_absolute():
            self.base_log_dir = Path.cwd() / self.base_log_dir

    def _run_startup_cleanup(self):
        """Run automatic log cleanup on startup if enabled."""
        if run_cleanup_on_startup is None:
            return  # Cleanup utility not available

        # Check environment variable to skip cleanup (for configure command)
        import os

        if os.environ.get("CLAUDE_MPM_SKIP_CLEANUP", "0") == "1":
            logger.debug("Startup cleanup skipped (CLAUDE_MPM_SKIP_CLEANUP=1)")
            return

        try:
            # Get cleanup configuration
            cleanup_config = self.config.get("log_cleanup", {})

            # Check if automatic cleanup is enabled (default: True)
            if not cleanup_config.get("auto_cleanup_enabled", True):
                logger.debug("Automatic log cleanup is disabled")
                return

            # Convert hours to days for cleanup utility
            cleanup_params = {
                "auto_cleanup_enabled": True,
                "session_retention_days": self.retention_hours.get("sessions", 168)
                // 24,
                "archive_retention_days": cleanup_config.get(
                    "archive_retention_days", 30
                ),
                "log_retention_days": cleanup_config.get("log_retention_days", 14),
            }

            # Run cleanup in background thread to avoid blocking startup
            def cleanup_task():
                try:
                    result = run_cleanup_on_startup(self.base_log_dir, cleanup_params)
                    if result:
                        logger.debug(
                            f"Startup cleanup completed: "
                            f"Removed {result.get('total_removed', 0)} items"
                        )
                except Exception as e:
                    logger.debug(f"Startup cleanup failed: {e}")

            cleanup_thread = Thread(target=cleanup_task, daemon=True)
            cleanup_thread.start()

        except Exception as e:
            logger.debug(f"Could not run startup cleanup: {e}")

    def _start_background_threads(self):
        """Start background threads for async operations."""
        with self._lock:
            if not self._write_thread or not self._write_thread.is_alive():
                self._write_thread = Thread(
                    target=self._process_write_queue, daemon=True
                )
                self._write_thread.start()

            if not self._cleanup_thread or not self._cleanup_thread.is_alive():
                self._cleanup_thread = Thread(
                    target=self._process_cleanup_queue, daemon=True
                )
                self._cleanup_thread.start()

    def _process_write_queue(self):
        """Process write operations from the queue."""
        while not self._shutdown:
            try:
                # Get write operation with timeout
                operation = self.write_queue.get(timeout=1.0)
                if operation is None:  # Shutdown signal
                    break

                # Execute write operation
                try:
                    operation()
                except Exception as e:
                    logger.error(f"Error in write operation: {e}")
                finally:
                    self.write_queue.task_done()

            except Exception:
                continue  # Timeout or other error, continue loop

    def _process_cleanup_queue(self):
        """Process cleanup operations from the queue."""
        while not self._shutdown:
            try:
                # Get cleanup operation with timeout
                operation = self.cleanup_queue.get(timeout=1.0)
                if operation is None:  # Shutdown signal
                    break

                # Execute cleanup operation
                try:
                    operation()
                except Exception as e:
                    logger.error(f"Error in cleanup operation: {e}")
                finally:
                    self.cleanup_queue.task_done()

            except Exception:
                continue  # Timeout or other error, continue loop

    async def setup_logging(self, log_type: str) -> Path:
        """
        Unified log setup for all log types.

        Args:
            log_type: Type of logging to setup (startup, mpm, prompts, sessions)

        Returns:
            Path to the log directory
        """
        # Get or create directory for log type
        log_dir = self._get_log_directory(log_type)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Add to cache
        self._dir_cache[log_type] = log_dir

        # One-time migration for MPM logs from old location to new subdirectory
        if log_type == "mpm" and not hasattr(self, "_mpm_logs_migrated"):
            await self._migrate_mpm_logs()
            self._mpm_logs_migrated = True

        # Schedule cleanup for old logs
        await self.cleanup_old_logs(
            log_dir,
            pattern="*",
            retention_hours=self.retention_hours.get(
                log_type, self.retention_hours["default"]
            ),
        )

        return log_dir

    def _get_log_directory(self, log_type: str) -> Path:
        """
        Get the directory path for a specific log type.

        Args:
            log_type: Type of log (startup, mpm, prompts, sessions)

        Returns:
            Path to the log directory
        """
        if log_type in self._dir_cache:
            return self._dir_cache[log_type]

        # Map log types to directory names
        dir_mapping = {
            "startup": "startup",
            "mpm": "mpm",  # MPM logs in dedicated subdirectory
            "prompts": "prompts",
            "sessions": "sessions",
            "agents": "agents",
            "system": "system",
        }

        subdir = dir_mapping.get(log_type, log_type)
        log_dir = self.base_log_dir / subdir if subdir else self.base_log_dir

        self._dir_cache[log_type] = log_dir
        return log_dir

    async def cleanup_old_logs(
        self, directory: Path, pattern: str = "*", retention_hours: int = 48
    ) -> int:
        """
        Consolidated cleanup with time-based retention.

        Removes log files older than the retention period.

        Args:
            directory: Directory to clean up
            pattern: File pattern to match (default: all files)
            retention_hours: Hours to retain logs (default: 48)

        Returns:
            Number of files deleted
        """
        if not directory.exists():
            return 0

        # Calculate cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)

        # Schedule async cleanup
        deleted_count = await self._async_cleanup(directory, pattern, cutoff_time)

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old log files from {directory}")

        return deleted_count

    async def _async_cleanup(
        self, directory: Path, pattern: str, cutoff_time: datetime
    ) -> int:
        """
        Perform async cleanup of old files.

        Args:
            directory: Directory to clean
            pattern: File pattern to match
            cutoff_time: Delete files older than this time

        Returns:
            Number of files deleted
        """
        deleted_count = 0

        def cleanup_task():
            nonlocal deleted_count
            try:
                # Find matching files
                if pattern == "*":
                    files = list(directory.iterdir())
                else:
                    files = list(directory.glob(pattern))

                for file_path in files:
                    if not file_path.is_file():
                        continue

                    try:
                        # Check file modification time
                        mtime = datetime.fromtimestamp(
                            file_path.stat().st_mtime, tz=timezone.utc
                        )
                        if mtime < cutoff_time:
                            file_path.unlink()
                            deleted_count += 1
                    except Exception as e:
                        logger.debug(f"Could not delete {file_path}: {e}")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

        # Run cleanup in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, cleanup_task)

        return deleted_count

    def _sync_cleanup_old_logs(
        self, directory: Path, pattern: str = "*", retention_hours: int = 48
    ) -> int:
        """
        Synchronous version of cleanup for backward compatibility.

        Args:
            directory: Directory to clean up
            pattern: File pattern to match
            retention_hours: Hours to retain logs

        Returns:
            Number of files deleted
        """
        if not directory.exists():
            return 0

        # Calculate cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        deleted_count = 0

        try:
            # Find matching files
            if pattern == "*":
                files = list(directory.iterdir())
            else:
                files = list(directory.glob(pattern))

            for file_path in files:
                if not file_path.is_file():
                    continue

                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(
                        file_path.stat().st_mtime, tz=timezone.utc
                    )
                    if mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                except Exception as e:
                    logger.debug(f"Could not delete {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error during sync cleanup: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old log files from {directory}")

        return deleted_count

    async def _migrate_mpm_logs(self):
        """
        One-time migration to move existing MPM logs to new subdirectory.

        Moves mpm_*.log files from old locations to .claude-mpm/logs/mpm/
        """
        try:
            # Check old possible locations (including incorrectly created ones)
            old_locations = [
                Path.cwd() / "logs",  # Incorrectly created in project root
                Path.cwd() / ".claude-mpm" / "logs",  # Correct base location
                self.base_log_dir,  # Current base location (.claude-mpm/logs/)
            ]
            new_location = self.base_log_dir / "mpm"

            # Collect all MPM logs from all old locations
            all_mpm_logs = []
            for old_location in old_locations:
                if old_location.exists() and old_location != new_location:
                    # Find all MPM log files in this location
                    mpm_logs = list(old_location.glob("mpm_*.log"))
                    all_mpm_logs.extend(mpm_logs)

            if not all_mpm_logs:
                return  # No logs to migrate

            # Ensure new directory exists
            new_location.mkdir(parents=True, exist_ok=True)

            migrated_count = 0
            for log_file in all_mpm_logs:
                try:
                    # Move file to new location
                    new_path = new_location / log_file.name
                    if not new_path.exists():  # Don't overwrite existing files
                        log_file.rename(new_path)
                        migrated_count += 1
                except Exception as e:
                    logger.debug(f"Could not migrate {log_file}: {e}")

            if migrated_count > 0:
                logger.info(
                    f"Migrated {migrated_count} MPM log files to {new_location}"
                )

        except Exception as e:
            # Migration is best-effort, don't fail if something goes wrong
            logger.debug(f"MPM log migration skipped: {e}")

    async def log_prompt(
        self, prompt_type: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
        """
        Save prompts to prompts directory.

        Args:
            prompt_type: Type of prompt (system, agent, custom)
            content: The prompt content
            metadata: Additional metadata to save with prompt

        Returns:
            Path to the saved prompt file, or None if failed
        """
        try:
            # Setup prompts directory
            prompts_dir = await self.setup_logging("prompts")

            # Generate filename with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[
                :-3
            ]  # Microseconds to milliseconds

            # Sanitize prompt type for filename
            if prompt_type is None:
                prompt_type = "unknown"
            safe_type = str(prompt_type).replace(" ", "_").replace("/", "_")

            # Handle None content
            if content is None:
                content = ""

            # Determine file extension based on content
            if content and (
                content.strip().startswith("{") or content.strip().startswith("[")
            ):
                extension = ".json"
            else:
                extension = ".md"

            filename = f"{safe_type}_{timestamp}{extension}"
            file_path = prompts_dir / filename

            # Prepare prompt data
            prompt_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": prompt_type,
                "content": content,
                "metadata": metadata or {},
            }

            # Add session ID if available
            if "session_id" in os.environ:
                prompt_data["session_id"] = os.environ.get("session_id")

            # Queue async write
            await self._queue_write(file_path, prompt_data, extension)

            logger.debug(f"Queued prompt logging to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to log prompt: {e}")
            return None

    async def _queue_write(self, file_path: Path, data: Any, extension: str):
        """
        Queue a write operation for async processing.

        Args:
            file_path: Path to write to
            data: Data to write
            extension: File extension to determine format
        """

        def write_task():
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)

                if extension == ".json":
                    # JSON files also get structured metadata for consistency
                    with file_path.open("w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                # For markdown or text files
                elif isinstance(data, dict):
                    # Write as formatted markdown with metadata
                    with file_path.open("w", encoding="utf-8") as f:
                        f.write("---\n")
                        f.write(f"timestamp: {data.get('timestamp', 'unknown')}\n")
                        f.write(f"type: {data.get('type', 'unknown')}\n")
                        if data.get("session_id"):
                            f.write(f"session_id: {data['session_id']}\n")
                        if data.get("metadata"):
                            f.write(f"metadata: {json.dumps(data['metadata'])}\n")
                        f.write("---\n\n")
                        f.write(data.get("content", ""))
                else:
                    # Write content directly
                    with file_path.open("w", encoding="utf-8") as f:
                        f.write(str(data))
            except Exception as e:
                logger.error(f"Failed to write {file_path}: {e}")

        try:
            self.write_queue.put_nowait(write_task)
        except Full:
            # Queue is full, execute synchronously as fallback
            logger.warning("Write queue full, executing synchronously")
            write_task()

    async def write_log_async(self, message: str, level: str = "INFO"):
        """
        Async fire-and-forget logging.

        Args:
            message: Log message to write
            level: Log level (INFO, WARNING, ERROR, DEBUG)
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        # Get appropriate log file based on context
        log_dir = self._get_log_directory("mpm")
        log_file = log_dir / f"mpm_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log"

        def write_task():
            try:
                # Ensure directory exists before writing (race condition with cleanup)
                log_dir.mkdir(parents=True, exist_ok=True)
                with log_file.open("a", encoding="utf-8") as f:
                    f.write(log_entry)
            except Exception as e:
                logger.error(f"Failed to write log: {e}")

        try:
            self.write_queue.put_nowait(write_task)
        except Full:
            # Queue full, log to standard logger as fallback
            getattr(logger, level.lower(), logger.info)(message)

    def cleanup_old_startup_logs(
        self, project_root: Optional[Path] = None, keep_hours: Optional[int] = None
    ) -> int:
        """
        Replacement for the old cleanup_old_startup_logs function.

        Now uses time-based retention instead of count-based.

        Args:
            project_root: Root directory for the project
            keep_hours: Hours to keep logs (default from config)

        Returns:
            Number of log files deleted
        """
        if keep_hours is None:
            keep_hours = self.retention_hours.get(
                "startup", self.DEFAULT_STARTUP_RETENTION_HOURS
            )

        if project_root is None:
            project_root = Path.cwd()

        log_dir = project_root / ".claude-mpm" / "logs" / "startup"

        # Use synchronous cleanup for compatibility
        return self._sync_cleanup_old_logs(log_dir, "startup-*.log", keep_hours)

    def cleanup_old_mpm_logs(
        self, log_dir: Optional[Path] = None, keep_hours: Optional[int] = None
    ) -> int:
        """
        Replacement for the old cleanup_old_mpm_logs function.

        Now uses time-based retention instead of count-based.

        Args:
            log_dir: Directory containing log files
            keep_hours: Hours to keep logs (default from config)

        Returns:
            Number of log files deleted
        """
        if keep_hours is None:
            keep_hours = self.retention_hours.get(
                "mpm", self.DEFAULT_MPM_RETENTION_HOURS
            )

        if log_dir is None:
            from claude_mpm.core.unified_paths import get_project_root

            deployment_root = get_project_root()
            log_dir = deployment_root / ".claude-mpm" / "logs"

        # Use synchronous cleanup for compatibility
        return self._sync_cleanup_old_logs(log_dir, "mpm_*.log", keep_hours)

    def shutdown(self):
        """Gracefully shutdown the LogManager."""
        self._shutdown = True

        # Signal threads to stop
        try:
            self.write_queue.put_nowait(None)
            self.cleanup_queue.put_nowait(None)
        except Exception:
            pass

        # Wait for threads to finish
        if self._write_thread and self._write_thread.is_alive():
            self._write_thread.join(timeout=2.0)

        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2.0)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


# Global singleton instance
_log_manager_instance: Optional[LogManager] = None
_log_manager_lock = Lock()


def get_log_manager() -> LogManager:
    """
    Get or create the global LogManager instance.

    Returns:
        The global LogManager instance
    """
    global _log_manager_instance

    if _log_manager_instance is None:
        with _log_manager_lock:
            if _log_manager_instance is None:
                _log_manager_instance = LogManager()

    return _log_manager_instance
