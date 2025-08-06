"""Standalone Socket.IO server with independent versioning and deployment agnostic design.

This server is designed to run independently of claude-mpm and maintain its own versioning.
It provides a persistent Socket.IO service that can handle multiple claude-mpm client connections.

KEY DESIGN PRINCIPLES:
1. Single server per machine - Only one instance should run
2. Persistent across sessions - Server keeps running when code is pushed  
3. Separate versioning - Server has its own version schema independent of claude-mpm
4. Version compatibility mapping - Track which server versions work with which claude-mpm versions
5. Deployment agnostic - Works with local script, PyPI, npm installations

WHY standalone architecture:
- Allows server evolution independent of claude-mpm releases
- Enables persistent monitoring across multiple claude-mpm sessions
- Provides better resource management (one server vs multiple)
- Simplifies debugging and maintenance
- Supports different installation methods (PyPI, local, Docker, etc.)
"""

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from collections import deque
import importlib.metadata
import fcntl  # Unix file locking
import platform

# Import health monitoring and recovery systems
try:
    from .health_monitor import (
        AdvancedHealthMonitor, ProcessResourceChecker, 
        NetworkConnectivityChecker, ServiceHealthChecker,
        HealthStatus, HealthCheckResult
    )
    from .recovery_manager import RecoveryManager, RecoveryEvent
    HEALTH_MONITORING_AVAILABLE = True
except ImportError as e:
    HEALTH_MONITORING_AVAILABLE = False
    # Create stub classes to prevent errors
    class AdvancedHealthMonitor:
        def __init__(self, *args, **kwargs): pass
        def add_checker(self, *args): pass
        def start_monitoring(self): pass
        async def stop_monitoring(self): pass
        def get_current_status(self): return None
        def export_diagnostics(self): return {}
    
    class RecoveryManager:
        def __init__(self, *args, **kwargs): pass
        def handle_health_result(self, *args): return None
        def get_recovery_status(self): return {}

# Import enhanced error classes
try:
    from .exceptions import (
        DaemonConflictError, PortConflictError, StaleProcessError,
        RecoveryFailedError, HealthCheckError, format_troubleshooting_guide
    )
    ENHANCED_ERRORS_AVAILABLE = True
except ImportError as e:
    ENHANCED_ERRORS_AVAILABLE = False
    # Create stub classes to prevent errors
    class DaemonConflictError(Exception): pass
    class PortConflictError(Exception): pass
    class StaleProcessError(Exception): pass
    class RecoveryFailedError(Exception): pass
    class HealthCheckError(Exception): pass
    def format_troubleshooting_guide(error): return str(error)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Windows file locking support
if platform.system() == 'Windows':
    try:
        import msvcrt
        WINDOWS_LOCKING = True
    except ImportError:
        WINDOWS_LOCKING = False
else:
    WINDOWS_LOCKING = False
    msvcrt = None

try:
    import socketio
    from aiohttp import web
    SOCKETIO_AVAILABLE = True
    
    # Get Socket.IO version
    try:
        SOCKETIO_VERSION = importlib.metadata.version('python-socketio')
    except Exception:
        SOCKETIO_VERSION = 'unknown'
        
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None
    web = None
    SOCKETIO_VERSION = 'not-installed'

# Standalone server version - independent of claude-mpm
STANDALONE_SERVER_VERSION = "1.0.0"

# Compatibility matrix - which server versions work with which claude-mpm versions
COMPATIBILITY_MATRIX = {
    "1.0.0": {
        "claude_mpm_versions": [">=0.7.0"],
        "min_python": "3.8",
        "socketio_min": "5.11.0",
        "features": [
            "persistent_server",
            "version_compatibility",
            "process_isolation",
            "health_monitoring",
            "advanced_health_monitoring",
            "automatic_recovery",
            "circuit_breaker",
            "resource_monitoring",
            "event_namespacing",
            "comprehensive_diagnostics",
            "metrics_export"
        ]
    }
}


class StandaloneSocketIOServer:
    """Standalone Socket.IO server with independent lifecycle and versioning.
    
    This server runs independently of claude-mpm processes and provides:
    - Version compatibility checking
    - Process isolation and management
    - Persistent operation across claude-mpm sessions
    - Health monitoring and diagnostics
    - Event namespacing and routing
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765, 
                 server_id: Optional[str] = None):
        self.server_version = STANDALONE_SERVER_VERSION
        self.server_id = server_id or f"socketio-{uuid.uuid4().hex[:8]}"
        self.host = host
        self.port = port
        self.start_time = datetime.utcnow()
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Server state
        self.running = False
        self.clients: Set[str] = set()
        self.event_history: deque = deque(maxlen=10000)  # Larger history for standalone server
        self.client_versions: Dict[str, str] = {}  # Track client claude-mpm versions
        self.health_stats = {
            "events_processed": 0,
            "clients_served": 0,
            "errors": 0,
            "last_activity": None
        }
        
        # Asyncio components
        self.loop = None
        self.app = None
        self.sio = None
        self.runner = None
        self.site = None
        
        # Process management
        self.pid = os.getpid()
        self.pidfile_path = self._get_pidfile_path()
        self.pidfile_lock = None  # File lock object
        self.process_start_time = None
        if PSUTIL_AVAILABLE:
            try:
                current_process = psutil.Process(self.pid)
                self.process_start_time = current_process.create_time()
            except Exception as e:
                self.logger.warning(f"Could not get process start time: {e}")
        
        if not SOCKETIO_AVAILABLE:
            self.logger.error("Socket.IO dependencies not available. Install with: pip install python-socketio aiohttp")
            return
        
        # Log initialization with comprehensive info
        self.logger.info(f"Standalone Socket.IO server v{self.server_version} initialized")
        self.logger.info(f"Server ID: {self.server_id}, PID: {self.pid}")
        self.logger.info(f"Using python-socketio v{SOCKETIO_VERSION}")
        self.logger.info(f"Enhanced validation: psutil {'available' if PSUTIL_AVAILABLE else 'not available'}")
        self.logger.info(f"File locking: {platform.system()} {'supported' if (platform.system() != 'Windows' or WINDOWS_LOCKING) else 'not supported'}")
        self.logger.info(f"Health monitoring: {'available' if HEALTH_MONITORING_AVAILABLE else 'not available'}")
        
        # Initialize health monitoring system
        self.health_monitor = None
        self.recovery_manager = None
        if HEALTH_MONITORING_AVAILABLE:
            self._initialize_health_monitoring()
        
        if self.process_start_time:
            self.logger.debug(f"Process start time: {self.process_start_time}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup dedicated logging for standalone server."""
        logger = logging.getLogger(f"socketio_standalone_{self.server_id}")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - StandaloneSocketIO[{self.server_id}] - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _initialize_health_monitoring(self):
        """Initialize health monitoring and recovery systems."""
        try:
            # Health monitoring configuration
            health_config = {
                'check_interval': 30,  # Check every 30 seconds
                'history_size': 100,   # Keep 100 health check results
                'aggregation_window': 300  # 5 minute aggregation window
            }
            
            self.health_monitor = AdvancedHealthMonitor(health_config)
            
            # Add health checkers
            
            # Process resource monitoring
            if PSUTIL_AVAILABLE:
                process_checker = ProcessResourceChecker(
                    pid=self.pid,
                    cpu_threshold=80.0,      # 80% CPU threshold
                    memory_threshold_mb=500,  # 500MB memory threshold
                    fd_threshold=1000        # 1000 file descriptor threshold
                )
                self.health_monitor.add_checker(process_checker)
            
            # Network connectivity monitoring
            network_checker = NetworkConnectivityChecker(
                host=self.host,
                port=self.port,
                timeout=2.0
            )
            self.health_monitor.add_checker(network_checker)
            
            # Service health monitoring (will be initialized after server stats are available)
            # This is added later in start_async after health_stats is fully initialized
            
            # Recovery manager configuration
            recovery_config = {
                'enabled': True,
                'check_interval': 60,
                'max_recovery_attempts': 5,
                'recovery_timeout': 30,
                'circuit_breaker': {
                    'failure_threshold': 5,
                    'timeout_seconds': 300,
                    'success_threshold': 3
                },
                'strategy': {
                    'warning_threshold': 2,
                    'critical_threshold': 1,
                    'failure_window_seconds': 300,
                    'min_recovery_interval': 60
                }
            }
            
            self.recovery_manager = RecoveryManager(recovery_config, self)
            
            # Link health monitor and recovery manager
            self.health_monitor.add_health_callback(self._handle_health_result)
            
            self.logger.info("Health monitoring and recovery systems initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize health monitoring: {e}")
            self.health_monitor = None
            self.recovery_manager = None
    
    def _handle_health_result(self, health_result: HealthCheckResult):
        """Handle health check results and trigger recovery if needed."""
        try:
            if self.recovery_manager:
                recovery_event = self.recovery_manager.handle_health_result(health_result)
                if recovery_event:
                    self.logger.info(f"Recovery triggered: {recovery_event.action.value}")
        except Exception as e:
            self.logger.error(f"Error handling health result: {e}")
            
            # Enhanced error reporting for health check failures
            if ENHANCED_ERRORS_AVAILABLE:
                if hasattr(health_result, 'status') and health_result.status in ['critical', 'failed']:
                    health_error = HealthCheckError(
                        check_name=getattr(health_result, 'check_name', 'unknown'),
                        check_status=getattr(health_result, 'status', 'failed'),
                        check_details=getattr(health_result, 'details', {})
                    )
                    self.logger.error(f"\nHealth Check Failure Details:\n{health_error}")
    
    def _get_pidfile_path(self) -> Path:
        """Get path for PID file to track running server."""
        # Use system temp directory or user home
        if os.name == 'nt':  # Windows
            temp_dir = Path(os.environ.get('TEMP', os.path.expanduser('~')))
        else:  # Unix-like
            temp_dir = Path('/tmp') if Path('/tmp').exists() else Path.home()
        
        return temp_dir / f"claude_mpm_socketio_{self.port}.pid"
    
    def check_compatibility(self, client_version: str) -> Dict[str, Any]:
        """Check if client version is compatible with this server version.
        
        Returns compatibility info including warnings and supported features.
        """
        server_compat = COMPATIBILITY_MATRIX.get(self.server_version, {})
        
        result = {
            "compatible": False,
            "server_version": self.server_version,
            "client_version": client_version,
            "warnings": [],
            "supported_features": server_compat.get("features", []),
            "requirements": {
                "min_python": server_compat.get("min_python", "3.8"),
                "socketio_min": server_compat.get("socketio_min", "5.11.0")
            }
        }
        
        # Simple version compatibility check
        # In production, you'd use proper semantic versioning
        try:
            if client_version >= "0.7.0":  # Minimum supported
                result["compatible"] = True
            else:
                result["warnings"].append(f"Client version {client_version} may not be fully supported")
                result["compatible"] = False
        except Exception as e:
            result["warnings"].append(f"Could not parse client version: {e}")
            result["compatible"] = False
        
        return result
    
    def _validate_process_identity(self, pid: int, expected_cmdline_patterns: List[str] = None) -> Dict[str, Any]:
        """Validate that a process is actually our Socket.IO server.
        
        Args:
            pid: Process ID to validate
            expected_cmdline_patterns: Command line patterns that should match our server
            
        Returns:
            Dict with validation results and process info
        """
        validation_result = {
            "is_valid": False,
            "is_zombie": False,
            "is_our_server": False,
            "process_info": {},
            "validation_errors": []
        }
        
        if not PSUTIL_AVAILABLE:
            validation_result["validation_errors"].append("psutil not available for enhanced validation")
            # Fallback to basic process existence check
            try:
                os.kill(pid, 0)
                validation_result["is_valid"] = True
                validation_result["process_info"] = {"pid": pid, "method": "basic_os_check"}
            except OSError:
                validation_result["validation_errors"].append(f"Process {pid} does not exist")
            return validation_result
        
        try:
            process = psutil.Process(pid)
            
            # Basic process info
            process_info = {
                "pid": pid,
                "status": process.status(),
                "create_time": process.create_time(),
                "name": process.name(),
                "cwd": None,
                "cmdline": [],
                "memory_info": None
            }
            
            # Check if process is zombie
            if process.status() == psutil.STATUS_ZOMBIE:
                validation_result["is_zombie"] = True
                validation_result["validation_errors"].append(f"Process {pid} is a zombie")
                validation_result["process_info"] = process_info
                return validation_result
            
            # Get additional process details
            try:
                process_info["cwd"] = process.cwd()
                process_info["cmdline"] = process.cmdline()
                process_info["memory_info"] = process.memory_info()._asdict()
            except (psutil.AccessDenied, psutil.NoSuchProcess) as e:
                validation_result["validation_errors"].append(f"Access denied getting process details: {e}")
            
            validation_result["process_info"] = process_info
            validation_result["is_valid"] = True
            
            # Validate this is likely our server process
            cmdline = process_info.get("cmdline", [])
            cmdline_str = " ".join(cmdline).lower()
            
            # Default patterns for our Socket.IO server
            if expected_cmdline_patterns is None:
                expected_cmdline_patterns = [
                    "socketio",
                    "standalone_socketio_server",
                    "claude-mpm",
                    str(self.port)
                ]
            
            # Check if any patterns match the command line
            matches = [pattern.lower() in cmdline_str for pattern in expected_cmdline_patterns]
            if any(matches):
                validation_result["is_our_server"] = True
                self.logger.debug(f"Process {pid} matches server patterns: {[p for p, m in zip(expected_cmdline_patterns, matches) if m]}")
            else:
                validation_result["validation_errors"].append(
                    f"Process {pid} command line '{cmdline_str}' does not match expected patterns: {expected_cmdline_patterns}"
                )
                self.logger.warning(f"Process {pid} does not appear to be our server: {cmdline}")
            
        except psutil.NoSuchProcess:
            validation_result["validation_errors"].append(f"Process {pid} no longer exists")
        except psutil.AccessDenied as e:
            validation_result["validation_errors"].append(f"Access denied to process {pid}: {e}")
        except Exception as e:
            validation_result["validation_errors"].append(f"Error validating process {pid}: {e}")
        
        return validation_result
    
    def _acquire_pidfile_lock(self, pidfile_fd) -> bool:
        """Acquire exclusive lock on PID file.
        
        Args:
            pidfile_fd: Open file descriptor for PID file
            
        Returns:
            True if lock acquired successfully, False otherwise
        """
        try:
            if platform.system() == 'Windows' and WINDOWS_LOCKING:
                # Windows file locking
                msvcrt.locking(pidfile_fd.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            else:
                # Unix file locking
                fcntl.flock(pidfile_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
        except (IOError, OSError) as e:
            self.logger.debug(f"Could not acquire PID file lock: {e}")
            return False
    
    def _release_pidfile_lock(self, pidfile_fd):
        """Release lock on PID file.
        
        Args:
            pidfile_fd: Open file descriptor for PID file
        """
        try:
            if platform.system() == 'Windows' and WINDOWS_LOCKING:
                msvcrt.locking(pidfile_fd.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(pidfile_fd.fileno(), fcntl.LOCK_UN)
        except (IOError, OSError) as e:
            self.logger.debug(f"Error releasing PID file lock: {e}")
    
    def _validate_pidfile_timestamp(self, pidfile_path: Path, process_start_time: float) -> bool:
        """Validate that PID file was created around the same time as the process.
        
        Args:
            pidfile_path: Path to PID file
            process_start_time: Process start time from psutil
            
        Returns:
            True if timestamps are reasonably close, False otherwise
        """
        try:
            pidfile_mtime = pidfile_path.stat().st_mtime
            time_diff = abs(pidfile_mtime - process_start_time)
            
            # Allow up to 5 seconds difference (process start vs file creation)
            if time_diff <= 5.0:
                return True
            else:
                self.logger.warning(
                    f"PID file timestamp ({pidfile_mtime}) and process start time ({process_start_time}) "
                    f"differ by {time_diff:.2f} seconds"
                )
                return False
        except Exception as e:
            self.logger.warning(f"Could not validate PID file timestamp: {e}")
            return False
    
    def is_already_running(self, raise_on_conflict: bool = False) -> bool:
        """Enhanced check if another server instance is already running on this port.
        
        This method performs comprehensive validation including:
        - PID file existence and validity
        - Process identity verification (command line, start time)
        - Zombie process detection
        - Port availability check
        - Automatic cleanup of stale PID files
        
        Returns:
            True if a valid server is already running, False otherwise
        """
        self.logger.debug(f"Checking if server is already running on {self.host}:{self.port}")
        
        try:
            # Step 1: Check PID file existence
            if not self.pidfile_path.exists():
                self.logger.debug("No PID file found")
                return self._check_port_only(raise_on_conflict)
            
            self.logger.debug(f"Found PID file: {self.pidfile_path}")
            
            # Step 2: Read PID from file with support for both JSON and legacy formats
            try:
                with open(self.pidfile_path, 'r') as f:
                    pid_content = f.read().strip()
                    
                    if not pid_content:
                        self.logger.warning("Empty PID file")
                        self._cleanup_stale_pidfile("empty_file")
                        return self._check_port_only(raise_on_conflict)
                    
                    # Try JSON format first (new format)
                    try:
                        pidfile_data = json.loads(pid_content)
                        old_pid = pidfile_data["pid"]
                        server_id = pidfile_data.get("server_id", "unknown")
                        self.logger.debug(f"Found PID {old_pid} for server {server_id} in JSON format")
                    except (json.JSONDecodeError, KeyError, TypeError):
                        # Fallback to legacy format (plain PID number)
                        if pid_content.isdigit():
                            old_pid = int(pid_content)
                            self.logger.debug(f"Found PID {old_pid} in legacy format")
                        else:
                            self.logger.warning(f"Invalid PID content in file: '{pid_content[:100]}...' (truncated)")
                            self._cleanup_stale_pidfile("invalid_content")
                            return self._check_port_only(raise_on_conflict)
                    
            except (IOError, ValueError) as e:
                self.logger.warning(f"Could not read PID file: {e}")
                self._cleanup_stale_pidfile("read_error")
                return self._check_port_only(raise_on_conflict)
            
            # Step 3: Enhanced process validation
            validation = self._validate_process_identity(old_pid)
            
            if not validation["is_valid"]:
                self.logger.info(f"Process {old_pid} is not valid: {validation['validation_errors']}")
                if raise_on_conflict and ENHANCED_ERRORS_AVAILABLE:
                    raise StaleProcessError(
                        pid=old_pid,
                        pidfile_path=self.pidfile_path,
                        process_status="not_found",
                        validation_errors=validation['validation_errors']
                    )
                self._cleanup_stale_pidfile("invalid_process")
                return self._check_port_only(raise_on_conflict)
            
            if validation["is_zombie"]:
                self.logger.info(f"Process {old_pid} is a zombie, cleaning up")
                if raise_on_conflict and ENHANCED_ERRORS_AVAILABLE:
                    raise StaleProcessError(
                        pid=old_pid,
                        pidfile_path=self.pidfile_path,
                        process_status="zombie",
                        validation_errors=["Process is a zombie (terminated but not reaped)"]
                    )
                self._cleanup_stale_pidfile("zombie_process")
                return self._check_port_only(raise_on_conflict)
            
            # Step 4: Verify this is actually our server process
            if not validation["is_our_server"]:
                self.logger.warning(
                    f"Process {old_pid} exists but does not appear to be our Socket.IO server. "
                    f"Command line: {validation['process_info'].get('cmdline', 'unknown')}"
                )
                # Don't automatically clean up - might be another legitimate process
                return self._check_port_only(raise_on_conflict)
            
            # Step 5: Validate process start time against PID file timestamp
            if PSUTIL_AVAILABLE and 'create_time' in validation['process_info']:
                process_start_time = validation['process_info']['create_time']
                if not self._validate_pidfile_timestamp(self.pidfile_path, process_start_time):
                    self.logger.warning("PID file timestamp does not match process start time")
                    # Continue anyway - timestamp validation is not critical
            
            # Step 6: All validations passed
            process_info = validation['process_info']
            self.logger.info(
                f"Found valid running server: PID {old_pid}, "
                f"status: {process_info.get('status', 'unknown')}, "
                f"name: {process_info.get('name', 'unknown')}"
            )
            
            if raise_on_conflict and ENHANCED_ERRORS_AVAILABLE:
                # Try to extract server ID from PID file if available
                server_id = "unknown"
                try:
                    with open(self.pidfile_path, 'r') as f:
                        content = f.read().strip()
                        if content.startswith('{'):
                            pidfile_data = json.loads(content)
                            server_id = pidfile_data.get("server_id", "unknown")
                except:
                    pass
                
                raise DaemonConflictError(
                    port=self.port,
                    existing_pid=old_pid,
                    existing_server_id=server_id,
                    process_info=process_info,
                    pidfile_path=self.pidfile_path
                )
            
            return True
            
        except (DaemonConflictError, StaleProcessError, PortConflictError) as e:
            # Re-raise our enhanced errors instead of catching them
            raise
        except Exception as e:
            self.logger.error(f"Error during enhanced server check: {e}")
            # Fallback to basic port check on unexpected errors
            return self._check_port_only(raise_on_conflict)
    
    def _check_port_only(self, raise_on_conflict: bool = False) -> bool:
        """Fallback method to check if port is in use.
        
        Args:
            raise_on_conflict: If True, raises PortConflictError instead of returning True
        
        Returns:
            True if port is in use, False otherwise
            
        Raises:
            PortConflictError: If raise_on_conflict=True and port is in use
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                result = s.connect_ex((self.host, self.port))
                if result == 0:
                    self.logger.info(f"Port {self.port} is in use by some process")
                    
                    if raise_on_conflict and ENHANCED_ERRORS_AVAILABLE:
                        # Try to identify the conflicting process if psutil is available
                        conflicting_process = {}
                        if PSUTIL_AVAILABLE:
                            try:
                                import psutil
                                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                                    try:
                                        for conn in proc.connections():
                                            if (conn.laddr.ip == self.host or conn.laddr.ip == '0.0.0.0') and conn.laddr.port == self.port:
                                                conflicting_process = {
                                                    'pid': proc.info['pid'],
                                                    'name': proc.info['name'],
                                                    'cmdline': proc.info['cmdline']
                                                }
                                                break
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        continue
                                    if conflicting_process:
                                        break
                            except Exception:
                                pass  # Ignore errors in process discovery
                        
                        raise PortConflictError(
                            port=self.port,
                            host=self.host,
                            conflicting_process=conflicting_process
                        )
                    
                    return True
        except Exception as e:
            if not isinstance(e, PortConflictError):  # Don't mask our own exceptions
                self.logger.debug(f"Error checking port availability: {e}")
        
        return False
    
    def _cleanup_stale_pidfile(self, reason: str):
        """Clean up stale PID file with logging.
        
        Args:
            reason: Reason for cleanup (for logging)
        """
        try:
            if self.pidfile_path.exists():
                self.pidfile_path.unlink()
                self.logger.info(f"Cleaned up stale PID file (reason: {reason}): {self.pidfile_path}")
        except Exception as e:
            self.logger.error(f"Failed to clean up stale PID file: {e}")
    
    def create_pidfile(self):
        """Create PID file with exclusive locking to track this server instance.
        
        This method creates a PID file with exclusive locking to prevent race conditions
        and ensures only one server instance can hold the lock at a time.
        """
        try:
            self.pidfile_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Open file for writing with exclusive creation
            pidfile_fd = open(self.pidfile_path, 'w')
            
            # Try to acquire exclusive lock
            if not self._acquire_pidfile_lock(pidfile_fd):
                pidfile_fd.close()
                if ENHANCED_ERRORS_AVAILABLE:
                    raise DaemonConflictError(
                        port=self.port,
                        existing_pid=0,  # Unknown PID since we can't get lock
                        existing_server_id="unknown",
                        pidfile_path=self.pidfile_path
                    )
                else:
                    raise RuntimeError("Could not acquire exclusive lock on PID file")
            
            # Write PID and additional metadata
            pidfile_content = {
                "pid": self.pid,
                "server_id": self.server_id,
                "server_version": self.server_version,
                "port": self.port,
                "host": self.host,
                "start_time": self.start_time.isoformat() + "Z",
                "process_start_time": self.process_start_time if self.process_start_time else None,
                "python_version": sys.version.split()[0],
                "platform": platform.system(),
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            # Write JSON format for better validation
            pidfile_fd.write(json.dumps(pidfile_content, indent=2))
            pidfile_fd.flush()
            
            # Keep file descriptor open to maintain lock
            self.pidfile_lock = pidfile_fd
            
            self.logger.info(f"Created PID file with exclusive lock: {self.pidfile_path}")
            self.logger.debug(f"PID file content: {pidfile_content}")
            
        except Exception as e:
            self.logger.error(f"Failed to create PID file: {e}")
            if 'pidfile_fd' in locals():
                try:
                    pidfile_fd.close()
                except:
                    pass
            raise
    
    def remove_pidfile(self):
        """Remove PID file and release lock on shutdown."""
        try:
            # Release file lock first
            if self.pidfile_lock:
                try:
                    self._release_pidfile_lock(self.pidfile_lock)
                    self.pidfile_lock.close()
                    self.pidfile_lock = None
                    self.logger.debug("Released PID file lock")
                except Exception as e:
                    self.logger.warning(f"Error releasing PID file lock: {e}")
            
            # Remove PID file
            if self.pidfile_path.exists():
                self.pidfile_path.unlink()
                self.logger.info(f"Removed PID file: {self.pidfile_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to remove PID file: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    async def start_async(self):
        """Start the server asynchronously."""
        if not SOCKETIO_AVAILABLE:
            error_msg = "Socket.IO dependencies not available. Install with: pip install python-socketio aiohttp"
            if ENHANCED_ERRORS_AVAILABLE:
                raise RuntimeError(error_msg + "\n\nInstallation steps:\n  1. pip install python-socketio aiohttp\n  2. Restart the server\n  3. Verify installation: python -c 'import socketio; print(socketio.__version__)'")
            else:
                raise RuntimeError(error_msg)
        
        self.logger.info(f"Starting standalone Socket.IO server v{self.server_version}")
        
        # Create Socket.IO server with production settings
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",  # Configure appropriately for production
            async_mode='aiohttp',
            ping_timeout=60,
            ping_interval=25,
            max_http_buffer_size=1000000,
            logger=False,  # Use our own logger
            engineio_logger=False
        )
        
        # Create aiohttp application
        self.app = web.Application()
        self.sio.attach(self.app)
        
        # Setup routes and event handlers
        self._setup_routes()
        self._setup_event_handlers()
        
        # Start the server
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self.running = True
            
            # Create PID file after successful server start
            self.create_pidfile()
            
            # Start health monitoring
            if self.health_monitor:
                # Add service health checker now that stats are available
                service_checker = ServiceHealthChecker(
                    service_stats=self.health_stats,
                    max_clients=1000,
                    max_error_rate=0.1
                )
                self.health_monitor.add_checker(service_checker)
                
                # Start monitoring
                self.health_monitor.start_monitoring()
                self.logger.info("Health monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            # Clean up partial initialization
            if hasattr(self, 'runner') and self.runner:
                try:
                    await self.runner.cleanup()
                except:
                    pass
            
            # Enhanced error handling for common startup failures
            if ENHANCED_ERRORS_AVAILABLE:
                if "Address already in use" in str(e) or "Permission denied" in str(e):
                    # This is likely a port conflict
                    try:
                        # Check if port is in use and raise appropriate error
                        self._check_port_only(raise_on_conflict=True)
                    except PortConflictError:
                        # Re-raise the more specific error
                        raise
            
            raise
        
        self.logger.info(f"🚀 Standalone Socket.IO server STARTED on http://{self.host}:{self.port}")
        self.logger.info(f"🔧 Server ID: {self.server_id}")
        self.logger.info(f"💾 PID file: {self.pidfile_path}")
    
    def start(self):
        """Start the server in the main thread (for standalone execution)."""
        if self.is_already_running():
            self.logger.error("Server is already running. Use stop() first or choose a different port.")
            return False
        
        self.setup_signal_handlers()
        
        # Run in main thread for standalone operation
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_forever())
        except KeyboardInterrupt:
            self.logger.info("Received KeyboardInterrupt, shutting down...")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise
        finally:
            self.stop()
        
        return True
    
    async def _run_forever(self):
        """Run the server until stopped."""
        await self.start_async()
        
        try:
            # Keep server running with periodic health checks
            last_health_check = time.time()
            
            while self.running:
                await asyncio.sleep(1)
                
                # Periodic health check and stats update
                now = time.time()
                if now - last_health_check > 30:  # Every 30 seconds
                    self._update_health_stats()
                    last_health_check = now
                    
        except Exception as e:
            self.logger.error(f"Error in server loop: {e}")
            raise
    
    def stop(self):
        """Stop the server gracefully."""
        self.logger.info("Stopping standalone Socket.IO server...")
        self.running = False
        
        if self.loop and self.loop.is_running():
            # Schedule shutdown in the event loop
            self.loop.create_task(self._shutdown_async())
        else:
            # Direct shutdown
            asyncio.run(self._shutdown_async())
        
        self.remove_pidfile()
        self.logger.info("Server stopped")
    
    async def _shutdown_async(self):
        """Async shutdown process."""
        try:
            # Stop health monitoring
            if self.health_monitor:
                await self.health_monitor.stop_monitoring()
                self.logger.info("Health monitoring stopped")
            
            # Close all client connections
            if self.sio:
                await self.sio.shutdown()
            
            # Stop the web server
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
                
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def _setup_routes(self):
        """Setup HTTP routes for health checks and admin endpoints."""
        
        async def version_endpoint(request):
            """Version discovery endpoint."""
            compatibility_info = {
                "server_version": self.server_version,
                "server_id": self.server_id,
                "socketio_version": SOCKETIO_VERSION,
                "compatibility_matrix": COMPATIBILITY_MATRIX,
                "supported_client_versions": COMPATIBILITY_MATRIX[self.server_version].get("claude_mpm_versions", []),
                "features": COMPATIBILITY_MATRIX[self.server_version].get("features", [])
            }
            return web.json_response(compatibility_info)
        
        async def health_endpoint(request):
            """Health check endpoint with detailed diagnostics."""
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            
            health_info = {
                "status": "healthy" if self.running else "stopped",
                "server_version": self.server_version,
                "server_id": self.server_id,
                "pid": self.pid,
                "uptime_seconds": uptime,
                "start_time": self.start_time.isoformat() + "Z",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "client_versions": dict(self.client_versions),
                "health_stats": dict(self.health_stats),
                "port": self.port,
                "host": self.host,
                "dependencies": {
                    "socketio_version": SOCKETIO_VERSION,
                    "python_version": sys.version.split()[0]
                }
            }
            return web.json_response(health_info)
        
        async def compatibility_check(request):
            """Check compatibility with a specific client version."""
            data = await request.json()
            client_version = data.get("client_version", "unknown")
            
            compatibility = self.check_compatibility(client_version)
            return web.json_response(compatibility)
        
        async def stats_endpoint(request):
            """Server statistics endpoint."""
            stats = {
                "server_info": {
                    "version": self.server_version,
                    "id": self.server_id,
                    "uptime": (datetime.utcnow() - self.start_time).total_seconds()
                },
                "connections": {
                    "current_clients": len(self.clients),
                    "total_served": self.health_stats["clients_served"],
                    "client_versions": dict(self.client_versions)
                },
                "events": {
                    "total_processed": self.health_stats["events_processed"],
                    "history_size": len(self.event_history),
                    "last_activity": self.health_stats["last_activity"]
                },
                "errors": self.health_stats["errors"]
            }
            return web.json_response(stats)
        
        # Register routes
        self.app.router.add_get('/version', version_endpoint)
        self.app.router.add_get('/health', health_endpoint)
        self.app.router.add_get('/status', health_endpoint)  # Alias
        self.app.router.add_post('/compatibility', compatibility_check)
        self.app.router.add_get('/stats', stats_endpoint)
        
        # Serve Socket.IO client library
        self.app.router.add_static('/socket.io/', 
                                 path=Path(__file__).parent / 'static', 
                                 name='socketio_static')
    
    def _setup_event_handlers(self):
        """Setup Socket.IO event handlers."""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            """Handle client connection with version compatibility checking."""
            self.clients.add(sid)
            client_addr = environ.get('REMOTE_ADDR', 'unknown')
            
            # Extract client version from auth if provided
            client_version = "unknown"
            if auth and isinstance(auth, dict):
                client_version = auth.get('claude_mpm_version', 'unknown')
            
            self.client_versions[sid] = client_version
            self.health_stats["clients_served"] += 1
            self.health_stats["last_activity"] = datetime.utcnow().isoformat() + "Z"
            
            self.logger.info(f"🔗 Client {sid} connected from {client_addr}")
            self.logger.info(f"📋 Client version: {client_version}")
            self.logger.info(f"📊 Total clients: {len(self.clients)}")
            
            # Check version compatibility
            compatibility = self.check_compatibility(client_version)
            
            # Send connection acknowledgment with compatibility info
            await self.sio.emit('connection_ack', {
                "server_version": self.server_version,
                "server_id": self.server_id,
                "compatibility": compatibility,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, room=sid)
            
            # Send current server status
            await self._send_server_status(sid)
            
            if not compatibility["compatible"]:
                self.logger.warning(f"⚠️ Client {sid} version {client_version} has compatibility issues")
                await self.sio.emit('compatibility_warning', compatibility, room=sid)
        
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            if sid in self.clients:
                self.clients.remove(sid)
            if sid in self.client_versions:
                del self.client_versions[sid]
            
            self.logger.info(f"🔌 Client {sid} disconnected")
            self.logger.info(f"📊 Remaining clients: {len(self.clients)}")
        
        @self.sio.event
        async def ping(sid, data=None):
            """Handle ping requests."""
            await self.sio.emit('pong', {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "server_id": self.server_id
            }, room=sid)
        
        @self.sio.event
        async def get_version(sid):
            """Handle version info requests."""
            version_info = {
                "server_version": self.server_version,
                "server_id": self.server_id,
                "socketio_version": SOCKETIO_VERSION,
                "compatibility_matrix": COMPATIBILITY_MATRIX
            }
            await self.sio.emit('version_info', version_info, room=sid)
        
        @self.sio.event
        async def claude_event(sid, data):
            """Handle events from claude-mpm clients and broadcast to other clients."""
            try:
                # Add server metadata
                enhanced_data = {
                    **data,
                    "server_id": self.server_id,
                    "received_at": datetime.utcnow().isoformat() + "Z"
                }
                
                # Store in event history
                self.event_history.append(enhanced_data)
                self.health_stats["events_processed"] += 1
                self.health_stats["last_activity"] = datetime.utcnow().isoformat() + "Z"
                
                # Broadcast to all other clients
                await self.sio.emit('claude_event', enhanced_data, skip_sid=sid)
                
                self.logger.debug(f"📤 Broadcasted claude_event from {sid} to {len(self.clients)-1} clients")
                
            except Exception as e:
                self.logger.error(f"Error handling claude_event: {e}")
                self.health_stats["errors"] += 1
                
                # Check if error rate is becoming concerning
                if ENHANCED_ERRORS_AVAILABLE and self.health_stats["errors"] > 0:
                    error_rate = self.health_stats["errors"] / max(self.health_stats["events_processed"], 1)
                    if error_rate > 0.1:  # More than 10% error rate
                        self.logger.warning(f"⚠️ High error rate detected: {error_rate:.2%} ({self.health_stats['errors']} errors out of {self.health_stats['events_processed']} events)")
        
        @self.sio.event
        async def get_history(sid, data=None):
            """Handle event history requests."""
            params = data or {}
            limit = min(params.get("limit", 100), len(self.event_history))
            
            history = list(self.event_history)[-limit:] if limit > 0 else []
            
            await self.sio.emit('event_history', {
                "events": history,
                "total_available": len(self.event_history),
                "returned": len(history)
            }, room=sid)
    
    async def _send_server_status(self, sid: str):
        """Send current server status to a client."""
        status = {
            "server_version": self.server_version,
            "server_id": self.server_id,
            "uptime": (datetime.utcnow() - self.start_time).total_seconds(),
            "clients_connected": len(self.clients),
            "events_processed": self.health_stats["events_processed"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.sio.emit('server_status', status, room=sid)
    
    def _update_health_stats(self):
        """Update health statistics."""
        self.logger.debug(f"🏥 Health check - Clients: {len(self.clients)}, "
                         f"Events: {self.health_stats['events_processed']}, "
                         f"Errors: {self.health_stats['errors']}")


def main():
    """Main entry point for standalone server execution."""
    import argparse
    import json
    import time
    
    parser = argparse.ArgumentParser(description="Standalone Claude MPM Socket.IO Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")  
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument("--server-id", help="Custom server ID")
    parser.add_argument("--check-running", action="store_true", 
                       help="Check if server is already running and exit")
    parser.add_argument("--stop", action="store_true", help="Stop running server")
    parser.add_argument("--version", action="store_true", help="Show version info")
    
    args = parser.parse_args()
    
    if args.version:
        print(f"Standalone Socket.IO Server v{STANDALONE_SERVER_VERSION}")
        print(f"Socket.IO v{SOCKETIO_VERSION}")
        print(f"Compatibility: {COMPATIBILITY_MATRIX[STANDALONE_SERVER_VERSION]['claude_mpm_versions']}")
        return
    
    server = StandaloneSocketIOServer(
        host=args.host,
        port=args.port,
        server_id=args.server_id
    )
    
    if args.check_running:
        if server.is_already_running():
            print(f"Server is running on {args.host}:{args.port}")
            sys.exit(0)
        else:
            print(f"No server running on {args.host}:{args.port}")
            sys.exit(1)
    
    if args.stop:
        if server.is_already_running():
            # Send termination signal to running server with enhanced validation
            try:
                # Read and validate PID file
                with open(server.pidfile_path, 'r') as f:
                    content = f.read().strip()
                
                # Try to parse as JSON first (new format), fallback to plain PID
                try:
                    pidfile_data = json.loads(content)
                    pid = pidfile_data["pid"]
                    server_id = pidfile_data.get("server_id", "unknown")
                    print(f"Found server {server_id} with PID {pid}")
                except (json.JSONDecodeError, KeyError):
                    # Fallback to old format
                    pid = int(content)
                    server_id = "unknown"
                
                # Validate the process before attempting to stop it
                validation = server._validate_process_identity(pid)
                if not validation["is_valid"]:
                    print(f"Process {pid} is not valid or no longer exists")
                    server._cleanup_stale_pidfile("stop_command_invalid_process")
                    print("Cleaned up stale PID file")
                    sys.exit(1)
                
                if validation["is_zombie"]:
                    print(f"Process {pid} is a zombie, cleaning up PID file")
                    server._cleanup_stale_pidfile("stop_command_zombie")
                    sys.exit(0)
                
                if not validation["is_our_server"]:
                    print(f"Warning: Process {pid} may not be our Socket.IO server")
                    print(f"Command line: {validation['process_info'].get('cmdline', 'unknown')}")
                    response = input("Stop it anyway? [y/N]: ")
                    if response.lower() != 'y':
                        print("Aborted")
                        sys.exit(1)
                
                # Send termination signal
                os.kill(pid, signal.SIGTERM)
                print(f"Sent stop signal to server (PID: {pid})")
                
                # Wait a moment for graceful shutdown
                time.sleep(2)
                
                # Check if process is still running
                try:
                    os.kill(pid, 0)
                    print(f"Server is still running, sending SIGKILL...")
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(1)
                except OSError:
                    print("Server stopped successfully")
                
            except Exception as e:
                print(f"Error stopping server: {e}")
                sys.exit(1)
        else:
            print("No server running to stop")
            sys.exit(1)
        return
    
    # Start the server
    try:
        server.start()
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()