"""
Startup logging utilities for MCP server and monitor setup status.

WHY: This module provides detailed startup logging for better debugging
visibility. It logs MCP server installation/configuration status and
monitor service initialization status during the startup sequence.

DESIGN DECISIONS:
- Use consistent INFO log format with existing startup messages
- Gracefully handle missing dependencies or services
- Provide informative but concise status messages
- Include helpful context for debugging
- Ensure logging works in all deployment contexts (dev, pipx, pip)
- Capture all startup logs to timestamped files for analysis
"""

import asyncio
import logging
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from ..core.logger import get_logger


def log_memory_stats(logger=None, prefix="Memory Usage"):
    """
    Log current memory statistics.

    Args:
        logger: Logger to use (defaults to 'cli' logger)
        prefix: Prefix for the log message

    Returns:
        Dict with memory stats or None if psutil unavailable
    """
    if not PSUTIL_AVAILABLE:
        return None

    if logger is None:
        logger = get_logger("cli")

    try:
        process = psutil.Process()
        memory_info = process.memory_info()

        # Convert to MB for readability
        rss_mb = memory_info.rss / (1024 * 1024)
        vms_mb = memory_info.vms / (1024 * 1024)

        # On macOS, VMS can report misleading values (400+ TB)
        # Skip VMS reporting if it's unreasonably large
        import platform

        if platform.system() == "Darwin" and vms_mb > 100000:  # > 100GB is suspicious
            # Get percentage of system memory if available
            try:
                memory_percent = process.memory_percent()
                logger.info(
                    f"{prefix}: RSS={rss_mb:.1f}MB, System={memory_percent:.1f}%"
                )
                return {"rss_mb": rss_mb, "vms_mb": None, "percent": memory_percent}
            except Exception:
                logger.info(f"{prefix}: RSS={rss_mb:.1f}MB")
                return {"rss_mb": rss_mb, "vms_mb": None, "percent": None}
        else:
            # Normal VMS reporting for non-macOS or reasonable values
            # Get percentage of system memory if available
            try:
                memory_percent = process.memory_percent()
                logger.info(
                    f"{prefix}: RSS={rss_mb:.1f}MB, VMS={vms_mb:.1f}MB, "
                    f"System={memory_percent:.1f}%"
                )
                return {"rss_mb": rss_mb, "vms_mb": vms_mb, "percent": memory_percent}
            except Exception:
                logger.info(f"{prefix}: RSS={rss_mb:.1f}MB, VMS={vms_mb:.1f}MB")
                return {"rss_mb": rss_mb, "vms_mb": vms_mb, "percent": None}

    except Exception as e:
        logger.debug(f"Failed to get memory info: {e}")
        return None


class StartupStatusLogger:
    """Logs MCP server and monitor setup status during startup."""

    def __init__(self, logger_name: str = "startup_status"):
        """Initialize the startup status logger."""
        self.logger = get_logger(logger_name)

    def log_mcp_server_status(self) -> None:
        """
        Log MCP server installation and configuration status.

        Checks:
        - MCP server executable availability
        - MCP server version if available
        - MCP configuration in ~/.claude.json
        - MCP-related errors or warnings
        """
        try:
            # Check if MCP server executable is available
            mcp_executable = self._find_mcp_executable()
            if mcp_executable:
                self.logger.info(f"MCP Server: Installed at {mcp_executable}")

                # Try to get version (only log if version is found)
                version = self._get_mcp_version(mcp_executable)
                if version:
                    self.logger.info(f"MCP Server: Version {version}")
            else:
                self.logger.info("MCP Server: Not found in PATH")

            # Check MCP configuration in ~/.claude.json
            config_status = self._check_mcp_configuration()
            if config_status["found"]:
                self.logger.info("MCP Server: Configuration found in ~/.claude.json")
                if config_status["servers_count"] > 0:
                    self.logger.info(
                        f"MCP Server: {config_status['servers_count']} server(s) configured"
                    )
                else:
                    self.logger.info("MCP Server: No servers configured")
                    self._log_mcp_setup_hint()
            else:
                self.logger.info("MCP Server: No configuration found in ~/.claude.json")
                self._log_mcp_setup_hint()

            # Check for claude-mpm MCP gateway status
            gateway_status = self._check_mcp_gateway_status()
            if gateway_status["configured"]:
                self.logger.info("MCP Gateway: Claude MPM gateway configured")
            else:
                self.logger.info("MCP Gateway: Claude MPM gateway not configured")
                # Check if this is a pipx installation that could benefit from auto-config
                if (
                    self._is_pipx_installation()
                    and not self._has_auto_config_preference()
                ):
                    self.logger.info(
                        "MCP Gateway: Auto-configuration available for pipx users"
                    )

        except Exception as e:
            self.logger.warning(f"MCP Server: Status check failed - {e}")

    def log_memory_status(self) -> None:
        """
        Log current process memory usage.

        Logs both RSS (Resident Set Size) and VMS (Virtual Memory Size)
        to help track memory consumption and potential leaks.
        """
        stats = log_memory_stats(self.logger, "Memory Usage")

        # Log warning if memory usage is high
        if stats and stats.get("rss_mb", 0) > 500:  # Warn if using more than 500MB
            self.logger.warning(f"High memory usage detected: {stats['rss_mb']:.1f}MB")

    def log_monitor_setup_status(
        self, monitor_mode: bool = False, websocket_port: int = 8765
    ) -> None:
        """
        Log monitor service initialization status.

        Args:
            monitor_mode: Whether monitor mode is enabled
            websocket_port: WebSocket port for monitoring

        Checks:
        - Monitor service initialization status
        - Which monitors are enabled/disabled
        - Monitor configuration details
        - Monitor-related errors or warnings
        """
        try:
            if monitor_mode:
                self.logger.info("Monitor: Mode enabled")

                # Check SocketIO dependencies
                socketio_status = self._check_socketio_dependencies()
                if socketio_status["available"]:
                    self.logger.info("Monitor: Socket.IO dependencies available")
                else:
                    self.logger.info(
                        f"Monitor: Socket.IO dependencies missing - {socketio_status['error']}"
                    )

                # Check if server is running
                server_running = self._check_socketio_server_running(websocket_port)
                if server_running:
                    self.logger.info(
                        f"Monitor: Socket.IO server running on port {websocket_port}"
                    )
                else:
                    self.logger.info(
                        f"Monitor: Socket.IO server will start on port {websocket_port}"
                    )

                # Check response logging configuration
                logging_config = self._check_response_logging_config()
                if logging_config["enabled"]:
                    self.logger.info(
                        f"Monitor: Response logging enabled to {logging_config['directory']}"
                    )
                else:
                    self.logger.info("Monitor: Response logging disabled")

            else:
                self.logger.info("Monitor: Mode disabled")

                # Still check if there's an existing server running
                server_running = self._check_socketio_server_running(websocket_port)
                if server_running:
                    self.logger.info(
                        f"Monitor: Background Socket.IO server detected on port {websocket_port}"
                    )

        except Exception as e:
            self.logger.warning(f"Monitor: Status check failed - {e}")

    def _find_mcp_executable(self) -> Optional[str]:
        """Find MCP server executable in PATH."""
        # Common MCP executable names
        executables = ["claude-mpm-mcp", "mcp", "claude-mcp"]

        for exe_name in executables:
            exe_path = shutil.which(exe_name)
            if exe_path:
                return exe_path

        # Check if it's installed as a Python package
        try:
            result = subprocess.run(
                [sys.executable, "-m", "claude_mpm.scripts.mcp_server", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return f"{sys.executable} -m claude_mpm.scripts.mcp_server"
        except Exception:
            pass

        return None

    def _get_mcp_version(self, executable: str) -> Optional[str]:
        """Get MCP server version."""
        try:
            # Try --version flag
            result = subprocess.run(
                [*executable.split(), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                # Extract version from output
                output = result.stdout.strip()
                if output:
                    return output

            # Try version command
            result = subprocess.run(
                [*executable.split(), "version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    return output

        except Exception:
            pass

        return None

    def _check_mcp_configuration(self) -> Dict[str, Any]:
        """Check MCP configuration in ~/.claude.json."""
        claude_json_path = Path.home() / ".claude.json"

        result = {"found": False, "servers_count": 0, "error": None}

        try:
            if not claude_json_path.exists():
                return result

            import json

            with claude_json_path.open() as f:
                config = json.load(f)

            result["found"] = True

            # Check for MCP servers configuration
            mcp_config = config.get("mcpServers", {})
            result["servers_count"] = len(mcp_config)

        except Exception as e:
            result["error"] = str(e)

        return result

    def _check_mcp_gateway_status(self) -> Dict[str, Any]:
        """Check Claude MPM MCP gateway configuration status."""
        result = {"configured": False, "error": None}

        try:
            # Check if MCP gateway startup verification is available
            from ..services.mcp_gateway.core.startup_verification import (
                is_mcp_gateway_configured,
            )

            result["configured"] = is_mcp_gateway_configured()
        except ImportError:
            # MCP gateway not available
            pass
        except Exception as e:
            result["error"] = str(e)

        return result

    def _check_socketio_dependencies(self) -> Dict[str, Any]:
        """Check if Socket.IO dependencies are available."""
        import importlib.util

        result = {"available": False, "error": None}

        try:
            # Check for socketio dependencies without importing them
            aiohttp_spec = importlib.util.find_spec("aiohttp")
            engineio_spec = importlib.util.find_spec("engineio")
            socketio_spec = importlib.util.find_spec("socketio")

            if aiohttp_spec and engineio_spec and socketio_spec:
                result["available"] = True
            else:
                missing = []
                if not aiohttp_spec:
                    missing.append("aiohttp")
                if not engineio_spec:
                    missing.append("engineio")
                if not socketio_spec:
                    missing.append("socketio")
                result["error"] = f"Missing dependencies: {', '.join(missing)}"
        except ImportError as e:
            result["error"] = f"Missing dependencies: {e}"
        except Exception as e:
            result["error"] = str(e)

        return result

    def _check_socketio_server_running(self, port: int) -> bool:
        """Check if Socket.IO server is running on specified port."""
        try:
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("localhost", port))
                return result == 0
        except Exception:
            return False

    def _check_response_logging_config(self) -> Dict[str, Any]:
        """Check response logging configuration."""
        result = {"enabled": False, "directory": None, "error": None}

        try:
            from ..core.shared.config_loader import ConfigLoader

            config_loader = ConfigLoader()
            config = config_loader.load_main_config()

            # Check response logging configuration
            response_logging = config.get("response_logging", {})
            result["enabled"] = response_logging.get("enabled", False)

            if result["enabled"]:
                log_dir = response_logging.get(
                    "session_directory", ".claude-mpm/responses"
                )
                if not Path(log_dir).is_absolute():
                    log_dir = Path.cwd() / log_dir
                result["directory"] = str(log_dir)

        except Exception as e:
            result["error"] = str(e)

        return result

    def _is_pipx_installation(self) -> bool:
        """Check if this is a pipx installation."""
        try:
            # Check if running from pipx
            if "pipx" in sys.executable.lower():
                return True

            # Check module path
            import claude_mpm

            module_path = Path(claude_mpm.__file__).parent
            if "pipx" in str(module_path):
                return True
        except Exception:
            pass

        return False

    def _has_auto_config_preference(self) -> bool:
        """Check if user has already been asked about auto-configuration."""
        try:
            from ..config.paths import paths

            preference_file = (
                paths.claude_mpm_dir_hidden / "mcp_auto_config_preference.json"
            )
            return preference_file.exists()
        except Exception:
            return False

    def _log_mcp_setup_hint(self) -> None:
        """Log helpful hints for MCP setup."""
        # Check if installed via pipx
        is_pipx = self._check_pipx_installation()

        if is_pipx:
            self.logger.info("💡 TIP: It looks like you installed claude-mpm via pipx")
            self.logger.info("   To configure MCP for Claude Code with pipx:")
            self.logger.info("   1. Run: python3 scripts/configure_mcp_pipx.py")
            self.logger.info("   2. Or see: docs/MCP_PIPX_SETUP.md for manual setup")
            self.logger.info("   3. Restart Claude Code after configuration")
        else:
            self.logger.info("💡 TIP: To enable MCP integration with Claude Code:")
            self.logger.info("   1. See docs/MCP_SETUP.md for setup instructions")
            self.logger.info("   2. Run: claude-mpm doctor --check mcp to verify")
            self.logger.info("   3. Restart Claude Code after configuration")

    def _check_pipx_installation(self) -> bool:
        """Check if claude-mpm was installed via pipx."""
        try:
            # Check if running from a pipx venv
            if "pipx" in sys.executable.lower():
                return True

            # Check if claude-mpm-mcp command exists and is from pipx
            mcp_cmd = shutil.which("claude-mpm-mcp")
            if mcp_cmd and "pipx" in mcp_cmd.lower():
                return True

            # Try to check pipx list
            result = subprocess.run(
                ["pipx", "list"], capture_output=True, text=True, timeout=2, check=False
            )
            if result.returncode == 0 and "claude-mpm" in result.stdout:
                return True

        except Exception:
            pass

        return False


def setup_startup_logging(project_root: Optional[Path] = None) -> Path:
    """
    Set up logging to both console and file for startup.

    WHY: Capture all startup logs (INFO, WARNING, ERROR, DEBUG) to timestamped
    files for later analysis by the doctor command. This helps diagnose
    startup issues that users may not notice in the console output.

    DESIGN DECISIONS:
    - Use ISO-like timestamp format for easy sorting and reading
    - Store in .claude-mpm/logs/startup/ directory
    - Keep all historical startup logs for pattern analysis
    - Add file handler to root logger to capture ALL module logs

    Args:
        project_root: Root directory for the project (defaults to cwd)

    Returns:
        Path to the created log file
    """
    if project_root is None:
        project_root = Path.cwd()

    # Create log directory
    log_dir = project_root / ".claude-mpm" / "logs" / "startup"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for log file
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")
    log_file = log_dir / f"startup-{timestamp}.log"

    # Create file handler with detailed formatting
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Capture all levels to file

    # Format with timestamp, logger name, level, and message
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    # Add to claude_mpm logger to capture all our logs
    # (Don't add to root logger to avoid duplicates from propagation)
    claude_logger = logging.getLogger("claude_mpm")
    claude_logger.addHandler(file_handler)
    claude_logger.setLevel(logging.DEBUG)  # Ensure all levels are captured

    # Log startup header
    logger = get_logger("startup")
    logger.info("=" * 60)
    logger.info(f"Claude MPM Startup - {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    # Log system information
    logger.info(f"Python: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"CWD: {Path.cwd()}")
    logger.info(f"Project root: {project_root}")

    # Log initial memory usage
    if PSUTIL_AVAILABLE:
        try:
            import platform

            process = psutil.Process()
            memory_info = process.memory_info()
            rss_mb = memory_info.rss / (1024 * 1024)
            vms_mb = memory_info.vms / (1024 * 1024)

            # On macOS, VMS can report misleading values (400+ TB)
            # Skip VMS reporting if it's unreasonably large
            if (
                platform.system() == "Darwin" and vms_mb > 100000
            ):  # > 100GB is suspicious
                logger.info(f"Initial Memory: RSS={rss_mb:.1f}MB")
            else:
                logger.info(f"Initial Memory: RSS={rss_mb:.1f}MB, VMS={vms_mb:.1f}MB")
        except Exception as e:
            logger.debug(f"Failed to get initial memory info: {e}")

    return log_file


def cleanup_old_startup_logs(
    project_root: Optional[Path] = None, keep_count: Optional[int] = None
) -> int:
    """
    Clean up old startup log files using time-based retention.

    WHY: This function now delegates to LogManager for unified log management
    with time-based retention instead of count-based.

    DESIGN DECISIONS:
    - Delegates to LogManager for consistency
    - Converts count to hours (48 hours default)
    - Maintains backward compatibility

    Args:
        project_root: Root directory for the project
        keep_count: Ignored (kept for backward compatibility)

    Returns:
        Number of log files deleted
    """
    try:
        from ..core.log_manager import get_log_manager

        log_manager = get_log_manager()

        # Use LogManager's time-based cleanup (48 hours default)
        return log_manager.cleanup_old_startup_logs(project_root)
    except ImportError:
        # Fallback to old implementation if LogManager not available
        # Get retention count from configuration if not specified
        if keep_count is None:
            from claude_mpm.core.config_constants import ConfigConstants

            keep_count = (
                ConfigConstants.get_logging_setting("startup_logs_retention_count")
                or 10
            )

        if project_root is None:
            project_root = Path.cwd()

        log_dir = project_root / ".claude-mpm" / "logs" / "startup"

        if not log_dir.exists():
            return 0

        # Get all startup log files
        log_files = sorted(
            log_dir.glob("startup-*.log"), key=lambda p: p.stat().st_mtime, reverse=True
        )  # Newest first

        if len(log_files) <= keep_count:
            return 0  # Already within limit

        # Delete older files beyond keep_count
        deleted_count = 0
        for log_file in log_files[
            keep_count:
        ]:  # Keep only the most recent keep_count files
            try:
                log_file.unlink()
                deleted_count += 1
            except Exception:
                pass  # Ignore deletion errors

        return deleted_count


async def trigger_vector_search_indexing(project_root: Optional[Path] = None) -> None:
    """
    Trigger mcp-vector-search indexing in the background.

    This function attempts to start the mcp-vector-search indexing process
    asynchronously so it doesn't block startup. If the service is not available,
    it fails silently.

    Args:
        project_root: Root directory for the project (defaults to cwd)
    """
    logger = get_logger("cli")

    if project_root is None:
        project_root = Path.cwd()

    try:
        # Check if mcp-vector-search is available
        from ..services.mcp_config_manager import MCPConfigManager

        manager = MCPConfigManager()
        vector_search_path = manager.detect_service_path("mcp-vector-search")

        if not vector_search_path:
            logger.debug("mcp-vector-search not found, skipping indexing")
            return

        # Build the command based on the service configuration
        if "python" in vector_search_path:
            # Using Python interpreter directly
            cmd = [
                vector_search_path,
                "-m",
                "mcp_vector_search.cli",
                "index",
                str(project_root),
            ]
        else:
            # Using installed binary
            cmd = [vector_search_path, "index", str(project_root)]

        logger.info(
            "MCP Vector Search: Starting background indexing for improved code search"
        )

        # Start the indexing process in the background
        # We use subprocess.Popen instead of run to avoid blocking
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=str(project_root),
        )

        # Store PID for logging
        pid = process.pid
        logger.debug(f"MCP Vector Search: Indexing process started (PID: {pid})")

        # Don't wait for completion - let it run independently in the background
        # We don't need to track its completion, so we can safely detach

    except ImportError:
        logger.debug(
            "MCP config manager not available, skipping vector search indexing"
        )
    except Exception as e:
        # Don't let indexing failures prevent startup
        logger.debug(f"Failed to start vector search indexing: {e}")


def start_vector_search_indexing(project_root: Optional[Path] = None) -> None:
    """
    Synchronous wrapper to trigger vector search indexing.

    This creates a new event loop if needed to run the async indexing function.
    Falls back to subprocess.Popen if async fails.

    Args:
        project_root: Root directory for the project (defaults to cwd)
    """
    logger = get_logger("cli")

    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're in an event loop, create a task (fire-and-forget)
        _task = loop.create_task(trigger_vector_search_indexing(project_root))
        # Fire-and-forget: task will complete in background
    except RuntimeError:
        # No event loop running - use subprocess directly to avoid event loop lifecycle issues
        # The async approach with asyncio.run() creates and closes a loop which causes
        # warnings when subprocesses are still running
        logger.debug("No event loop running, using subprocess approach")
        _start_vector_search_subprocess(project_root)


def _start_vector_search_subprocess(project_root: Optional[Path] = None) -> None:
    """
    Fallback method to start vector search indexing using subprocess.Popen.

    Args:
        project_root: Root directory for the project (defaults to cwd)
    """
    logger = get_logger("cli")

    if project_root is None:
        project_root = Path.cwd()

    try:
        from ..services.mcp_config_manager import MCPConfigManager

        manager = MCPConfigManager()
        vector_search_path = manager.detect_service_path("mcp-vector-search")

        if not vector_search_path:
            logger.debug("mcp-vector-search not found, skipping indexing")
            return

        # Build the command
        if "python" in vector_search_path:
            cmd = [
                vector_search_path,
                "-m",
                "mcp_vector_search.cli",
                "index",
                str(project_root),
            ]
        else:
            cmd = [vector_search_path, "index", str(project_root)]

        logger.info(
            "MCP Vector Search: Starting background indexing for improved code search"
        )

        # Start the indexing process in the background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(project_root),
        )

        logger.debug(
            f"MCP Vector Search: Indexing process started (PID: {process.pid})"
        )

    except Exception as e:
        logger.debug(f"Failed to start vector search indexing: {e}")


def get_latest_startup_log(project_root: Optional[Path] = None) -> Optional[Path]:
    """
    Get the path to the most recent startup log file.

    Args:
        project_root: Root directory for the project

    Returns:
        Path to latest log file or None if no logs exist
    """
    if project_root is None:
        project_root = Path.cwd()

    log_dir = project_root / ".claude-mpm" / "logs" / "startup"

    if not log_dir.exists():
        return None

    log_files = sorted(
        log_dir.glob("startup-*.log"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    return log_files[0] if log_files else None


def log_startup_status(monitor_mode: bool = False, websocket_port: int = 8765) -> None:
    """
    Log comprehensive startup status for MCP server and monitor setup.

    This function should be called during application startup to provide
    detailed information about MCP and monitor setup status.

    Args:
        monitor_mode: Whether monitor mode is enabled
        websocket_port: WebSocket port for monitoring
    """
    try:
        status_logger = StartupStatusLogger("cli")

        # Log memory status at startup
        status_logger.log_memory_status()

        # Log MCP server status
        status_logger.log_mcp_server_status()

        # Log monitor setup status
        status_logger.log_monitor_setup_status(monitor_mode, websocket_port)

        # Trigger vector search indexing in the background after MCP is configured
        # This will run asynchronously and not block startup
        start_vector_search_indexing()

    except Exception as e:
        # Don't let logging failures prevent startup
        logger = get_logger("cli")
        logger.debug(f"Startup status logging failed: {e}")
