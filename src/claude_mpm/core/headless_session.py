"""Headless session handler for Claude MPM.

This module provides headless execution that bypasses Rich console rendering
and pipes Claude Code's stream-json output directly to stdout for programmatic
consumption.

WHY: Headless mode is essential for:
- CI/CD pipelines
- Programmatic automation
- Piping output to other tools
- Integration with external systems

DESIGN DECISION: Uses subprocess.communicate() for simple stdin/stdout passthrough
without any Rich formatting, progress bars, or interactive elements.
"""

import os
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from claude_mpm.core.logger import get_logger

# Protocol imports for type checking without circular dependencies
if TYPE_CHECKING:
    from claude_mpm.core.protocols import ClaudeRunnerProtocol
else:
    # At runtime, accept any object with matching interface
    ClaudeRunnerProtocol = Any


class HeadlessSession:
    """Manages headless Claude execution with stream-json output.

    WHY: Headless mode bypasses all Rich console formatting and provides
    clean NDJSON output suitable for programmatic consumption.

    DESIGN DECISION: Minimal wrapper around subprocess that:
    - Reads prompt from stdin or argument
    - Passes stream-json output to stdout without modification
    - Passes stderr to stderr
    - Returns Claude Code's exit code
    """

    def __init__(self, runner: "ClaudeRunnerProtocol"):
        """Initialize the headless session with a reference to the runner.

        Args:
            runner: The ClaudeRunner instance (or any object matching ClaudeRunnerProtocol)
        """
        self.runner: ClaudeRunnerProtocol = runner
        self.logger = get_logger("headless_session")
        self.working_dir = self._get_working_directory()

    def _get_working_directory(self) -> Path:
        """Get the working directory for execution."""
        if "CLAUDE_MPM_USER_PWD" in os.environ:
            return Path(os.environ["CLAUDE_MPM_USER_PWD"])
        return Path.cwd()

    def build_claude_command(
        self, resume_session: Optional[str] = None
    ) -> list:
        """Build the Claude command for headless execution.

        Args:
            resume_session: Optional session ID to resume

        Returns:
            List of command arguments
        """
        # Base command with stream-json output for programmatic consumption
        cmd = ["claude", "--output-format", "stream-json"]

        # Add resume flag if specified
        if resume_session:
            cmd.extend(["--resume", resume_session])

        # Add custom arguments from runner (filtered)
        if self.runner.claude_args:
            # Filter out arguments that don't make sense in headless mode
            filtered_args = [
                arg for arg in self.runner.claude_args
                if arg not in ("--resume",)  # Already handled above
            ]
            cmd.extend(filtered_args)

        return cmd

    def run(
        self,
        prompt: Optional[str] = None,
        resume_session: Optional[str] = None,
    ) -> int:
        """Run Claude Code in headless mode with stream-json output.

        Args:
            prompt: The prompt to send to Claude. If None, reads from stdin.
            resume_session: Optional session ID to resume

        Returns:
            Exit code from Claude Code process
        """
        # Build the command
        cmd = self.build_claude_command(resume_session=resume_session)

        # Get prompt from argument or stdin
        if prompt is None:
            # Read from stdin for piping support
            if sys.stdin.isatty():
                self.logger.warning(
                    "No prompt provided and stdin is a TTY. "
                    "Use -i 'prompt' or pipe input: echo 'prompt' | claude-mpm run --headless"
                )
                return 1
            prompt = sys.stdin.read().strip()

        if not prompt:
            self.logger.error("Empty prompt provided")
            return 1

        # Add the prompt to command
        cmd.extend(["--print", prompt])

        self.logger.debug(f"Headless command: {' '.join(cmd[:5])}...")

        # Prepare environment
        env = self._prepare_environment()

        try:
            # Run subprocess with direct stdout/stderr passthrough
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.working_dir),
                env=env,
            )

            # Communicate and get output
            stdout, stderr = process.communicate()

            # Pass through stdout (stream-json) directly - no Rich formatting
            if stdout:
                sys.stdout.write(stdout)
                sys.stdout.flush()

            # Write stderr to stderr
            if stderr:
                sys.stderr.write(stderr)
                sys.stderr.flush()

            return process.returncode

        except FileNotFoundError:
            sys.stderr.write(
                "Error: Claude CLI not found. "
                "Please ensure 'claude' is installed and in your PATH\n"
            )
            sys.stderr.flush()
            return 127

        except PermissionError as e:
            sys.stderr.write(f"Error: Permission denied executing Claude CLI: {e}\n")
            sys.stderr.flush()
            return 126

        except Exception as e:
            sys.stderr.write(f"Error: Unexpected error: {e}\n")
            sys.stderr.flush()
            return 1

    def _prepare_environment(self) -> dict:
        """Prepare the execution environment."""
        env = os.environ.copy()

        # Disable telemetry for Claude Code
        env["DISABLE_TELEMETRY"] = "1"

        # Ensure no interactive prompts
        env["CI"] = "true"

        return env


def run_headless(
    prompt: Optional[str] = None,
    resume_session: Optional[str] = None,
    claude_args: Optional[list] = None,
) -> int:
    """Convenience function to run Claude in headless mode.

    Args:
        prompt: The prompt to send to Claude. If None, reads from stdin.
        resume_session: Optional session ID to resume
        claude_args: Additional arguments for Claude CLI

    Returns:
        Exit code from Claude Code process
    """
    # Create a minimal runner-like object for HeadlessSession
    class MinimalRunner:
        def __init__(self, args):
            self.claude_args = args or []

    runner = MinimalRunner(claude_args)
    session = HeadlessSession(runner)
    return session.run(prompt=prompt, resume_session=resume_session)
