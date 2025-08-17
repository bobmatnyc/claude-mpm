"""
Unit Tests for MCP Server
==========================

Comprehensive unit tests for the MCP server implementation.
Tests individual components in isolation with proper mocking.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from claude_mpm.services.mcp_gateway.core.interfaces import (
    IMCPCommunication,
    IMCPGateway,
    IMCPToolRegistry,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway


class TestMCPGatewayInitialization:
    """Test MCP gateway initialization."""

    def test_gateway_creation(self):
        """Test gateway can be created with default parameters."""
        gateway = MCPGateway()
        assert gateway.gateway_name == "claude-mpm-mcp"
        assert gateway.version == "1.0.0"
        assert gateway._tool_registry is None
        assert gateway._communication is None

    def test_gateway_creation_with_params(self):
        """Test gateway creation with custom parameters."""
        gateway = MCPGateway(gateway_name="test-gateway", version="2.0.0")
        assert gateway.gateway_name == "test-gateway"
        assert gateway.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initialization process."""
        server = MCPServer()

        # Mock the MCP server from official package
        with patch.object(server, "mcp_server") as mock_mcp_server:
            mock_mcp_server.get_capabilities.return_value = {"tools": {}}

            result = await server.initialize()
            assert result is True
            assert server.state.name == "RUNNING"

    @pytest.mark.asyncio
    async def test_server_initialization_failure(self):
        """Test server initialization failure handling."""
        server = MCPServer()

        # Mock initialization failure
        with patch.object(server, "mcp_server") as mock_mcp_server:
            mock_mcp_server.get_capabilities.side_effect = Exception("Init failed")

            result = await server.initialize()
            assert result is False
            assert server.state.name == "ERROR"


class TestMCPServerDependencyInjection:
    """Test dependency injection for MCP server."""

    def test_set_tool_registry(self):
        """Test setting tool registry dependency."""
        server = MCPServer()
        mock_registry = Mock(spec=IMCPToolRegistry)

        server.set_tool_registry(mock_registry)
        assert server._tool_registry is mock_registry

    def test_set_communication(self):
        """Test setting communication handler dependency."""
        server = MCPServer()
        mock_comm = Mock(spec=IMCPCommunication)

        server.set_communication(mock_comm)
        assert server._communication is mock_comm

    def test_get_capabilities(self):
        """Test getting server capabilities."""
        server = MCPServer()
        capabilities = server.get_capabilities()

        assert "tools" in capabilities
        assert "experimental" in capabilities


class TestMCPServerRequestHandling:
    """Test MCP server request handling."""

    @pytest.mark.asyncio
    async def test_handle_request_success(self):
        """Test successful request handling."""
        server = MCPServer()
        await server.initialize()

        # Mock request
        request = {"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}

        # Mock tool registry
        mock_registry = Mock(spec=IMCPToolRegistry)
        mock_registry.list_tools.return_value = []
        server.set_tool_registry(mock_registry)

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert "result" in response or "error" in response

    @pytest.mark.asyncio
    async def test_handle_request_unknown_method(self):
        """Test handling unknown method."""
        server = MCPServer()
        await server.initialize()

        request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "unknown/method",
            "params": {},
        }

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert "error" in response
        assert response["error"]["code"] == -32601  # Method not found

    @pytest.mark.asyncio
    async def test_handle_request_exception(self):
        """Test request handling with exception."""
        server = MCPServer()
        await server.initialize()

        request = {"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}

        # Mock tool registry that throws exception
        mock_registry = Mock(spec=IMCPToolRegistry)
        mock_registry.list_tools.side_effect = Exception("Registry error")
        server.set_tool_registry(mock_registry)

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert "error" in response
        assert response["error"]["code"] == -32603  # Internal error


class TestMCPServerMetrics:
    """Test MCP server metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_metrics_initialization(self):
        """Test metrics are properly initialized."""
        server = MCPServer()
        await server.initialize()

        metrics = server.get_metrics()
        assert metrics["requests_handled"] == 0
        assert metrics["tool_invocations"] == 0
        assert metrics["errors"] == 0
        assert "uptime" in metrics

    @pytest.mark.asyncio
    async def test_metrics_update_on_request(self):
        """Test metrics update when handling requests."""
        server = MCPServer()
        await server.initialize()

        # Mock tool registry
        mock_registry = Mock(spec=IMCPToolRegistry)
        mock_registry.list_tools.return_value = []
        server.set_tool_registry(mock_registry)

        request = {"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}

        await server.handle_request(request)

        metrics = server.get_metrics()
        assert metrics["requests_handled"] == 1

    def test_health_status(self):
        """Test health status reporting."""
        server = MCPServer()
        health = server.get_health_status()

        assert "healthy" in health
        assert "state" in health
        assert "uptime" in health


class TestMCPServerLifecycle:
    """Test MCP server lifecycle management."""

    @pytest.mark.asyncio
    async def test_server_shutdown(self):
        """Test server shutdown process."""
        server = MCPServer()
        await server.initialize()

        # Mock dependencies
        mock_registry = Mock(spec=IMCPToolRegistry)
        mock_registry.shutdown = AsyncMock()
        server.set_tool_registry(mock_registry)

        await server.shutdown()

        assert server.state.name == "STOPPED"
        mock_registry.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_stop_alias(self):
        """Test server stop method (alias for shutdown)."""
        server = MCPServer()
        await server.initialize()

        await server.stop()
        assert server.state.name == "STOPPED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
