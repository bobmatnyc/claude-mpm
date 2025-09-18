"""Centralized logging utilities for Claude MPM.

This module provides standardized logging initialization and configuration
to replace duplicate logger initialization code across 76+ files.
"""

import logging
import logging.handlers
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.constants import Defaults

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================


class LoggingConfig:
    """Logging configuration settings."""

    # Log levels
    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    # Default formats
    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    SIMPLE_FORMAT = "%(levelname)s: %(message)s"
    DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    JSON_FORMAT = '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'

    # Date formats
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

    # File settings
    MAX_BYTES = 5 * 1024 * 1024  # 5MB - lowered for better rotation testing
    BACKUP_COUNT = 5
    ROTATION_INTERVAL = "midnight"  # Daily rotation at midnight
    ROTATION_BACKUP_COUNT = 7  # Keep 7 days of daily logs

    # Component-specific log names
    COMPONENT_NAMES = {
        "agent": "claude_mpm.agent",
        "service": "claude_mpm.service",
        "core": "claude_mpm.core",
        "cli": "claude_mpm.cli",
        "hooks": "claude_mpm.hooks",
        "monitor": "claude_mpm.monitor",
        "socketio": "claude_mpm.socketio",
        "memory": "claude_mpm.memory",
        "config": "claude_mpm.config",
        "utils": "claude_mpm.utils",
    }


# ==============================================================================
# LOGGER FACTORY
# ==============================================================================


class LoggerFactory:
    """Factory for creating standardized loggers."""

    _initialized = False
    _log_dir: Optional[Path] = None
    _log_level: str = Defaults.DEFAULT_LOG_LEVEL
    _handlers: Dict[str, logging.Handler] = {}

    @classmethod
    def initialize(
        cls,
        log_level: Optional[str] = None,
        log_dir: Optional[Path] = None,
        log_to_file: bool = False,
        log_format: Optional[str] = None,
        date_format: Optional[str] = None,
    ) -> None:
        """Initialize the logging system globally.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            log_to_file: Whether to log to files
            log_format: Custom log format string
            date_format: Custom date format string
        """
        if cls._initialized:
            return

        cls._log_level = log_level or os.environ.get(
            "CLAUDE_MPM_LOG_LEVEL", Defaults.DEFAULT_LOG_LEVEL
        )
        cls._log_dir = log_dir

        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(LoggingConfig.LEVELS.get(cls._log_level, logging.INFO))

        # Remove existing handlers
        root_logger.handlers = []

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LoggingConfig.LEVELS.get(cls._log_level, logging.INFO))
        console_formatter = logging.Formatter(
            log_format or LoggingConfig.DEFAULT_FORMAT,
            date_format or LoggingConfig.DATE_FORMAT,
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        cls._handlers["console"] = console_handler

        # File handler (optional)
        if log_to_file and cls._log_dir:
            cls._setup_file_handler(log_format, date_format)

        cls._initialized = True

    @classmethod
    def _setup_file_handler(
        cls,
        log_format: Optional[str] = None,
        date_format: Optional[str] = None,
    ) -> None:
        """Set up file logging handlers with both size and time-based rotation."""
        if not cls._log_dir:
            return

        # Ensure log directory exists
        cls._log_dir.mkdir(parents=True, exist_ok=True)

        formatter = logging.Formatter(
            log_format or LoggingConfig.DETAILED_FORMAT,
            date_format or LoggingConfig.DATE_FORMAT,
        )

        # 1. Size-based rotating file handler (for current active log)
        log_file = cls._log_dir / "claude_mpm.log"
        size_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LoggingConfig.MAX_BYTES,
            backupCount=LoggingConfig.BACKUP_COUNT,
        )
        size_handler.setLevel(LoggingConfig.LEVELS.get(cls._log_level, logging.INFO))
        size_handler.setFormatter(formatter)
        logging.getLogger().addHandler(size_handler)
        cls._handlers["file"] = size_handler

        # 2. Time-based rotating file handler (daily rotation)
        daily_log_file = cls._log_dir / "claude_mpm_daily.log"
        time_handler = logging.handlers.TimedRotatingFileHandler(
            daily_log_file,
            when=LoggingConfig.ROTATION_INTERVAL,
            interval=1,
            backupCount=LoggingConfig.ROTATION_BACKUP_COUNT,
        )
        time_handler.setLevel(LoggingConfig.LEVELS.get(cls._log_level, logging.INFO))
        time_handler.setFormatter(formatter)

        # Add suffix to rotated files (e.g., claude_mpm_daily.log.2024-09-18)
        time_handler.suffix = "%Y-%m-%d"

        logging.getLogger().addHandler(time_handler)
        cls._handlers["file_daily"] = time_handler

    @classmethod
    def get_logger(
        cls,
        name: str,
        component: Optional[str] = None,
        level: Optional[str] = None,
    ) -> logging.Logger:
        """Get a standardized logger instance.

        Args:
            name: Logger name (typically __name__)
            component: Optional component category for namespacing
            level: Optional specific log level for this logger

        Returns:
            Configured logger instance
        """
        # Initialize if needed
        if not cls._initialized:
            cls.initialize()

        # Apply component namespace if specified
        if component and component in LoggingConfig.COMPONENT_NAMES:
            logger_name = LoggingConfig.COMPONENT_NAMES[component]
            if not name.startswith(logger_name):
                logger_name = f"{logger_name}.{name.split('.')[-1]}"
        else:
            logger_name = name

        logger = logging.getLogger(logger_name)

        # Set specific level if requested
        if level and level in LoggingConfig.LEVELS:
            logger.setLevel(LoggingConfig.LEVELS[level])

        return logger

    @classmethod
    def set_level(cls, level: str) -> None:
        """Change the global logging level.

        Args:
            level: New logging level
        """
        if level not in LoggingConfig.LEVELS:
            return

        cls._log_level = level
        log_level = LoggingConfig.LEVELS[level]

        # Update root logger
        logging.getLogger().setLevel(log_level)

        # Update all handlers
        for handler in cls._handlers.values():
            handler.setLevel(log_level)

    @classmethod
    def add_handler(cls, name: str, handler: logging.Handler) -> None:
        """Add a custom handler to the logging system.

        Args:
            name: Handler identifier
            handler: The handler to add
        """
        logging.getLogger().addHandler(handler)
        cls._handlers[name] = handler

    @classmethod
    def remove_handler(cls, name: str) -> None:
        """Remove a handler from the logging system.

        Args:
            name: Handler identifier to remove
        """
        if name in cls._handlers:
            logging.getLogger().removeHandler(cls._handlers[name])
            del cls._handlers[name]


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


@lru_cache(maxsize=128)
def get_logger(
    name: str,
    component: Optional[str] = None,
    level: Optional[str] = None,
) -> logging.Logger:
    """Get a standardized logger instance (cached).

    This is the primary function that should be used throughout the codebase
    to get logger instances. It replaces the pattern:
        import logging
        logger = logging.getLogger(__name__)

    With:
        from claude_mpm.core.logging_utils import get_logger
        logger = get_logger(__name__)

    Args:
        name: Logger name (typically __name__)
        component: Optional component category for namespacing
        level: Optional specific log level for this logger

    Returns:
        Configured logger instance
    """
    return LoggerFactory.get_logger(name, component, level)


def initialize_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[Path] = None,
    log_to_file: bool = False,
    log_format: Optional[str] = None,
) -> None:
    """Initialize the logging system with standard configuration.

    This should be called once at application startup.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_to_file: Whether to log to files
        log_format: Custom log format string
    """
    LoggerFactory.initialize(
        log_level=log_level,
        log_dir=log_dir,
        log_to_file=log_to_file,
        log_format=log_format,
    )


def set_log_level(level: str) -> None:
    """Change the global logging level dynamically.

    Args:
        level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    LoggerFactory.set_level(level)


def get_component_logger(component: str, name: Optional[str] = None) -> logging.Logger:
    """Get a logger for a specific component.

    Args:
        component: Component name (agent, service, core, etc.)
        name: Optional specific name within component

    Returns:
        Component-specific logger
    """
    if name is None:
        name = component
    return get_logger(name, component=component)


# ==============================================================================
# STRUCTURED LOGGING
# ==============================================================================


class StructuredLogger:
    """Wrapper for structured logging with context."""

    def __init__(self, logger: logging.Logger):
        """Initialize structured logger.

        Args:
            logger: Base logger instance
        """
        self.logger = logger
        self.context: Dict[str, Any] = {}

    def with_context(self, **kwargs) -> "StructuredLogger":
        """Add context to all log messages.

        Args:
            **kwargs: Context key-value pairs

        Returns:
            Self for chaining
        """
        self.context.update(kwargs)
        return self

    def clear_context(self) -> None:
        """Clear all context."""
        self.context.clear()

    def _format_message(self, message: str) -> str:
        """Format message with context.

        Args:
            message: Base message

        Returns:
            Formatted message with context
        """
        if not self.context:
            return message

        context_str = " ".join(f"{k}={v}" for k, v in self.context.items())
        return f"{message} [{context_str}]"

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self.logger.debug(self._format_message(message), **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self.logger.info(self._format_message(message), **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self.logger.warning(self._format_message(message), **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self.logger.error(self._format_message(message), **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context."""
        self.logger.critical(self._format_message(message), **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback and context."""
        self.logger.exception(self._format_message(message), **kwargs)


def get_structured_logger(
    name: str, component: Optional[str] = None, **context
) -> StructuredLogger:
    """Get a structured logger with initial context.

    Args:
        name: Logger name
        component: Optional component category
        **context: Initial context key-value pairs

    Returns:
        Structured logger instance
    """
    base_logger = get_logger(name, component)
    structured = StructuredLogger(base_logger)
    if context:
        structured.with_context(**context)
    return structured


# ==============================================================================
# PERFORMANCE LOGGING
# ==============================================================================


class PerformanceLogger:
    """Logger for performance metrics and timing."""

    def __init__(self, logger: logging.Logger):
        """Initialize performance logger.

        Args:
            logger: Base logger instance
        """
        self.logger = logger
        self._timers: Dict[str, float] = {}

    def start_timer(self, operation: str) -> None:
        """Start timing an operation.

        Args:
            operation: Operation identifier
        """
        import time

        self._timers[operation] = time.time()

    def end_timer(self, operation: str, log_level: str = "INFO") -> float:
        """End timing and log the duration.

        Args:
            operation: Operation identifier
            log_level: Level to log at

        Returns:
            Duration in seconds
        """
        import time

        if operation not in self._timers:
            return 0.0

        duration = time.time() - self._timers[operation]
        del self._timers[operation]

        level = LoggingConfig.LEVELS.get(log_level, logging.INFO)
        self.logger.log(
            level, f"Operation '{operation}' completed in {duration:.3f} seconds"
        )

        return duration

    def log_memory_usage(self, context: str = "") -> None:
        """Log current memory usage.

        Args:
            context: Optional context string
        """
        import os

        import psutil

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)

        ctx = f" [{context}]" if context else ""
        self.logger.info(f"Memory usage{ctx}: {memory_mb:.2f} MB")

    def log_metrics(self, metrics: Dict[str, Any], context: str = "") -> None:
        """Log performance metrics.

        Args:
            metrics: Dictionary of metric name to value
            context: Optional context string
        """
        ctx = f" [{context}]" if context else ""
        metrics_str = ", ".join(f"{k}={v}" for k, v in metrics.items())
        self.logger.info(f"Performance metrics{ctx}: {metrics_str}")


def get_performance_logger(name: str) -> PerformanceLogger:
    """Get a performance logger instance.

    Args:
        name: Logger name

    Returns:
        Performance logger instance
    """
    base_logger = get_logger(name)
    return PerformanceLogger(base_logger)
