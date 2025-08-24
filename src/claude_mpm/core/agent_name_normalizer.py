"""Agent name normalization utilities for consistent naming across the system."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AgentNameNormalizer:
    """
    Handles agent name normalization to ensure consistency across:
    - TodoWrite prefixes
    - Task tool display
    - Agent type identification
    - Color coding
    """

    # Canonical agent names (standardized format)
    CANONICAL_NAMES = {
        "research": "Research",
        "engineer": "Engineer",
        "qa": "QA",
        "security": "Security",
        "documentation": "Documentation",
        "ops": "Ops",
        "version_control": "Version Control",
        "data_engineer": "Data Engineer",
        "architect": "Architect",
        "pm": "PM",
    }

    # Aliases and variations that map to canonical names
    ALIASES = {
        # Research variations
        "research": "research",
        "Research": "research",
        "RESEARCH": "research",
        "researcher": "research",
        # Engineer variations
        "engineer": "engineer",
        "Engineer": "engineer",
        "ENGINEER": "engineer",
        "engineering": "engineer",
        "dev": "engineer",
        "developer": "engineer",
        # QA variations
        "qa": "qa",
        "QA": "qa",
        "Qa": "qa",
        "quality": "qa",
        "testing": "qa",
        "test": "qa",
        # Security variations
        "security": "security",
        "Security": "security",
        "SECURITY": "security",
        "sec": "security",
        # Documentation variations
        "documentation": "documentation",
        "Documentation": "documentation",
        "docs": "documentation",
        "doc": "documentation",
        # Ops variations
        "ops": "ops",
        "Ops": "ops",
        "OPS": "ops",
        "operations": "ops",
        "devops": "ops",
        # Version Control variations
        "version_control": "version_control",
        "version control": "version_control",
        "Version Control": "version_control",
        "git": "version_control",
        "vcs": "version_control",
        # Data Engineer variations
        "data_engineer": "data_engineer",
        "data engineer": "data_engineer",
        "Data Engineer": "data_engineer",
        "data": "data_engineer",
        # Architect variations
        "architect": "architect",
        "Architect": "architect",
        "architecture": "architect",
        "arch": "architect",
        # PM variations
        "pm": "pm",
        "PM": "pm",
        "project_manager": "pm",
        "project manager": "pm",
    }

    # Agent colors for consistent display
    AGENT_COLORS = {
        "research": "\033[36m",  # Cyan
        "engineer": "\033[32m",  # Green
        "qa": "\033[33m",  # Yellow
        "security": "\033[31m",  # Red
        "documentation": "\033[34m",  # Blue
        "ops": "\033[35m",  # Magenta
        "version_control": "\033[37m",  # White
        "data_engineer": "\033[96m",  # Bright Cyan
        "architect": "\033[95m",  # Bright Magenta
        "pm": "\033[92m",  # Bright Green
    }

    COLOR_RESET = "\033[0m"

    @classmethod
    def normalize(cls, agent_name: str) -> str:
        """
        Normalize an agent name to its canonical form.

        Args:
            agent_name: The agent name to normalize

        Returns:
            The canonical agent name
        """
        if not agent_name:
            return "Engineer"  # Default

        # Clean the input
        cleaned = agent_name.strip().lower().replace("-", "_")

        # Check aliases first
        if cleaned in cls.ALIASES:
            canonical_key = cls.ALIASES[cleaned]
            return cls.CANONICAL_NAMES.get(canonical_key, "Engineer")

        # Check if it's already a canonical key
        if cleaned in cls.CANONICAL_NAMES:
            return cls.CANONICAL_NAMES[cleaned]

        # Try to find partial matches
        for alias, canonical_key in cls.ALIASES.items():
            if cleaned in alias or alias in cleaned:
                return cls.CANONICAL_NAMES.get(canonical_key, "Engineer")

        logger.warning(f"Unknown agent name '{agent_name}', defaulting to Engineer")
        return "Engineer"

    @classmethod
    def to_key(cls, agent_name: str) -> str:
        """
        Convert an agent name to its key format (lowercase with underscores).

        Args:
            agent_name: The agent name to convert

        Returns:
            The key format of the agent name
        """
        normalized = cls.normalize(agent_name)
        return normalized.lower().replace(" ", "_")

    @classmethod
    def to_todo_prefix(cls, agent_name: str) -> str:
        """
        Format agent name for TODO prefix (e.g., [Research]).

        Args:
            agent_name: The agent name to format

        Returns:
            The formatted TODO prefix
        """
        normalized = cls.normalize(agent_name)
        return f"[{normalized}]"

    @classmethod
    def colorize(cls, agent_name: str, text: Optional[str] = None) -> str:
        """
        Apply consistent color coding to agent names.

        Args:
            agent_name: The agent name to colorize
            text: Optional text to colorize (defaults to agent name)

        Returns:
            The colorized text
        """
        key = cls.to_key(agent_name)
        color = cls.AGENT_COLORS.get(key, "")
        display_text = text if text else cls.normalize(agent_name)

        if color:
            return f"{color}{display_text}{cls.COLOR_RESET}"
        return display_text

    @classmethod
    def extract_from_todo(cls, todo_text: str) -> Optional[str]:
        """
        Extract agent name from a TODO line.

        Args:
            todo_text: The TODO text (e.g., "[Research] Analyze patterns")

        Returns:
            The normalized agent name, or None if not found
        """
        import re

        # Match [Agent] at the beginning
        match = re.match(r"^\[([^\]]+)\]", todo_text.strip())
        if match:
            return cls.normalize(match.group(1))

        # Try to find agent mentions in the text
        text_lower = todo_text.lower()
        for alias, canonical_key in cls.ALIASES.items():
            if alias in text_lower:
                return cls.CANONICAL_NAMES.get(canonical_key)

        return None

    @classmethod
    def validate_todo_format(cls, todo_text: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a TODO has proper agent prefix.

        Args:
            todo_text: The TODO text to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        agent = cls.extract_from_todo(todo_text)
        if not agent:
            return (
                False,
                "TODO must start with [Agent] prefix (e.g., [Research], [Engineer])",
            )

        # Check if it's a valid agent
        if cls.to_key(agent) not in cls.CANONICAL_NAMES:
            return (
                False,
                f"Unknown agent '{agent}'. Valid agents: {', '.join(cls.CANONICAL_NAMES.values())}",
            )

        return True, None

    @classmethod
    def to_task_format(cls, agent_name: str) -> str:
        """
        Convert agent name from TodoWrite format to Task tool format.

        Args:
            agent_name: The agent name in TodoWrite format (e.g., "Research", "Version Control")

        Returns:
            The agent name in Task tool format (e.g., "research", "version-control")

        Examples:
            "Research" → "research"
            "Version Control" → "version-control"
            "Data Engineer" → "data-engineer"
            "QA" → "qa"
        """
        # First normalize to canonical form
        normalized = cls.normalize(agent_name)
        # Convert to lowercase and replace spaces with hyphens
        return normalized.lower().replace(" ", "-")

    @classmethod
    def from_task_format(cls, task_format: str) -> str:
        """
        Convert agent name from Task tool format to TodoWrite format.

        Args:
            task_format: The agent name in Task tool format (e.g., "research", "version-control")

        Returns:
            The agent name in TodoWrite format (e.g., "Research", "Version Control")

        Examples:
            "research" → "Research"
            "version-control" → "Version Control"
            "data-engineer" → "Data Engineer"
            "qa" → "QA"
        """
        # Replace hyphens with underscores for lookup
        lookup_key = task_format.replace("-", "_")

        # Check if it's a valid canonical key
        if lookup_key in cls.CANONICAL_NAMES:
            return cls.CANONICAL_NAMES[lookup_key]

        # Try normalizing as-is
        return cls.normalize(task_format)


# Global instance for easy access
agent_name_normalizer = AgentNameNormalizer()
