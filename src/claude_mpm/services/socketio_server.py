"""Socket.IO server for real-time monitoring of Claude MPM sessions.

WHY: This provides a Socket.IO-based alternative to the WebSocket server,
offering improved connection reliability and automatic reconnection.
Socket.IO handles connection drops gracefully and provides better
cross-platform compatibility.
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Set, Dict, Any, Optional, List
from collections import deque

try:
    import socketio
    import aiohttp
    from aiohttp import web
    SOCKETIO_AVAILABLE = True
    try:
        version = getattr(socketio, '__version__', 'unknown')
        print(f"Socket.IO server using python-socketio v{version}")
    except:
        print("Socket.IO server using python-socketio (version unavailable)")
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None
    aiohttp = None
    web = None
    print("WARNING: python-socketio or aiohttp package not available")

from ..core.logger import get_logger
from ..deployment_paths import get_project_root, get_scripts_dir


class SocketIOClientProxy:
    """Proxy that connects to an existing Socket.IO server as a client.
    
    WHY: In exec mode, a persistent Socket.IO server runs in a separate process.
    The hook handler in the Claude process needs a Socket.IO-like interface
    but shouldn't start another server. This proxy provides that interface
    while the actual events are handled by the persistent server.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.logger = get_logger("socketio_client_proxy")
        self.running = True  # Always "running" for compatibility
        self._sio_client = None
        self._client_thread = None
        
    def start(self):
        """Start the Socket.IO client connection to the persistent server."""
        self.logger.debug(f"SocketIOClientProxy: Connecting to server on {self.host}:{self.port}")
        if SOCKETIO_AVAILABLE:
            self._start_client()
        
    def stop(self):
        """Stop the Socket.IO client connection."""
        self.logger.debug(f"SocketIOClientProxy: Disconnecting from server")
        if self._sio_client:
            self._sio_client.disconnect()
        
    def _start_client(self):
        """Start Socket.IO client in a background thread."""
        def run_client():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._connect_and_run())
            except Exception as e:
                self.logger.error(f"SocketIOClientProxy client thread error: {e}")
            
        self._client_thread = threading.Thread(target=run_client, daemon=True)
        self._client_thread.start()
        # Give it a moment to connect
        time.sleep(0.2)
        
    async def _connect_and_run(self):
        """Connect to the persistent Socket.IO server and keep connection alive."""
        try:
            self._sio_client = socketio.AsyncClient()
            
            @self._sio_client.event
            async def connect():
                self.logger.info(f"SocketIOClientProxy: Connected to server at http://{self.host}:{self.port}")
                
            @self._sio_client.event
            async def disconnect():
                self.logger.info(f"SocketIOClientProxy: Disconnected from server")
                
            # Connect to the server
            await self._sio_client.connect(f'http://127.0.0.1:{self.port}')
            
            # Keep the connection alive until stopped
            while self.running:
                await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"SocketIOClientProxy: Connection error: {e}")
            self._sio_client = None
        
    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Send event to the persistent Socket.IO server."""
        if not SOCKETIO_AVAILABLE:
            return
            
        # Ensure client is started
        if not self._client_thread or not self._client_thread.is_alive():
            self.logger.debug(f"SocketIOClientProxy: Starting client for {event_type}")
            self._start_client()
            
        if self._sio_client and self._sio_client.connected:
            try:
                event = {
                    "type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                }
                
                # Send asynchronously using emit
                asyncio.create_task(
                    self._sio_client.emit('claude_event', event)
                )
                
                self.logger.debug(f"SocketIOClientProxy: Sent event {event_type}")
            except Exception as e:
                self.logger.error(f"SocketIOClientProxy: Failed to send event {event_type}: {e}")
        else:
            self.logger.warning(f"SocketIOClientProxy: Client not ready for {event_type}")
    
    # Compatibility methods for WebSocketServer interface
    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        self.logger.debug(f"SocketIOClientProxy: Session started {session_id}")
        
    def session_ended(self):
        self.logger.debug(f"SocketIOClientProxy: Session ended")
        
    def claude_status_changed(self, status: str, pid: Optional[int] = None, message: str = ""):
        self.logger.debug(f"SocketIOClientProxy: Claude status {status}")
        
    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        self.logger.debug(f"SocketIOClientProxy: Agent {agent} delegated")
        
    def todo_updated(self, todos: List[Dict[str, Any]]):
        self.logger.debug(f"SocketIOClientProxy: Todo updated ({len(todos)} todos)")


class SocketIOServer:
    """Socket.IO server for broadcasting Claude MPM events.
    
    WHY: Socket.IO provides better connection reliability than raw WebSockets,
    with automatic reconnection, fallback transports, and better error handling.
    It maintains the same event interface as WebSocketServer for compatibility.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.logger = get_logger("socketio_server")
        self.clients: Set[str] = set()  # Store session IDs instead of connection objects
        self.event_history: deque = deque(maxlen=1000)  # Keep last 1000 events
        self.sio = None
        self.app = None
        self.runner = None
        self.site = None
        self.loop = None
        self.thread = None
        self.running = False
        
        # Session state
        self.session_id = None
        self.session_start = None
        self.claude_status = "stopped"
        self.claude_pid = None
        
        if not SOCKETIO_AVAILABLE:
            self.logger.warning("Socket.IO support not available. Install 'python-socketio' and 'aiohttp' packages to enable.")
        
    def start(self):
        """Start the Socket.IO server in a background thread."""
        if not SOCKETIO_AVAILABLE:
            self.logger.debug("Socket.IO server skipped - required packages not installed")
            return
            
        if self.running:
            self.logger.debug(f"Socket.IO server already running on port {self.port}")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        self.logger.info(f"🚀 Socket.IO server STARTING on http://{self.host}:{self.port}")
        self.logger.info(f"🔧 Thread created: {self.thread.name} (daemon={self.thread.daemon})")
        
        # Give server a moment to start
        time.sleep(0.1)
        
        if self.thread.is_alive():
            self.logger.info(f"✅ Socket.IO server thread is alive and running")
        else:
            self.logger.error(f"❌ Socket.IO server thread failed to start!")
        
    def stop(self):
        """Stop the Socket.IO server."""
        self.running = False
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._shutdown(), self.loop)
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Socket.IO server stopped")
        
    def _run_server(self):
        """Run the server event loop."""
        self.logger.info(f"🔄 _run_server starting on thread: {threading.current_thread().name}")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.logger.info(f"📡 Event loop created and set for Socket.IO server")
        
        try:
            self.logger.info(f"🎯 About to start _serve() coroutine")
            self.loop.run_until_complete(self._serve())
        except Exception as e:
            self.logger.error(f"❌ Socket.IO server error in _run_server: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
        finally:
            self.logger.info(f"🔚 Socket.IO server _run_server shutting down")
            self.loop.close()
            
    async def _serve(self):
        """Start the Socket.IO server."""
        try:
            self.logger.info(f"🔌 _serve() starting - attempting to bind to {self.host}:{self.port}")
            
            # Create Socket.IO server with improved configuration
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*",
                ping_timeout=120,
                ping_interval=30,
                max_http_buffer_size=1000000,
                allow_upgrades=True,
                transports=['websocket', 'polling'],
                logger=False,  # Reduce noise in logs
                engineio_logger=False
            )
            
            # Create aiohttp web application
            self.app = web.Application()
            self.sio.attach(self.app)
            
            # Add HTTP routes
            self.app.router.add_get('/health', self._handle_health)
            self.app.router.add_get('/status', self._handle_health)
            
            # Register event handlers
            self._register_events()
            
            # Start the server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self.logger.info(f"🎉 Socket.IO server SUCCESSFULLY listening on http://{self.host}:{self.port}")
            
            # Keep server running
            loop_count = 0
            while self.running:
                await asyncio.sleep(0.1)
                loop_count += 1
                if loop_count % 100 == 0:  # Log every 10 seconds
                    self.logger.debug(f"🔄 Socket.IO server heartbeat - {len(self.clients)} clients connected")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to start Socket.IO server: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            raise
                
    async def _shutdown(self):
        """Shutdown the server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
            
    async def _handle_health(self, request):
        """Handle health check requests."""
        return web.json_response({
            "status": "healthy",
            "server": "claude-mpm-python-socketio",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "port": self.port,
            "host": self.host,
            "clients_connected": len(self.clients)
        })
        
            
    def _register_events(self):
        """Register Socket.IO event handlers."""
        
        @self.sio.event
        async def connect(sid, environ, *args):
            """Handle client connection."""
            self.clients.add(sid)
            client_addr = environ.get('REMOTE_ADDR', 'unknown') 
            user_agent = environ.get('HTTP_USER_AGENT', 'unknown')
            self.logger.info(f"🔗 NEW CLIENT CONNECTED: {sid} from {client_addr}")
            self.logger.info(f"📱 User Agent: {user_agent[:100]}...")
            self.logger.info(f"📈 Total clients now: {len(self.clients)}")
            
            # Send initial status immediately with enhanced data
            status_data = {
                "server": "claude-mpm-python-socketio",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "session_id": self.session_id,
                "claude_status": self.claude_status,
                "claude_pid": self.claude_pid,
                "server_version": "2.0.0",
                "client_id": sid
            }
            
            try:
                await self.sio.emit('status', status_data, room=sid)
                await self.sio.emit('welcome', {
                    "message": "Connected to Claude MPM Socket.IO server",
                    "client_id": sid,
                    "server_time": datetime.utcnow().isoformat() + "Z"
                }, room=sid)
                
                # Automatically send the last 50 events to new clients
                await self._send_event_history(sid, limit=50)
                
                self.logger.debug(f"✅ Sent welcome messages and event history to client {sid}")
            except Exception as e:
                self.logger.error(f"❌ Failed to send welcome to client {sid}: {e}")
                import traceback
                self.logger.error(f"Full traceback: {traceback.format_exc()}")
            
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            if sid in self.clients:
                self.clients.remove(sid)
                self.logger.info(f"🔌 CLIENT DISCONNECTED: {sid}")
                self.logger.info(f"📉 Total clients now: {len(self.clients)}")
            else:
                self.logger.warning(f"⚠️  Attempted to disconnect unknown client: {sid}")
            
        @self.sio.event
        async def get_status(sid):
            """Handle status request."""
            # Send compatible status event (not claude_event)
            status_data = {
                "server": "claude-mpm-python-socketio",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "session_id": self.session_id,
                "claude_status": self.claude_status,
                "claude_pid": self.claude_pid
            }
            await self.sio.emit('status', status_data, room=sid)
            self.logger.debug(f"Sent status response to client {sid}")
            
        @self.sio.event
        async def get_history(sid, data=None):
            """Handle history request."""
            params = data or {}
            event_types = params.get("event_types", [])
            limit = min(params.get("limit", 100), len(self.event_history))
            
            await self._send_event_history(sid, event_types=event_types, limit=limit)
            
        @self.sio.event
        async def request_history(sid, data=None):
            """Handle legacy history request (for client compatibility)."""
            # This handles the 'request.history' event that the client currently emits
            params = data or {}
            event_types = params.get("event_types", [])
            limit = min(params.get("limit", 50), len(self.event_history))
            
            await self._send_event_history(sid, event_types=event_types, limit=limit)
            
        @self.sio.event
        async def subscribe(sid, data=None):
            """Handle subscription request."""
            channels = data.get("channels", ["*"]) if data else ["*"]
            await self.sio.emit('subscribed', {
                "channels": channels
            }, room=sid)
            
        @self.sio.event
        async def claude_event(sid, data):
            """Handle events from client proxies."""
            # Store in history
            self.event_history.append(data)
            self.logger.debug(f"📚 Event from client stored in history (total: {len(self.event_history)})")
            
            # Re-broadcast to all other clients
            await self.sio.emit('claude_event', data, skip_sid=sid)
            
    async def _send_current_status(self, sid: str):
        """Send current system status to a client."""
        try:
            status = {
                "type": "system.status",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "session_id": self.session_id,
                    "session_start": self.session_start,
                    "claude_status": self.claude_status,
                    "claude_pid": self.claude_pid,
                    "connected_clients": len(self.clients),
                    "websocket_port": self.port,
                    "instance_info": {
                        "port": self.port,
                        "host": self.host,
                        "working_dir": os.getcwd() if self.session_id else None
                    }
                }
            }
            await self.sio.emit('claude_event', status, room=sid)
            self.logger.debug("Sent status to client")
        except Exception as e:
            self.logger.error(f"Failed to send status to client: {e}")
            raise
            
    async def _send_event_history(self, sid: str, event_types: list = None, limit: int = 50):
        """Send event history to a specific client.
        
        WHY: When clients connect to the dashboard, they need context from recent events
        to understand what's been happening. This sends the most recent events in
        chronological order (oldest first) so the dashboard displays them properly.
        
        Args:
            sid: Socket.IO session ID of the client
            event_types: Optional list of event types to filter by
            limit: Maximum number of events to send (default: 50)
        """
        try:
            if not self.event_history:
                self.logger.debug(f"No event history to send to client {sid}")
                return
                
            # Limit to reasonable number to avoid overwhelming client
            limit = min(limit, 100)
            
            # Get the most recent events, filtered by type if specified
            history = []
            for event in reversed(self.event_history):
                if not event_types or event.get("type") in event_types:
                    history.append(event)
                    if len(history) >= limit:
                        break
            
            # Reverse to get chronological order (oldest first)
            history = list(reversed(history))
            
            if history:
                # Send as 'history' event that the client expects
                await self.sio.emit('history', {
                    "events": history,
                    "count": len(history),
                    "total_available": len(self.event_history)
                }, room=sid)
                
                self.logger.info(f"📚 Sent {len(history)} historical events to client {sid}")
            else:
                self.logger.debug(f"No matching events found for client {sid} with filters: {event_types}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to send event history to client {sid}: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            
    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connected clients."""
        if not SOCKETIO_AVAILABLE:
            self.logger.debug(f"⚠️  Socket.IO broadcast skipped - packages not available")
            return
            
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        
        self.logger.info(f"📤 BROADCASTING EVENT: {event_type}")
        self.logger.debug(f"📄 Event data: {json.dumps(data, indent=2)[:200]}...")
        
        # Store in history
        self.event_history.append(event)
        self.logger.debug(f"📚 Event stored in history (total: {len(self.event_history)})")
        
        # Check if we have clients and event loop
        if not self.clients:
            self.logger.warning(f"⚠️  No Socket.IO clients connected - event will not be delivered")
            return
            
        if not self.loop or not self.sio:
            self.logger.error(f"❌ No event loop or Socket.IO instance available - cannot broadcast event")
            return
            
        self.logger.info(f"🎯 Broadcasting to {len(self.clients)} clients via event loop")
        
        # Broadcast to clients with timeout and error handling
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.sio.emit('claude_event', event),
                self.loop
            )
            # Wait for completion with timeout to detect issues
            try:
                future.result(timeout=2.0)  # 2 second timeout
                self.logger.debug(f"📨 Successfully broadcasted {event_type} to {len(self.clients)} clients")
            except asyncio.TimeoutError:
                self.logger.warning(f"⏰ Broadcast timeout for event {event_type} - continuing anyway")
            except Exception as emit_error:
                self.logger.error(f"❌ Broadcast emit error for {event_type}: {emit_error}")
        except Exception as e:
            self.logger.error(f"❌ Failed to submit broadcast to event loop: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            
    # Convenience methods for common events (same interface as WebSocketServer)
    
    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Notify that a session has started."""
        self.session_id = session_id
        self.session_start = datetime.utcnow().isoformat() + "Z"
        self.broadcast_event("session.start", {
            "session_id": session_id,
            "start_time": self.session_start,
            "launch_method": launch_method,
            "working_directory": working_dir,
            "websocket_port": self.port,
            "instance_info": {
                "port": self.port,
                "host": self.host,
                "working_dir": working_dir
            }
        })
        
    def session_ended(self):
        """Notify that a session has ended."""
        if self.session_id:
            duration = None
            if self.session_start:
                start = datetime.fromisoformat(self.session_start.replace("Z", "+00:00"))
                duration = (datetime.utcnow() - start.replace(tzinfo=None)).total_seconds()
                
            self.broadcast_event("session.end", {
                "session_id": self.session_id,
                "end_time": datetime.utcnow().isoformat() + "Z",
                "duration_seconds": duration
            })
            
        self.session_id = None
        self.session_start = None
        
    def claude_status_changed(self, status: str, pid: Optional[int] = None, message: str = ""):
        """Notify Claude status change."""
        self.claude_status = status
        self.claude_pid = pid
        self.broadcast_event("claude.status", {
            "status": status,
            "pid": pid,
            "message": message
        })
        
    def claude_output(self, content: str, stream: str = "stdout"):
        """Broadcast Claude output."""
        self.broadcast_event("claude.output", {
            "content": content,
            "stream": stream
        })
        
    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        """Notify agent delegation."""
        self.broadcast_event("agent.delegation", {
            "agent": agent,
            "task": task,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    def todo_updated(self, todos: List[Dict[str, Any]]):
        """Notify todo list update."""
        stats = {
            "total": len(todos),
            "completed": sum(1 for t in todos if t.get("status") == "completed"),
            "in_progress": sum(1 for t in todos if t.get("status") == "in_progress"),
            "pending": sum(1 for t in todos if t.get("status") == "pending")
        }
        
        self.broadcast_event("todo.update", {
            "todos": todos,
            "stats": stats
        })
        
    def ticket_created(self, ticket_id: str, title: str, priority: str = "medium"):
        """Notify ticket creation."""
        self.broadcast_event("ticket.created", {
            "id": ticket_id,
            "title": title,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat() + "Z"
        })
        
    def memory_loaded(self, agent_id: str, memory_size: int, sections_count: int):
        """Notify when agent memory is loaded from file."""
        self.broadcast_event("memory:loaded", {
            "agent_id": agent_id,
            "memory_size": memory_size,
            "sections_count": sections_count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    def memory_created(self, agent_id: str, template_type: str):
        """Notify when new agent memory is created from template."""
        self.broadcast_event("memory:created", {
            "agent_id": agent_id,
            "template_type": template_type,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    def memory_updated(self, agent_id: str, learning_type: str, content: str, section: str):
        """Notify when learning is added to agent memory."""
        self.broadcast_event("memory:updated", {
            "agent_id": agent_id,
            "learning_type": learning_type,
            "content": content,
            "section": section,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    def memory_injected(self, agent_id: str, context_size: int):
        """Notify when agent memory is injected into context."""
        self.broadcast_event("memory:injected", {
            "agent_id": agent_id,
            "context_size": context_size,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })


# Global instance for easy access
_socketio_server: Optional[SocketIOServer] = None


def get_socketio_server() -> SocketIOServer:
    """Get or create the global Socket.IO server instance.
    
    WHY: In exec mode, a persistent Socket.IO server may already be running
    in a separate process. We need to detect this and create a client proxy
    instead of trying to start another server.
    """
    global _socketio_server
    if _socketio_server is None:
        # Check if a Socket.IO server is already running on the default port
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(('127.0.0.1', 8765))
                if result == 0:
                    # Server is already running - create a client proxy
                    _socketio_server = SocketIOClientProxy(port=8765)
                else:
                    # No server running - create a real server
                    _socketio_server = SocketIOServer()
        except Exception:
            # On any error, create a real server
            _socketio_server = SocketIOServer()
        
    return _socketio_server


def start_socketio_server():
    """Start the global Socket.IO server."""
    server = get_socketio_server()
    server.start()
    return server


def stop_socketio_server():
    """Stop the global Socket.IO server."""
    global _socketio_server
    if _socketio_server:
        _socketio_server.stop()
        _socketio_server = None