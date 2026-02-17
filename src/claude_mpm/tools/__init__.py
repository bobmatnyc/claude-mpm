"""
Tools package for Claude MPM.

This package contains:
1. Utility tools and debugging modules (code analysis, SocketIO debugging)
2. Service tool modules for bulk MCP operations (NEW)

Service Tools Framework:
    claude-mpm tools <service> <action> [options]

Services:
    google    - Google Workspace bulk operations
    slack     - Slack bulk operations
"""

from typing import Optional

try:
    from .base import BaseToolModule, ToolResult

    # Service registry - maps service name to module class
    _SERVICE_REGISTRY: dict[str, type[BaseToolModule]] = {}

    def register_service(service_name: str, module_class: type[BaseToolModule]) -> None:
        """Register a service tool module."""
        _SERVICE_REGISTRY[service_name] = module_class

    def get_service(service_name: str) -> Optional[type[BaseToolModule]]:
        """Get service module class by name."""
        return _SERVICE_REGISTRY.get(service_name)

    def list_services() -> list[str]:
        """Return list of registered service names."""
        return sorted(_SERVICE_REGISTRY.keys())

    def load_services() -> None:
        """Load and register all available service modules."""
        # Import service modules to register them
        try:
            from .google import GoogleTools
        except ImportError:
            pass  # Not yet implemented

        try:
            from .slack import SlackTools
        except ImportError:
            pass  # Not yet implemented

    __all__ = [
        "BaseToolModule",
        "ToolResult",
        "get_service",
        "list_services",
        "load_services",
        "register_service",
    ]

except ImportError:
    # Base module not available yet
    pass
