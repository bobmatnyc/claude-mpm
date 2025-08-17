"""
MCP Gateway Exception Classes
=============================

Custom exceptions for MCP Gateway operations.

Part of ISS-0034: Infrastructure Setup - MCP Gateway Project Foundation
"""

from typing import Any, Dict, Optional


class MCPException(Exception):
    """
    Base exception for all MCP Gateway errors.

    WHY: We create a base exception to allow catching all MCP-related
    errors in a single except block while still being able to handle
    specific error types when needed.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize MCP exception.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """String representation of the exception."""
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class MCPConfigurationError(MCPException):
    """
    Raised when MCP configuration is invalid or cannot be loaded.

    Common scenarios:
    - Missing required configuration fields
    - Invalid configuration values
    - Configuration file not found
    - YAML parsing errors
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
    ):
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
            expected_type: Expected type for the configuration value
        """
        details = {}
        if config_key:
            details["config_key"] = config_key
        if expected_type:
            details["expected_type"] = expected_type

        super().__init__(message, details)


class MCPToolNotFoundError(MCPException):
    """
    Raised when a requested tool is not found in the registry.

    This error occurs when:
    - Attempting to invoke a non-existent tool
    - Trying to unregister a tool that isn't registered
    - Searching for a tool that doesn't exist
    """

    def __init__(self, tool_name: str, available_tools: Optional[list] = None):
        """
        Initialize tool not found error.

        Args:
            tool_name: Name of the tool that wasn't found
            available_tools: List of available tool names for reference
        """
        message = f"Tool '{tool_name}' not found in registry"
        details = {"tool_name": tool_name}

        if available_tools:
            details["available_tools"] = available_tools
            message += f". Available tools: {', '.join(available_tools)}"

        super().__init__(message, details)


class MCPServerError(MCPException):
    """
    Raised when MCP server encounters an error.

    Common scenarios:
    - Server initialization failure
    - Port binding issues
    - Server crash during operation
    - Invalid server state transitions
    """

    def __init__(
        self,
        message: str,
        server_state: Optional[str] = None,
        error_code: Optional[int] = None,
    ):
        """
        Initialize server error.

        Args:
            message: Error message
            server_state: Current server state when error occurred
            error_code: Numeric error code if applicable
        """
        details = {}
        if server_state:
            details["server_state"] = server_state
        if error_code:
            details["error_code"] = error_code

        super().__init__(message, details)


class MCPCommunicationError(MCPException):
    """
    Raised when communication with MCP client fails.

    This includes:
    - Stdio communication failures
    - Message parsing errors
    - Protocol violations
    - Timeout errors
    """

    def __init__(
        self,
        message: str,
        direction: Optional[str] = None,
        raw_data: Optional[str] = None,
    ):
        """
        Initialize communication error.

        Args:
            message: Error message
            direction: Direction of communication ("send" or "receive")
            raw_data: Raw data that caused the error (for debugging)
        """
        details = {}
        if direction:
            details["direction"] = direction
        if raw_data and len(raw_data) < 1000:  # Limit raw data size in exceptions
            details["raw_data"] = raw_data
        elif raw_data:
            details["raw_data"] = raw_data[:1000] + "... (truncated)"

        super().__init__(message, details)


class MCPValidationError(MCPException):
    """
    Raised when validation fails.

    Used for:
    - Tool parameter validation
    - Schema validation
    - Input validation
    - Response validation
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
    ):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            expected: Expected value or type
            actual: Actual value received
        """
        details = {}
        if field:
            details["field"] = field
        if expected is not None:
            details["expected"] = str(expected)
        if actual is not None:
            details["actual"] = str(actual)

        super().__init__(message, details)


class MCPTimeoutError(MCPException):
    """
    Raised when an operation times out.

    Common scenarios:
    - Tool invocation timeout
    - Server startup timeout
    - Communication timeout
    """

    def __init__(self, operation: str, timeout_seconds: float):
        """
        Initialize timeout error.

        Args:
            operation: Operation that timed out
            timeout_seconds: Timeout duration in seconds
        """
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        details = {"operation": operation, "timeout_seconds": timeout_seconds}
        super().__init__(message, details)


class MCPAuthenticationError(MCPException):
    """
    Raised when authentication fails.

    For future use when MCP supports authentication.
    """

    def __init__(self, message: str, auth_method: Optional[str] = None):
        """
        Initialize authentication error.

        Args:
            message: Error message
            auth_method: Authentication method that failed
        """
        details = {}
        if auth_method:
            details["auth_method"] = auth_method

        super().__init__(message, details)
