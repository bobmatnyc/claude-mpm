#!/usr/bin/env python3
"""
Subprocess utilities for Claude MPM.

This module provides enhanced subprocess execution and management utilities
with proper error handling, timeouts, and process cleanup.
"""

import asyncio
import contextlib
import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional

import psutil

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class SubprocessError(Exception):
    """Unified exception for subprocess errors."""

    def __init__(
        self,
        message: str,
        returncode: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
    ):
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class SubprocessResult:
    """Result object for subprocess execution."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    @property
    def success(self) -> bool:
        """True if the subprocess completed successfully."""
        return self.returncode == 0


def run_command(command_string: str, timeout: float = 60) -> str:
    """
    Runs a command securely, avoiding shell injection.

    Args:
        command_string: Command string to execute
        timeout: Maximum time to wait for completion (seconds)

    Returns:
        Command stdout output

    Raises:
        SubprocessError: If the command fails or times out
    """
    # Split command string into a list to avoid shell=True
    command_parts = shlex.split(command_string)
    try:
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            check=True,  # Raise an exception for non-zero exit codes
            timeout=timeout,  # Prevent the process from hanging
        )
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        # Log the error, including stderr for better debugging
        stderr = e.stderr if hasattr(e, "stderr") else "N/A"
        logger.error(f'Command "{command_string}" failed: {stderr}')
        raise SubprocessError(
            f'Command "{command_string}" failed: {stderr}',
            returncode=getattr(e, "returncode", None),
            stdout=getattr(e, "stdout", ""),
            stderr=stderr,
        ) from e


def run_subprocess(
    cmd: List[str],
    timeout: Optional[float] = None,
    capture_output: bool = True,
    text: bool = True,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    **kwargs,
) -> SubprocessResult:
    """
    Run a subprocess with enhanced error handling and timeout support.

    Args:
        cmd: Command and arguments to execute
        timeout: Maximum time to wait for completion (seconds)
        capture_output: Whether to capture stdout/stderr
        text: Whether to return text (True) or bytes (False)
        cwd: Working directory for the subprocess
        env: Environment variables for the subprocess
        **kwargs: Additional arguments passed to subprocess.run

    Returns:
        SubprocessResult object with returncode, stdout, stderr

    Raises:
        SubprocessError: If the subprocess fails or times out
    """
    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=capture_output,
            text=text,
            cwd=cwd,
            env=env,
            **kwargs,
            check=False,
        )

        return SubprocessResult(
            returncode=result.returncode,
            stdout=result.stdout if capture_output else "",
            stderr=result.stderr if capture_output else "",
        )

    except subprocess.TimeoutExpired as e:
        raise SubprocessError(
            f"Command timed out after {timeout}s: {' '.join(cmd)}",
            returncode=None,
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "",
        ) from e
    except subprocess.CalledProcessError as e:
        raise SubprocessError(
            f"Command failed with return code {e.returncode}: {' '.join(cmd)}",
            returncode=e.returncode,
            stdout=e.stdout if e.stdout else "",
            stderr=e.stderr if e.stderr else "",
        ) from e
    except Exception as e:
        raise SubprocessError(f"Subprocess execution failed: {e}") from e


async def run_subprocess_async(
    cmd: List[str],
    timeout: Optional[float] = None,
    capture_output: bool = True,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    **kwargs,
) -> SubprocessResult:
    """
    Run a subprocess asynchronously with timeout support.

    Args:
        cmd: Command and arguments to execute
        timeout: Maximum time to wait for completion (seconds)
        capture_output: Whether to capture stdout/stderr
        cwd: Working directory for the subprocess
        env: Environment variables for the subprocess
        **kwargs: Additional arguments passed to asyncio.create_subprocess_exec

    Returns:
        SubprocessResult object with returncode, stdout, stderr

    Raises:
        SubprocessError: If the subprocess fails or times out
    """
    try:
        if capture_output:
            stdout = asyncio.subprocess.PIPE
            stderr = asyncio.subprocess.PIPE
        else:
            stdout = None
            stderr = None

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=stdout, stderr=stderr, cwd=cwd, env=env, **kwargs
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise SubprocessError(
                f"Command timed out after {timeout}s: {' '.join(cmd)}", returncode=None
            ) from None

        return SubprocessResult(
            returncode=process.returncode,
            stdout=stdout_data.decode() if stdout_data else "",
            stderr=stderr_data.decode() if stderr_data else "",
        )

    except Exception as e:
        if not isinstance(e, SubprocessError):
            raise SubprocessError(f"Async subprocess execution failed: {e}") from e
        raise


def terminate_process_tree(pid: int, timeout: float = 5.0) -> int:
    """
    Terminate a process and all its children.

    Args:
        pid: Process ID to terminate
        timeout: Time to wait for graceful termination before force killing

    Returns:
        Number of processes terminated

    Raises:
        SubprocessError: If the process cannot be terminated
    """
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return 0

    # Get all child processes recursively
    children = parent.children(recursive=True)
    processes = [parent, *children]

    terminated_count = 0

    # First, try graceful termination
    for process in processes:
        with contextlib.suppress(psutil.NoSuchProcess):
            process.terminate()

    # Wait for processes to terminate gracefully
    gone, alive = psutil.wait_procs(processes, timeout=timeout)
    terminated_count += len(gone)

    # Force kill any remaining processes
    for process in alive:
        try:
            process.kill()
            terminated_count += 1
        except psutil.NoSuchProcess:
            pass

    return terminated_count


def get_process_info(pid: Optional[int] = None) -> Dict[str, Any]:
    """
    Get information about a process.

    Args:
        pid: Process ID (defaults to current process)

    Returns:
        Dictionary with process information
    """
    try:
        process = psutil.Process(pid)
        return {
            "pid": process.pid,
            "name": process.name(),
            "status": process.status(),
            "create_time": process.create_time(),
            "cpu_percent": process.cpu_percent(),
            "memory_info": process.memory_info()._asdict(),
            "cmdline": process.cmdline(),
            "cwd": process.cwd() if hasattr(process, "cwd") else None,
            "num_threads": process.num_threads(),
            "children": [child.pid for child in process.children()],
        }
    except psutil.NoSuchProcess:
        return {"error": f"Process {pid} not found"}
    except Exception as e:
        return {"error": str(e)}


def monitor_process_resources(pid: int) -> Optional[Dict[str, Any]]:
    """
    Monitor resource usage of a process.

    Args:
        pid: Process ID to monitor

    Returns:
        Dictionary with resource information or None if process not found
    """
    try:
        process = psutil.Process(pid)
        memory_info = process.memory_info()

        return {
            "pid": pid,
            "cpu_percent": process.cpu_percent(),
            "memory_mb": memory_info.rss / 1024 / 1024,  # Convert to MB
            "memory_percent": process.memory_percent(),
            "num_threads": process.num_threads(),
            "status": process.status(),
            "create_time": process.create_time(),
        }
    except psutil.NoSuchProcess:
        return None
    except Exception:
        return None


def cleanup_orphaned_processes(pattern: str, max_age_hours: float = 1.0) -> int:
    """
    Clean up orphaned processes matching a pattern.

    Args:
        pattern: String pattern to match in process command line
        max_age_hours: Maximum age in hours before considering a process orphaned

    Returns:
        Number of processes cleaned up
    """
    current_time = time.time()
    cleanup_count = 0

    for process in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cmdline = " ".join(process.info["cmdline"] or [])
            if pattern in cmdline:
                # Check if process is old enough to be considered orphaned
                age_hours = (current_time - process.info["create_time"]) / 3600
                if age_hours > max_age_hours:
                    process.terminate()
                    cleanup_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return cleanup_count
