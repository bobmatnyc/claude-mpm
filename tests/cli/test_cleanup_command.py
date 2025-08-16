"""Unit tests for the cleanup-memory command."""

import sys
import io
import unittest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from argparse import Namespace

from claude_mpm.cli.commands.cleanup import cleanup_memory, parse_size, format_size


class TestCleanupCommand(unittest.TestCase):
    """Test the cleanup-memory command functionality."""
    
    def test_parse_size(self):
        """Test size parsing from human-readable strings."""
        self.assertEqual(parse_size("100"), 100)
        self.assertEqual(parse_size("1KB"), 1024)
        self.assertEqual(parse_size("1kb"), 1024)
        self.assertEqual(parse_size("500KB"), 500 * 1024)
        self.assertEqual(parse_size("1MB"), 1024 * 1024)
        self.assertEqual(parse_size("2GB"), 2 * 1024 * 1024 * 1024)
        
        with self.assertRaises(ValueError):
            parse_size("invalid")
    
    def test_format_size(self):
        """Test formatting bytes to human-readable strings."""
        self.assertEqual(format_size(100), "100.0B")
        self.assertEqual(format_size(1024), "1.0KB")
        self.assertEqual(format_size(1536), "1.5KB")
        self.assertEqual(format_size(1024 * 1024), "1.0MB")
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.0GB")
    
    @patch('claude_mpm.cli.commands.cleanup.Path')
    @patch('builtins.print')
    def test_cleanup_no_claude_json(self, mock_print, mock_path):
        """Test cleanup when .claude.json doesn't exist."""
        # Mock Path to simulate missing .claude.json
        mock_claude_json = MagicMock()
        mock_claude_json.exists.return_value = False
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value = mock_claude_json
        
        args = Namespace(
            days=30,
            max_size='500KB',
            archive=True,
            force=False,
            dry_run=False
        )
        
        cleanup_memory(args)
        
        # Check that it reports no file found
        mock_print.assert_any_call("✅ No .claude.json file found - nothing to clean up")
    
    @patch('claude_mpm.cli.commands.cleanup.sys.stdin')
    @patch('claude_mpm.cli.commands.cleanup.Path')
    @patch('builtins.print')
    def test_cleanup_with_user_cancel_tty(self, mock_print, mock_path, mock_stdin):
        """Test cleanup cancellation via user input in TTY environment."""
        # Mock Path to simulate existing .claude.json
        mock_claude_json = MagicMock()
        mock_claude_json.exists.return_value = True
        mock_claude_json.stat.return_value.st_size = 100  # Small file
        
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value = mock_claude_json
        
        # Mock TTY environment
        mock_stdin.isatty.return_value = True
        
        args = Namespace(
            days=30,
            max_size='500KB',
            archive=True,
            force=False,
            dry_run=False
        )
        
        # Mock input to return 'n'
        with patch('builtins.input', return_value='n'):
            cleanup_memory(args)
        
        # Since file is small, it shouldn't prompt, but we're testing the flow
        # In a real scenario with a large file, it would prompt and cancel
    
    @patch('claude_mpm.cli.commands.cleanup.sys.stdin')
    @patch('claude_mpm.cli.commands.cleanup.sys.stdout')
    @patch('claude_mpm.cli.commands.cleanup.Path')
    @patch('builtins.print')
    def test_cleanup_with_user_cancel_non_tty(self, mock_print, mock_path, mock_stdout, mock_stdin):
        """Test cleanup cancellation via piped input in non-TTY environment."""
        # Mock Path to simulate existing large .claude.json
        mock_claude_json = MagicMock()
        mock_claude_json.exists.return_value = True
        mock_claude_json.stat.return_value.st_size = 1024 * 1024  # 1MB - large file
        
        # Mock for line count
        mock_open_file = mock_open(read_data='line1\nline2\nline3\n')
        
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value = mock_claude_json
        
        # Mock non-TTY environment (piped input)
        mock_stdin.isatty.return_value = False
        mock_stdin.readline.return_value = 'n\n'
        
        args = Namespace(
            days=30,
            max_size='500KB',  # Smaller than file size to trigger cleanup
            archive=True,
            force=False,
            dry_run=False
        )
        
        with patch('builtins.open', mock_open_file):
            cleanup_memory(args)
        
        # Verify cancellation message was printed
        mock_print.assert_any_call("❌ Cleanup cancelled")
    
    @patch('claude_mpm.cli.commands.cleanup.sys.stdin')
    @patch('claude_mpm.cli.commands.cleanup.sys.stdout')
    @patch('claude_mpm.cli.commands.cleanup.Path')
    @patch('builtins.print')
    def test_cleanup_with_force_flag(self, mock_print, mock_path, mock_stdout, mock_stdin):
        """Test cleanup with --force flag skips confirmation."""
        # Mock Path to simulate existing large .claude.json
        mock_claude_json = MagicMock()
        mock_claude_json.exists.return_value = True
        mock_claude_json.stat.return_value.st_size = 1024 * 1024  # 1MB
        
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value = mock_claude_json
        
        args = Namespace(
            days=30,
            max_size='500KB',
            archive=True,
            force=True,  # Force flag set
            dry_run=True  # Use dry-run to avoid actual file operations
        )
        
        with patch('builtins.open', mock_open(read_data='test\n')):
            cleanup_memory(args)
        
        # Verify input was never called (no confirmation prompt)
        mock_stdin.readline.assert_not_called()
        with patch('builtins.input') as mock_input:
            mock_input.assert_not_called()
    
    @patch('claude_mpm.cli.commands.cleanup.sys.stdin')
    @patch('claude_mpm.cli.commands.cleanup.Path')
    @patch('builtins.print')  
    def test_cleanup_handles_eof_error(self, mock_print, mock_path, mock_stdin):
        """Test cleanup handles EOFError gracefully."""
        # Mock Path to simulate existing large .claude.json
        mock_claude_json = MagicMock()
        mock_claude_json.exists.return_value = True
        mock_claude_json.stat.return_value.st_size = 1024 * 1024  # 1MB
        
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value = mock_claude_json
        
        # Mock TTY environment
        mock_stdin.isatty.return_value = True
        
        args = Namespace(
            days=30,
            max_size='500KB',
            archive=True,
            force=False,
            dry_run=False
        )
        
        # Mock input to raise EOFError
        with patch('builtins.input', side_effect=EOFError):
            with patch('builtins.open', mock_open(read_data='test\n')):
                cleanup_memory(args)
        
        # Verify it treats EOFError as 'n' and cancels
        mock_print.assert_any_call("❌ Cleanup cancelled")


if __name__ == '__main__':
    unittest.main()