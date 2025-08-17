"""Socket.IO server for real-time monitoring of Claude MPM sessions.

WHY: This module provides backward compatibility and delegates to the new modular
SocketIO server structure. The massive SocketIOServer class has been split into
focused modules in the socketio/ package.

DESIGN DECISION: We maintain this file for backward compatibility while the actual
server logic has been moved to socketio/ modules for better maintainability.

REFACTORING NOTE: The original 1,934-line file has been split into:
- socketio/client_proxy.py: Client proxy for exec mode
- socketio/server/core.py: Core server management and static files
- socketio/server/broadcaster.py: Event broadcasting to clients
- socketio/server/main.py: Main server class that combines components
- socketio/handlers/: Modular event handler system (already existed)

IMPACT: Reduced from 1,934 lines to ~50 lines, with functionality split across
focused modules for better maintainability and testing.
"""

import socket
from typing import Optional

# Import from the new modular structure
from .socketio.client_proxy import SocketIOClientProxy
from .socketio.server.main import SocketIOServer

# Re-export for backward compatibility
__all__ = [
    "SocketIOClientProxy",
    "SocketIOServer",
    "get_socketio_server",
    "start_socketio_server",
    "stop_socketio_server",
]

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
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(("127.0.0.1", 8765))
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
    server.start_sync()
    return server


def stop_socketio_server():
    """Stop the global Socket.IO server."""
    global _socketio_server
    if _socketio_server:
        _socketio_server.stop_sync()
        _socketio_server = None


# All server functionality has been moved to the socketio/ package
# This file now serves as a compatibility layer that delegates to the modular structure
