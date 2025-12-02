"""
Local Deploy command implementation for claude-mpm.

WHY: This module provides CLI commands for managing local development deployments
using the UnifiedLocalOpsManager. Supports starting, stopping, monitoring, and
managing local processes with full health monitoring and auto-restart capabilities.

DESIGN DECISIONS:
- Use UnifiedLocalOpsManager as single entry point
- Rich terminal output for better user experience
- Subcommands: start, stop, restart, status, health, list, monitor, history
- Support both interactive and script-friendly output modes
"""

import json
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from claude_mpm.core.enums import ServiceState

from ...services.local_ops import StartConfig, UnifiedLocalOpsManager
from ..shared import BaseCommand, CommandResult


class LocalDeployCommand(BaseCommand):
    """Local Deploy command for managing local development deployments."""

    def __init__(self):
        super().__init__("local-deploy")
        self.console = Console()
        self.manager: Optional[UnifiedLocalOpsManager] = None

    def validate_args(self, args) -> Optional[str]:
        """Validate command arguments."""
        if not hasattr(args, "local_deploy_command") or not args.local_deploy_command:
            return "No subcommand specified. Use: start, stop, restart, status, list, monitor, history"

        valid_commands = [
            "start",
            "stop",
            "restart",
            "status",
            "health",
            "list",
            "monitor",
            "history",
            "enable-auto-restart",
            "disable-auto-restart",
        ]
        if args.local_deploy_command not in valid_commands:
            return f"Unknown subcommand: {args.local_deploy_command}. Valid commands: {', '.join(valid_commands)}"

        # Validate command-specific arguments
        if args.local_deploy_command == "start":
            if not hasattr(args, "command") or not args.command:
                return "Missing required argument: --command"

        elif args.local_deploy_command in [
            "stop",
            "restart",
            "status",
            "health",
            "history",
            "enable-auto-restart",
            "disable-auto-restart",
        ]:
            if not hasattr(args, "deployment_id") or not args.deployment_id:
                return "Missing required argument: --deployment-id"

        return None

    def run(self, args) -> CommandResult:
        """Execute the local-deploy command."""
        try:
            self.logger.info(f"Local deploy command: {args.local_deploy_command}")

            # Initialize manager
            project_root = getattr(args, "project_dir", None) or self.working_dir
            self.manager = UnifiedLocalOpsManager(project_root=Path(project_root))

            if not self.manager.initialize():
                return CommandResult.error_result(
                    "Failed to initialize local ops manager"
                )

            # Route to specific command
            command = args.local_deploy_command
            if command == "start":
                return self._start_command(args)
            if command == "stop":
                return self._stop_command(args)
            if command == "restart":
                return self._restart_command(args)
            if command == "status":
                return self._status_command(args)
            if command == "health":
                return self._health_command(args)
            if command == "list":
                return self._list_command(args)
            if command == "monitor":
                return self._monitor_command(args)
            if command == "history":
                return self._history_command(args)
            if command == "enable-auto-restart":
                return self._enable_auto_restart_command(args)
            if command == "disable-auto-restart":
                return self._disable_auto_restart_command(args)
            return CommandResult.error_result(f"Unknown command: {command}")

        except Exception as e:
            self.logger.error(
                f"Error executing local-deploy command: {e}", exc_info=True
            )
            return CommandResult.error_result(f"Error: {e}")
        finally:
            if self.manager:
                self.manager.shutdown()

    def _start_command(self, args) -> CommandResult:
        """Start a new deployment."""
        try:
            # Parse command
            command = (
                args.command.split() if isinstance(args.command, str) else args.command
            )

            # Create start configuration
            config = StartConfig(
                command=command,
                working_directory=str(args.working_directory or self.working_dir),
                port=getattr(args, "port", None),
                auto_find_port=getattr(args, "auto_find_port", True),
                environment=getattr(args, "env", {}) or {},
                metadata={"log_file": getattr(args, "log_file", None)},
            )

            # Start deployment
            auto_restart = getattr(args, "auto_restart", False)
            deployment = self.manager.start_deployment(
                config, auto_restart=auto_restart
            )

            # Output result
            self.console.print(
                Panel(
                    f"[green]✓[/green] Deployment started successfully\n\n"
                    f"[bold]Deployment ID:[/bold] {deployment.deployment_id}\n"
                    f"[bold]Process ID:[/bold] {deployment.process_id}\n"
                    f"[bold]Port:[/bold] {deployment.port or 'N/A'}\n"
                    f"[bold]Auto-restart:[/bold] {'Enabled' if auto_restart else 'Disabled'}\n"
                    f"[bold]Command:[/bold] {' '.join(deployment.command)}",
                    title="Deployment Started",
                    border_style="green",
                )
            )

            return CommandResult.success_result(
                f"Started deployment {deployment.deployment_id}",
                data={
                    "deployment_id": deployment.deployment_id,
                    "process_id": deployment.process_id,
                    "port": deployment.port,
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to start deployment: {e}", exc_info=True)
            self.console.print(f"[red]✗ Failed to start deployment: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _stop_command(self, args) -> CommandResult:
        """Stop a deployment."""
        try:
            deployment_id = args.deployment_id
            force = getattr(args, "force", False)
            timeout = getattr(args, "timeout", 10)

            success = self.manager.stop_deployment(
                deployment_id, timeout=timeout, force=force
            )

            if success:
                self.console.print(
                    f"[green]✓ Deployment {deployment_id} stopped successfully[/green]"
                )
                return CommandResult.success_result(
                    f"Stopped deployment {deployment_id}"
                )
            self.console.print(
                f"[red]✗ Failed to stop deployment {deployment_id}[/red]"
            )
            return CommandResult.error_result("Failed to stop deployment")

        except Exception as e:
            self.logger.error(f"Failed to stop deployment: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _restart_command(self, args) -> CommandResult:
        """Restart a deployment."""
        try:
            deployment_id = args.deployment_id
            timeout = getattr(args, "timeout", 10)

            deployment = self.manager.restart_deployment(deployment_id, timeout=timeout)

            self.console.print(
                Panel(
                    f"[green]✓[/green] Deployment restarted successfully\n\n"
                    f"[bold]Deployment ID:[/bold] {deployment.deployment_id}\n"
                    f"[bold]New Process ID:[/bold] {deployment.process_id}\n"
                    f"[bold]Port:[/bold] {deployment.port or 'N/A'}",
                    title="Deployment Restarted",
                    border_style="green",
                )
            )

            return CommandResult.success_result(f"Restarted deployment {deployment_id}")

        except Exception as e:
            self.logger.error(f"Failed to restart deployment: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _status_command(self, args) -> CommandResult:
        """Show deployment status."""
        try:
            deployment_id = args.deployment_id
            json_output = getattr(args, "json", False)

            status = self.manager.get_full_status(deployment_id)

            if json_output:
                print(json.dumps(status, indent=2, default=str))
                return CommandResult.success_result("Status retrieved")

            # Rich formatted output
            self._render_status_panel(status)

            return CommandResult.success_result("Status retrieved", data=status)

        except Exception as e:
            self.logger.error(f"Failed to get status: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _health_command(self, args) -> CommandResult:
        """Show health status."""
        try:
            deployment_id = args.deployment_id
            health = self.manager.get_health_status(deployment_id)

            if not health:
                self.console.print(
                    f"[yellow]No health data available for {deployment_id}[/yellow]"
                )
                return CommandResult.error_result("No health data available")

            # Render health status
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
                "unknown": "dim",
            }.get(health.overall_status.value, "dim")

            self.console.print(
                Panel(
                    f"[{status_color}]Status:[/{status_color}] {health.overall_status.value.upper()}\n\n"
                    f"[bold]HTTP Check:[/bold] {'✓' if health.http_healthy else '✗'}\n"
                    f"[bold]Process Check:[/bold] {'✓' if health.process_healthy else '✗'}\n"
                    f"[bold]Resource Check:[/bold] {'✓' if health.resource_healthy else '✗'}\n"
                    f"[bold]Last Check:[/bold] {health.last_check or 'Never'}\n"
                    f"{f'[bold]Failure Reason:[/bold] {health.failure_reason}' if health.failure_reason else ''}",
                    title=f"Health Status: {deployment_id}",
                    border_style=status_color,
                )
            )

            return CommandResult.success_result("Health status retrieved")

        except Exception as e:
            self.logger.error(f"Failed to get health status: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _list_command(self, args) -> CommandResult:
        """List all deployments."""
        try:
            status_filter_str = getattr(args, "status", None)
            status_filter = (
                ServiceState(status_filter_str) if status_filter_str else None
            )

            deployments = self.manager.list_deployments(status_filter=status_filter)

            if not deployments:
                self.console.print("[yellow]No deployments found[/yellow]")
                return CommandResult.success_result("No deployments found")

            # Create table
            table = Table(title="Local Deployments", show_header=True)
            table.add_column("Deployment ID", style="cyan")
            table.add_column("PID", style="magenta")
            table.add_column("Port", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Started At", style="dim")

            for deployment in deployments:
                table.add_row(
                    deployment.deployment_id,
                    str(deployment.process_id),
                    str(deployment.port) if deployment.port else "N/A",
                    deployment.status.value,
                    deployment.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                )

            self.console.print(table)

            return CommandResult.success_result(
                f"Found {len(deployments)} deployment(s)",
                data={"count": len(deployments)},
            )

        except Exception as e:
            self.logger.error(f"Failed to list deployments: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _monitor_command(self, args) -> CommandResult:
        """Live monitoring dashboard."""
        try:
            deployment_id = args.deployment_id
            refresh_interval = getattr(args, "refresh", 2)

            self.console.print(
                f"[cyan]Monitoring {deployment_id}... (Press Ctrl+C to stop)[/cyan]\n"
            )

            with Live(
                console=self.console, refresh_per_second=1 / refresh_interval
            ) as live:
                while True:
                    try:
                        status = self.manager.get_full_status(deployment_id)
                        live.update(self._render_live_status(status))
                        time.sleep(refresh_interval)
                    except KeyboardInterrupt:
                        break

            return CommandResult.success_result("Monitoring stopped")

        except Exception as e:
            self.logger.error(f"Failed to monitor deployment: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _history_command(self, args) -> CommandResult:
        """Show restart history."""
        try:
            deployment_id = args.deployment_id
            history = self.manager.get_restart_history(deployment_id)

            if not history:
                self.console.print(
                    f"[yellow]No restart history for {deployment_id}[/yellow]"
                )
                return CommandResult.success_result("No restart history")

            self.console.print(
                Panel(
                    f"[bold]Total Restarts:[/bold] {history.total_restarts}\n"
                    f"[bold]Successful:[/bold] {history.successful_restarts}\n"
                    f"[bold]Failed:[/bold] {history.failed_restarts}\n"
                    f"[bold]Circuit Breaker:[/bold] {history.circuit_breaker_state.value}\n"
                    f"[bold]Auto-restart:[/bold] {'Enabled' if history.auto_restart_enabled else 'Disabled'}",
                    title=f"Restart History: {deployment_id}",
                    border_style="cyan",
                )
            )

            # Show recent attempts
            if history.recent_attempts:
                table = Table(title="Recent Restart Attempts", show_header=True)
                table.add_column("Timestamp", style="dim")
                table.add_column("Success", style="green")
                table.add_column("Reason", style="yellow")

                for attempt in history.recent_attempts[-10:]:  # Last 10
                    table.add_row(
                        attempt.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "✓" if attempt.success else "✗",
                        attempt.reason or "Unknown",
                    )

                self.console.print("\n")
                self.console.print(table)

            return CommandResult.success_result("Restart history retrieved")

        except Exception as e:
            self.logger.error(f"Failed to get restart history: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _enable_auto_restart_command(self, args) -> CommandResult:
        """Enable auto-restart for a deployment."""
        try:
            deployment_id = args.deployment_id
            success = self.manager.enable_auto_restart(deployment_id)

            if success:
                self.console.print(
                    f"[green]✓ Auto-restart enabled for {deployment_id}[/green]"
                )
                return CommandResult.success_result(
                    f"Auto-restart enabled for {deployment_id}"
                )
            self.console.print(
                f"[red]✗ Failed to enable auto-restart for {deployment_id}[/red]"
            )
            return CommandResult.error_result("Failed to enable auto-restart")

        except Exception as e:
            self.logger.error(f"Failed to enable auto-restart: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _disable_auto_restart_command(self, args) -> CommandResult:
        """Disable auto-restart for a deployment."""
        try:
            deployment_id = args.deployment_id
            success = self.manager.disable_auto_restart(deployment_id)

            if success:
                self.console.print(
                    f"[green]✓ Auto-restart disabled for {deployment_id}[/green]"
                )
                return CommandResult.success_result(
                    f"Auto-restart disabled for {deployment_id}"
                )
            self.console.print(
                f"[red]✗ Failed to disable auto-restart for {deployment_id}[/red]"
            )
            return CommandResult.error_result("Failed to disable auto-restart")

        except Exception as e:
            self.logger.error(f"Failed to disable auto-restart: {e}", exc_info=True)
            self.console.print(f"[red]✗ Error: {e}[/red]")
            return CommandResult.error_result(str(e))

    def _render_status_panel(self, status: dict) -> None:
        """Render full status as a rich panel."""
        process = status.get("process", {})
        health = status.get("health", {})
        restart = status.get("restart_history", {})

        content = "[bold cyan]Process Information[/bold cyan]\n"
        content += f"  Status: {process.get('status', 'unknown')}\n"
        content += f"  PID: {process.get('pid', 'N/A')}\n"
        content += f"  Port: {process.get('port', 'N/A')}\n"
        content += f"  Uptime: {process.get('uptime_seconds', 0):.1f}s\n"
        content += f"  Memory: {process.get('memory_mb', 0):.1f} MB\n"
        content += f"  CPU: {process.get('cpu_percent', 0):.1f}%\n\n"

        if health:
            content += "[bold green]Health Status[/bold green]\n"
            content += f"  Overall: {health.get('status', 'unknown')}\n"
            content += f"  HTTP: {'✓' if health.get('http_healthy') else '✗'}\n"
            content += f"  Process: {'✓' if health.get('process_healthy') else '✗'}\n"
            content += (
                f"  Resources: {'✓' if health.get('resource_healthy') else '✗'}\n\n"
            )

        if restart:
            content += "[bold yellow]Restart Statistics[/bold yellow]\n"
            content += f"  Total Restarts: {restart.get('total_restarts', 0)}\n"
            content += f"  Successful: {restart.get('successful_restarts', 0)}\n"
            content += f"  Failed: {restart.get('failed_restarts', 0)}\n"
            content += f"  Auto-restart: {'Enabled' if restart.get('auto_restart_enabled') else 'Disabled'}"

        self.console.print(
            Panel(
                content,
                title=f"Status: {status.get('deployment_id', 'Unknown')}",
                border_style="cyan",
            )
        )

    def _render_live_status(self, status: dict) -> Panel:
        """Render status for live monitoring."""
        process = status.get("process", {})
        health = status.get("health", {})

        content = Text()
        content.append("Process Status\n", style="bold cyan")
        content.append(f"  PID: {process.get('pid', 'N/A')}\n")
        content.append(f"  Status: {process.get('status', 'unknown')}\n")
        content.append(f"  Uptime: {process.get('uptime_seconds', 0):.1f}s\n")
        content.append(f"  Memory: {process.get('memory_mb', 0):.1f} MB\n")
        content.append(f"  CPU: {process.get('cpu_percent', 0):.1f}%\n\n")

        if health:
            health_status = health.get("status", "unknown")
            health_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
            }.get(health_status, "white")

            content.append("Health Status\n", style="bold green")
            content.append("  Overall: ", style="white")
            content.append(f"{health_status.upper()}\n", style=health_color)
            content.append(
                f"  Checks: HTTP={'✓' if health.get('http_healthy') else '✗'} "
                f"Process={'✓' if health.get('process_healthy') else '✗'} "
                f"Resources={'✓' if health.get('resource_healthy') else '✗'}\n"
            )

        return Panel(
            content,
            title=f"Monitoring: {status.get('deployment_id', 'Unknown')}",
            border_style="cyan",
        )


__all__ = ["LocalDeployCommand"]
