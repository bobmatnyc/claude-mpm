"""Skills management services.

This package provides services for Git-based skills management:
- GitSkillSourceManager: Multi-repository orchestration with priority resolution
- SkillDiscoveryService: Parse skills from Git repositories (Markdown with YAML frontmatter)
"""

from claude_mpm.services.skills.git_skill_source_manager import GitSkillSourceManager
from claude_mpm.services.skills.skill_discovery_service import (
    SkillDiscoveryService,
    SkillMetadata,
)

__all__ = [
    "GitSkillSourceManager",
    "SkillDiscoveryService",
    "SkillMetadata",
]
