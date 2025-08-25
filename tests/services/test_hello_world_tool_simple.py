"""
Simple Unit Tests for Hello World MCP Tool
===========================================

Basic test suite for the Hello World tool implementation.
Focuses on core functionality testing.

Part of ISS-0036: Hello World Tool - Testing and Validation Tool
"""

import asyncio
import sys
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, "/Users/masa/Projects/claude-mpm/src")

from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from claude_mpm.services.mcp_gateway.tools.hello_world import HelloWorldTool


@pytest.mark.asyncio
async def test_tool_initialization():
    """Test that tool initializes correctly."""
    tool = HelloWorldTool()
    assert not tool._initialized

    result = await tool.initialize()
    assert result is True
    assert tool._initialized
    assert tool.version == "1.0.0"


@pytest.mark.asyncio
async def test_simple_greeting():
    """Test simple greeting mode."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "simple"}

    result = await tool.invoke(invocation)
    assert result.success is True
    assert result.data["greeting"] == "Hello World!"
    assert result.data["mode"] == "simple"


@pytest.mark.asyncio
async def test_personalized_greeting():
    """Test personalized greeting mode."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "personalized", "name": "Alice"}

    result = await tool.invoke(invocation)
    assert result.success is True
    assert "Alice" in result.data["greeting"]
    assert "Welcome to the MCP Gateway" in result.data["greeting"]


@pytest.mark.asyncio
async def test_multi_language_greeting():
    """Test multi-language greeting mode."""
    tool = HelloWorldTool()
    await tool.initialize()

    # Test Spanish
    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "multi_language", "language": "spanish"}

    result = await tool.invoke(invocation)
    assert result.success is True
    assert "Hola" in result.data["greeting"]

    # Test Japanese
    invocation.parameters = {"mode": "multi_language", "language": "japanese"}
    result = await tool.invoke(invocation)
    assert result.success is True
    assert "こんにちは" in result.data["greeting"]


@pytest.mark.asyncio
async def test_uppercase_transformation():
    """Test uppercase transformation."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "simple", "uppercase": True}

    result = await tool.invoke(invocation)
    assert result.success is True
    assert result.data["greeting"] == "HELLO WORLD!"


@pytest.mark.asyncio
async def test_repeat_greeting():
    """Test greeting repetition."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "simple", "repeat": 3}

    result = await tool.invoke(invocation)
    assert result.success is True
    assert result.data["greeting"] == "Hello World! Hello World! Hello World!"


@pytest.mark.asyncio
async def test_error_handling_missing_name():
    """Test error handling for missing name in personalized mode."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "personalized"}

    result = await tool.invoke(invocation)
    assert result.success is False
    assert "validation failed" in result.error.lower()


@pytest.mark.asyncio
async def test_error_handling_invalid_mode():
    """Test error handling for invalid mode."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "invalid_mode"}

    result = await tool.invoke(invocation)
    assert result.success is False
    assert "validation failed" in result.error.lower()


@pytest.mark.asyncio
async def test_metadata_inclusion():
    """Test metadata inclusion in response."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "simple", "include_metadata": True}

    result = await tool.invoke(invocation)
    assert result.success is True
    assert "metadata" in result.data
    assert result.data["metadata"]["tool_version"] == "1.0.0"
    assert "execution_environment" in result.data["metadata"]


@pytest.mark.asyncio
async def test_async_greeting():
    """Test async greeting with delay."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "async_test", "delay_ms": 100}

    import time

    start = time.time()
    result = await tool.invoke(invocation)
    duration = time.time() - start

    assert result.success is True
    assert "100ms" in result.data["greeting"]
    assert duration >= 0.1  # Should take at least 100ms


@pytest.mark.asyncio
async def test_system_info_greeting():
    """Test system info greeting mode."""
    tool = HelloWorldTool()
    await tool.initialize()

    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "system_info"}

    result = await tool.invoke(invocation)
    assert result.success is True
    assert "Python" in result.data["greeting"]
    assert "MCP Gateway" in result.data["greeting"]


@pytest.mark.asyncio
async def test_analytics_tracking():
    """Test that analytics are tracked correctly."""
    tool = HelloWorldTool()
    await tool.initialize()

    # Generate some greetings
    for _ in range(3):
        invocation = Mock(spec=MCPToolInvocation)
        invocation.parameters = {"mode": "simple"}
        await tool.invoke(invocation)

    analytics = tool.get_analytics()
    assert analytics["total_greetings"] == 3
    assert analytics["modes_used"]["simple"] == 3
    assert analytics["average_execution_time"] > 0


@pytest.mark.asyncio
async def test_tool_shutdown():
    """Test tool shutdown and cleanup."""
    tool = HelloWorldTool()
    await tool.initialize()

    # Generate a greeting
    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "simple"}
    await tool.invoke(invocation)

    assert len(tool.greeting_history) > 0
    assert tool._initialized is True

    # Shutdown
    await tool.shutdown()

    assert len(tool.greeting_history) == 0
    assert tool._initialized is False


@pytest.mark.asyncio
async def test_error_simulation():
    """Test error simulation modes."""
    tool = HelloWorldTool()
    await tool.initialize()

    # Test validation error
    invocation = Mock(spec=MCPToolInvocation)
    invocation.parameters = {"mode": "error_test", "error_type": "validation"}
    result = await tool.invoke(invocation)
    assert result.success is False
    assert "validation error" in result.error.lower()

    # Test runtime error
    invocation.parameters = {"mode": "error_test", "error_type": "runtime"}
    result = await tool.invoke(invocation)
    assert result.success is False
    assert "runtime error" in result.error.lower()


@pytest.mark.asyncio
async def test_concurrent_invocations():
    """Test that tool handles concurrent invocations correctly."""
    tool = HelloWorldTool()
    await tool.initialize()

    # Create multiple invocations
    invocations = []
    for i in range(5):
        inv = Mock(spec=MCPToolInvocation)
        inv.parameters = {"mode": "simple", "repeat": i + 1}
        invocations.append(inv)

    # Run concurrently
    results = await asyncio.gather(*[tool.invoke(inv) for inv in invocations])

    # All should succeed
    assert all(r.success for r in results)
    assert len(tool.greeting_history) == 5


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
