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

import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..core.logger import get_logger


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
                
                # Try to get version
                version = self._get_mcp_version(mcp_executable)
                if version:
                    self.logger.info(f"MCP Server: Version {version}")
                else:
                    self.logger.info("MCP Server: Version unknown")
            else:
                self.logger.info("MCP Server: Not found in PATH")
            
            # Check MCP configuration in ~/.claude.json
            config_status = self._check_mcp_configuration()
            if config_status["found"]:
                self.logger.info("MCP Server: Configuration found in ~/.claude.json")
                if config_status["servers_count"] > 0:
                    self.logger.info(f"MCP Server: {config_status['servers_count']} server(s) configured")
                else:
                    self.logger.info("MCP Server: No servers configured")
            else:
                self.logger.info("MCP Server: No configuration found in ~/.claude.json")
            
            # Check for claude-mpm MCP gateway status
            gateway_status = self._check_mcp_gateway_status()
            if gateway_status["configured"]:
                self.logger.info("MCP Gateway: Claude MPM gateway configured")
            else:
                self.logger.info("MCP Gateway: Claude MPM gateway not configured")
                
        except Exception as e:
            self.logger.warning(f"MCP Server: Status check failed - {e}")
    
    def log_monitor_setup_status(self, monitor_mode: bool = False, websocket_port: int = 8765) -> None:
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
                    self.logger.info(f"Monitor: Socket.IO dependencies missing - {socketio_status['error']}")
                
                # Check if server is running
                server_running = self._check_socketio_server_running(websocket_port)
                if server_running:
                    self.logger.info(f"Monitor: Socket.IO server running on port {websocket_port}")
                else:
                    self.logger.info(f"Monitor: Socket.IO server will start on port {websocket_port}")
                
                # Check response logging configuration
                logging_config = self._check_response_logging_config()
                if logging_config["enabled"]:
                    self.logger.info(f"Monitor: Response logging enabled to {logging_config['directory']}")
                else:
                    self.logger.info("Monitor: Response logging disabled")
                    
            else:
                self.logger.info("Monitor: Mode disabled")
                
                # Still check if there's an existing server running
                server_running = self._check_socketio_server_running(websocket_port)
                if server_running:
                    self.logger.info(f"Monitor: Background Socket.IO server detected on port {websocket_port}")
                    
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
                timeout=5
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
                executable.split() + ["--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output
                output = result.stdout.strip()
                if output:
                    return output
            
            # Try version command
            result = subprocess.run(
                executable.split() + ["version"],
                capture_output=True,
                text=True,
                timeout=5
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
        
        result = {
            "found": False,
            "servers_count": 0,
            "error": None
        }
        
        try:
            if not claude_json_path.exists():
                return result
            
            import json
            with open(claude_json_path, 'r') as f:
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
        result = {
            "configured": False,
            "error": None
        }
        
        try:
            # Check if MCP gateway startup verification is available
            from ..services.mcp_gateway.core.startup_verification import is_mcp_gateway_configured
            result["configured"] = is_mcp_gateway_configured()
        except ImportError:
            # MCP gateway not available
            pass
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _check_socketio_dependencies(self) -> Dict[str, Any]:
        """Check if Socket.IO dependencies are available."""
        result = {
            "available": False,
            "error": None
        }
        
        try:
            import socketio
            import aiohttp
            import engineio
            result["available"] = True
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
                result = s.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def _check_response_logging_config(self) -> Dict[str, Any]:
        """Check response logging configuration."""
        result = {
            "enabled": False,
            "directory": None,
            "error": None
        }
        
        try:
            from ..core.shared.config_loader import ConfigLoader
            
            config_loader = ConfigLoader()
            config = config_loader.load_main_config()
            
            # Check response logging configuration
            response_logging = config.get("response_logging", {})
            result["enabled"] = response_logging.get("enabled", False)
            
            if result["enabled"]:
                log_dir = response_logging.get("session_directory", ".claude-mpm/responses")
                if not Path(log_dir).is_absolute():
                    log_dir = Path.cwd() / log_dir
                result["directory"] = str(log_dir)
            
        except Exception as e:
            result["error"] = str(e)
        
        return result


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
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_file = log_dir / f"startup-{timestamp}.log"
    
    # Create file handler with detailed formatting
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Capture all levels to file
    
    # Format with timestamp, logger name, level, and message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add to claude_mpm logger to capture all our logs
    # (Don't add to root logger to avoid duplicates from propagation)
    claude_logger = logging.getLogger("claude_mpm")
    claude_logger.addHandler(file_handler)
    claude_logger.setLevel(logging.DEBUG)  # Ensure all levels are captured
    
    # Log startup header
    logger = get_logger("startup")
    logger.info("="*60)
    logger.info(f"Claude MPM Startup - {datetime.now().isoformat()}")
    logger.info(f"Log file: {log_file}")
    logger.info("="*60)
    
    # Log system information
    logger.info(f"Python: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info(f"CWD: {Path.cwd()}")
    logger.info(f"Project root: {project_root}")
    
    return log_file


def cleanup_old_startup_logs(project_root: Optional[Path] = None, 
                            keep_days: int = 7,
                            keep_min_count: int = 10) -> int:
    """
    Clean up old startup log files.
    
    WHY: Prevent unbounded growth of startup logs while keeping enough
    history for debugging patterns.
    
    DESIGN DECISIONS:
    - Keep logs from last N days
    - Always keep minimum count regardless of age
    - Return count of deleted files for reporting
    
    Args:
        project_root: Root directory for the project
        keep_days: Number of days to keep logs
        keep_min_count: Minimum number of logs to keep regardless of age
        
    Returns:
        Number of log files deleted
    """
    if project_root is None:
        project_root = Path.cwd()
    
    log_dir = project_root / ".claude-mpm" / "logs" / "startup"
    
    if not log_dir.exists():
        return 0
    
    # Get all startup log files
    log_files = sorted(log_dir.glob("startup-*.log"), 
                      key=lambda p: p.stat().st_mtime,
                      reverse=True)  # Newest first
    
    if len(log_files) <= keep_min_count:
        return 0  # Keep minimum count
    
    # Calculate cutoff time
    cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
    
    deleted_count = 0
    for log_file in log_files[keep_min_count:]:  # Skip minimum count
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                deleted_count += 1
            except Exception:
                pass  # Ignore deletion errors
    
    return deleted_count


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
    
    log_files = sorted(log_dir.glob("startup-*.log"),
                      key=lambda p: p.stat().st_mtime,
                      reverse=True)
    
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
        
        # Log MCP server status
        status_logger.log_mcp_server_status()
        
        # Log monitor setup status
        status_logger.log_monitor_setup_status(monitor_mode, websocket_port)
        
    except Exception as e:
        # Don't let logging failures prevent startup
        logger = get_logger("cli")
        logger.debug(f"Startup status logging failed: {e}")