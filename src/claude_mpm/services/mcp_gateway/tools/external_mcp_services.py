"""
External MCP Services Integration
==================================

Manages installation and basic setup of external MCP services like mcp-vector-search
and mcp-browser. These services run as separate MCP servers in Claude Code,
not as part of the Claude MPM MCP Gateway.

Note: As of the latest architecture, external services are registered as separate
MCP servers in Claude Code configuration, not as tools within the gateway.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter


class ExternalMCPService(BaseToolAdapter):
    """Base class for external MCP service integration."""

    def __init__(self, service_name: str, package_name: str):
        """
        Initialize external MCP service.

        Args:
            service_name: Name of the service for MCP
            package_name: Python package name to install/run
        """
        # Import here to avoid circular imports
        from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolDefinition

        # Create a basic tool definition for the service
        tool_def = MCPToolDefinition(
            name=service_name,
            description=f"External MCP service: {package_name}",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )
        super().__init__(tool_def)
        self.service_name = service_name
        self.package_name = package_name
        self.process = None
        self._is_installed = False

    async def invoke(self, invocation):
        """
        Invoke method required by BaseToolAdapter interface.

        This base implementation should be overridden by subclasses.
        """
        # Import here to avoid circular imports
        from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolResult

        return MCPToolResult(
            success=False,
            error="invoke method not implemented in base ExternalMCPService",
            execution_time=0.0,
        )

    async def initialize(self) -> bool:
        """Initialize the external service."""
        try:
            # Check if package is installed
            self._is_installed = await self._check_installation()

            if not self._is_installed:
                self.logger.debug(
                    f"{self.package_name} not installed - will attempt automatic installation if needed"
                )
                await self._install_package()
                self._is_installed = await self._check_installation()

            if not self._is_installed:
                self.logger.error(f"Failed to install {self.package_name}")
                return False

            self.logger.info(f"{self.package_name} is available")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize {self.service_name}: {e}")
            return False

    async def _check_installation(self) -> bool:
        """Check if the package is installed."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", self.package_name.replace("-", "_"), "--help"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.CalledProcessError,
        ):
            return False

    async def _install_package(self) -> bool:
        """Install the package using pip."""
        try:
            self.logger.info(f"Installing {self.package_name}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", self.package_name],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                self.logger.info(f"Successfully installed {self.package_name}")
                return True
            self.logger.error(f"Failed to install {self.package_name}: {result.stderr}")
            return False

        except Exception as e:
            self.logger.error(f"Error installing {self.package_name}: {e}")
            return False

    def get_definition(self) -> Dict[str, Any]:
        """Get service definition for MCP registration."""
        return {
            "name": self.service_name,
            "description": f"External MCP service: {self.package_name}",
            "type": "external_service",
            "package": self.package_name,
            "installed": self._is_installed,
        }


class MCPVectorSearchService(ExternalMCPService):
    """MCP Vector Search service integration."""

    def __init__(self):
        """Initialize MCP Vector Search service."""
        super().__init__("mcp-vector-search", "mcp-vector-search")

    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for MCP registration."""
        base_def = super().get_definition()
        base_def.update(
            {
                "description": "Semantic code search powered by vector embeddings",
                "tools": [
                    {
                        "name": "mcp__mcp-vector-search__search_code",
                        "description": "Search for code using semantic similarity",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query",
                                },
                                "limit": {"type": "integer", "default": 10},
                                "similarity_threshold": {
                                    "type": "number",
                                    "default": 0.3,
                                },
                                "language": {"type": "string"},
                                "file_extensions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "files": {"type": "string"},
                                "class_name": {"type": "string"},
                                "function_name": {"type": "string"},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "mcp__mcp-vector-search__search_similar",
                        "description": "Find code similar to a specific file or function",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to the file",
                                },
                                "function_name": {"type": "string"},
                                "limit": {"type": "integer", "default": 10},
                                "similarity_threshold": {
                                    "type": "number",
                                    "default": 0.3,
                                },
                            },
                            "required": ["file_path"],
                        },
                    },
                    {
                        "name": "mcp__mcp-vector-search__search_context",
                        "description": "Search for code based on contextual description",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "description": {
                                    "type": "string",
                                    "description": "Contextual description",
                                },
                                "focus_areas": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "limit": {"type": "integer", "default": 10},
                            },
                            "required": ["description"],
                        },
                    },
                    {
                        "name": "mcp__mcp-vector-search__get_project_status",
                        "description": "Get project indexing status and statistics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                    {
                        "name": "mcp__mcp-vector-search__index_project",
                        "description": "Index or reindex the project codebase",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "force": {"type": "boolean", "default": False},
                                "file_extensions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": [],
                        },
                    },
                ],
            }
        )
        return base_def

    async def invoke(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool from mcp-vector-search."""
        try:
            # Extract the actual tool name (remove prefix)
            actual_tool = tool_name.replace("mcp__mcp-vector-search__", "")

            # Prepare the command
            cmd = [
                sys.executable,
                "-m",
                "mcp_vector_search",
                "--tool",
                actual_tool,
                "--args",
                json.dumps(arguments),
            ]

            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=Path.cwd(),
                check=False,  # Use current working directory for project context
            )

            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"result": result.stdout}
            else:
                return {"error": result.stderr or "Tool invocation failed"}

        except subprocess.TimeoutExpired:
            return {"error": "Tool invocation timed out"}
        except Exception as e:
            return {"error": str(e)}


class MCPBrowserService(ExternalMCPService):
    """MCP Browser service integration."""

    def __init__(self):
        """Initialize MCP Browser service."""
        super().__init__("mcp-browser", "mcp-browser")

    def get_definition(self) -> Dict[str, Any]:
        """Get tool definition for MCP registration."""
        base_def = super().get_definition()
        base_def.update(
            {
                "description": "Web browsing and content extraction capabilities",
                "tools": [
                    {
                        "name": "mcp__mcp-browser__browse",
                        "description": "Browse a webpage and extract content",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "URL to browse",
                                },
                                "extract": {
                                    "type": "string",
                                    "description": "What to extract",
                                },
                            },
                            "required": ["url"],
                        },
                    },
                    {
                        "name": "mcp__mcp-browser__search",
                        "description": "Search the web",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query",
                                },
                                "num_results": {"type": "integer", "default": 10},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "mcp__mcp-browser__screenshot",
                        "description": "Take a screenshot of a webpage",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "URL to screenshot",
                                },
                                "full_page": {"type": "boolean", "default": False},
                            },
                            "required": ["url"],
                        },
                    },
                ],
            }
        )
        return base_def

    async def invoke(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool from mcp-browser."""
        try:
            # Extract the actual tool name (remove prefix)
            actual_tool = tool_name.replace("mcp__mcp-browser__", "")

            # Prepare the command
            cmd = [
                sys.executable,
                "-m",
                "mcp_browser",
                "--tool",
                actual_tool,
                "--args",
                json.dumps(arguments),
            ]

            # Run the command
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=False
            )

            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"result": result.stdout}
            else:
                return {"error": result.stderr or "Tool invocation failed"}

        except subprocess.TimeoutExpired:
            return {"error": "Tool invocation timed out"}
        except Exception as e:
            return {"error": str(e)}


class ExternalMCPServiceManager:
    """Manager for external MCP services.

    This manager is responsible for checking and installing Python packages
    for external MCP services. The actual registration of these services
    happens in Claude Code configuration as separate MCP servers.

    Note: This class is maintained for backward compatibility and package
    management. The actual tool registration is handled by separate MCP
    server instances in Claude Code.
    """

    def __init__(self):
        """Initialize the service manager."""
        self.services: List[ExternalMCPService] = []
        self.logger = None

    async def initialize_services(self) -> List[ExternalMCPService]:
        """Initialize all external MCP services.

        This method checks if external service packages are installed
        and attempts to install them if missing. It does NOT register
        them as tools in the gateway - they run as separate MCP servers.
        """
        # Create service instances
        # Note: kuzu-memory is configured via MCPConfigManager and runs as a separate MCP server
        # It doesn't need to be included here since it's already set up through the MCP config
        services = [MCPVectorSearchService(), MCPBrowserService()]

        # Initialize each service
        initialized_services = []
        for service in services:
            try:
                if await service.initialize():
                    initialized_services.append(service)
                    if self.logger:
                        self.logger.info(
                            f"Initialized external service: {service.service_name}"
                        )
                elif self.logger:
                    self.logger.debug(
                        f"Service not available (optional): {service.service_name}"
                    )
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error initializing {service.service_name}: {e}")

        self.services = initialized_services
        return initialized_services

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tool definitions from external services."""
        all_tools = []
        for service in self.services:
            service_def = service.get_definition()
            if "tools" in service_def:
                all_tools.extend(service_def["tools"])
        return all_tools

    async def invoke_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke a tool from any registered external service."""
        # Find the service that handles this tool
        for service in self.services:
            if tool_name.startswith(f"mcp__{service.service_name}__"):
                if isinstance(service, (MCPVectorSearchService, MCPBrowserService)):
                    return await service.invoke(tool_name, arguments)

        return {"error": f"No service found for tool: {tool_name}"}

    async def shutdown(self):
        """Shutdown all external services."""
        for service in self.services:
            try:
                await service.shutdown()
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Error shutting down {service.service_name}: {e}"
                    )
