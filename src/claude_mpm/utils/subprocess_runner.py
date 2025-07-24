"""
SubprocessRunner utility for consolidated subprocess execution patterns.

This module provides a unified interface for subprocess operations across
the claude-mpm framework, reducing code duplication and standardizing
error handling, timeout management, and output capture.

Features:
- Synchronous and asynchronous subprocess execution
- Timeout management with graceful termination
- Output capture (stdout, stderr, combined)
- Environment variable and working directory support
- Comprehensive error handling and logging
- Process lifecycle management
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager


class OutputMode(Enum):
    """Output capture modes for subprocess execution."""
    STDOUT_ONLY = "stdout"
    STDERR_ONLY = "stderr"
    COMBINED = "combined"
    SEPARATE = "separate"
    NONE = "none"


@dataclass
class SubprocessResult:
    """Result of a subprocess execution."""
    command: List[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    combined_output: str = ""
    execution_time: float = 0.0
    timed_out: bool = False
    error: Optional[Exception] = None
    
    @property
    def success(self) -> bool:
        """Check if the subprocess execution was successful."""
        return self.returncode == 0 and not self.timed_out and self.error is None


class SubprocessRunner:
    """
    Unified subprocess execution utility for the claude-mpm framework.
    
    This class consolidates subprocess patterns found throughout the codebase,
    providing a consistent interface for process execution with comprehensive
    error handling, timeout management, and output capture.
    
    Examples:
        # Basic usage
        runner = SubprocessRunner()
        result = runner.run(['ls', '-la'])
        if result.success:
            print(result.stdout)
        
        # With timeout
        result = runner.run_with_timeout(['long-running-command'], timeout=30)
        if result.timed_out:
            print("Command timed out")
        
        # Capture output modes
        result = runner.capture_output(['command'], mode=OutputMode.COMBINED)
        print(result.combined_output)
        
        # Async execution
        async def main():
            result = await runner.run_async(['command'])
            print(result.stdout)
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the SubprocessRunner.
        
        Args:
            logger: Optional logger instance. If not provided, creates a default logger.
        """
        self.logger = logger or logging.getLogger(__name__)
        
    def run(
        self,
        command: List[str],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
        text: bool = True,
        check: bool = False,
        input: Optional[str] = None,
        **kwargs
    ) -> SubprocessResult:
        """
        Execute a subprocess with standard options.
        
        Args:
            command: Command and arguments as a list
            cwd: Working directory for the subprocess
            env: Environment variables (merged with current environment)
            capture_output: Whether to capture stdout/stderr
            text: Whether to decode output as text
            check: Whether to raise exception on non-zero exit
            input: Input to send to subprocess stdin
            **kwargs: Additional arguments passed to subprocess.run
            
        Returns:
            SubprocessResult containing execution details
        """
        start_time = time.time()
        
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # Log command execution
        self.logger.debug(f"Running command: {' '.join(command)}")
        if cwd:
            self.logger.debug(f"Working directory: {cwd}")
        
        try:
            # Execute subprocess
            result = subprocess.run(
                command,
                cwd=cwd,
                env=process_env,
                capture_output=capture_output,
                text=text,
                check=check,
                input=input,
                **kwargs
            )
            
            execution_time = time.time() - start_time
            
            return SubprocessResult(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout if capture_output else "",
                stderr=result.stderr if capture_output else "",
                combined_output=(result.stdout + result.stderr) if capture_output else "",
                execution_time=execution_time
            )
            
        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            return SubprocessResult(
                command=command,
                returncode=e.returncode,
                stdout=e.stdout if capture_output else "",
                stderr=e.stderr if capture_output else "",
                combined_output=(e.stdout + e.stderr) if capture_output else "",
                execution_time=execution_time,
                error=e
            )
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error running command: {e}")
            return SubprocessResult(
                command=command,
                returncode=-1,
                execution_time=execution_time,
                error=e
            )
    
    def run_with_timeout(
        self,
        command: List[str],
        timeout: float,
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
        text: bool = True,
        **kwargs
    ) -> SubprocessResult:
        """
        Execute a subprocess with timeout management.
        
        Args:
            command: Command and arguments as a list
            timeout: Maximum execution time in seconds
            cwd: Working directory for the subprocess
            env: Environment variables
            capture_output: Whether to capture stdout/stderr
            text: Whether to decode output as text
            **kwargs: Additional arguments passed to subprocess.run
            
        Returns:
            SubprocessResult containing execution details
        """
        start_time = time.time()
        
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        self.logger.debug(f"Running command with timeout {timeout}s: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=process_env,
                capture_output=capture_output,
                text=text,
                timeout=timeout,
                **kwargs
            )
            
            execution_time = time.time() - start_time
            
            return SubprocessResult(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout if capture_output else "",
                stderr=result.stderr if capture_output else "",
                combined_output=(result.stdout + result.stderr) if capture_output else "",
                execution_time=execution_time
            )
            
        except subprocess.TimeoutExpired as e:
            execution_time = time.time() - start_time
            self.logger.warning(f"Command timed out after {execution_time:.1f}s")
            
            # Try to get partial output if available
            stdout = e.stdout if hasattr(e, 'stdout') and e.stdout else ""
            stderr = e.stderr if hasattr(e, 'stderr') and e.stderr else ""
            
            return SubprocessResult(
                command=command,
                returncode=-1,
                stdout=stdout,
                stderr=stderr,
                combined_output=stdout + stderr,
                execution_time=execution_time,
                timed_out=True,
                error=e
            )
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error running command: {e}")
            return SubprocessResult(
                command=command,
                returncode=-1,
                execution_time=execution_time,
                error=e
            )
    
    def capture_output(
        self,
        command: List[str],
        mode: OutputMode = OutputMode.SEPARATE,
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> SubprocessResult:
        """
        Execute a subprocess with specific output capture mode.
        
        Args:
            command: Command and arguments as a list
            mode: Output capture mode
            cwd: Working directory for the subprocess
            env: Environment variables
            timeout: Optional timeout in seconds
            **kwargs: Additional arguments passed to subprocess
            
        Returns:
            SubprocessResult with captured output according to mode
        """
        # Handle output mode
        if mode == OutputMode.NONE:
            capture_output = False
            stdout_target = None
            stderr_target = None
        elif mode == OutputMode.COMBINED:
            capture_output = False
            stdout_target = subprocess.PIPE
            stderr_target = subprocess.STDOUT
        else:
            capture_output = True
            stdout_target = None
            stderr_target = None
        
        # Prepare kwargs
        run_kwargs = kwargs.copy()
        if stdout_target is not None:
            run_kwargs['stdout'] = stdout_target
        if stderr_target is not None:
            run_kwargs['stderr'] = stderr_target
        
        # Execute with or without timeout
        if timeout:
            result = self.run_with_timeout(
                command, timeout, cwd=cwd, env=env, 
                capture_output=capture_output, **run_kwargs
            )
        else:
            result = self.run(
                command, cwd=cwd, env=env,
                capture_output=capture_output, **run_kwargs
            )
        
        # Process output based on mode
        if mode == OutputMode.STDOUT_ONLY:
            result.stderr = ""
            result.combined_output = result.stdout
        elif mode == OutputMode.STDERR_ONLY:
            result.stdout = ""
            result.combined_output = result.stderr
        elif mode == OutputMode.COMBINED and result.stdout:
            result.combined_output = result.stdout
            result.stderr = ""
        
        return result
    
    async def run_async(
        self,
        command: List[str],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> SubprocessResult:
        """
        Execute a subprocess asynchronously.
        
        Args:
            command: Command and arguments as a list
            cwd: Working directory for the subprocess
            env: Environment variables
            timeout: Optional timeout in seconds
            **kwargs: Additional arguments for the process
            
        Returns:
            SubprocessResult containing execution details
        """
        start_time = time.time()
        
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        self.logger.debug(f"Running async command: {' '.join(command)}")
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=process_env,
                **kwargs
            )
            
            # Wait for completion with optional timeout
            if timeout:
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=timeout
                    )
                    timed_out = False
                except asyncio.TimeoutError:
                    self.logger.warning(f"Async command timed out after {timeout}s")
                    process.terminate()
                    await asyncio.sleep(0.1)  # Give it a moment to terminate
                    if process.returncode is None:
                        process.kill()
                    stdout, stderr = await process.communicate()
                    timed_out = True
            else:
                stdout, stderr = await process.communicate()
                timed_out = False
            
            execution_time = time.time() - start_time
            
            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            return SubprocessResult(
                command=command,
                returncode=process.returncode if process.returncode is not None else -1,
                stdout=stdout_str,
                stderr=stderr_str,
                combined_output=stdout_str + stderr_str,
                execution_time=execution_time,
                timed_out=timed_out
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error running async command: {e}")
            return SubprocessResult(
                command=command,
                returncode=-1,
                execution_time=execution_time,
                error=e
            )
    
    @contextmanager
    def managed_process(
        self,
        command: List[str],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Context manager for managed subprocess execution.
        
        Ensures proper cleanup of subprocess resources.
        
        Args:
            command: Command and arguments as a list
            cwd: Working directory for the subprocess
            env: Environment variables
            **kwargs: Additional arguments for subprocess.Popen
            
        Yields:
            subprocess.Popen instance
            
        Example:
            with runner.managed_process(['long-running-command']) as proc:
                # Interact with process
                stdout, stderr = proc.communicate(timeout=30)
        """
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        process = None
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=process_env,
                **kwargs
            )
            yield process
        finally:
            if process and process.poll() is None:
                # Process is still running, terminate it
                self.logger.debug("Terminating managed process")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Force killing process")
                    process.kill()
                    process.wait()
    
    def run_shell(
        self,
        command: str,
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> SubprocessResult:
        """
        Execute a shell command (use with caution).
        
        Args:
            command: Shell command as a string
            cwd: Working directory for the subprocess
            env: Environment variables
            timeout: Optional timeout in seconds
            **kwargs: Additional arguments
            
        Returns:
            SubprocessResult containing execution details
            
        Warning:
            Shell execution can be a security risk. Use only with trusted input.
        """
        self.logger.warning("Using shell execution - ensure command is from trusted source")
        
        # Set shell=True in kwargs
        kwargs['shell'] = True
        
        if timeout:
            return self.run_with_timeout(
                [command], timeout, cwd=cwd, env=env, **kwargs
            )
        else:
            return self.run([command], cwd=cwd, env=env, **kwargs)


# Convenience functions for common patterns
def quick_run(command: List[str], **kwargs) -> SubprocessResult:
    """Quick subprocess execution without creating a runner instance."""
    return SubprocessRunner().run(command, **kwargs)


def quick_run_with_timeout(command: List[str], timeout: float, **kwargs) -> SubprocessResult:
    """Quick subprocess execution with timeout."""
    return SubprocessRunner().run_with_timeout(command, timeout, **kwargs)


async def quick_run_async(command: List[str], **kwargs) -> SubprocessResult:
    """Quick async subprocess execution."""
    return await SubprocessRunner().run_async(command, **kwargs)