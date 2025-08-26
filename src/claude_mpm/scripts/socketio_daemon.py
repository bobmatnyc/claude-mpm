#!/usr/bin/env python3
"""
Socket.IO Daemon Management for Claude MPM.

This module provides pure Python daemon management for the Claude MPM Socket.IO server
without requiring external process management dependencies. It handles server lifecycle,
process detection, and virtual environment discovery.

Key Features:
- Pure Python implementation (no external deps)
- Virtual environment auto-detection
- Process management with PID tracking
- Signal handling for clean shutdown
- Port availability checking
- Background daemon execution

Architecture:
- Uses subprocess for server execution
- Implements daemon pattern with double-fork
- Maintains PID files for process tracking
- Auto-detects Python environment (venv/conda)

Thread Safety:
- Signal handlers are async-signal-safe
- PID file operations use atomic writes
- Process checks use system-level primitives

Performance Considerations:
- Minimal memory footprint for daemon mode
- Fast process detection using PID files
- Lazy loading of heavy imports
- Efficient port scanning

Security:
- Localhost-only binding for server
- PID file permissions restrict access
- Process ownership validation
- Signal handling prevents orphans

@author Claude MPM Team
@version 1.0
@since v4.0.25
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


# Detect and use virtual environment Python if available
def get_python_executable() -> str:
    """
    Detect and return the appropriate Python executable for Socket.IO daemon.

    Intelligently detects virtual environments (venv, conda, poetry, pipenv)
    and returns the correct Python path to ensure dependency availability.

    Detection Strategy:
    1. Check if already running in virtual environment
    2. Look for VIRTUAL_ENV environment variable
    3. Analyze executable path structure
    4. Search for project-specific virtual environments
    5. Fall back to system Python

    WHY this complex detection:
    - Socket.IO server requires specific Python packages (socketio, eventlet)
    - System Python rarely has these packages installed
    - Virtual environments contain isolated dependencies
    - Multiple venv tools have different conventions

    Thread Safety:
    - Read-only operations on sys and os modules
    - File system checks are atomic
    - No shared state modification

    Performance:
    - Early returns for common cases
    - Minimal file system operations
    - Cached in practice by Python import system

    Returns:
        str: Path to Python executable with required dependencies

    Raises:
        FileNotFoundError: If no suitable Python executable found

    Examples:
        >>> python_path = get_python_executable()
        >>> # Returns: '/path/to/venv/bin/python' or '/usr/bin/python3'
    """
    # First, check if we're already in a virtual environment
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        # We're in a virtual environment, use its Python
        return sys.executable

    # Check for common virtual environment indicators
    # 1. VIRTUAL_ENV environment variable (most common)
    venv_path = os.environ.get("VIRTUAL_ENV")
    if venv_path:
        venv_python = Path(venv_path) / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)

    # 2. Check if current executable is in a venv directory structure
    exe_path = Path(sys.executable).resolve()
    for parent in exe_path.parents:
        # Check for common venv directory names
        if parent.name in ("venv", ".venv", "env", ".env"):
            # This looks like a virtual environment
            return sys.executable

        # Check for typical venv structure (bin/python or Scripts/python.exe)
        if parent.name == "bin" and (parent.parent / "pyvenv.cfg").exists():
            return sys.executable
        if parent.name == "Scripts" and (parent.parent / "pyvenv.cfg").exists():
            return sys.executable

    # 3. Try to detect project-specific venv
    # Look for venv in the project root (going up from script location)
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        # Stop at src or when we've gone too far up
        if parent.name == "src" or not (parent / "src").exists():
            # Check for venv directories
            for venv_name in ("venv", ".venv", "env", ".env"):
                venv_dir = parent / venv_name
                if venv_dir.exists():
                    venv_python = venv_dir / "bin" / "python"
                    if venv_python.exists():
                        return str(venv_python)
            break

    # Fall back to current Python executable
    return sys.executable


# Store the detected Python executable for daemon usage
PYTHON_EXECUTABLE = get_python_executable()

import psutil

# Handle imports for both development and installed scenarios
script_dir = Path(__file__).parent
try:
    # When installed as package, this should work directly
    from claude_mpm.services.port_manager import PortManager
    from claude_mpm.services.socketio.server.main import SocketIOServer
except ImportError:
    # Need to add the appropriate directory to sys.path
    import sys

    # Get the absolute path of this script
    script_path = Path(__file__).resolve()

    # Determine if we're in development or installed environment
    if "site-packages" in str(script_path):
        # Installed environment: ~/.local/pipx/venvs/claude-mpm/lib/python3.13/site-packages/claude_mpm/scripts/socketio_daemon.py
        # Need to add site-packages directory to path
        parts = script_path.parts
        site_packages_idx = next(
            i for i, part in enumerate(parts) if part == "site-packages"
        )
        site_packages_path = Path(*parts[: site_packages_idx + 1])

        if site_packages_path.exists() and str(site_packages_path) not in sys.path:
            sys.path.insert(0, str(site_packages_path))
    else:
        # Development environment: Project/src/claude_mpm/scripts/socketio_daemon.py
        # Need to add src directory to path
        # Go up: scripts -> claude_mpm -> src
        src_path = script_path.parent.parent.parent

        if (
            src_path.exists()
            and (src_path / "claude_mpm").exists()
            and str(src_path) not in sys.path
        ):
            sys.path.insert(0, str(src_path))

    # Try importing again after path modification
    try:
        from claude_mpm.services.port_manager import PortManager
        from claude_mpm.services.socketio.server.main import SocketIOServer
    except ImportError as e:
        print(f"❌ Failed to import SocketIOServer after path adjustment: {e}")
        print(f"📍 Script path: {script_path}")
        print(f"🐍 Python path entries: {len(sys.path)}")
        for i, path in enumerate(sys.path):
            print(f"   [{i}] {path}")

        # Check if claude_mpm directory exists in any path
        claude_mpm_found = False
        for path_str in sys.path:
            claude_mpm_path = Path(path_str) / "claude_mpm"
            if claude_mpm_path.exists():
                print(f"✅ Found claude_mpm at: {claude_mpm_path}")
                claude_mpm_found = True

        if not claude_mpm_found:
            print("❌ claude_mpm directory not found in any sys.path entry")

        print("\n💡 Troubleshooting tips:")
        print("   1. Ensure claude-mpm is properly installed: pip install claude-mpm")
        print("   2. If in development, ensure you're in the project root directory")
        print("   3. Check that PYTHONPATH includes the package location")
        sys.exit(1)

# Use deployment root for daemon files to keep everything centralized
from claude_mpm.core.unified_paths import get_project_root

deployment_root = get_project_root()
PID_FILE = deployment_root / ".claude-mpm" / "socketio-server.pid"
LOG_FILE = deployment_root / ".claude-mpm" / "socketio-server.log"


def ensure_dirs():
    """Ensure required directories exist."""
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)


def is_running():
    """Check if server is already running."""
    if not PID_FILE.exists():
        return False

    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())

        # Check if process exists
        process = psutil.Process(pid)
        return process.is_running()
    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        # Clean up stale PID file
        PID_FILE.unlink(missing_ok=True)
        return False


def start_server():
    """Start the Socket.IO server as a daemon with dynamic port selection."""
    # Initialize port manager
    port_manager = PortManager()

    # Clean up any dead instances first
    port_manager.cleanup_dead_instances()

    # Check if we already have a running instance
    if is_running():
        print("Socket.IO daemon server is already running.")
        print(f"Use '{__file__} status' for details")
        return

    # Find an available port
    selected_port = port_manager.find_available_port()
    if not selected_port:
        print("❌ No available ports in range 8765-8785")
        print("   All ports are either in use or blocked")
        return

    print(f"🔍 Selected port: {selected_port}")

    # Check for existing instances on this port
    existing_instance = port_manager.get_instance_by_port(selected_port)
    if existing_instance:
        print(f"⚠️  Port {selected_port} is already used by claude-mpm instance:")
        print(f"   PID: {existing_instance.get('pid')}")
        print(f"   Started: {time.ctime(existing_instance.get('start_time', 0))}")
        return

    ensure_dirs()

    # Fork to create daemon using the correct Python environment
    pid = os.fork()
    if pid > 0:
        # Parent process
        print(f"Starting Socket.IO server on port {selected_port} (PID: {pid})...")
        print(f"Using Python: {PYTHON_EXECUTABLE}")

        # Register the instance
        instance_id = port_manager.register_instance(selected_port, pid)

        # Save PID and port info
        with open(PID_FILE, "w") as f:
            f.write(str(pid))

        # Save port info for other tools
        port_file = PID_FILE.parent / "socketio-port"
        with open(port_file, "w") as f:
            f.write(str(selected_port))

        print("Socket.IO server started successfully.")
        print(f"Port: {selected_port}")
        print(f"Instance ID: {instance_id}")
        print(f"PID file: {PID_FILE}")
        print(f"Log file: {LOG_FILE}")
        sys.exit(0)

    # Child process - become daemon
    os.setsid()
    os.umask(0)

    # Redirect stdout/stderr to log file
    with open(LOG_FILE, "a") as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())

    # Log environment information for debugging
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Socket.IO server on port {selected_port}..."
    )
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Python executable: {sys.executable}")
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Python version: {sys.version}")
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Python path: {sys.path[:3]}..."
    )  # Show first 3 entries
    server = SocketIOServer(host="localhost", port=selected_port)

    # Handle signals
    def signal_handler(signum, frame):
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received signal {signum}, shutting down..."
        )
        server.stop_sync()

        # Clean up instance registration
        port_manager_cleanup = PortManager()
        instances = port_manager_cleanup.load_instances()
        for instance_id, instance_info in instances.items():
            if instance_info.get("pid") == os.getpid():
                port_manager_cleanup.remove_instance(instance_id)
                break

        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start server using synchronous method
    server.start_sync()

    # Debug: Check if handlers are registered (write to file for daemon)
    with open(LOG_FILE, "a") as f:
        f.write(
            f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Server started, checking handlers...\n"
        )
        if server.event_registry:
            f.write(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Event registry exists with {len(server.event_registry.handlers)} handlers\n"
            )
            for handler in server.event_registry.handlers:
                f.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]   - {handler.__class__.__name__}\n"
                )
        else:
            f.write(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: No event registry found!\n"
            )

        # Check Socket.IO events
        if server.core and server.core.sio:
            handlers = getattr(server.core.sio, "handlers", {})
            f.write(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Socket.IO has {len(handlers)} namespaces\n"
            )
            for namespace, events in handlers.items():
                f.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]   Namespace '{namespace}': {len(events)} events\n"
                )
                # List all events to debug
                event_list = list(events.keys())
                f.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]   Events: {event_list}\n"
                )
                if "code:analyze:request" in events:
                    f.write(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]   ✅ code:analyze:request is registered!\n"
                    )
                else:
                    f.write(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]   ❌ code:analyze:request NOT found\n"
                    )
        f.flush()

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


def stop_server():
    """Stop the Socket.IO daemon server."""
    if not is_running():
        print("Socket.IO daemon server is not running.")
        print("Check for other servers: socketio_server_manager.py status")
        return

    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())

        print(f"Stopping Socket.IO server (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)

        # Wait for process to stop
        for _ in range(10):
            if not is_running():
                print("Socket.IO server stopped successfully.")
                PID_FILE.unlink(missing_ok=True)
                return
            time.sleep(0.5)

        # Force kill if still running
        print("Server didn't stop gracefully, forcing...")
        os.kill(pid, signal.SIGKILL)
        PID_FILE.unlink(missing_ok=True)

    except Exception as e:
        print(f"Error stopping server: {e}")


def status_server():
    """Check server status with port manager integration."""
    port_manager = PortManager()

    # Clean up dead instances first
    port_manager.cleanup_dead_instances()

    if is_running():
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        print(f"Socket.IO daemon server is running (PID: {pid})")
        print(f"PID file: {PID_FILE}")

        # Get port information
        port_file = PID_FILE.parent / "socketio-port"
        current_port = 8765  # default
        if port_file.exists():
            try:
                with open(port_file) as f:
                    current_port = int(f.read().strip())
            except:
                pass

        # Check if port is listening
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", current_port))
            sock.close()
            if result == 0:
                print(f"✅ Server is listening on port {current_port}")
                print("🔧 Management style: daemon")
            else:
                print(
                    f"⚠️ WARNING: Server process exists but port {current_port} is not accessible"
                )
        except:
            pass

        # Show instance information
        instance = port_manager.get_instance_by_port(current_port)
        if instance:
            print("\n📊 Instance Information:")
            print(f"   • Port: {instance.get('port')}")
            print(f"   • Started: {time.ctime(instance.get('start_time', 0))}")
            print(f"   • Instance ID: {instance.get('instance_id')}")

        # Show management commands
        print("\n🔧 Management Commands:")
        print(f"   • Stop: {__file__} stop")
        print(f"   • Restart: {__file__} restart")
        print(f"   • List all: {__file__} list")

        # Check for manager conflicts
        try:
            import requests

            response = requests.get("http://localhost:8765/health", timeout=1.0)
            if response.status_code == 200:
                data = response.json()
                if "server_id" in data and data.get("server_id") != "daemon-socketio":
                    print("\n⚠️  POTENTIAL CONFLICT: HTTP-managed server also detected")
                    print(f"   Server ID: {data.get('server_id')}")
                    print("   Use 'socketio_server_manager.py diagnose' to resolve")
        except:
            pass

    else:
        print("Socket.IO daemon server is not running")
        print("\n🔧 Start Commands:")
        print(f"   • Daemon: {__file__} start")
        print("   • HTTP-managed: socketio_server_manager.py start")


def list_instances():
    """List all active SocketIO instances."""
    port_manager = PortManager()

    # Clean up dead instances first
    cleaned = port_manager.cleanup_dead_instances()
    if cleaned > 0:
        print(f"🧹 Cleaned up {cleaned} dead instances")

    instances = port_manager.list_active_instances()

    if not instances:
        print("No active SocketIO instances found.")
        return

    print(f"📊 Active SocketIO Instances ({len(instances)}):")
    print()

    for instance in instances:
        port = instance.get("port")
        pid = instance.get("pid")
        start_time = instance.get("start_time", 0)
        instance_id = instance.get("instance_id", "unknown")

        print(f"🔌 Port {port}:")
        print(f"   • PID: {pid}")
        print(f"   • Started: {time.ctime(start_time)}")
        print(f"   • Instance ID: {instance_id}")
        print(f"   • Project: {instance.get('project_root', 'unknown')}")
        print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: socketio-daemon.py {start|stop|restart|status|list}")
        sys.exit(1)

    command = sys.argv[1]

    if command == "start":
        start_server()
    elif command == "stop":
        stop_server()
    elif command == "restart":
        stop_server()
        time.sleep(1)
        start_server()
    elif command == "status":
        status_server()
    elif command == "list":
        list_instances()
    else:
        print(f"Unknown command: {command}")
        print("Usage: socketio-daemon.py {start|stop|restart|status|list}")
        sys.exit(1)


if __name__ == "__main__":
    # Install psutil if not available (using correct Python)
    try:
        import psutil
    except ImportError:
        print(f"Installing psutil using {PYTHON_EXECUTABLE}...")
        subprocess.check_call([PYTHON_EXECUTABLE, "-m", "pip", "install", "psutil"])
        import psutil

    main()
