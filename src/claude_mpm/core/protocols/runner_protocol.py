"""Protocol definitions for ClaudeRunner dependencies.

These protocols use Python's typing.Protocol for structural subtyping,
allowing dependency injection without circular imports.
"""

from pathlib import Path
from typing import Any, Optional, Protocol


class SystemPromptProvider(Protocol):
    """Protocol for providing system prompts without circular dependency.

    This protocol allows InteractiveSession to get system prompts without
    directly importing ClaudeRunner, breaking the circular dependency.
    """

    def _create_system_prompt(self) -> str:
        """Create the complete system prompt including instructions.

        Returns:
            Complete system prompt as string
        """
        ...


class ClaudeRunnerProtocol(Protocol):
    """Protocol defining the interface InteractiveSession needs from ClaudeRunner.

    This protocol breaks the circular dependency between InteractiveSession
    and ClaudeRunner by defining only the methods that InteractiveSession
    actually uses, without requiring the full ClaudeRunner import.

    Design Decision: Uses Protocol instead of ABC to allow structural subtyping.
    This means ClaudeRunner doesn't need to explicitly inherit from this protocol,
    it just needs to implement these methods with matching signatures.
    """

    # Configuration attributes
    enable_websocket: bool
    enable_tickets: bool
    log_level: str
    claude_args: Optional[list]
    launch_method: str
    websocket_port: int
    use_native_agents: bool
    config: Any
    session_log_file: Optional[Path]

    # Service references
    project_logger: Any
    websocket_server: Any
    command_handler_service: Any
    subprocess_launcher_service: Any

    def setup_agents(self) -> bool:
        """Deploy native agents to .claude/agents/.

        Returns:
            True if successful, False otherwise
        """
        ...

    def deploy_project_agents_to_claude(self) -> bool:
        """Deploy project agents from .claude-mpm/agents/ to .claude/agents/.

        Returns:
            True if successful, False otherwise
        """
        ...

    def _create_system_prompt(self) -> str:
        """Create the complete system prompt including instructions.

        Returns:
            Complete system prompt as string
        """
        ...

    def _get_version(self) -> str:
        """Get version string.

        Returns:
            Version string
        """
        ...

    def _log_session_event(self, event_data: dict) -> None:
        """Log an event to the session log file.

        Args:
            event_data: Event data to log
        """
        ...

    def _launch_subprocess_interactive(self, cmd: list, env: dict) -> None:
        """Launch Claude as a subprocess with PTY for interactive mode.

        Args:
            cmd: Command to execute
            env: Environment variables
        """
        ...
