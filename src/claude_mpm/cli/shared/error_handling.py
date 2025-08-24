"""
Common error handling patterns for CLI commands.
"""

import traceback
from functools import wraps
from typing import Any, Callable, Optional

from ...core.logger import get_logger


class CLIErrorHandler:
    """Centralized error handling for CLI commands."""

    def __init__(self, command_name: str):
        """
        Initialize error handler.

        Args:
            command_name: Name of the command for logging context
        """
        self.command_name = command_name
        self.logger = get_logger(f"cli.{command_name}")

    def handle_error(self, error: Exception, context: Optional[str] = None) -> int:
        """
        Handle an error with appropriate logging and user feedback.

        Args:
            error: The exception that occurred
            context: Additional context about when the error occurred

        Returns:
            Appropriate exit code
        """
        # Build error message
        error_msg = str(error)
        if context:
            error_msg = f"{context}: {error_msg}"

        # Determine error type and appropriate response
        if isinstance(error, KeyboardInterrupt):
            self.logger.info("Operation cancelled by user")
            print("\nOperation cancelled by user.")
            return 130  # Standard exit code for SIGINT

        if isinstance(error, FileNotFoundError):
            self.logger.error(f"File not found: {error}")
            print(f"Error: File not found - {error}")
            return 2

        if isinstance(error, PermissionError):
            self.logger.error(f"Permission denied: {error}")
            print(f"Error: Permission denied - {error}")
            return 13

        if isinstance(error, ValueError):
            self.logger.error(f"Invalid value: {error}")
            print(f"Error: Invalid value - {error}")
            return 22

        # Generic error handling
        self.logger.error(f"Command failed: {error}", exc_info=True)
        print(f"Error: {error_msg}")

        # Show traceback in debug mode
        if self.logger.isEnabledFor(10):  # DEBUG level
            traceback.print_exc()

        return 1

    def handle_validation_error(self, message: str) -> int:
        """
        Handle validation errors.

        Args:
            message: Validation error message

        Returns:
            Exit code for validation errors
        """
        self.logger.error(f"Validation error: {message}")
        print(f"Error: {message}")
        return 22  # Invalid argument exit code

    def handle_config_error(self, error: Exception) -> int:
        """
        Handle configuration-related errors.

        Args:
            error: Configuration error

        Returns:
            Exit code for configuration errors
        """
        self.logger.error(f"Configuration error: {error}")
        print(f"Configuration Error: {error}")
        print("Please check your configuration file and try again.")
        return 78  # Configuration error exit code


def handle_cli_errors(command_name: str):
    """
    Decorator to add standard error handling to CLI command functions.

    Args:
        command_name: Name of the command for error context

    Returns:
        Decorated function with error handling
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> int:
            error_handler = CLIErrorHandler(command_name)

            try:
                result = func(*args, **kwargs)

                # Handle different return types
                if isinstance(result, int):
                    return result
                if hasattr(result, "exit_code"):
                    return result.exit_code
                return 0  # Success

            except Exception as e:
                return error_handler.handle_error(e)

        return wrapper

    return decorator


def safe_execute(
    func: Callable, *args, error_handler: CLIErrorHandler = None, **kwargs
) -> Any:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        *args: Function arguments
        error_handler: Optional error handler
        **kwargs: Function keyword arguments

    Returns:
        Function result or None if error occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_handler:
            error_handler.handle_error(e)
        else:
            # Fallback error handling
            logger = get_logger("cli.safe_execute")
            logger.error(f"Error executing {func.__name__}: {e}", exc_info=True)
        return None


def validate_file_exists(file_path: str, error_handler: CLIErrorHandler = None) -> bool:
    """
    Validate that a file exists.

    Args:
        file_path: Path to validate
        error_handler: Optional error handler

    Returns:
        True if file exists, False otherwise
    """
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        message = f"File does not exist: {file_path}"
        if error_handler:
            error_handler.handle_validation_error(message)
        return False

    if not path.is_file():
        message = f"Path is not a file: {file_path}"
        if error_handler:
            error_handler.handle_validation_error(message)
        return False

    return True


def validate_directory_exists(
    dir_path: str, error_handler: CLIErrorHandler = None
) -> bool:
    """
    Validate that a directory exists.

    Args:
        dir_path: Directory path to validate
        error_handler: Optional error handler

    Returns:
        True if directory exists, False otherwise
    """
    from pathlib import Path

    path = Path(dir_path)
    if not path.exists():
        message = f"Directory does not exist: {dir_path}"
        if error_handler:
            error_handler.handle_validation_error(message)
        return False

    if not path.is_dir():
        message = f"Path is not a directory: {dir_path}"
        if error_handler:
            error_handler.handle_validation_error(message)
        return False

    return True


def confirm_operation(message: str, force: bool = False) -> bool:
    """
    Ask user for confirmation unless force flag is set.

    Args:
        message: Confirmation message
        force: If True, skip confirmation

    Returns:
        True if operation should proceed
    """
    if force:
        return True

    try:
        response = input(f"{message} (y/N): ").strip().lower()
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print("\nOperation cancelled.")
        return False
