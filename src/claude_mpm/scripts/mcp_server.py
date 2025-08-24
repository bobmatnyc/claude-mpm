#!/usr/bin/env python3
"""MCP Server launcher script for Claude Code.

This script launches the MCP gateway server for Claude Code integration.
It handles proper Python path setup and error reporting to stderr.
"""

import logging
import os
import sys

# Since we're now in src/claude_mpm/scripts/, we need to go up 3 levels to reach the project root
# Then down into src to add it to the path
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
sys.path.insert(0, os.path.join(project_root, "src"))


def setup_logging():
    """Configure logging to stderr to avoid interfering with stdio protocol."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


def main():
    """Main entry point for the MCP server launcher."""
    try:
        # Setup logging first
        setup_logging()
        logger = logging.getLogger("MCPLauncher")

        # Import modules after path setup
        try:
            import asyncio

            from claude_mpm.services.mcp_gateway.server.stdio_server import (
                SimpleMCPServer,
            )
        except ImportError as e:
            logger.error(f"Failed to import required modules: {e}")
            logger.error("Make sure claude-mpm is properly installed")
            sys.exit(1)

        # Create and run server
        logger.info("Starting MCP Gateway Server...")

        async def run_server():
            """Async function to run the server."""
            try:
                server = SimpleMCPServer(name="claude-mpm-gateway", version="1.0.0")
                await server.run()
            except Exception as e:
                logger.error(f"Server runtime error: {e}")
                raise

        # Run the async server
        asyncio.run(run_server())

    except KeyboardInterrupt:
        # Clean shutdown on Ctrl+C
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        # Log any unexpected errors
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
