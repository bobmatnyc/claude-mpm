from pathlib import Path

"""Event Aggregator Service for Claude MPM.

WHY: This service connects to the Socket.IO dashboard server as a client and
captures all events emitted during Claude MPM sessions. It builds complete
session representations that can be saved as JSON documents for analysis.

DESIGN DECISION: We run as a Socket.IO client rather than modifying the server
to avoid interfering with the existing dashboard functionality. This allows the
aggregator to run alongside the dashboard without any conflicts.
"""

import asyncio
import json
import signal
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

import contextlib

from ..core.logger import get_logger
from ..models.agent_session import AgentSession


class EventAggregator:
    """Aggregates Socket.IO events into complete agent sessions.

    WHY: The dashboard emits events in real-time but doesn't persist complete
    sessions. This service captures those events and builds structured session
    documents for analysis and debugging.

    DESIGN DECISION: We maintain active sessions in memory and save them when
    they complete or after a timeout. This balances memory usage with the need
    to capture all events even if a session doesn't complete cleanly.
    """

    def __init__(
        self, host: str = "localhost", port: int = 8765, save_dir: Optional[str] = None
    ):
        """Initialize the event aggregator.

        Args:
            host: Socket.IO server host
            port: Socket.IO server port
            save_dir: Directory to save session files (defaults to .claude-mpm/sessions/)
        """
        self.host = host
        self.port = port
        self.logger = get_logger("event_aggregator")

        # Load configuration using ConfigLoader
        from claude_mpm.core.shared.config_loader import ConfigLoader

        config_loader = ConfigLoader()
        self.config = config_loader.load_main_config()

        # Session storage
        self.active_sessions: Dict[str, AgentSession] = {}
        self.session_timeout = (
            self.config.get("event_aggregator.session_timeout_minutes", 60) * 60
        )
        self.last_activity: Dict[str, float] = {}

        # Save directory - use config or provided dir or default to .claude-mpm/activity
        if save_dir is None:
            activity_dir = self.config.get(
                "event_aggregator.activity_directory", ".claude-mpm/activity"
            )
            self.save_dir = (
                Path.cwd() / activity_dir
                if not Path(activity_dir).is_absolute()
                else Path(activity_dir)
            )
        else:
            self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Socket.IO client
        self.sio_client = None
        self.connected = False
        self.running = False
        self.client_thread = None
        self.client_loop = None

        # Event statistics
        self.total_events_captured = 0
        self.events_by_type = defaultdict(int)
        self.sessions_completed = 0

        # Cleanup task
        self.cleanup_task = None

        self.logger.info(
            f"Event Aggregator initialized - will connect to {host}:{port}"
        )
        self.logger.info(f"Sessions will be saved to: {self.save_dir}")

    def start(self) -> bool:
        """Start the aggregator service.

        Returns:
            True if started successfully, False otherwise
        """
        if not SOCKETIO_AVAILABLE:
            self.logger.error(
                "Socket.IO client not available. Install python-socketio package."
            )
            return False

        if self.running:
            self.logger.warning("Aggregator already running")
            return True

        self.running = True

        # Start the Socket.IO client in a background thread
        self.client_thread = threading.Thread(target=self._run_client, daemon=True)
        self.client_thread.start()

        # Wait a moment for connection
        time.sleep(1)

        if self.connected:
            self.logger.info("Event Aggregator started successfully")
            return True
        self.logger.error("Failed to connect to Socket.IO server")
        self.running = False
        return False

    def stop(self):
        """Stop the aggregator service."""
        self.logger.info("Stopping Event Aggregator...")
        self.running = False

        # Save all active sessions
        self._save_all_sessions()

        # Disconnect Socket.IO client
        if self.sio_client and self.connected:
            with contextlib.suppress(Exception):
                asyncio.run_coroutine_threadsafe(
                    self.sio_client.disconnect(), self.client_loop
                ).result(timeout=2)

        # Stop the client thread
        if self.client_thread and self.client_thread.is_alive():
            self.client_thread.join(timeout=3)

        self.logger.info(
            f"Event Aggregator stopped - captured {self.total_events_captured} events"
        )
        self.logger.info(f"Completed sessions: {self.sessions_completed}")

    def _run_client(self):
        """Run the Socket.IO client in a background thread."""
        self.client_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.client_loop)

        try:
            self.client_loop.run_until_complete(self._connect_and_listen())
        except Exception as e:
            self.logger.error(f"Client thread error: {e}")
        finally:
            self.client_loop.close()

    async def _connect_and_listen(self):
        """Connect to Socket.IO server and listen for events."""
        try:
            self.sio_client = socketio.AsyncClient(
                reconnection=True,
                reconnection_attempts=0,  # Infinite retries
                reconnection_delay=1,
                reconnection_delay_max=5,
            )

            # Register event handlers
            self._register_handlers()

            # Connect to server
            url = f"http://{self.host}:{self.port}"
            self.logger.info(f"Connecting to Socket.IO server at {url}")
            await self.sio_client.connect(url)

            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

            # Keep running until stopped
            while self.running:
                await asyncio.sleep(0.5)

            # Cancel cleanup task
            if self.cleanup_task:
                self.cleanup_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.cleanup_task

        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.connected = False

    def _register_handlers(self):
        """Register Socket.IO event handlers."""

        @self.sio_client.event
        async def connect():
            """Handle connection to server."""
            self.connected = True
            self.logger.info("Connected to Socket.IO server")

            # Request event history to catch up on any missed events
            await self.sio_client.emit("get_history", {"limit": 100})

        @self.sio_client.event
        async def disconnect():
            """Handle disconnection from server."""
            self.connected = False
            self.logger.warning("Disconnected from Socket.IO server")

        @self.sio_client.event
        async def claude_event(data):
            """Handle Claude events from the server.

            WHY: This is the main event handler that captures all events
            emitted by the dashboard and processes them into sessions.
            """
            try:
                await self._process_event(data)
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")

        @self.sio_client.event
        async def history(data):
            """Handle historical events from the server.

            WHY: When we connect, we request recent history to ensure we
            don't miss events from sessions that started before we connected.
            """
            try:
                events = data.get("events", [])
                self.logger.info(f"Received {len(events)} historical events")

                for event in events:
                    await self._process_event(event)

            except Exception as e:
                self.logger.error(f"Error processing history: {e}")

    async def _process_event(self, event_data: Dict[str, Any]):
        """Process a single event and add it to the appropriate session.

        WHY: Each event needs to be routed to the correct session and
        processed according to its type.
        """
        try:
            # Extract event metadata
            event_type = event_data.get("type", "unknown")
            timestamp = event_data.get("timestamp", datetime.utcnow().isoformat() + "Z")
            data = event_data.get("data", {})

            # Update statistics
            self.total_events_captured += 1
            self.events_by_type[event_type] += 1

            # Determine session ID
            session_id = self._extract_session_id(event_type, data)

            if not session_id:
                # Some events don't belong to a specific session
                self.logger.debug(f"Event {event_type} has no session ID, skipping")
                return

            # Get or create session
            session = self._get_or_create_session(
                session_id, event_type, data, timestamp
            )

            # Add event to session
            session.add_event(event_type, data, timestamp)

            # Update last activity time
            self.last_activity[session_id] = time.time()

            # Check if session ended
            if event_type in ["session.end", "Stop"]:
                await self._finalize_session(session_id)

            # Log progress periodically
            if self.total_events_captured % 100 == 0:
                self.logger.info(
                    f"Processed {self.total_events_captured} events, "
                    f"active sessions: {len(self.active_sessions)}"
                )

        except Exception as e:
            self.logger.error(
                f"Error processing event {event_data.get('type', 'unknown')}: {e}"
            )

    def _extract_session_id(
        self, event_type: str, data: Dict[str, Any]
    ) -> Optional[str]:
        """Extract session ID from event data.

        WHY: Events use different field names for session ID depending on
        their source and type.
        """
        # Try common session ID fields
        session_id = (
            data.get("session_id")
            or data.get("sessionId")
            or data.get("session")
            or data.get("sid")
        )

        # For session.start events, the session_id is the key piece of data
        if event_type == "session.start" and "session_id" in data:
            return data["session_id"]

        # For hook events, check nested data
        if not session_id and isinstance(data, dict):
            for key in ["hook_data", "event_data", "context"]:
                if key in data and isinstance(data[key], dict):
                    nested_id = data[key].get("session_id") or data[key].get(
                        "sessionId"
                    )
                    if nested_id:
                        return nested_id

        return session_id

    def _get_or_create_session(
        self, session_id: str, event_type: str, data: Dict[str, Any], timestamp: str
    ) -> AgentSession:
        """Get existing session or create a new one.

        WHY: Sessions are created on demand when we see the first event
        for a new session ID.
        """
        if session_id not in self.active_sessions:
            # Create new session
            session = AgentSession(session_id=session_id, start_time=timestamp)

            # Extract initial metadata if this is a session.start event
            if event_type == "session.start":
                session.working_directory = data.get("working_directory", "")
                session.launch_method = data.get("launch_method", "")
                session.claude_pid = data.get("pid")

                # Try to get git branch and project info
                instance_info = data.get("instance_info", {})
                session.git_branch = instance_info.get("git_branch")
                session.project_root = instance_info.get("working_dir")

            self.active_sessions[session_id] = session
            self.last_activity[session_id] = time.time()

            self.logger.info(f"Created new session: {session_id[:8]}...")

        return self.active_sessions[session_id]

    async def _finalize_session(self, session_id: str):
        """Finalize and save a completed session.

        WHY: When a session ends, we need to calculate final metrics
        and persist it to disk.
        """
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]

        # Finalize the session
        session.finalize()

        # Save to file
        try:
            filepath = session.save_to_file(self.save_dir)
            self.logger.info(f"Saved session {session_id[:8]}... to {filepath}")
            self.logger.info(f"  - Events: {session.metrics.total_events}")
            self.logger.info(f"  - Delegations: {session.metrics.total_delegations}")
            self.logger.info(f"  - Tools used: {len(session.metrics.tools_used)}")
            self.logger.info(
                f"  - Files modified: {len(session.metrics.files_modified)}"
            )

            self.sessions_completed += 1
        except Exception as e:
            self.logger.error(f"Failed to save session {session_id}: {e}")

        # Remove from active sessions
        del self.active_sessions[session_id]
        if session_id in self.last_activity:
            del self.last_activity[session_id]

    async def _periodic_cleanup(self):
        """Periodically clean up inactive sessions.

        WHY: Some sessions may not complete cleanly, so we need to
        periodically save and remove inactive sessions to prevent
        memory leaks.
        """
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                current_time = time.time()
                sessions_to_finalize = []

                for session_id, last_time in list(self.last_activity.items()):
                    if current_time - last_time > self.session_timeout:
                        sessions_to_finalize.append(session_id)

                for session_id in sessions_to_finalize:
                    self.logger.info(
                        f"Finalizing inactive session: {session_id[:8]}..."
                    )
                    await self._finalize_session(session_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")

    def _save_all_sessions(self):
        """Save all active sessions to disk.

        WHY: Called on shutdown to ensure we don't lose any data.
        """
        for session_id in list(self.active_sessions.keys()):
            try:
                session = self.active_sessions[session_id]
                session.finalize()
                filepath = session.save_to_file(self.save_dir)
                self.logger.info(
                    f"Saved active session {session_id[:8]}... to {filepath}"
                )
            except Exception as e:
                self.logger.error(f"Failed to save session {session_id}: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the aggregator.

        Returns:
            Status dictionary with metrics and state
        """
        return {
            "running": self.running,
            "connected": self.connected,
            "server": f"{self.host}:{self.port}",
            "save_directory": str(self.save_dir),
            "active_sessions": len(self.active_sessions),
            "sessions_completed": self.sessions_completed,
            "total_events": self.total_events_captured,
            "events_by_type": dict(self.events_by_type),
            "active_session_ids": [sid[:8] + "..." for sid in self.active_sessions],
        }

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List captured sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        sessions = []

        # Get saved session files
        session_files = sorted(
            self.save_dir.glob("session_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]

        for filepath in session_files:
            try:
                # Load just the metadata, not the full session
                with open(filepath) as f:
                    data = json.load(f)

                sessions.append(
                    {
                        "file": filepath.name,
                        "session_id": data.get("session_id", "unknown")[:8] + "...",
                        "start_time": data.get("start_time", "unknown"),
                        "end_time": data.get("end_time", "unknown"),
                        "events": data.get("metrics", {}).get("total_events", 0),
                        "delegations": data.get("metrics", {}).get(
                            "total_delegations", 0
                        ),
                        "initial_prompt": (
                            (data.get("initial_prompt", "")[:50] + "...")
                            if data.get("initial_prompt")
                            else "N/A"
                        ),
                    }
                )
            except Exception as e:
                self.logger.error(f"Error reading session file {filepath}: {e}")

        return sessions

    def load_session(self, session_id_prefix: str) -> Optional[AgentSession]:
        """Load a session by ID prefix.

        Args:
            session_id_prefix: First few characters of session ID

        Returns:
            AgentSession if found, None otherwise
        """
        # Search for matching session file
        for filepath in self.save_dir.glob("session_*.json"):
            if session_id_prefix in filepath.name:
                try:
                    return AgentSession.load_from_file(str(filepath))
                except Exception as e:
                    self.logger.error(f"Error loading session from {filepath}: {e}")

        return None


# Global aggregator instance
_aggregator: Optional[EventAggregator] = None


def get_aggregator() -> EventAggregator:
    """Get or create the global aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = EventAggregator()
    return _aggregator


def start_aggregator() -> bool:
    """Start the global aggregator service."""
    aggregator = get_aggregator()
    return aggregator.start()


def stop_aggregator():
    """Stop the global aggregator service."""
    global _aggregator
    if _aggregator:
        _aggregator.stop()
        _aggregator = None


def aggregator_status() -> Dict[str, Any]:
    """Get status of the aggregator service."""
    aggregator = get_aggregator()
    return aggregator.get_status()


# Signal handlers for graceful shutdown
def _signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = get_logger("event_aggregator")
    logger.info(f"Received signal {signum}, shutting down...")
    stop_aggregator()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)
