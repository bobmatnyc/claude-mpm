"""
Local Deploy parser module for claude-mpm CLI.

WHY: Provides argument parsing for local deployment management commands.
Extracted from the monolithic parser.py for better organization.

DESIGN DECISION: Supports multiple subcommands (start, stop, restart, status, etc.)
with command-specific arguments for comprehensive process management.
"""

from pathlib import Path


def add_local_deploy_arguments(subparsers) -> None:
    """
    Add local-deploy command and its subcommands to the parser.

    WHY: Provides a comprehensive CLI for managing local development deployments
    with process monitoring, health checks, and auto-restart capabilities.

    Args:
        subparsers: The subparsers object to add commands to
    """
    # Main local-deploy command
    local_deploy_parser = subparsers.add_parser(
        "local-deploy",
        help="Manage local development deployments with process monitoring",
        description=(
            "Manage local development deployments with comprehensive process management, "
            "health monitoring, and auto-restart capabilities."
        ),
    )

    # Create subparsers for local-deploy subcommands
    local_deploy_subparsers = local_deploy_parser.add_subparsers(
        dest="local_deploy_command",
        help="Local deployment commands",
    )

    # ===== START command =====
    start_parser = local_deploy_subparsers.add_parser(
        "start",
        help="Start a new local deployment",
        description="Start a new local deployment with process monitoring and optional auto-restart",
    )
    start_parser.add_argument(
        "--command",
        "-c",
        required=True,
        help="Command to execute (e.g., 'npm run dev' or 'python manage.py runserver')",
    )
    start_parser.add_argument(
        "--working-directory",
        "-d",
        type=Path,
        help="Working directory for the process (default: current directory)",
    )
    start_parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="Port number for the deployment",
    )
    start_parser.add_argument(
        "--auto-find-port",
        action="store_true",
        default=True,
        help="Automatically find alternative port if specified port is unavailable (default: enabled)",
    )
    start_parser.add_argument(
        "--no-auto-find-port",
        action="store_false",
        dest="auto_find_port",
        help="Disable automatic port finding",
    )
    start_parser.add_argument(
        "--auto-restart",
        action="store_true",
        help="Enable automatic restart on crashes",
    )
    start_parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file for monitoring error patterns",
    )
    start_parser.add_argument(
        "--env",
        "-e",
        action="append",
        help="Environment variables in KEY=VALUE format (can be specified multiple times)",
    )

    # ===== STOP command =====
    stop_parser = local_deploy_subparsers.add_parser(
        "stop",
        help="Stop a running deployment",
        description="Stop a running deployment with graceful shutdown",
    )
    stop_parser.add_argument(
        "deployment_id",
        help="Deployment ID to stop",
    )
    stop_parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=10,
        help="Timeout in seconds for graceful shutdown (default: 10)",
    )
    stop_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force kill immediately without graceful shutdown",
    )

    # ===== RESTART command =====
    restart_parser = local_deploy_subparsers.add_parser(
        "restart",
        help="Restart a deployment",
        description="Restart a deployment with the same configuration",
    )
    restart_parser.add_argument(
        "deployment_id",
        help="Deployment ID to restart",
    )
    restart_parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=10,
        help="Timeout in seconds for graceful shutdown (default: 10)",
    )

    # ===== STATUS command =====
    status_parser = local_deploy_subparsers.add_parser(
        "status",
        help="Show comprehensive deployment status",
        description="Show comprehensive status including process info, health, and restart history",
    )
    status_parser.add_argument(
        "deployment_id",
        help="Deployment ID to check",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output status in JSON format",
    )

    # ===== HEALTH command =====
    health_parser = local_deploy_subparsers.add_parser(
        "health",
        help="Show health status",
        description="Show health check status including HTTP, process, and resource checks",
    )
    health_parser.add_argument(
        "deployment_id",
        help="Deployment ID to check",
    )

    # ===== LIST command =====
    list_parser = local_deploy_subparsers.add_parser(
        "list",
        help="List all deployments",
        description="List all local deployments with their status",
    )
    list_parser.add_argument(
        "--status",
        "-s",
        choices=["running", "stopped", "crashed", "stopping"],
        help="Filter deployments by status",
    )

    # ===== MONITOR command =====
    monitor_parser = local_deploy_subparsers.add_parser(
        "monitor",
        help="Live monitoring dashboard",
        description="Display live monitoring dashboard for a deployment",
    )
    monitor_parser.add_argument(
        "deployment_id",
        help="Deployment ID to monitor",
    )
    monitor_parser.add_argument(
        "--refresh",
        "-r",
        type=int,
        default=2,
        help="Refresh interval in seconds (default: 2)",
    )

    # ===== HISTORY command =====
    history_parser = local_deploy_subparsers.add_parser(
        "history",
        help="Show restart history",
        description="Show restart history and statistics for a deployment",
    )
    history_parser.add_argument(
        "deployment_id",
        help="Deployment ID to check",
    )

    # ===== ENABLE-AUTO-RESTART command =====
    enable_auto_restart_parser = local_deploy_subparsers.add_parser(
        "enable-auto-restart",
        help="Enable auto-restart for a deployment",
        description="Enable automatic restart on crashes for a deployment",
    )
    enable_auto_restart_parser.add_argument(
        "deployment_id",
        help="Deployment ID to enable auto-restart for",
    )

    # ===== DISABLE-AUTO-RESTART command =====
    disable_auto_restart_parser = local_deploy_subparsers.add_parser(
        "disable-auto-restart",
        help="Disable auto-restart for a deployment",
        description="Disable automatic restart on crashes for a deployment",
    )
    disable_auto_restart_parser.add_argument(
        "deployment_id",
        help="Deployment ID to disable auto-restart for",
    )


__all__ = ["add_local_deploy_arguments"]
