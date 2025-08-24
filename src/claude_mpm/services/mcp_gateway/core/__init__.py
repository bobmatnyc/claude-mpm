"""
MCP Gateway Core Module
=======================

Core interfaces and base classes for the MCP Gateway service.
"""

from .base import BaseMCPService, MCPServiceState
from .exceptions import (
    MCPCommunicationError,
    MCPConfigurationError,
    MCPException,
    MCPServerError,
    MCPToolNotFoundError,
    MCPValidationError,
)
from .interfaces import (
    IMCPCommunication,
    IMCPConfiguration,
    IMCPGateway,
    IMCPLifecycle,
    IMCPToolAdapter,
    IMCPToolRegistry,
)

__all__ = [
    # Base classes
    "BaseMCPService",
    "IMCPCommunication",
    "IMCPConfiguration",
    # Interfaces
    "IMCPGateway",
    "IMCPLifecycle",
    "IMCPToolAdapter",
    "IMCPToolRegistry",
    "MCPCommunicationError",
    "MCPConfigurationError",
    # Exceptions
    "MCPException",
    "MCPServerError",
    "MCPServiceState",
    "MCPToolNotFoundError",
    "MCPValidationError",
]
