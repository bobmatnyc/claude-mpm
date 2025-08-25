"""
Tests for Socket.IO Manager Service
====================================

WHY: Comprehensive test coverage for the SocketIOManager service to ensure reliable
Socket.IO server lifecycle management.

COVERAGE:
- Server starting and stopping
- Port finding and availability
- Server status checking
- Process management
- Error handling (port conflicts, process failures)
- Graceful shutdown
- Dependency checking
"""

import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, PropertyMock

import pytest

from claude_mpm.services.cli.socketio_manager import (
    ISocketIOManager,
    SocketIOManager,
    ServerInfo
)


class TestSocketIOManagerInterface:
    """Test that SocketIOManager implements ISocketIOManager interface correctly."""
    
    def test_implements_interface(self):
        """Verify SocketIOManager implements all required interface methods."""
        manager = SocketIOManager()
        assert isinstance(manager, ISocketIOManager)
        
        # Check all interface methods are implemented
        assert hasattr(manager, 'start_server')
        assert hasattr(manager, 'stop_server')
        assert hasattr(manager, 'is_server_running')
        assert hasattr(manager, 'get_server_info')
        assert hasattr(manager, 'wait_for_server')
        assert hasattr(manager, 'find_available_port')
        assert hasattr(manager, 'ensure_dependencies')


class TestSocketIOManagerStartStop:
    """Test server starting and stopping functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a SocketIOManager instance with mocked logger."""
        with patch('claude_mpm.services.cli.socketio_manager.get_logger') as mock_logger:
            manager = SocketIOManager()
            manager.logger = Mock()
            return manager
    
    @patch('claude_mpm.services.cli.socketio_manager.subprocess.Popen')
    @patch('claude_mpm.services.cli.socketio_manager.get_scripts_dir')
    @patch('claude_mpm.services.cli.socketio_manager.get_package_root')
    def test_start_server_success(self, mock_pkg_root, mock_scripts_dir, mock_popen, manager):
        """Test successful server startup."""
        # Setup mocks
        mock_pkg_root.return_value = Path("/fake/package")
        mock_scripts_dir.return_value = Path("/fake/scripts")
        
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Mock dependency check
        manager.ensure_dependencies = Mock(return_value=(True, None))
        
        # Mock port availability
        manager.find_available_port = Mock(return_value=8765)
        manager.is_server_running = Mock(return_value=False)
        manager.wait_for_server = Mock(return_value=True)
        
        # Mock get_server_info to return running server
        manager.get_server_info = Mock(return_value=ServerInfo(
            port=8765,
            pid=12345,
            is_running=True,
            launch_time=time.time(),
            url="http://localhost:8765"
        ))
        
        # Mock daemon script exists
        with patch('pathlib.Path.exists', return_value=True):
            # Start server
            success, info = manager.start_server(port=8765, timeout=5)
        
        # Verify
        assert success is True
        assert info.port == 8765
        assert info.is_running is True
        manager.ensure_dependencies.assert_called_once()
        manager.wait_for_server.assert_called_once_with(8765, 5)
    
    @patch('claude_mpm.services.cli.socketio_manager.subprocess.Popen')
    def test_start_server_already_running(self, mock_popen, manager):
        """Test starting server when already running on port."""
        # Mock server already running
        manager.is_server_running = Mock(return_value=True)
        manager.get_server_info = Mock(return_value=ServerInfo(
            port=8765,
            pid=12345,
            is_running=True,
            launch_time=time.time(),
            url="http://localhost:8765"
        ))
        
        # Start server
        success, info = manager.start_server(port=8765)
        
        # Verify
        assert success is True
        assert info.port == 8765
        assert info.is_running is True
        mock_popen.assert_not_called()  # Should not start new process
    
    def test_start_server_dependency_failure(self, manager):
        """Test server start fails when dependencies missing."""
        # Mock dependency check failure
        manager.ensure_dependencies = Mock(return_value=(False, "Dependencies missing"))
        manager.is_server_running = Mock(return_value=False)
        manager.find_available_port = Mock(return_value=8765)
        
        # Start server
        success, info = manager.start_server(port=8765)
        
        # Verify
        assert success is False
        assert info.is_running is False
        assert info.port == 8765
    
    @patch('claude_mpm.services.cli.socketio_manager.subprocess.Popen')
    @patch('claude_mpm.services.cli.socketio_manager.get_scripts_dir')
    def test_start_server_script_not_found(self, mock_scripts_dir, mock_popen, manager):
        """Test server start fails when daemon script not found."""
        # Setup mocks
        mock_scripts_dir.return_value = Path("/fake/scripts")
        
        # Mock dependencies OK, server not running
        manager.ensure_dependencies = Mock(return_value=(True, None))
        manager.is_server_running = Mock(return_value=False)
        manager.find_available_port = Mock(return_value=8765)
        
        # Mock daemon script doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            # Start server
            success, info = manager.start_server(port=8765)
        
        # Verify
        assert success is False
        assert info.is_running is False
        mock_popen.assert_not_called()
    
    def test_stop_server_managed_process(self, manager):
        """Test stopping a managed server process."""
        # Setup mock process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        
        manager._server_processes[8765] = mock_process
        
        # Stop server
        success = manager.stop_server(port=8765, timeout=5)
        
        # Verify
        assert success is True
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        assert 8765 not in manager._server_processes
    
    def test_stop_server_force_kill(self, manager):
        """Test force killing server when graceful shutdown fails."""
        # Setup mock process that won't terminate gracefully
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.terminate = Mock()
        # First wait() throws timeout, second wait() after kill succeeds
        mock_process.wait = Mock(side_effect=[subprocess.TimeoutExpired("cmd", 5), None])
        mock_process.kill = Mock()
        
        manager._server_processes[8765] = mock_process
        
        # Stop server
        success = manager.stop_server(port=8765, timeout=5)
        
        # Verify
        assert success is True
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert mock_process.wait.call_count == 2  # Called twice: after terminate and after kill
        assert 8765 not in manager._server_processes
    
    @patch('claude_mpm.services.cli.socketio_manager.os.kill')
    def test_stop_server_external_process(self, mock_kill, manager):
        """Test stopping an external server process."""
        # Mock external process info
        mock_process_info = Mock()
        mock_process_info.pid = 12345
        mock_process_info.is_ours = True
        
        manager.port_manager.get_process_on_port = Mock(return_value=mock_process_info)
        
        # Stop server
        success = manager.stop_server(port=8765)
        
        # Verify
        assert success is True
        mock_kill.assert_any_call(12345, signal.SIGTERM)
    
    def test_stop_all_servers(self, manager):
        """Test stopping all managed servers."""
        # Setup multiple mock processes
        mock_process1 = Mock()
        mock_process1.poll.return_value = None
        mock_process1.terminate = Mock()
        mock_process1.wait = Mock()
        
        mock_process2 = Mock()
        mock_process2.poll.return_value = None
        mock_process2.terminate = Mock()
        mock_process2.wait = Mock()
        
        manager._server_processes[8765] = mock_process1
        manager._server_processes[8766] = mock_process2
        
        # Stop all servers
        success = manager.stop_server()  # No port specified
        
        # Verify
        assert success is True
        mock_process1.terminate.assert_called_once()
        mock_process2.terminate.assert_called_once()
        assert len(manager._server_processes) == 0


class TestSocketIOManagerStatus:
    """Test server status checking functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a SocketIOManager instance."""
        with patch('claude_mpm.services.cli.socketio_manager.get_logger'):
            return SocketIOManager()
    
    def test_is_server_running_managed_process(self, manager):
        """Test checking if managed server is running."""
        # Setup mock process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        
        manager._server_processes[8765] = mock_process
        
        # Check status
        is_running = manager.is_server_running(8765)
        
        # Verify
        assert is_running is True
    
    def test_is_server_running_terminated_process(self, manager):
        """Test checking terminated managed process."""
        # Setup mock terminated process
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process terminated
        
        manager._server_processes[8765] = mock_process
        
        # Mock port manager to return no process (since we're cleaning up)
        manager.port_manager.get_process_on_port = Mock(return_value=None)
        
        # Check status
        is_running = manager.is_server_running(8765)
        
        # Verify
        assert is_running is False
        # Process should be cleaned up
        assert 8765 not in manager._server_processes
    
    def test_is_server_running_external_socketio(self, manager):
        """Test detecting external Socket.IO server."""
        # Mock external process info
        mock_process_info = Mock()
        mock_process_info.cmdline = "python socketio_server.py"
        mock_process_info.is_daemon = False
        
        manager.port_manager.get_process_on_port = Mock(return_value=mock_process_info)
        
        # Check status
        is_running = manager.is_server_running(8765)
        
        # Verify
        assert is_running is True
    
    def test_is_server_running_daemon_process(self, manager):
        """Test detecting daemon process."""
        # Mock daemon process info
        mock_process_info = Mock()
        mock_process_info.cmdline = "some_daemon"
        mock_process_info.is_daemon = True
        
        manager.port_manager.get_process_on_port = Mock(return_value=mock_process_info)
        
        # Check status
        is_running = manager.is_server_running(8765)
        
        # Verify
        assert is_running is True
    
    def test_get_server_info_running(self, manager):
        """Test getting info for running server."""
        # Mock running server
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        
        manager._server_processes[8765] = mock_process
        manager.is_server_running = Mock(return_value=True)
        
        # Get info
        info = manager.get_server_info(8765)
        
        # Verify
        assert info.port == 8765
        assert info.pid == 12345
        assert info.is_running is True
        assert info.url == "http://localhost:8765"
    
    def test_get_server_info_not_running(self, manager):
        """Test getting info for non-running server."""
        # Mock no server
        manager.is_server_running = Mock(return_value=False)
        
        # Get info
        info = manager.get_server_info(8765)
        
        # Verify
        assert info.port == 8765
        assert info.pid is None
        assert info.is_running is False
        assert info.launch_time is None


class TestSocketIOManagerPortManagement:
    """Test port management functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a SocketIOManager instance."""
        with patch('claude_mpm.services.cli.socketio_manager.get_logger'):
            return SocketIOManager()
    
    def test_find_available_port_preferred_available(self, manager):
        """Test finding port when preferred is available."""
        # Mock preferred port available
        manager.port_manager.is_port_available = Mock(return_value=True)
        
        # Find port
        port = manager.find_available_port(preferred_port=8765)
        
        # Verify
        assert port == 8765
        manager.port_manager.is_port_available.assert_called_once_with(8765)
    
    def test_find_available_port_alternative(self, manager):
        """Test finding alternative port when preferred unavailable."""
        # Mock preferred port unavailable
        manager.port_manager.is_port_available = Mock(return_value=False)
        manager.port_manager.get_available_port = Mock(return_value=8766)
        
        # Find port
        port = manager.find_available_port(preferred_port=8765)
        
        # Verify
        assert port == 8766
        manager.port_manager.get_available_port.assert_called_once_with(8765)
    
    @patch('claude_mpm.services.cli.socketio_manager.socket.socket')
    @patch('claude_mpm.services.cli.socketio_manager.time.time')
    @patch('claude_mpm.services.cli.socketio_manager.time.sleep')
    def test_wait_for_server_success(self, mock_sleep, mock_time, mock_socket_class, manager):
        """Test waiting for server to be ready."""
        # Mock time progression
        mock_time.side_effect = [0, 0.5, 1.0]  # Start, first check, second check
        
        # Mock socket connection
        mock_socket = Mock()
        mock_socket.__enter__ = Mock(return_value=mock_socket)
        mock_socket.__exit__ = Mock(return_value=None)
        mock_socket.connect_ex.side_effect = [1, 0]  # First fails, second succeeds
        mock_socket_class.return_value = mock_socket
        
        # Wait for server
        ready = manager.wait_for_server(8765, timeout=30)
        
        # Verify
        assert ready is True
        assert mock_socket.connect_ex.call_count == 2
    
    @patch('claude_mpm.services.cli.socketio_manager.socket.socket')
    @patch('claude_mpm.services.cli.socketio_manager.time.time')
    @patch('claude_mpm.services.cli.socketio_manager.time.sleep')
    def test_wait_for_server_timeout(self, mock_sleep, mock_time, mock_socket_class, manager):
        """Test waiting for server timeout."""
        # Mock time progression past timeout
        mock_time.side_effect = [0, 15, 31]  # Start, mid-check, past timeout
        
        # Mock socket always fails to connect
        mock_socket = Mock()
        mock_socket.__enter__ = Mock(return_value=mock_socket)
        mock_socket.__exit__ = Mock(return_value=None)
        mock_socket.connect_ex.return_value = 1  # Connection refused
        mock_socket_class.return_value = mock_socket
        
        # Wait for server
        ready = manager.wait_for_server(8765, timeout=30)
        
        # Verify
        assert ready is False


class TestSocketIOManagerDependencies:
    """Test dependency management functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a SocketIOManager instance."""
        with patch('claude_mpm.services.cli.socketio_manager.get_logger'):
            return SocketIOManager()
    
    @patch('claude_mpm.services.cli.socketio_manager.ensure_socketio_dependencies')
    def test_ensure_dependencies_success(self, mock_ensure_deps, manager):
        """Test successful dependency check."""
        # Mock dependencies available
        mock_ensure_deps.return_value = (True, None)
        
        # Check dependencies
        success, error_msg = manager.ensure_dependencies()
        
        # Verify
        assert success is True
        assert error_msg is None
        mock_ensure_deps.assert_called_once()
    
    @patch('claude_mpm.services.cli.socketio_manager.ensure_socketio_dependencies')
    def test_ensure_dependencies_failure(self, mock_ensure_deps, manager):
        """Test dependency check failure."""
        # Mock dependencies missing
        mock_ensure_deps.return_value = (False, "Package not found")
        
        # Check dependencies
        success, error_msg = manager.ensure_dependencies()
        
        # Verify
        assert success is False
        assert "Package not found" in error_msg
    
    @patch('claude_mpm.services.cli.socketio_manager.ensure_socketio_dependencies')
    def test_ensure_dependencies_exception(self, mock_ensure_deps, manager):
        """Test dependency check exception handling."""
        # Mock exception
        mock_ensure_deps.side_effect = Exception("Import error")
        
        # Check dependencies
        success, error_msg = manager.ensure_dependencies()
        
        # Verify
        assert success is False
        assert "Import error" in error_msg


class TestSocketIOManagerConcurrency:
    """Test thread-safety and concurrency handling."""
    
    @pytest.fixture
    def manager(self):
        """Create a SocketIOManager instance."""
        with patch('claude_mpm.services.cli.socketio_manager.get_logger'):
            return SocketIOManager()
    
    def test_concurrent_start_stop(self, manager):
        """Test concurrent start/stop operations are thread-safe."""
        # Mock methods to be fast
        manager.is_server_running = Mock(return_value=False)
        manager.ensure_dependencies = Mock(return_value=(True, None))
        manager.find_available_port = Mock(return_value=8765)
        manager.wait_for_server = Mock(return_value=True)
        
        results = []
        
        def start_server():
            with patch('claude_mpm.services.cli.socketio_manager.subprocess.Popen'):
                with patch('pathlib.Path.exists', return_value=True):
                    success, _ = manager.start_server(8765)
                    results.append(('start', success))
        
        def stop_server():
            success = manager.stop_server(8765)
            results.append(('stop', success))
        
        # Create threads
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=start_server))
            threads.append(threading.Thread(target=stop_server))
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=2)
        
        # Verify no crashes and operations completed
        assert len(results) == 10  # All operations completed
    
    def test_cleanup_process_thread_safe(self, manager):
        """Test cleanup_process is thread-safe."""
        # Add mock processes
        for port in range(8765, 8770):
            mock_process = Mock()
            mock_process.poll.return_value = 0  # Terminated
            mock_process.kill = Mock()
            mock_process.wait = Mock()
            manager._server_processes[port] = mock_process
        
        # Concurrent cleanup
        threads = []
        for port in range(8765, 8770):
            t = threading.Thread(target=manager._cleanup_process, args=(port,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=1)
        
        # Verify all cleaned up
        assert len(manager._server_processes) == 0


class TestSocketIOManagerIntegration:
    """Integration tests with real components where feasible."""
    
    @pytest.fixture
    def manager(self):
        """Create a real SocketIOManager instance."""
        return SocketIOManager()
    
    def test_port_availability_check(self, manager):
        """Test real port availability checking."""
        # This test uses real socket operations
        # Find a likely available port in test range
        test_port = 59999  # High port unlikely to be used
        
        # Check if we can actually bind to it
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(('localhost', test_port))
                # Port is available
                available = manager.port_manager.is_port_available(test_port)
                assert available is False  # Should be False while we hold it
        except OSError:
            # Port already in use, skip test
            pytest.skip("Test port already in use")
        
        # Now check again after releasing
        available = manager.port_manager.is_port_available(test_port)
        # Should be True now (unless another process grabbed it)
    
    @patch('claude_mpm.services.cli.socketio_manager.ensure_socketio_dependencies')
    def test_dependency_check_integration(self, mock_ensure_deps, manager):
        """Test dependency checking integration."""
        # Test with actual dependency manager behavior
        mock_ensure_deps.return_value = (False, "python-socketio not installed")
        
        # Mock server is not running
        manager.is_server_running = Mock(return_value=False)
        manager.find_available_port = Mock(return_value=8765)
        
        # Start server should fail due to missing dependencies
        success, info = manager.start_server(8765)
        
        assert success is False
        assert not info.is_running
        mock_ensure_deps.assert_called()