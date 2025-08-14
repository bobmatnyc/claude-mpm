"""
Communication Services Module
============================

This module contains all communication-related services including
SocketIO server and WebSocket utilities.

Part of TSK-0046: Service Layer Architecture Reorganization

Services:
- SocketIOServer: Main SocketIO server for real-time communication
- WebSocketClientManager: WebSocket client management utilities
"""

from .socketio import SocketIOServer
from .websocket import SocketIOClientManager

__all__ = [
    'SocketIOServer',
    'SocketIOClientManager',
]