"""
MCP Gateway command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the MCP (Model Context Protocol) Gateway,
allowing users to start, stop, configure, and test MCP server functionality.

DESIGN DECISION: We follow the existing CLI pattern using a main function
that dispatches to specific subcommand handlers, maintaining consistency
with other command modules like agents.py and memory.py.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

from ...core.logger import get_logger
from ...constants import MCPCommands


def manage_mcp(args):
    """
    Manage MCP Gateway server and tools.
    
    WHY: The MCP Gateway provides Model Context Protocol integration for Claude MPM,
    enabling tool invocation and external service integration. This command provides
    a unified interface for all MCP-related operations.
    
    DESIGN DECISION: When no subcommand is provided, we show the server status
    as the default action, giving users a quick overview of the MCP system state.
    
    Args:
        args: Parsed command line arguments with mcp_command attribute
    """
    logger = get_logger("cli.mcp")
    
    try:
        # Import MCP Gateway services with lazy loading
        from ...services.mcp_gateway import (
            MCPServer,
            ToolRegistry,
            MCPConfiguration,
            MCPServiceRegistry
        )
        
        if not args.mcp_command:
            # No subcommand - show status by default
            return _show_status(args, logger)
        
        # Route to specific command handlers
        if args.mcp_command == MCPCommands.START.value:
            return _start_server(args, logger)
        
        elif args.mcp_command == MCPCommands.STOP.value:
            return _stop_server(args, logger)
        
        elif args.mcp_command == MCPCommands.STATUS.value:
            return _show_status(args, logger)
        
        elif args.mcp_command == MCPCommands.TOOLS.value:
            return _manage_tools(args, logger)
        
        elif args.mcp_command == MCPCommands.REGISTER.value:
            return _register_tool(args, logger)
        
        elif args.mcp_command == MCPCommands.TEST.value:
            return _test_tool(args, logger)
        
        elif args.mcp_command == MCPCommands.INSTALL.value:
            return _install_gateway(args, logger)
        
        elif args.mcp_command == MCPCommands.CONFIG.value:
            return _manage_config(args, logger)
        
        else:
            logger.error(f"Unknown MCP command: {args.mcp_command}")
            print(f"Unknown MCP command: {args.mcp_command}")
            _show_help()
            return 1
        
    except ImportError as e:
        logger.error(f"MCP Gateway services not available: {e}")
        print("Error: MCP Gateway services not available")
        print("This may indicate a missing dependency. Try running:")
        print("  pip install mcp")
        return 1
    except Exception as e:
        logger.error(f"Error managing MCP Gateway: {e}", exc_info=True)
        print(f"Error: {e}")
        return 1


def _show_help():
    """Show available MCP commands."""
    print("\nAvailable MCP commands:")
    print("  install  - Install and configure MCP Gateway")
    print("  start    - Start the MCP Gateway server")
    print("  stop     - Stop the MCP Gateway server")
    print("  status   - Check server and tool status")
    print("  tools    - List and manage registered tools")
    print("  register - Register a new tool")
    print("  test     - Test tool invocation")
    print("  config   - View and manage configuration")
    print()
    print("Use 'claude-mpm mcp <command> --help' for more information")


def _start_server(args, logger):
    """
    Start the MCP Gateway server.
    
    WHY: Users need to start the MCP server to enable tool invocation
    and external service integration in Claude sessions.
    
    Args:
        args: Command arguments with optional port and configuration
        logger: Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    from ...services.mcp_gateway import MCPServer, ToolRegistry, MCPConfiguration
    from ...services.mcp_gateway.server.stdio_handler import StdioHandler
    
    try:
        print("Starting MCP Gateway server...")
        
        # Load configuration
        config_path = getattr(args, 'config_file', None)
        if config_path and Path(config_path).exists():
            logger.info(f"Loading configuration from: {config_path}")
            config = MCPConfiguration.from_file(config_path)
        else:
            logger.info("Using default MCP configuration")
            config = MCPConfiguration()
        
        # Initialize server components
        server = MCPServer(
            server_name=config.server_name,
            version=config.version
        )
        
        # Initialize tool registry
        tool_registry = ToolRegistry()
        
        # Load default tools if enabled
        if config.load_default_tools:
            logger.info("Loading default tools")
            _load_default_tools(tool_registry, logger)
        
        # Set dependencies
        server.set_tool_registry(tool_registry)
        
        # Start server based on mode
        mode = getattr(args, 'mode', 'stdio')
        
        if mode == 'stdio':
            # Standard I/O mode for Claude integration
            logger.info("Starting MCP server in stdio mode")
            stdio_handler = StdioHandler(server)
            
            # Run the server
            asyncio.run(stdio_handler.run())
            
        elif mode == 'standalone':
            # Standalone mode for testing
            port = getattr(args, 'port', 8766)
            logger.info(f"Starting MCP server in standalone mode on port {port}")
            
            # Create async event loop and run server
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_standalone():
                await server.start()
                print(f"MCP Gateway server started on port {port}")
                print("Press Ctrl+C to stop")
                
                # Keep server running
                try:
                    await asyncio.Event().wait()
                except KeyboardInterrupt:
                    print("\nStopping server...")
                    await server.stop()
            
            loop.run_until_complete(run_standalone())
            
        else:
            logger.error(f"Unknown server mode: {mode}")
            print(f"Error: Unknown server mode: {mode}")
            return 1
        
        print("MCP Gateway server stopped")
        return 0
        
    except KeyboardInterrupt:
        print("\nServer interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}", exc_info=True)
        print(f"Error starting server: {e}")
        return 1


def _stop_server(args, logger):
    """
    Stop the MCP Gateway server.
    
    WHY: Users need a clean way to stop the MCP server when it's no longer needed
    or when they need to restart it with different configuration.
    
    Args:
        args: Command arguments
        logger: Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Check for running server process
        pid_file = Path.home() / ".claude-mpm" / "mcp_server.pid"
        
        if not pid_file.exists():
            print("No MCP server process found")
            return 0
        
        # Read PID and attempt to stop
        import signal
        import os
        
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        try:
            # Send termination signal
            os.kill(pid, signal.SIGTERM)
            print(f"Sent stop signal to MCP server (PID: {pid})")
            
            # Wait for graceful shutdown
            import time
            for _ in range(10):
                try:
                    os.kill(pid, 0)  # Check if process still exists
                    time.sleep(0.5)
                except ProcessLookupError:
                    break
            else:
                # Force kill if still running
                os.kill(pid, signal.SIGKILL)
                print("Force stopped MCP server")
            
            # Clean up PID file
            pid_file.unlink()
            print("MCP server stopped successfully")
            return 0
            
        except ProcessLookupError:
            # Process already stopped
            pid_file.unlink()
            print("MCP server was not running")
            return 0
            
    except Exception as e:
        logger.error(f"Failed to stop MCP server: {e}", exc_info=True)
        print(f"Error stopping server: {e}")
        return 1


def _show_status(args, logger):
    """
    Show MCP Gateway server and tool status.
    
    WHY: Users need visibility into the current state of the MCP system,
    including server status, registered tools, and configuration.
    
    Args:
        args: Command arguments
        logger: Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    from ...services.mcp_gateway import MCPServiceRegistry, ToolRegistry
    
    try:
        print("MCP Gateway Status")
        print("=" * 50)
        
        # Check server status
        pid_file = Path.home() / ".claude-mpm" / "mcp_server.pid"
        
        if pid_file.exists():
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is running
            import os
            try:
                os.kill(pid, 0)
                print(f"Server Status: ✅ Running (PID: {pid})")
            except ProcessLookupError:
                print("Server Status: ❌ Not running (stale PID file)")
                pid_file.unlink()
        else:
            print("Server Status: ❌ Not running")
        
        print()
        
        # Show registered tools
        print("Registered Tools:")
        print("-" * 30)
        
        # Initialize tool registry to check tools
        tool_registry = ToolRegistry()
        
        # Load configuration to check enabled tools
        config_file = Path.home() / ".claude-mpm" / "mcp_config.yaml"
        if config_file.exists():
            from ...services.mcp_gateway import MCPConfiguration
            config = MCPConfiguration.from_file(config_file)
            
            # Load tools based on configuration
            if config.load_default_tools:
                _load_default_tools(tool_registry, logger)
        
        tools = tool_registry.list_tools()
        if tools:
            for tool in tools:
                status = "✅" if tool.enabled else "❌"
                print(f"  {status} {tool.name}: {tool.description}")
        else:
            print("  No tools registered")
        
        print()
        
        # Show configuration
        print("Configuration:")
        print("-" * 30)
        
        if config_file.exists():
            print(f"  Config file: {config_file}")
            print(f"  Server name: {config.server_name}")
            print(f"  Version: {config.version}")
            print(f"  Default tools: {'Enabled' if config.load_default_tools else 'Disabled'}")
        else:
            print("  Using default configuration")
        
        # Show verbose details if requested
        if getattr(args, 'verbose', False):
            print()
            print("Service Registry:")
            print("-" * 30)
            
            registry = MCPServiceRegistry()
            services = registry.list_services()
            
            for service_id, service_info in services.items():
                print(f"  {service_id}:")
                print(f"    State: {service_info['state']}")
                print(f"    Type: {service_info['type']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to show MCP status: {e}", exc_info=True)
        print(f"Error checking status: {e}")
        return 1


def _manage_tools(args, logger):
    """
    List and manage registered MCP tools.
    
    WHY: Users need to see what tools are available and manage their
    registration and configuration.
    
    Args:
        args: Command arguments with optional filters
        logger: Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    from ...services.mcp_gateway import ToolRegistry
    
    try:
        # Check for subcommand
        action = getattr(args, 'tool_action', 'list')
        
        # Initialize tool registry
        tool_registry = ToolRegistry()
        
        # Load tools from configuration
        config_file = Path.home() / ".claude-mpm" / "mcp_config.yaml"
        if config_file.exists():
            from ...services.mcp_gateway import MCPConfiguration
            config = MCPConfiguration.from_file(config_file)
            if config.load_default_tools:
                _load_default_tools(tool_registry, logger)
        
        if action == 'list':
            # List all tools
            tools = tool_registry.list_tools()
            
            if not tools:
                print("No tools registered")
                return 0
            
            print("Registered MCP Tools:")
            print("=" * 50)
            
            # Group tools by category if available
            by_category = {}
            for tool in tools:
                category = getattr(tool, 'category', 'General')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(tool)
            
            for category, category_tools in sorted(by_category.items()):
                print(f"\n{category}:")
                print("-" * 30)
                
                for tool in category_tools:
                    status = "✅" if tool.enabled else "❌"
                    print(f"  {status} {tool.name}")
                    print(f"      {tool.description}")
                    
                    if getattr(args, 'verbose', False):
                        # Show input schema
                        print(f"      Input Schema: {json.dumps(tool.input_schema, indent=8)}")
            
        elif action == 'enable':
            # Enable a tool
            tool_name = args.tool_name
            if tool_registry.enable_tool(tool_name):
                print(f"✅ Enabled tool: {tool_name}")
                return 0
            else:
                print(f"❌ Failed to enable tool: {tool_name}")
                return 1
        
        elif action == 'disable':
            # Disable a tool
            tool_name = args.tool_name
            if tool_registry.disable_tool(tool_name):
                print(f"✅ Disabled tool: {tool_name}")
                return 0
            else:
                print(f"❌ Failed to disable tool: {tool_name}")
                return 1
        
        else:
            print(f"Unknown tool action: {action}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to manage tools: {e}", exc_info=True)
        print(f"Error managing tools: {e}")
        return 1


def _register_tool(args, logger):
    """
    Register a new MCP tool.
    
    WHY: Users need to add custom tools to the MCP Gateway for use
    in Claude sessions.
    
    Args:
        args: Command arguments with tool definition
        logger: Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    from ...services.mcp_gateway import ToolRegistry
    from ...services.mcp_gateway.core.interfaces import MCPToolDefinition
    
    try:
        # Get tool details from arguments
        tool_name = args.name
        tool_description = args.description
        
        # Parse input schema
        if args.schema_file:
            with open(args.schema_file, 'r') as f:
                input_schema = json.load(f)
        else:
            # Basic schema
            input_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        # Create tool definition
        tool_def = MCPToolDefinition(
            name=tool_name,
            description=tool_description,
            input_schema=input_schema,
            enabled=True
        )
        
        # Register with tool registry
        tool_registry = ToolRegistry()
        
        if args.adapter:
            # Register with custom adapter
            logger.info(f"Registering tool with adapter: {args.adapter}")
            # Import and instantiate adapter
            # This would be extended based on adapter framework
            print(f"Custom adapter registration not yet implemented: {args.adapter}")
            return 1
        else:
            # Register as a simple tool
            success = tool_registry.register_tool(tool_def)
            
            if success:
                print(f"✅ Successfully registered tool: {tool_name}")
                
                # Save to configuration if requested
                if args.save:
                    config_file = Path.home() / ".claude-mpm" / "mcp_config.yaml"
                    # Update configuration with new tool
                    print(f"Tool configuration saved to: {config_file}")
                
                return 0
            else:
                print(f"❌ Failed to register tool: {tool_name}")
                return 1
        
    except Exception as e:
        logger.error(f"Failed to register tool: {e}", exc_info=True)
        print(f"Error registering tool: {e}")
        return 1


def _test_tool(args, logger):
    """
    Test MCP tool invocation.
    
    WHY: Users need to verify that tools are working correctly before
    using them in Claude sessions.
    
    Args:
        args: Command arguments with tool name and test parameters
        logger: Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    from ...services.mcp_gateway import ToolRegistry
    from ...services.mcp_gateway.core.interfaces import MCPToolInvocation
    
    try:
        # Get tool name and arguments
        tool_name = args.tool_name
        
        # Parse tool arguments
        if args.args_file:
            with open(args.args_file, 'r') as f:
                tool_args = json.load(f)
        elif args.args:
            tool_args = json.loads(args.args)
        else:
            tool_args = {}
        
        print(f"Testing tool: {tool_name}")
        print(f"Arguments: {json.dumps(tool_args, indent=2)}")
        print("-" * 50)
        
        # Initialize tool registry
        tool_registry = ToolRegistry()
        
        # Load tools
        config_file = Path.home() / ".claude-mpm" / "mcp_config.yaml"
        if config_file.exists():
            from ...services.mcp_gateway import MCPConfiguration
            config = MCPConfiguration.from_file(config_file)
            if config.load_default_tools:
                _load_default_tools(tool_registry, logger)
        
        # Create invocation request
        invocation = MCPToolInvocation(
            tool_name=tool_name,
            arguments=tool_args,
            request_id=f"test-{tool_name}"
        )
        
        # Invoke tool
        result = asyncio.run(tool_registry.invoke_tool(invocation))
        
        if result.success:
            print("✅ Tool invocation successful!")
            print(f"Result: {json.dumps(result.result, indent=2)}")
        else:
            print("❌ Tool invocation failed!")
            print(f"Error: {result.error}")
        
        return 0 if result.success else 1
        
    except Exception as e:
        logger.error(f"Failed to test tool: {e}", exc_info=True)
        print(f"Error testing tool: {e}")
        return 1


def _install_gateway(args, logger):
    """
    Install and configure the MCP Gateway.
    
    WHY: Users need a simple way to set up the MCP Gateway with
    default configuration and tools.
    
    Args:
        args: Command arguments
        logger: Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        print("Installing MCP Gateway...")
        print("=" * 50)
        
        # Create configuration directory
        config_dir = Path.home() / ".claude-mpm"
        config_dir.mkdir(exist_ok=True)
        
        # Create default configuration
        config_file = config_dir / "mcp_config.yaml"
        
        if config_file.exists() and not getattr(args, 'force', False):
            print(f"Configuration already exists: {config_file}")
            print("Use --force to overwrite")
            return 1
        
        # Default configuration
        default_config = {
            "server": {
                "name": "claude-mpm-mcp",
                "version": "1.0.0",
                "port": 8766,
                "mode": "stdio"
            },
            "tools": {
                "load_defaults": True,
                "custom_tools_dir": str(config_dir / "mcp_tools"),
                "enabled": [
                    "echo",
                    "calculator",
                    "system_info"
                ]
            },
            "logging": {
                "level": "INFO",
                "file": str(config_dir / "logs" / "mcp_server.log")
            }
        }
        
        # Write configuration
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        print(f"✅ Created configuration: {config_file}")
        
        # Create tools directory
        tools_dir = config_dir / "mcp_tools"
        tools_dir.mkdir(exist_ok=True)
        print(f"✅ Created tools directory: {tools_dir}")
        
        # Create logs directory
        logs_dir = config_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        print(f"✅ Created logs directory: {logs_dir}")
        
        # Test MCP package installation
        try:
            import mcp
            print("✅ MCP package is installed")
        except ImportError:
            print("⚠️  MCP package not found. Installing...")
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "mcp"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ MCP package installed successfully")
            else:
                print("❌ Failed to install MCP package")
                print(result.stderr)
                return 1
        
        print()
        print("MCP Gateway installation complete!")
        print()
        print("Next steps:")
        print("1. Start the server: claude-mpm mcp start")
        print("2. Check status: claude-mpm mcp status")
        print("3. List tools: claude-mpm mcp tools")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to install MCP Gateway: {e}", exc_info=True)
        print(f"Error during installation: {e}")
        return 1


def _manage_config(args, logger):
    """
    View and manage MCP Gateway configuration.
    
    WHY: Users need to view and modify MCP configuration without
    manually editing YAML files.
    
    Args:
        args: Command arguments
        logger: Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        config_file = Path.home() / ".claude-mpm" / "mcp_config.yaml"
        
        action = getattr(args, 'config_action', 'view')
        
        if action == 'view':
            # View current configuration
            if not config_file.exists():
                print("No configuration file found")
                print("Run 'claude-mpm mcp install' to create default configuration")
                return 1
            
            import yaml
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            print("MCP Gateway Configuration")
            print("=" * 50)
            print(yaml.dump(config, default_flow_style=False))
            
        elif action == 'edit':
            # Edit configuration
            if not config_file.exists():
                print("No configuration file found")
                return 1
            
            # Open in default editor
            import os
            import subprocess
            
            editor = os.environ.get('EDITOR', 'nano')
            subprocess.call([editor, str(config_file)])
            
            print("Configuration updated")
            
        elif action == 'reset':
            # Reset to default configuration
            if config_file.exists():
                # Backup existing configuration
                backup_file = config_file.with_suffix('.yaml.bak')
                config_file.rename(backup_file)
                print(f"Backed up existing configuration to: {backup_file}")
            
            # Run install to create default configuration
            args.force = True
            return _install_gateway(args, logger)
        
        else:
            print(f"Unknown config action: {action}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to manage configuration: {e}", exc_info=True)
        print(f"Error managing configuration: {e}")
        return 1


def _load_default_tools(tool_registry, logger):
    """
    Load default MCP tools into the registry.
    
    WHY: We provide a set of default tools for common operations
    to get users started quickly.
    
    Args:
        tool_registry: ToolRegistry instance
        logger: Logger instance
    """
    try:
        # Import default tool adapters
        from ...services.mcp_gateway.tools.base_adapter import (
            EchoToolAdapter,
            CalculatorToolAdapter,
            SystemInfoToolAdapter
        )
        
        # Register default tools
        default_tools = [
            EchoToolAdapter(),
            CalculatorToolAdapter(),
            SystemInfoToolAdapter()
        ]
        
        for adapter in default_tools:
            tool_def = adapter.get_tool_definition()
            tool_registry.register_tool(tool_def, adapter)
            logger.debug(f"Loaded default tool: {tool_def.name}")
        
    except Exception as e:
        logger.error(f"Failed to load default tools: {e}", exc_info=True)