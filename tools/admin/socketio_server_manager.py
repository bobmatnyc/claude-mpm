#!/usr/bin/env python3
"""Socket.IO Server Manager - Deployment-agnostic server management.

This script provides unified management for Socket.IO servers across different deployment scenarios:
- Local development
- PyPI installation
- Docker containers
- System service installation

Features:
- Start/stop/restart standalone servers
- Version compatibility checking
- Health monitoring and diagnostics
- Multi-instance management
- Automatic dependency installation
"""

import argparse
import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ServerManager:
    """Manages Socket.IO server instances across different deployment modes."""

    def __init__(self):
        self.base_port = 8765
        self.max_instances = 5
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        # Daemon PID file location (used by bin/socketio-daemon)
        self.daemon_pidfile_path = Path.home() / ".claude-mpm" / "socketio-server.pid"
        # Standalone server PID file location pattern
        self.standalone_pidfile_pattern = "/tmp/claude_mpm_socketio_{port}.pid"

    def get_server_info(self, port: int) -> Optional[Dict]:
        """Get server information from a running instance with daemon compatibility."""
        if not REQUESTS_AVAILABLE:
            return self._check_daemon_fallback(port)

        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                # Check if this is a daemon-style response (no 'pid' field)
                if "pid" not in data and "status" in data:
                    # Try to get PID from daemon PID file
                    daemon_pid = self._get_daemon_pid()
                    if daemon_pid:
                        data["pid"] = daemon_pid
                        data["management_style"] = "daemon"
                return data
        except Exception:
            # If HTTP fails, try daemon fallback
            return self._check_daemon_fallback(port)
        return None

    def list_running_servers(self) -> List[Dict]:
        """List all running Socket.IO servers including daemon-style servers."""
        running_servers = []

        # Check standard port range
        for port in range(self.base_port, self.base_port + self.max_instances):
            server_info = self.get_server_info(port)
            if server_info:
                server_info["port"] = port
                running_servers.append(server_info)

        # Also check for daemon-style server specifically
        daemon_info = self._get_daemon_server_info()
        if daemon_info and not any(
            s["port"] == daemon_info.get("port", self.base_port)
            for s in running_servers
        ):
            running_servers.append(daemon_info)

        return running_servers

    def find_available_port(self, start_port: Optional[int] = None) -> int:
        """Find the next available port for a new server."""
        start_port = start_port or self.base_port

        for port in range(start_port, start_port + self.max_instances):
            if not self.get_server_info(port):
                return port

        raise RuntimeError(
            f"No available ports found in range {start_port}-{start_port + self.max_instances}"
        )

    def start_server(
        self,
        port: Optional[int] = None,
        server_id: Optional[str] = None,
        host: str = "localhost",
    ) -> bool:
        """Start a standalone Socket.IO server with conflict detection."""

        # Find available port if not specified
        if port is None:
            try:
                port = self.find_available_port()
            except RuntimeError as e:
                print(f"Error: {e}")
                return False

        # Check if server is already running on this port
        existing_server = self.get_server_info(port)
        if existing_server:
            management_style = existing_server.get("management_style", "http")
            server_id_existing = existing_server.get("server_id", "unknown")

            print(f"❌ Server already running on port {port}")
            print(
                f"   Existing server: {server_id_existing} ({management_style}-managed)"
            )

            if management_style == "daemon":
                print(
                    f"💡 To stop daemon server: {self.project_root / 'bin' / 'socketio-daemon'} stop"
                )
            else:
                print(
                    f"💡 To stop server: {sys.executable} {__file__} stop --port {port}"
                )

            return False

        # Warn if daemon server exists on default port but we're starting on different port
        if port != self.base_port and self._get_daemon_pid():
            print(
                f"⚠️ Warning: Daemon server is running on port {self.base_port}, you're starting on port {port}"
            )
            print("   This may cause conflicts. Consider stopping daemon first.")

        # Try different ways to start the server based on deployment
        success = False

        # Method 1: Try installed claude-mpm package
        try:
            cmd = [
                sys.executable,
                "-m",
                "claude_mpm.services.standalone_socketio_server",
                "--host",
                host,
                "--port",
                str(port),
            ]
            if server_id:
                cmd.extend(["--server-id", server_id])

            print(f"Starting server on {host}:{port} using installed package...")

            # Start in background
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Wait for server to start
            for _ in range(10):  # Wait up to 10 seconds
                time.sleep(1)
                if self.get_server_info(port):
                    success = True
                    break

        except Exception as e:
            print(f"Failed to start via installed package: {e}")

        # Method 2: Try local development mode
        if not success:
            try:
                server_path = (
                    self.project_root
                    / "src"
                    / "claude_mpm"
                    / "services"
                    / "standalone_socketio_server.py"
                )
                if server_path.exists():
                    cmd = [
                        sys.executable,
                        str(server_path),
                        "--host",
                        host,
                        "--port",
                        str(port),
                    ]
                    if server_id:
                        cmd.extend(["--server-id", server_id])

                    print("Starting server using local development mode...")

                    # Set PYTHONPATH for local development
                    env = os.environ.copy()
                    src_path = str(self.project_root / "src")
                    if "PYTHONPATH" in env:
                        env["PYTHONPATH"] = f"{src_path}:{env['PYTHONPATH']}"
                    else:
                        env["PYTHONPATH"] = src_path

                    subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                    )

                    # Wait for server to start
                    for _ in range(10):
                        time.sleep(1)
                        if self.get_server_info(port):
                            success = True
                            break

            except Exception as e:
                print(f"Failed to start in development mode: {e}")

        if success:
            print(f"✅ Server started successfully on {host}:{port}")
            print("💡 Management commands:")
            print(f"   Status: {sys.executable} {__file__} status")
            print(f"   Stop: {sys.executable} {__file__} stop --port {port}")
            return True
        print(f"❌ Failed to start server on {host}:{port}")
        print("💡 Troubleshooting:")
        print(f"   • Check if port {port} is already in use: lsof -i :{port}")
        print(f"   • Check server status: {sys.executable} {__file__} status")
        print(
            f"   • Try different port: {sys.executable} {__file__} start --port {port + 1}"
        )
        return False

    def stop_server(
        self, port: Optional[int] = None, server_id: Optional[str] = None
    ) -> bool:
        """Stop a running Socket.IO server with daemon compatibility."""

        if port is None and server_id is None:
            print("Must specify either port or server_id")
            return False

        # Find server by ID if port not specified
        if port is None:
            running_servers = self.list_running_servers()
            for server in running_servers:
                if server.get("server_id") == server_id:
                    port = server["port"]
                    break

            if port is None:
                print(f"Server with ID '{server_id}' not found")
                return False

        # Get server info
        server_info = self.get_server_info(port)
        if not server_info:
            # Try daemon-specific stop as fallback
            return self._try_daemon_stop(port)

        # Determine management style
        management_style = server_info.get("management_style", "http")

        # Try HTTP-based stop first
        pid = server_info.get("pid")
        if pid:
            try:
                # Validate PID before attempting to kill
                if self._validate_pid(pid):
                    os.kill(pid, signal.SIGTERM)
                    print(f"✅ Sent termination signal to server (PID: {pid})")

                    # Wait for server to stop
                    for i in range(10):
                        time.sleep(1)
                        if not self.get_server_info(port):
                            print("✅ Server stopped successfully")
                            return True
                        if i == 5:  # After 5 seconds, show progress
                            print("⏳ Waiting for server to stop...")

                    # Force kill if still running
                    try:
                        if self._validate_pid(pid):
                            os.kill(pid, signal.SIGKILL)
                            print(f"⚠️ Force killed server (PID: {pid})")
                            return True
                    except OSError:
                        pass

                else:
                    print(f"⚠️ PID {pid} is no longer valid, trying daemon stop...")
                    return self._try_daemon_stop(port)

            except OSError as e:
                print(f"Error stopping server via PID {pid}: {e}")
                if management_style == "daemon":
                    print("🔄 Trying daemon-style stop...")
                    return self._try_daemon_stop(port)

        # If HTTP method failed, try daemon stop
        if management_style == "daemon" or not pid:
            print("🔄 Attempting daemon-style stop...")
            return self._try_daemon_stop(port)

        print(f"❌ Failed to stop server on port {port}")
        print(
            "💡 Try using the bin/socketio-daemon stop command if this is a daemon-managed server"
        )
        return False

    def restart_server(
        self, port: Optional[int] = None, server_id: Optional[str] = None
    ) -> bool:
        """Restart a Socket.IO server."""

        # Stop the server first
        if self.stop_server(port, server_id):
            time.sleep(2)  # Give it time to fully stop

            # Start it again
            if port is None:
                port = self.find_available_port()

            return self.start_server(port)

        return False

    def status(self, verbose: bool = False) -> None:
        """Show status of all Socket.IO servers with management style info."""
        running_servers = self.list_running_servers()

        if not running_servers:
            print("No Socket.IO servers currently running")
            print()
            print("💡 Management options:")
            print(f"  • Start with manager: {sys.executable} {__file__} start")
            print(
                f"  • Start with daemon: {self.project_root / 'bin' / 'socketio-daemon'} start"
            )
            return

        print(f"Found {len(running_servers)} running server(s):")
        print()

        for server in running_servers:
            port = server["port"]
            server_id = server.get("server_id", "unknown")
            version = server.get("server_version", "unknown")
            uptime = server.get("uptime_seconds", 0)
            clients = server.get("clients_connected", 0)
            management_style = server.get("management_style", "http")

            # Different icons based on management style
            icon = "🖥️" if management_style == "http" else "🔧"

            print(f"{icon}  Server ID: {server_id}")
            print(f"   Port: {port}")
            print(f"   Version: {version}")
            print(f"   Management: {management_style}")
            print(f"   Uptime: {self._format_uptime(uptime)}")
            print(f"   Clients: {clients}")

            if verbose:
                print(f"   PID: {server.get('pid', 'unknown')}")
                print(f"   Host: {server.get('host', 'unknown')}")

                # Show appropriate stop command
                if management_style == "daemon":
                    print(
                        f"   Stop command: {self.project_root / 'bin' / 'socketio-daemon'} stop"
                    )
                else:
                    print(
                        f"   Stop command: {sys.executable} {__file__} stop --port {port}"
                    )

                # Get additional stats (only for HTTP-style servers)
                if management_style == "http":
                    stats = self._get_server_stats(port)
                    if stats:
                        events_processed = stats.get("events", {}).get(
                            "total_processed", 0
                        )
                        clients_served = stats.get("connections", {}).get(
                            "total_served", 0
                        )
                        print(f"   Events processed: {events_processed}")
                        print(f"   Total clients served: {clients_served}")

            print()

    def health_check(self, port: Optional[int] = None) -> bool:
        """Perform health check on server(s) with management style awareness."""

        if port:
            # Check specific server
            server_info = self.get_server_info(port)
            if server_info:
                status = server_info.get("status", "unknown")
                management_style = server_info.get("management_style", "http")
                server_id = server_info.get("server_id", "unknown")

                print(
                    f"Server {server_id} on port {port}: {status} ({management_style}-managed)"
                )

                # Additional health info for daemon servers
                if management_style == "daemon":
                    pid = server_info.get("pid")
                    if pid and self._validate_pid(pid):
                        print(f"  ✅ Process {pid} is running")
                    else:
                        print(f"  ❌ Process {pid} is not running")
                        return False

                return status in ["healthy", "running"]
            print(f"No server found on port {port}")
            # Try daemon fallback for default port
            if port == self.base_port:
                daemon_info = self._get_daemon_server_info()
                if daemon_info:
                    print(f"  Found daemon server: {daemon_info['server_id']}")
                    return True
            return False
        # Check all servers
        running_servers = self.list_running_servers()
        if not running_servers:
            print("No servers running")
            print(f"💡 Start a server with: {sys.executable} {__file__} start")
            return False

        all_healthy = True
        for server in running_servers:
            port = server["port"]
            status = server.get("status", "unknown")
            server_id = server.get("server_id", "unknown")
            management_style = server.get("management_style", "http")

            health_status = status in ["healthy", "running"]
            icon = "✅" if health_status else "❌"

            print(
                f"{icon} Server {server_id} (port {port}): {status} ({management_style}-managed)"
            )

            if not health_status:
                all_healthy = False

        return all_healthy

    def install_dependencies(self) -> bool:
        """Install required dependencies for Socket.IO server."""
        dependencies = ["python-socketio>=5.11.0", "aiohttp>=3.9.0", "requests>=2.25.0"]

        print("Installing Socket.IO server dependencies...")

        try:
            cmd = [sys.executable, "-m", "pip", "install", *dependencies]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                print("✅ Dependencies installed successfully")
                return True
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False

        except Exception as e:
            print(f"❌ Error installing dependencies: {e}")
            return False

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in a human-readable way."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            return f"{seconds / 60:.1f}m"
        return f"{seconds / 3600:.1f}h"

    def _get_server_stats(self, port: int) -> Optional[Dict]:
        """Get detailed server statistics."""
        if not REQUESTS_AVAILABLE:
            return None

        try:
            response = requests.get(f"http://localhost:{port}/stats", timeout=2.0)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def _check_daemon_fallback(self, port: int) -> Optional[Dict]:
        """Check for daemon-style server when HTTP fails."""
        if port == self.base_port:  # Only check daemon for default port
            return self._get_daemon_server_info()
        return None

    def _get_daemon_pid(self) -> Optional[int]:
        """Get PID from daemon PID file."""
        try:
            if self.daemon_pidfile_path.exists():
                with open(self.daemon_pidfile_path) as f:
                    content = f.read().strip()
                    if content.isdigit():
                        pid = int(content)
                        # Validate the PID exists
                        if self._validate_pid(pid):
                            return pid
        except Exception:
            pass
        return None

    def _get_daemon_server_info(self) -> Optional[Dict]:
        """Get server info for daemon-style server."""
        daemon_pid = self._get_daemon_pid()
        if daemon_pid:
            # Basic server info for daemon
            info = {
                "pid": daemon_pid,
                "server_id": "daemon-socketio",
                "management_style": "daemon",
                "status": "running",
                "port": self.base_port,
                "server_version": "daemon-managed",
            }

            # Try to get additional process info if psutil is available
            if PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process(daemon_pid)
                    info.update(
                        {
                            "uptime_seconds": time.time() - process.create_time(),
                            "host": "localhost",
                            "process_name": process.name(),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                    pass

            return info
        return None

    def _validate_pid(self, pid: int) -> bool:
        """Validate that a PID represents a running process."""
        try:
            # Check if process exists
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _try_daemon_stop(self, port: int) -> bool:
        """Try to stop daemon-style server."""
        if port != self.base_port:
            print(
                f"⚠️ Daemon management only supports default port {self.base_port}, not {port}"
            )
            return False

        daemon_pid = self._get_daemon_pid()
        if not daemon_pid:
            print(
                f"❌ No daemon server found (no PID file at {self.daemon_pidfile_path})"
            )
            return False

        try:
            print(f"🔄 Stopping daemon server (PID: {daemon_pid})...")
            os.kill(daemon_pid, signal.SIGTERM)

            # Wait for daemon to stop
            for i in range(10):
                time.sleep(1)
                if not self._validate_pid(daemon_pid):
                    print("✅ Daemon server stopped successfully")
                    # Clean up PID file
                    with contextlib.suppress(Exception):
                        self.daemon_pidfile_path.unlink(missing_ok=True)
                    return True
                if i == 5:
                    print("⏳ Waiting for daemon to stop...")

            # Force kill if still running
            if self._validate_pid(daemon_pid):
                print("⚠️ Force killing daemon server...")
                os.kill(daemon_pid, signal.SIGKILL)
                time.sleep(1)
                if not self._validate_pid(daemon_pid):
                    print("✅ Daemon server force stopped")
                    with contextlib.suppress(Exception):
                        self.daemon_pidfile_path.unlink(missing_ok=True)
                    return True

        except OSError as e:
            print(f"❌ Error stopping daemon server: {e}")
            return False

        print("❌ Failed to stop daemon server")
        return False

    def diagnose_conflicts(self, port: Optional[int] = None) -> None:
        """Diagnose server management conflicts and suggest resolutions."""
        if port is None:
            port = self.base_port

        print(f"🔍 Diagnosing Socket.IO server management on port {port}")
        print("=" * 60)

        # Check HTTP-managed server
        http_server = None
        daemon_server = None

        try:
            if REQUESTS_AVAILABLE:
                response = requests.get(f"http://localhost:{port}/health", timeout=2.0)
                if response.status_code == 200:
                    data = response.json()
                    if "pid" in data:
                        http_server = data
        except (requests.RequestException, ValueError, KeyError):
            pass

        # Check daemon-managed server
        daemon_pid = self._get_daemon_pid()
        if daemon_pid and port == self.base_port:
            daemon_server = self._get_daemon_server_info()

        # Analysis
        print("📊 Server Analysis:")

        if http_server and daemon_server:
            print("⚠️  CONFLICT DETECTED: Both HTTP and daemon servers found!")
            print(
                f"   HTTP server: PID {http_server.get('pid')}, ID {http_server.get('server_id')}"
            )
            print(
                f"   Daemon server: PID {daemon_server.get('pid')}, ID {daemon_server.get('server_id')}"
            )
            print()
            print("🔧 Resolution Steps:")
            print("   1. Choose one management approach:")
            print(
                f"      • Keep HTTP: {sys.executable} {__file__} stop --port {port} (stops daemon)"
            )
            print(
                "      • Keep daemon: Stop HTTP server first, then use daemon commands"
            )
            print()

        elif http_server:
            print("✅ HTTP-managed server found")
            print(f"   Server ID: {http_server.get('server_id')}")
            print(f"   PID: {http_server.get('pid')}")
            print(f"   Status: {http_server.get('status')}")
            print()
            print("🔧 Management Commands:")
            print(f"   • Stop: {sys.executable} {__file__} stop --port {port}")
            print(f"   • Status: {sys.executable} {__file__} status")
            print()

        elif daemon_server:
            print("✅ Daemon-managed server found")
            print(f"   PID: {daemon_server.get('pid')}")
            print(f"   PID file: {self.daemon_pidfile_path}")
            print()
            print("🔧 Management Commands:")
            daemon_script = self.project_root / "bin" / "socketio-daemon"
            print(f"   • Stop: {daemon_script} stop")
            print(f"   • Status: {daemon_script} status")
            print(f"   • Restart: {daemon_script} restart")
            print()

        else:
            print("❌ No servers found on specified port")
            print()
            print("🔧 Start a server:")
            print(f"   • HTTP-managed: {sys.executable} {__file__} start --port {port}")
            daemon_script = self.project_root / "bin" / "socketio-daemon"
            if port == self.base_port:
                print(f"   • Daemon-managed: {daemon_script} start")
            print()

        # Port conflict check
        try:
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(("localhost", port))
                if result == 0:
                    print("🌐 Port Status: IN USE")
                    if not http_server and not daemon_server:
                        print(f"   ⚠️  Port {port} is occupied by unknown process")
                        if PSUTIL_AVAILABLE:
                            print(
                                "   🔍 Use 'lsof -i :{port}' or 'netstat -tulpn | grep {port}' to identify"
                            )
                else:
                    print("🌐 Port Status: AVAILABLE")
        except (OSError, ValueError):
            print("🌐 Port Status: UNKNOWN")

        print()
        print("📚 Management Style Comparison:")
        print("   HTTP-managed:")
        print("     • Pros: Full API, stats, multi-instance support")
        print("     • Cons: More complex, requires HTTP client")
        print("   Daemon-managed:")
        print("     • Pros: Simple, lightweight, traditional daemon")
        print("     • Cons: Single instance, basic management")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Socket.IO Server Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a Socket.IO server")
    start_parser.add_argument(
        "--port", type=int, help="Port to bind to (auto-detect if not specified)"
    )
    start_parser.add_argument("--host", default="localhost", help="Host to bind to")
    start_parser.add_argument("--server-id", help="Custom server ID")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop a Socket.IO server")
    stop_parser.add_argument("--port", type=int, help="Port of server to stop")
    stop_parser.add_argument("--server-id", help="Server ID to stop")

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart a Socket.IO server")
    restart_parser.add_argument("--port", type=int, help="Port of server to restart")
    restart_parser.add_argument("--server-id", help="Server ID to restart")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show server status")
    status_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )

    # Health check command
    health_parser = subparsers.add_parser("health", help="Perform health check")
    health_parser.add_argument(
        "--port", type=int, help="Port to check (all servers if not specified)"
    )

    # Install dependencies command
    subparsers.add_parser("install-deps", help="Install required dependencies")

    # List command
    subparsers.add_parser("list", help="List running servers")

    # Diagnose command
    diagnose_parser = subparsers.add_parser(
        "diagnose", help="Diagnose server management conflicts"
    )
    diagnose_parser.add_argument(
        "--port", type=int, default=8765, help="Port to diagnose"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = ServerManager()

    if args.command == "start":
        success = manager.start_server(
            port=args.port, server_id=args.server_id, host=args.host
        )
        sys.exit(0 if success else 1)

    elif args.command == "stop":
        success = manager.stop_server(port=args.port, server_id=args.server_id)
        sys.exit(0 if success else 1)

    elif args.command == "restart":
        success = manager.restart_server(port=args.port, server_id=args.server_id)
        sys.exit(0 if success else 1)

    elif args.command == "status":
        manager.status(verbose=args.verbose)

    elif args.command == "health":
        healthy = manager.health_check(port=args.port)
        sys.exit(0 if healthy else 1)

    elif args.command == "install-deps":
        success = manager.install_dependencies()
        sys.exit(0 if success else 1)

    elif args.command == "list":
        manager.status(verbose=False)

    elif args.command == "diagnose":
        manager.diagnose_conflicts(port=args.port)


if __name__ == "__main__":
    main()
