"""Unified Claude CLI launcher for all orchestrators."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, IO
import logging
from enum import Enum

from ..utils.logger import get_logger


class LaunchMode(Enum):
    """Claude launch modes."""
    INTERACTIVE = "interactive"
    PRINT = "print"
    SYSTEM_PROMPT = "system_prompt"


class ClaudeLauncher:
    """Centralized Claude CLI launcher using subprocess.Popen."""
    
    def __init__(
        self,
        model: str = "opus",
        skip_permissions: bool = True,
        log_level: str = "INFO"
    ):
        """Initialize Claude launcher.
        
        Args:
            model: Claude model to use (default: opus)
            skip_permissions: Whether to add --dangerously-skip-permissions flag
            log_level: Logging level
        """
        self.model = model
        self.skip_permissions = skip_permissions
        self.logger = get_logger(self.__class__.__name__)
        self.claude_path = self._find_claude_executable()
        
        if not self.claude_path:
            raise RuntimeError("Claude executable not found in PATH")
    
    def _find_claude_executable(self) -> Optional[str]:
        """Find Claude executable in PATH.
        
        Returns:
            Path to claude executable or None if not found
        """
        # Check common locations first
        common_paths = [
            "/usr/local/bin/claude",
            "/opt/homebrew/bin/claude",
            os.path.expanduser("~/.local/bin/claude"),
        ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                self.logger.debug(f"Found claude at: {path}")
                return path
        
        # Fall back to PATH search
        for path_dir in os.environ.get("PATH", "").split(os.pathsep):
            claude_path = os.path.join(path_dir, "claude")
            if os.path.exists(claude_path) and os.access(claude_path, os.X_OK):
                self.logger.debug(f"Found claude at: {claude_path}")
                return claude_path
        
        return None
    
    def build_command(
        self,
        mode: LaunchMode = LaunchMode.INTERACTIVE,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> List[str]:
        """Build command array based on mode and options.
        
        Args:
            mode: Launch mode (interactive, print, or system_prompt)
            session_id: Optional session ID for Claude
            system_prompt: System prompt content (for system_prompt mode)
            extra_args: Additional command line arguments
            
        Returns:
            Command array ready for subprocess
        """
        cmd = [self.claude_path]
        
        # Always add model
        cmd.extend(["--model", self.model])
        
        # Add permissions flag if enabled
        if self.skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        
        # Add session ID if provided
        if session_id:
            cmd.extend(["--session-id", session_id])
        
        # Mode-specific flags
        if mode == LaunchMode.PRINT:
            cmd.append("--print")
        elif mode == LaunchMode.SYSTEM_PROMPT and system_prompt:
            cmd.extend(["--append-system-prompt", system_prompt])
        
        # Add any extra arguments
        if extra_args:
            cmd.extend(extra_args)
        
        self.logger.debug(f"Built command: {' '.join(cmd)}")
        return cmd
    
    def launch(
        self,
        mode: LaunchMode = LaunchMode.INTERACTIVE,
        input_text: Optional[str] = None,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        stdin: Optional[Union[int, IO]] = None,
        stdout: Optional[Union[int, IO]] = None,
        stderr: Optional[Union[int, IO]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        **popen_kwargs
    ) -> subprocess.Popen:
        """Launch Claude using subprocess.Popen.
        
        This is the single unified endpoint for all Claude launches.
        
        Args:
            mode: Launch mode
            input_text: Input text for print mode
            session_id: Optional session ID
            system_prompt: System prompt for system_prompt mode
            extra_args: Additional command line arguments
            stdin: stdin for Popen (default: PIPE)
            stdout: stdout for Popen (default: PIPE)
            stderr: stderr for Popen (default: PIPE)
            env: Environment variables
            cwd: Working directory
            **popen_kwargs: Additional arguments passed to Popen
            
        Returns:
            Popen process object
        """
        # Build command
        cmd = self.build_command(
            mode=mode,
            session_id=session_id,
            system_prompt=system_prompt,
            extra_args=extra_args
        )
        
        # For print mode with input text, append it to command
        if mode == LaunchMode.PRINT and input_text and "--print" in cmd:
            cmd.append(input_text)
            input_text = None  # Don't send via stdin
        
        # Set default stdio if not provided
        if stdin is None:
            stdin = subprocess.PIPE
        if stdout is None:
            stdout = subprocess.PIPE
        if stderr is None:
            stderr = subprocess.PIPE
        
        # Prepare environment
        launch_env = os.environ.copy()
        if env:
            launch_env.update(env)
        
        # Log launch details
        self.logger.info(f"Launching Claude in {mode.value} mode")
        
        # Launch process
        process = subprocess.Popen(
            cmd,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=launch_env,
            cwd=cwd,
            text=True,
            **popen_kwargs
        )
        
        # Send input text if provided (for stdin mode)
        if input_text and process.stdin:
            process.stdin.write(input_text)
            process.stdin.flush()
        
        return process
    
    def launch_interactive(
        self,
        session_id: Optional[str] = None,
        **popen_kwargs
    ) -> subprocess.Popen:
        """Convenience method for interactive mode.
        
        Args:
            session_id: Optional session ID
            **popen_kwargs: Arguments passed to Popen
            
        Returns:
            Popen process object
        """
        return self.launch(
            mode=LaunchMode.INTERACTIVE,
            session_id=session_id,
            **popen_kwargs
        )
    
    def launch_oneshot(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_stdin: bool = True,
        timeout: Optional[float] = None
    ) -> Tuple[str, str, int]:
        """Convenience method for one-shot execution with response.
        
        Args:
            message: Message to send to Claude
            session_id: Optional session ID
            use_stdin: Whether to send message via stdin (True) or command line (False)
            timeout: Timeout in seconds for response
            
        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        process = self.launch(
            mode=LaunchMode.PRINT,
            input_text=message if use_stdin else None,
            extra_args=[] if use_stdin else [message],
            session_id=session_id
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return stdout, stderr, process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return stdout, stderr, -1
    
    def launch_with_system_prompt(
        self,
        system_prompt: str,
        session_id: Optional[str] = None,
        **popen_kwargs
    ) -> subprocess.Popen:
        """Convenience method for system prompt mode.
        
        Args:
            system_prompt: System prompt to append
            session_id: Optional session ID
            **popen_kwargs: Arguments passed to Popen
            
        Returns:
            Popen process object
        """
        return self.launch(
            mode=LaunchMode.SYSTEM_PROMPT,
            system_prompt=system_prompt,
            session_id=session_id,
            **popen_kwargs
        )