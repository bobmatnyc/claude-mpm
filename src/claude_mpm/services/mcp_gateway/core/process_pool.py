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
import sys
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
            with info_file.open("w") as f:
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


async def auto_initialize_vector_search():
    """
    Auto-initialize mcp-vector-search for the current project.

    WHY: Vector search requires project initialization before it can be used.
    This function ensures the current project is automatically initialized
    for vector search when the system starts up.

    DESIGN DECISION:
    - Automatically install mcp-vector-search if not present
    - Run in background with timeout to avoid blocking startup
    - Failures are logged but don't prevent the system from starting
    """
    logger = get_logger("vector_search_init")

    try:
        # Import MCPConfigManager to handle installation
        from claude_mpm.services.mcp_config_manager import MCPConfigManager

        config_manager = MCPConfigManager()

        # Check if mcp-vector-search is already installed
        vector_search_path = config_manager.detect_service_path("mcp-vector-search")

        if vector_search_path:
            logger.debug(f"mcp-vector-search found at: {vector_search_path}")
        else:
            # Not installed - attempt installation
            logger.info("🔍 mcp-vector-search not found. Installing via pipx...")

            # First check if pipx is available
            import shutil
            import subprocess

            if not shutil.which("pipx"):
                logger.warning(
                    "⚠️ pipx not found. Please install pipx to enable automatic mcp-vector-search installation"
                )
                logger.info("   Install pipx with: python -m pip install --user pipx")
                return

            try:
                result = subprocess.run(
                    ["pipx", "install", "mcp-vector-search"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,  # 1 minute timeout for installation
                )

                if result.returncode == 0:
                    logger.info("✅ mcp-vector-search installed successfully")
                    # Detect the newly installed path
                    vector_search_path = config_manager.detect_service_path(
                        "mcp-vector-search"
                    )
                    if not vector_search_path:
                        logger.warning(
                            "mcp-vector-search installed but command not found in PATH"
                        )
                        return

                    # Update the Claude configuration to include the newly installed service
                    logger.info("📝 Updating Claude configuration...")
                    config_success, config_msg = (
                        config_manager.ensure_mcp_services_configured()
                    )
                    if config_success:
                        logger.info(f"✅ {config_msg}")
                    else:
                        logger.warning(f"⚠️ Configuration update issue: {config_msg}")
                else:
                    logger.warning(
                        f"Failed to install mcp-vector-search: {result.stderr}"
                    )
                    return

            except subprocess.TimeoutExpired:
                logger.warning("Installation of mcp-vector-search timed out")
                return
            except Exception as e:
                logger.warning(f"Error installing mcp-vector-search: {e}")
                return

        # At this point, mcp-vector-search should be available
        # Get the actual command to use
        import shutil

        vector_search_cmd = shutil.which("mcp-vector-search")
        if not vector_search_cmd:
            # Try pipx installation path as fallback
            pipx_path = (
                Path.home()
                / ".local/pipx/venvs/mcp-vector-search/bin/mcp-vector-search"
            )
            if pipx_path.exists():
                vector_search_cmd = str(pipx_path)
            else:
                logger.debug("mcp-vector-search command not found after installation")
                return

        # Check if current project is already initialized
        current_dir = Path.cwd()
        vector_config = current_dir / ".mcp-vector-search/config.json"

        if vector_config.exists():
            logger.debug(f"Vector search already initialized for {current_dir}")

            # Ensure .mcp-vector-search is in gitignore even if already initialized
            try:
                from ....services.project.project_organizer import ProjectOrganizer

                if (current_dir / ".claude-mpm").exists() or (
                    current_dir / ".git"
                ).exists():
                    organizer = ProjectOrganizer(current_dir)
                    organizer.update_gitignore(
                        additional_patterns=[".mcp-vector-search/"]
                    )
                    logger.debug("Ensured .mcp-vector-search is in gitignore")
            except Exception as e:
                logger.debug(f"Could not update gitignore for .mcp-vector-search: {e}")
            # Check if index needs rebuilding (corrupted database)
            chroma_db = current_dir / ".mcp-vector-search/chroma.sqlite3"
            if chroma_db.exists():
                # Quick health check - verify database file exists and is accessible
                try:
                    # Check if database file exists and has reasonable size
                    if chroma_db.exists() and chroma_db.stat().st_size > 0:
                        logger.info("✓ Vector search index is healthy and ready")
                        return
                    logger.info("⚠️ Vector search index may be corrupted, rebuilding...")
                except Exception as e:
                    logger.debug(
                        f"Vector search health check failed: {e}, will attempt to rebuild"
                    )

        # Initialize or reinitialize the project
        logger.info(f"🎯 Initializing vector search for project: {current_dir}")

        # Initialize the project (this creates the config)
        # Note: mcp-vector-search operates on the current directory
        import subprocess

        proc = subprocess.run(
            [vector_search_cmd, "init"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(current_dir),
            check=False,  # Run in the project directory
        )

        if proc.returncode == 0:
            logger.info("✅ Vector search initialization completed")

            # Ensure .mcp-vector-search is in gitignore
            try:
                from ....services.project.project_organizer import ProjectOrganizer

                # Check if we're in a git repository (parent of .claude-mpm)
                if (current_dir / ".claude-mpm").exists() or (
                    current_dir / ".git"
                ).exists():
                    organizer = ProjectOrganizer(current_dir)
                    organizer.update_gitignore(
                        additional_patterns=[".mcp-vector-search/"]
                    )
                    logger.debug("Ensured .mcp-vector-search is in gitignore")
            except Exception as e:
                logger.debug(f"Could not update gitignore for .mcp-vector-search: {e}")
                # Non-critical, don't fail initialization

            # Start background indexing (non-blocking)
            def background_index():
                try:
                    logger.info("🔄 Starting project indexing in background...")
                    index_proc = subprocess.run(
                        [vector_search_cmd, "index", "main"],
                        capture_output=True,
                        text=True,
                        timeout=300,  # 5 minute timeout for indexing
                        cwd=str(current_dir),
                        check=False,  # Run in the project directory
                    )
                    if index_proc.returncode == 0:
                        logger.info("✅ Project indexing completed successfully")
                        # Parse output to show statistics if available
                        if "indexed" in index_proc.stdout.lower():
                            # Extract and log indexing statistics
                            lines = index_proc.stdout.strip().split("\n")
                            for line in lines:
                                if "indexed" in line.lower() or "files" in line.lower():
                                    logger.info(f"   {line.strip()}")
                    else:
                        logger.warning(
                            f"⚠️ Project indexing failed: {index_proc.stderr}"
                        )
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "⚠️ Project indexing timed out (will continue in background)"
                    )
                except Exception as e:
                    logger.debug(f"Background indexing error (non-critical): {e}")

            # Run indexing in background thread
            import threading

            index_thread = threading.Thread(target=background_index, daemon=True)
            index_thread.start()
            logger.info(
                "📚 Background indexing started - vector search will be available shortly"
            )

        else:
            logger.warning(f"⚠️ Vector search initialization failed: {proc.stderr}")

    except Exception as e:
        logger.debug(f"Vector search auto-initialization error (non-critical): {e}")


async def auto_initialize_kuzu_memory():
    """
    Auto-initialize kuzu-memory for persistent knowledge storage.

    WHY: Kuzu-memory provides a graph database for structured memory storage
    with semantic search capabilities, enabling persistent context across sessions.

    DESIGN DECISION:
    - Automatically install kuzu-memory if not present via pipx
    - Initialize database in background to avoid blocking startup
    - Failures are logged but don't prevent the system from starting
    """
    logger = get_logger("kuzu_memory_init")

    try:
        # Import MCPConfigManager to handle installation
        from claude_mpm.services.mcp_config_manager import MCPConfigManager

        config_manager = MCPConfigManager()

        # Check if kuzu-memory is already installed
        kuzu_memory_path = config_manager.detect_service_path("kuzu-memory")

        if kuzu_memory_path:
            logger.debug(f"kuzu-memory found at: {kuzu_memory_path}")
        else:
            # Not installed - attempt installation
            logger.info("🧠 kuzu-memory not found. Installing via pipx...")

            # First check if pipx is available
            import shutil
            import subprocess

            if not shutil.which("pipx"):
                logger.warning(
                    "⚠️ pipx not found. Please install pipx to enable automatic kuzu-memory installation"
                )
                logger.info("   Install pipx with: python -m pip install --user pipx")
                return

            try:
                result = subprocess.run(
                    ["pipx", "install", "kuzu-memory"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,  # 1 minute timeout for installation
                )

                if result.returncode == 0:
                    logger.info("✅ kuzu-memory installed successfully")
                    # Detect the newly installed path
                    kuzu_memory_path = config_manager.detect_service_path("kuzu-memory")
                    if not kuzu_memory_path:
                        logger.warning(
                            "kuzu-memory installed but command not found in PATH"
                        )
                        return

                    # Update the Claude configuration to include the newly installed service
                    logger.info("📝 Updating Claude configuration...")
                    config_success, config_msg = (
                        config_manager.ensure_mcp_services_configured()
                    )
                    if config_success:
                        logger.info(f"✅ {config_msg}")
                    else:
                        logger.warning(f"⚠️ Configuration update issue: {config_msg}")
                else:
                    logger.warning(f"Failed to install kuzu-memory: {result.stderr}")
                    return

            except subprocess.TimeoutExpired:
                logger.warning("Installation of kuzu-memory timed out")
                return
            except Exception as e:
                logger.warning(f"Error installing kuzu-memory: {e}")
                return

        # At this point, kuzu-memory should be available
        # Get the actual command to use
        import shutil

        kuzu_memory_cmd = shutil.which("kuzu-memory")
        if not kuzu_memory_cmd:
            # Try pipx installation path as fallback
            pipx_path = Path.home() / ".local/pipx/venvs/kuzu-memory/bin/kuzu-memory"
            if pipx_path.exists():
                kuzu_memory_cmd = str(pipx_path)
            else:
                logger.debug("kuzu-memory command not found after installation")
                return

        # Check for kuzu-memory updates (non-blocking)
        try:
            await _check_kuzu_memory_updates(kuzu_memory_cmd)
        except Exception as e:
            logger.debug(f"Update check failed (non-critical): {e}")

        # Initialize kuzu-memory database in current project
        current_dir = Path.cwd()
        kuzu_memories_dir = current_dir / "kuzu-memories"

        # Check if database is already initialized
        if kuzu_memories_dir.exists():
            logger.debug(
                f"Kuzu-memory database already initialized at {kuzu_memories_dir}"
            )

            # Ensure kuzu-memories is in gitignore even if already initialized
            try:
                from ....services.project.project_organizer import ProjectOrganizer

                if (current_dir / ".claude-mpm").exists() or (
                    current_dir / ".git"
                ).exists():
                    organizer = ProjectOrganizer(current_dir)
                    organizer.update_gitignore(additional_patterns=["kuzu-memories/"])
                    logger.debug("Ensured kuzu-memories is in gitignore")
            except Exception as e:
                logger.debug(f"Could not update gitignore for kuzu-memories: {e}")
        else:
            logger.info(
                f"🎯 Initializing kuzu-memory database for project: {current_dir}"
            )

            # Initialize the database in current project directory
            import subprocess

            proc = subprocess.run(
                [kuzu_memory_cmd, "init"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(current_dir),
                check=False,
            )

            if proc.returncode == 0:
                logger.info("✅ Kuzu-memory database initialized successfully")

                # Ensure kuzu-memories is in gitignore
                try:
                    from ....services.project.project_organizer import ProjectOrganizer

                    if (current_dir / ".claude-mpm").exists() or (
                        current_dir / ".git"
                    ).exists():
                        organizer = ProjectOrganizer(current_dir)
                        organizer.update_gitignore(
                            additional_patterns=["kuzu-memories/"]
                        )
                        logger.debug("Ensured kuzu-memories is in gitignore")
                except Exception as e:
                    logger.debug(f"Could not update gitignore for kuzu-memories: {e}")
                    # Non-critical, don't fail initialization
            else:
                logger.warning(f"⚠️ Kuzu-memory initialization failed: {proc.stderr}")

    except Exception as e:
        logger.debug(f"Kuzu-memory auto-initialization error (non-critical): {e}")


async def _check_kuzu_memory_updates(kuzu_cmd: Path) -> None:
    """
    Check for kuzu-memory updates and prompt user.

    Args:
        kuzu_cmd: Path to kuzu-memory command

    WHY: Keep users informed about important updates that may fix bugs
    or add features they need.

    DESIGN DECISIONS:
    - Non-blocking with timeout to prevent startup delays
    - Respects user preferences and environment variables
    - Only prompts in interactive TTY sessions
    """
    logger = get_logger("kuzu_memory_update")

    # Skip if environment variable set
    if os.environ.get("CLAUDE_MPM_SKIP_UPDATE_CHECK"):
        return

    # Skip if not TTY (can't prompt)
    if not sys.stdin.isatty():
        return

    # Import update utilities
    from ..utils.package_version_checker import PackageVersionChecker
    from ..utils.update_preferences import UpdatePreferences

    # Check if updates are enabled for this package
    if not UpdatePreferences.should_check_package("kuzu-memory"):
        return

    try:
        # Get current version from pipx
        result = subprocess.run(
            ["pipx", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode == 0:
            pipx_data = json.loads(result.stdout)
            venvs = pipx_data.get("venvs", {})
            kuzu_info = venvs.get("kuzu-memory", {})
            metadata = kuzu_info.get("metadata", {})
            current_version = metadata.get("main_package", {}).get(
                "package_version", "unknown"
            )

            if current_version != "unknown":
                # Check for updates
                checker = PackageVersionChecker()
                update_info = await checker.check_for_update(
                    "kuzu-memory", current_version
                )

                if update_info and update_info.get("update_available"):
                    latest_version = update_info["latest"]

                    # Check if user wants to skip this version
                    if UpdatePreferences.should_skip_version(
                        "kuzu-memory", latest_version
                    ):
                        logger.debug(
                            f"Skipping kuzu-memory update to {latest_version} per user preference"
                        )
                        return

                    # Prompt for update
                    _prompt_kuzu_update(update_info["current"], latest_version)

    except Exception as e:
        logger.debug(f"Update check error: {e}")


def _prompt_kuzu_update(current: str, latest: str) -> None:
    """
    Prompt user to update kuzu-memory.

    Args:
        current: Current installed version
        latest: Latest available version
    """
    from ...cli.shared.error_handling import confirm_operation
    from ..utils.update_preferences import UpdatePreferences

    logger = get_logger("kuzu_memory_update")

    message = (
        f"\n🔄 A new version of kuzu-memory is available!\n"
        f"   Current: v{current}\n"
        f"   Latest:  v{latest}\n\n"
        f"   This update may include bug fixes and performance improvements.\n"
        f"   Update now?"
    )

    # Check if running in a non-interactive context
    try:
        if confirm_operation(message):
            print("🚀 Updating kuzu-memory...", file=sys.stderr)
            try:
                result = subprocess.run(
                    ["pipx", "upgrade", "kuzu-memory"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if result.returncode == 0:
                    print("✅ Successfully updated kuzu-memory!", file=sys.stderr)
                    logger.info(f"Updated kuzu-memory from {current} to {latest}")
                else:
                    print(f"⚠️ Update failed: {result.stderr}", file=sys.stderr)
                    logger.warning(f"kuzu-memory update failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("⚠️ Update timed out. Please try again later.", file=sys.stderr)
                logger.warning("kuzu-memory update timed out")
            except Exception as e:
                print(f"⚠️ Update failed: {e}", file=sys.stderr)
                logger.warning(f"kuzu-memory update error: {e}")
        else:
            # User declined update
            print("\n  To skip this version permanently, run:", file=sys.stderr)
            print(
                f"    claude-mpm config set-skip-version kuzu-memory {latest}",
                file=sys.stderr,
            )
            print("  To disable update checks for kuzu-memory:", file=sys.stderr)
            print(
                "    claude-mpm config disable-update-checks kuzu-memory",
                file=sys.stderr,
            )

            # Ask if user wants to skip this version
            if confirm_operation("\n  Skip this version in future checks?"):
                UpdatePreferences.set_skip_version("kuzu-memory", latest)
                print(
                    f"  Version {latest} will be skipped in future checks.",
                    file=sys.stderr,
                )
    except (KeyboardInterrupt, EOFError):
        # User interrupted or input not available
        pass


async def pre_warm_mcp_servers():
    """
    Pre-warm MCP servers from configuration.

    DISABLED: This function is currently disabled to avoid conflicts with
    Claude Code's native MCP server management. When enabled, this can
    cause issues with MCP server initialization and stderr/stdout handling.

    TODO: Re-enable after ensuring compatibility with Claude Code's MCP handling.
    """
    logger = get_logger("MCPProcessPool")
    logger.debug("MCP server pre-warming is currently disabled")

    # COMMENTED OUT: Auto-initialization that can interfere with Claude Code
    # # Auto-initialize vector search for current project
    # await auto_initialize_vector_search()
    #
    # # Auto-initialize kuzu-memory for persistent knowledge
    # await auto_initialize_kuzu_memory()
    #
    # pool = get_process_pool()
    #
    # # Load MCP configurations
    # configs = {}
    #
    # # Check .claude.json for MCP server configs
    # claude_config_path = Path.home() / ".claude.json"
    # if not claude_config_path.exists():
    #     # Try project-local config
    #     claude_config_path = Path.cwd() / ".claude.json"
    #
    # if claude_config_path.exists():
    #     try:
    #         with claude_config_path.open() as f:
    #             config_data = json.load(f)
    #             mcp_servers = config_data.get("mcpServers", {})
    #             configs.update(mcp_servers)
    #     except Exception as e:
    #         get_logger("MCPProcessPool").warning(f"Failed to load Claude config: {e}")
    #
    # # Check .mcp.json for additional configs
    # mcp_config_path = Path.cwd() / ".mcp.json"
    # if mcp_config_path.exists():
    #     try:
    #         with mcp_config_path.open() as f:
    #             config_data = json.load(f)
    #             mcp_servers = config_data.get("mcpServers", {})
    #             configs.update(mcp_servers)
    #     except Exception as e:
    #         get_logger("MCPProcessPool").warning(f"Failed to load MCP config: {e}")
    #
    # if configs:
    #     await pool.pre_warm_servers(configs)
    #     await pool.start_health_monitoring()
    #
    # return pool

    # Return a basic pool instance without pre-warming
    return get_process_pool()
