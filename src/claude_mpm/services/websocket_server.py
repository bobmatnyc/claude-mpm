"""WebSocket server for real-time monitoring of Claude MPM sessions."""

import asyncio
import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Set, Dict, Any, Optional, List
from collections import deque

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None
    WebSocketServerProtocol = None

from ..core.logger import get_logger


class WebSocketServer:
    """WebSocket server for broadcasting Claude MPM events."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.logger = get_logger("websocket_server")
        self.clients: Set[WebSocketServerProtocol] = set() if WEBSOCKETS_AVAILABLE else set()
        self.event_history: deque = deque(maxlen=1000)  # Keep last 1000 events
        self.server = None
        self.loop = None
        self.thread = None
        self.running = False
        
        # Session state
        self.session_id = None
        self.session_start = None
        self.claude_status = "stopped"
        self.claude_pid = None
        
        if not WEBSOCKETS_AVAILABLE:
            self.logger.warning("WebSocket support not available. Install 'websockets' package to enable.")
        
    def start(self):
        """Start the WebSocket server in a background thread."""
        if not WEBSOCKETS_AVAILABLE:
            self.logger.debug("WebSocket server skipped - websockets package not installed")
            return
            
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        self.logger.info(f"WebSocket server starting on ws://{self.host}:{self.port}")
        
    def stop(self):
        """Stop the WebSocket server."""
        self.running = False
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._shutdown(), self.loop)
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("WebSocket server stopped")
        
    def _run_server(self):
        """Run the server event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._serve())
        except Exception as e:
            self.logger.error(f"WebSocket server error: {e}")
        finally:
            self.loop.close()
            
    async def _serve(self):
        """Start the WebSocket server."""
        async with websockets.serve(self._handle_client, self.host, self.port):
            self.logger.info(f"WebSocket server listening on ws://{self.host}:{self.port}")
            while self.running:
                await asyncio.sleep(0.1)
                
    async def _shutdown(self):
        """Shutdown the server."""
        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
            
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a new client connection."""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        self.logger.info(f"Client connected from {client_addr}")
        
        try:
            # Send current status
            await self._send_current_status(websocket)
            
            # Handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_command(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "data": {"message": "Invalid JSON"}
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            self.logger.info(f"Client disconnected from {client_addr}")
            
    async def _send_current_status(self, websocket: WebSocketServerProtocol):
        """Send current system status to a client."""
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
        await websocket.send(json.dumps(status))
        
    async def _handle_command(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle commands from clients."""
        command = data.get("command")
        
        if command == "get_status":
            await self._send_current_status(websocket)
            
        elif command == "get_history":
            # Send recent events
            params = data.get("params", {})
            event_types = params.get("event_types", [])
            limit = min(params.get("limit", 100), len(self.event_history))
            
            history = []
            for event in reversed(self.event_history):
                if not event_types or event["type"] in event_types:
                    history.append(event)
                    if len(history) >= limit:
                        break
                        
            await websocket.send(json.dumps({
                "type": "history",
                "data": {"events": list(reversed(history))}
            }))
            
        elif command == "subscribe":
            # For now, all clients get all events
            await websocket.send(json.dumps({
                "type": "subscribed",
                "data": {"channels": data.get("channels", ["*"])}
            }))
            
    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connected clients."""
        if not WEBSOCKETS_AVAILABLE:
            return
            
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        
        # Store in history
        self.event_history.append(event)
        
        # Broadcast to clients
        if self.clients and self.loop:
            asyncio.run_coroutine_threadsafe(
                self._broadcast(json.dumps(event)),
                self.loop
            )
            
    async def _broadcast(self, message: str):
        """Send a message to all connected clients."""
        if self.clients:
            # Send to all clients concurrently
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
            
    # Convenience methods for common events
    
    def _get_git_branch(self, working_dir: str) -> str:
        """Get the current git branch for the working directory."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "not a git repo"
    
    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Notify that a session has started."""
        self.session_id = session_id
        self.session_start = datetime.utcnow().isoformat() + "Z"
        
        # Get git branch if in a git repo
        git_branch = self._get_git_branch(working_dir)
        
        self.broadcast_event("session.start", {
            "session_id": session_id,
            "start_time": self.session_start,
            "launch_method": launch_method,
            "working_directory": working_dir,
            "git_branch": git_branch,
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
_websocket_server: Optional[WebSocketServer] = None


def get_websocket_server() -> WebSocketServer:
    """Get or create the global WebSocket server instance."""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = WebSocketServer()
    return _websocket_server


def start_websocket_server():
    """Start the global WebSocket server."""
    server = get_websocket_server()
    server.start()
    return server


def stop_websocket_server():
    """Stop the global WebSocket server."""
    global _websocket_server
    if _websocket_server:
        _websocket_server.stop()
        _websocket_server = None