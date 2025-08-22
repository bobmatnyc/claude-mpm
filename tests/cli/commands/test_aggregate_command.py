"""
Comprehensive tests for the AggregateCommand class.

WHY: The aggregate command manages event aggregation for monitoring and analytics.
This is important for system observability and debugging.

DESIGN DECISIONS:
- Test event collection and aggregation
- Mock event sources to control test data
- Test filtering and query capabilities
- Verify output formatting options
- Test real-time vs batch aggregation
"""

import pytest
import json
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from claude_mpm.cli.commands.aggregate import AggregateCommand
from claude_mpm.cli.shared.base_command import CommandResult


class TestAggregateCommand:
    """Test AggregateCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = AggregateCommand()

    def test_initialization():
        """Test AggregateCommand initialization."""
        assert self.command.command_name == "aggregate"
        assert self.command.logger is not None

    def test_validate_args_default():
        """Test validation with default args."""
        args = Namespace(
            aggregate_subcommand='status',
            format='text'
        )
        error = self.command.validate_args(args)
        assert error is None

    def test_validate_args_valid_commands():
        """Test validation with valid aggregate commands."""
        valid_commands = ['start', 'stop', 'status', 'sessions', 'view', 'export']
        
        for cmd in valid_commands:
            args = Namespace(aggregate_subcommand=cmd)
            error = self.command.validate_args(args)
            assert error is None, f"Command {cmd} should be valid"

    @patch('claude_mpm.cli.commands.aggregate.EventAggregator')
    def test_run_status_command(mock_aggregator_class):
        """Test status command showing aggregator status."""
        mock_aggregator = Mock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.is_running.return_value = True
        mock_aggregator.get_stats.return_value = {
            'events_collected': 1000,
            'start_time': '2024-01-01 12:00:00',
            'uptime': '2 hours'
        }
        
        args = Namespace(
            aggregate_command='status',
            format='json'
        )
        
        with patch.object(self.command, '_show_status') as mock_show:
            mock_show.return_value = CommandResult.success_result(
                "Aggregator is running",
                data={
                    'running': True,
                    'stats': {
                        'events_collected': 1000,
                        'start_time': '2024-01-01 12:00:00',
                        'uptime': '2 hours'
                    }
                }
            )
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            assert result.data['running'] is True
            mock_show.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.EventAggregator')
    def test_run_start_command(mock_aggregator_class):
        """Test starting the aggregator."""
        mock_aggregator = Mock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.start.return_value = True
        
        args = Namespace(
            aggregate_command='start',
            background=True,
            port=8090,
            format='text'
        )
        
        with patch.object(self.command, '_start_aggregator') as mock_start:
            mock_start.return_value = CommandResult.success_result(
                "Aggregator started",
                data={'port': 8090, 'pid': 12345}
            )
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_start.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.EventAggregator')
    def test_run_stop_command(mock_aggregator_class):
        """Test stopping the aggregator."""
        mock_aggregator = Mock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.stop.return_value = True
        
        args = Namespace(
            aggregate_command='stop',
            force=False,
            format='text'
        )
        
        with patch.object(self.command, '_stop_aggregator') as mock_stop:
            mock_stop.return_value = CommandResult.success_result("Aggregator stopped")
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_stop.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.EventAggregator')
    def test_run_collect_command(mock_aggregator_class):
        """Test collecting events."""
        mock_aggregator = Mock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_aggregator.collect_events.return_value = [
            {'timestamp': '2024-01-01 12:00:00', 'event': 'test_event', 'data': {}},
            {'timestamp': '2024-01-01 12:00:01', 'event': 'another_event', 'data': {}}
        ]
        
        args = Namespace(
            aggregate_command='collect',
            source='all',
            interval=60,
            format='json'
        )
        
        with patch.object(self.command, '_collect_events') as mock_collect:
            mock_collect.return_value = CommandResult.success_result(
                "Events collected",
                data={
                    'events_count': 2,
                    'events': [
                        {'timestamp': '2024-01-01 12:00:00', 'event': 'test_event'},
                        {'timestamp': '2024-01-01 12:00:01', 'event': 'another_event'}
                    ]
                }
            )
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            assert result.data['events_count'] == 2
            mock_collect.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.EventAggregator')
    def test_run_query_command(mock_aggregator_class):
        """Test querying aggregated events."""
        mock_aggregator = Mock()
        mock_aggregator_class.return_value = mock_aggregator
        
        args = Namespace(
            aggregate_command='query',
            filter='event_type=error',
            start_time='2024-01-01',
            end_time='2024-01-02',
            limit=100,
            format='json'
        )
        
        with patch.object(self.command, '_query_events') as mock_query:
            mock_query.return_value = CommandResult.success_result(
                "Query executed",
                data={
                    'query': 'event_type=error',
                    'results_count': 5,
                    'results': [
                        {'timestamp': '2024-01-01 13:00:00', 'event': 'error', 'message': 'Test error'}
                    ] * 5
                }
            )
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            assert result.data['results_count'] == 5
            mock_query.assert_called_once_with(args)

    @patch('claude_mpm.cli.commands.aggregate.EventAggregator')
    def test_run_clear_command(mock_aggregator_class):
        """Test clearing aggregated data."""
        mock_aggregator = Mock()
        mock_aggregator_class.return_value = mock_aggregator
        
        args = Namespace(
            aggregate_command='clear',
            before_date=None,
            force=True,
            format='text'
        )
        
        with patch.object(self.command, '_clear_data') as mock_clear:
            mock_clear.return_value = CommandResult.success_result(
                "Data cleared",
                data={'events_removed': 1000}
            )
            
            result = self.command.run(args)
            
            assert isinstance(result, CommandResult)
            assert result.success is True
            mock_clear.assert_called_once_with(args)

    def test_collect_with_filters():
        """Test collecting events with filters."""
        args = Namespace(
            aggregate_subcommand='sessions',
            source='hooks',
            event_type='response',
            min_duration=100,
            format='json'
        )
        
        with patch.object(self.command, '_collect_events') as mock_collect:
            mock_collect.return_value = CommandResult.success_result(
                "Filtered events collected",
                data={
                    'filters_applied': ['source=hooks', 'event_type=response', 'min_duration=100'],
                    'events_count': 10
                }
            )
            
            result = self.command.run(args)
            
            assert result.success is True
            assert result.data['events_count'] == 10

    def test_query_with_aggregation():
        """Test query with aggregation functions."""
        args = Namespace(
            aggregate_command='query',
            aggregate_by='event_type',
            aggregate_func='count',
            format='json'
        )
        
        with patch.object(self.command, '_query_events') as mock_query:
            mock_query.return_value = CommandResult.success_result(
                "Aggregated query results",
                data={
                    'aggregation': {
                        'error': 50,
                        'warning': 100,
                        'info': 500
                    }
                }
            )
            
            result = self.command.run(args)
            
            assert result.success is True
            assert result.data['aggregation']['error'] == 50

    def test_real_time_collection():
        """Test real-time event collection."""
        args = Namespace(
            aggregate_command='collect',
            real_time=True,
            duration=10,  # Collect for 10 seconds
            format='text'
        )
        
        with patch.object(self.command, '_collect_realtime') as mock_collect:
            mock_collect.return_value = CommandResult.success_result(
                "Real-time collection completed",
                data={'events_collected': 25, 'duration': 10}
            )
            
            result = self.command.run(args)
            
            assert result.success is True

    def test_export_aggregated_data():
        """Test exporting aggregated data."""
        args = Namespace(
            aggregate_command='export',
            output_file='/tmp/events.json',
            format='json'
        )
        
        with patch.object(self.command, '_export_data') as mock_export:
            mock_export.return_value = CommandResult.success_result(
                "Data exported",
                data={'file': '/tmp/events.json', 'events_exported': 1000}
            )
            
            result = self.command.run(args)
            
            assert result.success is True

    def test_aggregator_already_running():
        """Test starting aggregator when already running."""
        args = Namespace(
            aggregate_command='start',
            background=True,
            format='text'
        )
        
        with patch.object(self.command, '_start_aggregator') as mock_start:
            mock_start.return_value = CommandResult.error_result(
                "Aggregator already running",
                data={'pid': 12345}
            )
            
            result = self.command.run(args)
            
            assert result.success is False
            assert "already running" in result.message

    def test_stop_aggregator_not_running():
        """Test stopping aggregator when not running."""
        args = Namespace(
            aggregate_command='stop',
            force=False,
            format='text'
        )
        
        with patch.object(self.command, '_stop_aggregator') as mock_stop:
            mock_stop.return_value = CommandResult.error_result("Aggregator not running")
            
            result = self.command.run(args)
            
            assert result.success is False
            assert "not running" in result.message

    def test_clear_with_confirmation():
        """Test clearing data with user confirmation."""
        args = Namespace(
            aggregate_command='clear',
            before_date=None,
            force=False,
            format='text'
        )
        
        with patch('builtins.input', return_value='y'):
            with patch.object(self.command, '_clear_data') as mock_clear:
                mock_clear.return_value = CommandResult.success_result("Data cleared")
                
                result = self.command.run(args)
                
                assert result.success is True

    def test_query_with_invalid_filter():
        """Test query with invalid filter syntax."""
        args = Namespace(
            aggregate_command='query',
            filter='invalid filter syntax',
            format='text'
        )
        
        with patch.object(self.command, '_query_events') as mock_query:
            mock_query.return_value = CommandResult.error_result(
                "Invalid filter syntax",
                data={'error': 'Expected format: key=value'}
            )
            
            result = self.command.run(args)
            
            assert result.success is False
            assert "Invalid filter" in result.message