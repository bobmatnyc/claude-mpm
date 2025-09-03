"""
SocketIO Client Proxy for claude-mpm.

WHY: This module contains the SocketIOClientProxy class that was extracted from
the monolithic socketio_server.py file. In exec mode, a persistent Socket.IO
server runs in a separate process, and this proxy provides a Socket.IO-like
interface without starting another server.

DESIGN DECISION: Separated client proxy logic from server logic for better
organization and to reduce the complexity of the main server file.
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

import contextlib

from ...core.logging_config import get_logger


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
        self.logger = get_logger(__name__ + ".SocketIOClientProxy")
        self.running = True  # Always "running" for compatibility
        self._sio_client = None
        self._client_thread = None
        self._client_loop = None

    def start(self):
        """Start the Socket.IO client connection (compatibility wrapper).

        This method exists for backward compatibility with code that expects
        a start() method. It simply calls start_sync().
        """
        return self.start_sync()

    def stop(self):
        """Stop the Socket.IO client connection (compatibility wrapper).

        This method exists for backward compatibility with code that expects
        a stop() method. It simply calls stop_sync().
        """
        return self.stop_sync()

    def start_sync(self):
        """Start the Socket.IO client connection to the persistent server."""
        self.logger.debug(
            f"SocketIOClientProxy: Connecting to server on {self.host}:{self.port}"
        )
        if SOCKETIO_AVAILABLE:
            self._start_client()

    def stop_sync(self):
        """Stop the Socket.IO client connection."""
        self.logger.debug("SocketIOClientProxy: Disconnecting from server")
        if self._sio_client:
            self._sio_client.disconnect()

    def _start_client(self):
        """Start Socket.IO client in a background thread."""

        def run_client():
            self._client_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._client_loop)
            try:
                self._client_loop.run_until_complete(self._connect_and_run())
            except Exception as e:
                self.logger.error(f"SocketIOClientProxy client thread error: {e}")
            finally:
                self._client_loop.close()

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
                self.logger.info(
                    f"SocketIOClientProxy: Connected to server at http://{self.host}:{self.port}"
                )

            @self._sio_client.event
            async def disconnect():
                self.logger.info("SocketIOClientProxy: Disconnected from server")

            # Try connecting with different hostname formats
            # Some systems resolve localhost differently than 127.0.0.1
            connection_urls = [
                f"http://{self.host}:{self.port}",  # Use the provided host (usually "localhost")
                f"http://127.0.0.1:{self.port}",  # Try IP address
                f"http://localhost:{self.port}",  # Try localhost explicitly
            ]

            connected = False
            last_error = None

            for url in connection_urls:
                try:
                    self.logger.debug(
                        f"SocketIOClientProxy: Attempting connection to {url}"
                    )
                    await self._sio_client.connect(url)
                    connected = True
                    self.logger.info(
                        f"SocketIOClientProxy: Successfully connected to {url}"
                    )
                    break
                except Exception as e:
                    last_error = e
                    # Only log as debug to avoid confusion when fallback succeeds
                    self.logger.debug(
                        f"SocketIOClientProxy: Failed to connect to {url}: {e}"
                    )
                    # Disconnect any partial connection before trying next URL
                    with contextlib.suppress(Exception):
                        await self._sio_client.disconnect()

            if not connected:
                # Only show error if all attempts failed
                self.logger.error(
                    f"SocketIOClientProxy: Connection error after trying all addresses: {last_error}"
                )
                self._sio_client = None
                return

            # Keep the connection alive until stopped
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"SocketIOClientProxy: Unexpected error: {e}")
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
                    "data": data,
                }

                # Send event safely using run_coroutine_threadsafe
                if (
                    hasattr(self, "_client_loop")
                    and self._client_loop
                    and not self._client_loop.is_closed()
                ):
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self._sio_client.emit("claude_event", event),
                            self._client_loop,
                        )
                        # Don't wait for the result to avoid blocking
                        self.logger.debug(
                            f"SocketIOClientProxy: Scheduled emit for {event_type}"
                        )
                    except Exception as e:
                        self.logger.error(
                            f"SocketIOClientProxy: Failed to schedule emit for {event_type}: {e}"
                        )
                else:
                    self.logger.warning(
                        f"SocketIOClientProxy: Client event loop not available for {event_type}"
                    )

                self.logger.debug(f"SocketIOClientProxy: Sent event {event_type}")
            except Exception as e:
                self.logger.error(
                    f"SocketIOClientProxy: Failed to send event {event_type}: {e}"
                )
        else:
            self.logger.warning(
                f"SocketIOClientProxy: Client not ready for {event_type}"
            )

    # Compatibility methods for WebSocketServer interface
    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        self.logger.debug(f"SocketIOClientProxy: Session started {session_id}")

    def session_ended(self):
        self.logger.debug("SocketIOClientProxy: Session ended")

    def claude_status_changed(
        self, status: str, pid: Optional[int] = None, message: str = ""
    ):
        self.logger.debug(f"SocketIOClientProxy: Claude status {status}")

    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        self.logger.debug(f"SocketIOClientProxy: Agent {agent} delegated")

    def todo_updated(self, todos: List[Dict[str, Any]]):
        self.logger.debug(f"SocketIOClientProxy: Todo updated ({len(todos)} todos)")
