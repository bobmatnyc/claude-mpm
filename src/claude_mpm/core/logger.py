"""Unified logging system for Claude MPM.

This module consolidates features from:
- utils/logger.py (simple console/file logging)
- core/logging_config.py (Rich formatting, JSON, streaming)
- core/project_logger.py (project-local logging, statistics)
"""

import functools
import json
import logging
import logging.handlers
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.unified_paths import get_project_root

# Rich support has been removed
HAS_RICH = False

# Thread lock for symlink creation to prevent race conditions
_symlink_lock = threading.Lock()


class LogLevel(Enum):
    """Log levels for different verbosity."""

    OFF = "off"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class StreamingHandler(logging.StreamHandler):
    """
    Custom handler for single-line streaming INFO messages.

    Shows progress indicators that update in place using carriage returns
    while keeping ERROR and WARNING messages on separate lines.
    """

    def __init__(self, stream=None):
        super().__init__(stream)
        self._last_info_message = False
        self._info_line_active = False

    def emit(self, record):
        """Emit a log record with streaming support for INFO messages."""
        try:
            msg = self.format(record)
            stream = self.stream

            # Handle different log levels
            if record.levelno == logging.INFO:
                # For INFO messages, use carriage return for streaming
                if self._info_line_active:
                    # Clear the previous line by overwriting with spaces
                    stream.write("\r" + " " * 100 + "\r")

                # Write INFO message with carriage return (no newline)
                stream.write(f"\r{msg}")
                stream.flush()
                self._info_line_active = True
                self._last_info_message = True

            else:
                # For WARNING, ERROR, CRITICAL - always on new lines
                if self._info_line_active:
                    # Finish the INFO line first
                    stream.write("\n")
                    self._info_line_active = False

                stream.write(f"{msg}\n")
                stream.flush()
                self._last_info_message = False

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)

    def finalize_info_line(self):
        """
        Finalize any active INFO line by adding a newline.
        Call this when you want to ensure the final INFO message remains visible.
        """
        if self._info_line_active:
            self.stream.write("\n")
            self.stream.flush()
            self._info_line_active = False


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging(
    name: str = "claude_mpm",
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    log_file: Optional[Path] = None,
    console_output: bool = True,
    file_output: bool = True,
    use_rich: bool = False,
    json_format: bool = False,
    use_streaming: bool = False,
) -> logging.Logger:
    """
    Set up logging with both console and file handlers.

    Args:
        name: Logger name
        level: Logging level (OFF, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to ~/.claude-mpm/logs)
        log_file: Specific log file path (overrides log_dir)
        console_output: Enable console output
        file_output: Enable file output
        use_rich: (Deprecated) Rich support has been removed
        json_format: Use JSON format for structured logging
        use_streaming: Use streaming handler for single-line INFO messages

    Returns:
        Configured logger
    """
    # Detect deployment context for install-type-aware defaults
    if level == "INFO":  # Only override default, not explicit settings
        from claude_mpm.core.unified_paths import DeploymentContext, PathContext

        context = PathContext.detect_deployment_context()
        if context in (
            DeploymentContext.DEVELOPMENT,
            DeploymentContext.EDITABLE_INSTALL,
        ):
            level = "INFO"  # Development: verbose logging
        else:
            level = "OFF"  # Production installs: silent by default

    logger = logging.getLogger(name)

    # Handle OFF level
    if level.upper() == "OFF":
        logger.setLevel(logging.CRITICAL + 1)  # Higher than CRITICAL
        logger.handlers.clear()
        return logger

    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Prevent duplicate handlers
    logger.handlers.clear()

    # Create formatters
    if json_format:
        formatter = JsonFormatter()
    else:
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        simple_formatter = logging.Formatter("%(levelname)s: %(message)s")

    # Console handler
    if console_output:
        if use_streaming:
            # Use streaming handler for single-line INFO messages
            console_handler = StreamingHandler(sys.stdout)
            console_handler.setFormatter(simple_formatter)
        elif use_rich and not json_format:
            # Rich support has been removed, use standard handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(simple_formatter)
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter if json_format else simple_formatter)

        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    # File handler
    if file_output and level.upper() in ["INFO", "DEBUG"]:
        if log_file:
            # Use specific log file
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            # Use rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,  # 10 MB
            )
        else:
            # Use default log directory
            if log_dir is None:
                # Use deployment root for logs to keep everything centralized
                deployment_root = get_project_root()
                log_dir = deployment_root / ".claude-mpm" / "logs" / "mpm"

            log_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamped log file
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"mpm_{timestamp}.log"

            file_handler = logging.FileHandler(log_file)

            # Clean up old MPM logs (using configured retention count)
            try:
                deleted_count = cleanup_old_mpm_logs(log_dir)
                if deleted_count > 0:
                    # Log to the new file handler that we're about to add
                    pass  # Deletion count will be logged when logger is ready
            except Exception:
                pass  # Ignore cleanup errors

            # Also create a symlink to latest log (with thread safety)
            latest_link = log_dir / "latest.log"

            # Use a lock to prevent race conditions in concurrent environments
            with _symlink_lock:
                # Remove existing symlink/file if it exists
                # Note: We need to handle both regular files and symlinks (including broken ones)
                try:
                    # unlink() works for both files and symlinks, even broken ones
                    # This is more robust than checking exists() which returns False for broken symlinks
                    if latest_link.is_symlink() or latest_link.exists():
                        latest_link.unlink()
                except (OSError, PermissionError) as e:
                    # Log warning but continue - symlink is nice-to-have, not critical
                    logger.debug(f"Could not remove existing latest.log: {e}")
                except Exception as e:
                    # Catch any other unexpected errors
                    logger.debug(f"Unexpected error removing latest.log: {e}")

                # Create new symlink with proper error handling
                try:
                    # Use relative path for better portability
                    latest_link.symlink_to(log_file.name)
                except FileExistsError:
                    # This can happen in race conditions - try to remove and recreate
                    try:
                        latest_link.unlink()
                        latest_link.symlink_to(log_file.name)
                    except Exception as e:
                        logger.debug(
                            f"Could not recreate latest.log symlink after FileExistsError: {e}"
                        )
                except (OSError, NotImplementedError) as e:
                    # Handle platforms where symlinks aren't supported (e.g., Windows without admin)
                    # or filesystem doesn't support symlinks
                    logger.debug(f"Could not create latest.log symlink: {e}")
                    # Fallback: try to create a regular file with reference to actual log
                    try:
                        latest_link.write_text(f"Latest log: {log_file.name}\n")
                    except Exception:
                        pass  # Silently fail - logging should not break the application
                except Exception as e:
                    # Catch any other unexpected errors to ensure logging doesn't break
                    logger.debug(f"Unexpected error creating latest.log symlink: {e}")

        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter if json_format else detailed_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def cleanup_old_mpm_logs(
    log_dir: Optional[Path] = None, keep_count: Optional[int] = None
) -> int:
    """
    Clean up old MPM log files using time-based retention.

    WHY: This function now delegates to LogManager for unified log management
    with time-based retention instead of count-based.

    DESIGN DECISIONS:
    - Delegates to LogManager for consistency
    - Uses time-based retention (48 hours default)
    - Maintains backward compatibility

    Args:
        log_dir: Directory containing log files (defaults to .claude-mpm/logs)
        keep_count: Ignored (kept for backward compatibility)

    Returns:
        Number of log files deleted
    """
    try:
        from .log_manager import get_log_manager

        log_manager = get_log_manager()

        # Use LogManager's time-based cleanup (48 hours default)
        return log_manager.cleanup_old_mpm_logs(log_dir)
    except ImportError:
        # Fallback to old implementation if LogManager not available
        # Get retention count from configuration if not specified
        if keep_count is None:
            from claude_mpm.core.config_constants import ConfigConstants

            keep_count = (
                ConfigConstants.get_logging_setting("mpm_logs_retention_count") or 10
            )
        if log_dir is None:
            deployment_root = get_project_root()
            log_dir = deployment_root / ".claude-mpm" / "logs"

        if not log_dir.exists():
            return 0

        # Get all MPM log files
        log_files = sorted(
            log_dir.glob("mpm_*.log"), key=lambda p: p.stat().st_mtime, reverse=True
        )  # Newest first

        if len(log_files) <= keep_count:
            return 0  # Already within limit

        # Delete older files beyond keep_count
        deleted_count = 0
        for log_file in log_files[
            keep_count:
        ]:  # Keep only the most recent keep_count files
            try:
                log_file.unlink()
                deleted_count += 1
            except Exception:
                pass  # Ignore deletion errors

        return deleted_count


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"claude_mpm.{name}")


def setup_streaming_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Convenience function to setup a logger with streaming INFO support.

    Args:
        name: Logger name
        level: Log level (default: INFO)

    Returns:
        Logger configured with streaming handler
    """
    return setup_logging(name=name, level=level, use_rich=False, use_streaming=True)


def finalize_streaming_logs(logger: logging.Logger):
    """
    Finalize any active streaming INFO lines for a logger.

    This ensures the final INFO message remains visible by adding
    a newline to complete any streaming output.
    """
    for handler in logger.handlers:
        if isinstance(handler, StreamingHandler):
            handler.finalize_info_line()


def log_performance(func):
    """Decorator to log function execution time."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise

    return wrapper


async def log_async_performance(func):
    """Decorator to log async function execution time."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise

    return wrapper


class ProjectLogger:
    """
    Manages project-local logging in ./claude-mpm directory.

    This is a simplified version of the original ProjectLogger,
    focused on essential features for backwards compatibility.
    """

    def __init__(
        self,
        project_dir: Optional[Path] = None,
        log_level: str = "INFO",
        create_structure: bool = True,
    ):
        """Initialize project logger.

        Args:
            project_dir: Project directory (defaults to cwd)
            log_level: Logging level (INFO, DEBUG, OFF)
            create_structure: Whether to create directory structure
        """
        self.project_dir = project_dir or Path.cwd()
        self.claude_mpm_dir = self.project_dir / ".claude-mpm"
        self.log_level = LogLevel(log_level.lower())

        # Basic directory structure
        self.dirs = {
            "base": self.claude_mpm_dir,
            "logs": self.claude_mpm_dir / "logs",
            "logs_system": self.claude_mpm_dir / "logs" / "system",
            "logs_agents": self.claude_mpm_dir / "logs" / "agents",
            "logs_sessions": self.claude_mpm_dir / "logs" / "sessions",
            "stats": self.claude_mpm_dir / "stats",
        }

        if create_structure:
            for path in self.dirs.values():
                path.mkdir(parents=True, exist_ok=True)

        # Create session directory
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.session_start_time = datetime.now(timezone.utc)
        self.session_dir = self.dirs["logs_sessions"] / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Statistics tracking
        self.stats = defaultdict(
            lambda: {
                "total_calls": 0,
                "total_tokens": 0,
                "total_time_seconds": 0,
                "by_agent": defaultdict(
                    lambda: {
                        "calls": 0,
                        "tokens": 0,
                        "time_seconds": 0,
                        "success_rate": 0.0,
                        "tasks": [],
                    }
                ),
            }
        )

    def log_system(self, message: str, level: str = "INFO", component: str = "general"):
        """Log system-level message."""
        if self.log_level == LogLevel.OFF:
            return

        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "component": component,
            "message": message,
        }

        # Write to daily log file
        log_file = (
            self.dirs["logs_system"]
            / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        )
        with log_file.open("a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def log_agent_invocation(
        self,
        agent: str,
        task: str,
        prompt: str,
        response: str,
        execution_time: float,
        tokens: int,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log agent invocation with configurable detail level."""
        if self.log_level == LogLevel.OFF:
            return

        timestamp = datetime.now(timezone.utc).isoformat()

        # Update statistics
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.stats[today]["total_calls"] += 1
        self.stats[today]["total_tokens"] += tokens
        self.stats[today]["total_time_seconds"] += execution_time

        agent_stats = self.stats[today]["by_agent"][agent.lower()]
        agent_stats["calls"] += 1
        agent_stats["tokens"] += tokens
        agent_stats["time_seconds"] += execution_time

        # Prepare log entry
        log_entry = {
            "timestamp": timestamp,
            "agent": agent,
            "task": task[:200],
            "execution_time": execution_time,
            "tokens": tokens,
            "success": success,
            "metadata": metadata or {},
        }

        # Add full details in DEBUG mode
        if self.log_level == LogLevel.DEBUG:
            log_entry["prompt"] = prompt
            log_entry["response"] = response

        # Write to agent-specific log
        agent_log_dir = self.dirs["logs_agents"] / agent.lower()
        agent_log_dir.mkdir(exist_ok=True)

        daily_log = (
            agent_log_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        )
        with daily_log.open("a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        return {
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "start_time": self.session_id,
            "stats": self.stats.get(
                datetime.now(timezone.utc).strftime("%Y-%m-%d"), {}
            ),
        }


# Singleton instance for project logger
_project_logger = None


def get_project_logger(log_level: str = "INFO") -> ProjectLogger:
    """Get or create the project logger singleton.

    Args:
        log_level: Log level (INFO, DEBUG, OFF)

    Returns:
        ProjectLogger instance
    """
    global _project_logger
    if _project_logger is None:
        _project_logger = ProjectLogger(log_level=log_level)
    return _project_logger
