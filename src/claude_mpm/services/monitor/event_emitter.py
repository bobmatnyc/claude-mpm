"""
High-Performance Async Event Emitter
====================================

Provides ultra-low latency event emission with direct function calls for in-process
events and connection pooling for external HTTP requests.

WHY: Eliminates HTTP overhead for in-process events while maintaining external API support.
"""

import asyncio
import weakref
from datetime import datetime
from typing import Any, Dict, Optional, Set

import aiohttp

from ...core.logging_config import get_logger


class AsyncEventEmitter:
    """High-performance async event emitter with direct calls and connection pooling."""

    _instance: Optional["AsyncEventEmitter"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """Initialize the event emitter."""
        self.logger = get_logger(__name__)

        # Direct emission targets (in-process)
        self._socketio_servers: Set[weakref.ref] = set()

        # HTTP connection pool for external requests
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._http_connector: Optional[aiohttp.TCPConnector] = None

        # Performance metrics
        self._direct_events = 0
        self._http_events = 0
        self._failed_events = 0

        # Event queue for batching (if needed)
        self._event_queue = asyncio.Queue(maxsize=10000)
        self._batch_processor_task: Optional[asyncio.Task] = None

    @classmethod
    async def get_instance(cls) -> "AsyncEventEmitter":
        """Get singleton instance with async initialization."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    await cls._instance._initialize()
        return cls._instance

    async def _initialize(self):
        """Initialize async components."""
        try:
            # Create HTTP connection pool with optimized settings
            self._http_connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=20,  # Connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,  # Keep connections alive
                enable_cleanup_closed=True,
                force_close=False,  # Reuse connections
            )

            # Create session with timeout and connection pooling
            timeout = aiohttp.ClientTimeout(
                total=5.0,  # Total timeout
                connect=1.0,  # Connection timeout
                sock_read=2.0,  # Socket read timeout
            )

            self._http_session = aiohttp.ClientSession(
                connector=self._http_connector,
                timeout=timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Claude-MPM-EventEmitter/1.0",
                },
            )

            self.logger.info("AsyncEventEmitter initialized with connection pooling")

        except Exception as e:
            self.logger.error(f"Error initializing AsyncEventEmitter: {e}")
            raise

    def register_socketio_server(self, sio_server):
        """Register a Socket.IO server for direct event emission."""
        # Use weak reference to avoid circular references
        weak_ref = weakref.ref(sio_server)
        self._socketio_servers.add(weak_ref)
        self.logger.debug(f"Registered Socket.IO server: {id(sio_server)}")

    def unregister_socketio_server(self, sio_server):
        """Unregister a Socket.IO server."""
        to_remove = []
        for weak_ref in self._socketio_servers:
            if weak_ref() is sio_server or weak_ref() is None:
                to_remove.append(weak_ref)

        for weak_ref in to_remove:
            self._socketio_servers.discard(weak_ref)

        self.logger.debug(f"Unregistered Socket.IO server: {id(sio_server)}")

    async def emit_event(
        self,
        namespace: str,
        event: str,
        data: Dict[str, Any],
        force_http: bool = False,
        endpoint: str = None,
    ) -> bool:
        """
        Emit event with optimal routing (direct calls vs HTTP).

        Args:
            namespace: Event namespace (e.g., 'hook')
            event: Event name (e.g., 'claude_event')
            data: Event data
            force_http: Force HTTP emission even if direct emission available
            endpoint: HTTP endpoint URL (defaults to localhost:8765)

        Returns:
            True if event was emitted successfully
        """
        try:
            # Clean up dead weak references
            self._cleanup_dead_references()

            # Try direct emission first (unless forced to use HTTP)
            if not force_http and self._socketio_servers:
                success = await self._emit_direct(event, data)
                if success:
                    self._direct_events += 1
                    return True

            # Fallback to HTTP emission
            if endpoint or not self._socketio_servers:
                success = await self._emit_http(namespace, event, data, endpoint)
                if success:
                    self._http_events += 1
                    return True

            self._failed_events += 1
            return False

        except Exception as e:
            self.logger.error(f"Error emitting event {event}: {e}")
            self._failed_events += 1
            return False

    async def _emit_direct(self, event: str, data: Dict[str, Any]) -> bool:
        """Emit event directly to registered Socket.IO servers."""
        success_count = 0

        for weak_ref in list(
            self._socketio_servers
        ):  # Copy to avoid modification during iteration
            sio_server = weak_ref()
            if sio_server is None:
                continue  # Will be cleaned up later

            try:
                # Direct async call to Socket.IO server
                await sio_server.emit(event, data)
                success_count += 1

            except Exception as e:
                self.logger.warning(
                    f"Direct emission failed for server {id(sio_server)}: {e}"
                )

        if success_count > 0:
            self.logger.debug(
                f"Direct emission successful to {success_count} servers: {event}"
            )
            return True

        return False

    async def _emit_http(
        self, namespace: str, event: str, data: Dict[str, Any], endpoint: str = None
    ) -> bool:
        """Emit event via HTTP with connection pooling."""
        if not self._http_session:
            self.logger.warning("HTTP session not initialized")
            return False

        url = endpoint or "http://localhost:8765/api/events"

        payload = {
            "namespace": namespace,
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "source": "async_emitter",
        }

        try:
            async with self._http_session.post(url, json=payload) as response:
                if response.status in [200, 204]:
                    self.logger.debug(f"HTTP emission successful: {event}")
                    return True
                self.logger.warning(
                    f"HTTP emission failed with status {response.status}: {event}"
                )
                return False

        except asyncio.TimeoutError:
            self.logger.warning(f"HTTP emission timeout: {event}")
            return False
        except aiohttp.ClientError as e:
            self.logger.warning(f"HTTP emission client error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"HTTP emission unexpected error: {e}")
            return False

    def _cleanup_dead_references(self):
        """Clean up dead weak references."""
        to_remove = []
        for weak_ref in self._socketio_servers:
            if weak_ref() is None:
                to_remove.append(weak_ref)

        for weak_ref in to_remove:
            self._socketio_servers.discard(weak_ref)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "direct_events": self._direct_events,
            "http_events": self._http_events,
            "failed_events": self._failed_events,
            "registered_servers": len(
                [ref for ref in self._socketio_servers if ref() is not None]
            ),
            "connection_pool_size": (
                self._http_connector.limit if self._http_connector else 0
            ),
            "active_connections": (
                len(self._http_connector._conns) if self._http_connector else 0
            ),
        }

    async def close(self):
        """Clean up resources with proper order and timing."""
        try:
            # Cancel batch processor if running
            if self._batch_processor_task and not self._batch_processor_task.done():
                self._batch_processor_task.cancel()
                try:
                    await self._batch_processor_task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.logger.debug(f"Error cancelling batch processor: {e}")
                finally:
                    self._batch_processor_task = None

            # Clear Socket.IO server references first
            # This prevents any new events from being emitted
            self._socketio_servers.clear()

            # Close HTTP session (must be done before connector)
            if self._http_session:
                try:
                    # Cancel any pending requests
                    if (
                        hasattr(self._http_session, "_connector")
                        and self._http_session._connector
                    ):
                        # Give ongoing requests a moment to complete
                        await asyncio.sleep(0.1)

                    # Close the session
                    await self._http_session.close()

                    # CRITICAL: Wait for session to fully close
                    # This prevents the "I/O operation on closed kqueue" error
                    await asyncio.sleep(0.25)

                except Exception as e:
                    self.logger.debug(f"Error closing HTTP session: {e}")
                finally:
                    self._http_session = None

            # Then close the connector (after session is fully closed)
            if self._http_connector:
                try:
                    # Close the connector
                    await self._http_connector.close()

                    # Give the connector adequate time to close all connections
                    # This is critical for preventing kqueue errors
                    await asyncio.sleep(0.5)

                except Exception as e:
                    self.logger.debug(f"Error closing HTTP connector: {e}")
                finally:
                    self._http_connector = None

            # Reset singleton instance
            AsyncEventEmitter._instance = None

            self.logger.info("AsyncEventEmitter closed successfully")

        except Exception as e:
            self.logger.error(f"Error closing AsyncEventEmitter: {e}")
        finally:
            # Ensure references are cleared even if errors occur
            self._http_session = None
            self._http_connector = None
            self._socketio_servers.clear()
            AsyncEventEmitter._instance = None


# Global instance for easy access
_global_emitter: Optional[AsyncEventEmitter] = None


async def get_event_emitter() -> AsyncEventEmitter:
    """Get the global event emitter instance."""
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = await AsyncEventEmitter.get_instance()
    return _global_emitter


async def cleanup_event_emitter():
    """Clean up the global event emitter instance."""
    global _global_emitter
    if _global_emitter is not None:
        await _global_emitter.close()
        _global_emitter = None
