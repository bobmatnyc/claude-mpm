"""
Utility functions for the CLI.

WHY: This module contains shared utility functions used across different CLI commands.
Centralizing these functions reduces code duplication and provides a single place
for common CLI operations.
"""

import difflib
import sys
from pathlib import Path
from typing import List, Optional

from ..core.logger import get_logger


def get_user_input(input_arg: Optional[str], logger) -> str:
    """
    Get user input based on command line arguments.

    WHY: This function handles the three ways users can provide input:
    1. Direct text via -i/--input
    2. File path via -i/--input
    3. stdin (for piping)

    DESIGN DECISION: We check if the input is a file path first, then fall back
    to treating it as direct text. This allows maximum flexibility.

    Args:
        input_arg: The value of the -i/--input argument
        logger: Logger instance for output

    Returns:
        The user input as a string
    """
    if input_arg:
        # Check if it's a file path
        input_path = Path(input_arg)
        if input_path.exists():
            logger.info(f"Reading input from file: {input_path}")
            return input_path.read_text()
        logger.info("Using command line input")
        return input_arg
    # Read from stdin
    logger.info("Reading input from stdin")
    return sys.stdin.read()


def get_agent_versions_display() -> Optional[str]:
    """
    Get formatted agent versions display as a string.

    WHY: This function provides a single source of truth for agent version
    information that can be displayed both at startup and on-demand via the
    /mpm agents command. This ensures consistency in how agent versions are
    presented to users.

    Returns:
        Formatted string containing agent version information, or None if failed
    """
    try:
        import os
        from pathlib import Path

        from ..services import AgentDeploymentService

        # Determine the user's working directory from environment
        user_working_dir = None
        if "CLAUDE_MPM_USER_PWD" in os.environ:
            user_working_dir = Path(os.environ["CLAUDE_MPM_USER_PWD"])

        deployment_service = AgentDeploymentService(working_directory=user_working_dir)

        # Get deployed agents
        verification = deployment_service.verify_deployment()
        if not verification.get("agents_found"):
            return None

        output_lines = []
        output_lines.append("\nDeployed Agent Versions:")
        output_lines.append("-" * 40)

        # Sort agents by name for consistent display
        agents = sorted(
            verification["agents_found"], key=lambda x: x.get("name", x.get("file", ""))
        )

        for agent in agents:
            name = agent.get("name", "unknown")
            version = agent.get("version", "unknown")
            # Format: name (version)
            output_lines.append(f"  {name:<20} {version}")

        # Add base agent version info
        try:
            import json

            base_agent_path = deployment_service.base_agent_path
            if base_agent_path.exists():
                base_data = json.loads(base_agent_path.read_text())
                # Parse version the same way as AgentDeploymentService
                raw_version = base_data.get("base_version") or base_data.get(
                    "version", 0
                )
                base_version_tuple = deployment_service._parse_version(raw_version)
                base_version_str = deployment_service._format_version_display(
                    base_version_tuple
                )
                output_lines.append(f"\n  Base Agent Version:  {base_version_str}")
        except Exception:
            pass

        # Check for agents needing migration
        if verification.get("agents_needing_migration"):
            output_lines.append(
                f"\n  ⚠️  {len(verification['agents_needing_migration'])} agent(s) need migration to semantic versioning"
            )
            output_lines.append("     Run 'claude-mpm agents deploy' to update")

        output_lines.append("-" * 40)
        return "\n".join(output_lines)
    except Exception as e:
        # Log error but don't fail
        logger = get_logger("cli")
        logger.debug(f"Failed to get agent versions: {e}")
        return None


def list_agent_versions_at_startup() -> None:
    """
    List deployed agent versions at startup.

    WHY: Users want to see what agents are available when they start a session.
    This provides immediate feedback about the deployed agent environment.

    DESIGN DECISION: We suppress INFO logging during this call to avoid duplicate
    initialization messages since the deployment service will be initialized again
    later in the ClaudeRunner.
    """
    # Temporarily suppress INFO level logging to avoid duplicate initialization messages
    import logging

    original_level = logging.getLogger("claude_mpm").level
    logging.getLogger("claude_mpm").setLevel(logging.WARNING)

    try:
        agent_versions = get_agent_versions_display()
        if agent_versions:
            print(agent_versions)
            print()  # Extra newline after the display
    finally:
        # Restore original logging level
        logging.getLogger("claude_mpm").setLevel(original_level)


def setup_logging(args) -> object:
    """
    Set up logging based on parsed arguments.

    WHY: This centralizes logging setup logic, handling the deprecated --debug flag
    and the new --logging argument consistently across all commands.

    Args:
        args: Parsed command line arguments

    Returns:
        Logger instance
    """
    from ..constants import LogLevel
    from ..core.logger import setup_logging as core_setup_logging

    # Set default logging level if not specified
    if not hasattr(args, "logging") or args.logging is None:
        args.logging = LogLevel.OFF.value

    # Handle deprecated --debug flag
    if hasattr(args, "debug") and args.debug and args.logging == LogLevel.INFO.value:
        args.logging = LogLevel.DEBUG.value

    # Only setup logging if not OFF
    if args.logging != LogLevel.OFF.value:
        logger = core_setup_logging(
            level=args.logging, log_dir=getattr(args, "log_dir", None)
        )
    else:
        # Minimal logger for CLI feedback
        import logging

        logger = logging.getLogger("cli")
        logger.setLevel(logging.WARNING)

    return logger


def ensure_directories() -> None:
    """
    Ensure required directories exist on first run.

    WHY: Claude-mpm needs certain directories to function properly. Rather than
    failing when they don't exist, we create them automatically for a better
    user experience.
    """
    try:
        from ..init import ensure_directories as init_ensure_directories

        init_ensure_directories()
    except Exception:
        # Continue even if initialization fails
        # The individual commands will handle missing directories as needed
        pass


def suggest_similar_commands(
    invalid_command: str,
    valid_commands: List[str],
    cutoff: float = 0.6,
    max_suggestions: int = 3,
) -> Optional[str]:
    """
    Suggest similar commands for an invalid command using fuzzy matching.

    WHY: Helps users quickly identify typos and discover correct command names
    by suggesting the most similar valid commands. Uses stdlib difflib for
    zero-dependency fuzzy matching.

    DESIGN DECISION: Using difflib.get_close_matches provides good results for
    typos and partial matches while being simple and lightweight (no external deps).

    Args:
        invalid_command: The invalid command the user typed
        valid_commands: List of valid commands to match against
        cutoff: Similarity threshold (0.0-1.0), default 0.6
        max_suggestions: Maximum number of suggestions to return, default 3

    Returns:
        Formatted suggestion string or None if no good matches found

    Examples:
        >>> suggest_similar_commands("tickts", ["tickets", "run", "agents"])
        "Did you mean 'tickets'?"

        >>> suggest_similar_commands("mem", ["memory", "monitor", "mcp"])
        "Did you mean one of these?\n  memory\n  monitor\n  mcp"

        >>> suggest_similar_commands("xyz", ["tickets", "run"])
        None  # No good matches
    """
    # Use difflib to find close matches
    matches = difflib.get_close_matches(
        invalid_command, valid_commands, n=max_suggestions, cutoff=cutoff
    )

    if not matches:
        return None

    # Format suggestion message
    if len(matches) == 1:
        return f"Did you mean '{matches[0]}'?"
    suggestions = "\n  ".join(matches)
    return f"Did you mean one of these?\n  {suggestions}"
