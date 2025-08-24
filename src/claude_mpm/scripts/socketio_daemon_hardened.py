#!/usr/bin/env python3
"""
Production-hardened Socket.IO daemon with automatic recovery and monitoring.

WHY: Production environments require robust daemon management with automatic
recovery, comprehensive monitoring, and graceful degradation under load.

FEATURES:
- Automatic retry with exponential backoff
- Supervisor pattern for crash recovery
- Comprehensive error handling and logging
- Resource management and cleanup
- Process management with PID files
- Signal handling for graceful shutdown
- Health monitoring and metrics
- Configuration through environment variables
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional


# Detect and use virtual environment Python if available
def get_python_executable():
    """Get the appropriate Python executable, preferring virtual environment."""
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        return sys.executable

    venv_path = os.environ.get("VIRTUAL_ENV")
    if venv_path:
        venv_python = Path(venv_path) / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)

    exe_path = Path(sys.executable).resolve()
    for parent in exe_path.parents:
        if parent.name in ("venv", ".venv", "env", ".env"):
            return sys.executable
        if parent.name == "bin" and (parent.parent / "pyvenv.cfg").exists():
            return sys.executable
        if parent.name == "Scripts" and (parent.parent / "pyvenv.cfg").exists():
            return sys.executable

    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        if parent.name == "src" or not (parent / "src").exists():
            for venv_name in ("venv", ".venv", "env", ".env"):
                venv_dir = parent / venv_name
                if venv_dir.exists():
                    venv_python = venv_dir / "bin" / "python"
                    if venv_python.exists():
                        return str(venv_python)
            break

    return sys.executable


PYTHON_EXECUTABLE = get_python_executable()


# Configuration from environment variables
class Config:
    """Centralized configuration with environment variable support."""

    # Retry configuration
    MAX_RETRIES = int(os.environ.get("SOCKETIO_MAX_RETRIES", "10"))
    INITIAL_RETRY_DELAY = float(os.environ.get("SOCKETIO_INITIAL_RETRY_DELAY", "1.0"))
    MAX_RETRY_DELAY = float(os.environ.get("SOCKETIO_MAX_RETRY_DELAY", "60.0"))
    BACKOFF_FACTOR = float(os.environ.get("SOCKETIO_BACKOFF_FACTOR", "2.0"))

    # Health check configuration
    HEALTH_CHECK_INTERVAL = float(
        os.environ.get("SOCKETIO_HEALTH_CHECK_INTERVAL", "30.0")
    )
    HEALTH_CHECK_TIMEOUT = float(os.environ.get("SOCKETIO_HEALTH_CHECK_TIMEOUT", "5.0"))
    UNHEALTHY_THRESHOLD = int(os.environ.get("SOCKETIO_UNHEALTHY_THRESHOLD", "3"))

    # Process management
    STARTUP_TIMEOUT = float(os.environ.get("SOCKETIO_STARTUP_TIMEOUT", "30.0"))
    SHUTDOWN_TIMEOUT = float(os.environ.get("SOCKETIO_SHUTDOWN_TIMEOUT", "10.0"))
    FORCE_KILL_TIMEOUT = float(os.environ.get("SOCKETIO_FORCE_KILL_TIMEOUT", "5.0"))

    # Port configuration
    PORT_RANGE_START = int(os.environ.get("SOCKETIO_PORT_START", "8765"))
    PORT_RANGE_END = int(os.environ.get("SOCKETIO_PORT_END", "8785"))

    # Logging
    LOG_LEVEL = os.environ.get("SOCKETIO_LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # Monitoring
    METRICS_ENABLED = (
        os.environ.get("SOCKETIO_METRICS_ENABLED", "true").lower() == "true"
    )
    METRICS_FILE = os.environ.get(
        "SOCKETIO_METRICS_FILE", ".claude-mpm/socketio-metrics.json"
    )


# Setup structured logging
import contextlib
import logging

logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL), format=Config.LOG_FORMAT)
logger = logging.getLogger("socketio-daemon")

try:
    import psutil
except ImportError:
    logger.info(f"Installing psutil using {PYTHON_EXECUTABLE}...")
    subprocess.check_call([PYTHON_EXECUTABLE, "-m", "pip", "install", "psutil"])
    import psutil

# Import project modules
try:
    from claude_mpm.core.unified_paths import get_project_root
    from claude_mpm.services.port_manager import PortManager
    from claude_mpm.services.socketio.server.main import SocketIOServer
except ImportError:
    script_path = Path(__file__).resolve()
    if "site-packages" in str(script_path):
        parts = script_path.parts
        site_packages_idx = next(
            i for i, part in enumerate(parts) if part == "site-packages"
        )
        site_packages_path = Path(*parts[: site_packages_idx + 1])
        if site_packages_path.exists() and str(site_packages_path) not in sys.path:
            sys.path.insert(0, str(site_packages_path))
    else:
        src_path = script_path.parent.parent.parent
        if (
            src_path.exists()
            and (src_path / "claude_mpm").exists()
            and str(src_path) not in sys.path
        ):
            sys.path.insert(0, str(src_path))

    from claude_mpm.core.unified_paths import get_project_root
    from claude_mpm.services.port_manager import PortManager
    from claude_mpm.services.socketio.server.main import SocketIOServer


class DaemonMetrics:
    """Track and persist daemon metrics for monitoring."""

    def __init__(self, metrics_file: Path):
        self.metrics_file = metrics_file
        self.metrics = {
            "start_time": None,
            "restarts": 0,
            "total_failures": 0,
            "last_failure": None,
            "health_checks_passed": 0,
            "health_checks_failed": 0,
            "uptime_seconds": 0,
            "last_health_check": None,
            "status": "initializing",
        }
        self.lock = threading.Lock()
        self.load()

    def load(self):
        """Load metrics from file if exists."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file) as f:
                    saved = json.load(f)
                    self.metrics.update(saved)
            except Exception as e:
                logger.warning(f"Could not load metrics: {e}")

    def save(self):
        """Persist metrics to file."""
        try:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            with self.lock, open(self.metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Could not save metrics: {e}")

    def update(self, **kwargs):
        """Update metrics atomically."""
        with self.lock:
            self.metrics.update(kwargs)
            if self.metrics["start_time"]:
                start = datetime.fromisoformat(str(self.metrics["start_time"]))
                self.metrics["uptime_seconds"] = int(
                    (datetime.now() - start).total_seconds()
                )
        self.save()

    def increment(self, key: str, amount: int = 1):
        """Increment a counter metric."""
        with self.lock:
            self.metrics[key] = self.metrics.get(key, 0) + amount
        self.save()


class ExponentialBackoff:
    """Implement exponential backoff with jitter for retry logic."""

    def __init__(
        self, initial_delay: float = 1.0, max_delay: float = 60.0, factor: float = 2.0
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.factor = factor
        self.current_delay = initial_delay
        self.attempt = 0

    def next_delay(self) -> float:
        """Get the next delay with jitter."""
        import random

        self.attempt += 1

        # Calculate exponential delay
        delay = min(self.initial_delay * (self.factor**self.attempt), self.max_delay)

        # Add jitter (±25% randomization)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        actual_delay = max(0.1, delay + jitter)

        logger.debug(f"Backoff attempt {self.attempt}: {actual_delay:.2f}s")
        return actual_delay

    def reset(self):
        """Reset the backoff counter."""
        self.attempt = 0
        self.current_delay = self.initial_delay


class HealthMonitor:
    """Monitor daemon health and trigger recovery if needed."""

    def __init__(self, port: int, metrics: DaemonMetrics):
        self.port = port
        self.metrics = metrics
        self.consecutive_failures = 0
        self.running = False
        self.thread = None

    def start(self):
        """Start health monitoring in background thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Health monitor started")

    def stop(self):
        """Stop health monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Health monitor stopped")

    def _monitor_loop(self):
        """Main health check loop."""
        while self.running:
            try:
                time.sleep(Config.HEALTH_CHECK_INTERVAL)

                if self._check_health():
                    self.consecutive_failures = 0
                    self.metrics.increment("health_checks_passed")
                    self.metrics.update(
                        last_health_check=datetime.now(), status="healthy"
                    )
                else:
                    self.consecutive_failures += 1
                    self.metrics.increment("health_checks_failed")
                    self.metrics.update(
                        last_health_check=datetime.now(), status="unhealthy"
                    )

                    if self.consecutive_failures >= Config.UNHEALTHY_THRESHOLD:
                        logger.error(
                            f"Health check failed {self.consecutive_failures} times - daemon unhealthy"
                        )
                        # Supervisor will handle restart

            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    def _check_health(self) -> bool:
        """Perform health check on the daemon."""
        try:
            import socket

            # Try to connect to the socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(Config.HEALTH_CHECK_TIMEOUT)
            result = sock.connect_ex(("localhost", self.port))
            sock.close()

            if result != 0:
                logger.warning(
                    f"Health check failed: cannot connect to port {self.port}"
                )
                return False

            # Try to make an HTTP health request if possible
            try:
                import urllib.request

                url = f"http://localhost:{self.port}/health"
                with urllib.request.urlopen(
                    url, timeout=Config.HEALTH_CHECK_TIMEOUT
                ) as response:
                    if response.status == 200:
                        return True
            except:
                # Fall back to simple port check
                pass

            return True

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False


class DaemonSupervisor:
    """Supervise the daemon process and handle automatic recovery."""

    def __init__(self):
        self.deployment_root = get_project_root()
        self.pid_file = self.deployment_root / ".claude-mpm" / "socketio-server.pid"
        self.log_file = self.deployment_root / ".claude-mpm" / "socketio-server.log"
        self.lock_file = self.deployment_root / ".claude-mpm" / "socketio-server.lock"
        self.supervisor_pid_file = (
            self.deployment_root / ".claude-mpm" / "socketio-supervisor.pid"
        )

        # Metrics tracking
        metrics_file = self.deployment_root / ".claude-mpm" / Config.METRICS_FILE
        self.metrics = DaemonMetrics(metrics_file)

        # Recovery state
        self.backoff = ExponentialBackoff(
            Config.INITIAL_RETRY_DELAY, Config.MAX_RETRY_DELAY, Config.BACKOFF_FACTOR
        )

        self.port_manager = PortManager()
        self.server_process = None
        self.selected_port = None
        self.health_monitor = None
        self.shutdown_requested = False

    def ensure_dirs(self):
        """Ensure required directories exist."""
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def acquire_lock(self) -> bool:
        """Acquire exclusive lock to prevent multiple instances."""
        try:
            self.ensure_dirs()

            # Check for existing lock
            if self.lock_file.exists():
                try:
                    with open(self.lock_file) as f:
                        old_pid = int(f.read().strip())

                    # Check if old process is still running
                    if psutil.pid_exists(old_pid):
                        process = psutil.Process(old_pid)
                        if process.is_running():
                            logger.warning(
                                f"Another supervisor is running (PID: {old_pid})"
                            )
                            return False
                except:
                    pass

                # Clean up stale lock
                self.lock_file.unlink(missing_ok=True)

            # Create new lock
            with open(self.lock_file, "w") as f:
                f.write(str(os.getpid()))

            return True

        except Exception as e:
            logger.error(f"Could not acquire lock: {e}")
            return False

    def release_lock(self):
        """Release the exclusive lock."""
        self.lock_file.unlink(missing_ok=True)

    def find_available_port(self) -> Optional[int]:
        """Find an available port for the server."""
        self.port_manager.cleanup_dead_instances()
        port = self.port_manager.find_available_port()

        if not port:
            # Try extended range if configured
            for p in range(Config.PORT_RANGE_START, Config.PORT_RANGE_END + 1):
                import socket

                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex(("localhost", p))
                    sock.close()
                    if result != 0:
                        return p
                except:
                    pass

        return port

    def start_server_process(self) -> bool:
        """Start the actual Socket.IO server process."""
        try:
            # Find available port
            self.selected_port = self.find_available_port()
            if not self.selected_port:
                logger.error("No available ports")
                return False

            logger.info(f"Starting server on port {self.selected_port}")

            # Fork to create daemon process
            pid = os.fork()
            if pid > 0:
                # Parent process - supervisor
                self.server_process = pid

                # Save PID files
                with open(self.pid_file, "w") as f:
                    f.write(str(pid))

                with open(self.supervisor_pid_file, "w") as f:
                    f.write(str(os.getpid()))

                # Save port info
                port_file = self.pid_file.parent / "socketio-port"
                with open(port_file, "w") as f:
                    f.write(str(self.selected_port))

                # Register with port manager
                self.port_manager.register_instance(self.selected_port, pid)

                # Wait for server to start
                if self._wait_for_server_start():
                    logger.info(f"Server started successfully (PID: {pid})")
                    self.metrics.update(start_time=datetime.now(), status="running")
                    self.backoff.reset()
                    return True
                logger.error("Server failed to start within timeout")
                self._cleanup_failed_server(pid)
                return False

            # Child process - actual server
            self._run_server_process()

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            logger.debug(traceback.format_exc())
            return False

    def _run_server_process(self):
        """Run the Socket.IO server in the child process."""
        try:
            # Become a proper daemon
            os.setsid()
            os.umask(0)

            # Redirect output to log file
            with open(self.log_file, "a") as log:
                os.dup2(log.fileno(), sys.stdout.fileno())
                os.dup2(log.fileno(), sys.stderr.fileno())

            # Log startup info
            print(
                f"[{datetime.now()}] Starting Socket.IO server on port {self.selected_port}"
            )
            print(f"[{datetime.now()}] Python: {sys.executable}")
            print(f"[{datetime.now()}] Version: {sys.version}")

            # Create and start server with error handling
            server = None
            try:
                server = SocketIOServer(host="localhost", port=self.selected_port)

                # Setup signal handlers
                def signal_handler(signum, frame):
                    print(
                        f"[{datetime.now()}] Received signal {signum}, shutting down..."
                    )
                    if server:
                        with contextlib.suppress(Exception):
                            server.stop_sync()
                    sys.exit(0)

                signal.signal(signal.SIGTERM, signal_handler)
                signal.signal(signal.SIGINT, signal_handler)

                # Start server
                server.start_sync()

                # Keep running
                while True:
                    time.sleep(1)

            except KeyboardInterrupt:
                if server:
                    server.stop_sync()
                sys.exit(0)
            except Exception as e:
                print(f"[{datetime.now()}] Server error: {e}")
                print(traceback.format_exc())
                sys.exit(1)

        except Exception as e:
            print(f"[{datetime.now()}] Fatal error: {e}")
            sys.exit(1)

    def _wait_for_server_start(self) -> bool:
        """Wait for the server to become responsive."""
        import socket

        start_time = time.time()
        while time.time() - start_time < Config.STARTUP_TIMEOUT:
            # Check if process is still alive
            if not self._is_process_alive(self.server_process):
                return False

            # Try to connect
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(("localhost", self.selected_port))
                sock.close()

                if result == 0:
                    return True
            except:
                pass

            time.sleep(0.5)

        return False

    def _is_process_alive(self, pid: int) -> bool:
        """Check if a process is alive."""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _cleanup_failed_server(self, pid: int):
        """Clean up after a failed server start."""
        try:
            if self._is_process_alive(pid):
                os.kill(pid, signal.SIGKILL)
        except:
            pass

        self.pid_file.unlink(missing_ok=True)

        if self.selected_port:
            instances = self.port_manager.load_instances()
            for instance_id, info in instances.items():
                if info.get("pid") == pid:
                    self.port_manager.remove_instance(instance_id)
                    break

    def monitor_and_restart(self):
        """Monitor the server and restart if it crashes."""
        retry_count = 0

        while retry_count < Config.MAX_RETRIES and not self.shutdown_requested:
            try:
                # Start the server
                if self.start_server_process():
                    # Start health monitoring
                    if Config.METRICS_ENABLED and self.selected_port:
                        self.health_monitor = HealthMonitor(
                            self.selected_port, self.metrics
                        )
                        self.health_monitor.start()

                    # Monitor the process
                    while not self.shutdown_requested:
                        time.sleep(5)

                        # Check if process is still alive
                        if not self._is_process_alive(self.server_process):
                            logger.error("Server process died unexpectedly")
                            self.metrics.increment("total_failures")
                            self.metrics.update(
                                last_failure=datetime.now(), status="crashed"
                            )
                            break

                        # Check health status
                        if (
                            self.health_monitor
                            and self.health_monitor.consecutive_failures
                            >= Config.UNHEALTHY_THRESHOLD
                        ):
                            logger.error("Server is unhealthy, restarting...")
                            self._stop_server_process()
                            break

                    if self.shutdown_requested:
                        break

                    # Stop health monitor before restart
                    if self.health_monitor:
                        self.health_monitor.stop()
                        self.health_monitor = None

                    # Server crashed, apply backoff before restart
                    retry_count += 1
                    delay = self.backoff.next_delay()
                    logger.info(
                        f"Restarting in {delay:.1f}s (attempt {retry_count}/{Config.MAX_RETRIES})"
                    )
                    time.sleep(delay)
                    self.metrics.increment("restarts")

                else:
                    # Failed to start
                    retry_count += 1
                    delay = self.backoff.next_delay()
                    logger.error(
                        f"Failed to start, retrying in {delay:.1f}s (attempt {retry_count}/{Config.MAX_RETRIES})"
                    )
                    time.sleep(delay)

            except KeyboardInterrupt:
                logger.info("Supervisor interrupted")
                break
            except Exception as e:
                logger.error(f"Supervisor error: {e}")
                logger.debug(traceback.format_exc())
                retry_count += 1
                time.sleep(self.backoff.next_delay())

        if retry_count >= Config.MAX_RETRIES:
            logger.error(f"Max retries ({Config.MAX_RETRIES}) exceeded, giving up")
            self.metrics.update(status="failed")

        self.cleanup()

    def _stop_server_process(self):
        """Stop the server process gracefully."""
        if not self.server_process:
            return

        try:
            # Try graceful shutdown
            os.kill(self.server_process, signal.SIGTERM)

            # Wait for shutdown
            start_time = time.time()
            while time.time() - start_time < Config.SHUTDOWN_TIMEOUT:
                if not self._is_process_alive(self.server_process):
                    logger.info("Server stopped gracefully")
                    return
                time.sleep(0.5)

            # Force kill if still running
            logger.warning("Server didn't stop gracefully, forcing...")
            os.kill(self.server_process, signal.SIGKILL)
            time.sleep(Config.FORCE_KILL_TIMEOUT)

        except Exception as e:
            logger.error(f"Error stopping server: {e}")

    def cleanup(self):
        """Clean up resources on shutdown."""
        logger.info("Cleaning up supervisor resources")

        # Stop health monitor
        if self.health_monitor:
            self.health_monitor.stop()

        # Stop server process
        if self.server_process:
            self._stop_server_process()

        # Clean up port registration
        if self.selected_port:
            instances = self.port_manager.load_instances()
            for instance_id, info in instances.items():
                if info.get("pid") == self.server_process:
                    self.port_manager.remove_instance(instance_id)
                    break

        # Remove PID files
        self.pid_file.unlink(missing_ok=True)
        self.supervisor_pid_file.unlink(missing_ok=True)

        # Update metrics
        self.metrics.update(status="stopped")

        # Release lock
        self.release_lock()

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_requested = True


def start_daemon():
    """Start the hardened daemon with supervisor."""
    supervisor = DaemonSupervisor()

    # Check if already running
    if supervisor.pid_file.exists():
        try:
            with open(supervisor.pid_file) as f:
                old_pid = int(f.read().strip())

            if supervisor._is_process_alive(old_pid):
                print(f"Socket.IO daemon is already running (PID: {old_pid})")
                return
        except:
            pass

        # Clean up stale PID file
        supervisor.pid_file.unlink(missing_ok=True)

    # Acquire lock
    if not supervisor.acquire_lock():
        print("Could not acquire lock - another instance may be running")
        return

    print("Starting hardened Socket.IO daemon with supervisor...")
    print(f"Python: {PYTHON_EXECUTABLE}")
    print(f"Max retries: {Config.MAX_RETRIES}")
    print(f"Health checks: {'enabled' if Config.METRICS_ENABLED else 'disabled'}")

    # Setup signal handlers
    signal.signal(signal.SIGTERM, supervisor.handle_shutdown)
    signal.signal(signal.SIGINT, supervisor.handle_shutdown)

    try:
        # Start monitoring and auto-restart loop
        supervisor.monitor_and_restart()
    finally:
        supervisor.cleanup()

    print("Socket.IO daemon stopped")


def stop_daemon():
    """Stop the hardened daemon."""
    deployment_root = get_project_root()
    pid_file = deployment_root / ".claude-mpm" / "socketio-server.pid"
    supervisor_pid_file = deployment_root / ".claude-mpm" / "socketio-supervisor.pid"

    # Try to stop supervisor first
    if supervisor_pid_file.exists():
        try:
            with open(supervisor_pid_file) as f:
                supervisor_pid = int(f.read().strip())

            print(f"Stopping supervisor (PID: {supervisor_pid})...")
            os.kill(supervisor_pid, signal.SIGTERM)

            # Wait for supervisor to stop
            for _ in range(20):
                if not psutil.pid_exists(supervisor_pid):
                    print("Supervisor stopped successfully")
                    supervisor_pid_file.unlink(missing_ok=True)
                    return
                time.sleep(0.5)

            # Force kill if needed
            print("Supervisor didn't stop gracefully, forcing...")
            os.kill(supervisor_pid, signal.SIGKILL)
            supervisor_pid_file.unlink(missing_ok=True)

        except Exception as e:
            print(f"Error stopping supervisor: {e}")

    # Also try to stop server directly if supervisor failed
    if pid_file.exists():
        try:
            with open(pid_file) as f:
                server_pid = int(f.read().strip())

            if psutil.pid_exists(server_pid):
                print(f"Stopping server (PID: {server_pid})...")
                os.kill(server_pid, signal.SIGTERM)
                time.sleep(2)

                if psutil.pid_exists(server_pid):
                    os.kill(server_pid, signal.SIGKILL)

            pid_file.unlink(missing_ok=True)

        except Exception as e:
            print(f"Error stopping server: {e}")


def status_daemon():
    """Show detailed daemon status."""
    deployment_root = get_project_root()
    pid_file = deployment_root / ".claude-mpm" / "socketio-server.pid"
    supervisor_pid_file = deployment_root / ".claude-mpm" / "socketio-supervisor.pid"
    metrics_file = deployment_root / ".claude-mpm" / Config.METRICS_FILE

    print("Socket.IO Daemon Status")
    print("=" * 50)

    # Check supervisor
    if supervisor_pid_file.exists():
        try:
            with open(supervisor_pid_file) as f:
                supervisor_pid = int(f.read().strip())

            if psutil.pid_exists(supervisor_pid):
                process = psutil.Process(supervisor_pid)
                print(f"✅ Supervisor: RUNNING (PID: {supervisor_pid})")
                print(f"   Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
                print(f"   CPU: {process.cpu_percent()}%")
            else:
                print(f"❌ Supervisor: NOT RUNNING (stale PID: {supervisor_pid})")
        except:
            print("❌ Supervisor: ERROR reading status")
    else:
        print("❌ Supervisor: NOT RUNNING")

    # Check server
    if pid_file.exists():
        try:
            with open(pid_file) as f:
                server_pid = int(f.read().strip())

            if psutil.pid_exists(server_pid):
                process = psutil.Process(server_pid)
                print(f"✅ Server: RUNNING (PID: {server_pid})")
                print(f"   Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
                print(f"   CPU: {process.cpu_percent()}%")

                # Check port
                port_file = deployment_root / ".claude-mpm" / "socketio-port"
                if port_file.exists():
                    with open(port_file) as f:
                        port = int(f.read().strip())
                    print(f"   Port: {port}")

                    # Test connection
                    import socket

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex(("localhost", port))
                    sock.close()

                    if result == 0:
                        print(f"   ✅ Listening on port {port}")
                    else:
                        print(f"   ❌ Not responding on port {port}")
            else:
                print(f"❌ Server: NOT RUNNING (stale PID: {server_pid})")
        except:
            print("❌ Server: ERROR reading status")
    else:
        print("❌ Server: NOT RUNNING")

    # Show metrics
    if metrics_file.exists():
        try:
            with open(metrics_file) as f:
                metrics = json.load(f)

            print("\n📊 Metrics:")
            print(f"   Status: {metrics.get('status', 'unknown')}")
            print(f"   Uptime: {metrics.get('uptime_seconds', 0)} seconds")
            print(f"   Restarts: {metrics.get('restarts', 0)}")
            print(f"   Failures: {metrics.get('total_failures', 0)}")
            print(f"   Health Checks Passed: {metrics.get('health_checks_passed', 0)}")
            print(f"   Health Checks Failed: {metrics.get('health_checks_failed', 0)}")

            if metrics.get("last_failure"):
                print(f"   Last Failure: {metrics['last_failure']}")
            if metrics.get("last_health_check"):
                print(f"   Last Health Check: {metrics['last_health_check']}")

        except Exception as e:
            print(f"\n❌ Could not read metrics: {e}")

    print("\n🔧 Configuration:")
    print(f"   Max Retries: {Config.MAX_RETRIES}")
    print(f"   Health Check Interval: {Config.HEALTH_CHECK_INTERVAL}s")
    print(f"   Port Range: {Config.PORT_RANGE_START}-{Config.PORT_RANGE_END}")
    print(f"   Log Level: {Config.LOG_LEVEL}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: socketio-daemon-hardened.py {start|stop|restart|status}")
        sys.exit(1)

    command = sys.argv[1]

    if command == "start":
        start_daemon()
    elif command == "stop":
        stop_daemon()
    elif command == "restart":
        stop_daemon()
        time.sleep(2)
        start_daemon()
    elif command == "status":
        status_daemon()
    else:
        print(f"Unknown command: {command}")
        print("Usage: socketio-daemon-hardened.py {start|stop|restart|status}")
        sys.exit(1)


if __name__ == "__main__":
    main()
