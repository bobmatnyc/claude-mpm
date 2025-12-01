"""Service for discovering and parsing skills from Git repositories.

Skills are stored as Markdown files with YAML frontmatter. This service handles:
- Discovery of skill files in repository cache
- Parsing of YAML frontmatter for metadata
- Extraction of skill content (body)
- Detection of bundled resources (scripts/, references/, assets/)

Design Decision: YAML Frontmatter Format

Rationale: YAML frontmatter is a well-established pattern for metadata in
Markdown files (used by Jekyll, Hugo, MkDocs). It provides clean separation
between metadata and content, with excellent library support.

Trade-offs:
- Standardization: Widely recognized format
- Parsing Complexity: Requires regex + YAML parsing
- Extensibility: Easy to add new metadata fields

Example Skill File:
    ---
    name: code-review
    description: Comprehensive code review skill
    skill_version: 1.0.0
    tags: [review, quality, best-practices]
    agent_types: [engineer, qa]
    ---

    # Code Review Skill

    When reviewing code, check for:
    - Code quality and style
    - Security vulnerabilities
    ...
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from claude_mpm.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SkillMetadata:
    """Metadata extracted from skill file.

    Attributes:
        name: Skill name (human-readable)
        description: Brief description of skill purpose
        skill_version: Version string (e.g., "1.0.0")
        tags: List of tags for categorization
        agent_types: Optional list of agent types this skill applies to
        source_file: Path to skill file
        resources: Optional list of bundled resource paths

    Example:
        >>> metadata = SkillMetadata(
        ...     name="code-review",
        ...     description="Comprehensive code review",
        ...     skill_version="1.0.0",
        ...     tags=["review", "quality"],
        ...     agent_types=["engineer"],
        ...     source_file=Path("skills/code-review.md"),
        ...     resources=[]
        ... )
    """

    name: str
    description: str
    skill_version: str
    tags: List[str]
    agent_types: Optional[List[str]]
    source_file: Path
    resources: Optional[List[Path]]


class SkillDiscoveryService:
    """Discovers and parses skills from Git repositories.

    Skills Format:
        - Markdown files with YAML frontmatter
        - Frontmatter contains metadata (name, description, version, tags)
        - Body contains skill instructions/prompt
        - Optional bundled resources in scripts/, references/, assets/

    Design Pattern: Service with Single Responsibility

    This service focuses solely on discovery and parsing. Syncing, caching,
    and priority resolution are handled by GitSkillSourceManager.

    Example:
        >>> service = SkillDiscoveryService(Path("~/.claude-mpm/cache/skills/system"))
        >>> skills = service.discover_skills()
        >>> for skill in skills:
        ...     print(f"{skill['name']}: {skill['description']}")
    """

    def __init__(self, skills_dir: Path):
        """Initialize skill discovery service.

        Args:
            skills_dir: Directory containing skill files
        """
        self.skills_dir = skills_dir
        self.logger = get_logger(__name__)

    def discover_skills(self) -> List[Dict[str, Any]]:
        """Discover all skills in directory.

        Scans directory RECURSIVELY for SKILL.md files and parses each as a skill.
        This supports nested Git repository structures while deploying to flat structure.

        Nested Repository Structure:
            collaboration/
                dispatching-parallel-agents/SKILL.md
                brainstorming/SKILL.md
            debugging/
                systematic-debugging/SKILL.md

        Deployed Flat Structure:
            collaboration-dispatching-parallel-agents/SKILL.md
            collaboration-brainstorming/SKILL.md
            debugging-systematic-debugging/SKILL.md

        Skips files that can't be parsed or are missing required fields.

        Returns:
            List of skill dictionaries:
            [
                {
                    "skill_id": str,           # Normalized skill ID
                    "name": str,               # Human-readable name
                    "description": str,        # Brief description
                    "skill_version": str,      # Version string
                    "tags": List[str],         # Tags for categorization
                    "agent_types": List[str],  # Applicable agent types (optional)
                    "content": str,            # Skill body content
                    "source_file": str,        # Path to skill file
                    "resources": List[str],    # Bundled resource paths (optional)
                    "deployment_name": str,    # Flattened deployment directory name
                    "relative_path": str       # Relative path from skills_dir to SKILL.md
                }
            ]

        Example:
            >>> service = SkillDiscoveryService(Path("cache/skills/system"))
            >>> skills = service.discover_skills()
            >>> print(f"Found {len(skills)} skills")
        """
        skills = []

        if not self.skills_dir.exists():
            self.logger.debug(f"Skills directory does not exist: {self.skills_dir}")
            return skills

        # Find all SKILL.md files recursively (Claude Code standard naming)
        skill_md_files = list(self.skills_dir.rglob("SKILL.md"))

        # Also find legacy *.md files in top-level directory for backward compatibility
        legacy_md_files = [
            f
            for f in self.skills_dir.glob("*.md")
            if f.name != "SKILL.md" and f.name.lower() != "readme.md"
        ]

        all_skill_files = skill_md_files + legacy_md_files

        self.logger.debug(
            f"Found {len(skill_md_files)} SKILL.md files recursively "
            f"and {len(legacy_md_files)} legacy .md files in {self.skills_dir}"
        )

        # Track deployment names to detect collisions
        deployment_names = {}

        for skill_file in all_skill_files:
            try:
                # Calculate deployment name from path
                deployment_name = self._calculate_deployment_name(skill_file)

                # Detect name collisions
                if deployment_name in deployment_names:
                    self.logger.warning(
                        f"Deployment name collision: '{deployment_name}' would be created by both:\n"
                        f"  - {deployment_names[deployment_name]}\n"
                        f"  - {skill_file}\n"
                        f"Skipping {skill_file} to avoid overwrite."
                    )
                    continue

                skill_dict = self._parse_skill_file(skill_file)
                if skill_dict:
                    # Add deployment metadata
                    skill_dict["deployment_name"] = deployment_name
                    skill_dict["relative_path"] = str(
                        skill_file.relative_to(self.skills_dir)
                    )

                    skills.append(skill_dict)
                    deployment_names[deployment_name] = skill_file
                    self.logger.debug(
                        f"Successfully parsed skill: {skill_file.name} -> {deployment_name}"
                    )
                else:
                    self.logger.warning(
                        f"Failed to parse skill (missing required fields): {skill_file}"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to parse skill {skill_file}: {e}")

        self.logger.info(f"Discovered {len(skills)} skills from {self.skills_dir.name}")
        return skills

    def _parse_skill_file(self, skill_file: Path) -> Optional[Dict[str, Any]]:
        """Parse a skill Markdown file with YAML frontmatter.

        Expected Format:
            ---
            name: skill-name
            description: Brief description
            skill_version: 1.0.0
            tags: [tag1, tag2]
            agent_types: [engineer, qa]  # Optional
            ---

            # Skill Content

            Skill instructions and prompt here...

        Args:
            skill_file: Path to skill .md file

        Returns:
            Skill dictionary or None if parsing fails

        Error Handling:
            - Returns None if frontmatter is missing
            - Returns None if required fields are missing (name, description)
            - Uses defaults for optional fields (tags=[], agent_types=None)
            - Logs warnings for parsing errors
        """
        try:
            content = skill_file.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Failed to read file {skill_file}: {e}")
            return None

        # Extract YAML frontmatter and body
        try:
            frontmatter, body = self._extract_frontmatter(content)
        except Exception as e:
            self.logger.warning(f"No valid frontmatter in {skill_file.name}: {e}")
            return None

        # Validate required fields
        if "name" not in frontmatter:
            self.logger.warning(f"Missing 'name' field in {skill_file.name}")
            return None

        if "description" not in frontmatter:
            self.logger.warning(f"Missing 'description' field in {skill_file.name}")
            return None

        # Extract metadata with defaults
        name = frontmatter["name"]
        description = frontmatter["description"]
        skill_version = frontmatter.get("skill_version", "1.0.0")
        tags = frontmatter.get("tags", [])
        agent_types = frontmatter.get("agent_types", None)

        # Ensure tags is a list
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = []

        # Ensure agent_types is a list (if present)
        if agent_types is not None:
            if isinstance(agent_types, str):
                agent_types = [agent_types]
            elif not isinstance(agent_types, list):
                agent_types = None

        # Generate skill_id from name (lowercase, replace spaces/underscores with hyphens)
        skill_id = self._generate_skill_id(name)

        # Find bundled resources
        resources = self._find_bundled_resources(skill_file)

        # Build skill dictionary
        skill_dict = {
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "skill_version": skill_version,
            "tags": tags,
            "content": body.strip(),
            "source_file": str(skill_file),
        }

        # Add optional fields
        if agent_types is not None:
            skill_dict["agent_types"] = agent_types

        if resources:
            skill_dict["resources"] = [str(r) for r in resources]

        return skill_dict

    def _extract_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Extract YAML frontmatter and body from Markdown.

        Frontmatter must be at the start of the file, delimited by "---".

        Args:
            content: Markdown file content

        Returns:
            Tuple of (frontmatter_dict, body_content)

        Raises:
            ValueError: If no valid frontmatter found

        Frontmatter Format:
            ---
            key: value
            list: [item1, item2]
            ---

            Body content here...

        Example:
            >>> content = "---\\nname: test\\n---\\nBody"
            >>> frontmatter, body = service._extract_frontmatter(content)
            >>> frontmatter["name"]
            'test'
            >>> body
            'Body'
        """
        # Use regex to extract frontmatter between --- markers
        # Pattern: Start of string, ---, content, ---, rest
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            raise ValueError("No valid YAML frontmatter found")

        frontmatter_text = match.group(1)
        body = match.group(2)

        # Parse YAML
        try:
            frontmatter = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in frontmatter: {e}") from e

        if not isinstance(frontmatter, dict):
            raise ValueError("Frontmatter must be a YAML dictionary")

        return frontmatter, body

    def _calculate_deployment_name(self, skill_file: Path) -> str:
        """Calculate flat deployment name from nested skill path.

        Flattens nested Git repository structure into hyphen-separated name
        suitable for Claude Code's flat skill directory structure.

        Path Flattening Algorithm:
        1. Get relative path from skills_dir to skill file
        2. Extract all parent directory names (excluding the final skill directory)
        3. Join path components with hyphens
        4. Normalize to lowercase, remove special characters

        Args:
            skill_file: Path to SKILL.md or skill markdown file

        Returns:
            Flattened deployment directory name

        Examples:
            >>> # Nested repository structure
            >>> skill_file = Path("cache/skills/system/collaboration/dispatching-parallel-agents/SKILL.md")
            >>> name = service._calculate_deployment_name(skill_file)
            >>> name
            'collaboration-dispatching-parallel-agents'

            >>> # Single-level structure (legacy)
            >>> skill_file = Path("cache/skills/system/code-review.md")
            >>> name = service._calculate_deployment_name(skill_file)
            >>> name
            'code-review'

            >>> # Deep nesting
            >>> skill_file = Path("cache/skills/system/aws/s3/bucket-ops/SKILL.md")
            >>> name = service._calculate_deployment_name(skill_file)
            >>> name
            'aws-s3-bucket-ops'
        """
        # Get relative path from skills_dir to skill file
        try:
            relative_path = skill_file.relative_to(self.skills_dir)
        except ValueError:
            # Fallback: skill_file is not under skills_dir
            # Use just the filename
            self.logger.warning(
                f"Skill file {skill_file} is not under {self.skills_dir}, "
                f"using filename as deployment name"
            )
            return skill_file.stem

        # Get all path parts (directories + filename)
        parts = list(relative_path.parts)

        # Handle different structures:
        # 1. SKILL.md case: collaboration/dispatching-parallel-agents/SKILL.md
        #    -> Take parent directories: ['collaboration', 'dispatching-parallel-agents']
        # 2. Legacy .md case: code-review.md
        #    -> Take just filename stem: ['code-review']

        if skill_file.name == "SKILL.md":
            # SKILL.md case: use all parent directories as deployment name
            # Remove the final 'SKILL.md' part
            deployment_parts = parts[:-1]

            if not deployment_parts:
                # Edge case: SKILL.md at top level
                # Use parent directory name or 'skill'
                deployment_parts = ["skill"]
        else:
            # Legacy .md case: use filename stem
            deployment_parts = [skill_file.stem]

        # Join with hyphens and normalize
        deployment_name = "-".join(deployment_parts)

        # Normalize: lowercase, remove special chars, collapse hyphens
        deployment_name = deployment_name.lower()
        deployment_name = deployment_name.replace("_", "-")
        deployment_name = re.sub(r"[^a-z0-9-]+", "", deployment_name)
        deployment_name = re.sub(r"-+", "-", deployment_name)
        return deployment_name.strip("-")

    def _generate_skill_id(self, name: str) -> str:
        """Generate skill ID from name.

        Converts name to lowercase, replaces spaces/underscores with hyphens,
        removes non-alphanumeric characters, and collapses multiple hyphens.

        Args:
            name: Human-readable skill name

        Returns:
            Normalized skill ID

        Example:
            >>> service._generate_skill_id("Code Review")
            'code-review'
            >>> service._generate_skill_id("Python_Style-Check!")
            'python-style-check'
        """
        # 1. Convert to lowercase
        skill_id = name.lower()

        # 2. Replace spaces and underscores with hyphens
        skill_id = skill_id.replace(" ", "-").replace("_", "-")

        # 3. Remove any characters that aren't alphanumeric or hyphens
        skill_id = re.sub(r"[^a-z0-9-]+", "", skill_id)

        # 4. Collapse multiple consecutive hyphens into one
        skill_id = re.sub(r"-+", "-", skill_id)

        # 5. Remove leading/trailing hyphens
        return skill_id.strip("-")

    def _find_bundled_resources(self, skill_file: Path) -> List[Path]:
        """Find bundled resources for a skill.

        Resources are in parallel directories:
            skills/
                skill-name.md
            scripts/
                skill-name/
                    helper.sh
            references/
                skill-name/
                    docs.md
            assets/
                skill-name/
                    image.png

        Args:
            skill_file: Path to skill .md file

        Returns:
            List of resource file paths

        Example:
            >>> skill_file = Path("cache/skills/system/code-review.md")
            >>> resources = service._find_bundled_resources(skill_file)
            >>> print(resources)
            [Path('cache/skills/system/scripts/code-review/helper.sh')]
        """
        resources = []

        # Derive skill name from filename (without .md extension)
        skill_name = skill_file.stem

        # Get parent directory (where skills/ is located)
        parent_dir = skill_file.parent

        # Check for resource directories
        resource_dirs = ["scripts", "references", "assets"]

        for resource_dir_name in resource_dirs:
            resource_dir = parent_dir / resource_dir_name / skill_name

            if resource_dir.exists() and resource_dir.is_dir():
                # Find all files in resource directory (recursively)
                for resource_file in resource_dir.rglob("*"):
                    if resource_file.is_file():
                        resources.append(resource_file)

        if resources:
            self.logger.debug(
                f"Found {len(resources)} bundled resources for {skill_name}"
            )

        return resources

    def get_skill_metadata(self, skill_name: str) -> Optional[SkillMetadata]:
        """Get metadata for a specific skill.

        Args:
            skill_name: Name of the skill to retrieve

        Returns:
            SkillMetadata if found, None otherwise

        Example:
            >>> service = SkillDiscoveryService(Path("cache/skills/system"))
            >>> metadata = service.get_skill_metadata("code-review")
            >>> if metadata:
            ...     print(f"{metadata.name}: {metadata.description}")
        """
        for md_file in self.skills_dir.glob("*.md"):
            skill_dict = self._parse_skill_file(md_file)
            if skill_dict and skill_dict["name"] == skill_name:
                return SkillMetadata(
                    name=skill_dict["name"],
                    description=skill_dict["description"],
                    skill_version=skill_dict["skill_version"],
                    tags=skill_dict["tags"],
                    agent_types=skill_dict.get("agent_types"),
                    source_file=Path(skill_dict["source_file"]),
                    resources=[Path(r) for r in skill_dict.get("resources", [])],
                )
        return None

    def __repr__(self) -> str:
        """Return string representation."""
        return f"SkillDiscoveryService(skills_dir='{self.skills_dir}')"
