"""
Enhanced Connection Manager for SocketIO Server.

WHY: This module provides robust connection management with state tracking,
health monitoring, event buffering for disconnected clients, and automatic
recovery from connection failures.

DESIGN DECISION: Centralized connection management ensures consistent handling
of client states, proper event delivery, and automatic recovery mechanisms.
"""

import asyncio
import contextlib
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Deque, Dict, List, Optional
from uuid import uuid4

from ....core.logging_config import get_logger


class ConnectionState(Enum):
    """Connection states for tracking client lifecycle."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    STALE = "stale"  # Connected but not responding


@dataclass
class ConnectionMetrics:
    """Metrics for a single connection."""

    connect_count: int = 0
    disconnect_count: int = 0
    reconnect_count: int = 0
    events_sent: int = 0
    events_acked: int = 0
    events_buffered: int = 0
    events_dropped: int = 0
    last_activity: float = field(default_factory=time.time)
    total_uptime: float = 0.0
    total_downtime: float = 0.0
    connection_quality: float = 1.0  # 0-1 quality score


@dataclass
class ClientConnection:
    """Represents a client connection with full state tracking."""

    sid: str  # Socket ID
    client_id: str  # Persistent client ID across reconnections
    state: ConnectionState
    connected_at: float
    disconnected_at: Optional[float] = None
    last_ping: Optional[float] = None
    last_pong: Optional[float] = None
    last_event: Optional[float] = None
    event_buffer: Deque[Dict[str, Any]] = field(
        default_factory=lambda: deque(maxlen=1000)
    )
    event_sequence: int = 0
    last_acked_sequence: int = 0
    pending_acks: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    metrics: ConnectionMetrics = field(default_factory=ConnectionMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_healthy(self, timeout: float = 90.0) -> bool:
        """Check if connection is healthy based on activity.

        Args:
            timeout: Seconds before considering connection unhealthy (default 90s)
        """
        if self.state != ConnectionState.CONNECTED:
            return False

        now = time.time()

        # Check last activity (ping, pong, or event)
        # Include metrics.last_activity for more comprehensive tracking
        last_activity = max(
            self.last_ping or 0,
            self.last_pong or 0,
            self.last_event or 0,
            self.metrics.last_activity or 0,
            self.connected_at,
        )

        # More aggressive timeout for stale detection (no grace period)
        # This helps identify truly stale connections faster
        return (now - last_activity) < timeout

    def calculate_quality(self) -> float:
        """Calculate connection quality score (0-1)."""
        if self.state != ConnectionState.CONNECTED:
            return 0.0

        # Factors for quality calculation
        factors = []

        # Reconnection rate (lower is better)
        if self.metrics.connect_count > 0:
            reconnect_rate = self.metrics.reconnect_count / self.metrics.connect_count
            factors.append(1.0 - min(reconnect_rate, 1.0))

        # Event acknowledgment rate
        if self.metrics.events_sent > 0:
            ack_rate = self.metrics.events_acked / self.metrics.events_sent
            factors.append(ack_rate)

        # Uptime ratio
        total_time = self.metrics.total_uptime + self.metrics.total_downtime
        if total_time > 0:
            uptime_ratio = self.metrics.total_uptime / total_time
            factors.append(uptime_ratio)

        # Recent activity (exponential decay over 5 minutes)
        now = time.time()
        time_since_activity = now - self.metrics.last_activity
        activity_score = max(0, 1.0 - (time_since_activity / 300))
        factors.append(activity_score)

        # Calculate average quality
        if factors:
            quality = sum(factors) / len(factors)
        else:
            quality = 1.0 if self.state == ConnectionState.CONNECTED else 0.0

        self.metrics.connection_quality = quality
        return quality


class ConnectionManager:
    """
    Enhanced connection manager with robust state tracking and recovery.

    Features:
    - Persistent client IDs across reconnections
    - Event buffering for disconnected clients
    - Sequence numbers for event ordering
    - Health monitoring with automatic stale detection
    - Connection quality metrics
    - Automatic event replay on reconnection
    """

    def __init__(
        self, max_buffer_size: Optional[int] = None, event_ttl: Optional[int] = None
    ):
        """
        Initialize connection manager with centralized configuration.

        Args:
            max_buffer_size: Maximum events to buffer per client (uses config if None)
            event_ttl: Time-to-live for buffered events in seconds (uses config if None)
        """
        from ....config.socketio_config import CONNECTION_CONFIG

        self.logger = get_logger(__name__)
        self.connections: Dict[str, ClientConnection] = {}
        self.client_mapping: Dict[str, str] = {}  # client_id -> current sid

        # Use centralized configuration with optional overrides
        self.max_buffer_size = max_buffer_size or CONNECTION_CONFIG["max_events_buffer"]
        self.event_ttl = event_ttl or CONNECTION_CONFIG["event_ttl"]
        self.global_sequence = 0
        self.health_check_interval = CONNECTION_CONFIG[
            "health_check_interval"
        ]  # 30 seconds
        self.stale_timeout = CONNECTION_CONFIG["stale_timeout"]  # 180 seconds (was 90)
        self.health_task = None
        self._lock = asyncio.Lock()

    async def register_connection(
        self, sid: str, client_id: Optional[str] = None
    ) -> ClientConnection:
        """
        Register a new connection or reconnection with retry logic.

        Args:
            sid: Socket ID
            client_id: Optional persistent client ID for reconnection

        Returns:
            ClientConnection object
        """
        max_retries = 3
        retry_delay = 0.1  # Start with 100ms

        for attempt in range(max_retries):
            try:
                async with self._lock:
                    now = time.time()

                    # Check if this is a reconnection
                    if client_id and client_id in self.client_mapping:
                        old_sid = self.client_mapping[client_id]
                        if old_sid in self.connections:
                            old_conn = self.connections[old_sid]

                            # Create new connection with history
                            conn = ClientConnection(
                                sid=sid,
                                client_id=client_id,
                                state=ConnectionState.CONNECTED,
                                connected_at=now,
                                event_buffer=old_conn.event_buffer,
                                event_sequence=old_conn.event_sequence,
                                last_acked_sequence=old_conn.last_acked_sequence,
                                metrics=old_conn.metrics,
                            )

                            # Update metrics
                            conn.metrics.reconnect_count += 1
                            conn.metrics.connect_count += 1
                            if old_conn.disconnected_at:
                                conn.metrics.total_downtime += (
                                    now - old_conn.disconnected_at
                                )

                            # Clean up old connection
                            del self.connections[old_sid]

                            self.logger.info(
                                f"Client {client_id} reconnected (new sid: {sid}, "
                                f"buffered events: {len(conn.event_buffer)})"
                            )
                        else:
                            # No old connection found, create new
                            client_id = client_id or str(uuid4())
                            conn = self._create_new_connection(sid, client_id, now)
                    else:
                        # New client
                        client_id = client_id or str(uuid4())
                        conn = self._create_new_connection(sid, client_id, now)

                    # Register connection with validation
                    if conn and conn.state == ConnectionState.CONNECTED:
                        self.connections[sid] = conn
                        self.client_mapping[client_id] = sid
                        return conn
                    raise ValueError(f"Invalid connection state for {sid}")

            except Exception as e:
                self.logger.warning(
                    f"Failed to register connection {sid} (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Final attempt failed, create minimal connection
                    self.logger.error(
                        f"All attempts failed for {sid}, creating minimal connection"
                    )
                    conn = ClientConnection(
                        sid=sid,
                        client_id=client_id or str(uuid4()),
                        state=ConnectionState.CONNECTED,
                        connected_at=time.time(),
                    )
                    self.connections[sid] = conn
                    return conn
        return None

    def _create_new_connection(
        self, sid: str, client_id: str, now: float
    ) -> ClientConnection:
        """Create a new connection object."""
        conn = ClientConnection(
            sid=sid,
            client_id=client_id,
            state=ConnectionState.CONNECTED,
            connected_at=now,
        )
        conn.metrics.connect_count = 1
        self.logger.info(f"New client connected: {client_id} (sid: {sid})")
        return conn

    async def unregister_connection(self, sid: str, reason: str = "unknown") -> None:
        """
        Unregister a connection but keep state for reconnection.

        Args:
            sid: Socket ID
            reason: Disconnection reason
        """
        async with self._lock:
            if sid not in self.connections:
                return

            conn = self.connections[sid]
            now = time.time()

            # Update connection state
            conn.state = ConnectionState.DISCONNECTED
            conn.disconnected_at = now
            conn.metrics.disconnect_count += 1

            # Update uptime
            if conn.connected_at:
                conn.metrics.total_uptime += now - conn.connected_at

            self.logger.info(
                f"Client {conn.client_id} disconnected (sid: {sid}, reason: {reason}, "
                f"buffered events: {len(conn.event_buffer)})"
            )

            # Keep connection for potential reconnection
            # It will be cleaned up by health check if not reconnected

    async def buffer_event(self, sid: str, event: Dict[str, Any]) -> bool:
        """
        Buffer an event for a client.

        Args:
            sid: Socket ID
            event: Event to buffer

        Returns:
            True if buffered successfully
        """
        async with self._lock:
            if sid not in self.connections:
                return False

            conn = self.connections[sid]

            # Add sequence number
            self.global_sequence += 1
            event["sequence"] = self.global_sequence
            event["timestamp"] = time.time()

            # Buffer the event
            conn.event_buffer.append(event)
            conn.event_sequence = self.global_sequence
            conn.metrics.events_buffered += 1

            # Drop old events if buffer is full
            if len(conn.event_buffer) >= self.max_buffer_size:
                conn.metrics.events_dropped += 1

            return True

    async def get_replay_events(
        self, sid: str, last_sequence: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get events to replay for a client after reconnection.

        Args:
            sid: Socket ID
            last_sequence: Last sequence number received by client

        Returns:
            List of events to replay
        """
        async with self._lock:
            if sid not in self.connections:
                return []

            conn = self.connections[sid]
            now = time.time()

            # Filter events by sequence and TTL
            replay_events = []
            for event in conn.event_buffer:
                if event.get("sequence", 0) > last_sequence:
                    # Check TTL
                    event_age = now - event.get("timestamp", 0)
                    if event_age < self.event_ttl:
                        replay_events.append(event)

            self.logger.info(
                f"Replaying {len(replay_events)} events for {conn.client_id} "
                f"(from sequence {last_sequence})"
            )

            return replay_events

    async def acknowledge_event(self, sid: str, sequence: int) -> None:
        """
        Acknowledge receipt of an event by a client.

        Args:
            sid: Socket ID
            sequence: Sequence number of acknowledged event
        """
        async with self._lock:
            if sid not in self.connections:
                return

            conn = self.connections[sid]
            conn.last_acked_sequence = max(conn.last_acked_sequence, sequence)
            conn.metrics.events_acked += 1

            # Remove from pending acks
            if sequence in conn.pending_acks:
                del conn.pending_acks[sequence]

    async def update_activity(self, sid: str, activity_type: str = "event") -> None:
        """
        Update last activity time for a connection.

        Args:
            sid: Socket ID
            activity_type: Type of activity (event, ping, pong)
        """
        if sid not in self.connections:
            return

        conn = self.connections[sid]
        now = time.time()

        if activity_type == "ping":
            conn.last_ping = now
        elif activity_type == "pong":
            conn.last_pong = now
        else:
            conn.last_event = now

        conn.metrics.last_activity = now

    async def start_health_monitoring(self) -> None:
        """Start the health monitoring task."""
        if self.health_task:
            return

        self.health_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Started connection health monitoring")

    async def stop_health_monitoring(self) -> None:
        """Stop the health monitoring task."""
        if self.health_task:
            self.health_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.health_task
            self.health_task = None
            self.logger.info("Stopped connection health monitoring")

    async def _health_check_loop(self) -> None:
        """Periodic health check for all connections."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self.check_connection_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")

    async def check_connection_health(self) -> Dict[str, Any]:
        """
        Check health of all connections and clean up stale ones.

        Returns:
            Health status report
        """
        async with self._lock:
            now = time.time()
            report = {
                "timestamp": datetime.now().isoformat(),
                "total_connections": len(self.connections),
                "healthy": 0,
                "stale": 0,
                "disconnected": 0,
                "cleaned": 0,
                "quality_scores": {},
            }

            to_clean = []

            for sid, conn in self.connections.items():
                # Calculate quality
                quality = conn.calculate_quality()
                report["quality_scores"][conn.client_id] = quality

                if conn.state == ConnectionState.CONNECTED:
                    if conn.is_healthy(self.stale_timeout):
                        report["healthy"] += 1
                    else:
                        # Mark as stale only if really stale (no grace period activity)
                        last_activity = max(
                            conn.last_ping or 0,
                            conn.last_pong or 0,
                            conn.last_event or 0,
                            conn.metrics.last_activity or 0,
                            conn.connected_at,
                        )
                        time_since_activity = now - last_activity

                        # Only mark as stale if significantly over timeout (2x)
                        if time_since_activity > (self.stale_timeout * 2):
                            conn.state = ConnectionState.STALE
                            report["stale"] += 1
                            self.logger.warning(
                                f"Connection {conn.client_id} marked as stale "
                                f"(last activity: {time_since_activity:.1f}s ago)"
                            )
                        else:
                            # Connection is borderline - keep it alive but log
                            report["healthy"] += 1
                            self.logger.debug(
                                f"Connection {conn.client_id} borderline "
                                f"(last activity: {time_since_activity:.1f}s ago)"
                            )

                elif conn.state == ConnectionState.DISCONNECTED:
                    report["disconnected"] += 1

                    # Clean up old disconnected connections (be conservative)
                    if conn.disconnected_at and (now - conn.disconnected_at) > (
                        self.event_ttl * 2
                    ):  # Double the TTL
                        to_clean.append(sid)

            # Clean up old connections
            for sid in to_clean:
                conn = self.connections[sid]
                del self.connections[sid]
                if conn.client_id in self.client_mapping:
                    del self.client_mapping[conn.client_id]
                report["cleaned"] += 1
                self.logger.info(f"Cleaned up old connection: {conn.client_id}")

            if report["stale"] > 0 or report["cleaned"] > 0:
                self.logger.info(
                    f"Health check: {report['healthy']} healthy, "
                    f"{report['stale']} stale, {report['disconnected']} disconnected, "
                    f"{report['cleaned']} cleaned"
                )

            return report

    def get_connection(self, sid: str) -> Optional[ClientConnection]:
        """Get connection by socket ID."""
        return self.connections.get(sid)

    def get_all_connections(self) -> Dict[str, ClientConnection]:
        """Get all connections."""
        return self.connections.copy()

    def get_metrics(self) -> Dict[str, Any]:
        """Get overall connection metrics."""
        total_events_sent = sum(
            c.metrics.events_sent for c in self.connections.values()
        )
        total_events_acked = sum(
            c.metrics.events_acked for c in self.connections.values()
        )
        total_events_buffered = sum(
            c.metrics.events_buffered for c in self.connections.values()
        )
        total_events_dropped = sum(
            c.metrics.events_dropped for c in self.connections.values()
        )
        avg_quality = sum(
            c.metrics.connection_quality for c in self.connections.values()
        ) / max(len(self.connections), 1)

        return {
            "total_connections": len(self.connections),
            "active_connections": sum(
                1
                for c in self.connections.values()
                if c.state == ConnectionState.CONNECTED
            ),
            "total_events_sent": total_events_sent,
            "total_events_acked": total_events_acked,
            "total_events_buffered": total_events_buffered,
            "total_events_dropped": total_events_dropped,
            "average_quality": avg_quality,
            "global_sequence": self.global_sequence,
        }
