#!/usr/bin/env python3
"""End-to-end tests for claude-mpm interactive and non-interactive modes."""

import subprocess
import sys
import time
import os
from pathlib import Path
import pytest
import tempfile
import signal

# Find project root
PROJECT_ROOT = Path(__file__).parent.parent
CLAUDE_MPM_SCRIPT = PROJECT_ROOT / "scripts" / "claude-mpm"


class TestE2E:
    """End-to-end tests for claude-mpm."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure claude-mpm script exists and is executable."""
        assert CLAUDE_MPM_SCRIPT.exists(), f"claude-mpm script not found at {CLAUDE_MPM_SCRIPT}"
        assert os.access(CLAUDE_MPM_SCRIPT, os.X_OK), f"claude-mpm script is not executable"
    
    def test_version_command(self):
        """Test that --version returns expected format."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0, f"Version command failed: {result.stderr}"
        assert "claude-mpm" in result.stdout.lower(), f"Version output missing 'claude-mpm': {result.stdout}"
        # Should match pattern like "claude-mpm 0.3.0"
        assert any(char.isdigit() for char in result.stdout), f"Version output missing version number: {result.stdout}"
    
    def test_help_command(self):
        """Test that --help shows expected commands."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0, f"Help command failed: {result.stderr}"
        
        # Check for expected commands
        expected_commands = ["run", "tickets", "info"]
        for cmd in expected_commands:
            assert cmd in result.stdout, f"Help output missing command '{cmd}'"
        
        # Check for expected options
        expected_options = ["--version", "--help", "--non-interactive"]
        for opt in expected_options:
            assert opt in result.stdout, f"Help output missing option '{opt}'"
    
    def test_non_interactive_simple_prompt(self):
        """Test non-interactive mode with a simple mathematical prompt."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "run", "-i", "What is 5 + 5?", "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        assert result.returncode == 0, f"Non-interactive command failed: {result.stderr}"
        assert "10" in result.stdout, f"Expected '10' in output, got: {result.stdout}"
    
    def test_non_interactive_stdin(self):
        """Test non-interactive mode reading from stdin."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "run", "--non-interactive"],
            input="What is 7 * 7?",
            capture_output=True,
            text=True,
            timeout=60
        )
        
        assert result.returncode == 0, f"Non-interactive stdin failed: {result.stderr}"
        assert "49" in result.stdout, f"Expected '49' in output, got: {result.stdout}"
    
    def test_interactive_mode_startup_and_exit(self):
        """Test that interactive mode starts and can exit cleanly."""
        # Start interactive mode
        process = subprocess.Popen(
            [str(CLAUDE_MPM_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Give it time to start
            time.sleep(2)
            
            # Send exit command
            stdout, stderr = process.communicate(input="exit\n", timeout=10)
            
            # Check that it started properly
            assert "claude-mpm" in stdout.lower() or "claude-mpm" in stderr.lower(), \
                f"Interactive mode startup missing expected output.\nStdout: {stdout}\nStderr: {stderr}"
            
            # Should exit cleanly
            assert process.returncode in [0, None], \
                f"Interactive mode exited with error code {process.returncode}.\nStderr: {stderr}"
            
        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Interactive mode did not exit within timeout")
    
    def test_info_command(self):
        """Test the info command."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "info"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Info command might have some errors but should still provide output
        assert "Claude MPM" in result.stdout or "Claude MPM" in result.stderr, \
            f"Info command missing expected output.\nStdout: {result.stdout}\nStderr: {result.stderr}"
    
    def test_subprocess_orchestrator(self):
        """Test subprocess orchestrator in non-interactive mode."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "run", "--subprocess", "-i", "What is 3 + 3?", "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        assert result.returncode == 0, f"Subprocess orchestrator failed: {result.stderr}"
        assert "6" in result.stdout, f"Expected '6' in output, got: {result.stdout}"
    
    @pytest.mark.parametrize("prompt,expected", [
        ("What is 2 + 2?", "4"),
        ("What is the capital of France?", "Paris"),
        ("What is 10 * 10?", "100"),
    ])
    def test_non_interactive_various_prompts(self, prompt, expected):
        """Test non-interactive mode with various prompts."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "run", "-i", prompt, "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        assert result.returncode == 0, f"Command failed for prompt '{prompt}': {result.stderr}"
        assert expected in result.stdout, f"Expected '{expected}' in output for prompt '{prompt}', got: {result.stdout}"
    
    def test_hook_service_startup(self):
        """Test that hook service starts when using claude-mpm."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "run", "-i", "test", "--non-interactive"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Check for hook service startup message in stdout or stderr
        combined_output = result.stdout + result.stderr
        assert "hook service started" in combined_output.lower() or "hook" in combined_output.lower(), \
            f"Hook service startup not detected in output: {combined_output}"
    
    def test_invalid_command(self):
        """Test handling of invalid commands."""
        result = subprocess.run(
            [str(CLAUDE_MPM_SCRIPT), "invalid-command"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Should fail with non-zero exit code
        assert result.returncode != 0, "Invalid command should fail"
        # Should show error or usage
        assert "error" in result.stderr.lower() or "usage" in result.stderr.lower(), \
            f"Invalid command should show error or usage: {result.stderr}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])