#!/usr/bin/env python3
"""
Comprehensive diagnostic tool for dashboard disconnection issues.

This script monitors and diagnoses what's causing the dashboard disconnections:
1. Server process lifecycle (PID changes, restarts)
2. WebSocket connection stability
3. File system events that might trigger restarts
4. Resource usage and port conflicts
"""

import asyncio
import json
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import psutil

try:
    import socketio
except ImportError:
    print("⚠️  python-socketio not installed. Installing for diagnostics...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "python-socketio[client]"]
    )
    import socketio


class ServerProcessMonitor:
    """Monitor the SocketIO server process for restarts and crashes."""

    def __init__(self, port: int = 8765):
        self.port = port
        self.events: List[Dict] = []
        self.current_pid: Optional[int] = None
        self.monitoring = False

    def find_server_process(self) -> Optional[int]:
        """Find the PID of the process listening on the target port."""
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == self.port and conn.status == "LISTEN":
                try:
                    process = psutil.Process(conn.pid)
                    # Check if it's a Python process (our server)
                    if "python" in process.name().lower():
                        return conn.pid
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return None

    def monitor_loop(self):
        """Main monitoring loop for server process."""
        print(f"🔍 Starting server process monitor on port {self.port}...")

        while self.monitoring:
            pid = self.find_server_process()
            timestamp = datetime.now(timezone.utc).isoformat()

            if pid != self.current_pid:
                if self.current_pid is None and pid:
                    # Server started
                    event = {
                        "type": "server_started",
                        "timestamp": timestamp,
                        "old_pid": None,
                        "new_pid": pid,
                        "message": f"Server started with PID {pid}",
                    }
                    self.events.append(event)
                    print(f"✅ {timestamp}: {event['message']}")

                elif self.current_pid and pid is None:
                    # Server stopped
                    event = {
                        "type": "server_stopped",
                        "timestamp": timestamp,
                        "old_pid": self.current_pid,
                        "new_pid": None,
                        "message": f"Server stopped (was PID {self.current_pid})",
                    }
                    self.events.append(event)
                    print(f"❌ {timestamp}: {event['message']}")

                elif self.current_pid and pid and self.current_pid != pid:
                    # Server restarted (PID changed)
                    event = {
                        "type": "server_restarted",
                        "timestamp": timestamp,
                        "old_pid": self.current_pid,
                        "new_pid": pid,
                        "message": f"Server RESTARTED! PID changed from {self.current_pid} to {pid}",
                    }
                    self.events.append(event)
                    print(f"🔄 {timestamp}: {event['message']}")

                self.current_pid = pid

            # Check process health if running
            if pid:
                try:
                    process = psutil.Process(pid)
                    cpu_percent = process.cpu_percent(interval=0.1)
                    memory_info = process.memory_info()

                    if cpu_percent > 80:
                        print(f"⚠️  High CPU usage: {cpu_percent:.1f}%")
                    if memory_info.rss > 500 * 1024 * 1024:  # 500MB
                        print(
                            f"⚠️  High memory usage: {memory_info.rss / 1024 / 1024:.1f}MB"
                        )

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            time.sleep(1)  # Check every second

    def start(self):
        """Start monitoring in a background thread."""
        self.monitoring = True
        self.thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop monitoring."""
        self.monitoring = False
        if hasattr(self, "thread"):
            self.thread.join(timeout=2)

    def get_summary(self) -> Dict:
        """Get summary of monitoring results."""
        restarts = len([e for e in self.events if e["type"] == "server_restarted"])
        stops = len([e for e in self.events if e["type"] == "server_stopped"])
        starts = len([e for e in self.events if e["type"] == "server_started"])

        return {
            "total_events": len(self.events),
            "restarts": restarts,
            "stops": stops,
            "starts": starts,
            "events": self.events[-10:],  # Last 10 events
        }


class WebSocketConnectionMonitor:
    """Monitor WebSocket connections to detect disconnection patterns."""

    def __init__(self, port: int = 8765):
        self.port = port
        self.url = f"http://localhost:{port}"
        self.events: List[Dict] = []
        self.connection_count = 0
        self.disconnection_count = 0
        self.sio = None
        self.connected = False
        self.connection_start = None

    async def connect_and_monitor(self):
        """Connect to the SocketIO server and monitor connection stability."""
        print(f"🔌 Connecting to WebSocket at {self.url}...")

        self.sio = socketio.AsyncClient(
            logger=False,
            engineio_logger=False,
            reconnection=True,
            reconnection_attempts=0,  # Infinite attempts
            reconnection_delay=1,
            reconnection_delay_max=5,
        )

        @self.sio.on("connect")
        async def on_connect():
            self.connection_count += 1
            self.connected = True
            self.connection_start = time.time()
            timestamp = datetime.now(timezone.utc).isoformat()

            event = {
                "type": "connected",
                "timestamp": timestamp,
                "connection_number": self.connection_count,
                "message": f"Connected (connection #{self.connection_count})",
            }
            self.events.append(event)
            print(f"✅ {timestamp}: WebSocket connected (#{self.connection_count})")

        @self.sio.on("disconnect")
        async def on_disconnect():
            self.disconnection_count += 1
            self.connected = False
            timestamp = datetime.now(timezone.utc).isoformat()

            # Calculate connection duration
            duration = None
            if self.connection_start:
                duration = time.time() - self.connection_start
                self.connection_start = None

            event = {
                "type": "disconnected",
                "timestamp": timestamp,
                "disconnection_number": self.disconnection_count,
                "duration_seconds": duration,
                "message": (
                    f"Disconnected (#{self.disconnection_count}, lasted {duration:.1f}s)"
                    if duration
                    else f"Disconnected (#{self.disconnection_count})"
                ),
            }
            self.events.append(event)
            print(
                f"❌ {timestamp}: WebSocket disconnected (#{self.disconnection_count}, lasted {duration:.1f}s)"
                if duration
                else f"❌ {timestamp}: WebSocket disconnected (#{self.disconnection_count})"
            )

        @self.sio.on("connect_error")
        async def on_connect_error(data):
            timestamp = datetime.now(timezone.utc).isoformat()
            event = {
                "type": "connect_error",
                "timestamp": timestamp,
                "error": str(data),
                "message": f"Connection error: {data}",
            }
            self.events.append(event)
            print(f"⚠️  {timestamp}: Connection error: {data}")

        try:
            await self.sio.connect(self.url)

            # Keep connection alive and monitor
            while True:
                await asyncio.sleep(1)

                # Send ping to keep connection alive
                if self.connected:
                    try:
                        await self.sio.emit("ping", {"timestamp": time.time()})
                    except Exception as e:
                        print(f"⚠️  Failed to send ping: {e}")

        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            self.events.append(
                {
                    "type": "connection_failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                    "message": f"Failed to connect: {e}",
                }
            )

    def get_summary(self) -> Dict:
        """Get summary of connection monitoring."""
        avg_duration = 0
        durations = [
            e.get("duration_seconds", 0)
            for e in self.events
            if e["type"] == "disconnected" and e.get("duration_seconds")
        ]
        if durations:
            avg_duration = sum(durations) / len(durations)

        return {
            "total_connections": self.connection_count,
            "total_disconnections": self.disconnection_count,
            "average_connection_duration": avg_duration,
            "currently_connected": self.connected,
            "events": self.events[-10:],  # Last 10 events
        }


class ResourceMonitor:
    """Monitor system resources and port conflicts."""

    def __init__(self, port: int = 8765):
        self.port = port
        self.events: List[Dict] = []

    def check_port_conflicts(self) -> List[Dict]:
        """Check for processes that might conflict with the server port."""
        conflicts = []

        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == self.port:
                try:
                    process = psutil.Process(conn.pid)
                    conflicts.append(
                        {
                            "pid": conn.pid,
                            "name": process.name(),
                            "cmdline": " ".join(process.cmdline()[:3]),  # First 3 args
                            "status": conn.status,
                            "created": datetime.fromtimestamp(
                                process.create_time()
                            ).isoformat(),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        return conflicts

    def check_system_resources(self) -> Dict:
        """Check system resource usage."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage("/").percent,
            "open_files": len(psutil.Process().open_files()),
            "connections": len(psutil.net_connections()),
        }

    def monitor_loop(self):
        """Monitor resources periodically."""
        while True:
            timestamp = datetime.now(timezone.utc).isoformat()

            # Check port conflicts
            conflicts = self.check_port_conflicts()
            if len(conflicts) > 1:  # More than just our server
                print(
                    f"⚠️  {timestamp}: Multiple processes on port {self.port}: {conflicts}"
                )
                self.events.append(
                    {
                        "type": "port_conflict",
                        "timestamp": timestamp,
                        "conflicts": conflicts,
                    }
                )

            # Check resources
            resources = self.check_system_resources()
            if resources["cpu_percent"] > 80:
                print(f"⚠️  {timestamp}: High CPU usage: {resources['cpu_percent']}%")
            if resources["memory_percent"] > 80:
                print(
                    f"⚠️  {timestamp}: High memory usage: {resources['memory_percent']}%"
                )

            time.sleep(5)  # Check every 5 seconds


class FileSystemMonitor:
    """Monitor file system changes that might trigger restarts."""

    def __init__(self):
        self.events: List[Dict] = []
        self.monitoring_paths = [
            Path.cwd() / "src",
            Path.cwd() / ".claude",
            Path.cwd() / "claude.json",
        ]

    def check_file_changes(self):
        """Check for recent file modifications."""
        recent_changes = []
        cutoff_time = time.time() - 60  # Files changed in last minute

        for path in self.monitoring_paths:
            if not path.exists():
                continue

            if path.is_file():
                if path.stat().st_mtime > cutoff_time:
                    recent_changes.append(
                        {
                            "path": str(path),
                            "modified": datetime.fromtimestamp(
                                path.stat().st_mtime
                            ).isoformat(),
                        }
                    )
            else:
                # Check directory recursively (limited depth)
                for file_path in path.rglob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime > cutoff_time:
                        recent_changes.append(
                            {
                                "path": str(file_path),
                                "modified": datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                ).isoformat(),
                            }
                        )

                        # Limit to prevent too much output
                        if len(recent_changes) > 20:
                            break

        return recent_changes


async def run_diagnostics(duration: int = 60):
    """Run all diagnostics for specified duration."""
    print("=" * 60)
    print("🔬 CLAUDE-MPM DASHBOARD DISCONNECTION DIAGNOSTICS")
    print("=" * 60)
    print(f"Running diagnostics for {duration} seconds...")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 60)

    # Initialize monitors
    server_monitor = ServerProcessMonitor()
    websocket_monitor = WebSocketConnectionMonitor()
    resource_monitor = ResourceMonitor()
    filesystem_monitor = FileSystemMonitor()

    # Start server process monitoring
    server_monitor.start()

    # Start resource monitoring in background
    resource_thread = threading.Thread(
        target=resource_monitor.monitor_loop, daemon=True
    )
    resource_thread.start()

    # Start WebSocket monitoring
    websocket_task = asyncio.create_task(websocket_monitor.connect_and_monitor())

    # Run for specified duration
    start_time = time.time()
    last_fs_check = start_time

    try:
        while time.time() - start_time < duration:
            await asyncio.sleep(5)

            # Check file system changes every 10 seconds
            if time.time() - last_fs_check > 10:
                changes = filesystem_monitor.check_file_changes()
                if changes:
                    print(f"📝 Recent file changes detected: {len(changes)} files")
                    for change in changes[:5]:  # Show first 5
                        print(f"   - {change['path']}")
                last_fs_check = time.time()

    except KeyboardInterrupt:
        print("\n⚠️  Diagnostics interrupted by user")

    # Stop monitoring
    server_monitor.stop()
    websocket_task.cancel()

    # Generate report
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC RESULTS")
    print("=" * 60)

    # Server process summary
    server_summary = server_monitor.get_summary()
    print("\n🖥️  SERVER PROCESS MONITORING:")
    print(f"   Total events: {server_summary['total_events']}")
    print(
        f"   Server restarts: {server_summary['restarts']} ⚠️"
        if server_summary["restarts"] > 0
        else "   Server restarts: 0 ✅"
    )
    print(f"   Server stops: {server_summary['stops']}")
    print(f"   Server starts: {server_summary['starts']}")

    if server_summary["restarts"] > 0:
        print(
            "\n   ⚠️  SERVER IS RESTARTING - This is likely the cause of disconnections!"
        )
        print("   Recent restart events:")
        for event in server_summary["events"]:
            if event["type"] == "server_restarted":
                print(f"      - {event['timestamp']}: {event['message']}")

    # WebSocket connection summary
    ws_summary = websocket_monitor.get_summary()
    print("\n🔌 WEBSOCKET CONNECTION MONITORING:")
    print(f"   Total connections: {ws_summary['total_connections']}")
    print(f"   Total disconnections: {ws_summary['total_disconnections']}")
    if ws_summary["average_connection_duration"] > 0:
        print(
            f"   Average connection duration: {ws_summary['average_connection_duration']:.1f} seconds"
        )
    print(
        f"   Currently connected: {'Yes' if ws_summary['currently_connected'] else 'No'}"
    )

    # Resource summary
    print("\n💻 SYSTEM RESOURCES:")
    resources = resource_monitor.check_system_resources()
    print(f"   CPU usage: {resources['cpu_percent']}%")
    print(f"   Memory usage: {resources['memory_percent']}%")
    print(f"   Open files: {resources['open_files']}")

    # Port conflicts
    conflicts = resource_monitor.check_port_conflicts()
    if len(conflicts) > 1:
        print(f"\n⚠️  PORT CONFLICTS DETECTED on port {resource_monitor.port}:")
        for conflict in conflicts:
            print(
                f"   - PID {conflict['pid']}: {conflict['name']} ({conflict['status']})"
            )

    # File system changes
    recent_changes = filesystem_monitor.check_file_changes()
    if recent_changes:
        print("\n📝 RECENT FILE CHANGES (last minute):")
        for change in recent_changes[:10]:
            print(f"   - {change['path']}: {change['modified']}")

    # Diagnosis
    print("\n" + "=" * 60)
    print("🔍 DIAGNOSIS:")
    print("=" * 60)

    if server_summary["restarts"] > 0:
        print("❌ PROBLEM IDENTIFIED: Server is restarting periodically")
        print("   This is causing the dashboard disconnections.")
        print("\n   Possible causes:")
        print("   1. File watcher detecting changes and triggering auto-reload")
        print("   2. Watchdog/supervisor restarting on file changes")
        print("   3. Memory issues causing process crashes")
        print("   4. Unhandled exceptions in server code")
        print("\n   Recommended actions:")
        print("   1. Check if watchdog is monitoring agent files")
        print("   2. Disable auto-reload features when running with --monitor")
        print("   3. Check server logs for exceptions")

    elif ws_summary["total_disconnections"] > 0 and server_summary["restarts"] == 0:
        print("⚠️  PROBLEM: WebSocket disconnections without server restarts")
        print("   The connection is dropping but the server stays up.")
        print("\n   Possible causes:")
        print("   1. Network/firewall issues")
        print("   2. Client-side timeout settings")
        print("   3. SocketIO heartbeat/ping issues")

    else:
        print("✅ No issues detected during monitoring period")
        print("   The dashboard connection appears stable.")

    # Save full report
    report_file = (
        Path.cwd()
        / f"diagnostic_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    )
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": duration,
        "server_monitoring": server_summary,
        "websocket_monitoring": ws_summary,
        "resource_monitoring": {
            "final_snapshot": resources,
            "port_conflicts": conflicts,
            "events": resource_monitor.events,
        },
        "filesystem_monitoring": {"recent_changes": recent_changes[:20]},
    }

    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    print(f"\n📄 Full report saved to: {report_file}")
    print("=" * 60)


if __name__ == "__main__":
    # Parse arguments
    duration = 60  # Default 60 seconds
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [duration_in_seconds]")
            sys.exit(1)

    # Run diagnostics
    asyncio.run(run_diagnostics(duration))
