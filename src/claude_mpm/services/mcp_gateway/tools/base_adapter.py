"""
Base Tool Adapter and Example Implementations
==============================================

Base class for MCP tool adapters and example implementations.

Part of ISS-0035: MCP Server Implementation - Core Server and Tool Registry
"""

from abc import ABC
from datetime import datetime
from typing import Any, Dict

from claude_mpm.services.mcp_gateway.core.base import BaseMCPService
from claude_mpm.services.mcp_gateway.core.interfaces import (
    IMCPToolAdapter,
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)


class BaseToolAdapter(BaseMCPService, IMCPToolAdapter, ABC):
    """
    Base class for MCP tool adapters.

    WHY: This base class provides common functionality for all tool adapters,
    including parameter validation, error handling, and metrics tracking.
    Concrete tool implementations should extend this class.

    DESIGN DECISIONS:
    - Provide default parameter validation using JSON Schema
    - Include standard error handling and logging
    - Track execution metrics for monitoring
    - Support both sync and async tool implementations
    """

    def __init__(self, tool_definition: MCPToolDefinition):
        """
        Initialize the base tool adapter.

        Args:
            tool_definition: Tool definition with schema and metadata
        """
        super().__init__(f"Tool-{tool_definition.name}")
        self._definition = tool_definition
        self._initialized = False

        # Metrics
        self._metrics = {
            "invocations": 0,
            "successes": 0,
            "failures": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "last_invocation": None,
            "last_error": None,
        }

    def get_definition(self) -> MCPToolDefinition:
        """
        Get the tool definition.

        Returns:
            Tool definition with schema and metadata
        """
        return self._definition

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate tool parameters against schema.

        Default implementation performs basic JSON Schema validation.
        Override for custom validation logic.

        Args:
            parameters: Parameters to validate

        Returns:
            True if parameters are valid
        """
        try:
            # Get required parameters from schema
            schema = self._definition.input_schema
            required = schema.get("required", [])
            properties = schema.get("properties", {})

            # Check required parameters
            for param in required:
                if param not in parameters:
                    self.log_error(f"Missing required parameter: {param}")
                    return False

            # Check parameter types (basic validation)
            for param_name, param_value in parameters.items():
                if param_name in properties:
                    expected_type = properties[param_name].get("type")
                    if expected_type:
                        if not self._validate_type(param_value, expected_type):
                            self.log_error(
                                f"Invalid type for parameter {param_name}: expected {expected_type}"
                            )
                            return False

            return True

        except Exception as e:
            self.log_error(f"Error validating parameters: {e}")
            return False

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """
        Validate a value against an expected JSON Schema type.

        Args:
            value: Value to validate
            expected_type: Expected type (string, number, boolean, array, object)

        Returns:
            True if type matches
        """
        type_map = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)

        return True  # Unknown type, allow it

    async def initialize(self) -> bool:
        """
        Initialize the tool adapter.

        Default implementation marks as initialized.
        Override for custom initialization logic.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info(f"Initializing tool: {self._definition.name}")
            self._initialized = True
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize tool: {e}")
            return False

    async def shutdown(self) -> None:
        """
        Shutdown the tool adapter and clean up resources.

        Default implementation marks as not initialized.
        Override for custom cleanup logic.
        """
        try:
            self.log_info(f"Shutting down tool: {self._definition.name}")
            self._initialized = False

        except Exception as e:
            self.log_error(f"Error during tool shutdown: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get tool metrics.

        Returns:
            Metrics dictionary
        """
        return self._metrics.copy()

    def _update_metrics(self, success: bool, execution_time: float) -> None:
        """
        Update tool metrics after invocation.

        Args:
            success: Whether invocation was successful
            execution_time: Execution time in seconds
        """
        self._metrics["invocations"] += 1

        if success:
            self._metrics["successes"] += 1
        else:
            self._metrics["failures"] += 1

        self._metrics["total_execution_time"] += execution_time
        self._metrics["average_execution_time"] = (
            self._metrics["total_execution_time"] / self._metrics["invocations"]
        )
        self._metrics["last_invocation"] = datetime.now().isoformat()


class EchoToolAdapter(BaseToolAdapter):
    """
    Example tool adapter that echoes input back.

    This is a simple example showing how to implement a concrete tool adapter.
    """

    def __init__(self):
        """Initialize the echo tool."""
        definition = MCPToolDefinition(
            name="echo",
            description="Echoes the input message back to the user",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The message to echo"},
                    "uppercase": {
                        "type": "boolean",
                        "description": "Whether to convert to uppercase",
                        "default": False,
                    },
                },
                "required": ["message"],
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke the echo tool.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with echoed message
        """
        start_time = datetime.now()

        try:
            # Get parameters
            message = invocation.parameters.get("message", "")
            uppercase = invocation.parameters.get("uppercase", False)

            # Process message
            result = message.upper() if uppercase else message

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Update metrics
            self._update_metrics(True, execution_time)

            return MCPToolResult(
                success=True,
                data=result,
                execution_time=execution_time,
                metadata={"tool": "echo", "length": len(result)},
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)
            self._metrics["last_error"] = str(e)

            return MCPToolResult(
                success=False,
                error=f"Echo tool failed: {e!s}",
                execution_time=execution_time,
            )


class CalculatorToolAdapter(BaseToolAdapter):
    """
    Example calculator tool adapter.

    Demonstrates a more complex tool with multiple operations.
    """

    def __init__(self):
        """Initialize the calculator tool."""
        definition = MCPToolDefinition(
            name="calculator",
            description="Performs basic mathematical calculations",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "The mathematical operation to perform",
                    },
                    "a": {"type": "number", "description": "First operand"},
                    "b": {"type": "number", "description": "Second operand"},
                },
                "required": ["operation", "a", "b"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "result": {
                        "type": "number",
                        "description": "The calculation result",
                    },
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression",
                    },
                },
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke the calculator tool.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with calculation
        """
        start_time = datetime.now()

        try:
            # Get parameters
            operation = invocation.parameters["operation"]
            a = invocation.parameters["a"]
            b = invocation.parameters["b"]

            # Perform calculation
            if operation == "add":
                result = a + b
                expression = f"{a} + {b} = {result}"
            elif operation == "subtract":
                result = a - b
                expression = f"{a} - {b} = {result}"
            elif operation == "multiply":
                result = a * b
                expression = f"{a} * {b} = {result}"
            elif operation == "divide":
                if b == 0:
                    raise ValueError("Division by zero")
                result = a / b
                expression = f"{a} / {b} = {result}"
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Update metrics
            self._update_metrics(True, execution_time)

            return MCPToolResult(
                success=True,
                data={"result": result, "expression": expression},
                execution_time=execution_time,
                metadata={"tool": "calculator", "operation": operation},
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)
            self._metrics["last_error"] = str(e)

            return MCPToolResult(
                success=False,
                error=f"Calculator tool failed: {e!s}",
                execution_time=execution_time,
            )


class SystemInfoToolAdapter(BaseToolAdapter):
    """
    Example system information tool adapter.

    Demonstrates async operations and system interaction.
    """

    def __init__(self):
        """Initialize the system info tool."""
        definition = MCPToolDefinition(
            name="system_info",
            description="Provides system information",
            input_schema={
                "type": "object",
                "properties": {
                    "info_type": {
                        "type": "string",
                        "enum": ["platform", "memory", "cpu", "time"],
                        "description": "Type of system information to retrieve",
                    }
                },
                "required": ["info_type"],
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke the system info tool.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with system information
        """
        start_time = datetime.now()

        try:
            import platform

            import psutil

            info_type = invocation.parameters["info_type"]

            if info_type == "platform":
                result = {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "python_version": platform.python_version(),
                }
            elif info_type == "memory":
                mem = psutil.virtual_memory()
                result = {
                    "total": mem.total,
                    "available": mem.available,
                    "percent": mem.percent,
                    "used": mem.used,
                    "free": mem.free,
                }
            elif info_type == "cpu":
                result = {
                    "count": psutil.cpu_count(),
                    "percent": psutil.cpu_percent(interval=0.1),
                    "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                }
            elif info_type == "time":
                result = {
                    "current": datetime.now().isoformat(),
                    "timestamp": datetime.now().timestamp(),
                    "timezone": str(datetime.now().astimezone().tzinfo),
                }
            else:
                raise ValueError(f"Unknown info type: {info_type}")

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Update metrics
            self._update_metrics(True, execution_time)

            return MCPToolResult(
                success=True,
                data=result,
                execution_time=execution_time,
                metadata={"tool": "system_info", "info_type": info_type},
            )

        except ImportError as e:
            # Handle missing psutil dependency gracefully
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"System info tool requires psutil: {e!s}",
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)
            self._metrics["last_error"] = str(e)

            return MCPToolResult(
                success=False,
                error=f"System info tool failed: {e!s}",
                execution_time=execution_time,
            )
