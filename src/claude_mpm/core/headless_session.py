"""Headless session handler for Claude MPM.

This module provides headless execution that bypasses Rich console rendering
and pipes Claude Code's stream-json output directly to stdout for programmatic
consumption.

WHY: Headless mode is essential for:
- CI/CD pipelines
- Programmatic automation
- Piping output to other tools
- Integration with external systems

DESIGN DECISION: Uses os.execvpe() to replace the claude-mpm process with claude,
matching the behavior of normal interactive mode. This ensures:
- Initialization happens only ONCE (hooks, agents, skills)
- Claude handles the entire session directly
- No claude-mpm process overhead during the session
"""

import os
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

    DESIGN DECISION: Uses os.execvpe() to replace claude-mpm with claude,
    matching normal interactive mode behavior:
    - claude-mpm initializes once (hooks, agents, skills)
    - os.execvpe() replaces the process with claude
    - Claude handles the entire session directly
    - No re-initialization on subsequent messages
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

    def _verify_hooks_deployed(self) -> None:
        """Verify hooks are deployed, warn to stderr if not.

        WHY: In headless mode, hooks are critical for MPM features like
        session management, auto-todos, and skill integration. If hooks
        aren't properly deployed, MPM features won't work.

        DESIGN DECISION: Warnings go to stderr (not stdout) to keep
        stdout clean for JSON streaming. Non-blocking - continues
        execution even if verification fails.
        """
        try:
            from claude_mpm.hooks.claude_hooks.installer import HookInstaller

            installer = HookInstaller()
            is_valid, issues = installer.verify_hooks()
            if not is_valid:
                # Write warning to stderr to keep stdout clean for JSON
                sys.stderr.write(f"Warning: Hook issues detected: {issues}\n")
                sys.stderr.flush()
        except Exception as e:
            # Non-blocking - log at debug level and continue
            self.logger.debug(f"Could not verify hooks: {e}")

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

    def _is_resume_mode(self, resume_session: Optional[str] = None) -> bool:
        """Check if we're in resume mode (either via argument or claude_args).

        Args:
            resume_session: Optional session ID passed directly

        Returns:
            True if resuming an existing session
        """
        if resume_session:
            return True
        claude_args = self.runner.claude_args or []
        return "--resume" in claude_args

    def _inject_system_prompt(self, cmd: list) -> list:
        """Inject system prompt into command if runner supports it.

        Uses file-based caching to avoid ARG_MAX limits on Linux/Windows.
        Falls back to inline --append-system-prompt if caching fails.

        Args:
            cmd: The command list to extend

        Returns:
            The command list with system prompt arguments added
        """
        # Check if runner has _create_system_prompt method
        if not hasattr(self.runner, "_create_system_prompt"):
            self.logger.debug(
                "Runner does not support _create_system_prompt, skipping system prompt injection"
            )
            return cmd

        try:
            system_prompt = self.runner._create_system_prompt()
        except Exception as e:
            self.logger.warning(f"Failed to create system prompt: {e}")
            return cmd

        if not system_prompt:
            self.logger.debug("No system prompt generated")
            return cmd

        # Check if it's just the simple context (no real instructions)
        try:
            from claude_mpm.core.system_context import create_simple_context

            if system_prompt == create_simple_context():
                self.logger.debug("System prompt is just simple context, skipping")
                return cmd
        except ImportError:
            pass  # Module not available, proceed with injection

        # Try to use cached instruction file for better performance
        try:
            from claude_mpm.services.instructions.instruction_cache_service import (
                InstructionCacheService,
            )

            # Get project root
            if "CLAUDE_MPM_USER_PWD" in os.environ:
                project_root = Path(os.environ["CLAUDE_MPM_USER_PWD"])
            else:
                project_root = self.working_dir

            # Instruction Caching to avoid ARG_MAX limits:
            # - Linux: 128 KB limit
            # - Windows: 32 KB limit
            # Cache updates only when content hash changes.
            cache_service = InstructionCacheService(project_root=project_root)

            # Update cache with assembled instruction content
            cache_result = cache_service.update_cache(instruction_content=system_prompt)

            # Use cache file if available
            if cache_result.get("updated") or cache_service.get_cache_path().exists():
                cache_file = cache_service.get_cache_path()

                if cache_result.get("updated"):
                    self.logger.debug(
                        f"Instruction cache updated: {cache_result.get('reason', 'unknown')}"
                    )
                else:
                    self.logger.debug("Using cached instructions")

                cmd.extend(["--system-prompt-file", str(cache_file)])
                self.logger.debug(f"Using file-based instruction loading: {cache_file}")
            else:
                # Fallback to inline if cache file doesn't exist
                self.logger.debug(
                    "Cache file not available, falling back to inline instruction"
                )
                cmd.extend(["--append-system-prompt", system_prompt])

        except ImportError:
            # InstructionCacheService not available, use inline
            self.logger.debug(
                "InstructionCacheService not available, using inline system prompt"
            )
            cmd.extend(["--append-system-prompt", system_prompt])
        except Exception as e:
            # Graceful fallback - cache failures don't break execution
            self.logger.warning(f"Failed to cache instructions, using inline: {e}")
            cmd.extend(["--append-system-prompt", system_prompt])

        return cmd

    def build_claude_command(self, resume_session: Optional[str] = None) -> list:
        """Build the Claude command for headless execution.

        Args:
            resume_session: Optional session ID to resume

        Returns:
            List of command arguments
        """
        # Check if we're in resume mode
        is_resume = self._is_resume_mode(resume_session)

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

        # Inject system prompt ONLY for initial sessions (not resume)
        # This matches interactive_session.py behavior where resume uses minimal command
        if not is_resume:
            self.logger.debug("Initial session - injecting system prompt")
            cmd = self._inject_system_prompt(cmd)
        else:
            self.logger.debug(
                "Resume mode - skipping system prompt injection to preserve conversation context"
            )

        return cmd

    def run(
        self,
        prompt: Optional[str] = None,
        resume_session: Optional[str] = None,
    ) -> int:
        """Run Claude Code in headless mode with stream-json output.

        Uses os.execvpe() to replace the claude-mpm process with claude,
        matching normal interactive mode. This ensures initialization
        happens only once - claude handles the entire session directly.

        Args:
            prompt: The prompt to send to Claude. If None, stdin passes through.
            resume_session: Optional session ID to resume

        Returns:
            Exit code from Claude Code process (only on exec failure)
        """
        # Verify hooks are deployed before execution
        # This ensures MPM features (session management, skills) work in headless mode
        self._verify_hooks_deployed()

        # Build the command
        cmd = self.build_claude_command(resume_session=resume_session)

        # Check if using stream-json input format (vibe-kanban compatibility)
        # When --input-format stream-json is passed, stdin passes through to Claude
        claude_args = self.runner.claude_args or []
        uses_stream_json_input = (
            "--input-format=stream-json" in claude_args
            or self._has_adjacent_args(claude_args, "--input-format", "stream-json")
        )

        if uses_stream_json_input:
            # Vibe-kanban mode: stdin passes through to Claude Code via exec
            self.logger.debug(
                "Using stream-json input mode (vibe-kanban compatibility)"
            )
        else:
            # Standard headless mode: read prompt from argument or stdin
            if prompt is None:
                # Read from stdin for piping support
                if sys.stdin.isatty():
                    sys.stderr.write(
                        "Error: No prompt provided and stdin is a TTY. "
                        "Use -i 'prompt' or pipe input: echo 'prompt' | claude-mpm run --headless\n"
                    )
                    sys.stderr.flush()
                    return 1
                prompt = sys.stdin.read().strip()

            if not prompt:
                sys.stderr.write("Error: Empty prompt provided\n")
                sys.stderr.flush()
                return 1

            # Add the prompt to command
            cmd.extend(["--print", prompt])

        self.logger.debug(f"Headless command: {' '.join(cmd[:5])}...")

        # Prepare environment
        env = self._prepare_environment()

        # Change to working directory before exec
        os.chdir(str(self.working_dir))

        try:
            # Replace this process with claude - no return on success
            # This matches normal interactive mode behavior:
            # - claude-mpm initializes once
            # - os.execvpe() replaces process with claude
            # - Claude handles the entire session
            os.execvpe(cmd[0], cmd, env)  # nosec B606

            # Only reached on exec failure
            return 1

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
