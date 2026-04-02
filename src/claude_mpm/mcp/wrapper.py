#!/usr/bin/env python3
"""
MCP Server Robust Wrapper
=========================

This wrapper ensures the Python environment is correctly set up regardless of how it's invoked.
It handles various edge cases and provides clear error messages for troubleshooting.

WHY: Claude Code may invoke this script in different ways (as module, script, different working dirs),
so we need a robust wrapper that handles all cases and sets up the environment correctly.

DESIGN DECISION: Use comprehensive environment detection and setup with clear error reporting
to make debugging easier when things go wrong.
"""

import atexit
import json
import logging
import os
import signal
import sys
import tempfile
import traceback
from datetime import UTC, datetime
from pathlib import Path


def setup_stderr_logging():
    """Configure logging to stderr to avoid interfering with stdio protocol."""
    logging.basicConfig(
        level=logging.DEBUG,  # Use DEBUG for maximum information during troubleshooting
        format="[MCP-WRAPPER] %(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=True,  # Force reconfiguration if already configured
    )
    return logging.getLogger("MCPWrapper")


class ProcessMonitor:
    """
    Monitor and manage the MCP server process.

    WHY: We need to track process lifecycle, detect duplicate instances,
    and ensure clean shutdown to prevent memory leaks.
    """

    def __init__(self, logger):
        """Initialize the process monitor."""
        self.logger = logger
        self.pid = os.getpid()
        self.start_time = datetime.now(UTC)
        self.pid_file = None
        self.setup_pid_tracking()
        self.setup_signal_handlers()

    def setup_pid_tracking(self):
        """Set up PID file for process tracking."""
        # Create PID file in temp directory
        pid_dir = Path(tempfile.gettempdir()) / "claude-mpm-mcp"
        pid_dir.mkdir(exist_ok=True)

        self.pid_file = pid_dir / f"mcp_server_{self.pid}.pid"

        # Write process info to PID file
        pid_info = {
            "pid": self.pid,
            "start_time": self.start_time.isoformat(),
            "python": sys.executable,
            "cwd": str(Path.cwd()),
            "ppid": os.getppid() if hasattr(os, "getppid") else None,
        }

        try:
            with open(self.pid_file, "w") as f:
                json.dump(pid_info, f, indent=2)
            self.logger.info(f"Process tracking file created: {self.pid_file}")

            # Register cleanup on exit
            atexit.register(self.cleanup_pid_file)
        except Exception as e:
            self.logger.warning(f"Could not create PID file: {e}")

    def cleanup_pid_file(self):
        """Remove PID file on exit."""
        if self.pid_file and self.pid_file.exists():
            try:
                self.pid_file.unlink()
                self.logger.info(f"Cleaned up PID file: {self.pid_file}")
            except Exception as e:
                self.logger.warning(f"Could not remove PID file: {e}")

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received signal {signal_name} ({signum})")
            self.logger.info("Initiating graceful shutdown...")
            self.cleanup_pid_file()
            sys.exit(0)

        # Register handlers for common termination signals
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            if hasattr(signal, "SIGHUP"):
                signal.signal(signal.SIGHUP, signal_handler)
            self.logger.info("Signal handlers registered for graceful shutdown")
        except Exception as e:
            self.logger.warning(f"Could not set up all signal handlers: {e}")

    def check_for_other_instances(self):
        """Check if other MCP server instances are running."""
        pid_dir = Path(tempfile.gettempdir()) / "claude-mpm-mcp"
        if not pid_dir.exists():
            return []

        other_instances = []
        for pid_file in pid_dir.glob("mcp_server_*.pid"):
            if pid_file == self.pid_file:
                continue

            try:
                with open(pid_file) as f:
                    info = json.load(f)

                # Check if process is still running
                pid = info.get("pid")
                if pid and self.is_process_running(pid):
                    other_instances.append(info)
                else:
                    # Clean up stale PID file
                    pid_file.unlink()
                    self.logger.info(f"Cleaned up stale PID file for process {pid}")
            except Exception as e:
                self.logger.debug(f"Could not read PID file {pid_file}: {e}")

        return other_instances

    def is_process_running(self, pid):
        """Check if a process with given PID is running."""
        try:
            # Send signal 0 to check if process exists
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def log_process_info(self):
        """Log information about the current process."""
        self.logger.info("Process Information:")
        self.logger.info(f"  PID: {self.pid}")
        self.logger.info(
            f"  Parent PID: {os.getppid() if hasattr(os, 'getppid') else 'unknown'}"
        )
        self.logger.info(f"  Start time: {self.start_time.isoformat()}")

        # Check for other instances
        other_instances = self.check_for_other_instances()
        if other_instances:
            self.logger.warning(
                f"Found {len(other_instances)} other MCP server instance(s) running:"
            )
            for instance in other_instances:
                self.logger.warning(
                    f"  - PID {instance['pid']} started at {instance['start_time']}"
                )
        else:
            self.logger.info("No other MCP server instances detected")


def find_project_root():
    """
    Find the project root directory by looking for pyproject.toml.

    Returns:
        Path: The project root directory path

    Raises:
        RuntimeError: If project root cannot be found
    """
    # Start from this module's location (src/claude_mpm/mcp/wrapper.py)
    current = Path(__file__).resolve().parent

    # Look up the directory tree for pyproject.toml
    for _ in range(8):  # Limit search depth to avoid infinite loops
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    # If not found, try common locations
    common_locations = [
        Path("/Users/masa/Projects/claude-mpm"),
        Path.home() / "Projects" / "claude-mpm",
        Path.cwd(),
    ]

    for location in common_locations:
        if location.exists() and (location / "pyproject.toml").exists():
            return location

    raise RuntimeError(
        "Could not find project root (no pyproject.toml found). "
        f"Started search from: {Path(__file__).resolve()}"
    )


def verify_environment(logger, project_root):
    """
    Verify the Python environment is correctly set up.

    Args:
        logger: Logger instance
        project_root: Path to project root

    Returns:
        dict: Environment information

    Raises:
        RuntimeError: If environment verification fails
    """
    env_info = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "python_executable": sys.executable,
        "working_directory": str(Path.cwd()),
        "project_root": str(project_root),
        "module_location": __file__,
        "sys_path": sys.path[:5],  # First 5 entries for brevity
    }

    logger.info("Environment Information:")
    for key, value in env_info.items():
        logger.info(f"  {key}: {value}")

    # Check project structure
    src_dir = project_root / "src"
    if not src_dir.exists():
        raise RuntimeError(
            f"Source directory not found at {src_dir}. "
            f"Project root might be incorrect: {project_root}"
        )

    claude_mpm_dir = src_dir / "claude_mpm"
    if not claude_mpm_dir.exists():
        raise RuntimeError(
            f"claude_mpm package not found at {claude_mpm_dir}. "
            f"Project structure might be damaged."
        )

    # Check for required files
    required_files = [
        project_root / "pyproject.toml",
        claude_mpm_dir / "__init__.py",
    ]

    for file_path in required_files:
        if not file_path.exists():
            raise RuntimeError(f"Required file not found: {file_path}")

    return env_info


def setup_python_path(logger, project_root):
    """
    Set up Python path to ensure claude_mpm can be imported.

    Args:
        logger: Logger instance
        project_root: Path to project root
    """
    src_dir = str(project_root / "src")

    # Add src directory to Python path if not already there
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
        logger.info(f"Added {src_dir} to Python path")
    else:
        logger.info(f"Source directory already in Python path: {src_dir}")

    # Also add project root for scripts access
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        logger.info(f"Added {project_root_str} to Python path")


def test_imports(logger):
    """
    Test that required modules can be imported.

    Args:
        logger: Logger instance

    Raises:
        ImportError: If required modules cannot be imported
    """
    logger.info("Testing module imports...")

    try:
        import claude_mpm

        logger.info(f"  ✓ claude_mpm imported from: {claude_mpm.__file__}")
    except ImportError as e:
        raise ImportError(f"Failed to import claude_mpm: {e}") from e

    # MCP gateway sub-package was removed in v6.x.
    # Skip stdio_server / SimpleMCPServer import checks.
    logger.info("  - MCP gateway imports skipped (removed in v6.x)")

    try:
        import asyncio  # noqa: F401

        logger.info("  ✓ asyncio module available")
    except ImportError as e:
        raise ImportError(f"Failed to import asyncio: {e}") from e

    try:
        import mcp

        logger.info(f"  ✓ mcp package imported from: {mcp.__file__}")
    except ImportError as e:
        logger.warning(f"MCP package not installed: {e}")
        logger.warning("Some MCP functionality may be limited")


def run_mcp_server(logger):
    """
    Run the actual MCP server.

    Args:
        logger: Logger instance

    Raises:
        Exception: If server fails to start
    """
    logger.info("Starting MCP Gateway Server...")

    logger.error(
        "MCP Gateway server was removed in v6.x. "
        "Use Claude Code's native MCP management instead."
    )
    raise RuntimeError("MCP Gateway server removed in v6.x")


def main():
    """Main entry point for the MCP wrapper."""
    # Setup logging first
    logger = setup_stderr_logging()

    logger.info("=" * 60)
    logger.info("MCP Server Wrapper Starting")
    logger.info("=" * 60)

    # Initialize process monitor
    monitor = ProcessMonitor(logger)
    monitor.log_process_info()

    try:
        # Find project root
        logger.info("Step 1: Finding project root...")
        project_root = find_project_root()
        logger.info(f"  Found project root: {project_root}")

        # Verify environment
        logger.info("Step 2: Verifying environment...")
        verify_environment(logger, project_root)

        # Setup Python path
        logger.info("Step 3: Setting up Python path...")
        setup_python_path(logger, project_root)

        # Apply env var defaults (respects existing shell values)
        from claude_mpm.core.env_defaults import apply_env_defaults

        apply_env_defaults()

        # Test imports
        logger.info("Step 4: Testing required imports...")
        test_imports(logger)

        # Run the server
        logger.info("Step 5: Starting MCP server...")
        logger.info("=" * 60)
        run_mcp_server(logger)

    except Exception as e:
        logger.error("=" * 60)
        logger.error("FATAL ERROR: MCP Server Wrapper Failed")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
        logger.error("Troubleshooting steps:")
        logger.error("1. Ensure claude-mpm is installed: pip install -e .")
        logger.error("2. Check Python version is 3.12+: python3 --version")
        logger.error("3. Verify project structure is intact")
        logger.error("4. Check Claude Code config points to this wrapper")
        logger.error("=" * 60)
        sys.exit(1)


def entry_point():
    """Callable entry point when imported as a module."""
    main()


if __name__ in {"__main__"}:
    main()
