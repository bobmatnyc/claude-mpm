"""
Claude MPM Skills Package

Skills system for sharing common capabilities across agents.
This reduces redundancy by extracting shared patterns into reusable skills.

Skills can be:
- Bundled with MPM (in skills/bundled/)
- User-installed (in ~/.claude/skills/)
- Project-specific (in .claude/skills/)
"""

from .registry import Skill, SkillsRegistry, get_registry
from .skill_manager import SkillManager

__all__ = [
    "Skill",
    "SkillsRegistry",
    "SkillManager",
    "get_registry",
]
