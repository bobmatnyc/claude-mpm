"""Tests for the MPM orchestrator."""

import pytest
import subprocess
import threading
import queue
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from orchestration.orchestrator import MPMOrchestrator


class TestMPMOrchestrator:
    """Test the MPMOrchestrator class."""
    
    def test_init(self, tmp_path):
        """Test orchestrator initialization."""
        orchestrator = MPMOrchestrator(
            framework_path=tmp_path,
            debug=True,
            log_dir=tmp_path / "logs"
        )
        
        assert orchestrator.framework_loader is not None
        assert orchestrator.ticket_extractor is not None
        assert orchestrator.process is None
        assert orchestrator.first_interaction is True
        assert orchestrator.running is False
        assert orchestrator.ticket_creation_enabled is True
    
    @patch('shutil.which')
    @patch('subprocess.Popen')
    def test_start_success(self, mock_popen, mock_which):
        """Test successful start of Claude subprocess."""
        # Mock finding claude executable
        mock_which.return_value = "/usr/local/bin/claude"
        
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        orchestrator = MPMOrchestrator()
        result = orchestrator.start()
        
        assert result is True
        assert orchestrator.process is not None
        assert orchestrator.running is True
        
        # Check command
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "/usr/local/bin/claude" in call_args
        assert "--model" in call_args
        assert "opus" in call_args
    
    @patch('shutil.which')
    def test_start_claude_not_found(self, mock_which):
        """Test start when Claude executable not found."""
        mock_which.return_value = None
        
        orchestrator = MPMOrchestrator()
        result = orchestrator.start()
        
        assert result is False
        assert orchestrator.process is None
        assert orchestrator.running is False
    
    def test_find_claude_executable(self):
        """Test finding Claude executable."""
        orchestrator = MPMOrchestrator()
        
        # Test with mocked which
        with patch('shutil.which', return_value="/path/to/claude"):
            result = orchestrator._find_claude_executable()
            assert result == "/path/to/claude"
        
        # Test when not found
        with patch('shutil.which', return_value=None):
            with patch.object(orchestrator, '_is_executable', return_value=False):
                result = orchestrator._find_claude_executable()
                assert result is None
    
    def test_send_input(self):
        """Test sending input to Claude."""
        orchestrator = MPMOrchestrator()
        orchestrator.send_input("test input")
        
        # Check input is queued
        assert orchestrator.input_queue.qsize() == 1
        assert orchestrator.input_queue.get() == "test input"
    
    def test_get_output(self):
        """Test getting output from Claude."""
        orchestrator = MPMOrchestrator()
        
        # Test with no output
        result = orchestrator.get_output(timeout=0.01)
        assert result is None
        
        # Test with output
        orchestrator.output_queue.put("test output")
        result = orchestrator.get_output()
        assert result == "test output"
    
    def test_ticket_extraction_from_output(self):
        """Test ticket extraction during output processing."""
        orchestrator = MPMOrchestrator()
        
        # Simulate output reader processing
        orchestrator.running = True
        orchestrator.process = MagicMock()
        orchestrator.process.poll.return_value = None
        orchestrator.process.stdout.readline.side_effect = [
            "Regular output\n",
            "TODO: Implement new feature\n",
            "BUG: Fix memory leak\n",
            ""  # EOF
        ]
        
        # Run output reader briefly
        orchestrator._output_reader()
        
        # Check tickets were extracted
        tickets = orchestrator.ticket_extractor.get_all_tickets()
        assert len(tickets) == 2
        assert any(t['title'] == 'Implement new feature' for t in tickets)
        assert any(t['title'] == 'Fix memory leak' for t in tickets)
    
    def test_framework_injection(self):
        """Test framework instruction injection on first interaction."""
        orchestrator = MPMOrchestrator()
        orchestrator.running = True
        orchestrator.process = MagicMock()
        
        # Mock framework instructions
        with patch.object(orchestrator.framework_loader, 'get_framework_instructions', 
                         return_value="# Framework Instructions"):
            
            # Queue input
            orchestrator.input_queue.put("User input")
            
            # Process one iteration of input writer
            orchestrator._input_writer()
            
            # Check that framework was injected
            orchestrator.process.stdin.write.assert_called()
            call_args = orchestrator.process.stdin.write.call_args[0][0]
            assert "# Framework Instructions" in call_args
            assert "User input" in call_args
            assert orchestrator.first_interaction is False
    
    @patch('shutil.which')
    @patch('subprocess.Popen')
    def test_stop(self, mock_popen, mock_which):
        """Test stopping the orchestrator."""
        # Set up running orchestrator
        mock_which.return_value = "/usr/local/bin/claude"
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        orchestrator = MPMOrchestrator()
        orchestrator.start()
        
        # Add some test tickets
        orchestrator.ticket_extractor.extract_from_line("TODO: Test ticket")
        
        # Stop orchestrator
        with patch.object(orchestrator, '_save_session_log'):
            with patch.object(orchestrator, '_create_tickets'):
                orchestrator.stop()
        
        assert orchestrator.running is False
        mock_process.terminate.assert_called_once()
    
    def test_session_logging(self):
        """Test session interaction logging."""
        orchestrator = MPMOrchestrator()
        
        # Log some interactions
        orchestrator._log_interaction("input", "user input")
        orchestrator._log_interaction("output", "claude output")
        
        assert len(orchestrator.session_log) == 2
        assert orchestrator.session_log[0]['type'] == "input"
        assert orchestrator.session_log[0]['content'] == "user input"
        assert orchestrator.session_log[1]['type'] == "output"
        assert orchestrator.session_log[1]['content'] == "claude output"
    
    @patch("services.ticket_manager.TicketManager")
    def test_create_tickets(self, mock_ticket_manager_class):
        """Test ticket creation at end of session."""
        # Mock ticket manager
        mock_ticket_manager = MagicMock()
        mock_ticket_manager.create_ticket.return_value = "TICKET-123"
        mock_ticket_manager_class.return_value = mock_ticket_manager
        
        orchestrator = MPMOrchestrator()
        
        # Add test tickets
        orchestrator.ticket_extractor.extract_from_line("TODO: First task")
        orchestrator.ticket_extractor.extract_from_line("BUG: First bug")
        
        # Create tickets
        orchestrator._create_tickets()
        
        # Verify calls
        assert mock_ticket_manager.create_ticket.call_count == 2
        
        # Check first ticket
        first_call = mock_ticket_manager.create_ticket.call_args_list[0]
        assert first_call.kwargs['title'] == 'First task'
        assert first_call.kwargs['ticket_type'] == 'task'
        
        # Check second ticket
        second_call = mock_ticket_manager.create_ticket.call_args_list[1]
        assert second_call.kwargs['title'] == 'First bug'
        assert second_call.kwargs['ticket_type'] == 'bug'
    
    def test_ticket_creation_disabled(self):
        """Test disabling ticket creation."""
        orchestrator = MPMOrchestrator()
        orchestrator.ticket_creation_enabled = False
        
        # Add test tickets
        orchestrator.ticket_extractor.extract_from_line("TODO: Task")
        
        # Try to create tickets
        with patch("services.ticket_manager.TicketManager") as mock_manager:
            orchestrator._create_tickets()
            # Should not create ticket manager
            mock_manager.assert_not_called()
    
    def test_save_session_log(self, tmp_path):
        """Test saving session log to file."""
        orchestrator = MPMOrchestrator()
        
        # Add some session data
        orchestrator._log_interaction("input", "test input")
        orchestrator._log_interaction("output", "test output")
        orchestrator.ticket_extractor.extract_from_line("TODO: Test task")
        
        # Mock home directory
        with patch.object(Path, 'home', return_value=tmp_path):
            orchestrator._save_session_log()
        
        # Check log file was created
        log_dir = tmp_path / ".claude-mpm" / "sessions"
        assert log_dir.exists()
        
        # Find the log file
        log_files = list(log_dir.glob("session_*.json"))
        assert len(log_files) == 1
        
        # Load and verify content
        import json
        with open(log_files[0]) as f:
            session_data = json.load(f)
        
        assert len(session_data['interactions']) == 2
        assert len(session_data['tickets_extracted']) == 1
        assert session_data['tickets_extracted'][0]['title'] == 'Test task'