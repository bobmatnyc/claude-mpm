"""Integration tests for SessionManager with run.py.

WHY: Ensures SessionManager properly integrates with the run command
and handles session lifecycle management correctly.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from claude_mpm.cli.commands.run import create_session_context
from claude_mpm.services.cli.session_manager import SessionManager


class TestSessionManagerIntegration(unittest.TestCase):
    """Test SessionManager integration with run command."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_dir = Path(self.temp_dir) / "sessions"
        self.manager = SessionManager(session_dir=self.session_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('claude_mpm.core.claude_runner.create_simple_context')
    def test_create_session_context_with_valid_session(self, mock_create_context):
        """Test creating session context with valid session."""
        # Setup
        mock_create_context.return_value = "Base context"
        
        # Create a session with some history
        session = self.manager.create_session(context="test")
        self.manager.record_agent_use(session.id, "agent1", "Task 1")
        self.manager.record_agent_use(session.id, "agent2", "Task 2")
        
        # Create session context
        context = create_session_context(session.id, self.manager)
        
        # Verify
        self.assertIn("Base context", context)
        self.assertIn("Session Resumption", context)
        self.assertIn(session.id[:8], context)
        self.assertIn("agent1", context)
        self.assertIn("Task 1", context)
    
    @patch('claude_mpm.core.claude_runner.create_simple_context')
    def test_create_session_context_with_missing_session(self, mock_create_context):
        """Test creating session context with non-existent session."""
        # Setup
        mock_create_context.return_value = "Base context"
        
        # Create context for non-existent session
        context = create_session_context("missing-id", self.manager)
        
        # Should just return base context
        self.assertEqual(context, "Base context")
    
    @patch('claude_mpm.core.claude_runner.create_simple_context')
    def test_create_session_context_truncates_many_agents(self, mock_create_context):
        """Test that session context truncates when there are many agents."""
        # Setup
        mock_create_context.return_value = "Base context"
        
        # Create a session with many agent runs
        session = self.manager.create_session(context="test")
        for i in range(10):
            self.manager.record_agent_use(session.id, f"agent{i}", f"Task {i}")
        
        # Create session context
        context = create_session_context(session.id, self.manager)
        
        # Should show last 5 agents
        self.assertIn("agent9", context)
        self.assertIn("agent8", context)
        self.assertIn("agent7", context)
        self.assertIn("agent6", context)
        self.assertIn("agent5", context)
        
        # Should not show earlier agents
        self.assertNotIn("agent0", context)
        self.assertNotIn("agent1", context)
        
        # Should indicate there are more
        self.assertIn("5 other agent interactions", context)
    
    def test_run_command_session_setup(self):
        """Test that RunCommand can set up session management."""
        from claude_mpm.cli.commands.run import RunCommand
        
        cmd = RunCommand()
        
        # Create mock args
        args = MagicMock()
        args.mpm_resume = None
        
        # Test session setup
        session_manager, resume_id, resume_context = cmd._setup_session_management(args)
        
        # Verify
        self.assertIsInstance(session_manager, SessionManager)
        self.assertIsNone(resume_id)
        self.assertIsNone(resume_context)
    
    def test_run_command_resume_last_session(self):
        """Test resuming last interactive session."""
        from claude_mpm.cli.commands.run import RunCommand
        
        # Create a session first
        test_session = self.manager.create_session(context="default")
        
        # Mock the SessionManager to return our test manager
        with patch('claude_mpm.cli.commands.run.SessionManager') as MockSessionManager:
            MockSessionManager.return_value = self.manager
            
            cmd = RunCommand()
            
            # Create mock args for resuming last session
            args = MagicMock()
            args.mpm_resume = "last"
            
            # Test session setup
            session_manager, resume_id, resume_context = cmd._setup_session_management(args)
            
            # Verify
            self.assertEqual(resume_id, test_session.id)
            self.assertEqual(resume_context, "default")
    
    def test_run_command_resume_specific_session(self):
        """Test resuming a specific session by ID."""
        from claude_mpm.cli.commands.run import RunCommand
        
        # Create a session
        test_session = self.manager.create_session(context="custom")
        
        # Mock the SessionManager to return our test manager
        with patch('claude_mpm.cli.commands.run.SessionManager') as MockSessionManager:
            MockSessionManager.return_value = self.manager
            
            cmd = RunCommand()
            
            # Create mock args for resuming specific session
            args = MagicMock()
            args.mpm_resume = test_session.id
            
            # Test session setup
            session_manager, resume_id, resume_context = cmd._setup_session_management(args)
            
            # Verify
            self.assertEqual(resume_id, test_session.id)
            self.assertEqual(resume_context, "custom")
    
    def test_run_command_resume_nonexistent_session(self):
        """Test error handling when resuming non-existent session."""
        from claude_mpm.cli.commands.run import RunCommand
        
        # Mock the SessionManager to return our test manager
        with patch('claude_mpm.cli.commands.run.SessionManager') as MockSessionManager:
            MockSessionManager.return_value = self.manager
            
            cmd = RunCommand()
            
            # Create mock args for resuming non-existent session
            args = MagicMock()
            args.mpm_resume = "nonexistent-id"
            
            # Test session setup - should raise error
            with self.assertRaises(RuntimeError) as context:
                cmd._setup_session_management(args)
            
            self.assertIn("nonexistent-id", str(context.exception))
            self.assertIn("not found", str(context.exception))


if __name__ == '__main__':
    unittest.main()