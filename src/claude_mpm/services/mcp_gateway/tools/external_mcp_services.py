"""
External MCP Services Integration
==================================

Manages detection and setup of external MCP services like mcp-vector-search
and mcp-browser. These services run as separate MCP servers in Claude Code,
not as part of the Claude MPM MCP Gateway.

IMPORTANT: External services are NOT auto-installed. Users must manually install
them using pipx or pip. This gives users explicit control over which optional
services they want to enable.

Installation:
    pipx install mcp-vector-search
    pipx install mcp-browser
    pipx install kuzu-memory
    pipx install mcp-ticketer

Note: External services are registered as separate MCP servers in Claude Code
configuration, not as tools within the gateway.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter


class ExternalMCPService(BaseToolAdapter):
    """Base class for external MCP service integration.

    External services are detected if already installed but are NOT
    automatically installed. Users must install them manually using
    pipx or pip to enable these optional features.
    """

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

    async def initialize(
        self, auto_install: bool = False, interactive: bool = False
    ) -> bool:
        """Initialize the external service.

        NOTE: Auto-installation is disabled by default (v4.9.0+). Users must
        manually install external services using pipx or pip.

        Args:
            auto_install: Whether to automatically install if not found (default: False)
                         Deprecated - will be removed in future versions
            interactive: Whether to prompt user for installation preferences (default: False)
                        Only used if auto_install=True
        """
        try:
            # Check if package is installed
            self._is_installed = await self._check_installation()

            if not self._is_installed and auto_install:
                # This path is deprecated but kept for backward compatibility
                self.logger.warning(
                    f"Auto-installation is deprecated. Please install {self.package_name} manually: "
                    f"pipx install {self.package_name}"
                )
                await self._install_package(interactive=interactive)
                self._is_installed = await self._check_installation()

            if not self._is_installed:
                self.logger.debug(
                    f"{self.package_name} is not available. "
                    f"Install manually with: pipx install {self.package_name}"
                )
                return False

            self.logger.info(f"{self.package_name} is available")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize {self.service_name}: {e}")
            return False

    async def _check_installation(self) -> bool:
        """Check if the package is installed."""
        # First check if importable (faster and more reliable)
        import_name = self.package_name.replace("-", "_")
        try:
            import importlib.util

            spec = importlib.util.find_spec(import_name)
            if spec is not None:
                return True
        except (ImportError, ModuleNotFoundError, ValueError):
            pass

        # Fallback: try running as module
        try:
            result = subprocess.run(
                [sys.executable, "-m", import_name, "--help"],
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

    async def _install_package(self, interactive: bool = True) -> bool:
        """Install the package using pip or pipx.

        Args:
            interactive: Whether to prompt user for installation method choice
        """
        try:
            install_method = None

            if interactive:
                # Show user-friendly installation prompt
                print(f"\n⚠️  {self.package_name} not found", file=sys.stderr)
                print(
                    "This package enables enhanced functionality (optional).",
                    file=sys.stderr,
                )
                print("\nInstallation options:", file=sys.stderr)
                print(
                    "1. Install via pip (recommended for this project)", file=sys.stderr
                )
                print("2. Install via pipx (isolated, system-wide)", file=sys.stderr)
                print("3. Skip (continue without this package)", file=sys.stderr)

                try:
                    choice = input("\nChoose option (1/2/3) [1]: ").strip() or "1"
                    if choice == "1":
                        install_method = "pip"
                    elif choice == "2":
                        install_method = "pipx"
                    else:
                        self.logger.info(
                            f"Skipping installation of {self.package_name}"
                        )
                        return False
                except (EOFError, KeyboardInterrupt):
                    print("\nInstallation cancelled", file=sys.stderr)
                    return False
            else:
                # Non-interactive: default to pip
                install_method = "pip"

            # Install using selected method
            if install_method == "pip":
                return await self._install_via_pip()
            if install_method == "pipx":
                return await self._install_via_pipx()

            return False

        except Exception as e:
            self.logger.error(f"Error installing {self.package_name}: {e}")
            return False

    async def _install_via_pip(self) -> bool:
        """Install package via pip."""
        try:
            print(f"\n📦 Installing {self.package_name} via pip...", file=sys.stderr)
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", self.package_name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if result.returncode == 0:
                print(f"✓ Successfully installed {self.package_name}", file=sys.stderr)
                self.logger.info(f"Successfully installed {self.package_name} via pip")
                return True

            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            print(f"✗ Installation failed: {error_msg}", file=sys.stderr)
            self.logger.error(f"Failed to install {self.package_name}: {error_msg}")
            return False

        except subprocess.TimeoutExpired:
            print("✗ Installation timed out", file=sys.stderr)
            self.logger.error(f"Installation of {self.package_name} timed out")
            return False
        except Exception as e:
            print(f"✗ Installation error: {e}", file=sys.stderr)
            self.logger.error(f"Error installing {self.package_name}: {e}")
            return False

    async def _install_via_pipx(self) -> bool:
        """Install package via pipx."""
        try:
            # Check if pipx is available
            pipx_check = subprocess.run(
                ["pipx", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            if pipx_check.returncode != 0:
                print("✗ pipx is not installed", file=sys.stderr)
                print("Install pipx first: python -m pip install pipx", file=sys.stderr)
                self.logger.error("pipx not available for installation")
                return False

            print(f"\n📦 Installing {self.package_name} via pipx...", file=sys.stderr)
            result = subprocess.run(
                ["pipx", "install", self.package_name],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if result.returncode == 0:
                print(f"✓ Successfully installed {self.package_name}", file=sys.stderr)
                self.logger.info(f"Successfully installed {self.package_name} via pipx")
                return True

            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            print(f"✗ Installation failed: {error_msg}", file=sys.stderr)
            self.logger.error(f"Failed to install {self.package_name}: {error_msg}")
            return False

        except FileNotFoundError:
            print("✗ pipx command not found", file=sys.stderr)
            print("Install pipx first: python -m pip install pipx", file=sys.stderr)
            self.logger.error("pipx command not found")
            return False
        except subprocess.TimeoutExpired:
            print("✗ Installation timed out", file=sys.stderr)
            self.logger.error(f"Installation of {self.package_name} timed out")
            return False
        except Exception as e:
            print(f"✗ Installation error: {e}", file=sys.stderr)
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

    This manager is responsible for detecting (but NOT installing) Python packages
    for external MCP services. The actual registration of these services happens
    in Claude Code configuration as separate MCP servers.

    IMPORTANT: As of v4.9.0, this manager NO LONGER auto-installs missing services.
    Users must manually install external services using pipx or pip:
        - pipx install mcp-vector-search
        - pipx install mcp-browser
        - pipx install kuzu-memory
        - pipx install mcp-ticketer

    Note: This class is maintained for backward compatibility and service detection.
    The actual tool registration is handled by separate MCP server instances in
    Claude Code.
    """

    def __init__(self):
        """Initialize the service manager."""
        self.services: List[ExternalMCPService] = []
        self.logger = None

    async def initialize_services(self) -> List[ExternalMCPService]:
        """Initialize all external MCP services.

        This method checks if external service packages are already installed
        and registers them if available. It does NOT auto-install missing services.

        External MCP services (mcp-vector-search, mcp-browser, kuzu-memory, mcp-ticketer)
        must be manually installed by users. This gives users explicit control over
        which services they want to use.

        Installation instructions:
        - mcp-vector-search: pipx install mcp-vector-search
        - mcp-browser: pipx install mcp-browser
        - kuzu-memory: pipx install kuzu-memory
        - mcp-ticketer: pipx install mcp-ticketer

        Services run as separate MCP servers in Claude Code, not as tools within
        the gateway.
        """
        # Create service instances
        # Note: kuzu-memory and mcp-ticketer are configured via MCPConfigManager
        # and run as separate MCP servers. They don't need to be included here
        # since they're already set up through the MCP config.
        services = [MCPVectorSearchService(), MCPBrowserService()]

        # Initialize each service (check if installed, but DO NOT auto-install)
        initialized_services = []
        for service in services:
            try:
                # Pass auto_install=False to prevent automatic installation
                if await service.initialize(auto_install=False, interactive=False):
                    initialized_services.append(service)
                    if self.logger:
                        self.logger.info(
                            f"Initialized external service: {service.service_name}"
                        )
                elif self.logger:
                    self.logger.debug(
                        f"Service not available (optional): {service.service_name}. "
                        f"Install manually with: pipx install {service.package_name}"
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
