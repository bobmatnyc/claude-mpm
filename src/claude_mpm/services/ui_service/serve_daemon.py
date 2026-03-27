"""
Serve Daemon — wraps the FastAPI ui_service with daemon lifecycle.

WHY: The ui_service FastAPI app already implements the full session management
API.  This module provides the "outer shell" that lets operators run it as a
background daemon via `claude-mpm serve start --background`, with proper PID
file management, log redirection, and (optional) ChannelHub integration.

DESIGN DECISIONS:
- PID and log files live in ~/.claude-mpm/ (global, not CWD-relative) because
  the serve daemon is a *user-level* service, not project-scoped.
- Env marker CLAUDE_MPM_SERVE_DAEMON=1 prevents recursive subprocess creation
  (separate from CLAUDE_MPM_SUBPROCESS_DAEMON=1 used by the monitor daemon).
- start_daemon_subprocess() is overridden so DaemonManager calls
  `claude-mpm serve start --background` rather than `monitor start`.
- When --channels is supplied, ChannelHub runs inside the same asyncio event
  loop via asyncio.gather(uvicorn_serve, channel_hub.start()).
- The /health endpoint (already in app.py) is augmented here to return the
  expected service identifier so DaemonManager.is_our_service() works.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

from ...core.logging_config import get_logger
from ...services.monitor.daemon_manager import DaemonManager

logger = get_logger(__name__)

# Environment variable used to break the recursive subprocess loop.
_SERVE_DAEMON_ENV_KEY = "CLAUDE_MPM_SERVE_DAEMON"


def _global_pid_file(port: int) -> Path:
    """Return a global (home-dir) PID file path for the serve daemon."""
    base = Path.home() / ".claude-mpm"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"serve-{port}.pid"


def _global_log_file(port: int) -> Path:
    """Return a global (home-dir) log file path for the serve daemon."""
    log_dir = Path.home() / ".claude-mpm" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"serve-{port}.log"


class ServeDaemon:
    """Lifecycle wrapper for the FastAPI ui_service daemon.

    Usage::

        daemon = ServeDaemon(host="127.0.0.1", port=7777)
        daemon.start()   # launches background process and returns
        daemon.stop()    # sends SIGTERM
        daemon.status()  # returns a dict describing current state

    Attributes:
        host: Host address to bind to.
        port: Port to listen on.
        daemon_mode: True → launch as detached background process.
        channels: Optional list of channel adapter names to enable.
        project_root: Default working directory for new sessions.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7777,
        daemon_mode: bool = True,
        channels: list[str] | None = None,
        project_root: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.daemon_mode = daemon_mode
        self.channels = channels or []
        self.project_root = project_root

        # Build explicit global paths so DaemonManager never falls back to CWD.
        pid_path = _global_pid_file(port)
        log_path = _global_log_file(port)

        self.lifecycle = _ServeDaemonManager(
            port=port,
            host=host,
            pid_file=str(pid_path),
            log_file=str(log_path),
            channels=self.channels,
            project_root=project_root,
        )

    # ------------------------------------------------------------------
    # Public API (mirrors UnifiedMonitorDaemon)
    # ------------------------------------------------------------------

    def start(self, force_restart: bool = False) -> bool:
        """Start the daemon.

        If daemon_mode is True the daemon is launched as a detached subprocess
        and this call returns quickly.  In foreground mode the uvicorn server
        (and optional ChannelHub) run directly in this process.

        Args:
            force_restart: Kill any running instance first.

        Returns:
            True if the daemon started (or is already running).
        """
        if self.daemon_mode:
            return self.lifecycle.start_daemon(force_restart=force_restart)

        # Foreground mode — run uvicorn in-process.
        return self._run_foreground()

    def stop(self) -> bool:
        """Stop the background daemon.

        Returns:
            True if the daemon was stopped (or was not running).
        """
        return self.lifecycle.stop_daemon()

    def restart(self) -> bool:
        """Restart the daemon.

        Returns:
            True if the daemon restarted successfully.
        """
        self.stop()
        time.sleep(1)
        return self.start(force_restart=True)

    def status(self) -> dict:
        """Return a dict describing the current daemon state.

        Returns:
            Dict with keys: running, host, port, pid (optional).
        """
        running = self.lifecycle.is_running()
        pid = self.lifecycle.get_pid() if running else None
        return {
            "service": "claude-mpm-serve",
            "running": running,
            "host": self.host,
            "port": self.port,
            "pid": pid,
            "url": f"http://{self.host}:{self.port}" if running else None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_foreground(self) -> bool:
        """Run uvicorn (and optional ChannelHub) in the current process."""
        # Write PID file so stop/status work correctly.
        try:
            self.lifecycle.write_pid_file()
            self.lifecycle._setup_signal_handlers()
        except Exception as exc:
            logger.warning("Could not write PID file: %s", exc)

        try:
            asyncio.run(self._async_serve())
        except KeyboardInterrupt:
            logger.info("Serve daemon interrupted by user")
        finally:
            self.lifecycle.cleanup_pid_file()

        return True

    async def _async_serve(self) -> None:
        """Async entry-point: uvicorn + optional ChannelHub."""
        import uvicorn

        from .app import create_app
        from .config import UIServiceConfig

        cfg = UIServiceConfig(
            host=self.host,
            port=self.port,
        )
        app = create_app(cfg)

        # Patch the /health endpoint to include the service identifier.
        _patch_health_endpoint(app)

        uv_config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        uv_server = uvicorn.Server(uv_config)

        if self.channels:
            await self._serve_with_channels(uv_server)
        else:
            await uv_server.serve()

    async def _serve_with_channels(self, uv_server) -> None:
        """Run uvicorn and ChannelHub concurrently in a single event loop."""
        try:
            from ...services.channels.channel_hub import (
                ChannelHub,  # type: ignore[import-not-found]
            )

            hub = ChannelHub(adapters=self.channels)
            await asyncio.gather(
                uv_server.serve(),
                hub.start(),
                return_exceptions=True,
            )
        except ImportError:
            logger.warning("ChannelHub not available; running without channels")
            await uv_server.serve()


class _ServeDaemonManager(DaemonManager):
    """DaemonManager subclass that launches `serve start` instead of `monitor start`.

    Overrides start_daemon_subprocess() so the subprocess runs::

        python -m claude_mpm.cli serve start --background --port N --host H

    instead of the monitor start command baked into the base class.
    """

    def __init__(
        self,
        port: int,
        host: str,
        pid_file: str,
        log_file: str,
        channels: list[str] | None = None,
        project_root: str | None = None,
    ) -> None:
        super().__init__(port=port, host=host, pid_file=pid_file, log_file=log_file)
        self._channels = channels or []
        self._project_root = project_root

    def use_subprocess_daemon(self) -> bool:
        """Use subprocess mode unless we are already inside the subprocess."""
        if os.environ.get(_SERVE_DAEMON_ENV_KEY) == "1":
            return False
        return True

    def start_daemon_subprocess(self, force_restart: bool = False) -> bool:
        """Start the serve daemon via a detached subprocess.

        Builds the correct `claude-mpm serve start --background` command so
        the subprocess re-enters through the CLI (not monitor) path.

        Args:
            force_restart: Passed through for logging context only.

        Returns:
            True if the daemon subprocess started and the port/PID file appeared.
        """
        try:
            python_exe = sys.executable

            cmd = [
                python_exe,
                "-m",
                "claude_mpm.cli",
                "serve",
                "start",
                "--background",
                "--port",
                str(self.port),
                "--host",
                self.host,
            ]

            if self._channels:
                cmd += ["--channels", ",".join(self._channels)]
            if self._project_root:
                cmd += ["--project-root", self._project_root]

            # Mark environment so the re-entered subprocess doesn't recurse.
            env = os.environ.copy()
            env[_SERVE_DAEMON_ENV_KEY] = "1"

            logger.info(
                "Starting serve daemon via subprocess: %s (force_restart=%s)",
                " ".join(cmd),
                force_restart,
            )

            log_file_handle = None
            if self.log_file:
                log_file_handle = Path(str(self.log_file)).open("a")
                log_target = log_file_handle
            else:
                log_target = subprocess.DEVNULL

            try:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=log_target,
                    stderr=subprocess.STDOUT if self.log_file else subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=(not self.log_file),
                    env=env,
                )
            finally:
                if log_file_handle and not log_file_handle.closed:
                    log_file_handle.close()

            pid = process.pid
            logger.info("Serve subprocess started with PID %s", pid)

            # Wait for port to be bound and PID file to appear (max 30 s).
            max_wait = int(os.environ.get("CLAUDE_MPM_SERVE_TIMEOUT", "30"))
            start_time = time.time()
            pid_found = False
            port_bound = False

            while time.time() - start_time < max_wait:
                if process.poll() is not None:
                    logger.error(
                        "Serve daemon subprocess exited prematurely (code %s)",
                        process.returncode,
                    )
                    return False

                if not pid_found and self.pid_file.exists():
                    try:
                        with self.pid_file.open() as f:
                            written_pid = int(f.read().strip())
                        if written_pid == pid:
                            pid_found = True
                            logger.debug("PID file found with PID %s", pid)
                    except Exception:
                        pass

                if not port_bound and not self._is_port_available():
                    port_bound = True
                    logger.debug("Port %s is now bound", self.port)

                if pid_found and port_bound:
                    logger.info(
                        "Serve daemon started on port %s (PID: %s)", self.port, pid
                    )
                    return True

                time.sleep(0.5)

            logger.error("Timeout waiting for serve daemon to start")
            if process.poll() is None:
                process.terminate()
                time.sleep(1)
                if process.poll() is None:
                    process.kill()
            return False

        except Exception as exc:
            logger.error("Failed to start serve daemon via subprocess: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Helper — patch the health endpoint to include service identifier
# ---------------------------------------------------------------------------


def _patch_health_endpoint(app) -> None:
    """Add a /health root endpoint (not under /api/v1) returning service info.

    The DaemonManager.is_our_service() method checks GET /health and looks
    for "claude" or "mpm" in the response body.  The existing /api/v1/health
    endpoint in app.py satisfies that requirement, but we also register a
    bare /health for compatibility with tools that do not include the prefix.
    """
    from fastapi.responses import JSONResponse

    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def _health_root() -> JSONResponse:  # type: ignore[misc]
        return JSONResponse(
            {
                "service": "claude-mpm-serve",
                "status": "healthy",
            }
        )
