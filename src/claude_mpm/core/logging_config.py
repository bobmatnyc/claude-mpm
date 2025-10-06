"""
Centralized logging configuration for Claude MPM.

This module provides a standardized logging infrastructure with:
- Consistent logger factory method
- Structured logging with context
- Performance logging decorators
- Context managers for operation tracking
- Standardized log levels and formatting

WHY: This centralized approach ensures consistent logging across the entire
codebase, making debugging and monitoring significantly easier. All components
use the same format, level hierarchy, and contextual information structure.

DESIGN DECISION: Built on top of existing logger.py but provides simplified
interface and enforces consistent patterns. This allows gradual migration
while maintaining backwards compatibility.
"""

import functools
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Union

from claude_mpm.core.logger import (
    JsonFormatter,
    finalize_streaming_logs,
    get_logger as _get_logger,
    log_async_performance,
    log_performance,
    setup_logging as _setup_logging,
)

# Standard log format for consistency
STANDARD_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"

# Log level mapping for consistent usage
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,  # Detailed diagnostic information
    "INFO": logging.INFO,  # Normal operations, significant events
    "WARNING": logging.WARNING,  # Potentially harmful situations
    "ERROR": logging.ERROR,  # Error events allowing continued operation
    "CRITICAL": logging.CRITICAL,  # Events that may cause abort
}


class LogContext:
    """
    Context manager for adding contextual information to log messages.

    WHY: Provides consistent way to add context like operation IDs, user info,
    or request IDs to all logs within a scope without modifying every log call.
    """

    _context: Dict[str, Any] = {}

    @classmethod
    def set(cls, **kwargs):
        """Set context values."""
        cls._context.update(kwargs)

    @classmethod
    def get(cls) -> Dict[str, Any]:
        """Get current context."""
        return cls._context.copy()

    @classmethod
    def clear(cls):
        """Clear all context."""
        cls._context.clear()

    @classmethod
    @contextmanager
    def context(cls, **kwargs):
        """Context manager for temporary context."""
        old_context = cls._context.copy()
        cls._context.update(kwargs)
        try:
            yield
        finally:
            cls._context = old_context


class ContextualLogger:
    """
    Logger wrapper that automatically includes context in all messages.

    WHY: Ensures all log messages from a component include relevant context
    without requiring manual addition to each log call.
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _log_with_context(self, level: int, msg: str, *args, **kwargs):
        """Add context to log message."""
        context = LogContext.get()
        if context:
            # Add context as extra fields for structured logging
            kwargs["extra"] = kwargs.get("extra", {})
            kwargs["extra"].update(context)

            # For human-readable logs, prepend context
            if not isinstance(self._logger.handlers[0].formatter, JsonFormatter):
                context_str = " ".join(f"[{k}={v}]" for k, v in context.items())
                if context_str:
                    msg = f"{context_str} {msg}"

        self._logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log exception with context."""
        kwargs["exc_info"] = True
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)


def get_logger(
    name: str, with_context: bool = True
) -> Union[ContextualLogger, logging.Logger]:
    """
    Get a configured logger instance.

    WHY: Centralized logger creation ensures all loggers follow the same
    naming convention and configuration patterns.

    Args:
        name: Logger name (typically __name__ from the calling module)
        with_context: Whether to wrap with ContextualLogger for automatic context

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing request", extra={"request_id": "123"})
    """
    # Ensure consistent naming
    if not name.startswith("claude_mpm"):
        name = f"claude_mpm.{name}"

    logger = _get_logger(name)

    if with_context:
        return ContextualLogger(logger)
    return logger


def configure_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    console_output: bool = True,
    file_output: bool = True,
    json_format: bool = False,
    use_streaming: bool = False,
) -> None:
    """
    Configure global logging settings.

    WHY: Provides single entry point for configuring all logging behavior
    across the application, ensuring consistency.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        console_output: Enable console output
        file_output: Enable file output
        json_format: Use JSON format for structured logging
        use_streaming: Use streaming handler for progress messages
    """
    # Configure root logger for claude_mpm
    _setup_logging(
        name="claude_mpm",
        level=level,
        log_dir=log_dir,
        console_output=console_output,
        file_output=file_output,
        json_format=json_format,
        use_streaming=use_streaming,
    )


@contextmanager
def log_operation(
    logger: Union[ContextualLogger, logging.Logger], operation: str, **context
):
    """
    Context manager for logging operation start/end with timing.

    WHY: Provides consistent way to track operation execution including
    timing, success/failure, and any relevant context.

    Args:
        logger: Logger instance
        operation: Operation name/description
        **context: Additional context to include in logs

    Example:
        with log_operation(logger, "database_query", query_type="select"):
            # Perform database operation
            pass
    """
    start_time = time.time()

    # Add operation context
    with LogContext.context(operation=operation, **context):
        logger.info(f"Starting {operation}")

        try:
            yield
            execution_time = time.time() - start_time
            logger.info(
                f"Completed {operation}",
                extra={"execution_time": execution_time, "status": "success"},
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Failed {operation}: {e}",
                extra={
                    "execution_time": execution_time,
                    "status": "failure",
                    "error": str(e),
                },
            )
            raise


@contextmanager
def log_performance_context(
    logger: Union[ContextualLogger, logging.Logger],
    operation: str,
    warn_threshold: float = 1.0,
    error_threshold: float = 5.0,
):
    """
    Context manager for performance monitoring with thresholds.

    WHY: Automatically warns or errors when operations exceed performance
    thresholds, helping identify performance issues early.

    Args:
        logger: Logger instance
        operation: Operation being monitored
        warn_threshold: Time in seconds to trigger warning
        error_threshold: Time in seconds to trigger error

    Example:
        with log_performance_context(logger, "api_call", warn_threshold=0.5):
            # Make API call
            pass
    """
    start_time = time.time()

    try:
        yield
    finally:
        execution_time = time.time() - start_time

        if execution_time > error_threshold:
            logger.error(
                f"{operation} took {execution_time:.3f}s (threshold: {error_threshold}s)",
                extra={"execution_time": execution_time, "threshold_exceeded": "error"},
            )
        elif execution_time > warn_threshold:
            logger.warning(
                f"{operation} took {execution_time:.3f}s (threshold: {warn_threshold}s)",
                extra={
                    "execution_time": execution_time,
                    "threshold_exceeded": "warning",
                },
            )
        else:
            logger.debug(
                f"{operation} completed in {execution_time:.3f}s",
                extra={"execution_time": execution_time},
            )


def log_function_call(func):
    """
    Decorator to log function calls with arguments and results.

    WHY: Provides automatic logging of function entry/exit for debugging
    without modifying function implementation.

    Example:
        @log_function_call
        def process_data(data: dict) -> dict:
            return {"processed": True}
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        func_name = func.__qualname__

        # Log function entry
        logger.debug(
            f"Calling {func_name}",
            extra={
                "function": func_name,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            },
        )

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.debug(
                f"{func_name} completed",
                extra={
                    "function": func_name,
                    "execution_time": execution_time,
                    "has_result": result is not None,
                },
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(
                f"{func_name} failed",
                extra={
                    "function": func_name,
                    "execution_time": execution_time,
                    "error_type": type(e).__name__,
                },
            )
            raise

    return wrapper


async def log_async_function_call(func):
    """
    Decorator to log async function calls with arguments and results.

    WHY: Provides automatic logging for async functions, essential for
    tracking async operation flow and performance.

    Example:
        @log_async_function_call
        async def fetch_data(url: str) -> dict:
            return {"data": "example"}
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        func_name = func.__qualname__

        # Log function entry
        logger.debug(
            f"Calling async {func_name}",
            extra={
                "function": func_name,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
                "is_async": True,
            },
        )

        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.debug(
                f"Async {func_name} completed",
                extra={
                    "function": func_name,
                    "execution_time": execution_time,
                    "has_result": result is not None,
                    "is_async": True,
                },
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(
                f"Async {func_name} failed",
                extra={
                    "function": func_name,
                    "execution_time": execution_time,
                    "error_type": type(e).__name__,
                    "is_async": True,
                },
            )
            raise

    return wrapper


# Logging standards and guidelines as constants for reference
LOGGING_STANDARDS = {
    "INFO": "Normal operations, significant events (e.g., service started, request completed)",
    "DEBUG": "Detailed diagnostic information (e.g., variable values, execution flow)",
    "WARNING": "Potentially harmful situations (e.g., deprecated API usage, retry attempts)",
    "ERROR": "Error events that allow continued operation (e.g., single request failure)",
    "CRITICAL": "Events that may cause abort (e.g., database connection lost, out of memory)",
}


def log_with_level(
    logger: Union[ContextualLogger, logging.Logger], level: str, message: str, **extra
):
    """
    Log a message with dynamic level selection.

    WHY: Allows log level to be determined at runtime, useful for
    configurable logging or conditional severity.

    Args:
        logger: Logger instance
        level: Log level as string
        message: Log message
        **extra: Additional fields for structured logging
    """
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    logger.log(log_level, message, extra=extra)


# Export main functions and decorators
__all__ = [
    "LOGGING_STANDARDS",
    "LOG_LEVELS",
    "ContextualLogger",
    "LogContext",
    "configure_logging",
    "finalize_streaming_logs",
    "get_logger",
    "log_async_function_call",
    "log_async_performance",
    "log_function_call",
    "log_operation",
    # Re-export from core.logger for backwards compatibility
    "log_performance",
    "log_performance_context",
    "log_with_level",
]
