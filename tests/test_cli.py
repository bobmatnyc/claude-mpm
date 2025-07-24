"""Tests for CLI functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from cli import main, run_session, list_tickets, show_info


class TestCLI:
    """Test the CLI interface."""
    
    def test_main_no_args(self):
        """Test main with no arguments defaults to run."""
        with patch('cli.run_session') as mock_run:
            result = main([])
            assert result == 0
            mock_run.assert_called_once()
    
    def test_main_run_command(self):
        """Test explicit run command."""
        with patch('cli.run_session') as mock_run:
            result = main(['run'])
            assert result == 0
            mock_run.assert_called_once()
    
    def test_main_tickets_command(self):
        """Test tickets command."""
        with patch('cli.list_tickets') as mock_list:
            result = main(['tickets'])
            assert result == 0
            mock_list.assert_called_once()
    
    def test_main_info_command(self):
        """Test info command."""
        with patch('cli.show_info') as mock_info:
            result = main(['info'])
            assert result == 0
            mock_info.assert_called_once()
    
    def test_main_debug_flag(self):
        """Test debug flag."""
        with patch('cli.run_session') as mock_run:
            with patch('cli.setup_logging') as mock_logging:
                main(['--debug', 'run'])
                mock_logging.assert_called_with(level='DEBUG', log_dir=None)
    
    def test_main_custom_log_dir(self, tmp_path):
        """Test custom log directory."""
        with patch('cli.run_session') as mock_run:
            with patch('cli.setup_logging') as mock_logging:
                main(['--log-dir', str(tmp_path), 'run'])
                mock_logging.assert_called_with(level='INFO', log_dir=tmp_path)
    
    def test_main_keyboard_interrupt(self):
        """Test handling keyboard interrupt."""
        with patch('cli.run_session', side_effect=KeyboardInterrupt):
            result = main(['run'])
            assert result == 0
    
    def test_main_exception(self):
        """Test handling general exception."""
        with patch('cli.run_session', side_effect=Exception("Test error")):
            result = main(['run'])
            assert result == 1
    
    @patch('orchestration.orchestrator.MPMOrchestrator')
    def test_run_session(self, mock_orchestrator_class):
        """Test run_session function."""
        # Mock orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.ticket_extractor.get_all_tickets.return_value = [
            {'type': 'task', 'title': 'Test task'},
            {'type': 'bug', 'title': 'Test bug'},
        ]
        mock_orchestrator.ticket_extractor.get_summary.return_value = {
            'task': 1,
            'bug': 1
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Create mock args
        args = Mock()
        args.framework_path = None
        args.debug = False
        args.log_dir = None
        args.no_tickets = False
        
        # Run session
        with patch('builtins.print') as mock_print:
            run_session(args)
        
        # Verify orchestrator was created and run
        mock_orchestrator.run_interactive.assert_called_once()
        
        # Verify summary was printed
        print_calls = mock_print.call_args_list
        assert any('Extracted 2 tickets' in str(call) for call in print_calls)
    
    def test_run_session_no_tickets(self):
        """Test run session with ticket creation disabled."""
        with patch('claude_mpm.orchestrator.MPMOrchestrator') as mock_class:
            mock_orchestrator = MagicMock()
            mock_class.return_value = mock_orchestrator
            
            args = Mock()
            args.no_tickets = True
            args.framework_path = None
            args.debug = False
            args.log_dir = None
            
            run_session(args)
            
            # Verify ticket creation was disabled
            assert mock_orchestrator.ticket_creation_enabled is False
    
    @patch('cli.TicketManager')
    def test_list_tickets(self, mock_manager_class, capsys):
        """Test listing tickets."""
        # Mock ticket manager
        mock_manager = MagicMock()
        mock_manager.list_recent_tickets.return_value = [
            {
                'id': 'TASK-001',
                'title': 'Test task',
                'status': 'open',
                'priority': 'high',
                'tags': ['todo', 'urgent'],
                'created_at': '2025-01-23T10:00:00'
            },
            {
                'id': 'BUG-001',
                'title': 'Test bug',
                'status': 'in_progress',
                'priority': 'medium',
                'tags': ['bug', 'backend'],
                'created_at': '2025-01-23T11:00:00'
            }
        ]
        mock_manager_class.return_value = mock_manager
        
        args = Mock()
        args.limit = 10
        
        list_tickets(args)
        
        # Check output
        captured = capsys.readouterr()
        assert 'TASK-001' in captured.out
        assert 'Test task' in captured.out
        assert 'BUG-001' in captured.out
        assert 'Test bug' in captured.out
        assert '🔵' in captured.out  # open status
        assert '🟡' in captured.out  # in_progress status
    
    def test_list_tickets_empty(self, capsys):
        """Test listing tickets when none exist."""
        with patch('cli.TicketManager') as mock_class:
            mock_manager = MagicMock()
            mock_manager.list_recent_tickets.return_value = []
            mock_class.return_value = mock_manager
            
            args = Mock()
            args.limit = 10
            
            list_tickets(args)
            
            captured = capsys.readouterr()
            assert 'No tickets found' in captured.out
    
    def test_list_tickets_import_error(self, capsys):
        """Test listing tickets when ai-trackdown-pytools not installed."""
        with patch('cli.TicketManager', side_effect=ImportError):
            args = Mock()
            args.limit = 10
            
            list_tickets(args)
            
            captured = capsys.readouterr()
            assert 'ai-trackdown-pytools not installed' in captured.out
    
    @patch('shutil.which')
    @patch('claude_mpm.framework_loader.FrameworkLoader')
    def test_show_info(self, mock_loader_class, mock_which, capsys):
        """Test showing info."""
        # Mock framework loader
        mock_loader = MagicMock()
        mock_loader.framework_content = {
            'loaded': True,
            'version': '016'
        }
        mock_loader.framework_path = '/path/to/framework'
        mock_loader.get_agent_list.return_value = ['engineer', 'qa', 'researcher']
        mock_loader_class.return_value = mock_loader
        
        # Mock Claude executable
        mock_which.return_value = '/usr/local/bin/claude'
        
        args = Mock()
        args.framework_path = None
        args.log_dir = None
        args.debug = False
        
        # Mock ai_trackdown_pytools as installed
        import sys
        mock_module = MagicMock()
        sys.modules['ai_trackdown_pytools'] = mock_module
        
        try:
            show_info(args)
            
            captured = capsys.readouterr()
            assert 'Claude MPM' in captured.out
            assert 'Version: 016' in captured.out
            assert 'engineer, qa, researcher' in captured.out
            assert '✓ Claude CLI:' in captured.out
            assert '✓ ai-trackdown-pytools: Installed' in captured.out
        finally:
            # Clean up mock
            if 'ai_trackdown_pytools' in sys.modules:
                del sys.modules['ai_trackdown_pytools']
    
    def test_show_info_no_framework(self, capsys):
        """Test showing info when framework not found."""
        with patch('claude_mpm.framework_loader.FrameworkLoader') as mock_class:
            mock_loader = MagicMock()
            mock_loader.framework_content = {'loaded': False}
            mock_class.return_value = mock_loader
            
            with patch('shutil.which', return_value=None):
                args = Mock()
                args.framework_path = None
                args.log_dir = None
                args.debug = False
                
                show_info(args)
                
                captured = capsys.readouterr()
                assert 'Framework: Not found' in captured.out
                assert '✗ Claude CLI: Not found' in captured.out