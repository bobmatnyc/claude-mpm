"""
Test Socket.IO Manager Integration with Run Command
====================================================

WHY: Verify that the SocketIOManager service is properly integrated with
the run command and that the refactoring maintains functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from claude_mpm.cli.commands.run import RunCommand
from claude_mpm.services.cli.socketio_manager import ServerInfo


class TestRunSocketIOIntegration:
    """Test SocketIOManager integration with RunCommand."""
    
    @pytest.fixture
    def run_command(self):
        """Create a RunCommand instance."""
        return RunCommand()
    
    @patch('claude_mpm.cli.commands.run.SocketIOManager')
    @patch('claude_mpm.cli.commands.run.DashboardLauncher')
    def test_setup_monitoring_with_socketio_manager(self, mock_dashboard, mock_socketio_class, run_command):
        """Test that _setup_monitoring uses SocketIOManager correctly."""
        # Setup mocks
        mock_socketio = Mock()
        mock_socketio_class.return_value = mock_socketio
        
        mock_socketio.ensure_dependencies.return_value = (True, None)
        mock_socketio.find_available_port.return_value = 8765
        mock_socketio.start_server.return_value = (True, ServerInfo(
            port=8765,
            pid=12345,
            is_running=True,
            launch_time=None,
            url="http://localhost:8765"
        ))
        
        mock_dashboard_instance = Mock()
        mock_dashboard.return_value = mock_dashboard_instance
        mock_dashboard_instance.get_dashboard_url.return_value = "http://localhost:8765"
        mock_dashboard_instance._open_browser.return_value = True
        
        # Create args with monitor mode
        args = Mock()
        args.monitor = True
        
        # Call _setup_monitoring
        monitor_mode, websocket_port = run_command._setup_monitoring(args)
        
        # Verify
        assert monitor_mode is True
        assert websocket_port == 8765
        
        # Verify SocketIOManager was used correctly
        mock_socketio_class.assert_called_once()
        mock_socketio.ensure_dependencies.assert_called_once()
        mock_socketio.find_available_port.assert_called_once_with(8765)
        mock_socketio.start_server.assert_called_once_with(port=8765)
        
        # Verify DashboardLauncher was used for browser
        mock_dashboard_instance.get_dashboard_url.assert_called_once_with(8765)
        mock_dashboard_instance._open_browser.assert_called_once()
    
    @patch('claude_mpm.cli.commands.run.SocketIOManager')
    def test_setup_monitoring_dependency_failure(self, mock_socketio_class, run_command):
        """Test monitoring disabled when dependencies missing."""
        # Setup mocks
        mock_socketio = Mock()
        mock_socketio_class.return_value = mock_socketio
        
        mock_socketio.ensure_dependencies.return_value = (False, "Dependencies missing")
        
        # Create args with monitor mode
        args = Mock()
        args.monitor = True
        
        # Call _setup_monitoring
        monitor_mode, websocket_port = run_command._setup_monitoring(args)
        
        # Verify monitor mode disabled
        assert monitor_mode is False
        assert websocket_port == 8765  # Default port
        
        # Verify no server start attempted
        assert not mock_socketio.start_server.called
    
    @patch('claude_mpm.cli.commands.run.SocketIOManager')
    @patch('claude_mpm.cli.commands.run.DashboardLauncher')
    def test_setup_monitoring_server_start_failure(self, mock_dashboard, mock_socketio_class, run_command):
        """Test monitoring disabled when server fails to start."""
        # Setup mocks
        mock_socketio = Mock()
        mock_socketio_class.return_value = mock_socketio
        
        mock_socketio.ensure_dependencies.return_value = (True, None)
        mock_socketio.find_available_port.return_value = 8766
        mock_socketio.start_server.return_value = (False, ServerInfo(
            port=8766,
            pid=None,
            is_running=False,
            launch_time=None,
            url="http://localhost:8766"
        ))
        
        # Create args with monitor mode
        args = Mock()
        args.monitor = True
        
        # Call _setup_monitoring
        monitor_mode, websocket_port = run_command._setup_monitoring(args)
        
        # Verify monitor mode disabled
        assert monitor_mode is False
        assert websocket_port == 8766  # Port that was attempted
        
        # Verify server start was attempted
        mock_socketio.start_server.assert_called_once_with(port=8766)
        
        # Verify browser not opened
        assert not mock_dashboard.return_value._open_browser.called
    
    @patch('claude_mpm.cli.commands.run.SocketIOManager')
    @patch('claude_mpm.cli.commands.run.DashboardLauncher')
    def test_setup_monitoring_browser_not_opened(self, mock_dashboard, mock_socketio_class, run_command):
        """Test handling when browser fails to open."""
        # Setup mocks
        mock_socketio = Mock()
        mock_socketio_class.return_value = mock_socketio
        
        mock_socketio.ensure_dependencies.return_value = (True, None)
        mock_socketio.find_available_port.return_value = 8765
        mock_socketio.start_server.return_value = (True, ServerInfo(
            port=8765,
            pid=12345,
            is_running=True,
            launch_time=None,
            url="http://localhost:8765"
        ))
        
        mock_dashboard_instance = Mock()
        mock_dashboard.return_value = mock_dashboard_instance
        mock_dashboard_instance.get_dashboard_url.return_value = "http://localhost:8765"
        mock_dashboard_instance._open_browser.return_value = False  # Browser failed
        
        # Create args with monitor mode
        args = Mock()
        args.monitor = True
        
        # Capture print output
        with patch('builtins.print') as mock_print:
            # Call _setup_monitoring
            monitor_mode, websocket_port = run_command._setup_monitoring(args)
        
        # Verify monitor mode still enabled (server is running)
        assert monitor_mode is True
        assert websocket_port == 8765
        
        # Verify browser open was attempted
        mock_dashboard_instance._open_browser.assert_called_once()
        
        # Verify URL was printed for manual access
        mock_print.assert_called()
        print_args = str(mock_print.call_args)
        assert "http://localhost:8765" in print_args
    
    def test_setup_monitoring_no_monitor_mode(self, run_command):
        """Test setup_monitoring when monitor mode is disabled."""
        # Create args without monitor mode
        args = Mock()
        args.monitor = False
        
        # Call _setup_monitoring
        monitor_mode, websocket_port = run_command._setup_monitoring(args)
        
        # Verify defaults
        assert monitor_mode is False
        assert websocket_port == 8765  # Default port


class TestLegacySocketIOFunctions:
    """Test legacy helper functions still work."""
    
    @patch('claude_mpm.cli.commands.run.SocketIOManager')
    @patch('claude_mpm.cli.commands.run.DashboardLauncher')
    def test_launch_socketio_monitor_legacy(self, mock_dashboard_class, mock_socketio_class):
        """Test legacy launch_socketio_monitor function."""
        from claude_mpm.cli.commands.run import launch_socketio_monitor
        
        # Setup mocks
        mock_socketio = Mock()
        mock_socketio_class.return_value = mock_socketio
        mock_socketio.start_server.return_value = (True, ServerInfo(
            port=8765,
            pid=12345,
            is_running=True,
            launch_time=None,
            url="http://localhost:8765"
        ))
        
        mock_dashboard = Mock()
        mock_dashboard_class.return_value = mock_dashboard
        mock_dashboard._open_browser.return_value = True
        
        # Call legacy function
        logger = Mock()
        success, browser_opened = launch_socketio_monitor(8765, logger)
        
        # Verify
        assert success is True
        assert browser_opened is True
        mock_socketio.start_server.assert_called_once_with(port=8765)
        mock_dashboard._open_browser.assert_called_once()
    
    @patch('claude_mpm.cli.commands.run.SocketIOManager')
    def test_check_socketio_server_running_legacy(self, mock_socketio_class):
        """Test legacy _check_socketio_server_running function."""
        from claude_mpm.cli.commands.run import _check_socketio_server_running
        
        # Setup mocks
        mock_socketio = Mock()
        mock_socketio_class.return_value = mock_socketio
        mock_socketio.is_server_running.return_value = True
        
        # Call legacy function
        logger = Mock()
        is_running = _check_socketio_server_running(8765, logger)
        
        # Verify
        assert is_running is True
        mock_socketio.is_server_running.assert_called_once_with(8765)
    
    @patch('claude_mpm.cli.commands.run.SocketIOManager')
    def test_start_standalone_socketio_server_legacy(self, mock_socketio_class):
        """Test legacy _start_standalone_socketio_server function."""
        from claude_mpm.cli.commands.run import _start_standalone_socketio_server
        
        # Setup mocks
        mock_socketio = Mock()
        mock_socketio_class.return_value = mock_socketio
        mock_socketio.start_server.return_value = (True, ServerInfo(
            port=8765,
            pid=12345,
            is_running=True,
            launch_time=None,
            url="http://localhost:8765"
        ))
        
        # Call legacy function
        logger = Mock()
        success = _start_standalone_socketio_server(8765, logger)
        
        # Verify
        assert success is True
        mock_socketio.start_server.assert_called_once_with(port=8765)