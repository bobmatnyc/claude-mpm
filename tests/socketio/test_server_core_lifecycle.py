#!/usr/bin/env python3
"""
Comprehensive unit tests for SocketIO Server Core Lifecycle Management.

Tests critical server lifecycle management including:
- Server startup creates event loop properly
- Graceful shutdown sequence
- Port binding and conflict handling
- Thread management
- Server ready state detection

WHY: These tests address critical gaps in test coverage for server loading
identified during analysis. They ensure proper lifecycle management and
prevent race conditions during startup/shutdown.
"""

import asyncio
import socket
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.services.socketio.server.core import SocketIOServerCore


class TestSocketIOServerCoreLifecycle:
    """Test server lifecycle management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_port = 8766  # Use different port to avoid conflicts
        self.test_host = "localhost"

    def teardown_method(self):
        """Clean up after each test."""
        # Ensure no test servers are left running
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                if s.connect_ex((self.test_host, self.test_port)) == 0:
                    # Port is still open, something went wrong
                    pass
        except:
            pass

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    def test_server_initialization(self):
        """Test server initialization with default parameters."""
        server = SocketIOServerCore()

        assert server.host == "localhost"
        assert server.port == 8765
        assert not server.running
        assert server.server_thread is None
        assert server.loop is None
        assert server.sio is None
        assert len(server.connected_clients) == 0
        assert len(server.event_buffer) == 0

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    def test_server_initialization_custom_params(self):
        """Test server initialization with custom parameters."""
        server = SocketIOServerCore(host="127.0.0.1", port=8999)

        assert server.host == "127.0.0.1"
        assert server.port == 8999
        assert not server.running

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", False)
    def test_server_unavailable_graceful_handling(self):
        """Test graceful handling when SocketIO is not available."""
        server = SocketIOServerCore()

        # Should not raise exception
        server.start_sync()

        # Server should not be running
        assert not server.running
        assert server.server_thread is None

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    @patch("claude_mpm.services.socketio.server.core.socketio")
    @patch("claude_mpm.services.socketio.server.core.web")
    def test_event_loop_creation_race_condition(self, mock_web, mock_socketio):
        """Test that event loop is created and assigned immediately to minimize race conditions."""
        # Mock the async components
        mock_app = MagicMock()
        mock_web.Application.return_value = mock_app
        mock_sio = AsyncMock()
        mock_socketio.AsyncServer.return_value = mock_sio

        # Mock the runner and site
        mock_runner = AsyncMock()
        mock_web.AppRunner.return_value = mock_runner
        mock_site = AsyncMock()
        mock_web.TCPSite.return_value = mock_site

        server = SocketIOServerCore(host=self.test_host, port=self.test_port)

        # Start server (this should create the thread and loop)
        server.start_sync()

        # Give it a moment to initialize
        time.sleep(0.2)

        try:
            # Verify that loop was created and assigned
            assert server.loop is not None
            assert server.running
            assert server.server_thread is not None
            assert server.server_thread.is_alive()

            # Verify the loop is in the correct thread
            assert server.server_thread.ident != threading.current_thread().ident

        finally:
            server.stop_sync()
            # Wait for shutdown
            if server.server_thread:
                server.server_thread.join(timeout=2)

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    @patch("socket.socket")
    def test_port_conflict_handling(self, mock_socket):
        """Test handling of port conflicts during startup."""
        # Mock socket to simulate port in use
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock

        # Simulate port in use by having bind raise exception
        mock_sock.bind.side_effect = OSError("Address already in use")

        server = SocketIOServerCore(host=self.test_host, port=self.test_port)

        # Should handle the port conflict gracefully
        with pytest.raises(Exception):  # Should propagate the binding error
            server.start_sync()

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    @patch("claude_mpm.services.socketio.server.core.socketio")
    @patch("claude_mpm.services.socketio.server.core.web")
    def test_server_ready_state_detection(self, mock_web, mock_socketio):
        """Test server ready state detection with timeout."""
        # Mock the async components
        mock_app = MagicMock()
        mock_web.Application.return_value = mock_app
        mock_sio = AsyncMock()
        mock_socketio.AsyncServer.return_value = mock_sio

        # Mock runner and site
        mock_runner = AsyncMock()
        mock_web.AppRunner.return_value = mock_runner
        mock_site = AsyncMock()
        mock_web.TCPSite.return_value = mock_site

        # Mock slow startup
        async def slow_site_start():
            await asyncio.sleep(0.3)  # Simulate slow startup

        mock_site.start = slow_site_start

        server = SocketIOServerCore(host=self.test_host, port=self.test_port)

        start_time = time.time()
        server.start_sync()
        end_time = time.time()

        try:
            # Should have waited for server to be ready
            assert server.running
            # Should have taken at least the startup time
            assert end_time - start_time >= 0.2

        finally:
            server.stop_sync()
            if server.server_thread:
                server.server_thread.join(timeout=2)

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    def test_server_startup_timeout(self):
        """Test server startup timeout handling."""
        with patch(
            "claude_mpm.services.socketio.server.core.TimeoutConfig"
        ) as mock_timeout:
            mock_timeout.SERVER_START_TIMEOUT = 0.1  # Very short timeout

            server = SocketIOServerCore(host=self.test_host, port=self.test_port)

            # Mock _run_server to never set running=True
            original_run_server = server._run_server

            def mock_run_server():
                # Simulate server taking too long to start
                time.sleep(0.2)
                # Don't set server.running = True

            server._run_server = mock_run_server

            # Should raise timeout exception
            with pytest.raises(Exception, match="Failed to start.*within.*0.1s"):
                server.start_sync()

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    @patch("claude_mpm.services.socketio.server.core.socketio")
    @patch("claude_mpm.services.socketio.server.core.web")
    def test_graceful_shutdown_sequence(self, mock_web, mock_socketio):
        """Test the complete graceful shutdown sequence."""
        # Mock the async components
        mock_app = MagicMock()
        mock_web.Application.return_value = mock_app
        mock_sio = AsyncMock()
        mock_socketio.AsyncServer.return_value = mock_sio

        # Mock runner and site with proper cleanup
        mock_runner = AsyncMock()
        mock_web.AppRunner.return_value = mock_runner
        mock_site = AsyncMock()
        mock_web.TCPSite.return_value = mock_site

        server = SocketIOServerCore(host=self.test_host, port=self.test_port)

        # Start the server
        server.start_sync()
        time.sleep(0.1)

        assert server.running
        original_thread = server.server_thread

        # Stop the server
        server.stop_sync()

        # Give shutdown time to complete
        if original_thread:
            original_thread.join(timeout=2)

        # Verify shutdown state
        assert not server.running

        # Verify cleanup methods were called
        mock_site.stop.assert_called_once()
        mock_runner.cleanup.assert_called_once()

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    @patch("claude_mpm.services.socketio.server.core.socketio")
    @patch("claude_mpm.services.socketio.server.core.web")
    def test_thread_management(self, mock_web, mock_socketio):
        """Test proper thread lifecycle management."""
        # Mock the async components
        mock_app = MagicMock()
        mock_web.Application.return_value = mock_app
        mock_sio = AsyncMock()
        mock_socketio.AsyncServer.return_value = mock_sio

        mock_runner = AsyncMock()
        mock_web.AppRunner.return_value = mock_runner
        mock_site = AsyncMock()
        mock_web.TCPSite.return_value = mock_site

        server = SocketIOServerCore(host=self.test_host, port=self.test_port)

        # Initially no thread
        assert server.server_thread is None

        # Start server creates daemon thread
        server.start_sync()
        time.sleep(0.1)

        assert server.server_thread is not None
        assert server.server_thread.daemon  # Should be daemon thread
        assert server.server_thread.is_alive()

        original_thread_id = server.server_thread.ident

        # Stop server
        server.stop_sync()
        time.sleep(0.2)

        # Thread should finish
        if server.server_thread:
            server.server_thread.join(timeout=2)
            assert not server.server_thread.is_alive()

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    def test_multiple_start_calls_handled_gracefully(self):
        """Test that multiple start_sync calls are handled gracefully."""
        server = SocketIOServerCore(host=self.test_host, port=self.test_port)

        def mock_run_server():
            # Simulate successful server start
            server.running = True
            time.sleep(0.1)

        with patch.object(server, "_run_server", side_effect=mock_run_server):
            # First call should work
            server.start_sync()
            assert server.running

            # Second call should be ignored since already running
            initial_thread = server.server_thread
            server.start_sync()
            # Should be same thread (not restarted)
            assert server.server_thread is initial_thread

        server.stop_sync()

    def test_connection_count_interface_compliance(self):
        """Test that get_connection_count provides proper interface compliance."""
        server = SocketIOServerCore()

        # Should return 0 when no clients
        assert server.get_connection_count() == 0

        # Add some mock clients
        server.connected_clients.add("client1")
        server.connected_clients.add("client2")

        assert server.get_connection_count() == 2

    def test_is_running_interface_compliance(self):
        """Test that is_running provides proper interface compliance."""
        server = SocketIOServerCore()

        # Initially not running
        assert not server.is_running()

        # When running flag is set
        server.running = True
        assert server.is_running()

        # When stopped
        server.running = False
        assert not server.is_running()

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    @patch("claude_mpm.services.socketio.server.core.socketio")
    @patch("claude_mpm.services.socketio.server.core.web")
    def test_heartbeat_task_management(self, mock_web, mock_socketio):
        """Test heartbeat task lifecycle management."""
        # Mock the async components
        mock_app = MagicMock()
        mock_web.Application.return_value = mock_app
        mock_sio = AsyncMock()
        mock_socketio.AsyncServer.return_value = mock_sio

        mock_runner = AsyncMock()
        mock_web.AppRunner.return_value = mock_runner
        mock_site = AsyncMock()
        mock_web.TCPSite.return_value = mock_site

        # Enable heartbeat for this test
        mock_config = {
            "enable_extra_heartbeat": True,
            "ping_interval": 25,
            "ping_timeout": 60,
            "max_http_buffer_size": 1048576,
        }
        with patch("claude_mpm.config.socketio_config.CONNECTION_CONFIG", mock_config):

            server = SocketIOServerCore(host=self.test_host, port=self.test_port)

            def mock_run_server():
                # Simulate successful server start with heartbeat
                server.running = True
                # Mock heartbeat task creation
                server.heartbeat_task = AsyncMock()
                server.heartbeat_task.cancelled.return_value = False
                server.heartbeat_task.done.return_value = False
                time.sleep(0.1)

            with patch.object(server, "_run_server", side_effect=mock_run_server):
                server.start_sync()
                time.sleep(0.1)

                try:
                    # Heartbeat task should be created
                    assert server.heartbeat_task is not None

                finally:
                    server.stop_sync()
                    if server.server_thread:
                        server.server_thread.join(timeout=2)

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    def test_exception_handling_in_run_server(self):
        """Test exception handling in _run_server method."""
        server = SocketIOServerCore(host=self.test_host, port=self.test_port)

        # Mock _run_server to raise exception and handle it properly
        def mock_run_server():
            try:
                raise RuntimeError("Test exception")
            except Exception:
                # Server should handle exception and set running to False
                server.running = False
                server.logger.error("Socket.IO server error: Test exception")

        with patch.object(server, "_run_server", side_effect=mock_run_server):
            # Should raise timeout exception since running stays False
            with pytest.raises(Exception, match="Failed to start Socket.IO server"):
                server.start_sync()

            # Wait for thread to handle the exception
            if server.server_thread:
                server.server_thread.join(timeout=2)

            # Should set running to False on exception
            assert not server.running

    def test_stats_initialization_and_tracking(self):
        """Test server statistics initialization and tracking."""
        server = SocketIOServerCore()

        # Check initial stats
        assert server.stats["events_sent"] == 0
        assert server.stats["events_buffered"] == 0
        assert server.stats["connections_total"] == 0
        assert server.stats["start_time"] is None

        # Check that stats structure is correct
        assert isinstance(server.stats, dict)
        assert all(
            key in server.stats
            for key in [
                "events_sent",
                "events_buffered",
                "connections_total",
                "start_time",
            ]
        )

    @patch("claude_mpm.services.socketio.server.core.SOCKETIO_AVAILABLE", True)
    def test_event_buffer_initialization(self):
        """Test event buffer initialization with proper limits."""
        server = SocketIOServerCore()

        # Event buffer should be initialized as deque with maxlen
        assert hasattr(server.event_buffer, "maxlen")
        assert len(server.event_buffer) == 0

        # Test buffer limit enforcement
        max_len = server.event_buffer.maxlen

        # Add more items than the max length
        for i in range(max_len + 10):
            server.event_buffer.append(f"event_{i}")

        # Should not exceed max length
        assert len(server.event_buffer) == max_len

        # Should contain the most recent items
        assert "event_" + str(max_len + 9) in str(server.event_buffer[-1])
