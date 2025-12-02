"""
Claude MPM Skills Package

Skills system for sharing common capabilities across agents.
This reduces redundancy by extracting shared patterns into reusable skills.

Skills can be:
- Bundled with MPM (in skills/bundled/)
- User-installed (in ~/.claude/skills/)
- Project-specific (in .claude/skills/)

New Skills Integration System:
- SkillsService: Core service for skill management
- AgentSkillsInjector: Dynamic skill injection into agent templates
- SkillsRegistry: Helper class for registry operations

Legacy System (maintained for compatibility):
- Skill: Dataclass for skill representation
- SkillManager: Legacy skill manager
- get_registry: Legacy registry access
"""

# New Skills Integration System
from .agent_skills_injector import AgentSkillsInjector

# Legacy System (maintained for compatibility)
from .registry import Skill, SkillsRegistry, get_registry
from .skill_manager import SkillManager
from .skills_registry import SkillsRegistry as SkillsRegistryHelper
from .skills_service import SkillsService

__all__ = [
    "AgentSkillsInjector",
    # Legacy System
    "Skill",
    "SkillManager",
    "SkillsRegistry",
    "SkillsRegistryHelper",
    # New Skills Integration System
    "SkillsService",
    "get_registry",
]
