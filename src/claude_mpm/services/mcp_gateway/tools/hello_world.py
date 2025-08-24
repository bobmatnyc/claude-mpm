"""
Hello World Tool for MCP Gateway Testing and Validation
=========================================================

Comprehensive Hello World tool that demonstrates all MCP capabilities.
This tool serves as the primary validation for the MCP Gateway system.

Part of ISS-0036: Hello World Tool - Testing and Validation Tool

WHY: We need a comprehensive test tool that exercises all MCP features
including async operations, input validation, error handling, multi-language
support, and proper metrics tracking. This tool validates that our MCP
Gateway is functioning correctly.

DESIGN DECISIONS:
- Multiple greeting variations to test different parameter combinations
- Async operations to validate async tool support
- Comprehensive input validation with detailed error messages
- Multi-language support to test Unicode handling
- Time-based greetings to test dynamic responses
- Detailed metrics tracking for monitoring
- Rich metadata in responses for debugging
"""

import asyncio
import json
import platform
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from claude_mpm.services.mcp_gateway.core.interfaces import (
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter


class HelloWorldTool(BaseToolAdapter):
    """
    Comprehensive Hello World tool for MCP Gateway testing.

    This tool provides multiple greeting variations to thoroughly test
    the MCP Gateway's tool execution capabilities.

    Features:
    - Simple greeting: Basic echo functionality
    - Personalized greeting: Name-based customization
    - Time-based greeting: Dynamic responses based on time of day
    - Multi-language greeting: Unicode and internationalization support
    - System info greeting: Integration with system information
    - Async greeting: Tests async operation support
    - Error scenarios: Validates error handling

    TRADE-OFFS:
    - Comprehensive testing vs simplicity: We chose comprehensive testing
      to ensure all MCP features work correctly
    - Multiple variations vs single greeting: Multiple variations allow
      testing different parameter combinations and edge cases
    """

    # Supported languages for multi-language greetings
    LANGUAGES = {
        "english": "Hello",
        "spanish": "Hola",
        "french": "Bonjour",
        "german": "Hallo",
        "italian": "Ciao",
        "portuguese": "Olá",
        "russian": "Привет",
        "japanese": "こんにちは",
        "chinese": "你好",
        "korean": "안녕하세요",
        "arabic": "مرحبا",
        "hindi": "नमस्ते",
        "hebrew": "שלום",
        "dutch": "Hallo",
        "polish": "Cześć",
        "swedish": "Hej",
        "norwegian": "Hei",
        "danish": "Hej",
        "finnish": "Hei",
        "greek": "Γειά σου",
        "turkish": "Merhaba",
        "thai": "สวัสดี",
        "vietnamese": "Xin chào",
        "indonesian": "Halo",
        "malay": "Hai",
    }

    # Time-based greeting thresholds
    TIME_GREETINGS = {
        (0, 5): "Good night",
        (5, 12): "Good morning",
        (12, 17): "Good afternoon",
        (17, 21): "Good evening",
        (21, 24): "Good night",
    }

    def __init__(self):
        """Initialize the Hello World tool with comprehensive schema."""
        definition = MCPToolDefinition(
            name="hello_world",
            description=(
                "A comprehensive Hello World tool for testing MCP Gateway functionality. "
                "Provides multiple greeting variations including simple, personalized, "
                "time-based, and multi-language greetings."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": [
                            "simple",
                            "personalized",
                            "time_based",
                            "multi_language",
                            "system_info",
                            "async_test",
                            "error_test",
                        ],
                        "description": "The greeting mode to use",
                        "default": "simple",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for personalized greeting (required for personalized mode)",
                        "minLength": 1,
                        "maxLength": 100,
                    },
                    "language": {
                        "type": "string",
                        "description": "Language for multi-language greeting",
                        "enum": list(self.LANGUAGES.keys()),
                        "default": "english",
                    },
                    "delay_ms": {
                        "type": "number",
                        "description": "Delay in milliseconds for async test",
                        "minimum": 0,
                        "maximum": 5000,
                        "default": 1000,
                    },
                    "error_type": {
                        "type": "string",
                        "enum": ["validation", "runtime", "timeout"],
                        "description": "Type of error to simulate for error_test mode",
                        "default": "validation",
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Whether to include detailed metadata in response",
                        "default": True,
                    },
                    "uppercase": {
                        "type": "boolean",
                        "description": "Convert greeting to uppercase",
                        "default": False,
                    },
                    "repeat": {
                        "type": "number",
                        "description": "Number of times to repeat the greeting",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 1,
                    },
                },
                "required": ["mode"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {
                    "greeting": {
                        "type": "string",
                        "description": "The generated greeting message",
                    },
                    "mode": {"type": "string", "description": "The mode that was used"},
                    "timestamp": {
                        "type": "string",
                        "description": "ISO timestamp when greeting was generated",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata about the greeting",
                        "properties": {
                            "tool_version": {"type": "string"},
                            "execution_environment": {"type": "object"},
                            "parameters_used": {"type": "object"},
                        },
                    },
                },
            },
        )
        super().__init__(definition)

        # Tool version for tracking
        self.version = "1.0.0"

        # Track greeting history for analytics
        self.greeting_history: List[Dict[str, Any]] = []
        self.max_history_size = 100

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Enhanced parameter validation with detailed error messages.

        Args:
            parameters: Parameters to validate

        Returns:
            True if parameters are valid, False otherwise
        """
        # First do base validation
        if not super().validate_parameters(parameters):
            return False

        mode = parameters.get("mode", "simple")

        # Validate mode is in allowed enum
        valid_modes = [
            "simple",
            "personalized",
            "time_based",
            "multi_language",
            "system_info",
            "async_test",
            "error_test",
        ]
        if mode not in valid_modes:
            self.log_error(f"Invalid mode: {mode}. Must be one of {valid_modes}")
            return False

        # Mode-specific validation
        if mode == "personalized":
            if "name" not in parameters or not parameters["name"]:
                self.log_error("Personalized mode requires 'name' parameter")
                return False

            # Validate name format (alphanumeric and basic punctuation)
            name = parameters["name"]
            if not re.match(r"^[a-zA-Z0-9\s\-\'\.]+$", name):
                self.log_error(f"Invalid name format: {name}")
                return False

        elif mode == "multi_language":
            language = parameters.get("language", "english")
            if language not in self.LANGUAGES:
                self.log_error(f"Unsupported language: {language}")
                return False

        elif mode == "async_test":
            delay = parameters.get("delay_ms", 1000)
            if not isinstance(delay, (int, float)) or delay < 0 or delay > 5000:
                self.log_error(f"Invalid delay_ms: {delay} (must be 0-5000)")
                return False

        elif mode == "error_test":
            error_type = parameters.get("error_type", "validation")
            if error_type not in ["validation", "runtime", "timeout"]:
                self.log_error(f"Invalid error_type: {error_type}")
                return False

        # Validate common parameters
        repeat = parameters.get("repeat", 1)
        if not isinstance(repeat, int) or repeat < 1 or repeat > 10:
            self.log_error(f"Invalid repeat value: {repeat} (must be 1-10)")
            return False

        return True

    async def initialize(self) -> bool:
        """
        Initialize the Hello World tool.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info(f"Initializing Hello World Tool v{self.version}")

            # Clear greeting history
            self.greeting_history.clear()

            # Mark as initialized
            self._initialized = True

            self.log_info("Hello World Tool initialized successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize Hello World Tool: {e}")
            return False

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke the Hello World tool with the specified mode.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with greeting
        """
        start_time = datetime.now()

        try:
            # Validate parameters
            if not self.validate_parameters(invocation.parameters):
                return MCPToolResult(
                    success=False,
                    error="Parameter validation failed",
                    execution_time=0.0,
                )

            # Extract parameters
            mode = invocation.parameters.get("mode", "simple")
            include_metadata = invocation.parameters.get("include_metadata", True)
            uppercase = invocation.parameters.get("uppercase", False)
            repeat = invocation.parameters.get("repeat", 1)

            # Generate greeting based on mode
            if mode == "simple":
                greeting = await self._simple_greeting()
            elif mode == "personalized":
                name = invocation.parameters["name"]
                greeting = await self._personalized_greeting(name)
            elif mode == "time_based":
                greeting = await self._time_based_greeting()
            elif mode == "multi_language":
                language = invocation.parameters.get("language", "english")
                name = invocation.parameters.get("name")
                greeting = await self._multi_language_greeting(language, name)
            elif mode == "system_info":
                greeting = await self._system_info_greeting()
            elif mode == "async_test":
                delay_ms = invocation.parameters.get("delay_ms", 1000)
                greeting = await self._async_greeting(delay_ms)
            elif mode == "error_test":
                error_type = invocation.parameters.get("error_type", "validation")
                return await self._error_test(error_type)
            else:
                greeting = f"Hello World! (Unknown mode: {mode})"

            # Apply transformations
            if uppercase:
                greeting = greeting.upper()

            if repeat > 1:
                greeting = " ".join([greeting] * repeat)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Build response data
            response_data = {
                "greeting": greeting,
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
            }

            # Add metadata if requested
            if include_metadata:
                response_data["metadata"] = {
                    "tool_version": self.version,
                    "execution_environment": {
                        "platform": platform.platform(),
                        "python_version": sys.version,
                        "processor": platform.processor() or "unknown",
                    },
                    "parameters_used": invocation.parameters,
                    "execution_time_ms": execution_time * 1000,
                }

            # Track in history
            self._add_to_history(mode, greeting, execution_time)

            # Update metrics
            self._update_metrics(True, execution_time)

            return MCPToolResult(
                success=True,
                data=response_data,
                execution_time=execution_time,
                metadata={"tool": "hello_world", "version": self.version, "mode": mode},
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)
            self._metrics["last_error"] = str(e)

            return MCPToolResult(
                success=False,
                error=f"Hello World tool failed: {e!s}",
                execution_time=execution_time,
            )

    async def _simple_greeting(self) -> str:
        """Generate a simple greeting."""
        return "Hello World!"

    async def _personalized_greeting(self, name: str) -> str:
        """Generate a personalized greeting."""
        return f"Hello, {name}! Welcome to the MCP Gateway."

    async def _time_based_greeting(self) -> str:
        """Generate a greeting based on current time."""
        current_hour = datetime.now().hour

        for (start, end), greeting in self.TIME_GREETINGS.items():
            if start <= current_hour < end:
                return f"{greeting}! It's {datetime.now().strftime('%I:%M %p')}."

        return "Hello! Time is a curious thing."

    async def _multi_language_greeting(
        self, language: str, name: Optional[str] = None
    ) -> str:
        """Generate a greeting in the specified language."""
        greeting_word = self.LANGUAGES.get(language, "Hello")

        if name:
            # Add name if provided (works for most languages)
            return f"{greeting_word}, {name}!"
        return f"{greeting_word}, World!"

    async def _system_info_greeting(self) -> str:
        """Generate a greeting with system information."""
        system = platform.system()
        node = platform.node()
        py_version = platform.python_version()

        return (
            f"Hello from {system} on {node}! "
            f"Running Python {py_version} with MCP Gateway."
        )

    async def _async_greeting(self, delay_ms: int) -> str:
        """Generate a greeting after an async delay."""
        self.log_info(f"Starting async greeting with {delay_ms}ms delay")

        # Convert milliseconds to seconds for asyncio.sleep
        delay_seconds = delay_ms / 1000.0
        await asyncio.sleep(delay_seconds)

        return f"Hello World! (after {delay_ms}ms async delay)"

    async def _error_test(self, error_type: str) -> MCPToolResult:
        """Simulate various error conditions for testing."""
        if error_type == "validation":
            return MCPToolResult(
                success=False,
                error="Simulated validation error: Invalid input parameters",
                execution_time=0.001,
            )
        if error_type == "runtime":
            # Simulate a runtime error
            raise RuntimeError("Simulated runtime error during greeting generation")
        if error_type == "timeout":
            # Simulate a timeout by sleeping longer than reasonable
            await asyncio.sleep(10)  # This would typically trigger a timeout
            return MCPToolResult(
                success=False, error="Operation timed out", execution_time=10.0
            )
        return MCPToolResult(
            success=False,
            error=f"Unknown error type: {error_type}",
            execution_time=0.001,
        )

    def _add_to_history(self, mode: str, greeting: str, execution_time: float) -> None:
        """
        Add greeting to history for analytics.

        Args:
            mode: Greeting mode used
            greeting: Generated greeting
            execution_time: Time taken to generate greeting
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "greeting": greeting[:100],  # Truncate long greetings
            "execution_time": execution_time,
        }

        self.greeting_history.append(entry)

        # Maintain history size limit
        if len(self.greeting_history) > self.max_history_size:
            self.greeting_history.pop(0)

    def get_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about tool usage.

        Returns:
            Analytics dictionary with usage statistics
        """
        if not self.greeting_history:
            return {
                "total_greetings": 0,
                "modes_used": {},
                "average_execution_time": 0.0,
                "last_greeting": None,
            }

        # Calculate mode usage
        modes_used = {}
        total_time = 0.0

        for entry in self.greeting_history:
            mode = entry["mode"]
            modes_used[mode] = modes_used.get(mode, 0) + 1
            total_time += entry["execution_time"]

        return {
            "total_greetings": len(self.greeting_history),
            "modes_used": modes_used,
            "average_execution_time": total_time / len(self.greeting_history),
            "last_greeting": (
                self.greeting_history[-1] if self.greeting_history else None
            ),
            "metrics": self.get_metrics(),
        }

    async def shutdown(self) -> None:
        """
        Shutdown the Hello World tool and clean up resources.
        """
        try:
            self.log_info(f"Shutting down Hello World Tool v{self.version}")

            # Log final analytics
            analytics = self.get_analytics()
            self.log_info(f"Final analytics: {json.dumps(analytics, indent=2)}")

            # Clear history
            self.greeting_history.clear()

            # Mark as not initialized
            self._initialized = False

            self.log_info("Hello World Tool shutdown complete")

        except Exception as e:
            self.log_error(f"Error during Hello World Tool shutdown: {e}")
