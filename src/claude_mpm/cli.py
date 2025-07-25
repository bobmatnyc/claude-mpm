"""Command-line interface for Claude MPM."""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    # Try relative imports first (when used as package)
    from ._version import __version__
    from .core.logger import get_logger, setup_logging
    from .services.json_rpc_hook_manager import JSONRPCHookManager
    from .constants import CLICommands, CLIPrefix, AgentCommands, LogLevel, CLIFlags
except ImportError:
    # Fall back to absolute imports (when run directly)
    from claude_mpm._version import __version__
    from core.logger import get_logger, setup_logging
    from services.json_rpc_hook_manager import JSONRPCHookManager
    from constants import CLICommands, CLIPrefix, AgentCommands, LogLevel, CLIFlags


def main(argv: Optional[list] = None):
    """Main CLI entry point."""
    # Ensure directories are initialized on first run
    try:
        from .init import ensure_directories
        ensure_directories()
    except Exception:
        # Continue even if initialization fails
        pass
    
    parser = argparse.ArgumentParser(
        prog="claude-mpm",
        description=f"Claude Multi-Agent Project Manager v{__version__} - Orchestrate Claude with agent delegation and ticket tracking",
        epilog="By default, runs an orchestrated Claude session. Use 'claude-mpm' for interactive mode or 'claude-mpm -i \"prompt\"' for non-interactive mode."
    )
    
    # Version
    parser.add_argument(
        "--version",
        action="version",
        version=f"claude-mpm {__version__}"
    )
    
    # Global options
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging (deprecated, use --logging DEBUG)"
    )
    
    parser.add_argument(
        "--logging",
        choices=[level.value for level in LogLevel],
        default=LogLevel.OFF.value,
        help="Logging level (default: OFF)"
    )
    
    parser.add_argument(
        "--log-dir",
        type=Path,
        help="Custom log directory (default: ~/.claude-mpm/logs)"
    )
    
    parser.add_argument(
        "--framework-path",
        type=Path,
        help="Path to claude-mpm framework"
    )
    
    parser.add_argument(
        "--agents-dir",
        type=Path,
        help="Custom agents directory to use"
    )
    
    parser.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable hook service (runs without hooks)"
    )
    
    # Add run-specific arguments at top level (for default behavior)
    parser.add_argument(
        "--no-tickets",
        action="store_true",
        help="Disable automatic ticket creation"
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input text or file path (for non-interactive mode)"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)"
    )
    parser.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents"
    )
    
    # Commands (prefixed with --mpm:)
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command (default) - duplicate args for explicit 'run' command
    run_parser = subparsers.add_parser(CLICommands.RUN.with_prefix(), help="Run orchestrated Claude session (default)")
    run_parser.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable hook service (runs without hooks)"
    )
    run_parser.add_argument(
        "--no-tickets",
        action="store_true",
        help="Disable automatic ticket creation"
    )
    run_parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input text or file path (for non-interactive mode)"
    )
    run_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)"
    )
    run_parser.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents"
    )
    
    # List tickets command
    list_parser = subparsers.add_parser(CLICommands.TICKETS.with_prefix(), help="List recent tickets")
    list_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="Number of tickets to show"
    )
    
    # Info command
    info_parser = subparsers.add_parser(CLICommands.INFO.with_prefix(), help="Show framework and configuration info")
    
    # UI command
    ui_parser = subparsers.add_parser("--mpm:ui", help="Launch terminal UI with multiple panes")
    ui_parser.add_argument(
        "--mode",
        choices=["terminal", "curses"],
        default="terminal",
        help="UI mode to launch (default: terminal)"
    )
    
    # Agent management commands
    agents_parser = subparsers.add_parser(CLICommands.AGENTS.with_prefix(), help="Manage Claude Code native agents")
    agents_subparsers = agents_parser.add_subparsers(dest="agents_command", help="Agent commands")
    
    # List agents
    list_agents_parser = agents_subparsers.add_parser(AgentCommands.LIST.value, help="List available agents")
    list_agents_parser.add_argument(
        "--system",
        action="store_true",
        help="List system agents"
    )
    list_agents_parser.add_argument(
        "--deployed",
        action="store_true", 
        help="List deployed agents"
    )
    
    # Deploy agents
    deploy_agents_parser = agents_subparsers.add_parser(AgentCommands.DEPLOY.value, help="Deploy system agents")
    deploy_agents_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/agents/)"
    )
    
    # Force deploy agents
    force_deploy_parser = agents_subparsers.add_parser(AgentCommands.FORCE_DEPLOY.value, help="Force deploy all system agents")
    force_deploy_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/agents/)"
    )
    
    # Clean agents
    clean_agents_parser = agents_subparsers.add_parser(AgentCommands.CLEAN.value, help="Remove deployed system agents")
    clean_agents_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/)"
    )
    
    # Parse arguments
    args = parser.parse_args(argv)
    
    # Debug: Print parsed args
    if hasattr(args, 'debug') and args.debug:
        print(f"DEBUG: Parsed args: {args}")
    
    # Set up logging first
    # Handle deprecated --debug flag
    if args.debug and args.logging == LogLevel.OFF.value:
        args.logging = LogLevel.DEBUG.value
    
    # Only setup logging if not OFF
    if args.logging != LogLevel.OFF.value:
        logger = setup_logging(level=args.logging, log_dir=args.log_dir)
    else:
        # Minimal logger for CLI feedback
        import logging
        logger = logging.getLogger("cli")
        logger.setLevel(logging.WARNING)
    
    # Initialize hook service manager (unless disabled)
    hook_manager = None
    if not getattr(args, 'no_hooks', False):
        try:
            # Check if hooks are enabled via config
            try:
                from .config.hook_config import HookConfig
            except ImportError:
                from config.hook_config import HookConfig
            if HookConfig.is_hooks_enabled():
                hook_manager = JSONRPCHookManager(log_dir=args.log_dir)
                if hook_manager.start_service():
                    logger.info("JSON-RPC hook system initialized")
                    if args.logging != LogLevel.OFF.value:
                        print("✓ JSON-RPC hook system initialized")
                else:
                    logger.warning("Failed to initialize JSON-RPC hooks, continuing without hooks")
                    if args.logging != LogLevel.OFF.value:
                        print("⚠️  Failed to initialize JSON-RPC hooks, continuing without hooks")
                    hook_manager = None
            else:
                logger.info("Hooks disabled via configuration")
        except Exception as e:
            logger.warning(f"Hook service initialization failed: {e}, continuing without hooks")
            hook_manager = None
    
    # Default to run command
    if not args.command:
        args.command = CLICommands.RUN.with_prefix()
        # Also set default arguments for run command when no subcommand specified
        args.no_tickets = getattr(args, 'no_tickets', False)
        args.no_hooks = getattr(args, 'no_hooks', False)
        args.input = getattr(args, 'input', None)
        args.non_interactive = getattr(args, 'non_interactive', False)
    
    # Debug output
    logger.debug(f"Command: {args.command}")
    logger.debug(f"Arguments: {args}")
    
    # Execute command
    try:
        if args.command == CLICommands.RUN.with_prefix():
            run_session(args, hook_manager)
        elif args.command == CLICommands.TICKETS.with_prefix():
            list_tickets(args)
        elif args.command == CLICommands.INFO.with_prefix():
            show_info(args, hook_manager)
        elif args.command == CLICommands.AGENTS.with_prefix():
            manage_agents(args)
        elif args.command == "--mpm:ui":
            run_terminal_ui(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        logger.info("Session interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        # Clean up hook service
        if hook_manager:
            hook_manager.stop_service()
    
    return 0


def _get_user_input(args, logger):
    """Get user input based on args."""
    if args.input:
        # Read from file or use as direct input
        input_path = Path(args.input)
        if input_path.exists():
            logger.info(f"Reading input from file: {input_path}")
            return input_path.read_text()
        else:
            logger.info("Using command line input")
            return args.input
    else:
        # Read from stdin
        logger.info("Reading input from stdin")
        return sys.stdin.read()




def run_session(args, hook_manager=None):
    """Run a simplified Claude session."""
    logger = get_logger("cli")
    if args.logging != LogLevel.OFF.value:
        logger.info("Starting Claude MPM session")
    
    try:
        from .core.simple_runner import SimpleClaudeRunner, create_simple_context
    except ImportError:
        from core.simple_runner import SimpleClaudeRunner, create_simple_context
    
    # Skip native agents if disabled
    if getattr(args, 'no_native_agents', False):
        print("Native agents disabled")
    
    # Create simple runner
    enable_tickets = not args.no_tickets
    runner = SimpleClaudeRunner(enable_tickets=enable_tickets, log_level=args.logging)
    
    # Create basic context
    context = create_simple_context()
    
    # Run session based on mode
    if args.non_interactive or args.input:
        user_input = _get_user_input(args, logger)
        success = runner.run_oneshot(user_input, context)
        if not success:
            logger.error("Session failed")
    else:
        # Run interactive session
        runner.run_interactive(context)


def list_tickets(args):
    """List recent tickets."""
    logger = get_logger("cli")
    
    try:
        try:
            from .services.ticket_manager import TicketManager
        except ImportError:
            from services.ticket_manager import TicketManager
        
        ticket_manager = TicketManager()
        tickets = ticket_manager.list_recent_tickets(limit=args.limit)
        
        if not tickets:
            print("No tickets found")
            return
        
        print(f"Recent tickets (showing {len(tickets)}):")
        print("-" * 80)
        
        for ticket in tickets:
            status_emoji = {
                "open": "🔵",
                "in_progress": "🟡",
                "done": "🟢",
                "closed": "⚫"
            }.get(ticket['status'], "⚪")
            
            print(f"{status_emoji} [{ticket['id']}] {ticket['title']}")
            print(f"   Priority: {ticket['priority']} | Tags: {', '.join(ticket['tags'])}")
            print(f"   Created: {ticket['created_at']}")
            print()
            
    except ImportError:
        logger.error("ai-trackdown-pytools not installed")
        print("Error: ai-trackdown-pytools not installed")
        print("Install with: pip install ai-trackdown-pytools")
    except Exception as e:
        logger.error(f"Error listing tickets: {e}")
        print(f"Error: {e}")


def manage_agents(args):
    """Manage Claude Code native agents."""
    logger = get_logger("cli")
    
    try:
        from .services.agent_deployment import AgentDeploymentService
        deployment_service = AgentDeploymentService()
        
        if not args.agents_command:
            print("Error: No agent command specified")
            print("\nUsage: claude-mpm --mpm:agents <command> [options]")
            print("\nAvailable commands:")
            print("  list          - List available agents")
            print("  deploy        - Deploy system agents")
            print("  force-deploy  - Force deploy all system agents")
            print("  clean         - Remove deployed system agents")
            print("\nExamples:")
            print("  claude-mpm --mpm:agents list --system")
            print("  claude-mpm --mpm:agents deploy")
            print("  claude-mpm --mpm:agents force-deploy")
            return
        
        if args.agents_command == AgentCommands.LIST.value:
            # Determine what to list
            if args.system:
                # List available agent templates
                print("Available Agent Templates:")
                print("-" * 80)
                agents = deployment_service.list_available_agents()
                if not agents:
                    print("No agent templates found")
                else:
                    for agent in agents:
                        print(f"📄 {agent['file']}")
                        if 'name' in agent:
                            print(f"   Name: {agent['name']}")
                        if 'description' in agent:
                            print(f"   Description: {agent['description']}")
                        if 'version' in agent:
                            print(f"   Version: {agent['version']}")
                        print()
            
            elif args.deployed:
                # List deployed agents
                print("Deployed Agents:")
                print("-" * 80)
                verification = deployment_service.verify_deployment()
                if not verification["agents_found"]:
                    print("No deployed agents found")
                else:
                    for agent in verification["agents_found"]:
                        print(f"📄 {agent['file']}")
                        if 'name' in agent:
                            print(f"   Name: {agent['name']}")
                        print(f"   Path: {agent['path']}")
                        print()
                
                if verification["warnings"]:
                    print("\nWarnings:")
                    for warning in verification["warnings"]:
                        print(f"  ⚠️  {warning}")
            
            else:
                # Default: list both
                print("Use --system to list system agents or --deployed to list deployed agents")
        
        elif args.agents_command == AgentCommands.DEPLOY.value:
            # Deploy agents
            print("Deploying system agents...")
            results = deployment_service.deploy_agents(args.target, force_rebuild=False)
            
            if results["deployed"]:
                print(f"\n✓ Successfully deployed {len(results['deployed'])} agents to {results['target_dir']}")
                for agent in results["deployed"]:
                    print(f"  - {agent['name']}")
        
        elif args.agents_command == AgentCommands.FORCE_DEPLOY.value:
            # Force deploy agents
            print("Force deploying all system agents...")
            results = deployment_service.deploy_agents(args.target, force_rebuild=True)
            
            if results["deployed"]:
                print(f"\n✓ Successfully deployed {len(results['deployed'])} agents to {results['target_dir']}")
                for agent in results["deployed"]:
                    print(f"  - {agent['name']}")
            
            if results.get("updated", []):
                print(f"\n✓ Updated {len(results['updated'])} agents")
                for agent in results["updated"]:
                    print(f"  - {agent['name']}")
            
            if results.get("skipped", []):
                print(f"\n✓ Skipped {len(results['skipped'])} up-to-date agents")
            
            if results["errors"]:
                print("\n❌ Errors during deployment:")
                for error in results["errors"]:
                    print(f"  - {error}")
            
            # Set environment
            env_vars = deployment_service.set_claude_environment(args.target.parent if args.target else None)
            print(f"\n✓ Set Claude environment variables:")
            for key, value in env_vars.items():
                print(f"  - {key}={value}")
        
        elif args.agents_command == AgentCommands.CLEAN.value:
            # Clean deployed agents
            print("Cleaning deployed system agents...")
            results = deployment_service.clean_deployment(args.target)
            
            if results["removed"]:
                print(f"\n✓ Removed {len(results['removed'])} agents")
                for path in results["removed"]:
                    print(f"  - {Path(path).name}")
            else:
                print("No system agents found to remove")
            
            if results["errors"]:
                print("\n❌ Errors during cleanup:")
                for error in results["errors"]:
                    print(f"  - {error}")
        
    except ImportError:
        logger.error("Agent deployment service not available")
        print("Error: Agent deployment service not available")
    except Exception as e:
        logger.error(f"Error managing agents: {e}")
        print(f"Error: {e}")


def run_terminal_ui(args):
    """Run the terminal UI."""
    logger = get_logger("cli")
    
    ui_mode = getattr(args, 'mode', 'terminal')
    
    try:
        if ui_mode == 'terminal':
            # Try rich UI first
            try:
                from .ui.rich_terminal_ui import main as run_rich_ui
                logger.info("Starting rich terminal UI...")
                run_rich_ui()
            except ImportError:
                # Fallback to curses UI
                logger.info("Rich not available, falling back to curses UI...")
                from .ui.terminal_ui import TerminalUI
                ui = TerminalUI()
                ui.run()
        else:
            # Use curses UI
            from .ui.terminal_ui import TerminalUI
            ui = TerminalUI()
            ui.run()
    except ImportError as e:
        logger.error(f"UI module not found: {e}")
        print(f"Error: Terminal UI requires 'curses' (built-in) or 'rich' (pip install rich)")
        return 1
    except Exception as e:
        logger.error(f"Error running terminal UI: {e}")
        print(f"Error: {e}")
        return 1
    
    return 0


def show_info(args, hook_manager=None):
    """Show framework and configuration information."""
    try:
        from .core.framework_loader import FrameworkLoader
    except ImportError:
        from core.framework_loader import FrameworkLoader
    
    print("Claude MPM - Multi-Agent Project Manager")
    print("=" * 50)
    
    # Framework info
    loader = FrameworkLoader(args.framework_path)
    if loader.framework_content["loaded"]:
        print(f"Framework: claude-multiagent-pm")
        print(f"Version: {loader.framework_content['version']}")
        print(f"Path: {loader.framework_path}")
        print(f"Agents: {', '.join(loader.get_agent_list())}")
    else:
        print("Framework: Not found (using minimal instructions)")
    
    print()
    
    # Configuration
    print("Configuration:")
    print(f"  Log directory: {args.log_dir or '~/.claude-mpm/logs'}")
    print(f"  Debug mode: {args.debug}")
    
    # Show agent hierarchy
    if loader.agent_registry:
        hierarchy = loader.agent_registry.get_agent_hierarchy()
        print("\nAgent Hierarchy:")
        print(f"  Project agents: {len(hierarchy['project'])}")
        print(f"  User agents: {len(hierarchy['user'])}")
        print(f"  System agents: {len(hierarchy['system'])}")
        
        # Show core agents
        core_agents = loader.agent_registry.get_core_agents()
        print(f"\nCore Agents: {', '.join(core_agents)}")
    
    # Check dependencies
    print("\nDependencies:")
    
    # Check Claude
    import shutil
    claude_path = shutil.which("claude")
    if claude_path:
        print(f"  ✓ Claude CLI: {claude_path}")
    else:
        print("  ✗ Claude CLI: Not found in PATH")
    
    # Check ai-trackdown-pytools
    try:
        import ai_trackdown_pytools
        print("  ✓ ai-trackdown-pytools: Installed")
    except ImportError:
        print("  ✗ ai-trackdown-pytools: Not installed")
    
    # Check hook service
    if hook_manager:
        info = hook_manager.get_service_info()
        if info['running']:
            print(f"  ✓ Hook System: JSON-RPC ({info.get('hook_count', 0)} hooks)")
            if 'discovered_hooks' in info and info['discovered_hooks']:
                print(f"     Hooks: {', '.join(info['discovered_hooks'][:5])}")
                if len(info['discovered_hooks']) > 5:
                    print(f"     ... and {len(info['discovered_hooks']) - 5} more")
        else:
            print("  ✗ Hook System: Not running")
    else:
        print("  ✗ Hook System: Disabled (--no-hooks)")


if __name__ == "__main__":
    sys.exit(main())