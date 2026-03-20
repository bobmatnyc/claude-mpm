"""
Enhanced error handling utilities for claude-mpm.

Inspired by awesome-claude-code's comprehensive error handling approach.
"""

import logging
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class MPMError(Exception):
    """Base exception for claude-mpm errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        suggestions: list[str] | None = None,
    ):
        """Initialize MPM error with details and suggestions."""
        super().__init__(message)
        self.details = details or {}
        self.suggestions = suggestions or []
        self.timestamp = datetime.now(UTC)

    def get_user_friendly_message(self) -> str:
        """Get a user-friendly error message."""
        lines = [f"❌ Error: {self!s}"]

        if self.details:
            lines.append("\nDetails:")
            for key, value in self.details.items():
                lines.append(f"  {key}: {value}")

        if self.suggestions:
            lines.append("\n💡 Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"  - {suggestion}")

        return "\n".join(lines)


class AgentLoadError(MPMError):
    """Raised when agent loading fails."""


class ValidationError(MPMError):
    """Raised when validation fails."""


class ExecutionError(MPMError):
    """Raised when agent execution fails."""


class ConfigurationError(MPMError):
    """Raised when configuration is invalid."""


def handle_errors(
    error_type: type[Exception] = Exception,
    fallback_value: Any = None,
    log_level: int = logging.ERROR,
) -> Callable:
    """
    Decorator for handling errors with detailed logging and user feedback.

    Args:
        error_type: Type of exception to catch
        fallback_value: Value to return on error
        log_level: Logging level for errors
    """

    def decorator(func: Callable) -> Callable:
        """Wrap the target function with error-catching and user-friendly reporting.

        WHY: Captures the outer handle_errors configuration (error_type, fallback, log
        level) via closure so the same error policy applies to any decorated callable.
        WHAT: Returns a wrapper that catches the configured exception type (and any
        unexpected Exception), logs it, prints a user-friendly message to stderr, and
        returns fallback_value.
        TEST: Decorate a function that raises MPMError; call it; assert fallback_value
        is returned and get_user_friendly_message() output appears on stderr.
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Execute the wrapped function and handle exceptions with user feedback.

            WHY: Provides the runtime enforcement of the error-handling policy chosen at
            decoration time, preventing unhandled exceptions from crashing callers.
            WHAT: Calls the original function; on caught exception logs it and prints a
            user-friendly or unexpected-error message to stderr; returns fallback_value.
            TEST: Wrap a function that raises a non-MPMError; assert stderr contains
            the "Unexpected error" prompt and the return value equals fallback_value.
            """
            try:
                return func(*args, **kwargs)
            except error_type as e:
                # Log the error with full traceback
                logger.log(log_level, f"Error in {func.__name__}: {e}", exc_info=True)

                # Provide user-friendly feedback
                if isinstance(e, MPMError):
                    print(e.get_user_friendly_message(), file=sys.stderr)
                else:
                    print(f"❌ Error: {e}", file=sys.stderr)

                return fallback_value
            except Exception as e:
                # Catch unexpected errors
                logger.critical(
                    f"Unexpected error in {func.__name__}: {e}", exc_info=True
                )
                print(f"❌ Unexpected error: {e}", file=sys.stderr)
                print("💡 This might be a bug. Please report it.", file=sys.stderr)
                return fallback_value

        return wrapper

    return decorator


class ErrorContext:
    """Context manager for enhanced error reporting."""

    def __init__(self, operation: str, details: dict[str, Any] | None = None):
        """Initialize error context."""
        self.operation = operation
        self.details = details or {}

    def __enter__(self):
        """Enter the context."""
        logger.debug(f"Starting operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context, handling any errors."""
        if exc_type is None:
            logger.debug(f"Completed operation: {self.operation}")
            return None

        # Log the error with context
        logger.error(
            f"Error during {self.operation}: {exc_val}",
            extra={"operation": self.operation, "details": self.details},
            exc_info=True,
        )

        # Don't suppress the exception
        return False


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator for retrying operations on error.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        backoff_factor: Multiplier for delay after each failure
        exceptions: Tuple of exceptions to retry on
    """

    def decorator(func: Callable) -> Callable:
        """Wrap the target function with retry logic, choosing async or sync wrapper.

        WHY: Captures the outer retry_on_error configuration via closure and selects
        the correct wrapper (async vs. sync) based on the decorated function type.
        WHAT: Returns async_wrapper for coroutine functions, sync_wrapper for regular
        functions; both implement exponential-backoff retry with the captured parameters.
        TEST: Decorate an async function that raises twice then succeeds; set max_attempts=3;
        assert the result is returned and the function was called exactly 3 times.
        """

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            """Retry an async function with exponential backoff.

            WHY: Handles transient async failures (network, service unavailability) without
            callers needing to write their own retry loops.
            WHAT: Awaits the original coroutine in a loop; on failure sleeps for an
            exponentially growing delay; raises the last exception after all attempts fail.
            TEST: Wrap an async function that raises on attempts 1-2 and succeeds on 3;
            assert the returned value matches the success result.
            """
            import asyncio

            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            """Retry a synchronous function with exponential backoff.

            WHY: Handles transient synchronous failures (I/O, locks) without callers
            needing to write their own retry loops.
            WHAT: Calls the original function in a loop; on failure sleeps for an
            exponentially growing delay; raises the last exception after all attempts fail.
            TEST: Wrap a function that raises on attempts 1-2 and succeeds on 3;
            assert the returned value matches the success result.
            """
            import time

            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            raise last_exception

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def format_exception_chain(exc: Exception) -> str:
    """Format an exception chain for display."""
    lines = []
    current = exc
    level = 0

    while current is not None:
        indent = "  " * level
        lines.append(
            f"{indent}{'└─' if level > 0 else ''}{type(current).__name__}: {current}"
        )

        if hasattr(current, "__cause__"):
            current = current.__cause__
            level += 1
        else:
            break

    return "\n".join(lines)


# Setup patterns from awesome-claude-code
def suggest_setup_fix(error: Exception) -> list[str]:
    """Suggest fixes for common setup errors."""
    suggestions = []
    error_msg = str(error).lower()

    if "git" in error_msg and "not found" in error_msg:
        suggestions.append("Install git from https://git-scm.com/downloads")

    if "python" in error_msg and "module" in error_msg:
        suggestions.append("Ensure you're in a virtual environment")
        suggestions.append("Run: pip install -e .")

    if "permission" in error_msg:
        suggestions.append("Check file permissions")
        suggestions.append("You may need to run with appropriate privileges")

    if "config" in error_msg or "configuration" in error_msg:
        suggestions.append("Check your configuration files")
        suggestions.append("Run: mpm validate-config")

    return suggestions
