"""Tool access control system for managing which tools agents can use."""

from typing import Dict, List, Set

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class ToolAccessControl:
    """
    Manages tool access permissions for different agent types.

    This ensures that only authorized agents can access specific tools,
    particularly restricting TodoWrite to the PM (parent process) only.
    """

    # Default tool sets for different contexts
    PM_TOOLS = {
        "Task",  # For delegating to agents
        "TodoWrite",  # For tracking tasks (PM ONLY)
        "WebSearch",  # For understanding requirements
        "WebFetch",  # For fetching external resources
    }

    AGENT_TOOLS = {
        "Read",  # Read files
        "Write",  # Write files
        "Edit",  # Edit files
        "MultiEdit",  # Multiple edits
        "Bash",  # Execute commands
        "Grep",  # Search in files
        "Glob",  # File pattern matching
        "LS",  # List directory
        "WebSearch",  # Search the web
        "WebFetch",  # Fetch web content
        "NotebookRead",  # Read Jupyter notebooks
        "NotebookEdit",  # Edit Jupyter notebooks
    }

    # Tool restrictions by agent type
    AGENT_RESTRICTIONS: Dict[str, Set[str]] = {
        # PM has very limited tools - delegation only
        "pm": PM_TOOLS,
        # All other agents get standard tools WITHOUT TodoWrite
        "engineer": AGENT_TOOLS,
        "research": AGENT_TOOLS,
        "qa": AGENT_TOOLS,
        "security": AGENT_TOOLS,
        "documentation": AGENT_TOOLS,
        "ops": AGENT_TOOLS,
        "version_control": AGENT_TOOLS,
        "data_engineer": AGENT_TOOLS,
        "architect": AGENT_TOOLS,
    }

    def __init__(self):
        """Initialize the tool access control system."""
        self.custom_restrictions: Dict[str, Set[str]] = {}
        logger.info("Tool access control system initialized")

    def get_allowed_tools(self, agent_type: str, is_parent: bool = False) -> List[str]:
        """
        Get the list of allowed tools for an agent type.

        Args:
            agent_type: The type of agent (pm, engineer, research, etc.)
            is_parent: Whether this is the parent process (PM)

        Returns:
            List of allowed tool names
        """
        # Normalize agent type
        agent_type = agent_type.lower().replace(" ", "_").replace("-", "_")

        # Parent process (PM) gets PM tools
        if is_parent or agent_type == "pm":
            allowed = self.PM_TOOLS.copy()
            logger.debug(f"PM/Parent process allowed tools: {allowed}")
            return sorted(allowed)

        # Check custom restrictions first
        if agent_type in self.custom_restrictions:
            allowed = self.custom_restrictions[agent_type]
        elif agent_type in self.AGENT_RESTRICTIONS:
            allowed = self.AGENT_RESTRICTIONS[agent_type]
        else:
            # Default to agent tools for unknown types
            logger.warning(
                f"Unknown agent type '{agent_type}', using default agent tools"
            )
            allowed = self.AGENT_TOOLS.copy()

        # Ensure TodoWrite is NEVER in child agent tools
        allowed = allowed - {"TodoWrite"}

        logger.debug(f"Agent '{agent_type}' allowed tools: {allowed}")
        return sorted(allowed)

    def format_allowed_tools_arg(self, agent_type: str, is_parent: bool = False) -> str:
        """
        Format the allowed tools as a comma-separated string for --allowedTools argument.

        Args:
            agent_type: The type of agent
            is_parent: Whether this is the parent process

        Returns:
            Comma-separated string of allowed tools
        """
        allowed_tools = self.get_allowed_tools(agent_type, is_parent)
        return ",".join(allowed_tools)

    def set_custom_restrictions(self, agent_type: str, allowed_tools: Set[str]):
        """
        Set custom tool restrictions for a specific agent type.

        Args:
            agent_type: The agent type to customize
            allowed_tools: Set of allowed tool names
        """
        agent_type = agent_type.lower().replace(" ", "_").replace("-", "_")

        # Ensure TodoWrite is not in custom restrictions for non-PM agents
        if agent_type != "pm" and "TodoWrite" in allowed_tools:
            logger.warning(
                f"Removing TodoWrite from custom restrictions for {agent_type}"
            )
            allowed_tools = allowed_tools - {"TodoWrite"}

        self.custom_restrictions[agent_type] = allowed_tools
        logger.info(f"Set custom tool restrictions for {agent_type}: {allowed_tools}")

    def validate_tool_usage(
        self, agent_type: str, tool_name: str, is_parent: bool = False
    ) -> bool:
        """
        Validate if an agent is allowed to use a specific tool.

        Args:
            agent_type: The type of agent
            tool_name: The name of the tool
            is_parent: Whether this is the parent process

        Returns:
            True if allowed, False otherwise
        """
        allowed_tools = self.get_allowed_tools(agent_type, is_parent)
        is_allowed = tool_name in allowed_tools

        if not is_allowed:
            logger.warning(
                f"Agent '{agent_type}' attempted to use forbidden tool '{tool_name}'"
            )

        return is_allowed

    def get_todo_guidance(self, agent_type: str) -> str:
        """
        Get guidance text for agents on how to handle TODOs.

        Args:
            agent_type: The type of agent

        Returns:
            Guidance text for handling TODOs
        """
        if agent_type.lower() == "pm":
            return """You have access to the TodoWrite tool for tracking tasks. Always prefix todos with [Agent] to indicate delegation target."""
        return """You do NOT have access to TodoWrite. Instead, when you identify tasks that need tracking:
1. Include them in your response with clear markers like "TODO:" or "TASK:"
2. Format them as a structured list with priority and description
3. The PM will extract and track these in the central todo list
4. Example format:
   TODO (High Priority): [Research] Analyze authentication patterns
   TODO (Medium Priority): [QA] Write tests for new endpoints"""


# Global instance for easy access
tool_access_control = ToolAccessControl()
