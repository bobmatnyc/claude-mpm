"""
MCP Process Pool Manager
========================

Manages a pool of MCP server processes to prevent multiple instances
and reduce startup overhead through connection reuse.

WHY: MCP vector search servers load 400MB+ indexes on startup causing 11.9s delays.
By maintaining a process pool and reusing connections, we eliminate this overhead.

DESIGN DECISIONS:
- Singleton process pool shared across all agent invocations
- Pre-warm processes during framework initialization
- Health checks and automatic restart of failed processes
- Graceful shutdown and resource cleanup
"""

import asyncio
import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.config.paths import paths
from claude_mpm.core.logger import get_logger


class MCPProcessPool:
    """
    Manages a pool of MCP server processes for efficient resource utilization.

    WHY: Prevent multiple MCP server instances from being spawned and
    reduce startup overhead by reusing existing processes.
    """

    _instance: Optional["MCPProcessPool"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the process pool manager."""
        if self._initialized:
            return

        self.logger = get_logger("MCPProcessPool")
        self._initialized = True

        # Process tracking
        self._processes: Dict[str, subprocess.Popen] = {}
        self._process_info: Dict[str, Dict] = {}
        self._startup_times: Dict[str, float] = {}

        # Configuration
        self.max_processes = 3  # Maximum number of pooled processes
        self.process_timeout = 300  # 5 minutes idle timeout
        self.health_check_interval = 30  # Check process health every 30s

        # Paths
        self.pool_dir = paths.claude_mpm_dir_hidden / "mcp" / "pool"
        self.pool_dir.mkdir(parents=True, exist_ok=True)

        # Pre-warming flag
        self._pre_warmed = False

        # Background health check task
        self._health_check_task: Optional[asyncio.Task] = None

        # Setup cleanup handlers
        self._setup_cleanup_handlers()

        self.logger.info("MCP Process Pool initialized")

    def _setup_cleanup_handlers(self):
        """Setup signal handlers for cleanup on termination."""

        def cleanup_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, cleaning up process pool")
            self.cleanup_all()

        signal.signal(signal.SIGTERM, cleanup_handler)
        signal.signal(signal.SIGINT, cleanup_handler)

    def get_or_create_process(
        self, server_name: str, config: Dict
    ) -> Optional[subprocess.Popen]:
        """
        Get an existing process or create a new one for the given server.

        Args:
            server_name: Name of the MCP server
            config: Server configuration including command and args

        Returns:
            Process handle or None if failed
        """
        start_time = time.time()

        # Check if we have a healthy existing process
        if server_name in self._processes:
            process = self._processes[server_name]
            if self._is_process_healthy(process):
                self.logger.info(
                    f"Reusing existing process for {server_name} (PID: {process.pid})"
                )
                return process
            # Process is dead, clean it up
            self.logger.warning(f"Process for {server_name} is dead, cleaning up")
            self._cleanup_process(server_name)

        # Check if we've hit the process limit
        if len(self._processes) >= self.max_processes:
            # Find and clean up the oldest idle process
            self._cleanup_oldest_idle_process()

        # Create new process
        self.logger.info(f"Creating new process for {server_name}")
        process = self._create_process(server_name, config)

        if process:
            create_time = time.time() - start_time
            self.logger.info(
                f"Process created for {server_name} in {create_time:.2f}s (PID: {process.pid})"
            )
            self._startup_times[server_name] = create_time

        return process

    def _create_process(
        self, server_name: str, config: Dict
    ) -> Optional[subprocess.Popen]:
        """
        Create a new MCP server process.

        Args:
            server_name: Name of the MCP server
            config: Server configuration

        Returns:
            Process handle or None if failed
        """
        try:
            # Extract command and args from config
            command = config.get("command", "")
            args = config.get("args", [])
            env = config.get("env", {})
            cwd = config.get("cwd")

            # Build full command
            full_command = [command, *args]

            # Merge environment variables
            process_env = os.environ.copy()
            process_env.update(env)

            # Add timing instrumentation
            process_env["MCP_STARTUP_TRACKING"] = "1"
            process_env["MCP_SERVER_NAME"] = server_name

            # Start the process
            process = subprocess.Popen(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=process_env,
                cwd=cwd,
                bufsize=0,  # Unbuffered for real-time communication
            )

            # Store process info
            self._processes[server_name] = process
            self._process_info[server_name] = {
                "pid": process.pid,
                "started_at": time.time(),
                "last_used": time.time(),
                "config": config,
            }

            # Write process info to file for debugging
            info_file = self.pool_dir / f"{server_name}_{process.pid}.json"
            with open(info_file, "w") as f:
                json.dump(self._process_info[server_name], f, indent=2)

            return process

        except Exception as e:
            self.logger.error(f"Failed to create process for {server_name}: {e}")
            return None

    def _is_process_healthy(self, process: subprocess.Popen) -> bool:
        """Check if a process is still running and healthy."""
        if process.poll() is not None:
            # Process has terminated
            return False

        try:
            # Send signal 0 to check if process is alive
            os.kill(process.pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _cleanup_process(self, server_name: str):
        """Clean up a specific process."""
        if server_name not in self._processes:
            return

        process = self._processes[server_name]

        try:
            # Try graceful shutdown first
            if self._is_process_healthy(process):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    process.kill()
                    process.wait()

            # Remove from tracking
            del self._processes[server_name]
            del self._process_info[server_name]

            # Clean up info file
            for info_file in self.pool_dir.glob(f"{server_name}_*.json"):
                info_file.unlink()

            self.logger.info(f"Cleaned up process for {server_name}")

        except Exception as e:
            self.logger.warning(f"Error cleaning up process for {server_name}: {e}")

    def _cleanup_oldest_idle_process(self):
        """Find and clean up the oldest idle process."""
        if not self._process_info:
            return

        # Find process with oldest last_used time
        oldest_server = min(
            self._process_info.keys(),
            key=lambda k: self._process_info[k].get("last_used", 0),
        )

        self.logger.info(f"Cleaning up oldest idle process: {oldest_server}")
        self._cleanup_process(oldest_server)

    async def pre_warm_servers(self, configs: Dict[str, Dict]):
        """
        Pre-warm MCP servers during framework initialization.

        Args:
            configs: Dictionary of server configurations
        """
        if self._pre_warmed:
            self.logger.info("Servers already pre-warmed")
            return

        self.logger.info(f"Pre-warming {len(configs)} MCP servers")
        start_time = time.time()

        # Start all servers in parallel
        for server_name, config in configs.items():
            # Only pre-warm critical servers (like vector search)
            if "vector" in server_name.lower() or config.get("pre_warm", False):
                self.logger.info(f"Pre-warming {server_name}")
                process = self.get_or_create_process(server_name, config)
                if process:
                    self.logger.info(f"Pre-warmed {server_name} (PID: {process.pid})")

        self._pre_warmed = True
        total_time = time.time() - start_time
        self.logger.info(f"Pre-warming completed in {total_time:.2f}s")

    async def start_health_monitoring(self):
        """Start background health monitoring of processes."""
        if self._health_check_task and not self._health_check_task.done():
            return

        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Started health monitoring")

    async def _health_check_loop(self):
        """Background loop to check process health."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                # Check each process
                dead_processes = []
                for server_name, process in self._processes.items():
                    if not self._is_process_healthy(process):
                        dead_processes.append(server_name)

                # Clean up dead processes
                for server_name in dead_processes:
                    self.logger.warning(f"Process {server_name} is dead, cleaning up")
                    self._cleanup_process(server_name)

                # Check for idle timeout
                current_time = time.time()
                idle_processes = []
                for server_name, info in self._process_info.items():
                    last_used = info.get("last_used", current_time)
                    if current_time - last_used > self.process_timeout:
                        idle_processes.append(server_name)

                # Clean up idle processes
                for server_name in idle_processes:
                    self.logger.info(f"Process {server_name} idle timeout, cleaning up")
                    self._cleanup_process(server_name)

            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")

    def mark_process_used(self, server_name: str):
        """Mark a process as recently used."""
        if server_name in self._process_info:
            self._process_info[server_name]["last_used"] = time.time()

    def get_startup_metrics(self) -> Dict[str, float]:
        """Get startup time metrics for all servers."""
        return self._startup_times.copy()

    def get_pool_status(self) -> Dict[str, Any]:
        """Get current status of the process pool."""
        return {
            "active_processes": len(self._processes),
            "max_processes": self.max_processes,
            "pre_warmed": self._pre_warmed,
            "processes": {
                name: {
                    "pid": info.get("pid"),
                    "uptime": time.time() - info.get("started_at", time.time()),
                    "idle_time": time.time() - info.get("last_used", time.time()),
                }
                for name, info in self._process_info.items()
            },
            "startup_metrics": self._startup_times,
        }

    def cleanup_all(self):
        """Clean up all processes in the pool."""
        self.logger.info("Cleaning up all processes in pool")

        # Stop health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()

        # Clean up all processes
        for server_name in list(self._processes.keys()):
            self._cleanup_process(server_name)

        self.logger.info("Process pool cleanup completed")


# Global instance
_pool: Optional[MCPProcessPool] = None


def get_process_pool() -> MCPProcessPool:
    """Get the global MCP process pool instance."""
    global _pool
    if _pool is None:
        _pool = MCPProcessPool()
    return _pool


async def pre_warm_mcp_servers():
    """Pre-warm MCP servers from configuration."""
    pool = get_process_pool()

    # Load MCP configurations
    configs = {}

    # Check .claude.json for MCP server configs
    claude_config_path = Path.home() / ".claude.json"
    if not claude_config_path.exists():
        # Try project-local config
        claude_config_path = Path.cwd() / ".claude.json"

    if claude_config_path.exists():
        try:
            with open(claude_config_path) as f:
                config_data = json.load(f)
                mcp_servers = config_data.get("mcpServers", {})
                configs.update(mcp_servers)
        except Exception as e:
            get_logger("MCPProcessPool").warning(f"Failed to load Claude config: {e}")

    # Check .mcp.json for additional configs
    mcp_config_path = Path.cwd() / ".mcp.json"
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path) as f:
                config_data = json.load(f)
                mcp_servers = config_data.get("mcpServers", {})
                configs.update(mcp_servers)
        except Exception as e:
            get_logger("MCPProcessPool").warning(f"Failed to load MCP config: {e}")

    if configs:
        await pool.pre_warm_servers(configs)
        await pool.start_health_monitoring()

    return pool
