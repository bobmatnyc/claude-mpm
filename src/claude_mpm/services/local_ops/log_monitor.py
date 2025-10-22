"""
Log Monitor for Claude MPM Framework
======================================

WHY: Provides real-time log file monitoring to detect error patterns that
indicate imminent crashes (OOM, exceptions, segfaults) BEFORE they occur.

DESIGN DECISION: Uses watchdog library for efficient OS-level file system
monitoring. Avoids polling by receiving file modification events from the OS.

ARCHITECTURE:
- Watchdog-based file system monitoring (OS-level events)
- Regex-based pattern matching for error detection
- Configurable error patterns with severity levels
- Rolling window of recent matches per deployment
- Callback system for pattern match alerts
- Thread-safe with proper locking

USAGE:
    monitor = LogMonitor()
    monitor.initialize()

    # Add error patterns
    monitor.add_pattern(r"OutOfMemoryError", severity="CRITICAL")
    monitor.add_pattern(r"Exception:", severity="ERROR")

    # Start monitoring a log file
    monitor.start_monitoring(
        log_file="/var/log/app.log",
        deployment_id="my-app"
    )

    # Get recent matches
    matches = monitor.get_recent_matches(deployment_id, limit=10)
"""

import re
import threading
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from claude_mpm.core.logger import get_logger
from claude_mpm.services.core.base import SyncBaseService
from claude_mpm.services.core.interfaces.stability import ILogMonitor
from claude_mpm.services.core.models.stability import LogPatternMatch


class LogFileHandler(FileSystemEventHandler):
    """
    File system event handler for log file monitoring.

    WHY: Receives OS-level file modification events and triggers
    pattern matching on new log lines.
    """

    def __init__(
        self,
        log_file: str,
        deployment_id: str,
        on_new_lines: Callable[[str, List[str]], None],
    ):
        """
        Initialize log file handler.

        Args:
            log_file: Path to log file being monitored
            deployment_id: Deployment identifier
            on_new_lines: Callback for new lines: (deployment_id, lines)
        """
        super().__init__()
        self.log_file = Path(log_file).resolve()
        self.deployment_id = deployment_id
        self.on_new_lines = on_new_lines
        self.last_position = 0

        # Initialize to end of file
        if self.log_file.exists():
            self.last_position = self.log_file.stat().st_size

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Handle file modification events.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        # Check if this is our log file
        event_path = Path(event.src_path).resolve()
        if event_path != self.log_file:
            return

        # Read new lines
        try:
            new_lines = self._read_new_lines()
            if new_lines:
                self.on_new_lines(self.deployment_id, new_lines)
        except Exception as e:
            # Log error but don't crash the monitoring thread
            get_logger().error(f"Error reading new log lines: {e}")

    def _read_new_lines(self) -> List[str]:
        """
        Read new lines from log file since last read.

        Returns:
            List of new lines
        """
        if not self.log_file.exists():
            return []

        new_lines = []

        with Path(self.log_file).open(encoding="utf-8", errors="ignore") as f:
            # Seek to last position
            f.seek(self.last_position)

            # Read new lines
            for line in f:
                new_lines.append(line.rstrip("\n\r"))

            # Update position
            self.last_position = f.tell()

        return new_lines


class LogMonitor(SyncBaseService, ILogMonitor):
    """
    Real-time log file monitoring service.

    WHY: Provides early warning of critical errors by monitoring log files
    in real-time and detecting patterns that indicate imminent failures.

    Thread Safety: All public methods are thread-safe with proper locking.
    """

    # Default error patterns
    DEFAULT_PATTERNS = [
        (r"OutOfMemoryError", "CRITICAL"),
        (r"Segmentation fault", "CRITICAL"),
        (r"Exception:", "ERROR"),
        (r"Traceback", "ERROR"),
        (r"Error:", "ERROR"),
        (r"FATAL", "CRITICAL"),
        (r"Database connection failed", "ERROR"),
        (r"Connection refused", "WARNING"),
        (r"Connection timeout", "WARNING"),
    ]

    def __init__(self, match_history_limit: int = 100):
        """
        Initialize log monitor.

        Args:
            match_history_limit: Number of matches to keep per deployment (default: 100)
        """
        super().__init__("LogMonitor")
        self.match_history_limit = match_history_limit

        # Error patterns: List[(pattern, severity)]
        self._patterns: List[Tuple[re.Pattern, str]] = []

        # Add default patterns
        for pattern, severity in self.DEFAULT_PATTERNS:
            self._patterns.append((re.compile(pattern), severity))

        # Watchdog observer and handlers
        self._observer: Optional[Observer] = None
        self._handlers: Dict[str, LogFileHandler] = {}  # deployment_id -> handler

        # Match history: deployment_id -> List[LogPatternMatch]
        self._match_history: Dict[str, List[LogPatternMatch]] = defaultdict(list)

        # Match callbacks
        self._match_callbacks: List[Callable[[str, LogPatternMatch], None]] = []

        # Thread safety
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        """
        Initialize the log monitor.

        Returns:
            True if initialization successful
        """
        try:
            # Create watchdog observer
            self._observer = Observer()
            self._observer.start()

            self._initialized = True
            self.log_info(
                f"Log monitor initialized with {len(self._patterns)} patterns"
            )
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize: {e}")
            return False

    def shutdown(self) -> None:
        """Shutdown log monitor and stop all monitoring."""
        # Stop all monitoring
        with self._lock:
            deployment_ids = list(self._handlers.keys())

        for deployment_id in deployment_ids:
            self.stop_monitoring(deployment_id)

        # Stop observer
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)

        self._shutdown = True
        self.log_info("Log monitor shutdown complete")

    def start_monitoring(self, log_file: str, deployment_id: str) -> None:
        """
        Start monitoring a log file for error patterns.

        WHY: Begins watching the log file for new entries. Uses OS-level
        file system events for efficiency.

        Args:
            log_file: Path to log file to monitor
            deployment_id: Deployment identifier for callbacks
        """
        log_path = Path(log_file).resolve()

        if not log_path.exists():
            self.log_warning(f"Log file does not exist: {log_file}")
            # Still create handler - it will start monitoring when file is created
            # return

        with self._lock:
            # Check if already monitoring
            if deployment_id in self._handlers:
                self.log_warning(f"Already monitoring logs for {deployment_id}")
                return

            # Create handler
            handler = LogFileHandler(
                log_file=str(log_path),
                deployment_id=deployment_id,
                on_new_lines=self._process_new_lines,
            )

            # Schedule handler with observer
            if self._observer:
                # Watch the directory containing the log file
                watch_dir = log_path.parent
                self._observer.schedule(handler, str(watch_dir), recursive=False)

            self._handlers[deployment_id] = handler

        self.log_info(f"Started monitoring log file for {deployment_id}: {log_file}")

    def stop_monitoring(self, deployment_id: str) -> None:
        """
        Stop monitoring a deployment's log file.

        Args:
            deployment_id: Deployment identifier
        """
        with self._lock:
            handler = self._handlers.pop(deployment_id, None)
            if handler and self._observer:
                # Unschedule handler
                self._observer.unschedule_all()

                # Reschedule remaining handlers
                for remaining_handler in self._handlers.values():
                    watch_dir = remaining_handler.log_file.parent
                    self._observer.schedule(
                        remaining_handler, str(watch_dir), recursive=False
                    )

        if handler:
            self.log_info(f"Stopped monitoring logs for {deployment_id}")

    def add_pattern(self, pattern: str, severity: str = "ERROR") -> None:
        """
        Add an error pattern to monitor.

        Args:
            pattern: Regex pattern to match
            severity: Error severity (ERROR, CRITICAL, WARNING)
        """
        with self._lock:
            compiled_pattern = re.compile(pattern)
            self._patterns.append((compiled_pattern, severity))

        self.log_debug(f"Added pattern: {pattern} (severity: {severity})")

    def get_recent_matches(
        self, deployment_id: str, limit: int = 10
    ) -> List[LogPatternMatch]:
        """
        Get recent pattern matches for a deployment.

        Args:
            deployment_id: Deployment identifier
            limit: Maximum number of matches to return

        Returns:
            List of LogPatternMatch objects, newest first
        """
        with self._lock:
            matches = self._match_history.get(deployment_id, [])
            return list(reversed(matches[-limit:]))

    def register_match_callback(
        self, callback: Callable[[str, LogPatternMatch], None]
    ) -> None:
        """
        Register callback for pattern matches.

        Args:
            callback: Function called with (deployment_id, match) when pattern detected
        """
        with self._lock:
            self._match_callbacks.append(callback)
            self.log_debug(f"Registered match callback: {callback.__name__}")

    def _process_new_lines(self, deployment_id: str, lines: List[str]) -> None:
        """
        Process new log lines for pattern matching.

        Args:
            deployment_id: Deployment identifier
            lines: New log lines to process
        """
        for line in lines:
            # Check against all patterns
            for pattern, severity in self._patterns:
                if pattern.search(line):
                    # Create match
                    match = LogPatternMatch(
                        deployment_id=deployment_id,
                        pattern=pattern.pattern,
                        line=line,
                        severity=severity,
                    )

                    # Add to history
                    with self._lock:
                        self._match_history[deployment_id].append(match)

                        # Trim history
                        if (
                            len(self._match_history[deployment_id])
                            > self.match_history_limit
                        ):
                            self._match_history[deployment_id] = self._match_history[
                                deployment_id
                            ][-self.match_history_limit :]

                    # Log match
                    self.log_warning(
                        f"Pattern matched in {deployment_id}: "
                        f"[{severity}] {pattern.pattern[:50]}"
                    )

                    # Trigger callbacks
                    self._trigger_match_callbacks(deployment_id, match)

                    # Only match first pattern per line
                    break

    def _trigger_match_callbacks(
        self, deployment_id: str, match: LogPatternMatch
    ) -> None:
        """
        Trigger registered callbacks for pattern matches.

        Args:
            deployment_id: Deployment that has a match
            match: LogPatternMatch with pattern details
        """
        for callback in self._match_callbacks:
            try:
                callback(deployment_id, match)
            except Exception as e:
                self.log_error(f"Error in match callback {callback.__name__}: {e}")


__all__ = ["LogMonitor"]
