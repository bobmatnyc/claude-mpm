"""Centralized error handling framework for Claude MPM.

This module provides standardized error handling utilities to replace
200+ generic try/except blocks across the codebase with context-aware,
properly logged, and recoverable error handling.
"""

import functools
import sys
import traceback
from contextlib import contextmanager
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from claude_mpm.core.constants import RetryConfig
from claude_mpm.core.exceptions import MPMError
from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


# ==============================================================================
# ERROR HANDLING STRATEGIES
# ==============================================================================


class ErrorStrategy(Enum):
    """Error handling strategies."""

    IGNORE = "ignore"  # Log and continue
    RETRY = "retry"  # Retry the operation
    FALLBACK = "fallback"  # Use fallback value/function
    ESCALATE = "escalate"  # Re-raise the exception
    RECOVER = "recover"  # Attempt recovery
    TERMINATE = "terminate"  # Terminate the process


class ErrorSeverity(Enum):
    """Error severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ==============================================================================
# ERROR HANDLER
# ==============================================================================


class ErrorHandler:
    """Centralized error handler with context and recovery capabilities."""

    def __init__(
        self,
        logger: Optional[Any] = None,
        default_strategy: ErrorStrategy = ErrorStrategy.ESCALATE,
        capture_traceback: bool = True,
    ):
        """Initialize error handler.

        Args:
            logger: Logger instance (uses module logger if None)
            default_strategy: Default error handling strategy
            capture_traceback: Whether to capture full tracebacks
        """
        self.logger = logger or get_logger(__name__)
        self.default_strategy = default_strategy
        self.capture_traceback = capture_traceback
        self.error_history: List[Dict[str, Any]] = []
        self.recovery_handlers: Dict[Type[Exception], Callable] = {}

    def handle(
        self,
        error: Exception,
        context: Optional[str] = None,
        operation: Optional[str] = None,
        strategy: Optional[ErrorStrategy] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        fallback_value: Any = None,
        max_retries: int = 0,
        **extra_context,
    ) -> Any:
        """Handle an error with the specified strategy.

        Args:
            error: The exception to handle
            context: Context description for logging
            operation: Operation name that failed
            strategy: Error handling strategy (uses default if None)
            severity: Error severity level
            fallback_value: Value to return for FALLBACK strategy
            max_retries: Maximum retries for RETRY strategy
            **extra_context: Additional context key-value pairs

        Returns:
            Result based on strategy (fallback value, None, or re-raises)
        """
        strategy = strategy or self.default_strategy

        # Build error context
        error_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "operation": operation or "unknown",
            "strategy": strategy.value,
            "severity": severity.value,
        }
        error_context.update(extra_context)

        # Add MPM error context if available
        if isinstance(error, MPMError) and error.context:
            error_context["mpm_context"] = error.context

        # Capture traceback if enabled
        if self.capture_traceback:
            error_context["traceback"] = traceback.format_exc()

        # Store in history
        self.error_history.append(error_context)

        # Log the error
        self._log_error(error, context, severity, error_context)

        # Apply strategy
        if strategy == ErrorStrategy.IGNORE:
            return None

        if strategy == ErrorStrategy.RETRY:
            return self._handle_retry(error, operation, max_retries, extra_context)

        if strategy == ErrorStrategy.FALLBACK:
            return fallback_value

        if strategy == ErrorStrategy.ESCALATE:
            raise error

        if strategy == ErrorStrategy.RECOVER:
            return self._handle_recovery(error, error_context)

        if strategy == ErrorStrategy.TERMINATE:
            self.logger.critical(f"Terminating due to critical error: {error}")
            sys.exit(1)
        return None

    def _log_error(
        self,
        error: Exception,
        context: Optional[str],
        severity: ErrorSeverity,
        error_context: Dict[str, Any],
    ) -> None:
        """Log error with appropriate severity.

        Args:
            error: The exception
            context: Context description
            severity: Error severity
            error_context: Full error context
        """
        message = f"{context or 'Error occurred'}: {error}"

        if severity == ErrorSeverity.DEBUG:
            self.logger.debug(message, extra=error_context)
        elif severity == ErrorSeverity.INFO:
            self.logger.info(message, extra=error_context)
        elif severity == ErrorSeverity.WARNING:
            self.logger.warning(message, extra=error_context)
        elif severity == ErrorSeverity.ERROR:
            self.logger.error(message, extra=error_context)
        elif severity == ErrorSeverity.CRITICAL:
            self.logger.critical(message, extra=error_context)

    def _handle_retry(
        self,
        error: Exception,
        operation: Optional[str],
        max_retries: int,
        context: Dict[str, Any],
    ) -> None:
        """Handle retry strategy.

        Args:
            error: The exception
            operation: Operation name
            max_retries: Maximum retries
            context: Error context
        """
        # This would need to be called from a retry decorator
        # For now, just log and escalate
        self.logger.warning(f"Retry requested for {operation} but not in retry context")
        raise error

    def _handle_recovery(
        self,
        error: Exception,
        error_context: Dict[str, Any],
    ) -> Any:
        """Attempt to recover from error.

        Args:
            error: The exception
            error_context: Full error context

        Returns:
            Recovery result or re-raises
        """
        error_type = type(error)

        # Check for registered recovery handler
        if error_type in self.recovery_handlers:
            try:
                handler = self.recovery_handlers[error_type]
                return handler(error, error_context)
            except Exception as recovery_error:
                self.logger.error(f"Recovery failed: {recovery_error}")
                raise error from recovery_error

        # No recovery handler available
        self.logger.warning(f"No recovery handler for {error_type.__name__}")
        raise error

    def register_recovery(
        self,
        error_type: Type[Exception],
        handler: Callable[[Exception, Dict], Any],
    ) -> None:
        """Register a recovery handler for an error type.

        Args:
            error_type: Exception class to handle
            handler: Recovery function
        """
        self.recovery_handlers[error_type] = handler

    def get_error_history(
        self,
        limit: Optional[int] = None,
        operation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get error history.

        Args:
            limit: Maximum number of errors to return
            operation: Filter by operation name

        Returns:
            List of error contexts
        """
        history = self.error_history

        if operation:
            history = [e for e in history if e.get("operation") == operation]

        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """Clear error history."""
        self.error_history.clear()


# ==============================================================================
# GLOBAL ERROR HANDLER
# ==============================================================================

# Global error handler instance
_global_handler = ErrorHandler()


def handle_error(
    error: Exception,
    context: Optional[str] = None,
    operation: Optional[str] = None,
    strategy: Optional[ErrorStrategy] = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    fallback_value: Any = None,
    logger: Optional[Any] = None,
    **extra_context,
) -> Any:
    """Handle an error using the global error handler.

    This is the main function to use for error handling throughout the codebase.

    Example:
        try:
            # operation
        except SpecificError as e:
            handle_error(e, context="operation_name", strategy=ErrorStrategy.FALLBACK,
                        fallback_value=default_value)

    Args:
        error: The exception to handle
        context: Context description for logging
        operation: Operation name that failed
        strategy: Error handling strategy
        severity: Error severity level
        fallback_value: Value to return for FALLBACK strategy
        logger: Optional specific logger to use
        **extra_context: Additional context key-value pairs

    Returns:
        Result based on strategy
    """
    handler = ErrorHandler(logger=logger) if logger else _global_handler

    return handler.handle(
        error=error,
        context=context,
        operation=operation,
        strategy=strategy,
        severity=severity,
        fallback_value=fallback_value,
        **extra_context,
    )


def register_recovery_handler(
    error_type: Type[Exception],
    handler: Callable[[Exception, Dict], Any],
) -> None:
    """Register a global recovery handler for an error type.

    Args:
        error_type: Exception class to handle
        handler: Recovery function
    """
    _global_handler.register_recovery(error_type, handler)


# ==============================================================================
# ERROR HANDLING DECORATORS
# ==============================================================================


def with_error_handling(
    strategy: ErrorStrategy = ErrorStrategy.ESCALATE,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    fallback_value: Any = None,
    max_retries: int = 0,
    retry_delay: float = 1.0,
    exceptions: Union[Type[Exception], tuple] = Exception,
):
    """Decorator for automatic error handling.

    Args:
        strategy: Error handling strategy
        severity: Error severity level
        fallback_value: Fallback value or callable
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries (seconds)
        exceptions: Exception types to catch
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            operation = func.__name__
            retries = 0

            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if strategy == ErrorStrategy.RETRY and retries < max_retries:
                        retries += 1
                        logger.warning(
                            f"Retrying {operation} (attempt {retries}/{max_retries})"
                        )
                        if retry_delay > 0:
                            import time

                            time.sleep(retry_delay)
                        continue

                    # Use fallback if it's callable
                    fb_value = fallback_value
                    if callable(fallback_value):
                        try:
                            fb_value = fallback_value(*args, **kwargs)
                        except Exception:
                            fb_value = None

                    return handle_error(
                        error=e,
                        operation=operation,
                        strategy=strategy,
                        severity=severity,
                        fallback_value=fb_value,
                    )

            # Max retries exceeded
            raise Exception(f"Max retries ({max_retries}) exceeded for {operation}")

        return wrapper

    return decorator


def safe_operation(
    fallback_value: Any = None,
    log_errors: bool = True,
    exceptions: Union[Type[Exception], tuple] = Exception,
):
    """Decorator for safe operations that should never fail.

    Args:
        fallback_value: Value to return on error
        log_errors: Whether to log errors
        exceptions: Exception types to catch
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if log_errors:
                    logger.warning(f"Safe operation {func.__name__} failed: {e}")

                if callable(fallback_value):
                    try:
                        return fallback_value(*args, **kwargs)
                    except Exception:
                        return None
                return fallback_value

        return wrapper

    return decorator


def retry_on_error(
    max_retries: int = RetryConfig.MAX_RETRIES,
    delay: float = RetryConfig.INITIAL_RETRY_DELAY,
    exponential_backoff: bool = True,
    exceptions: Union[Type[Exception], tuple] = Exception,
):
    """Decorator for automatic retry with exponential backoff.

    Args:
        max_retries: Maximum retry attempts
        delay: Initial delay between retries (seconds)
        exponential_backoff: Use exponential backoff
        exceptions: Exception types to retry on
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        logger.debug(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                            f"after {current_delay:.2f}s"
                        )

                        import time

                        time.sleep(current_delay)

                        if exponential_backoff:
                            current_delay = min(
                                current_delay * RetryConfig.EXPONENTIAL_BASE,
                                RetryConfig.MAX_RETRY_DELAY,
                            )

            # All retries exhausted
            logger.error(f"All {max_retries} retries failed for {func.__name__}")
            raise last_exception

        return wrapper

    return decorator


# ==============================================================================
# CONTEXT MANAGERS
# ==============================================================================


@contextmanager
def error_context(
    operation: str,
    strategy: ErrorStrategy = ErrorStrategy.ESCALATE,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    fallback_value: Any = None,
    **context,
):
    """Context manager for error handling.

    Example:
        with error_context("file_operation", strategy=ErrorStrategy.FALLBACK,
                          fallback_value=None, file=filename):
            # operations that might fail
            pass

    Args:
        operation: Operation name
        strategy: Error handling strategy
        severity: Error severity
        fallback_value: Fallback value
        **context: Additional context
    """
    try:
        yield
    except Exception as e:
        handle_error(
            error=e,
            operation=operation,
            strategy=strategy,
            severity=severity,
            fallback_value=fallback_value,
            **context,
        )
        if strategy == ErrorStrategy.FALLBACK:
            return fallback_value
        elif strategy != ErrorStrategy.ESCALATE:
            return


@contextmanager
def suppress_errors(
    *exceptions: Type[Exception],
    log: bool = True,
    fallback: Any = None,
):
    """Context manager to suppress specific errors.

    Example:
        with suppress_errors(FileNotFoundError, log=True):
            # operations that might fail
            pass

    Args:
        *exceptions: Exception types to suppress
        log: Whether to log suppressed errors
        fallback: Fallback value to yield on error
    """
    try:
        yield fallback
    except exceptions as e:
        if log:
            logger.debug(f"Suppressed error: {e}")
        yield fallback


# ==============================================================================
# ERROR AGGREGATION
# ==============================================================================


class ErrorCollector:
    """Collect errors without immediately failing."""

    def __init__(self, fail_fast: bool = False):
        """Initialize error collector.

        Args:
            fail_fast: Raise first error immediately
        """
        self.errors: List[Exception] = []
        self.fail_fast = fail_fast

    def collect(self, error: Exception) -> None:
        """Collect an error.

        Args:
            error: Exception to collect
        """
        self.errors.append(error)
        if self.fail_fast:
            raise error

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def raise_if_errors(self, message: str = "Multiple errors occurred") -> None:
        """Raise an exception if any errors were collected."""
        if self.errors:
            if len(self.errors) == 1:
                raise self.errors[0]
            error_messages = [str(e) for e in self.errors]
            raise Exception(f"{message}: {'; '.join(error_messages)}")

    def clear(self) -> None:
        """Clear collected errors."""
        self.errors.clear()

    @contextmanager
    def collecting(self):
        """Context manager for error collection.

        Example:
            collector = ErrorCollector()
            with collector.collecting():
                for item in items:
                    try:
                        process(item)
                    except Exception as e:
                        collector.collect(e)
            collector.raise_if_errors()
        """
        try:
            yield self
        finally:
            pass  # Errors are handled by caller
