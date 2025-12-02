#!/usr/bin/env python3
"""
Professional SocketIO debugging tool for dashboard development.

This tool provides real-time monitoring and analysis of SocketIO events
for developers working on the claude-mpm dashboard.
"""

import argparse
import asyncio

# Try to import Rich for enhanced output
import importlib.util
import json
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import socketio

if importlib.util.find_spec("rich"):
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
    console = Console()
else:
    RICH_AVAILABLE = False
    console = None


class DisplayMode(Enum):
    """Display modes for event output."""

    LIVE = "live"
    SUMMARY = "summary"
    FILTERED = "filtered"
    RAW = "raw"
    PRETTY = "pretty"


class ConnectionStatus(Enum):
    """Connection status states."""

    DISCONNECTED = "❌ Disconnected"
    CONNECTING = "⏳ Connecting"
    CONNECTED = "✅ Connected"
    ERROR = "⚠️ Error"
    RECONNECTING = "🔄 Reconnecting"


@dataclass
class EventStats:
    """Statistics for event tracking."""

    total_count: int = 0
    event_types: Dict[str, int] = field(default_factory=dict)
    tool_usage: Dict[str, int] = field(default_factory=dict)
    sessions: Set[str] = field(default_factory=set)
    first_event_time: Optional[float] = None
    last_event_time: Optional[float] = None
    events_per_second: float = 0.0

    def update_rate(self):
        """Update events per second rate."""
        if self.first_event_time and self.last_event_time:
            duration = self.last_event_time - self.first_event_time
            if duration > 0:
                self.events_per_second = self.total_count / duration


class SocketIODebugger:
    """Professional SocketIO debugging tool."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        mode: DisplayMode = DisplayMode.LIVE,
        filter_types: Optional[List[str]] = None,
        output_file: Optional[Path] = None,
        quiet: bool = False,
        show_raw: bool = False,
        max_reconnect_attempts: int = 10,
        reconnect_delay: float = 1.0,
    ):
        """Initialize the debugger."""
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self.mode = mode
        self.filter_types = filter_types or []
        self.output_file = output_file
        self.quiet = quiet
        self.show_raw = show_raw
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay

        # SocketIO client
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=max_reconnect_attempts,
            reconnection_delay=reconnect_delay,
            reconnection_delay_max=30,
            logger=False,
            engineio_logger=False,
        )

        # State tracking
        self.status = ConnectionStatus.DISCONNECTED
        self.stats = EventStats()
        self.events: List[Dict[str, Any]] = []
        self.connection_start = None
        self.latency = 0.0
        self.running = True
        self.output_buffer = []

        # Setup event handlers
        self._setup_handlers()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _setup_handlers(self):
        """Setup SocketIO event handlers."""

        @self.sio.event
        def connect():
            """Handle connection event."""
            self.status = ConnectionStatus.CONNECTED
            self.connection_start = time.time()
            self._log("success", f"Connected to {self.url}")
            self._log("info", f"Socket ID: {self.sio.sid}")

            # Request initial status and history
            self.sio.emit("get_status")
            self.sio.emit("get_history", {"limit": 50, "event_types": []})

        @self.sio.event
        def disconnect():
            """Handle disconnection event."""
            self.status = ConnectionStatus.DISCONNECTED
            self._log("warning", "Disconnected from server")

        @self.sio.event
        def connect_error(data):
            """Handle connection error."""
            self.status = ConnectionStatus.ERROR
            self._log("error", f"Connection error: {data}")

        @self.sio.event
        def claude_event(data):
            """Handle Claude event."""
            self._process_event(data)

        @self.sio.event
        def status(data):
            """Handle status response."""
            self._log("info", "Server Status:")
            if not self.quiet:
                self._format_json(data, indent=2)

        @self.sio.event
        def history(data):
            """Handle history response."""
            if data.get("events"):
                event_count = len(data["events"])
                self._log("info", f"Received {event_count} historical events")
                for event in data["events"]:
                    self._process_event(event, is_historical=True)

        # Ping/pong for latency measurement
        @self.sio.event
        def pong(data):
            """Handle pong response for latency measurement."""
            if "timestamp" in data:
                self.latency = (time.time() - data["timestamp"]) * 1000

    def _process_event(self, data: Dict[str, Any], is_historical: bool = False):
        """Process an incoming event."""
        # Update statistics
        self.stats.total_count += 1
        event_type = data.get("type", "unknown")

        # Track event types
        self.stats.event_types[event_type] = (
            self.stats.event_types.get(event_type, 0) + 1
        )

        # Track tool usage
        if "tool" in data.get("data", {}):
            tool_name = data["data"]["tool"]
            self.stats.tool_usage[tool_name] = (
                self.stats.tool_usage.get(tool_name, 0) + 1
            )

        # Track sessions
        if "session_id" in data.get("data", {}):
            self.stats.sessions.add(data["data"]["session_id"])

        # Update timestamps
        current_time = time.time()
        if not self.stats.first_event_time:
            self.stats.first_event_time = current_time
        self.stats.last_event_time = current_time
        self.stats.update_rate()

        # Store event
        self.events.append(data)
        if len(self.events) > 10000:  # Keep last 10k events
            self.events = self.events[-10000:]

        # Apply filtering
        if self.filter_types and event_type not in self.filter_types:
            return

        # Display based on mode
        if not self.quiet and not is_historical:
            self._display_event(data)

        # Write to file if specified
        if self.output_file:
            self._write_to_file(data)

    def _display_event(self, data: Dict[str, Any]):
        """Display an event based on current mode."""
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        event_type = data.get("type", "unknown")
        event_data = data.get("data", {})

        if self.show_raw or self.mode == DisplayMode.RAW:
            # Raw JSON output
            print(json.dumps(data, indent=2))
            print("-" * 50)
        elif self.mode == DisplayMode.PRETTY or (
            self.mode == DisplayMode.LIVE and RICH_AVAILABLE
        ):
            # Pretty formatted output
            self._display_pretty(timestamp, event_type, event_data)
        else:
            # Basic formatted output
            self._display_basic(timestamp, event_type, event_data)

    def _display_pretty(
        self, timestamp: str, event_type: str, event_data: Dict[str, Any]
    ):
        """Display event with rich formatting."""
        if not RICH_AVAILABLE:
            return self._display_basic(timestamp, event_type, event_data)

        # Event type icons
        icons = {
            "Start": "🚀",
            "Stop": "🛑",
            "SubagentStart": "🤖",
            "SubagentStop": "🤖",
            "PreToolUse": "🔧",
            "PostToolUse": "✅",
            "Error": "❌",
            "Warning": "⚠️",
            "Info": "[INFO]️",
            "MemoryUpdate": "🧠",
            "ConfigChange": "⚙️",
        }

        icon = icons.get(event_type, "📨")

        # Format the event
        output = Text()
        output.append(f"[{timestamp}] ", style="dim cyan")
        output.append(f"{icon} {event_type}", style="bold yellow")

        # Add key details
        if "tool" in event_data:
            output.append("\n├─ Tool: ", style="dim")
            output.append(event_data["tool"], style="green")

        if "session_id" in event_data:
            output.append("\n├─ Session: ", style="dim")
            output.append(event_data["session_id"][:8], style="blue")

        if "agent" in event_data:
            output.append("\n├─ Agent: ", style="dim")
            output.append(event_data["agent"], style="magenta")

        if "duration" in event_data:
            output.append("\n├─ Duration: ", style="dim")
            output.append(f"{event_data['duration']:.2f}s", style="cyan")

        if "success" in event_data:
            success_icon = "✓" if event_data["success"] else "✗"
            success_style = "green" if event_data["success"] else "red"
            output.append("\n└─ Result: ", style="dim")
            output.append(f"{success_icon}", style=success_style)

        console.print(output)
        console.print("─" * 50, style="dim")
        return None

    def _display_basic(
        self, timestamp: str, event_type: str, event_data: Dict[str, Any]
    ):
        """Display event with basic formatting."""
        print(f"[{timestamp}] {event_type}")

        if "tool" in event_data:
            print(f"  Tool: {event_data['tool']}")
        if "session_id" in event_data:
            print(f"  Session: {event_data['session_id'][:8]}")
        if "agent" in event_data:
            print(f"  Agent: {event_data['agent']}")
        if "duration" in event_data:
            print(f"  Duration: {event_data['duration']:.2f}s")
        if "success" in event_data:
            print(f"  Success: {event_data['success']}")

        print("-" * 50)

    def _display_summary(self):
        """Display event summary statistics."""
        if RICH_AVAILABLE:
            self._display_summary_rich()
        else:
            self._display_summary_basic()

    def _display_summary_rich(self):
        """Display rich summary with tables."""
        # Connection info panel
        conn_info = Panel(
            f"Server: {self.url}\n"
            f"Status: {self.status.value}\n"
            f"Latency: {self.latency:.0f}ms\n"
            f"Uptime: {self._get_uptime()}",
            title="Connection Info",
            border_style="blue",
        )

        # Event statistics table
        stats_table = Table(title="Event Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="yellow")

        stats_table.add_row("Total Events", str(self.stats.total_count))
        stats_table.add_row("Events/Second", f"{self.stats.events_per_second:.2f}")
        stats_table.add_row("Active Sessions", str(len(self.stats.sessions)))

        # Event types table
        types_table = Table(title="Event Types")
        types_table.add_column("Event Type", style="magenta")
        types_table.add_column("Count", style="green")

        for event_type, count in sorted(
            self.stats.event_types.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            types_table.add_row(event_type, str(count))

        # Tool usage table
        if self.stats.tool_usage:
            tools_table = Table(title="Tool Usage")
            tools_table.add_column("Tool", style="blue")
            tools_table.add_column("Count", style="yellow")

            for tool, count in sorted(
                self.stats.tool_usage.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                tools_table.add_row(tool, str(count))

            console.print(conn_info)
            console.print(stats_table)
            console.print(types_table)
            console.print(tools_table)
        else:
            console.print(conn_info)
            console.print(stats_table)
            console.print(types_table)

    def _display_summary_basic(self):
        """Display basic summary."""
        print("\n" + "=" * 60)
        print("SOCKETIO EVENT MONITOR SUMMARY")
        print("=" * 60)
        print(f"Server: {self.url}")
        print(f"Status: {self.status.value}")
        print(f"Latency: {self.latency:.0f}ms")
        print(f"Uptime: {self._get_uptime()}")
        print("-" * 60)
        print(f"Total Events: {self.stats.total_count}")
        print(f"Events/Second: {self.stats.events_per_second:.2f}")
        print(f"Active Sessions: {len(self.stats.sessions)}")
        print("-" * 60)
        print("Event Types:")
        for event_type, count in sorted(
            self.stats.event_types.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"  {event_type}: {count}")

        if self.stats.tool_usage:
            print("-" * 60)
            print("Tool Usage:")
            for tool, count in sorted(
                self.stats.tool_usage.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                print(f"  {tool}: {count}")

        print("=" * 60)

    def _get_uptime(self) -> str:
        """Get formatted uptime string."""
        if not self.connection_start:
            return "00:00:00"

        uptime = time.time() - self.connection_start
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _write_to_file(self, data: Dict[str, Any]):
        """Write event to output file."""
        if not self.output_file:
            return

        try:
            with self.output_file.open("a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self._log("error", f"Failed to write to file: {e}")

    def _format_json(self, data: Any, indent: int = 2):
        """Format and print JSON data."""
        try:
            formatted = json.dumps(data, indent=indent, default=str)
            print(formatted)
        except Exception as e:
            print(f"Failed to format JSON: {e}")
            print(data)

    def _log(self, level: str, message: str):
        """Log a message with appropriate formatting."""
        if self.quiet and level not in ["error", "critical"]:
            return

        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")

        if RICH_AVAILABLE:
            styles = {
                "info": "blue",
                "success": "green",
                "warning": "yellow",
                "error": "red bold",
                "critical": "red bold on white",
            }
            style = styles.get(level, "white")
            console.print(f"[{timestamp}] {message}", style=style)
        else:
            prefixes = {
                "info": "[INFO]️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🚨",
            }
            prefix = prefixes.get(level, "")
            print(f"[{timestamp}] {prefix} {message}")

    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signal."""
        self._log("info", "\nShutting down gracefully...")
        self.running = False
        self.stop()

    async def _monitor_latency(self):
        """Monitor connection latency."""
        while self.running and self.status == ConnectionStatus.CONNECTED:
            try:
                # Send ping with timestamp
                self.sio.emit("ping", {"timestamp": time.time()})
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception:
                pass

    def connect(self) -> bool:
        """Connect to the SocketIO server."""
        self._log("info", f"Connecting to {self.url}...")
        self.status = ConnectionStatus.CONNECTING

        try:
            self.sio.connect(self.url, wait_timeout=10)
            return True
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self._log("error", f"Failed to connect: {e}")
            return False

    def run(self):
        """Run the debugger."""
        # Print header
        if not self.quiet:
            self._print_header()

        # Connect to server
        if not self.connect():
            return False

        # Start latency monitoring
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        latency_task = loop.create_task(self._monitor_latency())

        try:
            # Main monitoring loop
            while self.running:
                try:
                    if self.mode == DisplayMode.SUMMARY:
                        # In summary mode, update display periodically
                        time.sleep(1)
                        if not self.quiet:
                            # Clear screen and show summary
                            print("\033[2J\033[H")  # Clear screen
                            self._display_summary()
                    else:
                        # In other modes, just keep connection alive
                        time.sleep(0.1)

                    # Check connection health
                    if not self.sio.connected and self.running:
                        self.status = ConnectionStatus.RECONNECTING
                        self._log(
                            "warning", "Connection lost, attempting to reconnect..."
                        )
                        self.connect()

                except KeyboardInterrupt:
                    break

        finally:
            # Clean up
            latency_task.cancel()
            self.stop()

            # Show final summary
            if not self.quiet:
                self._display_summary()

        return True

    def stop(self):
        """Stop the debugger and disconnect."""
        self.running = False
        if self.sio.connected:
            self.sio.disconnect()
        self._log("success", "Debugger stopped")

    def _print_header(self):
        """Print the debugger header."""
        if RICH_AVAILABLE:
            console.print(
                Panel.fit(
                    "[bold cyan]SocketIO Event Monitor v1.0[/bold cyan]\n"
                    "[dim]Professional debugging tool for claude-mpm dashboard[/dim]",
                    border_style="blue",
                )
            )
        else:
            print("╭─────────────────────────────────────────╮")
            print("│     SocketIO Event Monitor v1.0         │")
            print("├─────────────────────────────────────────┤")
            print(f"│ Server: {self.url:<30} │")
            print(f"│ Mode: {self.mode.value:<34} │")
            print("╰─────────────────────────────────────────╯")


def main():
    """Main entry point for standalone execution."""
    parser = argparse.ArgumentParser(
        description="SocketIO debugging tool for claude-mpm dashboard development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor all events in real-time
  %(prog)s

  # Show event summary statistics
  %(prog)s --summary

  # Filter specific event types
  %(prog)s --filter PreToolUse PostToolUse

  # Save events to file for analysis
  %(prog)s --output events.jsonl

  # Connect to specific server
  %(prog)s --host localhost --port 8765

  # Quiet mode for scripts
  %(prog)s --quiet --output events.jsonl
        """,
    )

    # Connection options
    parser.add_argument(
        "--host", default="localhost", help="SocketIO server host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="SocketIO server port (default: 8765)"
    )

    # Display options
    parser.add_argument(
        "--mode",
        choices=["live", "summary", "filtered", "raw", "pretty"],
        default="live",
        help="Display mode (default: live)",
    )
    parser.add_argument(
        "--filter", nargs="+", dest="filter_types", help="Filter specific event types"
    )
    parser.add_argument("--raw", action="store_true", help="Display raw JSON output")
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress output except errors"
    )

    # Output options
    parser.add_argument(
        "--output", type=Path, help="Save events to file (JSONL format)"
    )

    # Connection options
    parser.add_argument(
        "--max-reconnect",
        type=int,
        default=10,
        help="Maximum reconnection attempts (default: 10)",
    )
    parser.add_argument(
        "--reconnect-delay",
        type=float,
        default=1.0,
        help="Reconnection delay in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    # Create and run debugger
    debugger = SocketIODebugger(
        host=args.host,
        port=args.port,
        mode=DisplayMode(args.mode),
        filter_types=args.filter_types,
        output_file=args.output,
        quiet=args.quiet,
        show_raw=args.raw,
        max_reconnect_attempts=args.max_reconnect,
        reconnect_delay=args.reconnect_delay,
    )

    success = debugger.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
