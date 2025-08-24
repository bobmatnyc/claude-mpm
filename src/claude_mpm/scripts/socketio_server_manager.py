#!/usr/bin/env python3
"""
Socket.IO Server Manager wrapper for claude-mpm.

WHY: This module provides a wrapper around the ServerManager class from
tools/admin/socketio_server_manager.py to make it accessible from the
scripts directory as expected by the CLI monitor command.

DESIGN DECISION: Rather than duplicating code, we import and re-export
the ServerManager class from its actual location in tools/admin. This
ensures consistency and maintainability.
"""

import sys
from pathlib import Path

# Add the tools/admin directory to Python path to import ServerManager
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent.parent  # Up to project root
tools_admin_dir = project_root / "tools" / "admin"

if tools_admin_dir.exists() and str(tools_admin_dir) not in sys.path:
    sys.path.insert(0, str(tools_admin_dir))

try:
    # Import ServerManager from the actual implementation
    import subprocess

    from socketio_server_manager import ServerManager as BaseServerManager

    # Patch the ServerManager to use project-local PID file and daemon
    class ServerManager(BaseServerManager):
        """Patched ServerManager that uses project-local PID file and daemon.

        WHY: The daemon stores its PID file in the project's .claude-mpm
        directory, not in the home directory. This patch ensures the
        ServerManager looks in the correct location and uses the daemon
        for starting servers when the standalone module is not available.
        """

        def __init__(self):
            super().__init__()
            # Override the daemon PID file path to use project root
            from claude_mpm.core.unified_paths import get_project_root

            self.daemon_pidfile_path = (
                get_project_root() / ".claude-mpm" / "socketio-server.pid"
            )
            self.daemon_script = script_dir / "socketio_daemon.py"

        def start_server(
            self, port: int = None, host: str = "localhost", server_id: str = None
        ) -> bool:
            """Start Socket.IO server, preferring daemon over standalone.

            WHY: When the standalone_socketio_server module is not available,
            we fallback to using the daemon script which is always present.
            """
            # First check if the daemon is already running
            if self.daemon_pidfile_path.exists():
                try:
                    with open(self.daemon_pidfile_path) as f:
                        pid = int(f.read().strip())
                    # Check if process is running
                    import psutil

                    process = psutil.Process(pid)
                    if process.is_running():
                        print(
                            f"Socket.IO daemon server is already running (PID: {pid})"
                        )
                        return True
                except:
                    pass

            # Try to use the daemon script for starting
            if self.daemon_script.exists():
                print(
                    f"Starting server on {host}:{port or self.base_port} using daemon..."
                )
                try:
                    result = subprocess.run(
                        [sys.executable, str(self.daemon_script), "start"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if result.returncode == 0:
                        # Check if output contains success message
                        if "started successfully" in result.stdout.lower():
                            print(result.stdout)
                            return True
                        # Even if no explicit success message, check if process is running
                        if self.daemon_pidfile_path.exists():
                            print("Socket.IO daemon server started")
                            return True
                    else:
                        # If daemon fails, try parent's start_server method
                        if result.stderr:
                            print(f"Daemon error: {result.stderr}")
                        print("Trying standalone method...")
                except Exception as e:
                    print(f"Error running daemon: {e}")

            # Fall back to parent implementation
            return super().start_server(port=port, host=host, server_id=server_id)

        def stop_server(self, port: int = None) -> bool:
            """Stop Socket.IO server, handling daemon-style servers.

            WHY: The daemon server needs special handling for stopping.
            """
            # Check if daemon is running
            if self.daemon_pidfile_path.exists():
                print("🔄 Stopping daemon server", end="")
                try:
                    with open(self.daemon_pidfile_path) as f:
                        pid = int(f.read().strip())
                    print(f" (PID: {pid})...")

                    result = subprocess.run(
                        [sys.executable, str(self.daemon_script), "stop"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if result.returncode == 0:
                        print("✅ Daemon server stopped successfully")
                        return True
                    print(f"❌ Failed to stop daemon: {result.stderr}")
                except Exception as e:
                    print(f"❌ Error stopping daemon: {e}")

            # Fall back to parent implementation for non-daemon servers
            return super().stop_server(port=port)

        def restart_server(self, port: int = None) -> bool:
            """Restart Socket.IO server, handling daemon-style servers.

            WHY: The daemon server needs special handling for restarting.
            """
            # Check if daemon is running
            if self.daemon_pidfile_path.exists():
                try:
                    with open(self.daemon_pidfile_path) as f:
                        pid = int(f.read().strip())

                    print(f"🔄 Stopping daemon server (PID: {pid})...")

                    # Stop the daemon
                    result = subprocess.run(
                        [sys.executable, str(self.daemon_script), "stop"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    if result.returncode == 0:
                        print("✅ Daemon server stopped successfully")
                        # Wait a moment for clean shutdown
                        import time

                        time.sleep(1)

                        # Start it again
                        return self.start_server(port=port)
                    print(f"❌ Failed to stop daemon: {result.stderr}")
                    return False

                except Exception as e:
                    print(f"❌ Error restarting daemon: {e}")
                    return False
            else:
                print(
                    f"❌ No daemon server found (no PID file at {self.daemon_pidfile_path})"
                )

            # Fall back to parent implementation for non-daemon servers
            return super().restart_server(port=port)

    # Re-export for use by CLI
    __all__ = ["ServerManager"]

except ImportError:
    # Fallback: If tools/admin version not available, provide basic implementation
    # that delegates to socketio_daemon.py

    import subprocess
    from typing import Any, Dict, List, Optional

    class ServerManager:
        """Fallback ServerManager that uses socketio_daemon.py.

        WHY: This fallback ensures the monitor CLI command works even if
        the full ServerManager from tools/admin is not available. It provides
        basic functionality by delegating to the socketio_daemon.py script.
        """

        def __init__(self):
            self.daemon_script = script_dir / "socketio_daemon.py"
            self.base_port = 8765

        def start_server(
            self,
            port: Optional[int] = None,
            host: str = "localhost",
            server_id: Optional[str] = None,
        ) -> bool:
            """Start the Socket.IO server using daemon script.

            WHY: The daemon script handles port selection and process management,
            so we delegate to it for starting servers.
            """
            if port and port != self.base_port:
                print(f"Note: Daemon only supports default port {self.base_port}")
                print(f"Starting on port {self.base_port} instead...")

            try:
                result = subprocess.run(
                    [sys.executable, str(self.daemon_script), "start"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    print("Socket.IO server started successfully")
                    return True
                print(f"Failed to start server: {result.stderr}")
                return False

            except Exception as e:
                print(f"Error starting server: {e}")
                return False

        def stop_server(self, port: Optional[int] = None) -> bool:
            """Stop the Socket.IO server using daemon script."""
            if port and port != self.base_port:
                print(f"Note: Daemon only supports default port {self.base_port}")

            try:
                result = subprocess.run(
                    [sys.executable, str(self.daemon_script), "stop"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    print("Socket.IO server stopped successfully")
                    return True
                print(f"Failed to stop server: {result.stderr}")
                return False

            except Exception as e:
                print(f"Error stopping server: {e}")
                return False

        def restart_server(self, port: Optional[int] = None) -> bool:
            """Restart the Socket.IO server using daemon script."""
            if port and port != self.base_port:
                print(f"Note: Daemon only supports default port {self.base_port}")

            try:
                result = subprocess.run(
                    [sys.executable, str(self.daemon_script), "restart"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    print("Socket.IO server restarted successfully")
                    return True
                print(f"Failed to restart server: {result.stderr}")
                return False

            except Exception as e:
                print(f"Error restarting server: {e}")
                return False

        def list_running_servers(self) -> List[Dict[str, Any]]:
            """List running servers using daemon script status."""
            try:
                result = subprocess.run(
                    [sys.executable, str(self.daemon_script), "status"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Parse status output to determine if server is running
                if "is running" in result.stdout:
                    # Extract port from output if possible
                    port = self.base_port
                    for line in result.stdout.split("\n"):
                        if "port" in line.lower():
                            try:
                                # Try to extract port number
                                import re

                                match = re.search(r"port\s+(\d+)", line.lower())
                                if match:
                                    port = int(match.group(1))
                            except:
                                pass

                    return [
                        {
                            "port": port,
                            "server_id": "daemon-socketio",
                            "status": "running",
                        }
                    ]
                return []

            except Exception as e:
                print(f"Error checking server status: {e}")
                return []

        def get_server_info(self, port: int) -> Optional[Dict[str, Any]]:
            """Get information about a server on a specific port."""
            servers = self.list_running_servers()
            for server in servers:
                if server.get("port") == port:
                    return server
            return None


# If running as a script, delegate to the actual socketio_server_manager.py
if __name__ == "__main__":
    try:
        # Try to run the actual script from tools/admin
        import subprocess

        tools_script = tools_admin_dir / "socketio_server_manager.py"
        if tools_script.exists():
            subprocess.run(
                [sys.executable, str(tools_script)] + sys.argv[1:], check=False
            )
        else:
            print("Socket.IO server manager not found in tools/admin")
            print("Please ensure claude-mpm is properly installed")
            sys.exit(1)
    except Exception as e:
        print(f"Error running server manager: {e}")
        sys.exit(1)
