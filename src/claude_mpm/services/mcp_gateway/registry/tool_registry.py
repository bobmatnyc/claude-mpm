"""
MCP Tool Registry Implementation
=================================

Comprehensive tool registry system for managing MCP tools.
Provides registration, discovery, and invocation capabilities.

Part of ISS-0035: MCP Server Implementation - Core Server and Tool Registry
"""

import asyncio
import re
import traceback
from datetime import datetime
from threading import RLock
from typing import Any, Dict, List, Optional, Set

from claude_mpm.services.mcp_gateway.core.base import BaseMCPService
from claude_mpm.services.mcp_gateway.core.interfaces import (
    IMCPToolAdapter,
    IMCPToolRegistry,
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)


class ToolRegistry(BaseMCPService, IMCPToolRegistry):
    """
    Thread-safe tool registry implementation.

    WHY: We need a centralized registry to manage all MCP tools, ensuring
    thread safety for concurrent access, efficient tool discovery, and
    proper lifecycle management.

    DESIGN DECISIONS:
    - Use RLock for thread safety to allow recursive locking
    - Maintain both adapters and definitions for fast access
    - Implement caching for frequently used tools
    - Track metrics for monitoring and optimization
    - Support pattern-based search for tool discovery
    """

    def __init__(self):
        """Initialize the tool registry."""
        super().__init__("ToolRegistry")

        # Thread safety
        self._lock = RLock()

        # Tool storage
        self._adapters: Dict[str, IMCPToolAdapter] = {}
        self._definitions: Dict[str, MCPToolDefinition] = {}

        # Tool categories for organization
        self._categories: Dict[str, Set[str]] = {
            "system": set(),
            "user": set(),
            "builtin": set(),
            "external": set(),
        }

        # Metrics
        self._metrics = {
            "total_tools": 0,
            "invocations": {},  # Per-tool invocation counts
            "errors": {},  # Per-tool error counts
            "last_invocation": {},  # Per-tool last invocation time
            "registration_time": {},  # Per-tool registration time
        }

        # Cache for frequently used tools (LRU-style)
        self._cache_size = 10
        self._tool_cache: List[str] = []

    async def _do_initialize(self) -> bool:
        """
        Initialize the tool registry.

        Returns:
            True if initialization successful
        """
        try:
            self.log_info("Initializing tool registry")

            # Clear any existing data
            with self._lock:
                self._adapters.clear()
                self._definitions.clear()
                for category in self._categories.values():
                    category.clear()
                self._tool_cache.clear()

            self.log_info("Tool registry initialized")
            return True

        except Exception as e:
            self.log_error(f"Failed to initialize tool registry: {e}")
            return False

    async def _do_shutdown(self) -> None:
        """Shutdown the tool registry and clean up resources."""
        self.log_info("Shutting down tool registry")

        # Shutdown all tool adapters
        with self._lock:
            for tool_name, adapter in self._adapters.items():
                try:
                    self.log_info(f"Shutting down tool adapter: {tool_name}")
                    await adapter.shutdown()
                except Exception as e:
                    self.log_error(f"Error shutting down tool {tool_name}: {e}")

            # Clear all data
            self._adapters.clear()
            self._definitions.clear()
            for category in self._categories.values():
                category.clear()
            self._tool_cache.clear()

        self.log_info("Tool registry shutdown complete")

    def register_tool(self, adapter: IMCPToolAdapter, category: str = "user") -> bool:
        """
        Register a tool adapter.

        Args:
            adapter: Tool adapter to register
            category: Tool category (system, user, builtin, external)

        Returns:
            True if registration successful

        WHY: We validate the adapter and its definition before registration
        to ensure only valid tools are added to the registry.
        """
        try:
            # Get tool definition
            definition = adapter.get_definition()
            tool_name = definition.name

            self.log_info(f"Registering tool: {tool_name} (category: {category})")

            with self._lock:
                # Check if tool already registered
                if tool_name in self._adapters:
                    self.log_warning(f"Tool already registered: {tool_name}")
                    return False

                # Validate category
                if category not in self._categories:
                    self.log_warning(f"Invalid category: {category}, using 'user'")
                    category = "user"

                # Register the tool
                self._adapters[tool_name] = adapter
                self._definitions[tool_name] = definition
                self._categories[category].add(tool_name)

                # Update metrics
                self._metrics["total_tools"] = len(self._adapters)
                self._metrics["registration_time"][
                    tool_name
                ] = datetime.now().isoformat()
                self._metrics["invocations"][tool_name] = 0
                self._metrics["errors"][tool_name] = 0

            self.log_info(f"Tool registered successfully: {tool_name}")
            self.log_mcp_event(
                "tool_registered", {"tool": tool_name, "category": category}
            )

            return True

        except Exception as e:
            self.log_error(f"Failed to register tool: {e}")
            self.log_error(f"Traceback: {traceback.format_exc()}")
            return False

    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool by name.

        Args:
            tool_name: Name of tool to unregister

        Returns:
            True if unregistration successful
        """
        try:
            self.log_info(f"Unregistering tool: {tool_name}")

            with self._lock:
                # Check if tool exists
                if tool_name not in self._adapters:
                    self.log_warning(f"Tool not found: {tool_name}")
                    return False

                # Get the adapter for shutdown
                adapter = self._adapters[tool_name]

                # Remove from all storage
                del self._adapters[tool_name]
                del self._definitions[tool_name]

                # Remove from categories
                for category_tools in self._categories.values():
                    category_tools.discard(tool_name)

                # Remove from cache
                if tool_name in self._tool_cache:
                    self._tool_cache.remove(tool_name)

                # Update metrics
                self._metrics["total_tools"] = len(self._adapters)

            # Shutdown adapter (outside lock to avoid deadlock)
            try:
                asyncio.create_task(adapter.shutdown())
            except Exception as e:
                self.log_warning(f"Error shutting down tool adapter {tool_name}: {e}")

            self.log_info(f"Tool unregistered successfully: {tool_name}")
            self.log_mcp_event("tool_unregistered", {"tool": tool_name})

            return True

        except Exception as e:
            self.log_error(f"Failed to unregister tool {tool_name}: {e}")
            return False

    def get_tool(self, tool_name: str) -> Optional[IMCPToolAdapter]:
        """
        Get a tool adapter by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool adapter if found, None otherwise
        """
        with self._lock:
            adapter = self._adapters.get(tool_name)

            # Update cache if tool found
            if adapter and tool_name not in self._tool_cache:
                self._update_cache(tool_name)

            return adapter

    def list_tools(self) -> List[MCPToolDefinition]:
        """
        List all registered tools.

        Returns:
            List of tool definitions
        """
        with self._lock:
            return list(self._definitions.values())

    async def invoke_tool(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Invoke a tool through the registry.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result

        WHY: We handle invocation through the registry to provide centralized
        error handling, metrics tracking, and validation.
        """
        tool_name = invocation.tool_name
        start_time = datetime.now()

        try:
            self.log_info(f"Invoking tool: {tool_name}")

            # Get the adapter
            adapter = self.get_tool(tool_name)
            if not adapter:
                error_msg = f"Tool not found: {tool_name}"
                self.log_error(error_msg)
                return MCPToolResult(success=False, error=error_msg)

            # Validate parameters
            if not adapter.validate_parameters(invocation.parameters):
                error_msg = f"Invalid parameters for tool {tool_name}"
                self.log_error(error_msg)

                with self._lock:
                    self._metrics["errors"][tool_name] = (
                        self._metrics["errors"].get(tool_name, 0) + 1
                    )

                return MCPToolResult(success=False, error=error_msg)

            # Invoke the tool
            result = await adapter.invoke(invocation)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time

            # Update metrics
            with self._lock:
                self._metrics["invocations"][tool_name] = (
                    self._metrics["invocations"].get(tool_name, 0) + 1
                )
                self._metrics["last_invocation"][tool_name] = datetime.now().isoformat()

                if not result.success:
                    self._metrics["errors"][tool_name] = (
                        self._metrics["errors"].get(tool_name, 0) + 1
                    )

            # Log the invocation
            self.log_tool_invocation(tool_name, result.success, execution_time)

            return result

        except Exception as e:
            error_msg = f"Exception invoking tool {tool_name}: {e!s}"
            self.log_error(error_msg)
            self.log_error(f"Traceback: {traceback.format_exc()}")

            # Update error metrics
            with self._lock:
                self._metrics["errors"][tool_name] = (
                    self._metrics["errors"].get(tool_name, 0) + 1
                )

            execution_time = (datetime.now() - start_time).total_seconds()

            return MCPToolResult(
                success=False, error=error_msg, execution_time=execution_time
            )

    def search_tools(self, query: str) -> List[MCPToolDefinition]:
        """
        Search for tools by query.

        Supports:
        - Exact name matching
        - Partial name matching
        - Description keyword matching
        - Regex patterns

        Args:
            query: Search query

        Returns:
            List of matching tool definitions
        """
        try:
            query_lower = query.lower()
            matching_tools = []

            with self._lock:
                for name, definition in self._definitions.items():
                    # Exact match
                    if name.lower() == query_lower:
                        matching_tools.append(definition)
                        continue

                    # Partial name match
                    if query_lower in name.lower():
                        matching_tools.append(definition)
                        continue

                    # Description match
                    if query_lower in definition.description.lower():
                        matching_tools.append(definition)
                        continue

                    # Try regex match
                    try:
                        if re.search(query, name, re.IGNORECASE):
                            matching_tools.append(definition)
                            continue
                    except re.error:
                        # Not a valid regex, skip
                        pass

            self.log_info(
                f"Search query '{query}' returned {len(matching_tools)} tools"
            )
            return matching_tools

        except Exception as e:
            self.log_error(f"Error searching tools: {e}")
            return []

    def get_tools_by_category(self, category: str) -> List[MCPToolDefinition]:
        """
        Get all tools in a specific category.

        Args:
            category: Category name (system, user, builtin, external)

        Returns:
            List of tool definitions in the category
        """
        with self._lock:
            if category not in self._categories:
                self.log_warning(f"Invalid category: {category}")
                return []

            tool_names = self._categories[category]
            return [
                self._definitions[name]
                for name in tool_names
                if name in self._definitions
            ]

    def _update_cache(self, tool_name: str) -> None:
        """
        Update the tool cache (LRU-style).

        Args:
            tool_name: Name of tool to add to cache
        """
        # Remove if already in cache
        if tool_name in self._tool_cache:
            self._tool_cache.remove(tool_name)

        # Add to front
        self._tool_cache.insert(0, tool_name)

        # Trim cache if needed
        if len(self._tool_cache) > self._cache_size:
            self._tool_cache = self._tool_cache[: self._cache_size]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get registry metrics.

        Returns:
            Metrics dictionary
        """
        with self._lock:
            return {
                **self._metrics,
                "categories": {
                    category: len(tools) for category, tools in self._categories.items()
                },
                "cached_tools": list(self._tool_cache),
            }

    def clear_metrics(self) -> None:
        """Clear all metrics except registration data."""
        with self._lock:
            for tool_name in self._metrics["invocations"]:
                self._metrics["invocations"][tool_name] = 0
                self._metrics["errors"][tool_name] = 0
            self._metrics["last_invocation"].clear()

    async def initialize_all_tools(self) -> Dict[str, bool]:
        """
        Initialize all registered tool adapters.

        Returns:
            Dictionary mapping tool names to initialization success
        """
        results = {}

        with self._lock:
            adapters_copy = dict(self._adapters)

        for tool_name, adapter in adapters_copy.items():
            try:
                self.log_info(f"Initializing tool: {tool_name}")
                success = await adapter.initialize()
                results[tool_name] = success

                if success:
                    self.log_info(f"Tool initialized successfully: {tool_name}")
                else:
                    self.log_warning(f"Tool initialization failed: {tool_name}")

            except Exception as e:
                self.log_error(f"Exception initializing tool {tool_name}: {e}")
                results[tool_name] = False

        return results
