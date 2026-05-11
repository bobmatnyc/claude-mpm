"""MCP configuration management subpackage.

Decomposes the historic ``MCPConfigManager`` god class into focused services:

- :class:`MCPServiceLocator` -- discover service executables
- :class:`MCPServiceConfigBuilder` -- generate service config dicts
- :class:`MCPConfigFileManager` -- read/write Claude config files
- :class:`MCPServiceInstaller` -- install missing services
- :class:`MCPServiceHealthManager` -- detect/repair broken installations

The thin :class:`MCPConfigManager` facade in
``claude_mpm.services.mcp_config_manager`` remains the public entry point
for backward compatibility (#507).
"""

from .config_builder import MCPServiceConfigBuilder
from .config_file_manager import ConfigLocation, MCPConfigFileManager
from .health_manager import MCPServiceHealthManager
from .service_installer import MCPServiceInstaller
from .service_locator import MCPServiceLocator

__all__ = [
    "ConfigLocation",
    "MCPConfigFileManager",
    "MCPServiceConfigBuilder",
    "MCPServiceHealthManager",
    "MCPServiceInstaller",
    "MCPServiceLocator",
]
