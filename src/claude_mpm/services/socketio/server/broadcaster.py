"""
SocketIO Event Broadcaster for claude-mpm.

WHY: This module contains all the broadcasting methods extracted from the
monolithic socketio_server.py file. It handles sending events to connected
clients for various Claude MPM activities.

DESIGN DECISION: Separated broadcasting logic from core server management
to create focused, testable modules with single responsibilities.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ....core.logging_config import get_logger


class SocketIOEventBroadcaster:
    """Handles broadcasting events to connected Socket.IO clients.

    WHY: This class encapsulates all the event broadcasting logic that was
    scattered throughout the monolithic SocketIOServer class.
    """

    def __init__(
        self,
        sio,
        connected_clients: Set[str],
        event_buffer,
        buffer_lock,
        stats: Dict[str, Any],
        logger,
    ):
        self.sio = sio
        self.connected_clients = connected_clients
        self.event_buffer = event_buffer
        self.buffer_lock = buffer_lock
        self.stats = stats
        self.logger = logger

    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connected clients."""
        if not self.sio:
            return

        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        # Buffer the event for reliability
        with self.buffer_lock:
            self.event_buffer.append(event)
            self.stats["events_buffered"] += 1

        # Broadcast to all connected clients
        try:
            # Use run_coroutine_threadsafe to safely call from any thread
            if hasattr(self, "loop") and self.loop and not self.loop.is_closed():
                future = asyncio.run_coroutine_threadsafe(
                    self.sio.emit("claude_event", event), self.loop
                )
                # Don't wait for the result to avoid blocking
                self.stats["events_sent"] += 1
                self.logger.debug(f"Broadcasted event: {event_type}")
            else:
                self.logger.warning(
                    f"Cannot broadcast {event_type}: server loop not available"
                )

        except Exception as e:
            self.logger.error(f"Failed to broadcast event {event_type}: {e}")

    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Notify that a session has started."""
        self.broadcast_event(
            "session_started",
            {
                "session_id": session_id,
                "launch_method": launch_method,
                "working_dir": working_dir,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def session_ended(self):
        """Notify that a session has ended."""
        self.broadcast_event("session_ended", {"timestamp": datetime.now().isoformat()})

    def claude_status_changed(
        self, status: str, pid: Optional[int] = None, message: str = ""
    ):
        """Notify Claude status change."""
        self.broadcast_event(
            "claude_status", {"status": status, "pid": pid, "message": message}
        )

    def claude_output(self, content: str, stream: str = "stdout"):
        """Broadcast Claude output."""
        self.broadcast_event("claude_output", {"content": content, "stream": stream})

    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        """Notify agent delegation."""
        self.broadcast_event(
            "agent_delegated", {"agent": agent, "task": task, "status": status}
        )

    def todo_updated(self, todos: List[Dict[str, Any]]):
        """Notify todo list update."""
        # Limit the size of todo data to prevent large payloads
        limited_todos = todos[:50] if len(todos) > 50 else todos

        self.broadcast_event(
            "todo_updated",
            {
                "todos": limited_todos,
                "total_count": len(todos),
                "truncated": len(todos) > 50,
            },
        )

    def ticket_created(self, ticket_id: str, title: str, priority: str = "medium"):
        """Notify ticket creation."""
        self.broadcast_event(
            "ticket_created",
            {"ticket_id": ticket_id, "title": title, "priority": priority},
        )

    def memory_loaded(self, agent_id: str, memory_size: int, sections_count: int):
        """Notify when agent memory is loaded from file."""
        self.broadcast_event(
            "memory_loaded",
            {
                "agent_id": agent_id,
                "memory_size": memory_size,
                "sections_count": sections_count,
            },
        )

    def memory_created(self, agent_id: str, template_type: str):
        """Notify when new agent memory is created from template."""
        self.broadcast_event(
            "memory_created", {"agent_id": agent_id, "template_type": template_type}
        )

    def memory_updated(
        self, agent_id: str, learning_type: str, content: str, section: str
    ):
        """Notify when learning is added to agent memory."""
        # Truncate content if too long to prevent large payloads
        truncated_content = content[:500] + "..." if len(content) > 500 else content

        self.broadcast_event(
            "memory_updated",
            {
                "agent_id": agent_id,
                "learning_type": learning_type,
                "content": truncated_content,
                "section": section,
                "content_length": len(content),
                "truncated": len(content) > 500,
            },
        )

    def memory_injected(self, agent_id: str, context_size: int):
        """Notify when agent memory is injected into context."""
        self.broadcast_event(
            "memory_injected", {"agent_id": agent_id, "context_size": context_size}
        )

    def file_changed(
        self, file_path: str, change_type: str, content: Optional[str] = None
    ):
        """Notify file system changes."""
        event_data = {"file_path": file_path, "change_type": change_type}

        # Include content for small files only
        if content and len(content) < 1000:
            event_data["content"] = content
        elif content:
            event_data["content_preview"] = content[:200] + "..."
            event_data["content_length"] = len(content)

        self.broadcast_event("file_changed", event_data)

    def git_operation(self, operation: str, details: Dict[str, Any]):
        """Notify Git operations."""
        self.broadcast_event(
            "git_operation", {"operation": operation, "details": details}
        )

    def error_occurred(
        self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None
    ):
        """Notify when errors occur."""
        self.broadcast_event(
            "error",
            {"error_type": error_type, "message": message, "details": details or {}},
        )

    def performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """Broadcast performance metrics."""
        self.broadcast_event(
            "performance", {"metric": metric_name, "value": value, "unit": unit}
        )

    def system_status(self, status: Dict[str, Any]):
        """Broadcast system status information."""
        self.broadcast_event("system_status", status)
