"""
Simple Unit Tests for MCP Tool Registry
========================================

Focused unit tests that work with the actual ToolRegistry implementation.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from claude_mpm.services.mcp_gateway.core.interfaces import (
    IMCPToolAdapter,
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry


def create_mock_tool(name: str, description: str = "Test tool"):
    """Helper to create a mock tool adapter."""
    mock_tool = Mock(spec=IMCPToolAdapter)
    mock_definition = MCPToolDefinition(
        name=name,
        description=description,
        input_schema={"type": "object", "properties": {}},
    )
    mock_tool.get_definition.return_value = mock_definition
    mock_tool.initialize = AsyncMock(return_value=True)
    mock_tool.shutdown = AsyncMock()
    return mock_tool


class TestToolRegistryBasics:
    """Test basic tool registry functionality."""

    def test_registry_creation():
        """Test registry can be created."""
        registry = ToolRegistry()
        assert registry is not None

    @pytest.mark.asyncio
    async def test_registry_initialization():
        """Test registry initialization."""
        registry = ToolRegistry()
        result = await registry.initialize()

        assert result is True
        # Should start with no tools
        tools = registry.list_tools()
        assert len(tools) == 0

    @pytest.mark.asyncio
    async def test_tool_registration():
        """Test basic tool registration."""
        registry = ToolRegistry()
        await registry.initialize()

        # Create and register a mock tool
        mock_tool = create_mock_tool("test_tool")
        result = registry.register_tool(mock_tool)

        assert result is True

        # Check that tool was registered
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "test_tool"

        # Check that we can get the tool
        retrieved_tool = registry.get_tool("test_tool")
        assert retrieved_tool is mock_tool

    @pytest.mark.asyncio
    async def test_tool_invocation():
        """Test tool invocation through registry."""
        registry = ToolRegistry()
        await registry.initialize()

        # Create mock tool that returns success
        mock_tool = create_mock_tool("test_tool")
        mock_tool.invoke = AsyncMock(
            return_value=MCPToolResult(
                success=True, data="test result", execution_time=0.1
            )
        )

        registry.register_tool(mock_tool)

        # Invoke the tool
        invocation = MCPToolInvocation(
            tool_name="test_tool", parameters={"param": "value"}
        )
        result = await registry.invoke_tool(invocation)

        assert result.success is True
        assert result.data == "test result"
        mock_tool.invoke.assert_called_once_with(invocation)

    @pytest.mark.asyncio
    async def test_nonexistent_tool_invocation():
        """Test invoking non-existent tool."""
        registry = ToolRegistry()
        await registry.initialize()

        invocation = MCPToolInvocation(tool_name="nonexistent_tool", parameters={})
        result = await registry.invoke_tool(invocation)

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_multiple_tools():
        """Test registering multiple tools."""
        registry = ToolRegistry()
        await registry.initialize()

        # Register multiple tools
        tool_names = ["tool1", "tool2", "tool3"]
        for name in tool_names:
            mock_tool = create_mock_tool(name)
            result = registry.register_tool(mock_tool)
            assert result is True

        # Check all tools are listed
        tools = registry.list_tools()
        assert len(tools) == 3

        registered_names = [tool.name for tool in tools]
        for name in tool_names:
            assert name in registered_names

    @pytest.mark.asyncio
    async def test_tool_search():
        """Test tool search functionality."""
        registry = ToolRegistry()
        await registry.initialize()

        # Register tools with different names
        tools_data = [
            ("echo_tool", "Echo messages"),
            ("calculator", "Mathematical calculations"),
            ("system_info", "System information"),
        ]

        for name, desc in tools_data:
            mock_tool = create_mock_tool(name, desc)
            registry.register_tool(mock_tool)

        # Test search functionality if available
        if hasattr(registry, "search_tools"):
            results = registry.search_tools("echo")
            assert len(results) >= 1
            assert any(tool.name == "echo_tool" for tool in results)

    @pytest.mark.asyncio
    async def test_registry_shutdown():
        """Test registry shutdown."""
        registry = ToolRegistry()
        await registry.initialize()

        # Register a tool
        mock_tool = create_mock_tool("test_tool")
        registry.register_tool(mock_tool)

        # Shutdown registry
        await registry.shutdown()

        # Tool should have been shut down
        mock_tool.shutdown.assert_called_once()


class TestToolRegistryErrorHandling:
    """Test error handling in tool registry."""

    @pytest.mark.asyncio
    async def test_tool_invocation_exception():
        """Test tool invocation with exception."""
        registry = ToolRegistry()
        await registry.initialize()

        # Create mock tool that throws exception
        mock_tool = create_mock_tool("failing_tool")
        mock_tool.invoke = AsyncMock(side_effect=Exception("Tool error"))

        registry.register_tool(mock_tool)

        # Invoke the tool
        invocation = MCPToolInvocation(tool_name="failing_tool", parameters={})
        result = await registry.invoke_tool(invocation)

        assert result.success is False
        assert "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_duplicate_tool_registration():
        """Test registering duplicate tool."""
        registry = ToolRegistry()
        await registry.initialize()

        # Register first tool
        mock_tool1 = create_mock_tool("duplicate_tool")
        result1 = registry.register_tool(mock_tool1)
        assert result1 is True

        # Try to register another tool with same name
        mock_tool2 = create_mock_tool("duplicate_tool")
        result2 = registry.register_tool(mock_tool2)

        # Should either fail or replace (depending on implementation)
        # Both behaviors are acceptable
        assert isinstance(result2, bool)

        # Should still have only one tool with that name
        tools = registry.list_tools()
        duplicate_tools = [t for t in tools if t.name == "duplicate_tool"]
        assert len(duplicate_tools) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])