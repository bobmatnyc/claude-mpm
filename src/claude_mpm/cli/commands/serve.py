"""
Serve command implementation for claude-mpm.

WHY: This module provides CLI commands for managing the global session runner
daemon (the FastAPI ui_service).  It mirrors the monitor command structure so
operators have a consistent mental model for daemon lifecycle management.

DESIGN DECISIONS:
- PID file: ~/.claude-mpm/serve-{port}.pid  (global, not CWD-relative)
- Log file: ~/.claude-mpm/logs/serve-{port}.log  (global)
- Instantiates ServeDaemon instead of UnifiedMonitorDaemon
- Exports manage_serve(args) as the main entry point
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ...core.logging_config import get_logger
from ...services.ui_service.serve_daemon import ServeDaemon
from ..shared import BaseCommand, CommandResult

logger = get_logger(__name__)


class ServeCommand(BaseCommand):
    """CLI command for managing the global session runner daemon."""

    def __init__(self):
        super().__init__("serve")
        self._daemon: ServeDaemon | None = None

    def validate_args(self, args) -> str | None:
        """Validate CLI arguments.

        Returns:
            Error message string, or None if arguments are valid.
        """
        serve_command = getattr(args, "serve_command", None)
        valid = {"start", "stop", "restart", "status"}
        if serve_command and serve_command not in valid:
            return (
                f"Unknown serve command: {serve_command}. "
                f"Valid commands: {', '.join(sorted(valid))}"
            )
        return None

    def run(self, args) -> CommandResult:
        """Route to the appropriate subcommand handler.

        Args:
            args: Parsed CLI arguments.

        Returns:
            CommandResult indicating success or failure.
        """
        serve_command = getattr(args, "serve_command", None) or "status"

        try:
            if serve_command == "start":
                return self._start(args)
            if serve_command == "stop":
                return self._stop(args)
            if serve_command == "restart":
                return self._restart(args)
            if serve_command == "status":
                return self._status(args)

            return CommandResult.error_result(f"Unknown serve command: {serve_command}")
        except Exception as exc:
            self.logger.error("Error executing serve command: %s", exc, exc_info=True)
            return CommandResult.error_result(f"Error executing serve command: {exc}")

    # ------------------------------------------------------------------
    # Subcommand handlers
    # ------------------------------------------------------------------

    def _start(self, args) -> CommandResult:
        port = getattr(args, "port", 7777)
        host = getattr(args, "host", "127.0.0.1")
        force = getattr(args, "force", False)
        channels_str = getattr(args, "channels", None)
        project_root = getattr(args, "project_root", None)

        channels: list[str] = []
        if channels_str:
            channels = [c.strip() for c in channels_str.split(",") if c.strip()]

        # Determine run mode.
        if getattr(args, "foreground", False):
            daemon_mode = False
        elif getattr(args, "background", None) is not None:
            daemon_mode = bool(getattr(args, "background", True))
        else:
            daemon_mode = True  # default to background

        mode_str = "background/daemon" if daemon_mode else "foreground"
        self.logger.info(
            "Starting serve daemon on %s:%s (mode: %s)", host, port, mode_str
        )

        daemon = ServeDaemon(
            host=host,
            port=port,
            daemon_mode=daemon_mode,
            channels=channels,
            project_root=project_root,
        )

        # Guard against already-running instance.
        if daemon.lifecycle.is_running() and not force:
            existing_pid = daemon.lifecycle.get_pid()
            return CommandResult.success_result(
                f"Serve daemon already running with PID {existing_pid}",
                data={
                    "url": f"http://{host}:{port}",
                    "port": port,
                    "pid": existing_pid,
                },
            )

        if daemon.start(force_restart=force):
            if daemon_mode:
                time.sleep(0.5)
                if not daemon.lifecycle.is_running():
                    return CommandResult.error_result(
                        "Serve daemon failed to start. "
                        f"Check {Path.home() / '.claude-mpm' / 'logs' / f'serve-{port}.log'}"
                        " for details."
                    )
                actual_pid = daemon.lifecycle.get_pid()
                mode_info = f" in background (PID: {actual_pid})"
            else:
                mode_info = " in foreground"

            return CommandResult.success_result(
                f"Serve daemon started on {host}:{port}{mode_info}",
                data={"url": f"http://{host}:{port}", "port": port, "mode": mode_str},
            )

        return CommandResult.error_result(
            "Failed to start serve daemon. "
            f"Check {Path.home() / '.claude-mpm' / 'logs' / f'serve-{port}.log'}"
            " for details."
        )

    def _stop(self, args) -> CommandResult:
        port = getattr(args, "port", 7777)

        daemon = ServeDaemon(port=port)
        if not daemon.lifecycle.is_running():
            return CommandResult.success_result("No serve daemon running")

        if daemon.stop():
            return CommandResult.success_result("Serve daemon stopped")
        return CommandResult.error_result("Failed to stop serve daemon")

    def _restart(self, args) -> CommandResult:
        port = getattr(args, "port", 7777)
        host = getattr(args, "host", "127.0.0.1")
        daemon_mode = not getattr(args, "foreground", False)
        channels_str = getattr(args, "channels", None)
        project_root = getattr(args, "project_root", None)

        channels: list[str] = []
        if channels_str:
            channels = [c.strip() for c in channels_str.split(",") if c.strip()]

        self.logger.info("Restarting serve daemon on %s:%s", host, port)

        daemon = ServeDaemon(
            host=host,
            port=port,
            daemon_mode=daemon_mode,
            channels=channels,
            project_root=project_root,
        )
        if daemon.restart():
            return CommandResult.success_result(
                f"Serve daemon restarted on {host}:{port}"
            )
        return CommandResult.error_result("Failed to restart serve daemon")

    def _status(self, args) -> CommandResult:
        port = getattr(args, "port", 7777)
        daemon = ServeDaemon(port=port)
        status_data = daemon.status()

        if status_data["running"]:
            message = f"Serve daemon is running at {status_data['url']}" + (
                f" (PID: {status_data['pid']})" if status_data.get("pid") else ""
            )
        else:
            message = "Serve daemon is not running"

        return CommandResult.success_result(message, data=status_data)


# ---------------------------------------------------------------------------
# Public entry point (used by executor.py)
# ---------------------------------------------------------------------------


def manage_serve(args) -> int:
    """Main entry point for the serve command.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    command = ServeCommand()
    error = command.validate_args(args)

    if error:
        command.logger.error(error)
        print(f"Error: {error}")
        return 1

    result = command.run(args)

    if result.success:
        if result.message:
            print(result.message)
        if result.data and getattr(args, "verbose", False):
            print(json.dumps(result.data, indent=2))
        return 0

    if result.message:
        print(f"Error: {result.message}")
    return 1
