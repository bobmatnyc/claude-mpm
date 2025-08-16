"""
Simple MCP Server Implementation
=================================

A simplified MCP server implementation that follows the MCP protocol
without requiring the official MCP package.

Part of ISS-0035: MCP Server Implementation - Core Server and Tool Registry
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime
import traceback

from claude_mpm.services.mcp_gateway.core.interfaces import (
    IMCPServer,
    IMCPToolRegistry,
    IMCPCommunication,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.core.base import BaseMCPService, MCPServiceState


class SimpleMCPServer(BaseMCPService, IMCPServer):
    """
    Simplified MCP Server implementation using JSON-RPC over stdio.
    
    WHY: This implementation provides MCP protocol compatibility without
    requiring the official MCP package, making it more portable and testable.
    
    DESIGN DECISIONS:
    - Use standard JSON-RPC 2.0 protocol
    - Implement core MCP methods (initialize, tools/list, tools/call)
    - Handle stdio communication directly
    - Maintain compatibility with Claude Desktop's expectations
    """
    
    def __init__(self, server_name: str = "claude-mpm-mcp", version: str = "1.0.0"):
        """
        Initialize Simple MCP Server.
        
        Args:
            server_name: Name of the MCP server
            version: Server version
        """
        super().__init__(f"SimpleMCPServer-{server_name}")
        
        # Server configuration
        self.server_name = server_name
        self.version = version
        
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
            "experimental": {}
        }
        
        # Metrics
        self._metrics = {
            "requests_handled": 0,
            "errors": 0,
            "tool_invocations": 0,
            "start_time": None,
            "last_request_time": None
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
        async def handle_initialize(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle initialize request."""
            self.log_info("Handling initialize request")
            
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": self.get_capabilities(),
                "serverInfo": {
                    "name": self.server_name,
                    "version": self.version
                }
            }
        
        self._handlers["initialize"] = handle_initialize
        
        # Tools list handler
        async def handle_tools_list(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle tools/list request."""
            self.log_info("Handling tools/list request")
            
            if not self._tool_registry:
                self.log_warning("No tool registry available")
                return {"tools": []}
            
            tools = []
            for tool_def in self._tool_registry.list_tools():
                tool = {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "inputSchema": tool_def.input_schema
                }
                tools.append(tool)
            
            self.log_info(f"Returning {len(tools)} tools")
            return {"tools": tools}
        
        self._handlers["tools/list"] = handle_tools_list
        
        # Tools call handler
        async def handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle tools/call request."""
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            
            self.log_info(f"Handling tools/call request for tool: {name}")
            
            if not self._tool_registry:
                error_msg = "No tool registry available"
                self.log_error(error_msg)
                return {
                    "content": [
                        {"type": "text", "text": f"Error: {error_msg}"}
                    ]
                }
            
            # Create invocation request
            invocation = MCPToolInvocation(
                tool_name=name,
                parameters=arguments,
                request_id=f"req_{datetime.now().timestamp()}"
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
                        content = [{"type": "text", "text": result.data}]
                    else:
                        content = [{"type": "text", "text": json.dumps(result.data, indent=2)}]
                else:
                    # Return error
                    content = [{"type": "text", "text": f"Error: {result.error}"}]
                
                return {"content": content}
                    
            except Exception as e:
                error_msg = f"Failed to invoke tool {name}: {str(e)}"
                self.log_error(error_msg)
                self._metrics["errors"] += 1
                return {
                    "content": [
                        {"type": "text", "text": f"Error: {error_msg}"}
                    ]
                }
        
        self._handlers["tools/call"] = handle_tools_call
        
        # Ping handler
        async def handle_ping(params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle ping request."""
            return {}
        
        self._handlers["ping"] = handle_ping
    
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
            self.log_info("Initializing Simple MCP server components")
            
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
            
            self.log_info("Simple MCP server initialization complete")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to initialize Simple MCP server: {e}")
            return False
    
    async def _do_start(self) -> bool:
        """
        Start the MCP server.
        
        Returns:
            True if startup successful
        """
        try:
            self.log_info("Starting Simple MCP server")
            
            # Clear shutdown event
            self._shutdown_event.clear()
            
            # Start the run task
            self._run_task = asyncio.create_task(self.run())
            
            self.log_info("Simple MCP server started successfully")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to start Simple MCP server: {e}")
            return False
    
    async def _do_shutdown(self) -> None:
        """
        Shutdown the MCP server gracefully.
        """
        self.log_info("Shutting down Simple MCP server")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel run task if active
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
        
        # Clean up resources
        if self._tool_registry:
            self.log_info("Cleaning up tool registry")
            # Tool registry cleanup if needed
        
        self.log_info("Simple MCP server shutdown complete")
    
    async def stop(self) -> None:
        """
        Stop the MCP service gracefully.
        
        This implements the IMCPLifecycle interface method.
        """
        await self.shutdown()
    
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
            
            # Check for handler
            if method in self._handlers:
                handler = self._handlers[method]
                result = await handler(params)
                
                # Build response
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            else:
                # Unknown method
                self.log_warning(f"Unknown method: {method}")
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return response
            
        except Exception as e:
            self.log_error(f"Error handling request: {e}")
            self._metrics["errors"] += 1
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def run(self) -> None:
        """
        Run the MCP server main loop.
        
        This method handles incoming requests using the communication handler.
        
        WHY: We use a simple request/response loop that works with any
        communication handler (stdio, websocket, etc).
        """
        try:
            self.log_info("Starting Simple MCP server main loop")
            
            # If we have a communication handler, use it
            if self._communication:
                while not self._shutdown_event.is_set():
                    try:
                        # Receive message
                        message = await self._communication.receive_message()
                        if message:
                            # Handle request
                            response = await self.handle_request(message)
                            # Send response
                            await self._communication.send_message(response)
                        else:
                            # No message, wait a bit
                            await asyncio.sleep(0.1)
                    except Exception as e:
                        self.log_error(f"Error in message loop: {e}")
                        self._metrics["errors"] += 1
            else:
                # No communication handler, just wait for shutdown
                self.log_warning("No communication handler set, waiting for shutdown")
                await self._shutdown_event.wait()
            
            self.log_info("Simple MCP server main loop ended")
            
        except Exception as e:
            self.log_error(f"Error in Simple MCP server main loop: {e}")
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