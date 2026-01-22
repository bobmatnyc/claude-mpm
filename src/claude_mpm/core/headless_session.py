"""Headless session handler for Claude MPM.

This module provides headless execution that bypasses Rich console rendering
and pipes Claude Code's stream-json output directly to stdout for programmatic
consumption.

WHY: Headless mode is essential for:
- CI/CD pipelines
- Programmatic automation
- Piping output to other tools
- Integration with external systems

DESIGN DECISION: Uses real-time streaming for stdin/stdout passthrough
without any Rich formatting, progress bars, or interactive elements.
Output is streamed line-by-line for vibe-kanban compatibility.
"""

import os
import subprocess  # nosec B404
import sys
import threading
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

    def _has_adjacent_args(self, args: list, flag: str, value: str) -> bool:
        """Check if flag is followed by value in args list.

        This handles space-separated CLI args like: --input-format stream-json
        where args = ["--input-format", "stream-json", ...]

        Args:
            args: List of command-line arguments
            flag: The flag to look for (e.g., "--input-format")
            value: The expected value following the flag (e.g., "stream-json")

        Returns:
            True if flag is immediately followed by value in the args list
        """
        try:
            idx = args.index(flag)
            return idx + 1 < len(args) and args[idx + 1] == value
        except ValueError:
            return False

    def build_claude_command(
        self, resume_session: Optional[str] = None
    ) -> list:
        """Build the Claude command for headless execution.

        Args:
            resume_session: Optional session ID to resume

        Returns:
            List of command arguments
        """
        # Check if --output-format is already in claude_args (from passthrough flags)
        has_output_format = any(
            arg == "--output-format" for arg in (self.runner.claude_args or [])
        )

        # Base command - only add stream-json if no output format specified
        # --verbose is required when using --print with --output-format=stream-json
        if has_output_format:
            cmd = ["claude", "--verbose"]
        else:
            cmd = ["claude", "--verbose", "--output-format", "stream-json"]

        # Add resume flag if specified
        if resume_session:
            cmd.extend(["--resume", resume_session])

        # Add custom arguments from runner (filtered)
        if self.runner.claude_args:
            # Filter out arguments that don't make sense in headless mode
            # If resume_session is provided, skip --resume and the following session ID
            filtered_args = []
            skip_next = False
            for i, arg in enumerate(self.runner.claude_args):
                if skip_next:
                    skip_next = False
                    continue
                if arg == "--resume":
                    if resume_session:
                        # Skip --resume and check if next arg is a session ID
                        if i + 1 < len(self.runner.claude_args):
                            next_arg = self.runner.claude_args[i + 1]
                            # If next arg doesn't start with '-', it's a session ID
                            if not next_arg.startswith("-"):
                                skip_next = True
                        continue
                    # If no resume_session provided, keep --resume from runner
                if arg == "--fork-session" and resume_session:
                    # Skip --fork-session if we're using resume_session
                    continue
                filtered_args.append(arg)
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

        # Check if using stream-json input format (vibe-kanban compatibility)
        # When --input-format stream-json is passed, stdin should be passed
        # through to Claude Code directly, not read by claude-mpm
        # NOTE: Args can be space-separated ["--input-format", "stream-json"]
        # or combined ["--input-format=stream-json"] - we need to handle both
        claude_args = self.runner.claude_args or []
        uses_stream_json_input = (
            "--input-format=stream-json" in claude_args
            or self._has_adjacent_args(claude_args, "--input-format", "stream-json")
        )

        if uses_stream_json_input:
            # Vibe-kanban mode: pass stdin through to Claude Code
            # Don't read stdin here, let Claude Code handle it
            self.logger.debug("Using stream-json input mode (vibe-kanban compatibility)")
            self.logger.info(f"DEBUG: claude_args={claude_args}")
            self.logger.info(f"DEBUG: uses_stream_json_input={uses_stream_json_input}")
            self.logger.info(f"DEBUG: cmd={cmd}")
        else:
            # Standard headless mode: read prompt from argument or stdin
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
        self.logger.info(f"DEBUG: Full command: {' '.join(cmd)}")

        # Write debug info to file for vibe-kanban debugging
        import tempfile
        debug_file = Path(tempfile.gettempdir()) / "claude-mpm-debug.log"
        with open(debug_file, "a") as f:
            import datetime
            f.write(f"\n=== {datetime.datetime.now()} ===\n")
            f.write(f"uses_stream_json_input: {uses_stream_json_input}\n")
            f.write(f"claude_args: {claude_args}\n")
            f.write(f"cmd: {cmd}\n")
            f.write(f"prompt: {prompt}\n")
            f.write(f"resume_session: {resume_session}\n")

        # Prepare environment
        env = self._prepare_environment()

        try:
            # For vibe-kanban mode (stream-json input), pass stdin through
            # For standard headless mode, use PIPE and close immediately
            stdin_mode = sys.stdin if uses_stream_json_input else subprocess.PIPE

            # Run subprocess with direct stdout/stderr passthrough
            process = subprocess.Popen(
                cmd,
                stdin=stdin_mode,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.working_dir),
                env=env,
            )

            # Stream output in real-time instead of buffering with communicate()
            # This is critical for vibe-kanban integration which expects streaming output
            def stream_stderr():
                """Stream stderr in a separate thread."""
                for line in process.stderr:
                    sys.stderr.write(line)
                    sys.stderr.flush()

            # Start stderr streaming in background thread
            stderr_thread = threading.Thread(target=stream_stderr, daemon=True)
            stderr_thread.start()

            # Close stdin to signal we're done sending input (only for non-passthrough mode)
            # Claude Code needs this signal to start processing
            if not uses_stream_json_input:
                process.stdin.close()

            # Stream stdout (stream-json) directly in main thread - no Rich formatting
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()

            # Wait for process to complete and stderr thread to finish
            process.wait()
            stderr_thread.join(timeout=1.0)

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
