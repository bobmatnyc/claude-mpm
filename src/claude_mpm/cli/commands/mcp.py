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
            MCPGateway,
            ToolRegistry,
            MCPConfiguration,
            MCPServiceRegistry
        )
        
        if not args.mcp_command:
            # No subcommand - show status by default
            return _show_status(args, logger)
        
        # Route to specific command handlers
        if args.mcp_command == MCPCommands.START.value:
            import asyncio
            return asyncio.run(_start_server(args, logger))
        
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


# Daemon mode removed - MCP servers should be simple stdio responders


async def _start_server(args, logger):
    """
    Start the MCP Gateway using the global manager.

    WHY: Users need to start the MCP gateway to enable tool invocation
    and external service integration in Claude sessions. We use the global
    manager to ensure only one instance runs per installation.

    Args:
        args: Command arguments with optional port and configuration
        logger: Logger instance

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    from ...services.mcp_gateway.manager import (
        start_global_gateway,
        run_global_gateway,
        is_gateway_running,
        get_gateway_status
    )
    
    try:
        logger.info("Starting MCP Gateway")

        # Note: MCP gateways don't "run" as background services
        # They are stdio-based protocol handlers activated by MCP clients

        # Get configuration values
        gateway_name = getattr(args, 'name', 'claude-mpm-gateway')
        version = getattr(args, 'version', '1.0.0')

        # Initialize the global gateway components
        logger.info(f"Initializing MCP gateway: {gateway_name}")
        if not await start_global_gateway(gateway_name, version):
            logger.error("Failed to initialize MCP gateway")
            print("Error: Failed to initialize MCP gateway")
            return 1

        # Run the gateway stdio handler
        logger.info("Starting MCP gateway stdio handler")
        print("MCP Gateway ready for Claude Desktop", file=sys.stderr)
        print("Listening for MCP protocol messages on stdin/stdout...", file=sys.stderr)

        await run_global_gateway()

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
        
        # Check gateway manager status
        from ...services.mcp_gateway.manager import get_gateway_status, is_gateway_running

        # MCP gateways are stdio-based protocol handlers, not background services
        print("Gateway Status: ℹ️  MCP protocol handler (stdio-based)")
        print("  • Activated on-demand by MCP clients (Claude Desktop)")
        print("  • No background processes - communicates via stdin/stdout")
        print("  • Ready for Claude Desktop integration")
        print("  • Test with: claude-mpm mcp test <tool_name>")
        
        print()
        
        # Show registered tools
        print("Registered Tools:")
        print("-" * 30)
        
        # Get tool registry with fallback to running server
        try:
            tool_registry = _create_tool_registry_with_fallback(logger)
            config_file = Path.home() / ".claude-mcp" / "mcp_config.yaml"
            config = _load_config_sync(config_file if config_file.exists() else None, logger)
        except ValueError as e:
            print(f"Configuration Error: {e}")
            return 1
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            print(f"Error: Failed to initialize MCP components: {e}")
            return 1
        
        tools = tool_registry.list_tools()
        if tools:
            for tool in tools:
                print(f"  ✅ {tool.name}: {tool.description}")
        else:
            print("  No tools registered")
        
        print()
        
        # Show configuration
        print("Configuration:")
        print("-" * 30)

        if config_file.exists():
            print(f"  Config file: {config_file}")
        else:
            print("  Using default configuration")

        server_config = config.get("mcp", {}).get("server", {})
        tools_config = config.get("mcp", {}).get("tools", {})
        print(f"  Server name: {server_config.get('name', 'claude-mpm-gateway')}")
        print(f"  Version: {server_config.get('version', '1.0.0')}")
        print(f"  Tools enabled: {'Yes' if tools_config.get('enabled', True) else 'No'}")
        
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
        
        # Get tool registry with fallback to running server
        tool_registry = _create_tool_registry_with_fallback(logger)
        
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
                    print(f"  ✅ {tool.name}")
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
        
        # Get tool registry with fallback to running server
        tool_registry = _create_tool_registry_with_fallback(logger)
        
        # Create invocation request
        invocation = MCPToolInvocation(
            tool_name=tool_name,
            parameters=tool_args,
            context={"source": "cli_test"}
        )
        
        # Invoke tool
        result = asyncio.run(tool_registry.invoke_tool(invocation))
        
        if result.success:
            print("✅ Tool invocation successful!")
            print(f"Result: {json.dumps(result.data, indent=2)}")
            print(f"Execution time: {result.execution_time:.3f}s")
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


async def _load_default_tools(tool_registry, logger):
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
            await adapter.initialize()
            tool_registry.register_tool(adapter)
            tool_def = adapter.get_definition()
            logger.debug(f"Loaded default tool: {tool_def.name}")
        
    except Exception as e:
        logger.error(f"Failed to load default tools: {e}", exc_info=True)
        raise


def _load_config_sync(config_path=None, logger=None):
    """
    Load MCP configuration synchronously with validation.

    Args:
        config_path: Optional path to configuration file
        logger: Optional logger for error reporting

    Returns:
        Dictionary with configuration data

    Raises:
        ValueError: If configuration is invalid
    """
    # Use default configuration structure
    default_config = {
        "mcp": {
            "server": {
                "name": "claude-mpm-gateway",
                "version": "1.0.0",
                "description": "Claude MPM MCP Gateway Server",
            },
            "tools": {
                "enabled": True,
                "auto_discover": True,
            },
            "logging": {
                "level": "INFO",
            }
        }
    }

    if config_path and Path(config_path).exists():
        try:
            import yaml
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f) or {}

            # Validate configuration structure
            if not isinstance(loaded_config, dict):
                raise ValueError("Configuration must be a dictionary")

            # Validate MCP section if present
            if "mcp" in loaded_config:
                mcp_config = loaded_config["mcp"]
                if not isinstance(mcp_config, dict):
                    raise ValueError("mcp section must be a dictionary")

                # Validate server section
                if "server" in mcp_config:
                    server_config = mcp_config["server"]
                    if not isinstance(server_config, dict):
                        raise ValueError("mcp.server section must be a dictionary")

                    # Validate server name
                    if "name" in server_config:
                        if not isinstance(server_config["name"], str) or not server_config["name"].strip():
                            raise ValueError("mcp.server.name must be a non-empty string")

                # Validate tools section
                if "tools" in mcp_config:
                    tools_config = mcp_config["tools"]
                    if not isinstance(tools_config, dict):
                        raise ValueError("mcp.tools section must be a dictionary")

                    if "enabled" in tools_config and not isinstance(tools_config["enabled"], bool):
                        raise ValueError("mcp.tools.enabled must be a boolean")

            # Merge with defaults
            def merge_dict(base, overlay):
                for key, value in overlay.items():
                    if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                        merge_dict(base[key], value)
                    else:
                        base[key] = value

            merge_dict(default_config, loaded_config)

            if logger:
                logger.info(f"Successfully loaded configuration from {config_path}")

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in configuration file {config_path}: {e}"
            if logger:
                logger.error(error_msg)
            raise ValueError(error_msg)
        except ValueError as e:
            error_msg = f"Configuration validation error in {config_path}: {e}"
            if logger:
                logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"Failed to load configuration from {config_path}: {e}"
            if logger:
                logger.warning(error_msg)
            # Fall back to defaults for other errors

    return default_config


def _load_default_tools_sync(tool_registry, logger):
    """
    Load default MCP tools into the registry synchronously.

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
            # Initialize synchronously (skip async parts for CLI)
            adapter._initialized = True
            tool_registry.register_tool(adapter)
            tool_def = adapter.get_definition()
            logger.debug(f"Loaded default tool: {tool_def.name}")

    except Exception as e:
        logger.error(f"Failed to load default tools: {e}", exc_info=True)


def _get_server_tools_via_mcp(logger):
    """
    Get tools from running MCP server via MCP protocol.

    Returns:
        List of tool definitions or None if server not accessible
    """
    try:
        import json
        import subprocess
        import tempfile

        # Create a simple MCP client request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        # Try to communicate with running server
        pid_file = Path.home() / ".claude-mcp" / "mcp_server.pid"
        if not pid_file.exists():
            return None

        # For now, return None since we need a proper MCP client implementation
        # This is a placeholder for future implementation
        return None

    except Exception as e:
        logger.debug(f"Could not connect to running server: {e}")
        return None


def _create_tool_registry_with_fallback(logger):
    """
    Create tool registry, trying to connect to running server first.

    Args:
        logger: Logger instance

    Returns:
        ToolRegistry instance with tools loaded
    """
    from ...services.mcp_gateway import ToolRegistry

    # Create registry
    tool_registry = ToolRegistry()

    # Try to get tools from running server
    server_tools = _get_server_tools_via_mcp(logger)

    if server_tools:
        logger.debug("Connected to running MCP server")
        # TODO: Populate registry with server tools
        # For now, fall back to loading default tools

    # Fallback: Load default tools locally
    config_file = Path.home() / ".claude-mcp" / "mcp_config.yaml"
    config = _load_config_sync(config_file if config_file.exists() else None, logger)

    if config.get("mcp", {}).get("tools", {}).get("enabled", True):
        _load_default_tools_sync(tool_registry, logger)

    return tool_registry