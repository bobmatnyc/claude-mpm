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
    """Lazy import mechanism for MCP Gateway components using dictionary-based mapping."""
    from importlib import import_module

    # Dictionary mapping: name -> (module_path, attribute_name)
    _LAZY_IMPORTS = {
        # Core interfaces and base classes
        "IMCPGateway": (
            "claude_mpm.services.mcp_gateway.core.interfaces",
            "IMCPGateway",
        ),
        "IMCPToolRegistry": (
            "claude_mpm.services.mcp_gateway.core.interfaces",
            "IMCPToolRegistry",
        ),
        "IMCPConfiguration": (
            "claude_mpm.services.mcp_gateway.core.interfaces",
            "IMCPConfiguration",
        ),
        "IMCPToolAdapter": (
            "claude_mpm.services.mcp_gateway.core.interfaces",
            "IMCPToolAdapter",
        ),
        "BaseMCPService": (
            "claude_mpm.services.mcp_gateway.core.base",
            "BaseMCPService",
        ),
        # Gateway implementations
        "MCPGateway": (
            "claude_mpm.services.mcp_gateway.server.mcp_gateway",
            "MCPGateway",
        ),
        "StdioHandler": (
            "claude_mpm.services.mcp_gateway.server.stdio_handler",
            "StdioHandler",
        ),
        "AlternativeStdioHandler": (
            "claude_mpm.services.mcp_gateway.server.stdio_handler",
            "AlternativeStdioHandler",
        ),
        # Tool registry and adapters
        "ToolRegistry": (
            "claude_mpm.services.mcp_gateway.registry.tool_registry",
            "ToolRegistry",
        ),
        "BaseToolAdapter": (
            "claude_mpm.services.mcp_gateway.tools.base_adapter",
            "BaseToolAdapter",
        ),
        "EchoToolAdapter": (
            "claude_mpm.services.mcp_gateway.tools.base_adapter",
            "EchoToolAdapter",
        ),
        "CalculatorToolAdapter": (
            "claude_mpm.services.mcp_gateway.tools.base_adapter",
            "CalculatorToolAdapter",
        ),
        "SystemInfoToolAdapter": (
            "claude_mpm.services.mcp_gateway.tools.base_adapter",
            "SystemInfoToolAdapter",
        ),
        # Configuration management
        "MCPConfiguration": (
            "claude_mpm.services.mcp_gateway.config.configuration",
            "MCPConfiguration",
        ),
        "MCPConfigLoader": (
            "claude_mpm.services.mcp_gateway.config.config_loader",
            "MCPConfigLoader",
        ),
        # Service registry
        "MCPServiceRegistry": (
            "claude_mpm.services.mcp_gateway.registry.service_registry",
            "MCPServiceRegistry",
        ),
        # Exceptions
        "MCPException": (
            "claude_mpm.services.mcp_gateway.core.exceptions",
            "MCPException",
        ),
        "MCPConfigurationError": (
            "claude_mpm.services.mcp_gateway.core.exceptions",
            "MCPConfigurationError",
        ),
        "MCPToolNotFoundError": (
            "claude_mpm.services.mcp_gateway.core.exceptions",
            "MCPToolNotFoundError",
        ),
        "MCPServerError": (
            "claude_mpm.services.mcp_gateway.core.exceptions",
            "MCPServerError",
        ),
    }

    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = import_module(module_path)
        return getattr(module, attr_name)

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
