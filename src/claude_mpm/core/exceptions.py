"""Centralized exception hierarchy for Claude MPM.

This module provides a comprehensive exception hierarchy for standardized error
handling across the codebase. Each exception class supports contextual information
for better debugging and error resolution.

Design Principles:
1. Clear inheritance hierarchy with MPMError as the base
2. Context support for debugging (optional dict with additional details)
3. Helpful error messages with actionable guidance
4. Backward compatibility with existing error handling
5. Structured error data for programmatic handling

Usage:
    from claude_mpm.core.exceptions import ConfigurationError, AgentDeploymentError

    # With context for debugging
    raise ConfigurationError(
        "Invalid agent configuration",
        context={"agent_id": "engineer", "field": "version", "value": "invalid"}
    )

    # Simple usage
    raise AgentDeploymentError("Failed to deploy agent to .claude/agents directory")
"""

from typing import Any, Dict, Optional


class MPMError(Exception):
    """Base exception class for all Claude MPM errors.

    This base class provides common functionality for all MPM exceptions including
    context storage for debugging and structured error representation.

    Attributes:
        message: Human-readable error message
        context: Optional dictionary with additional debugging context
        error_code: Machine-readable error code (defaults to class name in lowercase)
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize MPM error with message and optional context.

        Args:
            message: Human-readable error message
            context: Optional dictionary with debugging context
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.error_code = self._generate_error_code()

    def _generate_error_code(self) -> str:
        """Generate error code from class name."""
        # Convert class name from CamelCase to snake_case
        name = self.__class__.__name__
        # Remove 'Error' suffix if present
        if name.endswith("Error"):
            name = name[:-5]
        # Special case for MPM acronym
        if name == "MPM":
            return "mpm"
        # Convert to snake_case
        import re

        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format for structured logging/handling.

        Returns:
            Dictionary with error type, code, message, and context
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
        }

    def __str__(self) -> str:
        """String representation with context if available."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (context: {context_str})"
        return self.message


class AgentDeploymentError(MPMError):
    """Exception raised when agent deployment fails.

    This error occurs during agent deployment to .claude/agents directory,
    including template building, version checking, and file operations.

    Common causes:
    - Template file not found or invalid
    - Permission issues with .claude/agents directory
    - Version conflicts or migration failures
    - YAML generation errors
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize agent deployment error.

        Args:
            message: Error message describing deployment failure
            context: Optional context with agent_id, template_path, deployment_path, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "agent_id" in context:
                self.message = f"[Agent: {context['agent_id']}] {message}"
            if "template_path" in context and "not found" in message.lower():
                self.message += (
                    f"\nEnsure template exists at: {context['template_path']}"
                )
            if "permission" in message.lower():
                self.message += "\nCheck directory permissions for .claude/agents"


class ConfigurationError(MPMError):
    """Exception raised when configuration validation fails.

    This error occurs when configuration files are invalid, missing required
    fields, or contain incompatible values.

    Common causes:
    - Missing required configuration fields
    - Invalid data types or formats
    - Configuration file not found
    - Schema validation failures
    - Incompatible configuration versions
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize configuration error.

        Args:
            message: Error message describing configuration issue
            context: Optional context with config_file, field, expected_type, actual_value, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "config_file" in context:
                self.message = f"[Config: {context['config_file']}] {message}"
            if "field" in context:
                self.message += f"\nField: {context['field']}"
                if "expected_type" in context:
                    self.message += f" (expected: {context['expected_type']})"
                if "actual_value" in context:
                    self.message += f" (got: {context['actual_value']})"


class ConnectionError(MPMError):
    """Exception raised when network or SocketIO connection fails.

    This error occurs during network operations, including SocketIO server
    connections, port binding, and inter-process communication.

    Common causes:
    - Port already in use
    - Network interface unavailable
    - SocketIO server not responding
    - Connection timeout
    - Authentication failures
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize connection error.

        Args:
            message: Error message describing connection failure
            context: Optional context with host, port, timeout, retry_count, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "host" in context and "port" in context:
                self.message = f"[{context['host']}:{context['port']}] {message}"
            if "timeout" in context:
                self.message += f"\nConnection timeout: {context['timeout']}s"
            if "retry_count" in context:
                self.message += f"\nRetry attempts: {context['retry_count']}"


class ValidationError(MPMError):
    """Exception raised when input validation fails.

    This error occurs when user input, agent definitions, or data structures
    fail validation against expected schemas or constraints.

    Common causes:
    - Invalid agent schema
    - Missing required fields
    - Type mismatches
    - Value out of allowed range
    - Format violations (e.g., invalid JSON/YAML)
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize validation error.

        Args:
            message: Error message describing validation failure
            context: Optional context with field, value, constraint, schema_path, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "field" in context:
                self.message = f"[Field: {context['field']}] {message}"
            if "constraint" in context:
                self.message += f"\nConstraint: {context['constraint']}"
            if "value" in context:
                self.message += f"\nProvided value: {context['value']}"
            if "schema_path" in context:
                self.message += f"\nSchema: {context['schema_path']}"


class ServiceNotFoundError(MPMError):
    """Exception raised when DI container cannot find requested service.

    This error occurs when the dependency injection container cannot locate
    or instantiate a requested service.

    Common causes:
    - Service not registered in container
    - Circular dependencies
    - Missing service dependencies
    - Service initialization failure
    - Incorrect service name or type
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize service not found error.

        Args:
            message: Error message describing missing service
            context: Optional context with service_name, service_type, available_services, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "service_name" in context:
                self.message = f"[Service: {context['service_name']}] {message}"
            if "available_services" in context:
                services = context["available_services"]
                if isinstance(services, list) and services:
                    self.message += f"\nAvailable services: {', '.join(services[:5])}"
                    if len(services) > 5:
                        self.message += f" (and {len(services) - 5} more)"


class MemoryError(MPMError):
    """Exception raised when memory service operations fail.

    This error occurs during agent memory operations including storage,
    retrieval, optimization, and routing.

    Common causes:
    - Memory storage failure
    - Corrupted memory data
    - Memory quota exceeded
    - Routing configuration errors
    - Serialization/deserialization failures

    Note: This shadows Python's built-in MemoryError but is scoped to
    claude_mpm.core.exceptions.MemoryError for clarity.
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize memory error.

        Args:
            message: Error message describing memory operation failure
            context: Optional context with agent_id, memory_type, operation, storage_path, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "agent_id" in context:
                self.message = f"[Agent: {context['agent_id']}] {message}"
            if "memory_type" in context:
                self.message += f"\nMemory type: {context['memory_type']}"
            if "operation" in context:
                self.message += f"\nOperation: {context['operation']}"
            if "storage_path" in context:
                self.message += f"\nStorage: {context['storage_path']}"


class HookError(MPMError):
    """Exception raised when hook execution fails.

    This error occurs during pre/post hook execution in the hook system,
    including hook registration, invocation, and cleanup.

    Common causes:
    - Hook handler exceptions
    - Hook timeout
    - Missing hook dependencies
    - Hook configuration errors
    - Incompatible hook versions
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize hook error.

        Args:
            message: Error message describing hook failure
            context: Optional context with hook_name, hook_type, event, error_details, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "hook_name" in context:
                self.message = f"[Hook: {context['hook_name']}] {message}"
            if "hook_type" in context:
                self.message += f"\nType: {context['hook_type']}"
            if "event" in context:
                self.message += f"\nEvent: {context['event']}"
            if "error_details" in context:
                self.message += f"\nDetails: {context['error_details']}"


class SessionError(MPMError):
    """Exception raised when session management fails.

    This error occurs during Claude session lifecycle management including
    session creation, state management, and cleanup.

    Common causes:
    - Session initialization failure
    - Invalid session state
    - Session timeout
    - Resource allocation failure
    - Session persistence errors
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize session error.

        Args:
            message: Error message describing session failure
            context: Optional context with session_id, session_type, state, operation, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "session_id" in context:
                self.message = f"[Session: {context['session_id']}] {message}"
            if "session_type" in context:
                self.message += f"\nType: {context['session_type']}"
            if "state" in context:
                self.message += f"\nState: {context['state']}"
            if "operation" in context:
                self.message += f"\nOperation: {context['operation']}"


class FileOperationError(MPMError):
    """Exception raised when file system operations fail.

    This error occurs during file I/O operations including reading, writing,
    copying, moving, and permission changes.

    Common causes:
    - File not found
    - Permission denied
    - Disk space exhausted
    - Path too long
    - File locked by another process
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize file operation error.

        Args:
            message: Error message describing file operation failure
            context: Optional context with file_path, operation, permissions, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "file_path" in context:
                self.message = f"[File: {context['file_path']}] {message}"
            if "operation" in context:
                self.message += f"\nOperation: {context['operation']}"
            if "permissions" in context:
                self.message += f"\nRequired permissions: {context['permissions']}"


class ProcessError(MPMError):
    """Exception raised when subprocess operations fail.

    This error occurs during subprocess execution including command launching,
    process monitoring, and cleanup.

    Common causes:
    - Command not found
    - Process timeout
    - Non-zero exit code
    - Permission denied
    - Resource limits exceeded
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize process error.

        Args:
            message: Error message describing process failure
            context: Optional context with command, exit_code, stdout, stderr, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "command" in context:
                self.message = f"[Command: {context['command']}] {message}"
            if "exit_code" in context:
                self.message += f"\nExit code: {context['exit_code']}"
            if context.get("stderr"):
                stderr_preview = str(context["stderr"])[:200]
                self.message += f"\nError output: {stderr_preview}"
                if len(str(context["stderr"])) > 200:
                    self.message += "..."


class RegistryError(MPMError):
    """Exception raised when registry operations fail.

    This error occurs during agent registry operations including registration,
    lookup, modification tracking, and discovery.

    Common causes:
    - Agent not found in registry
    - Registry corruption
    - Concurrent modification conflicts
    - Invalid registry state
    - Registry initialization failure
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize registry error.

        Args:
            message: Error message describing registry failure
            context: Optional context with agent_id, registry_type, operation, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "agent_id" in context:
                self.message = f"[Agent: {context['agent_id']}] {message}"
            if "registry_type" in context:
                self.message += f"\nRegistry: {context['registry_type']}"
            if "operation" in context:
                self.message += f"\nOperation: {context['operation']}"


class SerializationError(MPMError):
    """Exception raised when serialization/deserialization fails.

    This error occurs during JSON/YAML/pickle operations including encoding,
    decoding, and format validation.

    Common causes:
    - Invalid JSON/YAML syntax
    - Unsupported data types
    - Encoding/decoding errors
    - Corrupted data
    - Schema validation failures
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize serialization error.

        Args:
            message: Error message describing serialization failure
            context: Optional context with format, data_type, file_path, etc.
        """
        super().__init__(message, context)

        # Add helpful guidance based on context
        if context:
            if "format" in context:
                self.message = f"[Format: {context['format']}] {message}"
            if "data_type" in context:
                self.message += f"\nData type: {context['data_type']}"
            if "file_path" in context:
                self.message += f"\nFile: {context['file_path']}"


# Backward compatibility imports
# These allow existing code to continue working while migrating to new exceptions
def create_agent_deployment_error(message: str, **kwargs) -> AgentDeploymentError:
    """Factory function for creating agent deployment errors with context."""
    return AgentDeploymentError(message, context=kwargs if kwargs else None)


def create_configuration_error(message: str, **kwargs) -> ConfigurationError:
    """Factory function for creating configuration errors with context."""
    return ConfigurationError(message, context=kwargs if kwargs else None)


def create_connection_error(message: str, **kwargs) -> ConnectionError:
    """Factory function for creating connection errors with context."""
    return ConnectionError(message, context=kwargs if kwargs else None)


def create_validation_error(message: str, **kwargs) -> ValidationError:
    """Factory function for creating validation errors with context."""
    return ValidationError(message, context=kwargs if kwargs else None)


# Exception groups for catch-all handling
DEPLOYMENT_ERRORS = (AgentDeploymentError,)
CONFIGURATION_ERRORS = (ConfigurationError, ValidationError)
NETWORK_ERRORS = (ConnectionError,)
SERVICE_ERRORS = (ServiceNotFoundError, MemoryError, HookError, SessionError)
FILE_ERRORS = (FileOperationError,)
PROCESS_ERRORS = (ProcessError,)
REGISTRY_ERRORS = (RegistryError,)
SERIALIZATION_ERRORS = (SerializationError,)
ALL_MPM_ERRORS = (MPMError,)  # Catches all MPM-specific exceptions
