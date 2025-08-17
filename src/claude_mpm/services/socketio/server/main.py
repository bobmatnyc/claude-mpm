"""
Main SocketIO Server for claude-mpm.

WHY: This module combines the modular server components into a single
SocketIOServer class that maintains the same interface as the original
monolithic implementation while using the new modular structure.

DESIGN DECISION: Composition over inheritance - the main server class
delegates to specialized components rather than inheriting from them.
"""

import asyncio
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

try:
    import aiohttp
    import socketio
    from aiohttp import web

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None
    aiohttp = None
    web = None

from ....core.constants import (
    NetworkConfig,
    PerformanceConfig,
    SystemLimits,
    TimeoutConfig,
)
from ...core.interfaces.communication import SocketIOServiceInterface
from ....core.logging_config import get_logger, log_operation, log_performance_context
from ....core.unified_paths import get_project_root, get_scripts_dir
from ...exceptions import SocketIOServerError as MPMConnectionError
from ..handlers import EventHandlerRegistry, FileEventHandler, GitEventHandler
from .broadcaster import SocketIOEventBroadcaster
from .core import SocketIOServerCore


class SocketIOServer(SocketIOServiceInterface):
    """Socket.IO server for broadcasting Claude MPM events.

    WHY: Socket.IO provides better connection reliability than raw WebSockets,
    with automatic reconnection, fallback transports, and better error handling.
    It maintains the same event interface as WebSocketServer for compatibility.

    This class now uses composition to delegate to specialized components:
    - SocketIOServerCore: Server lifecycle and static file management
    - SocketIOEventBroadcaster: Event broadcasting to clients
    - EventHandlerRegistry: Modular event handler registration
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.logger = get_logger(__name__ + ".SocketIOServer")

        # Core server management
        self.core = SocketIOServerCore(host, port)

        # Event broadcasting (will be initialized after core starts)
        self.broadcaster = None

        # Event handler registry
        self.event_registry = None

        # Legacy compatibility attributes
        self.running = False
        self.connected_clients: Set[str] = set()
        self.client_info: Dict[str, Dict[str, Any]] = {}
        self.event_buffer = deque(maxlen=SystemLimits.MAX_EVENTS_BUFFER)
        self.buffer_lock = threading.Lock()
        self.stats = {
            "events_sent": 0,
            "events_buffered": 0,
            "connections_total": 0,
            "start_time": None,
        }

        # Session tracking
        self.session_id = None
        self.claude_status = "unknown"
        self.claude_pid = None
        self.event_history = deque(maxlen=SystemLimits.MAX_EVENTS_BUFFER)
        
        # Active session tracking for heartbeat
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def start_sync(self):
        """Start the Socket.IO server in a background thread (synchronous version)."""
        if not SOCKETIO_AVAILABLE:
            self.logger.warning("Socket.IO not available - server not started")
            return

        # Set reference to main server for session data
        self.core.main_server = self
        
        # Start the core server
        self.core.start_sync()

        # Initialize broadcaster with core server components
        self.broadcaster = SocketIOEventBroadcaster(
            sio=self.core.sio,
            connected_clients=self.connected_clients,
            event_buffer=self.event_buffer,
            buffer_lock=self.buffer_lock,
            stats=self.stats,
            logger=self.logger,
        )

        # Set the loop reference for broadcaster
        self.broadcaster.loop = self.core.loop

        # Register events
        self._register_events()

        # Update running state
        self.running = self.core.running
        self.stats["start_time"] = self.core.stats["start_time"]

        self.logger.info(
            f"SocketIO server started successfully on {self.host}:{self.port}"
        )

    def stop_sync(self):
        """Stop the Socket.IO server (synchronous version)."""
        self.core.stop_sync()
        self.running = False

    def _register_events(self):
        """Register Socket.IO event handlers.

        WHY: This method now uses the EventHandlerRegistry to manage all event
        handlers in a modular way. Each handler focuses on a specific domain,
        reducing complexity and improving maintainability.
        """
        # Initialize the event handler registry
        self.event_registry = EventHandlerRegistry(self)
        self.event_registry.initialize()

        # Register all events from all handlers
        self.event_registry.register_all_events()

        # Keep handler instances for HTTP endpoint compatibility
        self.file_handler = self.event_registry.get_handler(FileEventHandler)
        self.git_handler = self.event_registry.get_handler(GitEventHandler)

        self.logger.info("All Socket.IO events registered via handler system")

    # Delegate broadcasting methods to the broadcaster
    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connected clients."""
        if self.broadcaster:
            self.broadcaster.broadcast_event(event_type, data)
    
    def send_to_client(self, client_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """Send an event to a specific client.
        
        WHY: The SocketIOServiceInterface requires this method for targeted 
        messaging. We delegate to the Socket.IO server's emit method with
        the client's session ID as the room.
        
        Args:
            client_id: ID of the target client
            event_type: Type of event to send
            data: Event data to send
            
        Returns:
            True if message sent successfully
        """
        if not self.core or not self.core.sio:
            return False
        
        try:
            # Socket.IO uses session IDs as room names for individual clients
            # We can send to a specific client by using their session ID as the room
            if client_id in self.connected_clients:
                # Use the asyncio loop to emit to specific client
                if self.core.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.core.sio.emit(event_type, data, room=client_id),
                        self.core.loop
                    )
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error sending to client {client_id}: {e}")
            return False

    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Notify that a session has started."""
        self.session_id = session_id
        
        # Track active session for heartbeat
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "agent": "pm",  # Default to PM, will be updated if delegated
            "status": "active",
            "launch_method": launch_method,
            "working_dir": working_dir,
        }
        
        if self.broadcaster:
            self.broadcaster.session_started(session_id, launch_method, working_dir)

    def session_ended(self):
        """Notify that a session has ended."""
        # Remove from active sessions
        if self.session_id and self.session_id in self.active_sessions:
            del self.active_sessions[self.session_id]
            
        if self.broadcaster:
            self.broadcaster.session_ended()

    def claude_status_changed(
        self, status: str, pid: Optional[int] = None, message: str = ""
    ):
        """Notify Claude status change."""
        self.claude_status = status
        self.claude_pid = pid
        if self.broadcaster:
            self.broadcaster.claude_status_changed(status, pid, message)

    def claude_output(self, content: str, stream: str = "stdout"):
        """Broadcast Claude output."""
        if self.broadcaster:
            self.broadcaster.claude_output(content, stream)

    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        """Notify agent delegation."""
        # Update active session with current agent
        if self.session_id and self.session_id in self.active_sessions:
            self.active_sessions[self.session_id]["agent"] = agent
            self.active_sessions[self.session_id]["status"] = status
            
        if self.broadcaster:
            self.broadcaster.agent_delegated(agent, task, status)

    def todo_updated(self, todos: List[Dict[str, Any]]):
        """Notify todo list update."""
        if self.broadcaster:
            self.broadcaster.todo_updated(todos)

    def ticket_created(self, ticket_id: str, title: str, priority: str = "medium"):
        """Notify ticket creation."""
        if self.broadcaster:
            self.broadcaster.ticket_created(ticket_id, title, priority)

    def memory_loaded(self, agent_id: str, memory_size: int, sections_count: int):
        """Notify when agent memory is loaded from file."""
        if self.broadcaster:
            self.broadcaster.memory_loaded(agent_id, memory_size, sections_count)

    def memory_created(self, agent_id: str, template_type: str):
        """Notify when new agent memory is created from template."""
        if self.broadcaster:
            self.broadcaster.memory_created(agent_id, template_type)

    def memory_updated(
        self, agent_id: str, learning_type: str, content: str, section: str
    ):
        """Notify when learning is added to agent memory."""
        if self.broadcaster:
            self.broadcaster.memory_updated(agent_id, learning_type, content, section)

    def memory_injected(self, agent_id: str, context_size: int):
        """Notify when agent memory is injected into context."""
        if self.broadcaster:
            self.broadcaster.memory_injected(agent_id, context_size)

    # Delegate core server methods
    def get_connection_count(self) -> int:
        """Get number of connected clients."""
        return self.core.get_connection_count()

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.core.is_running()
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions for heartbeat.
        
        WHY: Provides session information for system heartbeat events.
        """
        # Clean up old sessions (older than 1 hour)
        cutoff_time = datetime.now().timestamp() - 3600
        sessions_to_remove = []
        
        for session_id, session_data in self.active_sessions.items():
            try:
                start_time = datetime.fromisoformat(session_data["start_time"])
                if start_time.timestamp() < cutoff_time:
                    sessions_to_remove.append(session_id)
            except:
                pass
        
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
        
        # Return list of active sessions
        return list(self.active_sessions.values())


    # Legacy compatibility properties
    @property
    def sio(self):
        """Access to the Socket.IO server instance."""
        return self.core.sio

    @property
    def clients(self):
        """Access to connected clients set."""
        return self.connected_clients
