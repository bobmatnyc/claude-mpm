"""Interactive CLI modules for Claude MPM.

This package contains interactive user interfaces and wizards for various
Claude MPM operations, providing user-friendly alternatives to command-line
arguments.
"""

from .agent_wizard import (
    AgentWizard,
    run_interactive_agent_manager,
    run_interactive_agent_wizard,
)
from .skills_wizard import SkillsWizard, discover_and_link_runtime_skills

__all__ = [
    "AgentWizard",
    "SkillsWizard",
    "discover_and_link_runtime_skills",
    "run_interactive_agent_manager",
    "run_interactive_agent_wizard",
]
