"""
MCP Gateway Implementation
==========================

MCP protocol gateway using Anthropic's official MCP package.
Handles stdio-based communication, request routing, and tool invocation.
Acts as a bridge between Claude Code and internal tools.

NOTE: MCP is ONLY for Claude Code - NOT for Claude Code.
Claude Code uses a different system for agent deployment.

Part of ISS-0035: MCP Gateway Implementation - Core Gateway and Tool Registry
"""

import asyncio
import contextlib
import json
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

# Import from the official MCP package
from mcp.server import Server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    TextContent,
    Tool,
)

from claude_mpm.services.mcp_gateway.core.base import BaseMCPService
from claude_mpm.services.mcp_gateway.core.interfaces import (
    IMCPCommunication,
    IMCPGateway,
    IMCPToolRegistry,
    MCPToolInvocation,
)


class MCPGateway(BaseMCPService, IMCPGateway):
    """
    MCP Protocol Gateway implementation using Anthropic's official MCP package.

    WHY: We use the official MCP package to ensure protocol compliance and
    compatibility with Claude Code. The stdio-based communication model allows
    seamless integration with Claude Code's MCP client as a protocol bridge.

    DESIGN DECISIONS:
    - Use asyncio for all I/O operations to handle concurrent requests efficiently
    - Maintain request handlers in a dictionary for extensibility
    - Implement comprehensive error handling to prevent gateway crashes
    - Use structured logging for debugging and monitoring
    """

    def __init__(self, gateway_name: str = "claude-mpm-mcp", version: str = "1.0.0"):
        """
        Initialize MCP Gateway.

        Args:
            gateway_name: Name of the MCP gateway
            version: Gateway version
        """
        super().__init__(f"MCPGateway-{gateway_name}")

        # Gateway configuration
        self.gateway_name = gateway_name
        self.server_name = gateway_name  # Keep for compatibility
        self.version = version

        # MCP Server instance from official package
        self.mcp_server = Server(gateway_name)

        # Dependencies (injected via setters)
        self._tool_registry: Optional[IMCPToolRegistry] = None
        self._communication: Optional[IMCPCommunication] = None

        # Request handlers
        self._handlers: Dict[str, Callable] = {}

        # Server capabilities
        self._capabilities = {
            "tools": {},
            "prompts": {},
            "resources": {},
            "experimental": {},
        }

        # Metrics
        self._metrics = {
            "requests_handled": 0,
            "errors": 0,
            "tool_invocations": 0,
            "start_time": None,
            "last_request_time": None,
        }

        # Running state
        self._run_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Setup default handlers
        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """
        Setup default MCP protocol handlers.

        WHY: The MCP protocol requires specific handlers for initialization,
        tool discovery, and tool invocation. We set these up to ensure
        protocol compliance.
        """

        # Initialize handler
        @self.mcp_server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Handle tools/list request."""
            self.log_info("Handling tools/list request")

            if not self._tool_registry:
                self.log_warning("No tool registry available")
                return []

            tools = []
            for tool_def in self._tool_registry.list_tools():
                tool = Tool(
                    name=tool_def.name,
                    description=tool_def.description,
                    inputSchema=tool_def.input_schema,
                )
                tools.append(tool)

            self.log_info(f"Returning {len(tools)} tools")
            return tools

        @self.mcp_server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
            """Handle tools/call request."""
            self.log_info(f"Handling tools/call request for tool: {name}")

            if not self._tool_registry:
                error_msg = "No tool registry available"
                self.log_error(error_msg)
                return [TextContent(type="text", text=f"Error: {error_msg}")]

            # Create invocation request
            invocation = MCPToolInvocation(
                tool_name=name,
                parameters=arguments,
                request_id=f"req_{datetime.now().timestamp()}",
            )

            try:
                # Invoke tool through registry
                result = await self._tool_registry.invoke_tool(invocation)

                # Update metrics
                self._metrics["tool_invocations"] += 1

                # Log invocation
                self.log_tool_invocation(name, result.success, result.execution_time)

                if result.success:
                    # Return successful result
                    if isinstance(result.data, str):
                        return [TextContent(type="text", text=result.data)]
                    return [
                        TextContent(type="text", text=json.dumps(result.data, indent=2))
                    ]
                # Return error
                return [TextContent(type="text", text=f"Error: {result.error}")]

            except Exception as e:
                error_msg = f"Failed to invoke tool {name}: {e!s}"
                self.log_error(error_msg)
                self._metrics["errors"] += 1
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    def set_tool_registry(self, registry: IMCPToolRegistry) -> None:
        """
        Set the tool registry for the server.

        Args:
            registry: Tool registry to use
        """
        self._tool_registry = registry
        self.log_info("Tool registry set")

    def set_communication(self, communication: IMCPCommunication) -> None:
        """
        Set the communication handler.

        Args:
            communication: Communication handler to use
        """
        self._communication = communication
        self.log_info("Communication handler set")

    async def _do_initialize(self) -> bool:
        """
        Perform server initialization.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing MCP server components")

            # Validate dependencies
            if not self._tool_registry:
                self.log_warning("No tool registry set - server will have no tools")

            # Initialize metrics
            self._metrics["start_time"] = datetime.now().isoformat()

            # Update capabilities based on registry
            if self._tool_registry:
                tools = self._tool_registry.list_tools()
                self._capabilities["tools"]["available"] = len(tools)
                self._capabilities["tools"]["names"] = [t.name for t in tools]

            self.log_info("MCP server initialization complete")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize MCP server: {e}")
            return False

    async def _do_start(self) -> bool:
        """
        Start the MCP server.

        Returns:
            True if startup successful
        """
        try:
            self.log_info("Starting MCP server")

            # Clear shutdown event
            self._shutdown_event.clear()

            # Start the run task
            self._run_task = asyncio.create_task(self.run())

            self.log_info("MCP server started successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to start MCP server: {e}")
            return False

    async def _do_shutdown(self) -> None:
        """
        Shutdown the MCP server gracefully.
        """
        self.log_info("Shutting down MCP server")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel run task if active
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._run_task

        # Clean up resources
        if self._tool_registry:
            self.log_info("Cleaning up tool registry")
            # Tool registry cleanup if needed

        self.log_info("MCP server shutdown complete")

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request.

        This method routes requests to appropriate handlers based on the method.

        Args:
            request: MCP request message

        Returns:
            Response message
        """
        try:
            # Update metrics
            self._metrics["requests_handled"] += 1
            self._metrics["last_request_time"] = datetime.now().isoformat()

            # Extract request details
            method = request.get("method", "")
            params = request.get("params", {})
            request_id = request.get("id")

            self.log_debug(f"Handling request: {method}")

            # Check for custom handler
            if method in self._handlers:
                handler = self._handlers[method]
                result = await handler(params)

                # Build response
                response = {"jsonrpc": "2.0", "id": request_id, "result": result}
            else:
                # Unknown method
                self.log_warning(f"Unknown method: {method}")
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

            return response

        except Exception as e:
            self.log_error(f"Error handling request: {e}")
            self._metrics["errors"] += 1

            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32603, "message": f"Internal error: {e!s}"},
            }

    async def run(self) -> None:
        """
        Run the MCP server main loop.

        This method uses the official MCP Server's stdio-based communication
        to handle incoming requests from Claude Code.

        WHY: We use stdio (stdin/stdout) as it's the standard communication
        method for MCP servers in Claude Code. This ensures compatibility
        and allows the server to be launched as a subprocess.
        """
        try:
            self.log_info("Starting MCP server main loop")

            # Import the stdio server function
            from mcp.server.lowlevel import NotificationOptions
            from mcp.server.models import InitializationOptions
            from mcp.server.stdio import stdio_server

            # Create initialization options
            init_options = InitializationOptions(
                server_name=self.server_name,
                server_version=self.version,
                capabilities=self.mcp_server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )

            # Run the MCP server with stdio transport
            async with stdio_server() as (read_stream, write_stream):
                self.log_info("MCP server stdio connection established")

                # Run the server
                await self.mcp_server.run(read_stream, write_stream, init_options)

            self.log_info("MCP server main loop ended")

        except Exception as e:
            self.log_error(f"Error in MCP server main loop: {e}")
            self.log_error(f"Traceback: {traceback.format_exc()}")
            self._metrics["errors"] += 1
            raise

    def register_handler(self, method: str, handler: Callable) -> None:
        """
        Register a custom request handler.

        Args:
            method: Method name to handle
            handler: Handler function
        """
        self._handlers[method] = handler
        self.log_info(f"Registered handler for method: {method}")

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get server capabilities.

        Returns:
            Dictionary of server capabilities formatted for MCP protocol
        """
        capabilities = {}

        # Add tool capabilities if registry is available
        if self._tool_registry:
            capabilities["tools"] = {}

        # Add experimental features
        capabilities["experimental"] = {}

        return capabilities

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get server metrics.

        Returns:
            Server metrics dictionary
        """
        return self._metrics.copy()

    async def stop(self) -> None:
        """
        Stop the MCP service gracefully.

        This implements the IMCPLifecycle interface method.
        """
        await self.shutdown()


# Backward compatibility alias
MCPServer = MCPGateway
