"""
MCP Gateway Startup Verification
================================

Provides startup verification and installation for MCP Gateway configuration.
Ensures the gateway is properly configured with essential tools on startup.

WHY: The MCP gateway should be automatically configured and verified on startup
to provide a seamless experience with diagnostic tools, file summarizer, and
ticket service.

DESIGN DECISIONS:
- Automatic configuration detection and installation
- Essential tools verification (diagnostics, file summarizer, ticket service)
- Graceful fallback when tools are unavailable
- Non-blocking startup (warnings instead of failures)
"""

from typing import Any, Dict

from claude_mpm.config.paths import paths
from claude_mpm.core.logger import get_logger

from .singleton_manager import get_gateway_manager, is_gateway_running


class MCPGatewayStartupVerifier:
    """
    Verifies and configures MCP Gateway on startup.

    Ensures the gateway is properly configured with essential tools and
    provides diagnostic information about the gateway state.
    """

    def __init__(self):
        """Initialize the startup verifier."""
        self.logger = get_logger("MCPGatewayStartupVerifier")
        self.config_dir = paths.claude_mpm_dir_hidden / "mcp"
        self.config_file = self.config_dir / "gateway_config.json"

        # Essential tools that should be available
        self.essential_tools = [
            "echo",  # Basic diagnostic tool
            "calculator",  # Math operations
            "system_info",  # System diagnostics
            "health_check",  # Health diagnostics
            "document_summarizer",  # File summarizer
            "ticket",  # Ticket service (unified)
        ]

    async def verify_and_configure(self) -> Dict[str, Any]:
        """
        Verify MCP gateway configuration and configure if needed.

        Returns:
            Dictionary with verification results and status
        """
        self.logger.info("Starting MCP Gateway verification")

        results = {
            "gateway_configured": False,
            "singleton_manager": False,
            "essential_tools": {},
            "configuration_created": False,
            "warnings": [],
            "errors": [],
        }

        try:
            # 1. Verify singleton manager
            results["singleton_manager"] = self._verify_singleton_manager()

            # 2. Ensure configuration directory exists
            self._ensure_config_directory()

            # 3. Verify or create gateway configuration
            config_created = await self._verify_gateway_configuration()
            results["configuration_created"] = config_created

            # 4. Verify essential tools
            tools_status = await self._verify_essential_tools()
            results["essential_tools"] = tools_status

            # 5. Check overall gateway status
            results["gateway_configured"] = self._assess_gateway_status(results)

            # Log summary
            self._log_verification_summary(results)

            return results

        except Exception as e:
            self.logger.error(f"Error during MCP Gateway verification: {e}")
            results["errors"].append(f"Verification failed: {e}")
            return results

    def _verify_singleton_manager(self) -> bool:
        """Verify singleton manager is working."""
        try:
            get_gateway_manager()
            # Test basic functionality
            running = is_gateway_running()
            self.logger.debug(
                f"Singleton manager operational, gateway running: {running}"
            )
            return True
        except Exception as e:
            self.logger.warning(f"Singleton manager issue: {e}")
            return False

    def _ensure_config_directory(self):
        """Ensure MCP configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"MCP config directory: {self.config_dir}")

    async def _verify_gateway_configuration(self) -> bool:
        """Verify or create gateway configuration."""
        if self.config_file.exists():
            self.logger.debug("Gateway configuration file exists")
            return False

        # Create default configuration
        default_config = self._create_default_configuration()

        try:
            import json

            with open(self.config_file, "w") as f:
                json.dump(default_config, f, indent=2)

            self.logger.info(
                f"Created default gateway configuration: {self.config_file}"
            )
            return True

        except Exception as e:
            self.logger.warning(f"Failed to create configuration: {e}")
            return False

    def _create_default_configuration(self) -> Dict[str, Any]:
        """Create default MCP gateway configuration."""
        return {
            "mcp": {
                "server": {
                    "name": "claude-mpm-mcp-gateway",
                    "version": "1.0.0",
                    "description": "Claude MPM MCP Gateway with essential tools",
                },
                "tools": {
                    "enabled": True,
                    "auto_discover": True,
                    "timeout_default": 30,
                    "max_concurrent": 10,
                    "essential_tools": self.essential_tools,
                },
                "logging": {
                    "level": "INFO",
                    "file": str(paths.logs_dir / "mcp_gateway.log"),
                },
                "security": {"validate_schemas": True, "sanitize_inputs": True},
            }
        }

    async def _verify_essential_tools(self) -> Dict[str, Dict[str, Any]]:
        """Verify essential tools are available."""
        tools_status = {}

        for tool_name in self.essential_tools:
            status = await self._verify_tool(tool_name)
            tools_status[tool_name] = status

        return tools_status

    async def _verify_tool(self, tool_name: str) -> Dict[str, Any]:
        """Verify a specific tool is available."""
        status = {
            "available": False,
            "initialized": False,
            "error": None,
        }

        try:
            # Try to import and initialize the tool
            tool_instance = await self._create_tool_instance(tool_name)

            if tool_instance:
                status["available"] = True

                # Try to initialize
                if hasattr(tool_instance, "initialize"):
                    initialized = await tool_instance.initialize()
                    status["initialized"] = initialized
                else:
                    status["initialized"] = True

        except Exception as e:
            status["error"] = str(e)
            self.logger.debug(f"Tool {tool_name} verification failed: {e}")

        return status

    async def _create_tool_instance(self, tool_name: str):
        """Create an instance of the specified tool."""
        tool_map = {
            "echo": ("..tools.base_adapter", "EchoToolAdapter"),
            "calculator": ("..tools.base_adapter", "CalculatorToolAdapter"),
            "system_info": ("..tools.base_adapter", "SystemInfoToolAdapter"),
            "health_check": ("..tools.health_check_tool", "HealthCheckTool"),
            "document_summarizer": (
                "..tools.document_summarizer",
                "DocumentSummarizerTool",
            ),
            "ticket": ("..tools.unified_ticket_tool", "UnifiedTicketTool"),
        }

        if tool_name not in tool_map:
            return None

        module_path, class_name = tool_map[tool_name]

        try:
            # Dynamic import
            from importlib import import_module

            module = import_module(module_path, package=__package__)
            tool_class = getattr(module, class_name)
            return tool_class()
        except (ImportError, AttributeError) as e:
            self.logger.debug(f"Could not import {tool_name}: {e}")
            return None

    def _assess_gateway_status(self, results: Dict[str, Any]) -> bool:
        """Assess overall gateway configuration status."""
        # Gateway is considered configured if:
        # 1. Singleton manager works
        # 2. At least basic tools are available
        # 3. No critical errors

        if not results["singleton_manager"]:
            return False

        if results["errors"]:
            return False

        # Check if at least basic diagnostic tools are available
        essential_available = 0
        for _tool_name, status in results["essential_tools"].items():
            if status.get("available", False):
                essential_available += 1

        # Consider configured if at least 3 essential tools are available
        return essential_available >= 3

    def _log_verification_summary(self, results: Dict[str, Any]):
        """Log verification summary."""
        if results["gateway_configured"]:
            self.logger.info("✅ MCP Gateway verification completed successfully")
        else:
            self.logger.warning("⚠️ MCP Gateway verification completed with issues")

        # Log tool status
        available_tools = []
        unavailable_tools = []

        for tool_name, status in results["essential_tools"].items():
            if status.get("available", False):
                available_tools.append(tool_name)
            else:
                unavailable_tools.append(tool_name)

        if available_tools:
            self.logger.info(f"Available tools: {', '.join(available_tools)}")

        if unavailable_tools:
            self.logger.warning(f"Unavailable tools: {', '.join(unavailable_tools)}")

        # Log warnings and errors
        for warning in results.get("warnings", []):
            self.logger.warning(warning)

        for error in results.get("errors", []):
            self.logger.error(error)


# Global verification function
async def verify_mcp_gateway_on_startup() -> Dict[str, Any]:
    """
    Verify MCP Gateway configuration on startup.

    This function should be called during application startup to ensure
    the MCP gateway is properly configured.

    Returns:
        Dictionary with verification results
    """
    verifier = MCPGatewayStartupVerifier()
    return await verifier.verify_and_configure()


def is_mcp_gateway_configured() -> bool:
    """
    Quick check if MCP gateway appears to be configured.

    Returns:
        True if gateway appears configured, False otherwise
    """
    try:
        # Check if singleton manager works
        get_gateway_manager()

        # Check if config directory exists
        config_dir = paths.claude_mpm_dir_hidden / "mcp"
        return config_dir.exists()

    except Exception:
        return False
