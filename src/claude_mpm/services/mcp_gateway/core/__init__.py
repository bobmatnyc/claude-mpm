"""
MCP Gateway Core Module
=======================

Core interfaces and base classes for the MCP Gateway service.
"""

from .interfaces import (
    IMCPGateway,
    IMCPToolRegistry,
    IMCPConfiguration,
    IMCPToolAdapter,
    IMCPLifecycle,
    IMCPCommunication,
)

from .base import (
    BaseMCPService,
    MCPServiceState,
)

from .exceptions import (
    MCPException,
    MCPConfigurationError,
    MCPToolNotFoundError,
    MCPServerError,
    MCPCommunicationError,
    MCPValidationError,
)

__all__ = [
    # Interfaces
    "IMCPGateway",
    "IMCPToolRegistry",
    "IMCPConfiguration",
    "IMCPToolAdapter",
    "IMCPLifecycle",
    "IMCPCommunication",
    
    # Base classes
    "BaseMCPService",
    "MCPServiceState",
    
    # Exceptions
    "MCPException",
    "MCPConfigurationError",
    "MCPToolNotFoundError",
    "MCPServerError",
    "MCPCommunicationError",
    "MCPValidationError",
]