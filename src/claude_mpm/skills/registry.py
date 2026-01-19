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
    """Represents a skill that can be used by agents.

    Supports agentskills.io specification with backward compatibility for legacy claude-mpm format.

    Spec fields (agentskills.io):
    - name: Required, 1-64 chars, lowercase alphanumeric + hyphens
    - description: Required, 1-1024 chars
    - license: Optional, license name or reference
    - compatibility: Optional, max 500 chars, environment requirements
    - metadata: Optional, key-value mapping for arbitrary data
    - allowed_tools: Optional, list of pre-approved tools

    Internal fields:
    - path: Path to skill file
    - content: Skill content (markdown)
    - source: Origin of skill ('bundled', 'user', 'project', 'pm')
    - version: Skill version (from metadata.version or top-level)
    - skill_id: Internal ID (defaults to name)
    - agent_types: Which agent types can use this skill
    - updated_at: Last update timestamp (from metadata.updated)
    - tags: Tags for discovery (from metadata.tags or top-level)

    Claude-mpm extensions (preserved for backward compat):
    - category: Skill category for organization
    - toolchain: Associated toolchain (python, javascript, etc.)
    - progressive_disclosure: Progressive disclosure configuration
    - user_invocable: Whether skill can be manually invoked
    """

    # Core spec fields (agentskills.io)
    name: str
    description: str
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Dict[str, Any] = None
    allowed_tools: List[str] = None

    # Internal fields (not in frontmatter spec)
    path: Path = None
    content: str = ""
    source: str = "bundled"  # 'bundled', 'user', 'project', 'pm'

    # Derived fields (from metadata or fallback)
    version: str = "0.1.0"  # From metadata.version or top-level
    skill_id: str = ""  # Internal ID (defaults to name)
    agent_types: List[str] = None  # Which agent types can use this skill
    updated_at: Optional[str] = None  # From metadata.updated
    tags: List[str] = None  # From metadata.tags or top-level

    # Claude-mpm extensions (preserved for backward compat)
    category: Optional[str] = None
    toolchain: Optional[str] = None
    progressive_disclosure: Optional[Dict[str, Any]] = None
    user_invocable: bool = False

    def __post_init__(self):
        """Initialize default values if not provided."""
        if self.metadata is None:
            self.metadata = {}
        if self.agent_types is None:
            self.agent_types = []
        if self.tags is None:
            self.tags = []
        if self.allowed_tools is None:
            self.allowed_tools = []
        if not self.skill_id:
            self.skill_id = self.name


def validate_agentskills_spec(skill: Skill) -> tuple[bool, List[str]]:
    """Validate skill against agentskills.io specification.

    Args:
        skill: Skill object to validate

    Returns:
        Tuple of (is_valid, list_of_warnings)
        - is_valid: True if skill meets spec requirements
        - warnings: List of warning messages for spec violations
    """
    warnings = []

    # Validate name (required field)
    if not skill.name:
        warnings.append("Missing required field: name")
        return False, warnings

    # Validate name format: lowercase alphanumeric + hyphens, no leading/trailing hyphens
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", skill.name):
        warnings.append(
            f"Invalid name format: '{skill.name}' (must be lowercase alphanumeric with hyphens, "
            "no leading/trailing hyphens, no consecutive hyphens)"
        )

    # Validate name length (max 64 chars)
    if len(skill.name) > 64:
        warnings.append(
            f"Name too long: {len(skill.name)} chars (max 64 per agentskills.io spec)"
        )

    # Validate description (required field)
    if not skill.description:
        warnings.append("Missing required field: description")
        return False, warnings

    # Validate description length (1-1024 chars)
    desc_len = len(skill.description)
    if desc_len < 1 or desc_len > 1024:
        warnings.append(
            f"Description length {desc_len} chars is outside spec range (1-1024 chars)"
        )

    # Validate compatibility length (max 500 chars)
    if skill.compatibility and len(skill.compatibility) > 500:
        warnings.append(
            f"Compatibility field too long: {len(skill.compatibility)} chars (max 500)"
        )

    # Validate metadata is dict
    if skill.metadata is not None and not isinstance(skill.metadata, dict):
        warnings.append("Metadata must be a key-value mapping (dict)")

    # Check for spec-compliant metadata structure
    spec_metadata_fields = ["version", "author", "updated", "tags"]
    for field in spec_metadata_fields:
        if hasattr(skill, field):
            field_value = getattr(skill, field)
            if field_value and field not in skill.metadata:
                warnings.append(
                    f"Field '{field}' should be in metadata block per agentskills.io spec "
                    f"(found as top-level field)"
                )

    # Valid if no errors (only warnings allowed)
    is_valid = len(warnings) == 0 or all("should be in metadata" in w for w in warnings)
    return is_valid, warnings


class SkillsRegistry:
    """Registry for managing skills across all tiers."""

    def __init__(self):
        """Initialize the skills registry."""
        self.skills: Dict[str, Skill] = {}
        self._load_bundled_skills()
        self._load_user_skills()
        self._load_project_skills()

    def _parse_skill_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from skill markdown file with spec validation.

        Supports both agentskills.io spec format and legacy claude-mpm format
        with automatic migration.

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
            if not frontmatter:
                return {}

            # Apply backward compatibility migration
            return self._apply_backward_compatibility(frontmatter)
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse skill frontmatter: {e}")
            return {}

    def _apply_backward_compatibility(
        self, frontmatter: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply backward compatibility transformations to legacy frontmatter.

        Auto-migrates legacy claude-mpm fields to agentskills.io spec format:
        - version → metadata.version
        - author → metadata.author
        - updated → metadata.updated
        - tags → metadata.tags (if not already present)

        Args:
            frontmatter: Parsed frontmatter dict

        Returns:
            Transformed frontmatter with spec-compliant structure
        """
        # Initialize metadata if not present
        if "metadata" not in frontmatter:
            frontmatter["metadata"] = {}

        metadata = frontmatter["metadata"]

        # Auto-migrate version (top-level → metadata.version)
        if "version" in frontmatter and "version" not in metadata:
            metadata["version"] = frontmatter["version"]
            logger.debug(
                f"Auto-migrated 'version' to metadata for skill '{frontmatter.get('name', 'unknown')}'"
            )

        # Auto-migrate author (top-level → metadata.author)
        if "author" in frontmatter and "author" not in metadata:
            metadata["author"] = frontmatter["author"]
            logger.debug(
                f"Auto-migrated 'author' to metadata for skill '{frontmatter.get('name', 'unknown')}'"
            )

        # Auto-migrate updated (top-level → metadata.updated)
        if "updated" in frontmatter and "updated" not in metadata:
            metadata["updated"] = frontmatter["updated"]
            logger.debug(
                f"Auto-migrated 'updated' to metadata for skill '{frontmatter.get('name', 'unknown')}'"
            )

        # Auto-migrate tags (top-level → metadata.tags)
        if "tags" in frontmatter and "tags" not in metadata:
            metadata["tags"] = frontmatter["tags"]
            logger.debug(
                f"Auto-migrated 'tags' to metadata for skill '{frontmatter.get('name', 'unknown')}'"
            )

        # Parse allowed-tools from space-delimited string to list
        if "allowed-tools" in frontmatter:
            allowed_tools = frontmatter["allowed-tools"]
            if isinstance(allowed_tools, str):
                frontmatter["allowed-tools"] = allowed_tools.split()

        # Set default compatibility for claude-code if not present
        if "compatibility" not in frontmatter:
            frontmatter["compatibility"] = "claude-code"

        return frontmatter

    def _create_skill_from_frontmatter(
        self, frontmatter: Dict[str, Any], path: Path, content: str, source: str
    ) -> Optional[Skill]:
        """Create Skill object from frontmatter with spec compliance.

        Args:
            frontmatter: Parsed and migrated frontmatter dict
            path: Path to skill file
            content: Full skill content
            source: Source type ('bundled', 'user', 'project', 'pm')

        Returns:
            Skill object or None if required fields missing
        """
        # Extract spec fields (required)
        name = frontmatter.get("name")
        description = frontmatter.get("description", "")

        # If name not in frontmatter, use filename stem
        if not name:
            name = path.stem

        # If description not in frontmatter, extract from content
        if not description:
            description = self._extract_description(content)

        # Validate required fields
        if not name or not description:
            logger.warning(
                f"Skipping skill at {path}: missing required field (name or description)"
            )
            return None

        # Extract spec fields (optional)
        license_field = frontmatter.get("license")
        compatibility = frontmatter.get("compatibility", "claude-code")
        metadata = frontmatter.get("metadata", {})
        allowed_tools = frontmatter.get("allowed-tools", [])

        # Extract derived fields from metadata or top-level
        version = frontmatter.get("version") or metadata.get("version", "0.1.0")
        skill_id = frontmatter.get("skill_id", name)
        updated_at = frontmatter.get("updated_at") or metadata.get("updated")
        tags = frontmatter.get("tags", []) or metadata.get("tags", [])

        # Extract claude-mpm extensions
        category = frontmatter.get("category")
        toolchain = frontmatter.get("toolchain")
        progressive_disclosure = frontmatter.get("progressive_disclosure")
        user_invocable = frontmatter.get("user-invocable", False)

        # Create skill object
        return Skill(
            name=name,
            description=description,
            license=license_field,
            compatibility=compatibility,
            metadata=metadata,
            allowed_tools=allowed_tools,
            path=path,
            content=content,
            source=source,
            version=version,
            skill_id=skill_id,
            updated_at=updated_at,
            tags=tags,
            category=category,
            toolchain=toolchain,
            progressive_disclosure=progressive_disclosure,
            user_invocable=user_invocable,
        )

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

                # Parse frontmatter with backward compatibility
                frontmatter = self._parse_skill_frontmatter(content)

                # Create skill from frontmatter
                skill = self._create_skill_from_frontmatter(
                    frontmatter, skill_file, content, "bundled"
                )
                if skill:
                    self.skills[skill_name] = skill
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
                content = skill_file.read_text(encoding="utf-8")

                # Parse frontmatter with backward compatibility
                frontmatter = self._parse_skill_frontmatter(content)

                # Create skill from frontmatter
                skill = self._create_skill_from_frontmatter(
                    frontmatter, skill_file, content, "user"
                )
                if skill:
                    # User skills override bundled skills
                    self.skills[skill_name] = skill
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
                content = skill_file.read_text(encoding="utf-8")

                # Parse frontmatter with backward compatibility
                frontmatter = self._parse_skill_frontmatter(content)

                # Create skill from frontmatter
                skill = self._create_skill_from_frontmatter(
                    frontmatter, skill_file, content, "project"
                )
                if skill:
                    # Project skills override both user and bundled skills
                    self.skills[skill_name] = skill
                    skill_count += 1
                    logger.debug(
                        f"Project skill '{skill_name}' overrides other versions"
                    )
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
