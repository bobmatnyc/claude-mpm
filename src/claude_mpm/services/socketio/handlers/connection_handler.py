"""
Enhanced Connection Event Handler for Socket.IO.

WHY: This module provides robust connection handling with state tracking,
event replay on reconnection, and health monitoring integration.

DESIGN DECISION: Centralized connection event handling ensures consistent
state management and provides resilient event delivery across reconnections.
"""

from datetime import datetime, timezone

from .base import BaseEventHandler


class EnhancedConnectionEventHandler(BaseEventHandler):
    """
    Handles Socket.IO connection events with enhanced robustness.

    Features:
    - Persistent client tracking across reconnections
    - Event replay on reconnection
    - Connection health monitoring
    - Acknowledgment system for guaranteed delivery
    """

    def register_events(self):
        """Register enhanced connection event handlers."""
        sio = self.server.core.sio

        @sio.event
        async def connect(sid, environ, auth):
            """Handle client connection with enhanced tracking."""
            try:
                # Extract client ID from auth or create new
                client_id = None
                if auth and isinstance(auth, dict):
                    client_id = auth.get("client_id")

                # Register connection with manager
                if self.server.connection_manager:
                    conn = await self.server.connection_manager.register_connection(
                        sid, client_id
                    )

                    # Add to server's connected clients
                    self.server.connected_clients.add(sid)
                    self.server.stats["connections_total"] += 1

                    # Store client info
                    self.server.client_info[sid] = {
                        "client_id": conn.client_id,
                        "connected_at": datetime.now(timezone.utc).isoformat(),
                        "user_agent": environ.get("HTTP_USER_AGENT", "unknown"),
                        "remote_addr": environ.get("REMOTE_ADDR", "unknown"),
                    }

                    # Send client ID back for future reconnections
                    await sio.emit(
                        "connection_established",
                        {
                            "client_id": conn.client_id,
                            "sid": sid,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "server_version": self.get_server_version(),
                        },
                        room=sid,
                    )

                    # Send current server status
                    await self._send_server_status(sid)

                    # Check for events to replay
                    last_sequence = 0
                    if auth and isinstance(auth, dict):
                        last_sequence = auth.get("last_sequence", 0)

                    if last_sequence > 0:
                        replay_events = (
                            await self.server.connection_manager.get_replay_events(
                                sid, last_sequence
                            )
                        )

                        if replay_events:
                            self.logger.info(
                                f"Replaying {len(replay_events)} events for client {conn.client_id}"
                            )

                            # Send replay events in batch
                            await sio.emit(
                                "event_replay",
                                {
                                    "events": replay_events,
                                    "count": len(replay_events),
                                    "from_sequence": last_sequence,
                                },
                                room=sid,
                            )

                    # Send event history for initial population
                    if (
                        hasattr(self.server, "event_history")
                        and self.server.event_history
                    ):
                        history_data = list(self.server.event_history)
                        await sio.emit(
                            "event_history",
                            {"events": history_data, "count": len(history_data)},
                            room=sid,
                        )

                    self.logger.info(
                        f"Client connected: {conn.client_id} (sid: {sid}, "
                        f"reconnect: {conn.metrics.reconnect_count > 0})"
                    )
                else:
                    # Fallback to basic connection tracking
                    self.server.connected_clients.add(sid)
                    self.server.stats["connections_total"] += 1

                    self.server.client_info[sid] = {
                        "connected_at": datetime.now(timezone.utc).isoformat(),
                        "user_agent": environ.get("HTTP_USER_AGENT", "unknown"),
                        "remote_addr": environ.get("REMOTE_ADDR", "unknown"),
                    }

                    await self._send_server_status(sid)

                    if (
                        hasattr(self.server, "event_history")
                        and self.server.event_history
                    ):
                        history_data = list(self.server.event_history)
                        await sio.emit(
                            "event_history",
                            {"events": history_data, "count": len(history_data)},
                            room=sid,
                        )

                    self.logger.info(f"Client connected: {sid}")

            except Exception as e:
                self.logger.error(f"Error handling connection for {sid}: {e}")

        @sio.event
        async def disconnect(sid):
            """Handle client disconnection with state preservation."""
            try:
                # Get disconnection reason if available
                reason = "client_disconnect"

                # Unregister from connection manager but preserve state
                if self.server.connection_manager:
                    await self.server.connection_manager.unregister_connection(
                        sid, reason
                    )

                # Remove from connected clients
                if sid in self.server.connected_clients:
                    self.server.connected_clients.remove(sid)

                # Remove client info
                if sid in self.server.client_info:
                    client_info = self.server.client_info[sid]
                    del self.server.client_info[sid]

                    client_id = client_info.get("client_id", sid)
                    self.logger.info(f"Client disconnected: {client_id} (sid: {sid})")
                else:
                    self.logger.info(f"Client disconnected: {sid}")

            except Exception as e:
                self.logger.error(f"Error handling disconnection for {sid}: {e}")

        @sio.event
        async def ping(sid):
            """Handle ping from client for health monitoring."""
            try:
                # Update activity in connection manager - CRITICAL for preventing stale connections
                if self.server.connection_manager:
                    await self.server.connection_manager.update_activity(sid, "ping")

                # Send pong response with timestamp
                await sio.emit(
                    "pong",
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "server_time": datetime.now(timezone.utc).timestamp(),
                    },
                    room=sid,
                )

            except Exception as e:
                self.logger.error(f"Error handling ping from {sid}: {e}")

        @sio.event
        async def acknowledge_event(sid, data):
            """Handle event acknowledgment from client."""
            try:
                if not isinstance(data, dict):
                    return

                sequence = data.get("sequence")
                if sequence and self.server.connection_manager:
                    await self.server.connection_manager.acknowledge_event(
                        sid, sequence
                    )

                    # Optional: Send confirmation
                    await sio.emit(
                        "ack_confirmed",
                        {
                            "sequence": sequence,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        room=sid,
                    )

            except Exception as e:
                self.logger.error(f"Error handling acknowledgment from {sid}: {e}")

        @sio.event
        async def request_replay(sid, data):
            """Handle replay request from client after reconnection."""
            try:
                if not isinstance(data, dict):
                    return

                last_sequence = data.get("last_sequence", 0)

                if self.server.connection_manager:
                    replay_events = (
                        await self.server.connection_manager.get_replay_events(
                            sid, last_sequence
                        )
                    )

                    if replay_events:
                        await sio.emit(
                            "event_replay",
                            {
                                "events": replay_events,
                                "count": len(replay_events),
                                "from_sequence": last_sequence,
                            },
                            room=sid,
                        )
                    else:
                        await sio.emit(
                            "event_replay",
                            {
                                "events": [],
                                "count": 0,
                                "from_sequence": last_sequence,
                                "message": "No events to replay",
                            },
                            room=sid,
                        )

            except Exception as e:
                self.logger.error(f"Error handling replay request from {sid}: {e}")

        @sio.event
        async def get_connection_stats(sid):
            """Get connection statistics for debugging."""
            try:
                stats = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_connections": len(self.server.connected_clients),
                    "server_stats": self.server.stats,
                }

                if self.server.connection_manager:
                    conn = self.server.connection_manager.get_connection(sid)
                    if conn:
                        stats["connection"] = {
                            "client_id": conn.client_id,
                            "state": conn.state.value,
                            "connected_at": conn.connected_at,
                            "quality": conn.calculate_quality(),
                            "metrics": {
                                "events_sent": conn.metrics.events_sent,
                                "events_acked": conn.metrics.events_acked,
                                "events_buffered": conn.metrics.events_buffered,
                                "reconnect_count": conn.metrics.reconnect_count,
                            },
                        }

                    stats["manager_metrics"] = (
                        self.server.connection_manager.get_metrics()
                    )

                await sio.emit("connection_stats", stats, room=sid)

            except Exception as e:
                self.logger.error(f"Error getting connection stats for {sid}: {e}")

        # Heartbeat handler removed - Using Socket.IO's built-in ping/pong instead
        # This prevents conflicting heartbeat systems that can cause disconnections

        self.logger.info("Enhanced connection event handlers registered")

    async def _send_server_status(self, sid: str):
        """Send current server status to a client."""
        try:
            status_data = {
                "server_running": self.server.running,
                "claude_status": self.server.claude_status,
                "claude_pid": self.server.claude_pid,
                "session_id": self.server.session_id,
                "connected_clients": len(self.server.connected_clients),
                "server_start_time": (
                    self.server.stats.get("start_time").isoformat()
                    if self.server.stats.get("start_time")
                    else None
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await self.server.core.sio.emit("server_status", status_data, room=sid)

        except Exception as e:
            self.logger.error(f"Error sending server status to {sid}: {e}")

    def get_server_version(self) -> str:
        """Get server version for client info."""
        try:
            from claude_mpm.services.version_service import VersionService

            return VersionService().get_version()
        except Exception:
            return "unknown"
