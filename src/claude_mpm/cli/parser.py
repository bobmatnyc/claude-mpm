"""
Argument parser for claude-mpm CLI.

WHY: This module centralizes all argument parsing logic to avoid duplication and provide
a single source of truth for CLI arguments. It uses inheritance to share common arguments
across commands while keeping command-specific args organized.

DESIGN DECISION: We use a base parser factory pattern to create parsers with common
arguments, then extend them for specific commands. This reduces duplication while
maintaining flexibility.
"""

import argparse
from pathlib import Path
from typing import Optional, List

from ..constants import CLICommands, CLIPrefix, AgentCommands, MemoryCommands, MonitorCommands, LogLevel, ConfigCommands, AggregateCommands, TicketCommands


def add_common_arguments(parser: argparse.ArgumentParser, version: str = None) -> None:
    """
    Add common arguments that apply to all commands.
    
    WHY: These arguments are needed across multiple commands, so we centralize them
    to ensure consistency and avoid duplication.
    
    Args:
        parser: The argument parser to add arguments to
        version: Version string to display (only needed for main parser)
    """
    # Version - only add to main parser, not subparsers
    if version is not None:
        parser.add_argument(
            "--version",
            action="version",
            version=f"%(prog)s {version}"
        )
    
    # Logging arguments
    logging_group = parser.add_argument_group('logging options')
    logging_group.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging (deprecated, use --logging DEBUG)"
    )
    logging_group.add_argument(
        "--logging",
        choices=[level.value for level in LogLevel],
        default=LogLevel.INFO.value,
        help="Logging level (default: INFO)"
    )
    logging_group.add_argument(
        "--log-dir",
        type=Path,
        help="Custom log directory (default: ~/.claude-mpm/logs)"
    )
    
    # Framework configuration
    framework_group = parser.add_argument_group('framework options')
    framework_group.add_argument(
        "--framework-path",
        type=Path,
        help="Path to claude-mpm framework"
    )
    framework_group.add_argument(
        "--agents-dir",
        type=Path,
        help="Custom agents directory to use"
    )


def add_run_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add arguments specific to the run command.
    
    WHY: The run command has specific arguments for controlling how Claude sessions
    are executed, including hook management, ticket creation, and interaction modes.
    
    Args:
        parser: The argument parser to add arguments to
    """
    run_group = parser.add_argument_group('run options')
    
    run_group.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable hook service (runs without hooks)"
    )
    run_group.add_argument(
        "--no-tickets",
        action="store_true",
        help="Disable automatic ticket creation"
    )
    run_group.add_argument(
        "--intercept-commands",
        action="store_true",
        help="Enable command interception in interactive mode (intercepts /mpm: commands)"
    )
    run_group.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents"
    )
    run_group.add_argument(
        "--launch-method",
        choices=["exec", "subprocess"],
        default="exec",
        help="Method to launch Claude: exec (replace process) or subprocess (child process)"
    )
    # Monitor options - consolidated monitoring and management interface
    run_group.add_argument(
        "--monitor",
        action="store_true",
        help="Enable monitoring and management interface with WebSocket server and dashboard (default port: 8765)"
    )
    run_group.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    run_group.add_argument(
        "--resume",
        type=str,
        nargs="?",
        const="last",
        help="Resume a session (last session if no ID specified, or specific session ID)"
    )
    
    # Dependency checking options
    dep_group = parser.add_argument_group('dependency options')
    dep_group.add_argument(
        "--no-check-dependencies",
        action="store_false",
        dest="check_dependencies",
        help="Skip agent dependency checking at startup"
    )
    dep_group.add_argument(
        "--force-check-dependencies",
        action="store_true",
        help="Force dependency checking even if cached results exist"
    )
    dep_group.add_argument(
        "--no-prompt",
        action="store_true",
        help="Never prompt for dependency installation (non-interactive mode)"
    )
    dep_group.add_argument(
        "--force-prompt",
        action="store_true",
        help="Force interactive prompting even in non-TTY environments (use with caution)"
    )
    
    # Input/output options
    io_group = parser.add_argument_group('input/output options')
    io_group.add_argument(
        "-i", "--input",
        type=str,
        help="Input text or file path (for non-interactive mode)"
    )
    io_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)"
    )
    
    # Claude CLI arguments
    parser.add_argument(
        "claude_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to Claude CLI (use -- before Claude args)"
    )


def create_parser(prog_name: str = "claude-mpm", version: str = "0.0.0") -> argparse.ArgumentParser:
    """
    Create the main argument parser with all subcommands.
    
    WHY: This factory function creates a complete parser with all commands and their
    arguments. It's the single entry point for creating the CLI parser, ensuring
    consistency across the application.
    
    DESIGN DECISION: We use subparsers for commands to provide a clean, git-like
    interface while maintaining backward compatibility with the original CLI.
    
    Args:
        prog_name: The program name to use
        version: The version string to display
        
    Returns:
        Configured ArgumentParser instance
    """
    # Main parser
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description=f"Claude Multi-Agent Project Manager v{version} - Orchestrate Claude with agent delegation and ticket tracking",
        epilog="By default, runs an orchestrated Claude session. Use 'claude-mpm' for interactive mode or 'claude-mpm -i \"prompt\"' for non-interactive mode.\n\nTo pass arguments to Claude CLI, use -- separator: claude-mpm run -- --model sonnet --temperature 0.1",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add common arguments to main parser with version
    add_common_arguments(parser, version=version)
    
    # Add run-specific arguments at top level for default behavior
    # WHY: This maintains backward compatibility - users can run `claude-mpm -i "prompt"`
    # without specifying the 'run' command
    # NOTE: We don't add claude_args here because REMAINDER interferes with subcommands
    run_group = parser.add_argument_group('run options (when no command specified)')
    
    run_group.add_argument(
        "--no-hooks",
        action="store_true",
        help="Disable hook service (runs without hooks)"
    )
    run_group.add_argument(
        "--no-tickets",
        action="store_true",
        help="Disable automatic ticket creation"
    )
    run_group.add_argument(
        "--intercept-commands",
        action="store_true",
        help="Enable command interception in interactive mode (intercepts /mpm: commands)"
    )
    run_group.add_argument(
        "--no-native-agents",
        action="store_true",
        help="Disable deployment of Claude Code native agents"
    )
    run_group.add_argument(
        "--launch-method",
        choices=["exec", "subprocess"],
        default="exec",
        help="Method to launch Claude: exec (replace process) or subprocess (child process)"
    )
    # Monitor options - consolidated monitoring and management interface
    run_group.add_argument(
        "--monitor",
        action="store_true",
        help="Enable monitoring and management interface with WebSocket server and dashboard (default port: 8765)"
    )
    run_group.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    run_group.add_argument(
        "--resume",
        type=str,
        nargs="?",
        const="last",
        help="Resume a session (last session if no ID specified, or specific session ID)"
    )
    run_group.add_argument(
        "--force",
        action="store_true",
        help="Force operations even with warnings (e.g., large .claude.json file)"
    )
    
    # Dependency checking options (for backward compatibility at top level)
    dep_group_top = parser.add_argument_group('dependency options (when no command specified)')
    dep_group_top.add_argument(
        "--no-check-dependencies",
        action="store_false",
        dest="check_dependencies",
        help="Skip agent dependency checking at startup"
    )
    dep_group_top.add_argument(
        "--force-check-dependencies",
        action="store_true",
        help="Force dependency checking even if cached results exist"
    )
    dep_group_top.add_argument(
        "--no-prompt",
        action="store_true",
        help="Never prompt for dependency installation (non-interactive mode)"
    )
    dep_group_top.add_argument(
        "--force-prompt",
        action="store_true",
        help="Force interactive prompting even in non-TTY environments (use with caution)"
    )
    
    # Input/output options
    io_group = parser.add_argument_group('input/output options (when no command specified)')
    io_group.add_argument(
        "-i", "--input",
        type=str,
        help="Input text or file path (for non-interactive mode)"
    )
    io_group.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (read from stdin or --input)"
    )
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        metavar="COMMAND"
    )
    
    # Run command (explicit)
    run_parser = subparsers.add_parser(
        CLICommands.RUN.value,
        help="Run orchestrated Claude session (default)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_common_arguments(run_parser)
    add_run_arguments(run_parser)
    
    # Tickets command with subcommands
    tickets_parser = subparsers.add_parser(
        CLICommands.TICKETS.value,
        help="Manage tickets and tracking"
    )
    add_common_arguments(tickets_parser)
    
    tickets_subparsers = tickets_parser.add_subparsers(
        dest="tickets_command",
        help="Ticket commands",
        metavar="SUBCOMMAND"
    )
    
    # Create ticket
    create_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.CREATE.value,
        help="Create a new ticket"
    )
    create_ticket_parser.add_argument(
        "title",
        help="Ticket title"
    )
    create_ticket_parser.add_argument(
        "-t", "--type",
        default="task",
        choices=["task", "bug", "feature", "issue", "epic"],
        help="Ticket type (default: task)"
    )
    create_ticket_parser.add_argument(
        "-p", "--priority",
        default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Priority level (default: medium)"
    )
    create_ticket_parser.add_argument(
        "-d", "--description",
        nargs="*",
        help="Ticket description"
    )
    create_ticket_parser.add_argument(
        "--tags",
        help="Comma-separated tags"
    )
    create_ticket_parser.add_argument(
        "--parent-epic",
        help="Parent epic ID"
    )
    create_ticket_parser.add_argument(
        "--parent-issue",
        help="Parent issue ID"
    )
    create_ticket_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    # List tickets
    list_tickets_parser = tickets_subparsers.add_parser(
        TicketCommands.LIST.value,
        help="List recent tickets"
    )
    list_tickets_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="Number of tickets to show (default: 10)"
    )
    list_tickets_parser.add_argument(
        "--type",
        choices=["task", "bug", "feature", "issue", "epic", "all"],
        default="all",
        help="Filter by ticket type"
    )
    list_tickets_parser.add_argument(
        "--status",
        choices=["open", "in_progress", "done", "closed", "blocked", "all"],
        default="all",
        help="Filter by status"
    )
    list_tickets_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed ticket information"
    )
    
    # View ticket
    view_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.VIEW.value,
        help="View a specific ticket"
    )
    view_ticket_parser.add_argument(
        "id",
        help="Ticket ID (e.g., TSK-0001)"
    )
    view_ticket_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show metadata and full details"
    )
    
    # Update ticket
    update_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.UPDATE.value,
        help="Update a ticket"
    )
    update_ticket_parser.add_argument(
        "id",
        help="Ticket ID"
    )
    update_ticket_parser.add_argument(
        "-s", "--status",
        choices=["open", "in_progress", "done", "closed", "blocked"],
        help="Update status"
    )
    update_ticket_parser.add_argument(
        "-p", "--priority",
        choices=["low", "medium", "high", "critical"],
        help="Update priority"
    )
    update_ticket_parser.add_argument(
        "-a", "--assign",
        help="Assign to user"
    )
    update_ticket_parser.add_argument(
        "--tags",
        help="Update tags (comma-separated)"
    )
    update_ticket_parser.add_argument(
        "-d", "--description",
        nargs="*",
        help="Update description"
    )
    
    # Close ticket
    close_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.CLOSE.value,
        help="Close a ticket"
    )
    close_ticket_parser.add_argument(
        "id",
        help="Ticket ID"
    )
    close_ticket_parser.add_argument(
        "--resolution",
        help="Resolution description"
    )
    
    # Delete ticket
    delete_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.DELETE.value,
        help="Delete a ticket"
    )
    delete_ticket_parser.add_argument(
        "id",
        help="Ticket ID"
    )
    delete_ticket_parser.add_argument(
        "--force",
        action="store_true",
        help="Force deletion without confirmation"
    )
    
    # Search tickets
    search_tickets_parser = tickets_subparsers.add_parser(
        TicketCommands.SEARCH.value,
        help="Search tickets"
    )
    search_tickets_parser.add_argument(
        "query",
        help="Search query"
    )
    search_tickets_parser.add_argument(
        "--type",
        choices=["task", "bug", "feature", "issue", "epic", "all"],
        default="all",
        help="Filter by ticket type"
    )
    search_tickets_parser.add_argument(
        "--status",
        choices=["open", "in_progress", "done", "closed", "blocked", "all"],
        default="all",
        help="Filter by status"
    )
    search_tickets_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=20,
        help="Maximum results to show"
    )
    
    # Add comment to ticket
    comment_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.COMMENT.value,
        help="Add comment to a ticket"
    )
    comment_ticket_parser.add_argument(
        "id",
        help="Ticket ID"
    )
    comment_ticket_parser.add_argument(
        "comment",
        nargs="+",
        help="Comment text"
    )
    
    # Update workflow state
    workflow_ticket_parser = tickets_subparsers.add_parser(
        TicketCommands.WORKFLOW.value,
        help="Update ticket workflow state"
    )
    workflow_ticket_parser.add_argument(
        "id",
        help="Ticket ID"
    )
    workflow_ticket_parser.add_argument(
        "state",
        choices=["todo", "in_progress", "ready", "tested", "done", "blocked"],
        help="New workflow state"
    )
    workflow_ticket_parser.add_argument(
        "--comment",
        help="Optional comment for the transition"
    )
    
    # Info command
    info_parser = subparsers.add_parser(
        CLICommands.INFO.value,
        help="Show framework and configuration info"
    )
    add_common_arguments(info_parser)
    
    # Agents command with subcommands
    agents_parser = subparsers.add_parser(
        CLICommands.AGENTS.value,
        help="Manage Claude Code native agents"
    )
    add_common_arguments(agents_parser)
    
    agents_subparsers = agents_parser.add_subparsers(
        dest="agents_command",
        help="Agent commands",
        metavar="SUBCOMMAND"
    )
    
    # List agents
    list_agents_parser = agents_subparsers.add_parser(
        AgentCommands.LIST.value,
        help="List available agents"
    )
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
    list_agents_parser.add_argument(
        "--by-tier",
        action="store_true",
        help="List agents grouped by precedence tier (PROJECT > USER > SYSTEM)"
    )
    
    # View agent details
    view_agent_parser = agents_subparsers.add_parser(
        AgentCommands.VIEW.value,
        help="View detailed information about a specific agent"
    )
    view_agent_parser.add_argument(
        "agent_name",
        help="Name of the agent to view"
    )
    
    # Fix agent frontmatter
    fix_agents_parser = agents_subparsers.add_parser(
        AgentCommands.FIX.value,
        help="Fix agent frontmatter issues"
    )
    fix_agents_parser.add_argument(
        "agent_name",
        nargs="?",
        help="Name of specific agent to fix (fix all if not specified with --all)"
    )
    fix_agents_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    fix_agents_parser.add_argument(
        "--all",
        action="store_true",
        help="Fix all agents"
    )
    
    # Deploy agents
    deploy_agents_parser = agents_subparsers.add_parser(
        AgentCommands.DEPLOY.value,
        help="Deploy system agents"
    )
    deploy_agents_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/agents/)"
    )
    deploy_agents_parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include all agents, overriding exclusion configuration"
    )
    
    # Force deploy agents
    force_deploy_parser = agents_subparsers.add_parser(
        AgentCommands.FORCE_DEPLOY.value,
        help="Force deploy all system agents"
    )
    force_deploy_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/agents/)"
    )
    force_deploy_parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include all agents, overriding exclusion configuration"
    )
    
    # Clean agents
    clean_agents_parser = agents_subparsers.add_parser(
        AgentCommands.CLEAN.value,
        help="Remove deployed system agents"
    )
    clean_agents_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory (default: .claude/)"
    )
    
    # Memory command with subcommands
    memory_parser = subparsers.add_parser(
        CLICommands.MEMORY.value,
        help="Manage agent memory files"
    )
    add_common_arguments(memory_parser)
    
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command",
        help="Memory commands",
        metavar="SUBCOMMAND"
    )
    
    # Init command
    init_parser = memory_subparsers.add_parser(
        MemoryCommands.INIT.value,
        help="Initialize project-specific memories via PM agent"
    )
    
    # Status command
    status_parser = memory_subparsers.add_parser(
        MemoryCommands.STATUS.value,
        help="Show memory file status"
    )
    
    # View command
    view_parser = memory_subparsers.add_parser(
        MemoryCommands.VIEW.value,
        help="View agent memory file"
    )
    view_parser.add_argument(
        "agent_id",
        nargs="?",
        help="Agent ID to view memory for (optional - shows all agents if not provided)"
    )
    
    # Add command
    add_parser = memory_subparsers.add_parser(
        MemoryCommands.ADD.value,
        help="Manually add learning to agent memory"
    )
    add_parser.add_argument(
        "agent_id",
        help="Agent ID to add learning to"
    )
    add_parser.add_argument(
        "learning_type",
        choices=["pattern", "error", "optimization", "preference", "context"],
        help="Type of learning to add"
    )
    add_parser.add_argument(
        "content",
        help="Learning content to add"
    )
    
    # Clean command
    clean_memory_parser = memory_subparsers.add_parser(
        MemoryCommands.CLEAN.value,
        help="Clean up old/unused memory files"
    )
    
    # Optimize command
    optimize_parser = memory_subparsers.add_parser(
        MemoryCommands.OPTIMIZE.value,
        help="Optimize memory files by removing duplicates and consolidating similar items"
    )
    optimize_parser.add_argument(
        "agent_id",
        nargs="?",
        help="Agent ID to optimize (optimize all if not specified)"
    )
    
    # Build command
    build_parser = memory_subparsers.add_parser(
        MemoryCommands.BUILD.value,
        help="Build agent memories from project documentation"
    )
    build_parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild even if docs haven't changed"
    )
    
    # Cross-reference command
    cross_ref_parser = memory_subparsers.add_parser(
        MemoryCommands.CROSS_REF.value,
        help="Find cross-references and common patterns across agent memories"
    )
    cross_ref_parser.add_argument(
        "--query",
        type=str,
        help="Optional search query to filter cross-references"
    )
    
    # Route command
    route_parser = memory_subparsers.add_parser(
        MemoryCommands.ROUTE.value,
        help="Test memory command routing logic"
    )
    route_parser.add_argument(
        "--content",
        type=str,
        required=True,
        help="Content to analyze for routing"
    )
    
    # Show command
    show_parser = memory_subparsers.add_parser(
        MemoryCommands.SHOW.value,
        help="Show agent memories in user-friendly format with cross-references"
    )
    show_parser.add_argument(
        "agent_id",
        nargs="?",
        help="Agent ID to show memory for (show all if not specified)"
    )
    show_parser.add_argument(
        "--format",
        choices=["summary", "detailed", "full"],
        default="summary",
        help="Display format: summary (default), detailed, or full"
    )
    show_parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw memory content in JSON format for programmatic processing"
    )
    
    # Add dependency management subcommands to agents
    deps_check_parser = agents_subparsers.add_parser(
        'deps-check',
        help='Check dependencies for deployed agents'
    )
    deps_check_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    deps_check_parser.add_argument(
        '--agent',
        type=str,
        help='Check dependencies for a specific agent only'
    )
    
    deps_install_parser = agents_subparsers.add_parser(
        'deps-install',
        help='Install missing dependencies for deployed agents'
    )
    deps_install_parser.add_argument(
        '--agent',
        type=str,
        help='Install dependencies for a specific agent only'
    )
    deps_install_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be installed without actually installing'
    )
    
    deps_list_parser = agents_subparsers.add_parser(
        'deps-list',
        help='List all dependencies from deployed agents'
    )
    deps_list_parser.add_argument(
        '--format',
        choices=['text', 'pip', 'json'],
        default='text',
        help='Output format for dependency list'
    )
    
    deps_fix_parser = agents_subparsers.add_parser(
        'deps-fix',
        help='Fix missing agent dependencies with robust retry logic'
    )
    deps_fix_parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum retry attempts per package (default: 3)'
    )
    
    # Config command with subcommands
    config_parser = subparsers.add_parser(
        CLICommands.CONFIG.value,
        help="Validate and manage configuration"
    )
    add_common_arguments(config_parser)
    
    config_subparsers = config_parser.add_subparsers(
        dest="config_command",
        help="Config commands",
        metavar="SUBCOMMAND"
    )
    
    # Validate config
    validate_config_parser = config_subparsers.add_parser(
        ConfigCommands.VALIDATE.value,
        help="Validate configuration file"
    )
    validate_config_parser.add_argument(
        "--config-file",
        type=Path,
        help="Path to configuration file (default: .claude-mpm/configuration.yaml)"
    )
    validate_config_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    
    # View config
    view_config_parser = config_subparsers.add_parser(
        ConfigCommands.VIEW.value,
        help="View current configuration"
    )
    view_config_parser.add_argument(
        "--config-file",
        type=Path,
        help="Path to configuration file"
    )
    view_config_parser.add_argument(
        "--section",
        help="View specific configuration section"
    )
    view_config_parser.add_argument(
        "--format",
        choices=["table", "json", "yaml"],
        default="table",
        help="Output format (default: table)"
    )
    
    # Config status
    status_config_parser = config_subparsers.add_parser(
        ConfigCommands.STATUS.value,
        help="Show configuration status and health"
    )
    status_config_parser.add_argument(
        "--config-file",
        type=Path,
        help="Path to configuration file"
    )
    status_config_parser.add_argument(
        "--check-response-logging",
        action="store_true",
        help="Show detailed response logging configuration"
    )
    status_config_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed errors and warnings"
    )
    
    # Monitor command with subcommands
    monitor_parser = subparsers.add_parser(
        CLICommands.MONITOR.value,
        help="Manage Socket.IO monitoring server"
    )
    add_common_arguments(monitor_parser)
    
    monitor_subparsers = monitor_parser.add_subparsers(
        dest="monitor_command",
        help="Monitor commands",
        metavar="SUBCOMMAND"
    )
    
    # Start monitor
    start_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.START.value,
        help="Start Socket.IO monitoring server"
    )
    start_monitor_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to start server on (default: 8765)"
    )
    start_monitor_parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)"
    )
    
    # Stop monitor
    stop_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.STOP.value,
        help="Stop Socket.IO monitoring server"
    )
    stop_monitor_parser.add_argument(
        "--port",
        type=int,
        help="Port of server to stop (auto-detect if not specified)"
    )
    
    # Restart monitor
    restart_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.RESTART.value,
        help="Restart Socket.IO monitoring server"
    )
    restart_monitor_parser.add_argument(
        "--port",
        type=int,
        help="Port of server to restart (auto-detect if not specified)"
    )
    
    # Port monitor - start/restart on specific port
    port_monitor_parser = monitor_subparsers.add_parser(
        MonitorCommands.PORT.value,
        help="Start/restart Socket.IO monitoring server on specific port"
    )
    port_monitor_parser.add_argument(
        "port",
        type=int,
        help="Port number to start/restart server on"
    )
    port_monitor_parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)"
    )
    
    # Import and add aggregate command parser
    from .commands.aggregate import add_aggregate_parser
    add_aggregate_parser(subparsers)
    
    # Import and add cleanup command parser
    from .commands.cleanup import add_cleanup_parser
    add_cleanup_parser(subparsers)
    
    return parser


def preprocess_args(argv: Optional[List[str]] = None) -> List[str]:
    """
    Preprocess arguments to handle --mpm: prefix commands.
    
    WHY: We support both --mpm:command and regular command syntax for flexibility
    and backward compatibility. This function normalizes the input.
    
    Args:
        argv: List of command line arguments, or None to use sys.argv[1:]
        
    Returns:
        Processed list of arguments with prefixes removed
    """
    import sys
    
    if argv is None:
        argv = sys.argv[1:]
    
    # Convert --mpm:command to command for argparse compatibility
    processed_args = []
    for arg in argv:
        if arg.startswith(CLIPrefix.MPM.value):
            # Extract command after prefix
            command = arg[len(CLIPrefix.MPM.value):]
            processed_args.append(command)
        else:
            processed_args.append(arg)
    
    return processed_args