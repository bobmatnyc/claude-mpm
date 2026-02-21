"""
Communication Services Module
============================

This module contains all communication-related services including
SocketIO server, WebSocket utilities, and cross-project messaging.

Part of TSK-0046: Service Layer Architecture Reorganization

Services:
- SocketIOServer: Main SocketIO server for real-time communication
- WebSocketClientManager: WebSocket client management utilities
- MessageService: Cross-project messaging system
"""

try:
    from .socketio import SocketIOServer

    _has_socketio = True
except ImportError:
    _has_socketio = False

from .message_service import MessageService

# from .websocket import SocketIOClientManager  # Module has import issues

__all__ = [
    "MessageService",
]

if _has_socketio:
    __all__.append("SocketIOServer")
    # 'SocketIOClientManager',
