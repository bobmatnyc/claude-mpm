"""
Test suite for the agent-manager reset subcommand.

This module tests the reset functionality that removes claude-mpm authored agents
while preserving user-created agents.
"""

import json
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from claude_mpm.cli.commands.agent_manager import AgentManagerCommand
from claude_mpm.cli.shared import CommandResult


class TestAgentManagerReset(unittest.TestCase):
    """Test cases for agent-manager reset subcommand."""

    def setUp(self):
        """Set up test fixtures."""
        self.command = AgentManagerCommand()
        self.command.logger = MagicMock()

    def test_reset_dry_run_mode(self):
        """Test reset command in dry-run mode."""
        # Create mock args
        args = MagicMock()
        args.agent_manager_command = "reset"
        args.dry_run = True
        args.force = False
        args.user_only = False
        args.project_only = False
        args.format = "text"

        # Mock directory scanning
        with patch.object(Path, "exists") as mock_exists:
            mock_exists.return_value = True
            
            with patch.object(Path, "glob") as mock_glob:
                # Create mock agent files
                mock_claude_agent = MagicMock()
                mock_claude_agent.name = "engineer.md"
                mock_claude_agent.read_text.return_value = "---\nauthor: claude-mpm\n---\n# Engineer Agent"
                
                mock_user_agent = MagicMock()
                mock_user_agent.name = "custom.md"
                mock_user_agent.read_text.return_value = "# My Custom Agent\n\nNo frontmatter here"
                
                mock_glob.return_value = [mock_claude_agent, mock_user_agent]
                
                # Run the command
                result = self.command._reset_agents(args)
                
                # Verify result
                self.assertTrue(result.success)
                self.assertIn("DRY RUN", result.message)
                self.assertIn("Would remove", result.message)
                self.assertIn("engineer.md", result.message)
                self.assertIn("Preserved", result.message)

    def test_reset_force_mode(self):
        """Test reset command with force flag."""
        # Create mock args
        args = MagicMock()
        args.agent_manager_command = "reset"
        args.dry_run = False
        args.force = True
        args.user_only = False
        args.project_only = False
        args.format = "text"

        # Mock directory and file operations
        with patch.object(Path, "cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/project")
            
            with patch.object(Path, "home") as mock_home:
                mock_home.return_value = Path("/home/user")
                
                with patch.object(Path, "exists") as mock_exists:
                    mock_exists.return_value = True
                    
                    with patch.object(Path, "glob") as mock_glob:
                        # Create mock agent files
                        mock_claude_agent = MagicMock()
                        mock_claude_agent.name = "engineer.md"
                        mock_claude_agent.read_text.return_value = "---\nauthor: claude-mpm\n---\n# Engineer Agent"
                        
                        mock_user_agent = MagicMock()
                        mock_user_agent.name = "custom.md"
                        mock_user_agent.read_text.return_value = "# My Custom Agent"
                        
                        mock_glob.return_value = [mock_claude_agent, mock_user_agent]
                        
                        # Mock the unlink operation on Path objects
                        with patch.object(Path, "unlink") as mock_unlink:
                            # Run the command
                            result = self.command._reset_agents(args)
                            
                            # Verify result
                            self.assertTrue(result.success)
                            self.assertIn("Reset Complete", result.message)
                            self.assertIn("Removed", result.message)
                            
                            # Verify unlink was called (at least once for claude-mpm agent)
                            mock_unlink.assert_called()

    def test_reset_project_only(self):
        """Test reset with --project-only flag."""
        args = MagicMock()
        args.agent_manager_command = "reset"
        args.dry_run = True
        args.force = False
        args.user_only = False
        args.project_only = True
        args.format = "text"

        with patch.object(Path, "cwd") as mock_cwd:
            mock_cwd.return_value = Path("/test/project")
            
            with patch.object(Path, "exists") as mock_exists:
                # Project dir exists, user dir should not be checked
                mock_exists.return_value = True
                
                with patch.object(Path, "glob") as mock_glob:
                    mock_glob.return_value = []
                    
                    result = self.command._reset_agents(args)
                    
                    self.assertTrue(result.success)
                    self.assertIn("Project Level", result.message)
                    self.assertNotIn("User Level", result.message)

    def test_reset_user_only(self):
        """Test reset with --user-only flag."""
        args = MagicMock()
        args.agent_manager_command = "reset"
        args.dry_run = True
        args.force = False
        args.user_only = True
        args.project_only = False
        args.format = "text"

        with patch.object(Path, "home") as mock_home:
            mock_home.return_value = Path("/home/user")
            
            with patch.object(Path, "exists") as mock_exists:
                # User dir exists, project dir should not be checked
                mock_exists.return_value = True
                
                with patch.object(Path, "glob") as mock_glob:
                    mock_glob.return_value = []
                    
                    result = self.command._reset_agents(args)
                    
                    self.assertTrue(result.success)
                    self.assertIn("User Level", result.message)
                    self.assertNotIn("Project Level", result.message)

    def test_reset_json_output(self):
        """Test reset with JSON output format."""
        args = MagicMock()
        args.agent_manager_command = "reset"
        args.dry_run = True
        args.force = False
        args.user_only = False
        args.project_only = False
        args.format = "json"

        with patch.object(Path, "exists") as mock_exists:
            mock_exists.return_value = False
            
            result = self.command._reset_agents(args)
            
            self.assertTrue(result.success)
            self.assertIsNotNone(result.data)
            self.assertIn("project", result.data)
            self.assertIn("user", result.data)
            self.assertIn("dry_run", result.data)
            self.assertTrue(result.data["dry_run"])

    def test_reset_with_confirmation(self):
        """Test reset command with user confirmation prompt."""
        args = MagicMock()
        args.agent_manager_command = "reset"
        args.dry_run = False
        args.force = False  # Should prompt for confirmation
        args.user_only = False
        args.project_only = False
        args.format = "text"

        with patch.object(Path, "exists") as mock_exists:
            mock_exists.return_value = True
            
            with patch.object(Path, "glob") as mock_glob:
                mock_agent = MagicMock()
                mock_agent.name = "test.md"
                mock_agent.read_text.return_value = "---\nauthor: claude-mpm\n---\n"
                mock_agent.unlink = MagicMock()
                mock_glob.return_value = [mock_agent]
                
                # Test confirmation accepted
                with patch("builtins.input", return_value="y"):
                    with patch("builtins.print"):
                        with patch.object(Path, "unlink") as mock_unlink:
                            result = self.command._reset_agents(args)
                            self.assertTrue(result.success)
                            # Agent should be removed
                            mock_unlink.assert_called()
                
                # Reset mock and glob for next test
                mock_glob.reset_mock()
                mock_glob.return_value = [mock_agent]
                
                # Test confirmation declined
                with patch("builtins.input", return_value="n"):
                    with patch("builtins.print"):
                        with patch.object(Path, "unlink") as mock_unlink:
                            result = self.command._reset_agents(args)
                            self.assertTrue(result.success)
                            self.assertIn("cancelled", result.message.lower())
                            mock_unlink.assert_not_called()

    def test_reset_handles_errors_gracefully(self):
        """Test reset handles errors during file operations."""
        args = MagicMock()
        args.agent_manager_command = "reset"
        args.dry_run = False
        args.force = True
        args.user_only = False
        args.project_only = False
        args.format = "text"

        with patch.object(Path, "exists") as mock_exists:
            mock_exists.return_value = True
            
            with patch.object(Path, "glob") as mock_glob:
                mock_agent = MagicMock()
                mock_agent.name = "broken.md"
                mock_agent.read_text.side_effect = PermissionError("Access denied")
                mock_glob.return_value = [mock_agent]
                
                # Should handle error gracefully
                result = self.command._reset_agents(args)
                self.assertTrue(result.success)  # Still succeeds overall
                self.command.logger.warning.assert_called()

    def test_scan_and_clean_directory(self):
        """Test the _scan_and_clean_directory helper method."""
        directory = Path("/test/dir")
        results = {"removed": [], "preserved": []}
        
        with patch.object(Path, "glob") as mock_glob:
            # Create mock files
            claude_agent = MagicMock()
            claude_agent.name = "claude.md"
            claude_agent.read_text.return_value = "author: claude-mpm"
            claude_agent.unlink = MagicMock()
            
            user_agent = MagicMock()
            user_agent.name = "user.md"
            user_agent.read_text.return_value = "no author metadata"
            
            mock_glob.return_value = [claude_agent, user_agent]
            
            # Test dry run
            self.command._scan_and_clean_directory(directory, results, dry_run=True)
            self.assertIn("claude.md", results["removed"])
            self.assertIn("user.md", results["preserved"])
            claude_agent.unlink.assert_not_called()
            
            # Test actual removal
            results = {"removed": [], "preserved": []}
            self.command._scan_and_clean_directory(directory, results, dry_run=False)
            self.assertIn("claude.md", results["removed"])
            self.assertIn("user.md", results["preserved"])
            claude_agent.unlink.assert_called_once()

    def test_format_reset_results(self):
        """Test the _format_reset_results helper method."""
        results = {
            "project": {
                "checked": True,
                "removed": ["agent1.md", "agent2.md"],
                "preserved": ["custom.md"]
            },
            "user": {
                "checked": True,
                "removed": [],
                "preserved": ["my-agent.md"]
            },
            "total_removed": 2,
            "total_preserved": 2
        }
        
        # Test dry run formatting
        output = self.command._format_reset_results(results, dry_run=True, force=False)
        self.assertIn("DRY RUN", output)
        self.assertIn("Would remove", output)
        self.assertIn("agent1.md", output)
        self.assertIn("Preserved", output)
        
        # Test actual run formatting
        output = self.command._format_reset_results(results, dry_run=False, force=True)
        self.assertIn("Reset Complete", output)
        self.assertIn("Removed", output)
        self.assertNotIn("Would remove", output)


if __name__ == "__main__":
    unittest.main()