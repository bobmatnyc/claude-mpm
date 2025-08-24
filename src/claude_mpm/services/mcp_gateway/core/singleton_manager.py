"""
MCP Gateway Singleton Manager
============================

Provides singleton management for MCP Gateway instances to ensure only one
gateway is running per claude-mpm installation.

WHY: MCP gateways are stdio-based protocol handlers that should have only one
instance per installation to avoid conflicts and resource contention.

DESIGN DECISIONS:
- File-based locking for cross-process coordination
- PID tracking for instance validation
- Automatic cleanup on process termination
- Thread-safe singleton pattern
"""

import contextlib
import fcntl
import json
import os
import signal
import threading
import time
from typing import Any, Dict, Optional

from claude_mpm.config.paths import paths
from claude_mpm.core.logger import get_logger


class MCPGatewayManager:
    """
    Singleton manager for MCP Gateway instances.

    Ensures only one gateway instance is running per installation using
    file-based locking and PID tracking.
    """

    _instance: Optional["MCPGatewayManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the gateway manager."""
        if self._initialized:
            return

        self.logger = get_logger("MCPGatewayManager")
        self._initialized = True

        # Paths for coordination
        self.mcp_dir = paths.claude_mpm_dir_hidden / "mcp"
        self.lock_file = self.mcp_dir / "gateway.lock"
        self.instance_file = self.mcp_dir / "gateway.json"

        # Ensure directory exists
        self.mcp_dir.mkdir(parents=True, exist_ok=True)

        # Lock file handle
        self._lock_fd: Optional[int] = None
        self._current_instance: Optional[Dict[str, Any]] = None

        # Setup cleanup handlers
        self._setup_cleanup_handlers()

    def _setup_cleanup_handlers(self):
        """Setup signal handlers for cleanup on termination."""

        def cleanup_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, cleaning up gateway")
            self.cleanup()

        signal.signal(signal.SIGTERM, cleanup_handler)
        signal.signal(signal.SIGINT, cleanup_handler)

    def acquire_lock(self) -> bool:
        """
        Acquire exclusive lock for gateway instance.

        Returns:
            True if lock acquired successfully, False otherwise
        """
        try:
            # Open lock file
            self._lock_fd = os.open(
                self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            )

            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write current PID to lock file
            os.write(self._lock_fd, str(os.getpid()).encode())
            os.fsync(self._lock_fd)

            self.logger.info(f"Acquired gateway lock (PID: {os.getpid()})")
            return True

        except OSError as e:
            if self._lock_fd:
                with contextlib.suppress(Exception):
                    os.close(self._lock_fd)
                self._lock_fd = None

            self.logger.debug(f"Failed to acquire gateway lock: {e}")
            return False

    def release_lock(self):
        """Release the gateway lock."""
        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
                self._lock_fd = None

                # Remove lock file
                if self.lock_file.exists():
                    self.lock_file.unlink()

                self.logger.info("Released gateway lock")
            except Exception as e:
                self.logger.warning(f"Error releasing lock: {e}")

    def is_gateway_running(self) -> bool:
        """
        Check if a gateway instance is currently running.

        Returns:
            True if gateway is running, False otherwise
        """
        instance_info = self.get_running_instance_info()
        return instance_info is not None

    def get_running_instance_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently running gateway instance.

        Returns:
            Instance information dict or None if no instance running
        """
        if not self.instance_file.exists():
            return None

        try:
            with open(self.instance_file) as f:
                instance_info = json.load(f)

            # Validate PID is still running
            pid = instance_info.get("pid")
            if pid and self._is_pid_running(pid):
                return instance_info
            # Stale instance file, remove it
            self.instance_file.unlink()
            return None

        except (json.JSONDecodeError, OSError) as e:
            self.logger.warning(f"Error reading instance file: {e}")
            return None

    def _is_pid_running(self, pid: int) -> bool:
        """Check if a PID is currently running."""
        try:
            os.kill(pid, 0)  # Signal 0 just checks if process exists
            return True
        except (OSError, ProcessLookupError):
            return False

    def register_instance(self, gateway_name: str, version: str) -> bool:
        """
        Register a new gateway instance.

        Args:
            gateway_name: Name of the gateway
            version: Gateway version

        Returns:
            True if registration successful, False otherwise
        """
        if not self.acquire_lock():
            return False

        try:
            instance_info = {
                "pid": os.getpid(),
                "gateway_name": gateway_name,
                "version": version,
                "started_at": time.time(),
                "lock_file": str(self.lock_file),
            }

            with open(self.instance_file, "w") as f:
                json.dump(instance_info, f, indent=2)

            self._current_instance = instance_info
            self.logger.info(f"Registered gateway instance: {gateway_name} v{version}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register instance: {e}")
            self.release_lock()
            return False

    def cleanup(self):
        """Clean up gateway instance and release resources."""
        try:
            # Remove instance file
            if self.instance_file.exists():
                self.instance_file.unlink()

            # Release lock
            self.release_lock()

            self._current_instance = None
            self.logger.info("Gateway cleanup completed")

        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")


# Global functions for easy access
_manager: Optional[MCPGatewayManager] = None


def get_gateway_manager() -> MCPGatewayManager:
    """Get the global gateway manager instance."""
    global _manager
    if _manager is None:
        _manager = MCPGatewayManager()
    return _manager


def is_gateway_running() -> bool:
    """Check if a gateway instance is currently running."""
    return get_gateway_manager().is_gateway_running()


def get_gateway_status() -> Optional[Dict[str, Any]]:
    """Get status of running gateway instance."""
    return get_gateway_manager().get_running_instance_info()


async def start_global_gateway(
    gateway_name: str = "claude-mpm-mcp", version: str = "1.0.0"
) -> bool:
    """
    Start the global MCP gateway instance.

    Args:
        gateway_name: Name for the gateway
        version: Gateway version

    Returns:
        True if started successfully, False otherwise
    """
    manager = get_gateway_manager()

    # Check if already running
    if manager.is_gateway_running():
        instance_info = manager.get_running_instance_info()
        manager.logger.info(
            f"Gateway already running (PID: {instance_info.get('pid')})"
        )
        return True

    # Register new instance
    if not manager.register_instance(gateway_name, version):
        manager.logger.error("Failed to register gateway instance")
        return False

    # Import and start the gateway
    try:
        from ..main import MCPGatewayOrchestrator

        orchestrator = MCPGatewayOrchestrator()

        if not await orchestrator.initialize():
            manager.logger.error("Failed to initialize gateway")
            manager.cleanup()
            return False

        if not await orchestrator.start():
            manager.logger.error("Failed to start gateway")
            manager.cleanup()
            return False

        manager.logger.info("Global gateway started successfully")
        return True

    except Exception as e:
        manager.logger.error(f"Error starting gateway: {e}")
        manager.cleanup()
        return False


async def run_global_gateway():
    """Run the global MCP gateway until shutdown."""
    manager = get_gateway_manager()

    try:
        from ..main import MCPGatewayOrchestrator

        orchestrator = MCPGatewayOrchestrator()
        await orchestrator.run()

    except Exception as e:
        manager.logger.error(f"Error running gateway: {e}")
    finally:
        manager.cleanup()
