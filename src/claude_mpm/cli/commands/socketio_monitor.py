"""Socket.IO monitoring functionality for run commands.

This module provides Socket.IO server management and monitoring dashboard functionality.
Extracted from run.py to reduce complexity and improve maintainability.
"""

import os
import subprocess
import sys
import webbrowser

from ...core.unified_paths import get_package_root
from ...services.port_manager import PortManager


class SocketIOMonitor:
    """Handles Socket.IO monitoring and server management."""

    def __init__(self, logger):
        """Initialize the Socket.IO monitor."""
        self.logger = logger

    def launch_monitor(self, port):
        """
        Launch the Socket.IO monitoring dashboard using static HTML file.

        Returns:
            tuple: (success: bool, browser_opened: bool)
        """
        try:
            # Verify Socket.IO dependencies are available
            try:
                import aiohttp
                import engineio
                import socketio

                self.logger.debug("Socket.IO dependencies verified")
            except ImportError as e:
                self.logger.error(f"Socket.IO dependencies not available: {e}")
                print(f"❌ Socket.IO dependencies missing: {e}")
                print("  This is unexpected - dependency installation may have failed.")
                return False, False

            print("🚀 Setting up Socket.IO monitor...")
            self.logger.info(f"Launching Socket.IO monitor (requested port: {port})")

            # First, check if there's already a running SocketIO server
            port_manager = PortManager()
            port_manager.cleanup_dead_instances()
            active_instances = port_manager.list_active_instances()

            if active_instances:
                # Use the first active instance (prefer port 8765 if available)
                socketio_port = None
                for instance in active_instances:
                    if instance.get("port") == 8765:
                        socketio_port = 8765
                        break
                if not socketio_port:
                    socketio_port = active_instances[0].get("port")

                print(f"🔍 Found existing SocketIO server on port {socketio_port}")
                server_running = True
            else:
                # No existing server, use requested port
                socketio_port = port
                server_running = self.check_server_running(socketio_port)

            # Use HTTP URL to access dashboard from Socket.IO server
            dashboard_url = f"http://localhost:{socketio_port}"

            if server_running:
                print(f"✅ Socket.IO server already running on port {socketio_port}")
                print(f"📊 Dashboard: {dashboard_url}")

                # Open browser with static HTML file
                try:
                    # Check if we should suppress browser opening (for tests)
                    if os.environ.get("CLAUDE_MPM_NO_BROWSER") != "1":
                        print("🌐 Opening dashboard in browser...")
                        self.open_in_browser_tab(dashboard_url)
                        self.logger.info(f"Socket.IO dashboard opened: {dashboard_url}")
                    else:
                        print("🌐 Browser opening suppressed (CLAUDE_MPM_NO_BROWSER=1)")
                        self.logger.info(
                            "Browser opening suppressed by environment variable"
                        )
                    return True, True
                except Exception as e:
                    self.logger.warning(f"Failed to open browser: {e}")
                    print("⚠️  Could not open browser automatically")
                    print(f"📊 Please open manually: {dashboard_url}")
                    return True, False
            else:
                # Start standalone Socket.IO server
                print("🔧 Starting Socket.IO server...")
                server_started = self.start_standalone_server(socketio_port)

                if server_started:
                    print("✅ Socket.IO server started successfully")
                    print(f"📊 Dashboard: {dashboard_url}")

                    # Open browser
                    try:
                        if os.environ.get("CLAUDE_MPM_NO_BROWSER") != "1":
                            print("🌐 Opening dashboard in browser...")
                            self.open_in_browser_tab(dashboard_url)
                            self.logger.info(
                                f"Socket.IO dashboard opened: {dashboard_url}"
                            )
                        else:
                            print(
                                "🌐 Browser opening suppressed (CLAUDE_MPM_NO_BROWSER=1)"
                            )
                        return True, True
                    except Exception as e:
                        self.logger.warning(f"Failed to open browser: {e}")
                        print("⚠️  Could not open browser automatically")
                        print(f"📊 Please open manually: {dashboard_url}")
                        return True, False
                else:
                    print("❌ Failed to start Socket.IO server")
                    print("💡 Troubleshooting tips:")
                    print(f"   - Check if port {socketio_port} is already in use")
                    print(
                        "   - Verify Socket.IO dependencies: pip install python-socketio aiohttp"
                    )
                    print("   - Try a different port with --websocket-port")
                    return False, False

        except Exception as e:
            self.logger.error(f"Failed to launch Socket.IO monitor: {e}")
            print(f"❌ Failed to launch Socket.IO monitor: {e}")
            return False, False

    def check_server_running(self, port):
        """Check if a Socket.IO server is running on the specified port."""
        try:
            import socket
            import urllib.error
            import urllib.request

            # First, do a basic TCP connection check
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    result = s.connect_ex(("127.0.0.1", port))
                    if result != 0:
                        self.logger.debug(f"TCP connection to port {port} failed")
                        return False
            except Exception as e:
                self.logger.debug(f"TCP socket check failed for port {port}: {e}")
                return False

            # If TCP connection succeeds, try HTTP health check
            try:
                response = urllib.request.urlopen(
                    f"http://localhost:{port}/status", timeout=5
                )
                if response.getcode() == 200:
                    self.logger.debug(
                        f"✅ Socket.IO server health check passed on port {port}"
                    )
                    return True
            except Exception as e:
                self.logger.debug(f"HTTP health check failed for port {port}: {e}")

        except Exception as e:
            self.logger.debug(
                f"❌ Unexpected error checking Socket.IO server on port {port}: {e}"
            )

        return False

    def start_standalone_server(self, port):
        """Start a standalone Socket.IO server using the Python daemon."""
        try:
            daemon_script = get_package_root() / "scripts" / "socketio_daemon.py"
            if not daemon_script.exists():
                self.logger.error(f"Daemon script not found: {daemon_script}")
                return False

            # Start the daemon
            result = subprocess.run(
                [sys.executable, str(daemon_script), "start", "--port", str(port)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                self.logger.info(
                    f"Socket.IO daemon started successfully on port {port}"
                )
                return True
            self.logger.error(f"Failed to start Socket.IO daemon: {result.stderr}")
            return False

        except Exception as e:
            self.logger.error(f"Failed to start standalone Socket.IO server: {e}")
            return False

    def open_in_browser_tab(self, url):
        """Open URL in browser, attempting to reuse existing tabs when possible."""
        try:
            # Try different methods based on platform
            import platform

            system = platform.system().lower()

            if system == "darwin":  # macOS
                try:
                    # Try to open in existing tab
                    subprocess.run(["open", "-g", url], check=True, timeout=5)
                    return
                except Exception:
                    pass
            elif system == "linux":
                try:
                    # Try xdg-open
                    subprocess.run(["xdg-open", url], check=True, timeout=5)
                    return
                except Exception:
                    pass

            # Fallback to standard webbrowser
            webbrowser.open(url)

        except Exception as e:
            self.logger.warning(f"Browser opening failed: {e}")
            # Final fallback
            webbrowser.open(url)
