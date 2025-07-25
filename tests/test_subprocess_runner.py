"""Tests for the SubprocessRunner utility."""

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.utils.subprocess_runner import (
    SubprocessRunner, SubprocessResult, OutputMode,
    quick_run, quick_run_with_timeout, quick_run_async
)


class TestSubprocessRunner:
    """Test cases for SubprocessRunner functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = SubprocessRunner()
    
    def test_basic_run_success(self):
        """Test successful command execution."""
        result = self.runner.run(['echo', 'Hello, World!'])
        
        assert result.success is True
        assert result.returncode == 0
        assert result.stdout.strip() == 'Hello, World!'
        assert result.stderr == ''
        assert result.timed_out is False
        assert result.error is None
        assert result.execution_time > 0
    
    def test_basic_run_failure(self):
        """Test failed command execution."""
        # Use a command that will fail
        result = self.runner.run(['ls', '/nonexistent/directory/path'])
        
        assert result.success is False
        assert result.returncode != 0
        assert 'No such file or directory' in result.stderr or 'cannot access' in result.stderr
        assert result.timed_out is False
    
    def test_run_with_timeout_success(self):
        """Test command execution with timeout that completes."""
        result = self.runner.run_with_timeout(['echo', 'Quick test'], timeout=5.0)
        
        assert result.success is True
        assert result.returncode == 0
        assert result.stdout.strip() == 'Quick test'
        assert result.timed_out is False
        assert result.execution_time < 5.0
    
    def test_run_with_timeout_exceeded(self):
        """Test command execution that times out."""
        # Create a command that will sleep longer than timeout
        result = self.runner.run_with_timeout(['sleep', '3'], timeout=1.0)
        
        assert result.success is False
        assert result.timed_out is True
        assert result.execution_time >= 1.0
        assert result.execution_time < 2.0  # Should stop shortly after timeout
    
    def test_capture_output_modes(self):
        """Test different output capture modes."""
        # Test STDOUT_ONLY
        result = self.runner.capture_output(
            ['echo', 'stdout message'],
            mode=OutputMode.STDOUT_ONLY
        )
        assert result.stdout.strip() == 'stdout message'
        assert result.stderr == ''
        assert result.combined_output.strip() == 'stdout message'
        
        # Test SEPARATE mode (default)
        result = self.runner.capture_output(
            ['echo', 'test'],
            mode=OutputMode.SEPARATE
        )
        assert result.stdout.strip() == 'test'
        assert result.stderr == ''
    
    def test_working_directory(self):
        """Test command execution with custom working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file in temp directory
            test_file = Path(tmpdir) / 'test.txt'
            test_file.write_text('test content')
            
            # Run command in that directory
            result = self.runner.run(['ls'], cwd=tmpdir)
            
            assert result.success is True
            assert 'test.txt' in result.stdout
    
    def test_environment_variables(self):
        """Test command execution with custom environment variables."""
        custom_env = {'TEST_VAR': 'test_value'}
        
        # Run command that outputs environment variable
        result = self.runner.run(
            ['sh', '-c', 'echo $TEST_VAR'],
            env=custom_env
        )
        
        assert result.success is True
        assert result.stdout.strip() == 'test_value'
    
    def test_input_to_subprocess(self):
        """Test sending input to subprocess stdin."""
        # Use a command that reads from stdin
        result = self.runner.run(
            ['cat'],
            input='Hello from stdin'
        )
        
        assert result.success is True
        assert result.stdout == 'Hello from stdin'
    
    @pytest.mark.asyncio
    async def test_async_run(self):
        """Test asynchronous command execution."""
        result = await self.runner.run_async(['echo', 'Async test'])
        
        assert result.success is True
        assert result.returncode == 0
        assert result.stdout.strip() == 'Async test'
        assert result.timed_out is False
    
    @pytest.mark.asyncio
    async def test_async_run_with_timeout(self):
        """Test asynchronous command execution with timeout."""
        result = await self.runner.run_async(
            ['sleep', '3'],
            timeout=1.0
        )
        
        assert result.success is False
        assert result.timed_out is True
        assert result.execution_time >= 1.0
        assert result.execution_time < 2.0
    
    def test_managed_process_context_manager(self):
        """Test managed process context manager."""
        with self.runner.managed_process(
            ['cat'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        ) as proc:
            # Send input and get output
            stdout, stderr = proc.communicate(input='Test input\n', timeout=1)
            
            assert stdout == 'Test input\n'
            assert proc.returncode == 0
    
    def test_run_shell_command(self):
        """Test shell command execution."""
        result = self.runner.run_shell('echo "Shell test" | tr a-z A-Z')
        
        assert result.success is True
        assert result.stdout.strip() == 'SHELL TEST'
    
    def test_quick_run_convenience_function(self):
        """Test quick_run convenience function."""
        result = quick_run(['echo', 'Quick run test'])
        
        assert result.success is True
        assert result.stdout.strip() == 'Quick run test'
    
    def test_quick_run_with_timeout_convenience_function(self):
        """Test quick_run_with_timeout convenience function."""
        result = quick_run_with_timeout(['echo', 'Timeout test'], timeout=5.0)
        
        assert result.success is True
        assert result.stdout.strip() == 'Timeout test'
        assert result.execution_time < 5.0
    
    @pytest.mark.asyncio
    async def test_quick_run_async_convenience_function(self):
        """Test quick_run_async convenience function."""
        result = await quick_run_async(['echo', 'Async quick test'])
        
        assert result.success is True
        assert result.stdout.strip() == 'Async quick test'
    
    def test_subprocess_result_properties(self):
        """Test SubprocessResult dataclass properties."""
        # Create a successful result
        result = SubprocessResult(
            command=['test', 'command'],
            returncode=0,
            stdout='output',
            stderr='',
            execution_time=1.0
        )
        assert result.success is True
        
        # Create a failed result
        failed_result = SubprocessResult(
            command=['test', 'command'],
            returncode=1,
            stdout='',
            stderr='error',
            execution_time=1.0
        )
        assert failed_result.success is False
        
        # Create a timed out result
        timeout_result = SubprocessResult(
            command=['test', 'command'],
            returncode=0,
            stdout='',
            stderr='',
            execution_time=1.0,
            timed_out=True
        )
        assert timeout_result.success is False
    
    def test_error_handling(self):
        """Test error handling for invalid commands."""
        # Try to run a non-existent command
        result = self.runner.run(['this_command_does_not_exist'])
        
        assert result.success is False
        assert result.error is not None
        assert result.returncode == -1


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])