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
