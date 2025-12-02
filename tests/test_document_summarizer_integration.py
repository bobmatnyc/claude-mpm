"""
Integration tests for Document Summarizer Tool with MCP Gateway
================================================================

Tests the document summarizer tool integration with the MCP Gateway.
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry
from claude_mpm.services.mcp_gateway.tools.document_summarizer import (
    DocumentSummarizerTool,
)


@pytest.mark.asyncio
async def test_document_summarizer_registry_integration():
    """Test that Document Summarizer can be registered and invoked through the registry."""
    # Create registry
    registry = ToolRegistry()
    await registry.initialize()

    # Create and register the tool
    tool = DocumentSummarizerTool()
    await tool.initialize()

    # Register the tool
    success = registry.register_tool(tool, category="builtin")
    assert success, "Failed to register DocumentSummarizerTool"

    # Verify tool is in registry
    tools = registry.list_tools()
    tool_names = [t.name for t in tools]
    assert "document_summarizer" in tool_names

    # Create a test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test document for integration testing. " * 50)
        test_file = f.name

    try:
        # Invoke through registry
        invocation = MCPToolInvocation(
            tool_name="document_summarizer",
            parameters={"file_path": test_file, "mode": "brief", "max_percentage": 30},
        )

        result = await registry.invoke_tool(invocation)

        # Verify result
        assert result.success, f"Tool invocation failed: {result.error}"
        assert result.data is not None
        assert "summary" in result.data
        assert result.data["reduction_percentage"] > 0

        # Check metrics
        metrics = registry.get_metrics()
        assert metrics["invocations"]["document_summarizer"] == 1
        assert metrics["errors"]["document_summarizer"] == 0

    finally:
        # Cleanup
        Path(test_file).unlink(missing_ok=True)
        await registry.shutdown()


@pytest.mark.asyncio
async def test_document_summarizer_search():
    """Test that Document Summarizer can be found through search."""
    # Create registry
    registry = ToolRegistry()
    await registry.initialize()

    # Register the tool
    tool = DocumentSummarizerTool()
    await tool.initialize()
    registry.register_tool(tool, category="builtin")

    # Search for the tool
    results = registry.search_tools("document")
    assert len(results) > 0
    assert any(t.name == "document_summarizer" for t in results)

    results = registry.search_tools("summarizer")
    assert len(results) > 0
    assert any(t.name == "document_summarizer" for t in results)

    results = registry.search_tools("memory")
    assert len(results) > 0
    assert any(t.name == "document_summarizer" for t in results)

    # Cleanup
    await registry.shutdown()


@pytest.mark.asyncio
async def test_document_summarizer_category():
    """Test that Document Summarizer is properly categorized."""
    # Create registry
    registry = ToolRegistry()
    await registry.initialize()

    # Register the tool in builtin category
    tool = DocumentSummarizerTool()
    await tool.initialize()
    registry.register_tool(tool, category="builtin")

    # Get tools by category
    builtin_tools = registry.get_tools_by_category("builtin")
    tool_names = [t.name for t in builtin_tools]
    assert "document_summarizer" in tool_names

    # Cleanup
    await registry.shutdown()


@pytest.mark.asyncio
async def test_document_summarizer_performance():
    """Test Document Summarizer performance with large file."""
    # Create registry
    registry = ToolRegistry()
    await registry.initialize()

    # Register the tool
    tool = DocumentSummarizerTool()
    await tool.initialize()
    registry.register_tool(tool, category="builtin")

    # Create a large test file (1MB)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        large_content = "Large document content. " * 50000  # ~1MB
        f.write(large_content)
        test_file = f.name

    try:
        # First invocation (no cache)
        invocation1 = MCPToolInvocation(
            tool_name="document_summarizer",
            parameters={"file_path": test_file, "mode": "brief", "use_cache": True},
        )

        result1 = await registry.invoke_tool(invocation1)
        assert result1.success
        assert not result1.data["cache_hit"]
        first_time = result1.execution_time

        # Second invocation (with cache)
        invocation2 = MCPToolInvocation(
            tool_name="document_summarizer",
            parameters={"file_path": test_file, "mode": "brief", "use_cache": True},
        )

        result2 = await registry.invoke_tool(invocation2)
        assert result2.success
        assert result2.data["cache_hit"]
        second_time = result2.execution_time

        # Cache should make it significantly faster
        assert second_time < first_time * 0.5  # At least 50% faster

        # Verify reduction percentage meets requirement (60%+)
        assert result1.data["reduction_percentage"] >= 60

    finally:
        # Cleanup
        Path(test_file).unlink(missing_ok=True)
        await registry.shutdown()


@pytest.mark.asyncio
async def test_document_summarizer_error_handling():
    """Test Document Summarizer error handling through registry."""
    # Create registry
    registry = ToolRegistry()
    await registry.initialize()

    # Register the tool
    tool = DocumentSummarizerTool()
    await tool.initialize()
    registry.register_tool(tool, category="builtin")

    # Test with invalid file
    invocation = MCPToolInvocation(
        tool_name="document_summarizer",
        parameters={"file_path": "/nonexistent/file.txt"},
    )

    result = await registry.invoke_tool(invocation)
    assert not result.success
    assert result.error is not None
    assert "not found" in result.error.lower()

    # Check error metrics
    metrics = registry.get_metrics()
    assert metrics["errors"]["document_summarizer"] == 1

    # Cleanup
    await registry.shutdown()
