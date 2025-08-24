"""
Claude PM Framework Agents Package

System-level agent implementations with Task Tool integration.
These agents provide specialized prompts and capabilities for PM orchestration.

Uses unified agent loader to load prompts from JSON templates in agents/templates/
for better structure and maintainability.
"""

# Import from unified agent loader
from .agent_loader import (
    clear_agent_cache,
    get_agent_prompt,
    list_available_agents,
    validate_agent_files,
)

# Import agent metadata (previously AGENT_CONFIG)
from .agents_metadata import (
    ALL_AGENT_CONFIGS,
    DATA_ENGINEER_CONFIG,
    DOCUMENTATION_CONFIG,
    ENGINEER_CONFIG,
    OPS_CONFIG,
    QA_CONFIG,
    RESEARCH_CONFIG,
    SECURITY_CONFIG,
    VERSION_CONTROL_CONFIG,
)

# Available system agents
__all__ = [
    "ALL_AGENT_CONFIGS",
    "DATA_ENGINEER_CONFIG",
    # Agent configs
    "DOCUMENTATION_CONFIG",
    "ENGINEER_CONFIG",
    "OPS_CONFIG",
    "QA_CONFIG",
    "RESEARCH_CONFIG",
    "SECURITY_CONFIG",
    # System registry
    "SYSTEM_AGENTS",
    "VERSION_CONTROL_CONFIG",
    "clear_agent_cache",
    # Generic agent interface
    "get_agent_prompt",
    # Agent utility functions
    "list_available_agents",
    "validate_agent_files",
]

# System agent registry - using generic agent loading
SYSTEM_AGENTS = {
    "documentation": {
        "agent_id": "documentation-agent",
        "config": DOCUMENTATION_CONFIG,
        "version": "2.0.0",
        "integration": "claude_pm_framework",
    },
    "version_control": {
        "agent_id": "version-control-agent",
        "config": VERSION_CONTROL_CONFIG,
        "version": "2.0.0",
        "integration": "claude_pm_framework",
    },
    "qa": {
        "agent_id": "qa-agent",
        "config": QA_CONFIG,
        "version": "2.0.0",
        "integration": "claude_pm_framework",
    },
    "research": {
        "agent_id": "research-agent",
        "config": RESEARCH_CONFIG,
        "version": "2.0.0",
        "integration": "claude_pm_framework",
    },
    "ops": {
        "agent_id": "ops-agent",
        "config": OPS_CONFIG,
        "version": "2.0.0",
        "integration": "claude_pm_framework",
    },
    "security": {
        "agent_id": "security-agent",
        "config": SECURITY_CONFIG,
        "version": "2.0.0",
        "integration": "claude_pm_framework",
    },
    "engineer": {
        "agent_id": "engineer-agent",
        "config": ENGINEER_CONFIG,
        "version": "2.0.0",
        "integration": "claude_pm_framework",
    },
    "data_engineer": {
        "agent_id": "data-engineer-agent",
        "config": DATA_ENGINEER_CONFIG,
        "version": "2.0.0",
        "integration": "claude_pm_framework",
    },
}


def get_system_agent_prompt(agent_type: str) -> str:
    """
    Get system agent prompt using the generic interface.

    Args:
        agent_type: Agent type (e.g., "documentation", "qa", "engineer")

    Returns:
        Agent prompt string

    Raises:
        ValueError: If agent type is not found
    """
    if agent_type not in SYSTEM_AGENTS:
        raise ValueError(f"Unknown agent type: {agent_type}")

    agent_id = SYSTEM_AGENTS[agent_type]["agent_id"]
    return get_agent_prompt(agent_id)
