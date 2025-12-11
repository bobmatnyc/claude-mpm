"""
MCP Gateway Interface Definitions
==================================

This module defines the core interfaces for the MCP Gateway service,
establishing contracts for dependency injection and service orchestration.

Part of ISS-0034: Infrastructure Setup - MCP Gateway Project Foundation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# Tool-related data structures
@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MCPToolInvocation:
    """Represents a tool invocation request."""

    tool_name: str
    parameters: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    timeout: Optional[float] = None
    request_id: Optional[str] = None


@dataclass
class MCPToolResult:
    """Result from a tool invocation."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None


# Core MCP interfaces
class IMCPConfiguration(ABC):
    """
    Interface for MCP configuration management.

    Handles loading, validation, and access to MCP Gateway configuration.
    """

    @abstractmethod
    def load_config(self, config_path: Path) -> bool:
        """
        Load configuration from a file.

        Args:
            config_path: Path to configuration file

        Returns:
            True if configuration loaded successfully
        """

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Configuration value
        """

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate the current configuration.

        Returns:
            True if configuration is valid
        """

    @abstractmethod
    def get_server_config(self) -> Dict[str, Any]:
        """
        Get MCP server configuration.

        Returns:
            Server configuration dictionary
        """

    @abstractmethod
    def get_tools_config(self) -> Dict[str, Any]:
        """
        Get tools configuration.

        Returns:
            Tools configuration dictionary
        """


class IMCPToolAdapter(ABC):
    """
    Interface for MCP tool adapters.

    Tool adapters wrap external tools to make them MCP-compatible.
    """

    @abstractmethod
    def get_definition(self) -> MCPToolDefinition:
        """
        Get the tool definition.

        Returns:
            Tool definition with schema and metadata
        """

    @abstractmethod
    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke the tool with given parameters.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result
        """

    @abstractmethod
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate tool parameters against schema.

        Args:
            parameters: Parameters to validate

        Returns:
            True if parameters are valid
        """

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the tool adapter.

        Returns:
            True if initialization successful
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the tool adapter and clean up resources.
        """


class IMCPToolRegistry(ABC):
    """
    Interface for MCP tool registry.

    Manages registration, discovery, and invocation of MCP tools.
    """

    @abstractmethod
    def register_tool(self, adapter: IMCPToolAdapter) -> bool:
        """
        Register a tool adapter.

        Args:
            adapter: Tool adapter to register

        Returns:
            True if registration successful
        """

    @abstractmethod
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool by name.

        Args:
            tool_name: Name of tool to unregister

        Returns:
            True if unregistration successful
        """

    @abstractmethod
    def get_tool(self, tool_name: str) -> Optional[IMCPToolAdapter]:
        """
        Get a tool adapter by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool adapter if found, None otherwise
        """

    @abstractmethod
    def list_tools(self) -> List[MCPToolDefinition]:
        """
        List all registered tools.

        Returns:
            List of tool definitions
        """

    @abstractmethod
    async def invoke_tool(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke a tool through the registry.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result
        """

    @abstractmethod
    def search_tools(self, query: str) -> List[MCPToolDefinition]:
        """
        Search for tools by query.

        Args:
            query: Search query

        Returns:
            List of matching tool definitions
        """


class IMCPCommunication(ABC):
    """
    Interface for MCP communication handling.

    Manages stdio-based communication with MCP clients.
    """

    @abstractmethod
    async def send_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message to the MCP client.

        Args:
            message: Message to send
        """

    @abstractmethod
    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """
        Receive a message from the MCP client.

        Returns:
            Received message or None if no message available
        """

    @abstractmethod
    async def send_response(self, request_id: str, result: Any) -> None:
        """
        Send a response to a request.

        Args:
            request_id: ID of the request being responded to
            result: Result data
        """

    @abstractmethod
    async def send_error(self, request_id: str, error: str, code: int = -1) -> None:
        """
        Send an error response.

        Args:
            request_id: ID of the request that caused the error
            error: Error message
            code: Error code
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if communication channel is connected.

        Returns:
            True if connected
        """


class IMCPLifecycle(ABC):
    """
    Interface for MCP service lifecycle management.

    Manages initialization, startup, shutdown, and health monitoring.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the MCP service.

        Returns:
            True if initialization successful
        """

    @abstractmethod
    async def start(self) -> bool:
        """
        Start the MCP service.

        Returns:
            True if startup successful
        """

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the MCP service gracefully.
        """

    @abstractmethod
    async def restart(self) -> bool:
        """
        Restart the MCP service.

        Returns:
            True if restart successful
        """

    @abstractmethod
    def get_state(self) -> str:
        """
        Get current service state.

        Returns:
            Service state (e.g., "initialized", "running", "stopped")
        """

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if service is healthy.

        Returns:
            True if service is healthy
        """

    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get detailed health status.

        Returns:
            Health status information
        """


class IMCPGateway(IMCPLifecycle):
    """
    Main interface for MCP gateway implementation.

    Orchestrates tool registry, communication, and request handling.
    Acts as a protocol bridge between Claude Code and internal tools.
    """

    @abstractmethod
    def set_tool_registry(self, registry: IMCPToolRegistry) -> None:
        """
        Set the tool registry for the server.

        Args:
            registry: Tool registry to use
        """

    @abstractmethod
    def set_communication(self, communication: IMCPCommunication) -> None:
        """
        Set the communication handler.

        Args:
            communication: Communication handler to use
        """

    @abstractmethod
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request.

        Args:
            request: MCP request message

        Returns:
            Response message
        """

    @abstractmethod
    async def run(self) -> None:
        """
        Run the MCP gateway main loop.

        This method should handle incoming requests and manage the gateway lifecycle.
        """

    @abstractmethod
    def register_handler(self, method: str, handler: Callable) -> None:
        """
        Register a custom request handler.

        Args:
            method: Method name to handle
            handler: Handler function
        """

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get gateway capabilities.

        Returns:
            Dictionary of gateway capabilities
        """
