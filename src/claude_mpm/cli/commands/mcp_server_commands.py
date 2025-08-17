"""MCP server command implementations.

This module provides MCP server management commands.
Extracted from mcp.py to reduce complexity and improve maintainability.
"""

import asyncio
import sys
import subprocess
from pathlib import Path


class MCPServerCommands:
    """Handles MCP server commands."""
    
    def __init__(self, logger):
        """Initialize the MCP server commands handler."""
        self.logger = logger
    
    async def start_server(self, args):
        """Start MCP server command.
        
        WHY: This command starts the MCP server using the proper stdio-based
        implementation that Claude Desktop/Code can communicate with.
        
        DESIGN DECISION: When called without flags, we run the server directly
        for Claude Code compatibility. With --instructions flag, we show setup info.
        """
        self.logger.info("MCP server start command called")
        
        # Check if we're being called by Claude Code (no special flags)
        show_instructions = getattr(args, 'instructions', False)
        test_mode = getattr(args, 'test', False)
        daemon_mode = getattr(args, 'daemon', False)
        
        if daemon_mode:
            # Daemon mode - not recommended for MCP
            print("⚠️  MCP servers are designed to be spawned by Claude Desktop/Code")
            print("   Running as a daemon is not recommended.")
            return 1
        
        if show_instructions:
            # Show configuration instructions
            print("🚀 MCP Server Setup Instructions")
            print("=" * 50)
            print("\nThe MCP server is designed to be spawned by Claude Desktop/Code.")
            print("\nTo use the MCP server with Claude Desktop:")
            print("\n1. Add this to your Claude Desktop configuration:")
            print("   (usually at ~/Library/Application Support/Claude/claude_desktop_config.json on macOS)")
            print("\n{")
            print('  "mcpServers": {')
            print('    "claude-mpm": {')
            
            # Find the correct binary path
            bin_path = Path(sys.executable).parent / "claude-mpm-mcp"
            if not bin_path.exists():
                # Try to find it in the project bin directory
                project_root = Path(__file__).parent.parent.parent.parent.parent
                bin_path = project_root / "bin" / "claude-mpm-mcp"
            
            if bin_path.exists():
                print(f'      "command": "{bin_path}"')
            else:
                print('      "command": "claude-mpm-mcp"')
                print('      // Or use the full path if not in PATH:')
                print('      // "command": "/path/to/claude-mpm/bin/claude-mpm-mcp"')
            
            print('    }')
            print('  }')
            print('}')
            print("\n2. Restart Claude Desktop to load the MCP server")
            print("\n3. The server will be automatically started when needed")
            print("\nFor Claude Code, the configuration is usually automatic.")
            print("\nTo test the server directly, run:")
            print("  claude-mpm mcp start --test")
            print("\nFor more information, see:")
            print("  https://github.com/anthropics/mcp")
            
            return 0
        
        # Default behavior: Run the server directly (for Claude Code compatibility)
        # When Claude Code spawns "claude-mpm mcp start", it expects the server to run
        if test_mode:
            print("🧪 Starting MCP server in test mode...")
            print("   This will run the server with stdio communication.")
            print("   Press Ctrl+C to stop.\n")
        
        try:
            # Configure logging to stderr for MCP mode
            import logging
            import sys
            
            # Disable all stdout logging when running MCP server
            # to prevent interference with JSON-RPC protocol
            root_logger = logging.getLogger()
            
            # Remove any existing handlers that might log to stdout
            for handler in root_logger.handlers[:]:
                if hasattr(handler, 'stream') and handler.stream == sys.stdout:
                    root_logger.removeHandler(handler)
            
            # Add stderr handler if needed (but keep it minimal)
            if not test_mode:
                # In production mode, minimize stderr output too
                logging.basicConfig(
                    level=logging.ERROR,
                    format='%(message)s',
                    stream=sys.stderr,
                    force=True
                )
            else:
                # In test mode, allow more verbose stderr logging
                logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stderr,
                    force=True
                )
            
            # Import and run the stdio server directly
            from ...services.mcp_gateway.server.stdio_server import SimpleMCPServer
            
            server = SimpleMCPServer(
                name="claude-mpm-gateway",
                version="1.0.0"
            )
            
            # Run the server (handles stdio communication)
            await server.run()
            return 0
            
        except ImportError as e:
            self.logger.error(f"Failed to import MCP server: {e}")
            # Don't print to stdout as it would interfere with JSON-RPC protocol
            # Log to stderr instead
            import sys
            print(f"❌ Error: Could not import MCP server components: {e}", file=sys.stderr)
            print("\nMake sure the MCP package is installed:", file=sys.stderr)
            print("  pip install mcp", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            # Graceful shutdown
            self.logger.info("MCP server interrupted")
            return 0
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            import sys
            print(f"❌ Error running server: {e}", file=sys.stderr)
            return 1
    
    def stop_server(self, args):
        """Stop MCP server command."""
        self.logger.info("MCP server stop command called")
        print("🛑 MCP server stop functionality has been simplified")
        print("   This command is now a placeholder - full implementation needed")
        return 0
    
    def show_status(self, args):
        """Show MCP server status command."""
        self.logger.info("MCP server status command called")
        print("📊 MCP server status functionality has been simplified")
        print("   This command is now a placeholder - full implementation needed")
        return 0
    
    def cleanup_locks(self, args):
        """Cleanup MCP server locks command."""
        self.logger.info("MCP server cleanup locks command called")
        print("🧹 MCP server cleanup locks functionality has been simplified")
        print("   This command is now a placeholder - full implementation needed")
        return 0
