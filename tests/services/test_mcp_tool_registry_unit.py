"""
Unit Tests for MCP Tool Registry
=================================

Focused unit tests for the tool registry implementation.
Tests core functionality with the actual implementation.
"""

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


class TestToolRegistryBasics:
    """Test basic tool registry functionality."""

    def test_registry_creation():
        """Test registry can be created."""
        registry = ToolRegistry()
        # Check that registry has the expected attributes
        assert hasattr(registry, "_lock")
        assert hasattr(registry, "_tool_adapters")
        assert hasattr(registry, "_tool_definitions")

    @pytest.mark.asyncio
    async def test_registry_initialization():
        """Test registry initialization."""
        registry = ToolRegistry()
        result = await registry.initialize()

        assert result is True
        # Should start with no tools
        tools = registry.list_tools()
        assert len(tools) == 0


class TestToolRegistration:
    """Test tool registration functionality."""

    @pytest.mark.asyncio
    async def test_register_tool_success():
        """Test successful tool registration."""
        registry = ToolRegistry()
        await registry.initialize()

        # Create mock tool adapter
        mock_tool = Mock(spec=IMCPToolAdapter)
        mock_definition = MCPToolDefinition(
            name="test_tool",
            description="Test tool",
            input_schema={"type": "object", "properties": {}},
        )
        mock_tool.get_definition.return_value = mock_definition
        mock_tool.initialize = AsyncMock(return_value=True)

        result = registry.register_tool(mock_tool, category="test")

        assert result is True
        # Check that tool was registered
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        mock_tool.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_tool():
        """Test registering duplicate tool."""
        registry = ToolRegistry()
        await registry.initialize()

        # Create mock tool adapter
        mock_tool = Mock(spec=IMCPToolAdapter)
        mock_definition = MCPToolDefinition(
            name="test_tool", description="Test tool", parameters={}
        )
        mock_tool.get_definition.return_value = mock_definition
        mock_tool.initialize = AsyncMock(return_value=True)

        # Register first time
        result1 = registry.register_tool(mock_tool, category="test")
        assert result1 is True

        # Register second time (should fail)
        result2 = registry.register_tool(mock_tool, category="test")
        assert result2 is False
        assert registry._metrics["total_tools"] == 1

    @pytest.mark.asyncio
    async def test_register_tool_invalid_category():
        """Test registering tool with invalid category."""
        registry = ToolRegistry()
        await registry.initialize()

        mock_tool = Mock(spec=IMCPToolAdapter)
        mock_definition = MCPToolDefinition(
            name="test_tool", description="Test tool", parameters={}
        )
        mock_tool.get_definition.return_value = mock_definition
        mock_tool.initialize = AsyncMock(return_value=True)

        # Register with invalid category (should default to 'user')
        result = registry.register_tool(mock_tool, category="invalid")

        assert result is True
        assert registry._categories["user"] == 1

    @pytest.mark.asyncio
    async def test_deregister_tool():
        """Test tool deregistration."""
        registry = ToolRegistry()
        await registry.initialize()

        # Register a tool first
        mock_tool = Mock(spec=IMCPToolAdapter)
        mock_definition = MCPToolDefinition(
            name="test_tool", description="Test tool", parameters={}
        )
        mock_tool.get_definition.return_value = mock_definition
        mock_tool.initialize = AsyncMock(return_value=True)
        mock_tool.shutdown = AsyncMock()

        registry.register_tool(mock_tool, category="test")
        assert registry._metrics["total_tools"] == 1

        # Deregister the tool
        result = registry.deregister_tool("test_tool")

        assert result is True
        assert "test_tool" not in registry._tools
        assert registry._metrics["total_tools"] == 0
        mock_tool.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_deregister_nonexistent_tool():
        """Test deregistering non-existent tool."""
        registry = ToolRegistry()
        await registry.initialize()

        result = registry.deregister_tool("nonexistent_tool")
        assert result is False


class TestToolDiscovery:
    """Test tool discovery functionality."""

    @pytest.mark.asyncio
    async def test_list_tools():
        """Test listing all tools."""
        registry = ToolRegistry()
        await registry.initialize()

        # Register multiple tools
        for i in range(3):
            mock_tool = Mock(spec=IMCPToolAdapter)
            mock_definition = MCPToolDefinition(
                name=f"tool_{i}", description=f"Test tool {i}", parameters={}
            )
            mock_tool.get_definition.return_value = mock_definition
            mock_tool.initialize = AsyncMock(return_value=True)
            registry.register_tool(mock_tool, category="test")

        tools = registry.list_tools()
        assert len(tools) == 3
        assert all(isinstance(tool, MCPToolDefinition) for tool in tools)

    @pytest.mark.asyncio
    async def test_search_tools():
        """Test searching for tools."""
        registry = ToolRegistry()
        await registry.initialize()

        # Register tools with different names
        tool_names = ["echo_tool", "calculator", "system_info"]
        for name in tool_names:
            mock_tool = Mock(spec=IMCPToolAdapter)
            mock_definition = MCPToolDefinition(
                name=name, description=f"Description for {name}", parameters={}
            )
            mock_tool.get_definition.return_value = mock_definition
            mock_tool.initialize = AsyncMock(return_value=True)
            registry.register_tool(mock_tool, category="test")

        # Search for tools containing "echo"
        results = registry.search_tools("echo")
        assert len(results) == 1
        assert results[0].name == "echo_tool"

        # Search for tools containing "tool"
        results = registry.search_tools("tool")
        assert len(results) == 1
        assert results[0].name == "echo_tool"

    @pytest.mark.asyncio
    async def test_get_tool_by_name():
        """Test getting tool by name."""
        registry = ToolRegistry()
        await registry.initialize()

        # Register a tool
        mock_tool = Mock(spec=IMCPToolAdapter)
        mock_definition = MCPToolDefinition(
            name="test_tool", description="Test tool", parameters={}
        )
        mock_tool.get_definition.return_value = mock_definition
        mock_tool.initialize = AsyncMock(return_value=True)
        registry.register_tool(mock_tool, category="test")

        # Get tool by name
        tool = registry.get_tool("test_tool")
        assert tool is mock_tool

        # Get non-existent tool
        tool = registry.get_tool("nonexistent")
        assert tool is None


class TestToolInvocation:
    """Test tool invocation functionality."""

    @pytest.mark.asyncio
    async def test_invoke_tool_success():
        """Test successful tool invocation."""
        registry = ToolRegistry()
        await registry.initialize()

        # Create mock tool that returns success
        mock_tool = Mock(spec=IMCPToolAdapter)
        mock_definition = MCPToolDefinition(
            name="test_tool", description="Test tool", parameters={}
        )
        mock_tool.get_definition.return_value = mock_definition
        mock_tool.initialize = AsyncMock(return_value=True)
        mock_tool.invoke = AsyncMock(
            return_value=MCPToolResult(
                success=True, data="test result", execution_time=0.1
            )
        )

        registry.register_tool(mock_tool, category="test")

        # Invoke the tool
        invocation = MCPToolInvocation(
            tool_name="test_tool", parameters={"param": "value"}
        )
        result = await registry.invoke_tool(invocation)

        assert result.success is True
        assert result.data == "test result"
        assert registry._metrics["invocations"]["test_tool"] == 1
        mock_tool.invoke.assert_called_once_with(invocation)

    @pytest.mark.asyncio
    async def test_invoke_nonexistent_tool():
        """Test invoking non-existent tool."""
        registry = ToolRegistry()
        await registry.initialize()

        invocation = MCPToolInvocation(tool_name="nonexistent_tool", parameters={})
        result = await registry.invoke_tool(invocation)

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invoke_tool_exception():
        """Test tool invocation with exception."""
        registry = ToolRegistry()
        await registry.initialize()

        # Create mock tool that throws exception
        mock_tool = Mock(spec=IMCPToolAdapter)
        mock_definition = MCPToolDefinition(
            name="test_tool", description="Test tool", parameters={}
        )
        mock_tool.get_definition.return_value = mock_definition
        mock_tool.initialize = AsyncMock(return_value=True)
        mock_tool.invoke = AsyncMock(side_effect=Exception("Tool error"))

        registry.register_tool(mock_tool, category="test")

        # Invoke the tool
        invocation = MCPToolInvocation(tool_name="test_tool", parameters={})
        result = await registry.invoke_tool(invocation)

        assert result.success is False
        assert "Tool error" in result.error


class TestToolRegistryMetrics:
    """Test tool registry metrics."""

    @pytest.mark.asyncio
    async def test_get_metrics():
        """Test getting registry metrics."""
        registry = ToolRegistry()
        await registry.initialize()

        metrics = registry.get_metrics()

        assert "total_tools" in metrics
        assert "invocations" in metrics
        assert "categories" in metrics
        assert "errors" in metrics
        assert metrics["total_tools"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
