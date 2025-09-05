"""
Claude Code Hooks Handler for Unified Monitor
=============================================

WHY: This handler ingests Claude Code hooks and events, providing integration
between Claude Code sessions and the unified monitor daemon. It processes
hook events and broadcasts them to dashboard clients.

DESIGN DECISIONS:
- Ingests Claude Code hooks via HTTP and WebSocket
- Processes and normalizes hook events
- Broadcasts events to connected dashboard clients
- Maintains event history and replay capability
"""

import asyncio
from collections import deque
from typing import Dict, List

import socketio

from ....core.logging_config import get_logger


class HookHandler:
    """Event handler for Claude Code hooks integration.

    WHY: Provides integration between Claude Code sessions and the unified
    monitor daemon, allowing real-time monitoring of Claude Code activities.
    """

    def __init__(self, sio: socketio.AsyncServer):
        """Initialize the hooks handler.

        Args:
            sio: Socket.IO server instance
        """
        self.sio = sio
        self.logger = get_logger(__name__)

        # Event storage
        self.event_history: deque = deque(maxlen=1000)  # Keep last 1000 events
        self.active_sessions: Dict[str, Dict] = {}

    def register(self):
        """Register Socket.IO event handlers."""
        try:
            # Claude Code hook events (HTTP POST pathway)
            self.sio.on("claude_event", self.handle_claude_event)

            # Hook ingestion events (alternative format)
            self.sio.on("hook:ingest", self.handle_hook_ingest)
            self.sio.on("hook:session:start", self.handle_session_start)
            self.sio.on("hook:session:end", self.handle_session_end)

            # Event replay and history
            self.sio.on("hook:history:get", self.handle_get_history)
            self.sio.on("hook:replay:start", self.handle_replay_start)

            # Session management
            self.sio.on("hook:sessions:list", self.handle_list_sessions)
            self.sio.on("hook:session:info", self.handle_session_info)

            self.logger.info("Hook event handlers registered")

        except Exception as e:
            self.logger.error(f"Error registering hook handlers: {e}")
            raise

    async def handle_claude_event(self, sid: str, data: Dict):
        """Handle Claude Code hook events sent via 'claude_event'.

        This is the primary integration point for Claude Code hooks.

        Args:
            sid: Socket.IO session ID
            data: Claude event data
        """
        try:
            self.logger.info(
                f"Received Claude Code hook event: {data.get('type', 'unknown')}"
            )

            # Process the Claude event
            processed_event = self._process_claude_event(data)

            # Store in history
            self.event_history.append(processed_event)

            # Update session tracking
            session_id = processed_event.get("session_id")
            if session_id:
                self._update_session_tracking(session_id, processed_event)

            # Broadcast to all dashboard clients
            # Emit both event names for compatibility
            await self.sio.emit("hook:event", processed_event)
            # Also emit as claude_event which is what the dashboard expects
            await self.sio.emit("claude_event", processed_event)

            self.logger.debug(
                f"Claude hook event processed and broadcasted: {processed_event.get('type', 'unknown')}"
            )

        except Exception as e:
            self.logger.error(f"Error processing Claude hook event: {e}")
            await self.sio.emit(
                "hook:error",
                {"error": f"Claude event processing error: {e!s}"},
                room=sid,
            )

    async def handle_hook_ingest(self, sid: str, data: Dict):
        """Handle incoming Claude Code hook event.

        Args:
            sid: Socket.IO session ID
            data: Hook event data
        """
        try:
            # Validate hook data
            if not self._validate_hook_data(data):
                await self.sio.emit(
                    "hook:error", {"error": "Invalid hook data format"}, room=sid
                )
                return

            # Process and normalize the hook event
            processed_event = self._process_hook_event(data)

            # Store in history
            self.event_history.append(processed_event)

            # Update session tracking
            session_id = processed_event.get("session_id")
            if session_id:
                self._update_session_tracking(session_id, processed_event)

            # Broadcast to all dashboard clients
            await self.sio.emit("hook:event", processed_event)
            # Also emit as claude_event for dashboard compatibility
            await self.sio.emit("claude_event", processed_event)

            self.logger.debug(
                f"Hook event processed: {processed_event.get('type', 'unknown')}"
            )

        except Exception as e:
            self.logger.error(f"Error processing hook event: {e}")
            await self.sio.emit(
                "hook:error", {"error": f"Hook processing error: {e!s}"}, room=sid
            )

    async def handle_session_start(self, sid: str, data: Dict):
        """Handle Claude Code session start.

        Args:
            sid: Socket.IO session ID
            data: Session start data
        """
        try:
            session_id = data.get("session_id")
            if not session_id:
                await self.sio.emit(
                    "hook:error", {"error": "No session ID provided"}, room=sid
                )
                return

            # Create session tracking
            session_info = {
                "session_id": session_id,
                "start_time": asyncio.get_event_loop().time(),
                "status": "active",
                "event_count": 0,
                "last_activity": asyncio.get_event_loop().time(),
                "metadata": data.get("metadata", {}),
            }

            self.active_sessions[session_id] = session_info

            # Broadcast session start
            await self.sio.emit("hook:session:started", session_info)
            # Also emit as claude_event for dashboard
            await self.sio.emit(
                "claude_event",
                {
                    "type": "session.started",
                    "session_id": session_id,
                    "data": session_info,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            )

            self.logger.info(f"Claude Code session started: {session_id}")

        except Exception as e:
            self.logger.error(f"Error handling session start: {e}")
            await self.sio.emit(
                "hook:error", {"error": f"Session start error: {e!s}"}, room=sid
            )

    async def handle_session_end(self, sid: str, data: Dict):
        """Handle Claude Code session end.

        Args:
            sid: Socket.IO session ID
            data: Session end data
        """
        try:
            session_id = data.get("session_id")
            if not session_id:
                await self.sio.emit(
                    "hook:error", {"error": "No session ID provided"}, room=sid
                )
                return

            # Update session status
            if session_id in self.active_sessions:
                session_info = self.active_sessions[session_id]
                session_info["status"] = "ended"
                session_info["end_time"] = asyncio.get_event_loop().time()
                session_info["duration"] = (
                    session_info["end_time"] - session_info["start_time"]
                )

                # Broadcast session end
                await self.sio.emit("hook:session:ended", session_info)
                # Also emit as claude_event for dashboard
                await self.sio.emit(
                    "claude_event",
                    {
                        "type": "session.ended",
                        "session_id": session_id,
                        "data": session_info,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                )

                # Remove from active sessions after a delay
                asyncio.create_task(
                    self._cleanup_session(session_id, delay=300)
                )  # 5 minutes

                self.logger.info(f"Claude Code session ended: {session_id}")
            else:
                self.logger.warning(f"Session end for unknown session: {session_id}")

        except Exception as e:
            self.logger.error(f"Error handling session end: {e}")
            await self.sio.emit(
                "hook:error", {"error": f"Session end error: {e!s}"}, room=sid
            )

    async def handle_get_history(self, sid: str, data: Dict):
        """Handle request for event history.

        Args:
            sid: Socket.IO session ID
            data: History request data
        """
        try:
            limit = data.get("limit", 100)
            event_type = data.get("type")
            session_id = data.get("session_id")

            # Filter events
            filtered_events = list(self.event_history)

            if event_type:
                filtered_events = [
                    e for e in filtered_events if e.get("type") == event_type
                ]

            if session_id:
                filtered_events = [
                    e for e in filtered_events if e.get("session_id") == session_id
                ]

            # Apply limit
            if limit > 0:
                filtered_events = filtered_events[-limit:]

            await self.sio.emit(
                "hook:history:response",
                {
                    "events": filtered_events,
                    "total": len(filtered_events),
                    "filters": {
                        "type": event_type,
                        "session_id": session_id,
                        "limit": limit,
                    },
                },
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error getting event history: {e}")
            await self.sio.emit(
                "hook:error", {"error": f"History error: {e!s}"}, room=sid
            )

    async def handle_replay_start(self, sid: str, data: Dict):
        """Handle event replay request.

        Args:
            sid: Socket.IO session ID
            data: Replay request data
        """
        try:
            session_id = data.get("session_id")
            speed = data.get("speed", 1.0)  # Replay speed multiplier

            if not session_id:
                await self.sio.emit(
                    "hook:error",
                    {"error": "No session ID provided for replay"},
                    room=sid,
                )
                return

            # Get events for session
            session_events = [
                e for e in self.event_history if e.get("session_id") == session_id
            ]

            if not session_events:
                await self.sio.emit(
                    "hook:error",
                    {"error": f"No events found for session: {session_id}"},
                    room=sid,
                )
                return

            # Start replay
            await self._replay_events(sid, session_events, speed)

        except Exception as e:
            self.logger.error(f"Error starting event replay: {e}")
            await self.sio.emit(
                "hook:error", {"error": f"Replay error: {e!s}"}, room=sid
            )

    async def handle_list_sessions(self, sid: str, data: Dict):
        """Handle request for active sessions list.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            sessions = list(self.active_sessions.values())

            await self.sio.emit(
                "hook:sessions:response",
                {"sessions": sessions, "total": len(sessions)},
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error listing sessions: {e}")
            await self.sio.emit(
                "hook:error", {"error": f"Sessions list error: {e!s}"}, room=sid
            )

    async def handle_session_info(self, sid: str, data: Dict):
        """Handle request for specific session info.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            session_id = data.get("session_id")
            if not session_id:
                await self.sio.emit(
                    "hook:error", {"error": "No session ID provided"}, room=sid
                )
                return

            session_info = self.active_sessions.get(session_id)
            if not session_info:
                await self.sio.emit(
                    "hook:error",
                    {"error": f"Session not found: {session_id}"},
                    room=sid,
                )
                return

            await self.sio.emit("hook:session:info:response", session_info, room=sid)

        except Exception as e:
            self.logger.error(f"Error getting session info: {e}")
            await self.sio.emit(
                "hook:error", {"error": f"Session info error: {e!s}"}, room=sid
            )

    def _validate_hook_data(self, data: Dict) -> bool:
        """Validate hook event data format.

        Args:
            data: Hook event data

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["type", "timestamp"]
        return all(field in data for field in required_fields)

    def _process_claude_event(self, data: Dict) -> Dict:
        """Process and normalize Claude Code hook event data.

        Args:
            data: Raw Claude event data

        Returns:
            Processed event data
        """
        processed = {
            "type": data.get("type", "hook"),
            "subtype": data.get("subtype", "unknown"),
            "timestamp": data.get("timestamp", asyncio.get_event_loop().time()),
            "session_id": data.get("session_id"),
            "source": data.get("source", "claude_hooks"),
            "data": data.get("data", {}),
            "metadata": data.get("metadata", {}),
            "processed_at": asyncio.get_event_loop().time(),
            "original_event": data,  # Keep original for debugging
        }

        return processed

    def _process_hook_event(self, data: Dict) -> Dict:
        """Process and normalize hook event data.

        Args:
            data: Raw hook event data

        Returns:
            Processed event data
        """
        processed = {
            "type": data.get("type"),
            "timestamp": data.get("timestamp"),
            "session_id": data.get("session_id"),
            "data": data.get("data", {}),
            "metadata": data.get("metadata", {}),
            "processed_at": asyncio.get_event_loop().time(),
        }

        return processed

    def _update_session_tracking(self, session_id: str, event: Dict):
        """Update session tracking with new event.

        Args:
            session_id: Session ID
            event: Event data
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session["event_count"] += 1
            session["last_activity"] = event.get(
                "timestamp", asyncio.get_event_loop().time()
            )

    async def _replay_events(self, sid: str, events: List[Dict], speed: float):
        """Replay events to a specific client.

        Args:
            sid: Socket.IO session ID
            events: Events to replay
            speed: Replay speed multiplier
        """
        try:
            await self.sio.emit(
                "hook:replay:started",
                {"event_count": len(events), "speed": speed},
                room=sid,
            )

            for i, event in enumerate(events):
                # Calculate delay based on speed
                if i > 0:
                    time_diff = event["timestamp"] - events[i - 1]["timestamp"]
                    delay = max(0.1, time_diff / speed)  # Minimum 0.1s delay
                    await asyncio.sleep(delay)

                # Emit replay event
                await self.sio.emit(
                    "hook:replay:event",
                    {"index": i, "total": len(events), "event": event},
                    room=sid,
                )

            await self.sio.emit(
                "hook:replay:completed", {"event_count": len(events)}, room=sid
            )

        except Exception as e:
            self.logger.error(f"Error during event replay: {e}")
            await self.sio.emit(
                "hook:error", {"error": f"Replay error: {e!s}"}, room=sid
            )

    async def _cleanup_session(self, session_id: str, delay: int = 300):
        """Cleanup session after delay.

        Args:
            session_id: Session ID to cleanup
            delay: Delay in seconds before cleanup
        """
        await asyncio.sleep(delay)
        self.active_sessions.pop(session_id, None)
        self.logger.debug(f"Cleaned up session: {session_id}")
