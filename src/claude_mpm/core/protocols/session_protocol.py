"""Protocol definitions for session management dependencies.

These protocols use Python's typing.Protocol for structural subtyping,
allowing dependency injection without circular imports.
"""

from typing import Any, Dict, Optional, Protocol, Tuple


class InteractiveSessionProtocol(Protocol):
    """Protocol for interactive session orchestration.

    This protocol defines the interface that SessionManagementService
    needs from InteractiveSession without requiring a full import.
    """

    def initialize_interactive_session(self) -> Tuple[bool, Optional[str]]:
        """Initialize the interactive session environment.

        Returns:
            Tuple of (success, error_message)
        """
        ...

    def setup_interactive_environment(self) -> Tuple[bool, Dict[str, Any]]:
        """Set up the interactive environment including agents and commands.

        Returns:
            Tuple of (success, environment_dict)
        """
        ...

    def handle_interactive_input(self, environment: Dict[str, Any]) -> bool:
        """Handle the interactive input/output loop.

        Args:
            environment: Dictionary with command, env vars, and session info

        Returns:
            True if successful, False otherwise
        """
        ...

    def cleanup_interactive_session(self) -> None:
        """Clean up resources after interactive session ends."""
        ...


class OneshotSessionProtocol(Protocol):
    """Protocol for oneshot session orchestration.

    This protocol defines the interface that SessionManagementService
    needs from OneshotSession without requiring a full import.
    """

    def initialize_session(self, prompt: str) -> Tuple[bool, Optional[str]]:
        """Initialize the oneshot session.

        Args:
            prompt: The command or prompt to execute

        Returns:
            Tuple of (success, error_message)
        """
        ...

    def deploy_agents(self) -> bool:
        """Deploy agents for the session.

        Returns:
            True if successful, False otherwise
        """
        ...

    def setup_infrastructure(self) -> Dict[str, Any]:
        """Set up session infrastructure.

        Returns:
            Dictionary with infrastructure configuration
        """
        ...

    def execute_command(
        self, prompt: str, context: Optional[str], infrastructure: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Execute the command with given context and infrastructure.

        Args:
            prompt: Command to execute
            context: Optional context
            infrastructure: Infrastructure configuration

        Returns:
            Tuple of (success, response)
        """
        ...

    def cleanup_session(self) -> None:
        """Clean up session resources."""
        ...


class SessionManagementProtocol(Protocol):
    """Protocol for session management service.

    This protocol defines the interface that ClaudeRunner needs from
    SessionManagementService without requiring a full import.
    """

    def run_interactive_session(self, initial_context: Optional[str] = None) -> bool:
        """Run Claude in interactive mode.

        Args:
            initial_context: Optional initial context to pass to Claude

        Returns:
            True if successful, False otherwise
        """
        ...

    def run_oneshot_session(self, prompt: str, context: Optional[str] = None) -> bool:
        """Run Claude with a single prompt.

        Args:
            prompt: The command or prompt to execute
            context: Optional context to prepend to the prompt

        Returns:
            True if successful, False otherwise
        """
        ...
