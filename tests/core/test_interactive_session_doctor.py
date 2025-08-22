"""Test the /mpm-doctor command in interactive session."""

import unittest
from unittest.mock import MagicMock, patch

from claude_mpm.core.interactive_session import InteractiveSession


class TestInteractiveSessionDoctor(unittest.TestCase):
    """Test the /mpm-doctor command functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_runner = MagicMock()
        self.mock_runner.config = {}
        self.mock_runner.websocket_server = None
        self.mock_runner.project_logger = None
        self.mock_runner.session_log_file = None
        self.session = InteractiveSession(self.mock_runner)
    
    def test_process_mpm_doctor_command(self):
        """Test that /mpm-doctor command is recognized."""
        result = self.session.process_interactive_command("/mpm-doctor")
        # Command should be recognized (not None)
        self.assertIsNotNone(result)
    
    def test_process_mpm_doctor_with_verbose(self):
        """Test /mpm-doctor command with --verbose flag."""
        result = self.session.process_interactive_command("/mpm-doctor --verbose")
        # Command should be recognized
        self.assertIsNotNone(result)
    
    @patch("claude_mpm.services.diagnostics.DoctorReporter")
    @patch("claude_mpm.services.diagnostics.DiagnosticRunner")
    def test_run_doctor_diagnostics(self, mock_runner, mock_reporter):
        """Test the _run_doctor_diagnostics method."""
        # Set up mocks
        mock_summary = MagicMock()
        mock_summary.error_count = 0
        mock_runner_instance = MagicMock()
        mock_runner_instance.run_diagnostics.return_value = mock_summary
        mock_runner.return_value = mock_runner_instance
        
        mock_reporter_instance = MagicMock()
        mock_reporter.return_value = mock_reporter_instance
        
        # Run diagnostics
        result = self.session._run_doctor_diagnostics([])
        
        # Verify it was called
        mock_runner.assert_called_once_with(verbose=False)
        mock_runner_instance.run_diagnostics.assert_called_once()
        mock_reporter.assert_called_once_with(use_color=True, verbose=False)
        mock_reporter_instance.report.assert_called_once_with(mock_summary, format="terminal")
        
        # Should return True when no errors
        self.assertTrue(result)
    
    @patch("claude_mpm.services.diagnostics.DoctorReporter")
    @patch("claude_mpm.services.diagnostics.DiagnosticRunner")
    def test_run_doctor_diagnostics_verbose(self, mock_runner, mock_reporter):
        """Test diagnostics with verbose flag."""
        # Set up mocks
        mock_summary = MagicMock()
        mock_summary.error_count = 0
        mock_runner_instance = MagicMock()
        mock_runner_instance.run_diagnostics.return_value = mock_summary
        mock_runner.return_value = mock_runner_instance
        
        mock_reporter_instance = MagicMock()
        mock_reporter.return_value = mock_reporter_instance
        
        # Run diagnostics with verbose
        result = self.session._run_doctor_diagnostics(["--verbose"])
        
        # Verify verbose was passed
        mock_runner.assert_called_once_with(verbose=True)
        mock_reporter.assert_called_once_with(use_color=True, verbose=True)
        
        self.assertTrue(result)
    
    @patch("claude_mpm.services.diagnostics.DoctorReporter")
    @patch("claude_mpm.services.diagnostics.DiagnosticRunner")
    def test_run_doctor_diagnostics_with_errors(self, mock_runner, mock_reporter):
        """Test diagnostics when errors are found."""
        # Set up mocks
        mock_summary = MagicMock()
        mock_summary.error_count = 1  # Has errors
        mock_runner_instance = MagicMock()
        mock_runner_instance.run_diagnostics.return_value = mock_summary
        mock_runner.return_value = mock_runner_instance
        
        mock_reporter_instance = MagicMock()
        mock_reporter.return_value = mock_reporter_instance
        
        # Run diagnostics
        result = self.session._run_doctor_diagnostics([])
        
        # Should return False when errors exist
        self.assertFalse(result)
    
    @patch("claude_mpm.services.diagnostics.DiagnosticRunner")
    def test_run_doctor_diagnostics_exception(self, mock_runner):
        """Test diagnostics when an exception occurs."""
        # Make runner raise an exception
        mock_runner_instance = MagicMock()
        mock_runner_instance.run_diagnostics.side_effect = Exception("Test error")
        mock_runner.return_value = mock_runner_instance
        
        # Run diagnostics
        result = self.session._run_doctor_diagnostics([])
        
        # Should return False on exception
        self.assertFalse(result)
    
    def test_process_interactive_command_not_recognized(self):
        """Test that non-special commands return None."""
        result = self.session.process_interactive_command("regular text")
        self.assertIsNone(result)
    
    def test_process_interactive_command_agents_still_works(self):
        """Test that /agents command still works."""
        with patch.object(self.session, "_show_available_agents", return_value=True):
            result = self.session.process_interactive_command("/agents")
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()