"""
Enhanced SubprocessRunner with comprehensive logging.

This module extends the base SubprocessRunner with detailed logging for:
- Process spawning with command details
- Process lifecycle events
- Stdout/stderr capture details
- Errors and exceptions
"""

import logging
import os
from typing import Optional

from claude_mpm.utils.subprocess_runner import SubprocessRunner as BaseRunner

# Create module-level logger
logger = logging.getLogger(__name__)


class EnhancedSubprocessRunner(BaseRunner):
    """SubprocessRunner with comprehensive logging enhancements."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize with enhanced logging."""
        # Use provided logger or module logger
        self.logger = logger or globals()['logger']
        
        # Initialize base class with our logger
        super().__init__(logger=self.logger)
        
        # Additional tracking
        self._process_count = 0
        self._total_execution_time = 0.0
        self._success_count = 0
        self._failure_count = 0
        
        self.logger.info("Enhanced SubprocessRunner initialized")
        
    def run(self, *args, **kwargs):
        """Override run method with enhanced logging."""
        # Generate process ID
        self._process_count += 1
        process_id = f"PROC-{self._process_count}"
        
        # Extract command for logging
        command = args[0] if args else kwargs.get('command', [])
        
        # Log comprehensive details
        self.logger.info(f"[{process_id}] Starting subprocess: {' '.join(command)}")
        self.logger.debug(f"[{process_id}] Full arguments: args={args}, kwargs={kwargs}")
        
        # Log environment details
        env = kwargs.get('env', {})
        if env:
            self.logger.debug(f"[{process_id}] Custom environment variables: {len(env)} entries")
            for key in sorted(env.keys()):
                if any(sensitive in key.lower() for sensitive in ['key', 'token', 'password', 'secret', 'auth']):
                    self.logger.debug(f"[{process_id}]   {key}: [MASKED]")
                else:
                    self.logger.debug(f"[{process_id}]   {key}: {env[key]}")
        
        # Call parent method
        result = super().run(*args, **kwargs)
        
        # Update statistics
        self._total_execution_time += result.execution_time
        if result.success:
            self._success_count += 1
        else:
            self._failure_count += 1
        
        # Log result details
        self._log_result(process_id, result)
        
        return result
    
    def run_with_timeout(self, *args, **kwargs):
        """Override run_with_timeout with enhanced logging."""
        # Generate process ID
        self._process_count += 1
        process_id = f"PROC-{self._process_count}"
        
        # Extract command and timeout
        command = args[0] if args else kwargs.get('command', [])
        timeout = args[1] if len(args) > 1 else kwargs.get('timeout', 'unknown')
        
        self.logger.info(
            f"[{process_id}] Starting subprocess with timeout {timeout}s: "
            f"{' '.join(command)}"
        )
        
        # Call parent method
        result = super().run_with_timeout(*args, **kwargs)
        
        # Update statistics
        self._total_execution_time += result.execution_time
        if result.success:
            self._success_count += 1
        else:
            self._failure_count += 1
        
        # Log result details
        self._log_result(process_id, result, timeout=timeout)
        
        return result
    
    async def run_async(self, *args, **kwargs):
        """Override run_async with enhanced logging."""
        # Generate process ID
        self._process_count += 1
        process_id = f"PROC-{self._process_count}"
        
        # Extract command
        command = args[0] if args else kwargs.get('command', [])
        timeout = kwargs.get('timeout')
        
        self.logger.info(f"[{process_id}] Starting async subprocess: {' '.join(command)}")
        if timeout:
            self.logger.debug(f"[{process_id}] Timeout: {timeout}s")
        
        # Call parent method
        result = await super().run_async(*args, **kwargs)
        
        # Update statistics
        self._total_execution_time += result.execution_time
        if result.success:
            self._success_count += 1
        else:
            self._failure_count += 1
        
        # Log result details
        self._log_result(process_id, result, is_async=True)
        
        return result
    
    def _log_result(self, process_id: str, result, timeout=None, is_async=False):
        """Log detailed result information."""
        # Basic completion info
        status = "completed" if result.success else "failed"
        async_prefix = "Async " if is_async else ""
        
        if result.timed_out:
            self.logger.warning(
                f"[{process_id}] {async_prefix}Subprocess timed out after "
                f"{result.execution_time:.3f}s (timeout was {timeout}s)"
            )
        elif result.success:
            self.logger.info(
                f"[{process_id}] {async_prefix}Subprocess {status}: "
                f"returncode={result.returncode}, "
                f"execution_time={result.execution_time:.3f}s"
            )
        else:
            self.logger.error(
                f"[{process_id}] {async_prefix}Subprocess {status}: "
                f"returncode={result.returncode}, "
                f"execution_time={result.execution_time:.3f}s"
            )
        
        # Log stdout
        if result.stdout:
            lines = result.stdout.count('\n')
            self.logger.debug(
                f"[{process_id}] Stdout: {len(result.stdout)} characters, {lines} lines"
            )
            if len(result.stdout) < 500:
                self.logger.debug(f"[{process_id}] Stdout content:\n{result.stdout}")
            else:
                self.logger.debug(
                    f"[{process_id}] Stdout content (first 500 chars):\n"
                    f"{result.stdout[:500]}..."
                )
        
        # Log stderr
        if result.stderr:
            lines = result.stderr.count('\n')
            level = logging.WARNING if result.returncode != 0 else logging.DEBUG
            self.logger.log(
                level,
                f"[{process_id}] Stderr: {len(result.stderr)} characters, {lines} lines"
            )
            if len(result.stderr) < 500:
                self.logger.log(level, f"[{process_id}] Stderr content:\n{result.stderr}")
            else:
                self.logger.log(
                    level,
                    f"[{process_id}] Stderr content (first 500 chars):\n"
                    f"{result.stderr[:500]}..."
                )
        
        # Log error details
        if result.error:
            self.logger.error(
                f"[{process_id}] Exception: {type(result.error).__name__}: {result.error}"
            )
    
    def get_statistics(self):
        """Get subprocess execution statistics."""
        stats = {
            'total_processes': self._process_count,
            'successful_processes': self._success_count,
            'failed_processes': self._failure_count,
            'total_execution_time': self._total_execution_time,
            'average_execution_time': (
                self._total_execution_time / self._process_count 
                if self._process_count > 0 else 0
            )
        }
        
        self.logger.info(
            f"Subprocess statistics: "
            f"total={stats['total_processes']}, "
            f"success={stats['successful_processes']}, "
            f"failed={stats['failed_processes']}, "
            f"avg_time={stats['average_execution_time']:.3f}s"
        )
        
        return stats


# Convenience function
def create_enhanced_runner(logger: Optional[logging.Logger] = None) -> EnhancedSubprocessRunner:
    """Create an enhanced subprocess runner with logging."""
    return EnhancedSubprocessRunner(logger=logger)