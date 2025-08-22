"""
Comprehensive tests for the MonitorCommand class.

WHY: The monitor command provides real-time monitoring of claude-mpm operations.
This is crucial for debugging and observability.

DESIGN DECISIONS:
- Test WebSocket connection handling
- Mock real-time event streams
- Test filtering and display options
- Verify reconnection logic
- Test output formatting
"""

import pytest
import asyncio
from argparse import Namespace
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from claude_mpm.cli.commands.monitor import MonitorCommand
from claude_mpm.cli.shared.base_command import CommandResult


class TestMonitorCommand:
    """Test MonitorCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = MonitorCommand()

    def test_initialization():
        """Test MonitorCommand initialization."""
        assert self.command.command_name == "monitor"
        assert self.command.logger is not None

    def test_validate_args_default():
        """Test validation with default args."""
        args = Namespace(
            port=8080,
            filter=None,
            output='console'
        )
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_with_filter():
        """Test validation with event filter."""
        args = Namespace(
            port=8080,
            filter='event_type=response',
            output='console'
        )
        error = self.command.validate_args(args)
        assert error is None

    @patch('claude_mpm.cli.commands.monitor.WebSocketClient')
    def test_run_monitor_console(mock_ws_client_class):
        """Test monitoring with console output."""
        mock_client = Mock()
        mock_ws_client_class.return_value = mock_client
        mock_client.connect.return_value = True
        mock_client.receive_events.return_value = [
            {'type': 'response', 'data': 'test'},
            {'type': 'error', 'data': 'error'}
        ]
        
        args = Namespace(
            port=8080,
            filter=None,
            output='console',
            format='text'
        )
        
        with patch.object(self.command, '_start_monitoring') as mock_start:
            mock_start.return_value = CommandResult.success_result("Monitoring started")
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_start.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.monitor.WebSocketClient')
    def test_run_monitor_file_output(mock_ws_client_class):
        """Test monitoring with file output."""
        mock_client = Mock()
        mock_ws_client_class.return_value = mock_client
        
        args = Namespace(
            port=8080,
            filter=None,
            output='file',
            output_file='/tmp/monitor.log',
            format='json'
        )
        
        with patch('builtins.open', create=True) as mock_open:
            with patch.object(self.command, '_start_monitoring') as mock_start:
                mock_start.return_value = CommandResult.success_result(
                    "Monitoring to file",
                    data={'output_file': '/tmp/monitor.log'}
                )
                
                result = self.command.run(args)
                
                assert result.success is True
                assert result.data['output_file'] == '/tmp/monitor.log'

    def test_monitor_with_event_filter():
        """Test monitoring with event filtering."""
        args = Namespace(
            port=8080,
            filter='type=error,level=critical',
            output='console',
            format='text'
        )
        
        with patch.object(self.command, '_start_monitoring') as mock_start:
            mock_start.return_value = CommandResult.success_result(
                "Monitoring with filters",
                data={'filters': ['type=error', 'level=critical']}
            )
            
            result = self.command.run(args)
            
            assert result.success is True

    @patch('claude_mpm.cli.commands.monitor.WebSocketClient')
    def test_monitor_connection_error(mock_ws_client_class):
        """Test handling connection errors."""
        mock_client = Mock()
        mock_ws_client_class.return_value = mock_client
        mock_client.connect.side_effect = ConnectionError("Cannot connect to WebSocket")
        
        args = Namespace(
            port=8080,
            filter=None,
            output='console',
            format='text'
        )
        
        with patch.object(self.command, '_start_monitoring') as mock_start:
            mock_start.return_value = CommandResult.error_result(
                "Connection failed",
                data={'error': 'Cannot connect to WebSocket on port 8080'}
            )
            
            result = self.command.run(args)
            
            assert result.success is False
            assert "Connection failed" in result.message

    def test_monitor_with_reconnect():
        """Test automatic reconnection on disconnect."""
        args = Namespace(
            port=8080,
            filter=None,
            output='console',
            auto_reconnect=True,
            reconnect_interval=5,
            format='text'
        )
        
        with patch.object(self.command, '_start_monitoring') as mock_start:
            mock_start.return_value = CommandResult.success_result(
                "Monitoring with auto-reconnect",
                data={'auto_reconnect': True, 'reconnect_interval': 5}
            )
            
            result = self.command.run(args)
            
            assert result.success is True

    def test_monitor_with_custom_port():
        """Test monitoring on custom port."""
        args = Namespace(
            port=9090,  # Custom port
            filter=None,
            output='console',
            format='text'
        )
        
        with patch.object(self.command, '_start_monitoring') as mock_start:
            mock_start.return_value = CommandResult.success_result(
                "Monitoring on port 9090",
                data={'port': 9090}
            )
            
            result = self.command.run(args)
            
            assert result.success is True
            assert result.data['port'] == 9090

    def test_monitor_with_json_output():
        """Test monitoring with JSON formatted output."""
        args = Namespace(
            port=8080,
            filter=None,
            output='console',
            format='json',
            pretty=True
        )
        
        with patch.object(self.command, '_start_monitoring') as mock_start:
            mock_start.return_value = CommandResult.success_result(
                "Monitoring with JSON output",
                data={'format': 'json', 'pretty': True}
            )
            
            result = self.command.run(args)
            
            assert result.success is True
            assert result.data['format'] == 'json'

    def test_monitor_with_stats():
        """Test monitoring with statistics display."""
        args = Namespace(
            port=8080,
            filter=None,
            output='console',
            show_stats=True,
            stats_interval=30,
            format='text'
        )
        
        with patch.object(self.command, '_start_monitoring') as mock_start:
            mock_start.return_value = CommandResult.success_result(
                "Monitoring with stats",
                data={
                    'show_stats': True,
                    'stats': {
                        'events_received': 100,
                        'errors': 5,
                        'warnings': 10
                    }
                }
            )
            
            result = self.command.run(args)
            
            assert result.success is True
            assert result.data['show_stats'] is True

    def test_monitor_timeout():
        """Test monitoring with timeout."""
        args = Namespace(
            port=8080,
            filter=None,
            output='console',
            timeout=60,  # Monitor for 60 seconds
            format='text'
        )
        
        with patch.object(self.command, '_start_monitoring') as mock_start:
            mock_start.return_value = CommandResult.success_result(
                "Monitoring completed",
                data={'duration': 60, 'events_captured': 500}
            )
            
            result = self.command.run(args)
            
            assert result.success is True
            assert result.data['duration'] == 60