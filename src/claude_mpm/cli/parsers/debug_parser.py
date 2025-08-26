"""
Debug command parser for claude-mpm CLI.

This module contains all arguments specific to debugging tools,
providing developer-focused commands for monitoring and analysis.
"""

import argparse

from .base_parser import add_common_arguments


def add_debug_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the debug subparser with all debugging commands.

    This provides professional debugging tools for developers working
    on claude-mpm, particularly for dashboard and event monitoring.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured debug subparser
    """
    # Main debug parser
    debug_parser = subparsers.add_parser(
        "debug",
        help="Development debugging tools",
        description="Professional debugging tools for claude-mpm developers",
    )

    # Add common arguments (logging, etc.)
    add_common_arguments(debug_parser)

    # Create subparsers for debug commands
    debug_subparsers = debug_parser.add_subparsers(
        dest="debug_command", help="Debug commands", metavar="SUBCOMMAND", required=True
    )

    # SocketIO event debugging
    _add_socketio_parser(debug_subparsers)

    # Connection debugging
    _add_connections_parser(debug_subparsers)

    # Services debugging
    _add_services_parser(debug_subparsers)

    # Agents debugging
    _add_agents_parser(debug_subparsers)

    # Hooks debugging
    _add_hooks_parser(debug_subparsers)

    # Cache debugging
    _add_cache_parser(debug_subparsers)

    # Performance debugging
    _add_performance_parser(debug_subparsers)

    return debug_parser


def _add_socketio_parser(subparsers):
    """Add SocketIO debugging subcommand."""
    socketio_parser = subparsers.add_parser(
        "socketio",
        help="Monitor and debug SocketIO events in real-time",
        aliases=["events", "socket"],
        description="""
Professional SocketIO event monitoring tool for dashboard development.

This tool provides real-time monitoring of all SocketIO events with:
- Live event streaming with formatted output
- Event statistics and aggregation
- Tool usage tracking
- Session monitoring
- Connection health checks
- Event filtering and export capabilities

Examples:
  # Monitor all events in real-time
  claude-mpm debug socketio

  # Show event summary statistics
  claude-mpm debug socketio --summary

  # Filter specific event types
  claude-mpm debug socketio --filter PreToolUse PostToolUse

  # Save events to file for analysis
  claude-mpm debug socketio --output events.jsonl

  # Connect to specific server
  claude-mpm debug socketio --host localhost --port 8765
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Connection settings
    conn_group = socketio_parser.add_argument_group("connection settings")
    conn_group.add_argument(
        "--host", default="localhost", help="SocketIO server host (default: localhost)"
    )
    conn_group.add_argument(
        "--port", type=int, default=8765, help="SocketIO server port (default: 8765)"
    )
    conn_group.add_argument(
        "--max-reconnect",
        type=int,
        default=10,
        help="Maximum reconnection attempts (default: 10)",
    )
    conn_group.add_argument(
        "--reconnect-delay",
        type=float,
        default=1.0,
        help="Reconnection delay in seconds (default: 1.0)",
    )

    # Display modes (mutually exclusive)
    display_group = socketio_parser.add_argument_group("display modes")
    mode_group = display_group.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--live",
        action="store_true",
        help="Live event monitoring with formatted output (default)",
    )
    mode_group.add_argument(
        "--summary",
        action="store_true",
        help="Show aggregated event statistics and summary",
    )
    mode_group.add_argument(
        "--raw", action="store_true", help="Display raw JSON output for each event"
    )
    mode_group.add_argument(
        "--pretty",
        action="store_true",
        help="Enhanced formatted output with colors and icons",
    )

    # Filtering and output
    filter_group = socketio_parser.add_argument_group("filtering and output")
    filter_group.add_argument(
        "--filter",
        nargs="+",
        dest="filter_types",
        metavar="TYPE",
        help="Filter specific event types (e.g., PreToolUse PostToolUse)",
    )
    filter_group.add_argument(
        "--output", "-o", metavar="FILE", help="Save events to file in JSONL format"
    )
    filter_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output except errors (useful with --output)",
    )


def _add_connections_parser(subparsers):
    """Add connections debugging subcommand."""
    connections_parser = subparsers.add_parser(
        "connections",
        help="Show active SocketIO server connections",
        aliases=["conn", "servers"],
        description="""
Display information about active SocketIO servers and their status.

This command shows:
- All running SocketIO server instances
- Port numbers and process IDs
- Connection health status
- Server start times

Examples:
  # Show all active servers
  claude-mpm debug connections

  # Show detailed information
  claude-mpm debug connections --verbose
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    connections_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed connection information in JSON format",
    )
    connections_parser.add_argument(
        "--check-health",
        action="store_true",
        help="Perform health checks on each server",
    )
    connections_parser.add_argument(
        "--cleanup", action="store_true", help="Clean up stale server entries"
    )


def _add_services_parser(subparsers):
    """Add services debugging subcommand."""
    services_parser = subparsers.add_parser(
        "services",
        help="Debug service container and dependencies",
        description="Inspect services, dependencies, and health status",
    )

    services_group = services_parser.add_mutually_exclusive_group()
    services_group.add_argument(
        "--list", action="store_true", help="List all registered services"
    )
    services_group.add_argument(
        "--status", action="store_true", help="Show service health status"
    )
    services_group.add_argument(
        "--dependencies", action="store_true", help="Show service dependency graph"
    )
    services_group.add_argument(
        "--trace",
        metavar="SERVICE",
        help="Trace service resolution for specific service",
    )


def _add_agents_parser(subparsers):
    """Add agents debugging subcommand."""
    agents_parser = subparsers.add_parser(
        "agents",
        help="Debug deployed agents and memory",
        description="Inspect deployed agents, memory, and traces",
    )

    agents_group = agents_parser.add_mutually_exclusive_group()
    agents_group.add_argument(
        "--deployed", action="store_true", help="List all deployed agents"
    )
    agents_group.add_argument(
        "--memory", action="store_true", help="Show agent memory status"
    )
    agents_group.add_argument(
        "--trace", metavar="AGENT", help="Trace specific agent execution"
    )
    agents_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )


def _add_hooks_parser(subparsers):
    """Add hooks debugging subcommand."""
    hooks_parser = subparsers.add_parser(
        "hooks",
        help="Debug hook system",
        description="List hooks, trace execution, analyze performance",
    )

    hooks_group = hooks_parser.add_mutually_exclusive_group()
    hooks_group.add_argument(
        "--list", action="store_true", help="List all registered hooks"
    )
    hooks_group.add_argument(
        "--trace", metavar="HOOK", help="Trace specific hook execution"
    )
    hooks_group.add_argument(
        "--performance", action="store_true", help="Analyze hook performance"
    )
    hooks_parser.add_argument(
        "--test", action="store_true", help="Run test execution when tracing"
    )


def _add_cache_parser(subparsers):
    """Add cache debugging subcommand."""
    cache_parser = subparsers.add_parser(
        "cache",
        help="Debug cache system",
        description="Inspect, clear, and analyze cache",
    )

    cache_group = cache_parser.add_mutually_exclusive_group()
    cache_group.add_argument(
        "--inspect", action="store_true", help="Inspect cache contents"
    )
    cache_group.add_argument("--clear", action="store_true", help="Clear all cache")
    cache_group.add_argument(
        "--stats", action="store_true", help="Show cache performance statistics"
    )
    cache_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed cache information"
    )
    cache_parser.add_argument(
        "--confirm",
        "-y",
        action="store_true",
        help="Skip confirmation for clear operation",
    )


def _add_performance_parser(subparsers):
    """Add performance debugging subcommand."""
    performance_parser = subparsers.add_parser(
        "performance",
        help="Performance profiling and analysis",
        description="Profile operations and analyze bottlenecks",
    )

    perf_group = performance_parser.add_mutually_exclusive_group()
    perf_group.add_argument(
        "--profile",
        metavar="OPERATION",
        help="Profile specific operation (agent_load, service_init, cache_ops, memory_ops)",
    )
    perf_group.add_argument(
        "--benchmark", action="store_true", help="Run performance benchmarks"
    )
