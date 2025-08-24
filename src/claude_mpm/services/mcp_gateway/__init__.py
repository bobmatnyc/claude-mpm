"""
MCP Gateway Service Module
==========================

This module provides the Model Context Protocol (MCP) gateway implementation for Claude MPM.
It enables integration with MCP-compatible tools and services through a standardized interface.

Part of ISS-0034: Infrastructure Setup - MCP Gateway Project Foundation

The MCP Gateway follows the claude-mpm service-oriented architecture with:
- Interface-based contracts for all components
- Dependency injection for service resolution
- Lazy loading for performance optimization
- Comprehensive error handling and logging

Structure:
- core/: Core interfaces and base classes for MCP services
- server/: MCP server implementation and lifecycle management
- tools/: Tool registry and tool adapter implementations
- config/: Configuration management for MCP Gateway
- registry/: Service discovery and registration
"""

# Version information
__version__ = "0.1.0"


# Lazy imports to prevent circular dependencies and improve startup performance
def __getattr__(name):
    """Lazy import mechanism for MCP Gateway components."""

    # Core interfaces and base classes
    if name == "IMCPGateway":
        from .core.interfaces import IMCPGateway

        return IMCPGateway
    if name == "IMCPToolRegistry":
        from .core.interfaces import IMCPToolRegistry

        return IMCPToolRegistry
    if name == "IMCPConfiguration":
        from .core.interfaces import IMCPConfiguration

        return IMCPConfiguration
    if name == "IMCPToolAdapter":
        from .core.interfaces import IMCPToolAdapter

        return IMCPToolAdapter
    if name == "BaseMCPService":
        from .core.base import BaseMCPService

        return BaseMCPService

    # Gateway implementations
    if name == "MCPGateway":
        from .server.mcp_gateway import MCPGateway

        return MCPGateway
    if name == "StdioHandler":
        from .server.stdio_handler import StdioHandler

        return StdioHandler
    if name == "AlternativeStdioHandler":
        from .server.stdio_handler import AlternativeStdioHandler

        return AlternativeStdioHandler

    # Tool registry and adapters
    if name == "ToolRegistry":
        from .registry.tool_registry import ToolRegistry

        return ToolRegistry
    if name == "BaseToolAdapter":
        from .tools.base_adapter import BaseToolAdapter

        return BaseToolAdapter
    if name == "EchoToolAdapter":
        from .tools.base_adapter import EchoToolAdapter

        return EchoToolAdapter
    if name == "CalculatorToolAdapter":
        from .tools.base_adapter import CalculatorToolAdapter

        return CalculatorToolAdapter
    if name == "SystemInfoToolAdapter":
        from .tools.base_adapter import SystemInfoToolAdapter

        return SystemInfoToolAdapter

    # Configuration management
    if name == "MCPConfiguration":
        from .config.configuration import MCPConfiguration

        return MCPConfiguration
    if name == "MCPConfigLoader":
        from .config.config_loader import MCPConfigLoader

        return MCPConfigLoader

    # Service registry
    if name == "MCPServiceRegistry":
        from .registry.service_registry import MCPServiceRegistry

        return MCPServiceRegistry

    # Exceptions
    if name == "MCPException":
        from .core.exceptions import MCPException

        return MCPException
    if name == "MCPConfigurationError":
        from .core.exceptions import MCPConfigurationError

        return MCPConfigurationError
    if name == "MCPToolNotFoundError":
        from .core.exceptions import MCPToolNotFoundError

        return MCPToolNotFoundError
    if name == "MCPServerError":
        from .core.exceptions import MCPServerError

        return MCPServerError

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Public API exports
__all__ = [
    "AlternativeStdioHandler",
    "BaseMCPService",
    "BaseToolAdapter",
    "CalculatorToolAdapter",
    "EchoToolAdapter",
    "IMCPConfiguration",
    # Core interfaces
    "IMCPGateway",
    "IMCPToolAdapter",
    "IMCPToolRegistry",
    "MCPConfigLoader",
    # Configuration
    "MCPConfiguration",
    "MCPConfigurationError",
    # Exceptions
    "MCPException",
    # Gateway implementations
    "MCPGateway",
    "MCPServerError",
    # Service registry
    "MCPServiceRegistry",
    "MCPToolNotFoundError",
    "StdioHandler",
    "SystemInfoToolAdapter",
    # Tool management
    "ToolRegistry",
]
