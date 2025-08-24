from pathlib import Path

"""
Async Claude Session Response Logger with Optimized Performance

High-performance async logging system with timestamp-based filenames to eliminate
concurrency issues and achieve near-zero performance overhead.

Key Features:
- Timestamp-based filenames with microsecond precision
- Async I/O with fire-and-forget pattern
- Queue-based background writing
- Optional OS-native logging format
- Zero blocking on main thread
- Configuration via .claude-mpm/configuration.yaml
"""

import json
import logging
import logging.handlers
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from queue import Full, Queue
from threading import Lock, Thread
from typing import Any, Dict, Optional

from claude_mpm.core.constants import PerformanceConfig, SystemLimits, TimeoutConfig

# Import configuration manager
from ..core.config import Config

logger = logging.getLogger(__name__)


class LogFormat(Enum):
    """Supported log formats for response storage."""

    JSON = "json"
    SYSLOG = "syslog"
    JOURNALD = "journald"


@dataclass
class LogEntry:
    """Represents a log entry to be written."""

    timestamp: str
    agent: str  # Standardized field name
    session_id: str
    request: str  # Standardized field name
    response: str  # Standardized field name
    metadata: Dict[str, Any]
    microseconds: int


class AsyncSessionLogger:
    """
    High-performance async logger with timestamp-based filenames.

    Features:
    - Non-blocking async writes with background queue processing
    - Timestamp-based filenames to eliminate lookup overhead
    - Configurable log formats (JSON, syslog, journald)
    - Fire-and-forget pattern for zero latency impact
    - Graceful degradation on errors
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        log_format: Optional[LogFormat] = None,
        max_queue_size: Optional[int] = None,
        enable_async: Optional[bool] = None,
        enable_compression: Optional[bool] = None,
        config: Optional[Config] = None,
    ):
        """
        Initialize the async session logger.

        Args:
            base_dir: Base directory for responses (overrides config)
            log_format: Format to use for logging (overrides config)
            max_queue_size: Maximum queue size for async writes (overrides config)
            enable_async: Enable async writing (overrides config)
            enable_compression: Enable gzip compression for JSON logs (overrides config)
            config: Configuration instance to use (creates new if not provided)
        """
        # Load configuration from YAML file or use provided config
        if config is None:
            config = Config()
        self.config = config

        # Get response logging configuration section
        response_config = self.config.get("response_logging", {})

        # Apply configuration with parameter overrides
        self.base_dir = Path(
            base_dir
            or response_config.get("session_directory", ".claude-mpm/responses")
        )

        # Convert log format string to enum
        format_str = response_config.get("format", "json").lower()
        if log_format is not None:
            self.log_format = log_format
        elif format_str == "syslog":
            self.log_format = LogFormat.SYSLOG
        elif format_str == "journald":
            self.log_format = LogFormat.JOURNALD
        else:
            self.log_format = LogFormat.JSON

        self.max_queue_size = (
            max_queue_size
            if max_queue_size is not None
            else response_config.get("max_queue_size", SystemLimits.MAX_QUEUE_SIZE)
        )

        # Handle async configuration with backward compatibility
        if enable_async is not None:
            self.enable_async = enable_async
        else:
            # Check configuration first, then environment variables for backward compatibility
            self.enable_async = response_config.get("use_async", True)
            # Override with environment variable if set (backward compatibility)
            if os.environ.get("CLAUDE_USE_ASYNC_LOG"):
                self.enable_async = (
                    os.environ.get("CLAUDE_USE_ASYNC_LOG", "true").lower() == "true"
                )

        # Check debug sync mode (forces synchronous for debugging)
        if (
            response_config.get("debug_sync", False)
            or os.environ.get("CLAUDE_LOG_SYNC", "").lower() == "true"
        ):
            logger.info("Debug sync mode enabled - forcing synchronous logging")
            self.enable_async = False

        self.enable_compression = (
            enable_compression
            if enable_compression is not None
            else response_config.get("enable_compression", False)
        )

        # Create base directory
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Session management
        self.session_id = self._get_claude_session_id()

        # Async infrastructure
        self._queue: Queue = Queue(maxsize=self.max_queue_size)
        self._worker_thread: Optional[Thread] = None
        self._shutdown = False
        self._lock = Lock()

        # Statistics
        self.stats = {
            "logged": 0,
            "queued": 0,
            "dropped": 0,
            "errors": 0,
            "avg_write_time_ms": 0.0,
        }

        # Initialize format-specific handlers
        self._init_format_handler()

        # Start background worker if async enabled
        if self.enable_async:
            self._start_worker()

    def _get_claude_session_id(self) -> str:
        """Get or generate a Claude session ID."""
        # Check environment variables in order of preference
        for env_var in ["CLAUDE_SESSION_ID", "ANTHROPIC_SESSION_ID", "SESSION_ID"]:
            session_id = os.environ.get(env_var)
            if session_id:
                logger.info(f"Using session ID from {env_var}: {session_id}")
                return session_id

        # Generate timestamp-based session ID
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Generated session ID: {session_id}")
        return session_id

    def _init_format_handler(self):
        """Initialize format-specific logging handlers."""
        if self.log_format == LogFormat.SYSLOG:
            # Setup syslog handler for ultra-fast OS-level logging
            try:
                if sys.platform == "darwin":
                    address = "/var/run/syslog"
                elif sys.platform.startswith("linux"):
                    address = "/dev/log"
                else:
                    address = ("localhost", 514)

                self.syslog_handler = logging.handlers.SysLogHandler(address=address)
                self.syslog_handler.setFormatter(
                    logging.Formatter("claude-mpm[%(process)d]: %(message)s")
                )
                logger.info("Initialized syslog handler")
            except Exception as e:
                logger.warning(f"Failed to init syslog, falling back to JSON: {e}")
                self.log_format = LogFormat.JSON

        elif self.log_format == LogFormat.JOURNALD:
            # Use systemd journal for Linux systems
            try:
                from systemd.journal import JournalHandler

                self.journal_handler = JournalHandler()
                self.journal_handler.setFormatter(logging.Formatter("%(message)s"))
                logger.info("Initialized journald handler")
            except ImportError:
                logger.warning("systemd not available, falling back to JSON")
                self.log_format = LogFormat.JSON

    def _start_worker(self):
        """Start the background worker thread for async writes."""
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._shutdown = False
                self._worker_thread = Thread(
                    target=self._process_queue, name="AsyncLoggerWorker", daemon=True
                )
                self._worker_thread.start()
                logger.debug("Started async logger worker thread")

    def _process_queue(self):
        """Background worker to process the log queue."""
        write_times = []

        while not self._shutdown:
            try:
                # Get entry with timeout to allow shutdown checks
                entry = self._queue.get(timeout=TimeoutConfig.QUEUE_GET_TIMEOUT)

                # Time the write operation
                start_time = time.perf_counter()
                self._write_entry(entry)
                write_time = (
                    time.perf_counter() - start_time
                ) * PerformanceConfig.SECONDS_TO_MS

                # Update statistics
                write_times.append(write_time)
                if len(write_times) > 100:
                    write_times = write_times[-100:]  # Keep last 100

                with self._lock:
                    self.stats["logged"] += 1
                    self.stats["avg_write_time_ms"] = sum(write_times) / len(
                        write_times
                    )

            except Exception as e:
                # Check if it's a timeout (queue.Empty) or real error
                if "Empty" not in str(type(e).__name__):
                    logger.error(f"Error in async worker: {e}", exc_info=True)
                    with self._lock:
                        self.stats["errors"] += 1
                # Otherwise it's just a timeout, continue to check shutdown

    def _write_entry(self, entry: LogEntry):
        """Write a log entry to disk or system log."""
        try:
            if self.log_format == LogFormat.JSON:
                self._write_json_entry(entry)
            elif self.log_format == LogFormat.SYSLOG:
                self._write_syslog_entry(entry)
            elif self.log_format == LogFormat.JOURNALD:
                self._write_journald_entry(entry)
        except Exception as e:
            logger.error(f"Failed to write log entry: {e}", exc_info=True)
            with self._lock:
                self.stats["errors"] += 1

    def _generate_filename(self, entry: LogEntry) -> str:
        """
        Generate a flat filename with session ID, agent, and timestamp.

        Args:
            entry: Log entry with session, agent, and timestamp info

        Returns:
            Filename in format: [session_id]-[agent]-timestamp.json
        """
        # Format timestamp for filename (remove special chars)
        timestamp_str = (
            entry.timestamp.replace(":", "").replace("-", "").replace(".", "_")
        )

        # Create filename: session_id-agent-timestamp.json
        filename = f"{entry.session_id}-{entry.agent}-{timestamp_str}.json"
        if self.enable_compression:
            filename += ".gz"
        return filename

    def _write_json_entry(self, entry: LogEntry):
        """Write entry as JSON file with timestamp-based filename."""
        # Ensure base directory exists (flat structure, no subdirs)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Generate flat filename
        filename = self._generate_filename(entry)
        file_path = self.base_dir / filename

        # Prepare data (exclude microseconds field which is internal only)
        data = asdict(entry)
        # Remove internal-only field
        data.pop("microseconds", None)

        # Write file
        if self.enable_compression:
            import gzip

            with gzip.open(file_path, "wt", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Wrote log entry to {file_path}")

    def _write_syslog_entry(self, entry: LogEntry):
        """Write entry to syslog for OS-level performance."""
        if hasattr(self, "syslog_handler"):
            # Format as structured log message with standardized field names
            msg = (
                f"agent={entry.agent} "
                f"session={entry.session_id} "
                f'request="{entry.request[:100]}" '
                f"response_len={len(entry.response)} "
                f"metadata={json.dumps(entry.metadata)}"
            )

            record = logging.LogRecord(
                name="claude-mpm",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=msg,
                args=(),
                exc_info=None,
            )

            self.syslog_handler.emit(record)

    def _write_journald_entry(self, entry: LogEntry):
        """Write entry to systemd journal."""
        if hasattr(self, "journal_handler"):
            # Create structured journal entry with standardized field names
            record = logging.LogRecord(
                name="claude-mpm",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"Claude MPM Response: {entry.request[:100]}",
                args=(),
                exc_info=None,
            )

            # Add structured fields with standardized names
            record.__dict__.update(
                {
                    "AGENT": entry.agent,
                    "SESSION_ID": entry.session_id,
                    "REQUEST": entry.request,
                    "RESPONSE_LENGTH": len(entry.response),
                    "METADATA": json.dumps(entry.metadata),
                }
            )

            self.journal_handler.emit(record)

    def log_response(
        self,
        request_summary: str,
        response_content: str,
        metadata: Optional[Dict[str, Any]] = None,
        agent: Optional[str] = None,
    ) -> bool:
        """
        Log a response with fire-and-forget async pattern.

        Args:
            request_summary: Brief summary of the request
            response_content: The full response content
            metadata: Optional metadata (agent name, model, etc.)
            agent: Optional agent name (overrides metadata)

        Returns:
            True if queued successfully, False if dropped
        """
        # Extract agent name from parameter, metadata, or use default
        agent_name = "unknown"
        if agent:
            agent_name = agent.replace(" ", "_").lower()
        elif metadata and "agent" in metadata:
            agent_name = metadata["agent"].replace(" ", "_").lower()

        # Create timestamp with microsecond precision
        now = datetime.now()
        timestamp = now.isoformat()
        microseconds = now.microsecond

        # Create log entry with standardized field names
        entry = LogEntry(
            timestamp=timestamp,
            agent=agent_name,  # Standardized field name
            session_id=self.session_id,
            request=request_summary,  # Standardized field name
            response=response_content,  # Standardized field name
            metadata=metadata or {},
            microseconds=microseconds,
        )

        # Queue for async processing or write directly
        if self.enable_async:
            try:
                self._queue.put_nowait(entry)
                with self._lock:
                    self.stats["queued"] += 1
                return True
            except Full:
                # Queue is full, drop the entry (fire-and-forget)
                logger.warning("Log queue full, dropping entry")
                with self._lock:
                    self.stats["dropped"] += 1
                return False
        else:
            # Synchronous write for debugging
            self._write_entry(entry)
            return True

    def flush(self, timeout: float = 5.0) -> bool:
        """
        Flush pending log entries with timeout.

        Args:
            timeout: Maximum time to wait for flush

        Returns:
            True if all entries flushed, False if timeout
        """
        if not self.enable_async:
            return True

        start_time = time.time()
        while not self._queue.empty():
            if time.time() - start_time > timeout:
                logger.warning(
                    f"Flush timeout with {self._queue.qsize()} entries remaining"
                )
                return False
            time.sleep(0.01)

        return True

    def shutdown(self, timeout: float = 5.0):
        """
        Gracefully shutdown the logger.

        Args:
            timeout: Maximum time to wait for shutdown
        """
        if self.enable_async:
            logger.info("Shutting down async logger")

            # Signal shutdown
            self._shutdown = True

            # Wait for worker to finish
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout)

                if self._worker_thread.is_alive():
                    logger.warning("Worker thread did not shutdown cleanly")

            # Log final statistics
            logger.info(f"Logger stats: {self.stats}")

    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics."""
        with self._lock:
            return self.stats.copy()

    def set_session_id(self, session_id: str):
        """Set a new session ID."""
        self.session_id = session_id
        logger.info(f"Session ID updated to: {session_id}")

    def is_enabled(self) -> bool:
        """Check if logging is enabled."""
        return True  # Always enabled in this implementation


# Singleton instance with lazy initialization
_logger_instance: Optional[AsyncSessionLogger] = None
_logger_lock = Lock()


def get_async_logger(
    log_format: Optional[LogFormat] = None,
    enable_async: Optional[bool] = None,
    config: Optional[Config] = None,
) -> AsyncSessionLogger:
    """
    Get the singleton async logger instance.

    Args:
        log_format: Optional log format override
        enable_async: Enable async mode override
        config: Optional configuration instance to use

    Returns:
        The shared AsyncSessionLogger instance
    """
    global _logger_instance

    with _logger_lock:
        if _logger_instance is None:
            # Load configuration if not provided
            if config is None:
                config = Config()

            # Get response logging configuration
            response_config = config.get("response_logging", {})

            # Determine log format
            if log_format is None:
                # Check configuration first
                format_str = response_config.get("format", "json").lower()

                # Check environment for backward compatibility
                format_env = os.environ.get("CLAUDE_LOG_FORMAT", "").lower()
                if format_env:
                    logger.info(
                        f"Using CLAUDE_LOG_FORMAT environment variable (deprecated): {format_env}"
                    )
                    format_str = format_env

                if format_str == "syslog":
                    log_format = LogFormat.SYSLOG
                elif format_str == "journald":
                    log_format = LogFormat.JOURNALD
                else:
                    log_format = LogFormat.JSON

            # Determine async mode if not specified
            if enable_async is None:
                # Configuration takes precedence
                enable_async = response_config.get("use_async", True)

                # Check environment for backward compatibility
                if os.environ.get("CLAUDE_USE_ASYNC_LOG"):
                    env_async = (
                        os.environ.get("CLAUDE_USE_ASYNC_LOG", "true").lower() == "true"
                    )
                    logger.info(
                        f"Using CLAUDE_USE_ASYNC_LOG environment variable (deprecated): {env_async}"
                    )
                    enable_async = env_async

                # Debug sync mode overrides everything
                if (
                    response_config.get("debug_sync", False)
                    or os.environ.get("CLAUDE_LOG_SYNC", "").lower() == "true"
                ):
                    if os.environ.get("CLAUDE_LOG_SYNC"):
                        logger.info(
                            "Using CLAUDE_LOG_SYNC environment variable (deprecated)"
                        )
                    enable_async = False

            _logger_instance = AsyncSessionLogger(
                log_format=log_format, enable_async=enable_async, config=config
            )

        return _logger_instance


def log_response_async(
    request_summary: str,
    response_content: str,
    metadata: Optional[Dict[str, Any]] = None,
    agent: Optional[str] = None,
) -> bool:
    """
    Convenience function for async response logging.

    Args:
        request_summary: Brief summary of the request
        response_content: The full response content
        metadata: Optional metadata
        agent: Optional agent name

    Returns:
        True if logged/queued successfully
    """
    logger = get_async_logger()
    return logger.log_response(request_summary, response_content, metadata, agent)


# Cleanup on module unload
import atexit


def _cleanup():
    """Cleanup function called on exit."""
    global _logger_instance
    if _logger_instance:
        _logger_instance.shutdown()


atexit.register(_cleanup)
