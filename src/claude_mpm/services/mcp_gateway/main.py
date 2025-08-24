from pathlib import Path

"""
MCP Gateway Main Entry Point
=============================

Main entry point for running the MCP Gateway server.
Orchestrates server initialization, tool registration, and lifecycle management.

Part of ISS-0035: MCP Server Implementation - Core Server and Tool Registry
"""

import argparse
import asyncio
import logging
import signal
import sys
from typing import Optional

# Import with fallback handling for missing dependencies
try:
    from claude_mpm.core.logger import get_logger
except ImportError:
    import logging

    def get_logger(name):
        return logging.getLogger(name)


try:
    from claude_mpm.services.mcp_gateway.config.configuration import MCPConfiguration
except ImportError:
    # Fallback configuration class
    class MCPConfiguration:
        def __init__(self):
            self.config = {}

        def load_config(self, path):
            return True

        def get(self, key, default=None):
            return default


try:
    from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry
except ImportError:
    # Minimal fallback registry
    class ToolRegistry:
        def __init__(self):
            self.tools = []

        async def initialize(self):
            return True

        def register_tool(self, tool, category="builtin"):
            return True

        async def shutdown(self):
            pass


try:
    from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway
except ImportError as e:
    raise ImportError(f"Critical: Cannot import MCPGateway server: {e}")

try:
    from claude_mpm.services.mcp_gateway.server.stdio_handler import StdioHandler
except ImportError:
    # Fallback stdio handler
    class StdioHandler:
        async def initialize(self):
            return True

        async def shutdown(self):
            pass


# Import tools with individual fallbacks
try:
    from claude_mpm.services.mcp_gateway.tools.base_adapter import (
        CalculatorToolAdapter,
        EchoToolAdapter,
        SystemInfoToolAdapter,
    )
except ImportError:
    # Create dummy tool adapters
    class BaseToolAdapter:
        def __init__(self):
            pass

        async def initialize(self):
            return True

        def get_definition(self):
            return type("ToolDef", (), {"name": "unknown"})

    CalculatorToolAdapter = BaseToolAdapter
    EchoToolAdapter = BaseToolAdapter
    SystemInfoToolAdapter = BaseToolAdapter

try:
    from claude_mpm.services.mcp_gateway.tools.document_summarizer import (
        DocumentSummarizerTool,
    )
except ImportError:
    DocumentSummarizerTool = None

try:
    from claude_mpm.services.mcp_gateway.tools.unified_ticket_tool import (
        UnifiedTicketTool,
    )
except ImportError:
    # Unified ticket tool is optional
    UnifiedTicketTool = None

# Manager module removed - using simplified architecture


class MCPGatewayOrchestrator:
    """
    Main MCP Gateway orchestrator.

    WHY: This class coordinates all MCP components, managing their lifecycle
    and ensuring proper initialization, startup, and shutdown sequences.

    DESIGN DECISIONS:
    - Use dependency injection to wire components together
    - Implement graceful shutdown on SIGINT/SIGTERM
    - Support both configuration file and CLI arguments
    - Provide comprehensive logging for debugging
    - Renamed from MCPGateway to avoid naming conflict with server class
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the MCP Gateway.

        Args:
            config_path: Optional path to configuration file
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config_path = config_path

        # Core components
        self.server: Optional[MCPGateway] = None
        self.registry: Optional[ToolRegistry] = None
        self.communication: Optional[StdioHandler] = None
        self.configuration: Optional[MCPConfiguration] = None

        # Shutdown handling
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(sig, frame):
            self.logger.info(f"Received signal {sig}, initiating shutdown...")
            self._shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def initialize(self) -> bool:
        """
        Initialize all MCP Gateway components.

        Returns:
            True if initialization successful
        """
        try:
            self.logger.info("Initializing MCP Gateway")

            # Load configuration
            self.configuration = MCPConfiguration()
            if self.config_path and self.config_path.exists():
                if not self.configuration.load_config(self.config_path):
                    self.logger.error("Failed to load configuration")
                    return False

            # Initialize tool registry with error handling
            try:
                self.registry = ToolRegistry()
                if not await self.registry.initialize():
                    self.logger.error("Failed to initialize tool registry")
                    # Continue anyway - server can run without tools
                    self.registry = None
            except Exception as e:
                self.logger.warning(f"Tool registry initialization failed: {e}")
                self.registry = None

            # Register built-in tools if registry is available
            if self.registry:
                try:
                    await self._register_builtin_tools()
                except Exception as e:
                    self.logger.warning(f"Failed to register some tools: {e}")
                    # Continue - server can run with partial tools

            # Initialize communication handler with fallback
            try:
                self.communication = StdioHandler()
                if not await self.communication.initialize():
                    self.logger.warning("Failed to initialize communication handler")
                    # Communication is optional for the server
                    self.communication = None
            except Exception as e:
                self.logger.warning(f"Communication handler initialization failed: {e}")
                self.communication = None

            # Initialize MCP gateway server
            gateway_name = self.configuration.get("server.name", "claude-mpm-mcp")
            version = self.configuration.get("server.version", "1.0.0")
            self.server = MCPGateway(gateway_name=gateway_name, version=version)

            # Wire dependencies (only if available)
            if self.registry:
                self.server.set_tool_registry(self.registry)
            else:
                self.logger.warning("Running without tool registry")

            if self.communication:
                self.server.set_communication(self.communication)
            else:
                self.logger.info("Running without custom communication handler")

            if not await self.server.initialize():
                self.logger.error("Failed to initialize MCP server")
                return False

            self.logger.info("MCP Gateway initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize MCP Gateway: {e}")
            return False

    async def _register_builtin_tools(self) -> None:
        """Register built-in tools with the registry."""
        self.logger.info("Registering built-in tools")

        # Create tool adapters (only include available tools)
        tools = []

        # Always include basic tools
        try:
            tools.extend(
                [
                    EchoToolAdapter(),
                    CalculatorToolAdapter(),
                    SystemInfoToolAdapter(),
                ]
            )
        except Exception as e:
            self.logger.warning(f"Could not load basic tools: {e}")

        # Optional: Health check tool
        try:
            from .tools.health_check_tool import HealthCheckTool

            tools.append(HealthCheckTool())
        except Exception as e:
            self.logger.warning(f"Could not load health check tool: {e}")

        # Optional: Document summarizer
        if DocumentSummarizerTool is not None:
            try:
                tools.append(DocumentSummarizerTool())
            except Exception as e:
                self.logger.warning(f"Could not load document summarizer: {e}")

        # Optional: Unified ticket management tool
        if UnifiedTicketTool is not None:
            try:
                tools.append(UnifiedTicketTool())
            except Exception as e:
                self.logger.warning(f"Could not load unified ticket tool: {e}")

        if not tools:
            self.logger.warning("No tools available to register")
            return

        # Register each tool
        for tool in tools:
            try:
                # Initialize the tool
                if await tool.initialize():
                    # Register with the registry
                    if self.registry.register_tool(tool, category="builtin"):
                        self.logger.info(
                            f"Registered tool: {tool.get_definition().name}"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to register tool: {tool.get_definition().name}"
                        )
                else:
                    self.logger.warning(
                        f"Failed to initialize tool: {tool.get_definition().name}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Error registering tool {tool.get_definition().name}: {e}"
                )

    async def start(self) -> bool:
        """
        Start the MCP Gateway server.

        Returns:
            True if startup successful
        """
        try:
            self.logger.info("Starting MCP Gateway")

            if not self.server:
                self.logger.error("Server not initialized")
                return False

            if not await self.server.start():
                self.logger.error("Failed to start MCP server")
                return False

            self.logger.info("MCP Gateway started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start MCP Gateway: {e}")
            return False

    async def run(self) -> None:
        """
        Run the MCP Gateway main loop.

        This method blocks until shutdown is requested.
        """
        try:
            self.logger.info("MCP Gateway running")

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            self.logger.info("Shutdown signal received")

        except Exception as e:
            self.logger.error(f"Error in MCP Gateway main loop: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the MCP Gateway gracefully."""
        try:
            self.logger.info("Shutting down MCP Gateway")

            # Shutdown server
            if self.server:
                await self.server.shutdown()

            # Shutdown registry (which will shutdown all tools)
            if self.registry:
                try:
                    await self.registry.shutdown()
                except Exception as e:
                    self.logger.warning(f"Error during registry shutdown: {e}")

            # Shutdown communication handler
            if self.communication:
                try:
                    await self.communication.shutdown()
                except Exception as e:
                    self.logger.warning(f"Error during communication shutdown: {e}")

            self.logger.info("MCP Gateway shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


async def main(args: argparse.Namespace) -> int:
    """
    Main entry point for the MCP Gateway.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create gateway orchestrator instance
    config_path = Path(args.config) if args.config else None
    gateway = MCPGatewayOrchestrator(config_path=config_path)

    try:
        # Initialize
        if not await gateway.initialize():
            logging.error("Failed to initialize MCP Gateway")
            return 1

        # Start
        if not await gateway.start():
            logging.error("Failed to start MCP Gateway")
            return 1

        # Run until shutdown
        await gateway.run()

        # Graceful shutdown
        await gateway.shutdown()

        return 0

    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        await gateway.shutdown()
        return 1


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Claude MPM MCP Gateway Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration
  python -m claude_mpm.services.mcp_gateway.main

  # Run with custom configuration file
  python -m claude_mpm.services.mcp_gateway.main --config /path/to/config.yaml

  # Run with debug logging
  python -m claude_mpm.services.mcp_gateway.main --debug

  # Run as MCP server for Claude Code
  python -m claude_mpm.services.mcp_gateway.main --stdio
        """,
    )

    parser.add_argument("--config", type=str, help="Path to configuration file")

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument(
        "--stdio",
        action="store_true",
        default=True,
        help="Use stdio for communication (default)",
    )

    parser.add_argument(
        "--version", action="version", version="Claude MPM MCP Gateway 1.0.0"
    )

    return parser.parse_args()


async def run_standalone_gateway(
    gateway_name: str = "claude-mpm-mcp", version: str = "1.0.0"
):
    """
    Run the MCP Gateway as a standalone server.

    This creates a simple instance without complex management.

    Args:
        gateway_name: Name for the gateway
        version: Gateway version
    """
    logger = get_logger("MCPGatewayMain")

    try:
        logger.info(f"Starting standalone MCP gateway: {gateway_name}")

        # Create and run a simple orchestrator
        orchestrator = MCPGatewayOrchestrator()

        if not await orchestrator.initialize():
            logger.error("Failed to initialize gateway")
            return False

        if not await orchestrator.start():
            logger.error("Failed to start gateway")
            return False

        # Run until shutdown
        await orchestrator.run()
        await orchestrator.shutdown()

        return True

    except Exception as e:
        logger.error(f"Error running standalone gateway: {e}")
        return False


if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()

    # Run the gateway
    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)
