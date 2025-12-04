"""Interactive session handler for Claude runner.

This module provides the InteractiveSession class that manages Claude's interactive mode
with proper separation of concerns and reduced complexity.

DEPENDENCY INJECTION:
This module uses protocol-based dependency injection to break circular imports.
Instead of importing ClaudeRunner directly, it uses ClaudeRunnerProtocol which
defines the interface it needs. This allows ClaudeRunner to create instances
of InteractiveSession without circular dependency issues.
"""

import contextlib
import os
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from claude_mpm.core.enums import ServiceState
from claude_mpm.core.logger import get_logger

# Protocol imports for type checking without circular dependencies
if TYPE_CHECKING:
    from claude_mpm.core.protocols import ClaudeRunnerProtocol
else:
    # At runtime, accept any object with matching interface
    ClaudeRunnerProtocol = Any


class InteractiveSession:
    """
    Handles interactive Claude sessions with proper separation of concerns.

    WHY: The original run_interactive() method had complexity of 39 and 262 lines.
    This class breaks down that functionality into smaller, focused methods with
    complexity <10 and lines <80 each, improving maintainability and testability.

    DESIGN DECISION: Uses composition over inheritance - takes ClaudeRunner as
    dependency rather than inheriting from it. This maintains loose coupling
    and makes testing easier while preserving all original functionality.
    """

    def __init__(self, runner: "ClaudeRunnerProtocol"):
        """Initialize interactive session handler.

        Args:
            runner: ClaudeRunner instance (or any object matching ClaudeRunnerProtocol)
                    with all necessary services
        """
        self.runner: ClaudeRunnerProtocol = runner
        self.logger = get_logger("interactive_session")
        self.session_id = None
        self.original_cwd = Path.cwd()

        # Initialize response tracking for interactive sessions
        # WHY: Interactive sessions need response logging just like oneshot sessions.
        # The hook system captures events, but we need the ResponseTracker to be
        # initialized to actually store them.
        self.response_tracker = None

        # Check if response logging is enabled in configuration
        try:
            response_config = self.runner.config.get("response_logging", {})
            response_logging_enabled = response_config.get("enabled", False)
        except (AttributeError, TypeError):
            # Handle mock or missing config gracefully
            response_logging_enabled = False

        if response_logging_enabled:
            try:
                from claude_mpm.services.response_tracker import ResponseTracker

                self.response_tracker = ResponseTracker(self.runner.config)
                self.logger.info(
                    "Response tracking initialized for interactive session"
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize response tracker: {e}")
                # Continue without response tracking - not fatal

    def initialize_interactive_session(self) -> Tuple[bool, Optional[str]]:
        """Initialize the interactive session environment.

        Sets up WebSocket connections, generates session IDs, and prepares
        the session for launch.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Generate session ID
            self.session_id = str(uuid.uuid4())

            # Initialize WebSocket if enabled
            if self.runner.enable_websocket:
                success, error = self._initialize_websocket()
                if not success:
                    self.logger.warning(f"WebSocket initialization failed: {error}")
                    # Continue without WebSocket - not a fatal error

            # Banner now displayed in CLI startup - see startup_display.py
            # Removed duplicate _display_welcome_message() to consolidate with main banner

            # Log session start
            if self.runner.project_logger:
                self.runner.project_logger.log_system(
                    "Starting interactive session", level="INFO", component="session"
                )

            if self.response_tracker and self.response_tracker.enabled:
                try:
                    # Set the session ID in the tracker for correlation
                    if (
                        hasattr(self.response_tracker, "session_logger")
                        and self.response_tracker.session_logger
                    ):
                        self.response_tracker.session_logger.set_session_id(
                            self.session_id
                        )
                        self.logger.debug(
                            f"Response tracker session ID set to: {self.session_id}"
                        )
                except Exception as e:
                    self.logger.debug(
                        f"Could not set session ID in response tracker: {e}"
                    )

            return True, None

        except Exception as e:
            error_msg = f"Failed to initialize session: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def setup_interactive_environment(self) -> Tuple[bool, Dict[str, Any]]:
        """Set up the interactive environment including agents and commands.

        Deploys system and project agents, prepares the command line,
        and sets up the execution environment.

        Returns:
            Tuple of (success, environment_dict)
        """
        try:
            # Deploy system agents
            if not self.runner.setup_agents():
                print("Continuing without native agents...")

            # Deploy project-specific agents
            self.runner.deploy_project_agents_to_claude()

            # Build command
            cmd = self._build_claude_command()

            # Prepare environment
            env = self._prepare_environment()

            # Change to user directory if needed
            self._change_to_user_directory(env)

            return True, {
                "command": cmd,
                "environment": env,
                "session_id": self.session_id,
            }

        except Exception as e:
            error_msg = f"Failed to setup environment: {e}"
            self.logger.error(error_msg)
            return False, {}

    def handle_interactive_input(self, environment: Dict[str, Any]) -> bool:
        """Handle the interactive input/output loop.

        Launches Claude and manages the interactive session using either
        exec or subprocess method based on configuration.

        Args:
            environment: Dictionary with command, env vars, and session info

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cmd = environment["command"]
            env = environment["environment"]

            print("Launching Claude...")

            # Log launch attempt
            self._log_launch_attempt(cmd)

            # Notify WebSocket if connected
            if self.runner.websocket_server:
                self.runner.websocket_server.claude_status_changed(
                    status=ServiceState.STARTING,
                    message="Launching Claude interactive session",
                )

            # Launch using selected method
            if self.runner.launch_method == "subprocess":
                return self._launch_subprocess_mode(cmd, env)
            return self._launch_exec_mode(cmd, env)

        except FileNotFoundError as e:
            self._handle_launch_error("FileNotFoundError", e)
            return False
        except PermissionError as e:
            self._handle_launch_error("PermissionError", e)
            return False
        except OSError as e:
            self._handle_launch_error("OSError", e)
            return self._attempt_fallback_launch(environment)
        except KeyboardInterrupt:
            self._handle_keyboard_interrupt()
            return True  # Clean exit
        except Exception as e:
            self._handle_launch_error("Exception", e)
            return self._attempt_fallback_launch(environment)

    def process_interactive_command(self, prompt: str) -> Optional[bool]:
        """Process special interactive commands.

        NOTE: As of v4.1.2, MPM slash commands are deployed as markdown files
        to ~/.claude/commands and handled directly by Claude Code.
        This method is kept for potential future use with non-Claude commands.

        Args:
            prompt: User input command

        Returns:
            Optional[bool]: True if handled, False if error, None if not a special command
        """
        # Currently no commands are intercepted - all MPM commands are handled by Claude Code
        return None

    def cleanup_interactive_session(self) -> None:
        """Clean up resources after interactive session ends.

        Restores original directory, closes connections, and logs session end.
        """
        try:
            # Restore original directory
            if self.original_cwd and Path(self.original_cwd).exists():
                with contextlib.suppress(OSError):
                    os.chdir(self.original_cwd)

            # Close WebSocket if connected
            if self.runner.websocket_server:
                self.runner.websocket_server.session_ended()
                self.runner.websocket_server = None

            # Log session end
            if self.runner.project_logger:
                self.runner.project_logger.log_system(
                    "Interactive session ended", level="INFO", component="session"
                )

            # Log session event
            if self.runner.session_log_file:
                self.runner._log_session_event(
                    {"event": "session_end", "session_id": self.session_id}
                )

            if self.response_tracker:
                try:
                    # Clear the session ID to stop tracking this session
                    if (
                        hasattr(self.response_tracker, "session_logger")
                        and self.response_tracker.session_logger
                    ):
                        self.response_tracker.session_logger.set_session_id(None)
                        self.logger.debug("Response tracker session cleared")
                except Exception as e:
                    self.logger.debug(f"Error clearing response tracker session: {e}")

        except Exception as e:
            self.logger.debug(f"Error during cleanup: {e}")

    # Private helper methods (each <80 lines, complexity <10)

    def _initialize_websocket(self) -> Tuple[bool, Optional[str]]:
        """Initialize WebSocket connection for monitoring."""
        try:
            from claude_mpm.services.socketio_server import SocketIOClientProxy

            self.runner.websocket_server = SocketIOClientProxy(
                port=self.runner.websocket_port
            )
            self.runner.websocket_server.start()
            self.logger.info("Connected to Socket.IO monitoring server")

            # Notify session start
            self.runner.websocket_server.session_started(
                session_id=self.session_id,
                launch_method=self.runner.launch_method,
                working_dir=Path.cwd(),
            )
            return True, None

        except ImportError as e:
            return False, f"Socket.IO module not available: {e}"
        except ConnectionError as e:
            return False, f"Cannot connect to Socket.IO server: {e}"
        except Exception as e:
            return False, f"Unexpected error with Socket.IO: {e}"

    def _display_welcome_message(self) -> None:
        """Display the interactive session welcome message.

        DEPRECATED: This method is kept for backward compatibility with tests.
        The main banner is now displayed in startup_display.py during CLI startup.
        This consolidated approach prevents duplicate banners.
        """
        version_str = self.runner._get_version()

        # Get output style status
        output_style_info = self._get_output_style_info()

        print("\033[32m╭───────────────────────────────────────────────────╮\033[0m")
        print(
            "\033[32m│\033[0m ✻ Claude MPM - Interactive Session                \033[32m│\033[0m"
        )
        print(f"\033[32m│\033[0m   Version {version_str:<40}\033[32m│\033[0m")
        if output_style_info:
            print(f"\033[32m│\033[0m   {output_style_info:<49}\033[32m│\033[0m")
        print("\033[32m│                                                   │\033[0m")
        print(
            "\033[32m│\033[0m   MPM Commands (via Claude Code):                 \033[32m│\033[0m"
        )
        print(
            "\033[32m│\033[0m     /mpm        - MPM overview and help           \033[32m│\033[0m"
        )
        print(
            "\033[32m│\033[0m     /mpm-init   - Initialize or update project    \033[32m│\033[0m"
        )
        print(
            "\033[32m│\033[0m     /mpm-agents - Show available agents           \033[32m│\033[0m"
        )
        print(
            "\033[32m│\033[0m     /mpm-doctor - Run diagnostic checks           \033[32m│\033[0m"
        )
        print(
            "\033[32m│\033[0m     Type / for autocomplete in Claude Code        \033[32m│\033[0m"
        )

        print("\033[32m╰───────────────────────────────────────────────────╯\033[0m")
        print("")  # Add blank line after box

    def _get_output_style_info(self) -> Optional[str]:
        """Get output style status for display."""
        try:
            # Check if output style manager is available through framework loader
            if (
                hasattr(self.runner, "framework_loader")
                and self.runner.framework_loader
            ) and hasattr(self.runner.framework_loader, "output_style_manager"):
                osm = self.runner.framework_loader.output_style_manager
                if osm:
                    if osm.claude_version and osm.supports_output_styles():
                        # Check if claude-mpm style is active
                        settings_file = osm.settings_file
                        if settings_file.exists():
                            import json

                            settings = json.loads(settings_file.read_text())
                            active_style = settings.get("activeOutputStyle")
                            if active_style == "claude-mpm":
                                return "Output Style: claude-mpm ✅"
                            return f"Output Style: {active_style or 'none'}"
                        return "Output Style: Available"
                    return "Output Style: Injected (legacy)"
        except Exception:
            pass
        return None

    def _build_claude_command(self) -> list:
        """Build the Claude command with all necessary arguments."""
        # Check if --resume flag is present
        has_resume = self.runner.claude_args and "--resume" in self.runner.claude_args

        if has_resume:
            # When resuming, use minimal command to avoid interfering with conversation selection
            self.logger.info(
                "🔄 Resume mode detected - using minimal Claude command to preserve conversation selection"
            )
            cmd = ["claude"]

            # Add only the claude_args (which includes --resume)
            if self.runner.claude_args:
                cmd.extend(self.runner.claude_args)
                self.logger.info(f"Resume command: {cmd}")

            return cmd
        # Normal mode - full command with all claude-mpm enhancements
        cmd = ["claude", "--dangerously-skip-permissions"]

        # Add custom arguments
        if self.runner.claude_args:
            # Enhanced debug logging for --resume flag verification
            self.logger.debug(f"Raw claude_args received: {self.runner.claude_args}")
            cmd.extend(self.runner.claude_args)

        # Add --agents flag if native agents mode is enabled
        if getattr(self.runner, "use_native_agents", False):
            agents_flag = self._build_agents_flag()
            if agents_flag:
                # Add --agents JSON directly (already properly formatted)
                cmd.extend(agents_flag)
                self.logger.info("✓ Native agents mode: Using --agents CLI flag")

        # Add system instructions with file-based caching
        from claude_mpm.core.system_context import create_simple_context
        from claude_mpm.services.instructions.instruction_cache_service import (
            InstructionCacheService,
        )

        system_prompt = self.runner._create_system_prompt()
        if system_prompt and system_prompt != create_simple_context():
            # Try to use cached instruction file for better performance
            try:
                # Initialize cache service with project root
                if "CLAUDE_MPM_USER_PWD" in os.environ:
                    project_root = Path(os.environ["CLAUDE_MPM_USER_PWD"])
                else:
                    project_root = Path.cwd()

                # Instruction Caching (1M-446)
                # Cache assembled instructions to file to avoid ARG_MAX limits on Linux/Windows.
                # - Linux: 128 KB limit, instructions are ~152 KB (exceeds by 19.1%)
                # - Windows: 32 KB limit (exceeds by 476%)
                # Cache updates only when content hash changes (hash-based invalidation).
                # Fallback to inline instruction if cache fails (graceful degradation).
                cache_service = InstructionCacheService(project_root=project_root)

                # Update cache with assembled instruction content
                cache_result = cache_service.update_cache(
                    instruction_content=system_prompt
                )

                # Use cache file if available
                if (
                    cache_result.get("updated")
                    or cache_service.get_cache_path().exists()
                ):
                    cache_file = cache_service.get_cache_path()

                    # Log cache operation
                    if cache_result.get("updated"):
                        self.logger.info(
                            f"Instruction cache updated: {cache_result.get('reason', 'unknown')}"
                        )
                        self.logger.debug(
                            f"Cache hash: {cache_result.get('content_hash', 'N/A')[:8]}..."
                        )
                        self.logger.debug(
                            f"Cache size: {cache_result.get('content_size_kb', 'N/A')} KB"
                        )
                    else:
                        self.logger.debug(
                            f"Using cached instructions: {cache_result.get('reason', 'unknown')}"
                        )

                    # Use file-based loading for better performance
                    cmd.extend(["--system-prompt-file", str(cache_file)])
                    self.logger.info(
                        f"✓ Using file-based instruction loading: {cache_file}"
                    )
                else:
                    # Fallback to inline if cache file doesn't exist
                    self.logger.warning(
                        "Cache file not available, falling back to inline instruction"
                    )
                    cmd.extend(["--append-system-prompt", system_prompt])

            except Exception as e:
                # Graceful fallback - cache failures don't break deployment
                self.logger.warning(f"Failed to cache instructions, using inline: {e}")
                cmd.extend(["--append-system-prompt", system_prompt])

        # Final command verification
        # self.logger.info(f"Final Claude command built: {' '.join(cmd)}")

        # Explicit --resume flag verification
        if "--resume" in cmd:
            self.logger.info("✅ VERIFIED: --resume flag IS included in final command")
            self.logger.debug(f"--resume position in command: {cmd.index('--resume')}")
        else:
            self.logger.debug("[INFO]️ --resume flag NOT included in final command")

        return cmd

    def _build_agents_flag(self) -> Optional[list]:
        """Build --agents flag with all MPM agents.

        Returns:
            List with ["--agents", "<json>"] or None if conversion fails
        """
        try:
            from claude_mpm.services.native_agent_converter import NativeAgentConverter

            converter = NativeAgentConverter()
            agents = converter.load_agents_from_templates()

            if not agents:
                self.logger.warning("No agents loaded for native mode")
                return None

            # Generate JSON for --agents flag
            agents_json = converter.generate_agents_json(agents)
            summary = converter.get_conversion_summary(agents)

            self.logger.info(
                f"Native agents: {summary['total_agents']} agents, "
                f"{summary['json_size_kb']} KB JSON"
            )

            # Return as list: ["--agents", "<json>"]
            return ["--agents", agents_json]

        except Exception as e:
            self.logger.error(f"Failed to build --agents flag: {e}", exc_info=True)
            return None

    def _prepare_environment(self) -> dict:
        """Prepare clean environment variables for Claude."""
        clean_env = os.environ.copy()

        # Remove Claude-specific variables that might interfere
        claude_vars_to_remove = [
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDECODE",
            "CLAUDE_CONFIG_DIR",
            "CLAUDE_MAX_PARALLEL_SUBAGENTS",
            "CLAUDE_TIMEOUT",
        ]
        for var in claude_vars_to_remove:
            clean_env.pop(var, None)

        # Disable telemetry for Claude Code
        # This ensures Claude Code doesn't send telemetry data during runtime
        clean_env["DISABLE_TELEMETRY"] = "1"

        return clean_env

    def _change_to_user_directory(self, env: dict) -> None:
        """Change to user's working directory if specified."""
        if "CLAUDE_MPM_USER_PWD" in env:
            user_pwd = env["CLAUDE_MPM_USER_PWD"]
            env["CLAUDE_WORKSPACE"] = user_pwd

            try:
                os.chdir(user_pwd)
                self.logger.info(f"Changed working directory to: {user_pwd}")
            except (PermissionError, FileNotFoundError, OSError) as e:
                self.logger.warning(f"Could not change to directory {user_pwd}: {e}")

    def _log_launch_attempt(self, cmd: list) -> None:
        """Log the Claude launch attempt."""
        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                f"Launching Claude interactive mode with {self.runner.launch_method}",
                level="INFO",
                component="session",
            )
            self.runner._log_session_event(
                {
                    "event": "launching_claude_interactive",
                    "command": " ".join(cmd),
                    "method": self.runner.launch_method,
                }
            )

    def _launch_exec_mode(self, cmd: list, env: dict) -> bool:
        """Launch Claude using exec mode (replaces current process)."""
        # Notify WebSocket before exec
        if self.runner.websocket_server:
            self.runner.websocket_server.claude_status_changed(
                status=ServiceState.RUNNING,
                message="Claude process started (exec mode)",
            )

        # This will not return if successful
        os.execvpe(cmd[0], cmd, env)
        return False  # Only reached on failure

    def _launch_subprocess_mode(self, cmd: list, env: dict) -> bool:
        """Launch Claude as subprocess with PTY."""
        # Delegate to runner's existing method
        self.runner._launch_subprocess_interactive(cmd, env)
        return True

    def _handle_launch_error(self, error_type: str, error: Exception) -> None:
        """Handle errors during Claude launch."""
        error_messages = {
            "FileNotFoundError": "Claude CLI not found. Please ensure 'claude' is installed and in your PATH",
            "PermissionError": "Permission denied executing Claude CLI",
            "OSError": "OS error launching Claude",
            "Exception": "Unexpected error launching Claude",
        }

        error_msg = f"{error_messages.get(error_type, 'Error')}: {error}"
        print(f"❌ {error_msg}")

        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                error_msg, level="ERROR", component="session"
            )
            self.runner._log_session_event(
                {
                    "event": "interactive_launch_failed",
                    "error": str(error),
                    "exception_type": error_type,
                }
            )

        # Notify WebSocket of error
        if self.runner.websocket_server:
            self.runner.websocket_server.claude_status_changed(
                status=ServiceState.ERROR, message=f"Failed to launch Claude: {error}"
            )

    def _handle_keyboard_interrupt(self) -> None:
        """Handle keyboard interrupt during session."""
        print("\n⚠️  Session interrupted by user")

        if self.runner.project_logger:
            self.runner.project_logger.log_system(
                "Session interrupted by user", level="INFO", component="session"
            )
            self.runner._log_session_event(
                {"event": "session_interrupted", "reason": "user_interrupt"}
            )

    def _attempt_fallback_launch(self, environment: Dict[str, Any]) -> bool:
        """Attempt fallback launch using subprocess."""
        print("\n🔄 Attempting fallback launch method...")

        try:
            cmd = environment["command"]
            env = environment["environment"]

            result = subprocess.run(
                cmd, stdin=None, stdout=None, stderr=None, env=env, check=False
            )

            if result.returncode == 0:
                if self.runner.project_logger:
                    self.runner.project_logger.log_system(
                        "Interactive session completed (subprocess fallback)",
                        level="INFO",
                        component="session",
                    )
                return True
            print(f"⚠️  Claude exited with code {result.returncode}")
            return False

        except FileNotFoundError:
            print("❌ Fallback failed: Claude CLI not found in PATH")
            print("\n💡 To fix this issue:")
            print("   1. Install Claude CLI: npm install -g @anthropic-ai/claude-ai")
            print("   2. Or specify the full path to the claude binary")
            return False
        except KeyboardInterrupt:
            print("\n⚠️  Fallback interrupted by user")
            return True
        except Exception as e:
            print(f"❌ Fallback failed with unexpected error: {e}")
            return False
