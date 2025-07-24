"""Command-line interface for Claude MPM."""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    # Try relative imports first (when used as package)
    from ._version import __version__
    from .utils.logger import get_logger, setup_logging
    from .services.hook_service_manager import HookServiceManager
    from .orchestration.factory import OrchestratorFactory
except ImportError:
    # Fall back to absolute imports (when run directly)
    from claude_mpm._version import __version__
    from utils.logger import get_logger, setup_logging
    from services.hook_service_manager import HookServiceManager
    from orchestration.factory import OrchestratorFactory


def main(argv: Optional[list] = None):
    """Main CLI entry point."""
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
        choices=["OFF", "INFO", "DEBUG"],
        default="OFF",
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
        "--subprocess",
        action="store_true",
        help="Use subprocess orchestration for agent delegations"
    )
    parser.add_argument(
        "--interactive-subprocess",
        action="store_true",
        help="Use interactive subprocess orchestration with pexpect control"
    )
    parser.add_argument(
        "--todo-hijack",
        action="store_true",
        help="Enable TODO hijacking to transform Claude's TODOs into agent delegations"
    )
    
    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command (default) - duplicate args for explicit 'run' command
    run_parser = subparsers.add_parser("run", help="Run orchestrated Claude session (default)")
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
        "--subprocess",
        action="store_true",
        help="Use subprocess orchestration for agent delegations"
    )
    run_parser.add_argument(
        "--interactive-subprocess",
        action="store_true",
        help="Use interactive subprocess orchestration with pexpect control"
    )
    
    # List tickets command
    list_parser = subparsers.add_parser("tickets", help="List recent tickets")
    list_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="Number of tickets to show"
    )
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show framework and configuration info")
    
    # Parse arguments
    args = parser.parse_args(argv)
    
    # Set up logging first
    # Handle deprecated --debug flag
    if args.debug and args.logging == "OFF":
        args.logging = "DEBUG"
    
    # Only setup logging if not OFF
    if args.logging != "OFF":
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
                hook_manager = HookServiceManager(log_dir=args.log_dir)
                if hook_manager.start_service():
                    logger.info(f"Hook service started on port {hook_manager.port}")
                    print(f"Hook service started on port {hook_manager.port}")
                else:
                    logger.warning("Failed to start hook service, continuing without hooks")
                    print("Failed to start hook service, continuing without hooks")
                    hook_manager = None
            else:
                logger.info("Hooks disabled via configuration")
        except Exception as e:
            logger.warning(f"Hook service initialization failed: {e}, continuing without hooks")
            hook_manager = None
    
    # Default to run command
    if not args.command:
        args.command = "run"
        # Also set default arguments for run command when no subcommand specified
        args.no_tickets = getattr(args, 'no_tickets', False)
        args.no_hooks = getattr(args, 'no_hooks', False)
        args.input = getattr(args, 'input', None)
        args.non_interactive = getattr(args, 'non_interactive', False)
        args.subprocess = getattr(args, 'subprocess', False)
        args.interactive_subprocess = getattr(args, 'interactive_subprocess', False)
    
    # Execute command
    try:
        if args.command == "run":
            run_session(args, hook_manager)
        elif args.command == "tickets":
            list_tickets(args)
        elif args.command == "info":
            show_info(args, hook_manager)
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


def _show_session_summary(orchestrator):
    """Show session summary for tickets and delegations."""
    # Show ticket summary
    if hasattr(orchestrator, 'ticket_extractor'):
        tickets = orchestrator.ticket_extractor.get_all_tickets()
        if tickets:
            print(f"\n📋 Extracted {len(tickets)} tickets during session:")
            summary = orchestrator.ticket_extractor.get_summary()
            for ticket_type, count in summary.items():
                print(f"  - {ticket_type}: {count}")
    
    # Show delegation summary
    if hasattr(orchestrator, 'agent_delegator'):
        delegations = orchestrator.agent_delegator.get_delegation_summary()
        if delegations:
            print(f"\n👥 Agent delegations during session:")
            for agent, count in delegations.items():
                print(f"  - {agent}: {count} tasks")


def run_session(args, hook_manager=None):
    """Run an orchestrated Claude session."""
    logger = get_logger("cli")
    if args.logging != "OFF":
        logger.info("Starting Claude MPM session")
        if hook_manager and hook_manager.is_available():
            logger.info(f"Hook service available at port {hook_manager.port}")
    
    # Create configuration for factory
    config = {
        "framework_path": args.framework_path,
        "agents_dir": getattr(args, 'agents_dir', None),
        "log_level": args.logging,
        "log_dir": args.log_dir,
        "hook_manager": hook_manager,
        "no_tickets": args.no_tickets,
        "subprocess": getattr(args, 'subprocess', False),
        "interactive_subprocess": getattr(args, 'interactive_subprocess', False),
        "enable_todo_hijacking": getattr(args, 'todo_hijack', False)
    }
    
    # Create orchestrator using factory
    factory = OrchestratorFactory()
    orchestrator = factory.create_orchestrator(config=config)
    
    # Run session based on mode
    if args.non_interactive or args.input:
        user_input = _get_user_input(args, logger)
        
        # Run appropriate session type
        if getattr(args, 'interactive_subprocess', False):
            orchestrator.run_orchestrated_session(user_input)
        else:
            orchestrator.run_non_interactive(user_input)
    else:
        # Run interactive session
        orchestrator.run_interactive()
    
    # Show session summary
    _show_session_summary(orchestrator)


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
            print(f"  ✓ Hook Service: Running on port {info['port']}")
        else:
            print("  ✗ Hook Service: Not running")
    else:
        print("  ✗ Hook Service: Disabled (--no-hooks)")


if __name__ == "__main__":
    sys.exit(main())