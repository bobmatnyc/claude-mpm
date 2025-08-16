"""
MCP Gateway Main Entry Point
=============================

Main entry point for running the MCP Gateway server.
Orchestrates server initialization, tool registration, and lifecycle management.

Part of ISS-0035: MCP Server Implementation - Core Server and Tool Registry
"""

import asyncio
import sys
import signal
from pathlib import Path
from typing import Optional, List
import argparse
import logging

from claude_mpm.services.mcp_gateway.server.mcp_gateway import MCPGateway
from claude_mpm.services.mcp_gateway.server.stdio_handler import StdioHandler
from claude_mpm.services.mcp_gateway.registry.tool_registry import ToolRegistry
from claude_mpm.services.mcp_gateway.tools.base_adapter import (
    EchoToolAdapter,
    CalculatorToolAdapter,
    SystemInfoToolAdapter
)
from claude_mpm.services.mcp_gateway.tools.document_summarizer import DocumentSummarizerTool
from claude_mpm.services.mcp_gateway.config.configuration import MCPConfiguration
from claude_mpm.core.logger import get_logger
from .manager import start_global_gateway, run_global_gateway


class MCPGateway:
    """
    Main MCP Gateway orchestrator.
    
    WHY: This class coordinates all MCP components, managing their lifecycle
    and ensuring proper initialization, startup, and shutdown sequences.
    
    DESIGN DECISIONS:
    - Use dependency injection to wire components together
    - Implement graceful shutdown on SIGINT/SIGTERM
    - Support both configuration file and CLI arguments
    - Provide comprehensive logging for debugging
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
        self.server: Optional[MCPServer] = None
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
            
            # Initialize tool registry
            self.registry = ToolRegistry()
            if not await self.registry.initialize():
                self.logger.error("Failed to initialize tool registry")
                return False
            
            # Register built-in tools
            await self._register_builtin_tools()
            
            # Initialize communication handler
            self.communication = StdioHandler()
            if not await self.communication.initialize():
                self.logger.error("Failed to initialize communication handler")
                return False
            
            # Initialize MCP gateway
            gateway_name = self.configuration.get("server.name", "claude-mpm-mcp")
            version = self.configuration.get("server.version", "1.0.0")
            self.server = MCPGateway(gateway_name=gateway_name, version=version)
            
            # Wire dependencies
            self.server.set_tool_registry(self.registry)
            self.server.set_communication(self.communication)
            
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
        
        # Create tool adapters
        tools = [
            EchoToolAdapter(),
            CalculatorToolAdapter(),
            SystemInfoToolAdapter(),
            DocumentSummarizerTool()  # ISS-0037: Document summarizer for memory optimization
        ]
        
        # Register each tool
        for tool in tools:
            try:
                # Initialize the tool
                if await tool.initialize():
                    # Register with the registry
                    if self.registry.register_tool(tool, category="builtin"):
                        self.logger.info(f"Registered tool: {tool.get_definition().name}")
                    else:
                        self.logger.warning(f"Failed to register tool: {tool.get_definition().name}")
                else:
                    self.logger.warning(f"Failed to initialize tool: {tool.get_definition().name}")
            except Exception as e:
                self.logger.error(f"Error registering tool {tool.get_definition().name}: {e}")
    
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
                await self.registry.shutdown()
            
            # Shutdown communication handler
            if self.communication:
                await self.communication.shutdown()
            
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
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create gateway instance
    config_path = Path(args.config) if args.config else None
    gateway = MCPGateway(config_path=config_path)
    
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
  
  # Run as MCP server for Claude Desktop
  python -m claude_mpm.services.mcp_gateway.main --stdio
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--stdio",
        action="store_true",
        default=True,
        help="Use stdio for communication (default)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Claude MPM MCP Gateway 1.0.0"
    )
    
    return parser.parse_args()


async def run_global_mcp_gateway(gateway_name: str = "claude-mpm-mcp", version: str = "1.0.0"):
    """
    Run the MCP Gateway using the global manager.

    This ensures only one gateway instance per installation.

    Args:
        gateway_name: Name for the gateway
        version: Gateway version
    """
    logger = get_logger("MCPGatewayMain")

    try:
        logger.info(f"Starting global MCP gateway: {gateway_name}")

        # Start the global gateway
        if not await start_global_gateway(gateway_name, version):
            logger.error("Failed to start global gateway")
            return False

        # Run the gateway
        await run_global_gateway()
        return True

    except Exception as e:
        logger.error(f"Error running global gateway: {e}")
        return False


if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()

    # Run the gateway
    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)