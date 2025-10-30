"""Skills registry - manages bundled and discovered skills."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class Skill:
    """Represents a skill that can be used by agents."""

    name: str
    path: Path
    content: str
    source: str  # 'bundled', 'user', or 'project'

    # Version tracking fields
    version: str = "0.1.0"
    skill_id: str = ""  # defaults to name if not provided

    # Existing fields
    description: str = ""
    agent_types: List[str] = None  # Which agent types can use this skill

    # Optional metadata
    updated_at: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        """Initialize default values if not provided."""
        if self.agent_types is None:
            self.agent_types = []
        if self.tags is None:
            self.tags = []
        if not self.skill_id:
            self.skill_id = self.name


class SkillsRegistry:
    """Registry for managing skills across all tiers."""

    def __init__(self):
        """Initialize the skills registry."""
        self.skills: Dict[str, Skill] = {}
        self._load_bundled_skills()
        self._load_user_skills()
        self._load_project_skills()

    def _parse_skill_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from skill markdown file.

        Returns:
            Dict with frontmatter fields or empty dict if no frontmatter
        """
        # Check for YAML frontmatter
        if not content.startswith("---"):
            return {}

        # Extract frontmatter (match: ---\n...yaml...\n---\nrest)
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
        if not match:
            return {}

        try:
            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter or {}
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse skill frontmatter: {e}")
            return {}

    def _load_bundled_skills(self):
        """Load skills bundled with MPM."""
        bundled_dir = Path(__file__).parent / "bundled"
        if not bundled_dir.exists():
            logger.warning(f"Bundled skills directory not found: {bundled_dir}")
            return

        skill_count = 0
        for skill_file in bundled_dir.glob("*.md"):
            try:
                skill_name = skill_file.stem
                content = skill_file.read_text(encoding="utf-8")

                # Parse frontmatter
                frontmatter = self._parse_skill_frontmatter(content)

                # Extract version fields from frontmatter
                version = frontmatter.get("skill_version", "0.1.0")
                skill_id = frontmatter.get("skill_id", skill_name)
                updated_at = frontmatter.get("updated_at")
                tags = frontmatter.get("tags", [])

                # Extract description (from frontmatter or fallback to content parsing)
                description = frontmatter.get("description", "")
                if not description:
                    description = self._extract_description(content)

                self.skills[skill_name] = Skill(
                    name=skill_name,
                    path=skill_file,
                    content=content,
                    source="bundled",
                    version=version,
                    skill_id=skill_id,
                    description=description,
                    updated_at=updated_at,
                    tags=tags,
                )
                skill_count += 1
            except Exception as e:
                logger.error(f"Error loading bundled skill {skill_file}: {e}")

        logger.debug(f"Loaded {skill_count} bundled skills")

    def _load_user_skills(self):
        """Load user-installed skills from ~/.claude/skills/"""
        user_skills_dir = Path.home() / ".claude" / "skills"
        if not user_skills_dir.exists():
            logger.debug("User skills directory not found, skipping")
            return

        skill_count = 0
        for skill_file in user_skills_dir.glob("*.md"):
            try:
                skill_name = skill_file.stem
                # User skills override bundled skills
                content = skill_file.read_text(encoding="utf-8")

                # Parse frontmatter
                frontmatter = self._parse_skill_frontmatter(content)

                # Extract version fields from frontmatter
                version = frontmatter.get("skill_version", "0.1.0")
                skill_id = frontmatter.get("skill_id", skill_name)
                updated_at = frontmatter.get("updated_at")
                tags = frontmatter.get("tags", [])

                # Extract description (from frontmatter or fallback to content parsing)
                description = frontmatter.get("description", "")
                if not description:
                    description = self._extract_description(content)

                self.skills[skill_name] = Skill(
                    name=skill_name,
                    path=skill_file,
                    content=content,
                    source="user",
                    version=version,
                    skill_id=skill_id,
                    description=description,
                    updated_at=updated_at,
                    tags=tags,
                )
                skill_count += 1
                logger.debug(f"User skill '{skill_name}' overrides bundled version")
            except Exception as e:
                logger.error(f"Error loading user skill {skill_file}: {e}")

        if skill_count > 0:
            logger.debug(f"Loaded {skill_count} user skills")

    def _load_project_skills(self):
        """Load project-specific skills from .claude/skills/"""
        project_skills_dir = Path.cwd() / ".claude" / "skills"
        if not project_skills_dir.exists():
            logger.debug("Project skills directory not found, skipping")
            return

        skill_count = 0
        for skill_file in project_skills_dir.glob("*.md"):
            try:
                skill_name = skill_file.stem
                # Project skills override both user and bundled skills
                content = skill_file.read_text(encoding="utf-8")

                # Parse frontmatter
                frontmatter = self._parse_skill_frontmatter(content)

                # Extract version fields from frontmatter
                version = frontmatter.get("skill_version", "0.1.0")
                skill_id = frontmatter.get("skill_id", skill_name)
                updated_at = frontmatter.get("updated_at")
                tags = frontmatter.get("tags", [])

                # Extract description (from frontmatter or fallback to content parsing)
                description = frontmatter.get("description", "")
                if not description:
                    description = self._extract_description(content)

                self.skills[skill_name] = Skill(
                    name=skill_name,
                    path=skill_file,
                    content=content,
                    source="project",
                    version=version,
                    skill_id=skill_id,
                    description=description,
                    updated_at=updated_at,
                    tags=tags,
                )
                skill_count += 1
                logger.debug(f"Project skill '{skill_name}' overrides other versions")
            except Exception as e:
                logger.error(f"Error loading project skill {skill_file}: {e}")

        if skill_count > 0:
            logger.debug(f"Loaded {skill_count} project skills")

    def _extract_description(self, content: str) -> str:
        """Extract description from skill content (first paragraph or summary)."""
        lines = content.strip().split("\n")
        description_lines = []

        # Skip title (first line starting with #)
        start_idx = 0
        if lines and lines[0].startswith("#"):
            start_idx = 1

        # Find first non-empty paragraph
        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                if description_lines:
                    break
                continue
            if line.startswith("#"):
                break
            description_lines.append(line)

        return " ".join(description_lines)[:200]  # Limit to 200 chars

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self.skills.get(name)

    def list_skills(self, source: Optional[str] = None) -> List[Skill]:
        """List all skills, optionally filtered by source."""
        if source:
            return [s for s in self.skills.values() if s.source == source]
        return list(self.skills.values())

    def get_skills_for_agent(self, agent_type: str) -> List[Skill]:
        """
        Get skills mapped to a specific agent type.

        Args:
            agent_type: Agent type/ID (e.g., 'engineer', 'python_engineer')

        Returns:
            List of skills applicable to this agent type
        """
        # Filter skills that explicitly list this agent type
        # If a skill has no agent_types specified, it's available to all agents
        return [
            skill
            for skill in self.skills.values()
            if not skill.agent_types or agent_type in skill.agent_types
        ]

    def reload(self):
        """Reload all skills from disk."""
        logger.info("Reloading skills registry...")
        self.skills.clear()
        self._load_bundled_skills()
        self._load_user_skills()
        self._load_project_skills()
        logger.info(f"Skills registry reloaded with {len(self.skills)} skills")


# Global registry instance (singleton pattern)
_registry: Optional[SkillsRegistry] = None


def get_registry() -> SkillsRegistry:
    """Get the global skills registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = SkillsRegistry()
    return _registry
