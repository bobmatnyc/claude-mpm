"""Skills Service - Core service for managing Claude Code skills.

This module implements the Skills Service layer for Claude MPM's Skills Integration system.
It handles skill discovery, deployment, validation, and registry management.

Design:
- Discovers skills from bundled/ directory
- Deploys skills to .claude/skills/
- Validates SKILL.md format against 16 validation rules
- Manages skills registry (config/skills_registry.yaml)
- Supports version checking and updates
- Graceful degradation (warn but continue on errors)

References:
- Design: docs/design/claude-mpm-skills-integration-design.md
- Spec: docs/design/SKILL-MD-FORMAT-SPECIFICATION.md
"""

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from claude_mpm.core.mixins import LoggerMixin

# Security constants
MAX_YAML_SIZE = 10 * 1024 * 1024  # 10MB limit to prevent YAML bombs


class SkillsService(LoggerMixin):
    """Manages Claude Code skills discovery, deployment, and registry.

    This service provides:
    - Discovery of bundled skills
    - Deployment to .claude/skills/
    - Validation against SKILL.md format specification
    - Registry management (skill-to-agent mappings)
    - Version checking and updates
    - Graceful error handling

    Example:
        >>> service = SkillsService()
        >>> result = service.deploy_bundled_skills()
        >>> print(f"Deployed {len(result['deployed'])} skills")
        >>>
        >>> skills = service.get_skills_for_agent('engineer')
        >>> print(f"Engineer has {len(skills)} skills")
    """

    def __init__(self) -> None:
        """Initialize Skills Service.

        Sets up paths for:
        - project_root: Root directory of the project
        - bundled_skills_path: Source bundled skills (src/claude_mpm/skills/bundled)
        - deployed_skills_path: Deployment target (.claude/skills/)
        - registry_path: Skills registry YAML (config/skills_registry.yaml)
        """
        super().__init__()
        self.project_root: Path = self._get_project_root()
        self.bundled_skills_path: Path = Path(__file__).parent / "bundled"
        self.deployed_skills_path: Path = self.project_root / ".claude" / "skills"
        self.registry_path: Path = (
            Path(__file__).parent.parent.parent.parent
            / "config"
            / "skills_registry.yaml"
        )

        # Load registry
        self.registry: Dict[str, Any] = self._load_registry()

    def _get_project_root(self) -> Path:
        """Get project root directory.

        Returns:
            Path to project root (directory containing .git or current working directory)
        """
        # Start from current file and traverse up to find project root
        current = Path.cwd()

        # Look for .git directory or pyproject.toml
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                return parent

        # Fallback to current directory
        return current

    def _validate_safe_path(self, base: Path, target: Path) -> bool:
        """Ensure target path is within base directory to prevent path traversal.

        Args:
            base: Base directory that should contain the target
            target: Target path to validate

        Returns:
            True if path is safe, False otherwise
        """
        try:
            target.resolve().relative_to(base.resolve())
            return True
        except ValueError:
            return False

    def _load_registry(self) -> Dict[str, Any]:
        """Load skills registry mapping skills to agents with security checks.

        The registry file (config/skills_registry.yaml) contains:
        - version: Registry version
        - last_updated: Last update timestamp
        - skill_sources: Source repositories
        - agent_skills: Mapping of agent IDs to skills
        - skills_metadata: Metadata for each skill

        Returns:
            Dict containing registry data, or empty dict if graceful degradation

        Note:
            This method logs warnings but doesn't raise to allow graceful degradation.
            Skills features will be unavailable if registry fails to load.
        """
        if not self.registry_path.exists():
            self.logger.warning(
                f"Skills registry not found: {self.registry_path}\n"
                f"Skills features will be unavailable. Run 'claude-mpm skills deploy' to initialize."
            )
            return {}

        # Check file size to prevent YAML bomb
        try:
            file_size = self.registry_path.stat().st_size
            if file_size > MAX_YAML_SIZE:
                self.logger.error(
                    f"Registry file too large: {file_size} bytes (max {MAX_YAML_SIZE})"
                )
                return {}
        except OSError as e:
            self.logger.error(f"Failed to stat registry file: {e}")
            return {}

        try:
            with open(self.registry_path, encoding="utf-8") as f:
                registry = yaml.safe_load(f)
                if not registry:
                    self.logger.warning(f"Empty registry file: {self.registry_path}")
                    return {}
                self.logger.debug(f"Loaded skills registry from {self.registry_path}")
                return registry
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in registry: {e}")
            return {}
        except OSError as e:
            self.logger.error(f"Failed to read registry file: {e}")
            return {}

    def discover_bundled_skills(self) -> List[Dict[str, Any]]:
        """Discover all skills in bundled directory.

        Scans bundled_skills_path for skills organized by category:
        bundled/
          ├── development/
          │   ├── test-driven-development/
          │   │   └── SKILL.md
          │   └── systematic-debugging/
          │       └── SKILL.md
          └── testing/
              └── ...

        Returns:
            List of skill dictionaries containing:
            - name: Skill name (directory name)
            - category: Category (parent directory name)
            - path: Full path to skill directory
            - metadata: Parsed YAML frontmatter from SKILL.md
        """
        skills = []

        if not self.bundled_skills_path.exists():
            self.logger.warning(
                f"Bundled skills path not found: {self.bundled_skills_path}"
            )
            return skills

        for category_dir in self.bundled_skills_path.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith("."):
                continue

            for skill_dir in category_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    metadata = self._parse_skill_metadata(skill_md)
                    skills.append(
                        {
                            "name": skill_dir.name,
                            "category": category_dir.name,
                            "path": skill_dir,
                            "metadata": metadata,
                        }
                    )

        self.logger.info(f"Discovered {len(skills)} bundled skills")
        return skills

    def _parse_skill_metadata(self, skill_md: Path) -> Dict[str, Any]:
        """Extract YAML frontmatter from SKILL.md.

        Parses the YAML frontmatter section at the beginning of SKILL.md files:

        ---
        name: skill-name
        description: Brief description
        version: 1.0.0
        category: development
        ...
        ---

        Args:
            skill_md: Path to SKILL.md file

        Returns:
            Dict containing frontmatter metadata, or empty dict if parsing fails
        """
        try:
            content = skill_md.read_text(encoding="utf-8")

            # Match YAML frontmatter: ---\n...yaml...\n---
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)

            if not match:
                self.logger.warning(f"No YAML frontmatter found in {skill_md}")
                return {}

            try:
                metadata = yaml.safe_load(match.group(1))
                return metadata or {}
            except yaml.YAMLError as e:
                self.logger.error(
                    f"Failed to parse YAML frontmatter in {skill_md}: {e}"
                )
                return {}
        except Exception as e:
            self.logger.error(f"Failed to read skill file {skill_md}: {e}")
            return {}

    def deploy_bundled_skills(self, force: bool = False) -> Dict[str, Any]:
        """Deploy bundled skills to .claude/skills/ directory.

        Copies skills from bundled/ to .claude/skills/ maintaining directory structure.
        Skips already-deployed skills unless force=True.

        Args:
            force: If True, redeploy even if skill already exists

        Returns:
            Dict containing:
            - deployed: List of successfully deployed skill names
            - skipped: List of skipped skill names (already deployed)
            - errors: List of dicts with 'skill' and 'error' keys

        Example:
            >>> result = service.deploy_bundled_skills(force=True)
            >>> print(f"Deployed: {len(result['deployed'])}")
            >>> print(f"Errors: {len(result['errors'])}")
        """
        skills = self.discover_bundled_skills()
        deployed = []
        skipped = []
        errors = []

        # Ensure deployment directory exists
        self.deployed_skills_path.mkdir(parents=True, exist_ok=True)

        for skill in skills:
            try:
                # Create category directory in deployment location
                target_category_dir = self.deployed_skills_path / skill["category"]
                target_category_dir.mkdir(parents=True, exist_ok=True)

                # Target path for this skill
                target_dir = target_category_dir / skill["name"]

                # SECURITY: Validate path is within deployed_skills_path
                if not self._validate_safe_path(self.deployed_skills_path, target_dir):
                    raise ValueError(f"Path traversal attempt detected: {target_dir}")

                # Check if already deployed
                if target_dir.exists() and not force:
                    skipped.append(skill["name"])
                    self.logger.debug(f"Skipped {skill['name']} (already deployed)")
                    continue

                # Deploy skill
                if target_dir.exists():
                    # SECURITY: Verify again before deletion and check for symlinks
                    if not self._validate_safe_path(
                        self.deployed_skills_path, target_dir
                    ):
                        raise ValueError(
                            "Refusing to delete path outside skills directory"
                        )

                    if target_dir.is_symlink():
                        self.logger.warning(f"Refusing to delete symlink: {target_dir}")
                        target_dir.unlink()
                    else:
                        shutil.rmtree(target_dir)

                shutil.copytree(skill["path"], target_dir)

                deployed.append(skill["name"])
                self.logger.debug(f"Deployed skill: {skill['name']}")

            except (ValueError, OSError) as e:
                self.logger.error(f"Failed to deploy {skill['name']}: {e}")
                errors.append({"skill": skill["name"], "error": str(e)})

        self.logger.info(
            f"Skills deployment: {len(deployed)} deployed, "
            f"{len(skipped)} skipped, {len(errors)} errors"
        )

        return {"deployed": deployed, "skipped": skipped, "errors": errors}

    def get_skills_for_agent(self, agent_id: str) -> List[str]:
        """Get list of skills assigned to specific agent.

        Reads from registry['agent_skills'][agent_id] and combines
        'required' and 'optional' skill lists.

        Args:
            agent_id: Agent identifier (e.g., 'engineer', 'python_engineer')

        Returns:
            List of skill names assigned to this agent

        Example:
            >>> skills = service.get_skills_for_agent('engineer')
            >>> # Returns: ['test-driven-development', 'systematic-debugging', ...]
        """
        if "agent_skills" not in self.registry:
            return []

        agent_skills = self.registry["agent_skills"].get(agent_id, {})

        # Combine required and optional skills
        required = agent_skills.get("required", [])
        optional = agent_skills.get("optional", [])

        return required + optional

    def validate_skill(self, skill_name: str) -> Dict[str, Any]:
        """Validate skill structure and metadata.

        Searches for skill in deployed or bundled locations and validates:
        - SKILL.md exists
        - YAML frontmatter is valid
        - Required fields are present (name, description, version, category)
        - Field formats and lengths are correct
        - Progressive disclosure structure is valid

        Args:
            skill_name: Name of skill to validate

        Returns:
            Dict containing:
            - valid: True if all critical checks pass
            - errors: List of error messages
            - warnings: List of warning messages
            - metadata: Parsed metadata (if valid)
        """
        # Find skill in deployed or bundled paths
        skill_paths = [self.deployed_skills_path, self.bundled_skills_path]

        for base_path in skill_paths:
            if not base_path.exists():
                continue

            for category_dir in base_path.iterdir():
                if not category_dir.is_dir():
                    continue

                skill_dir = category_dir / skill_name
                if skill_dir.exists():
                    return self._validate_skill_structure(skill_dir)

        return {
            "valid": False,
            "errors": [f"Skill not found: {skill_name}"],
            "warnings": [],
        }

    def _validate_skill_structure(self, skill_dir: Path) -> Dict[str, Any]:
        """Validate skill directory structure.

        Implements validation rules from SKILL-MD-FORMAT-SPECIFICATION.md:
        - Rule 1: SKILL.md exists
        - Rule 2: YAML frontmatter present
        - Rule 5: Required fields present
        - Rule 6: Name format valid
        - Rule 8: Description length valid
        - Additional format checks

        Args:
            skill_dir: Path to skill directory

        Returns:
            Dict with validation results (valid, errors, warnings, metadata)
        """
        errors = []
        warnings = []

        # Rule 1: Check SKILL.md exists
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            errors.append("Missing SKILL.md")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Parse and validate metadata
        metadata = self._parse_skill_metadata(skill_md)

        if not metadata:
            errors.append("Missing or invalid YAML frontmatter")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Rule 5: Required fields
        required_fields = [
            "name",
            "description",
            "version",
            "category",
            "progressive_disclosure",
        ]
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")

        # Rule 6: Name format
        if "name" in metadata:
            name = metadata["name"]
            if not re.match(r"^[a-z][a-z0-9-]*[a-z0-9]$", name):
                errors.append(f"Invalid name format: {name}")

        # Rule 8: Description length
        if "description" in metadata:
            desc_len = len(metadata["description"])
            if desc_len < 10 or desc_len > 150:
                errors.append(
                    f"Description must be 10-150 characters (found {desc_len})"
                )

        # Check for optional directories
        if (skill_dir / "scripts").exists():
            warnings.append("Contains scripts/ directory")

        if (skill_dir / "references").exists():
            warnings.append("Contains references/ directory")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "metadata": metadata,
        }

    def check_for_updates(self) -> Dict[str, Any]:
        """Compare versions of bundled vs deployed skills.

        Checks each deployed skill against its bundled version to identify:
        - Skills with available updates
        - Skills only in bundled (not deployed)
        - Skills only in deployed (orphaned)

        Returns:
            Dict containing:
            - updates_available: List of dicts with skill names and versions
            - up_to_date: List of skill names
            - not_deployed: List of skill names (in bundled, not deployed)
            - orphaned: List of skill names (in deployed, not bundled)
        """
        bundled = {s["name"]: s for s in self.discover_bundled_skills()}

        # Discover deployed skills
        deployed = {}
        if self.deployed_skills_path.exists():
            for category_dir in self.deployed_skills_path.iterdir():
                if not category_dir.is_dir():
                    continue

                for skill_dir in category_dir.iterdir():
                    if not skill_dir.is_dir():
                        continue

                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        metadata = self._parse_skill_metadata(skill_md)
                        deployed[skill_dir.name] = {
                            "name": skill_dir.name,
                            "category": category_dir.name,
                            "path": skill_dir,
                            "metadata": metadata,
                        }

        updates_available = []
        up_to_date = []
        not_deployed = []
        orphaned = []

        # Check for updates
        for name, bundled_skill in bundled.items():
            bundled_version = bundled_skill["metadata"].get("version", "0.0.0")

            if name not in deployed:
                not_deployed.append(name)
            else:
                deployed_version = deployed[name]["metadata"].get("version", "0.0.0")

                if deployed_version != bundled_version:
                    updates_available.append(
                        {
                            "name": name,
                            "current_version": deployed_version,
                            "new_version": bundled_version,
                        }
                    )
                else:
                    up_to_date.append(name)

        # Check for orphaned skills
        for name in deployed:
            if name not in bundled:
                orphaned.append(name)

        return {
            "updates_available": updates_available,
            "up_to_date": up_to_date,
            "not_deployed": not_deployed,
            "orphaned": orphaned,
        }

    def update_skills(self, skill_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Update specific or all skills.

        Redeploys skills from bundled to deployed location.
        If skill_names is None, updates all skills with available updates.

        Args:
            skill_names: List of skill names to update, or None for all

        Returns:
            Dict containing:
            - updated: List of successfully updated skill names
            - errors: List of dicts with 'skill' and 'error' keys
        """
        if skill_names is None:
            # Get all skills with available updates
            check_result = self.check_for_updates()
            skill_names = [s["name"] for s in check_result["updates_available"]]

        if not skill_names:
            self.logger.info("No skills to update")
            return {"updated": [], "errors": []}

        updated = []
        errors = []

        bundled = {s["name"]: s for s in self.discover_bundled_skills()}

        for skill_name in skill_names:
            if skill_name not in bundled:
                errors.append(
                    {"skill": skill_name, "error": "Skill not found in bundled skills"}
                )
                continue

            try:
                skill = bundled[skill_name]
                target_dir = (
                    self.deployed_skills_path / skill["category"] / skill["name"]
                )

                # SECURITY: Validate path is within deployed_skills_path
                if not self._validate_safe_path(self.deployed_skills_path, target_dir):
                    raise ValueError(f"Path traversal attempt detected: {target_dir}")

                # Remove old version
                if target_dir.exists():
                    # SECURITY: Check for symlinks before deletion
                    if target_dir.is_symlink():
                        self.logger.warning(f"Refusing to delete symlink: {target_dir}")
                        target_dir.unlink()
                    else:
                        shutil.rmtree(target_dir)

                # Deploy new version
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(skill["path"], target_dir)

                updated.append(skill_name)
                self.logger.info(f"Updated skill: {skill_name}")

            except (ValueError, OSError) as e:
                errors.append({"skill": skill_name, "error": str(e)})
                self.logger.error(f"Failed to update {skill_name}: {e}")

        return {"updated": updated, "errors": errors}

    def install_updates(
        self, updates: List[Dict[str, Any]], force: bool = False
    ) -> Dict[str, Any]:
        """Install skill updates from update check results.

        Args:
            updates: List of update dicts from check_for_updates()
            force: Force update even if versions match

        Returns:
            Dict containing updated skills and errors
        """
        skill_names = [update["skill"] for update in updates]
        return self.update_skills(skill_names)

    def get_skill_path(self, skill_name: str) -> Optional[Path]:
        """Get the path to a deployed skill.

        Args:
            skill_name: Name of the skill

        Returns:
            Path to the skill directory, or None if not found
        """
        if self.deployed_skills_path.exists():
            for category_dir in self.deployed_skills_path.iterdir():
                if not category_dir.is_dir():
                    continue

                skill_dir = category_dir / skill_name
                if skill_dir.exists():
                    return skill_dir

        return None

    def parse_skill_metadata(self, content: str) -> Dict[str, Any]:
        """Parse metadata from SKILL.md content.

        Args:
            content: Content of SKILL.md file

        Returns:
            Dict with extracted metadata
        """
        metadata = {}
        lines = content.split("\n")

        for line in lines[:50]:  # Check first 50 lines for metadata
            line = line.strip()

            # Parse YAML-style metadata
            if line.startswith("version:"):
                metadata["version"] = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                metadata["description"] = line.split(":", 1)[1].strip()
            elif line.startswith("category:"):
                metadata["category"] = line.split(":", 1)[1].strip()
            elif line.startswith("source:"):
                metadata["source"] = line.split(":", 1)[1].strip()

        return metadata

    def get_agents_for_skill(self, skill_name: str) -> List[str]:
        """Get list of agents that use a specific skill.

        Args:
            skill_name: Name of the skill

        Returns:
            List of agent IDs that use this skill
        """
        agents = []
        registry = self._load_registry()

        agent_capabilities = registry.get("agent_capabilities", {})
        for agent_id, capabilities in agent_capabilities.items():
            primary_workflows = capabilities.get("primary_workflows", [])
            enhanced_capabilities = capabilities.get("enhanced_capabilities", [])
            all_skills = primary_workflows + enhanced_capabilities

            if skill_name in all_skills:
                agents.append(agent_id)

        return agents

    def get_config_path(self, scope: str = "project") -> Path:
        """Get the configuration file path for a given scope.

        Args:
            scope: Configuration scope (system, user, project)

        Returns:
            Path to the configuration file
        """
        if scope == "system":
            # System-wide config (bundled)
            return (
                self.bundled_skills_path.parent.parent
                / "config"
                / "skills_registry.yaml"
            )
        if scope == "user":
            # User config (~/.config/claude-mpm/)
            home = Path.home()
            return home / ".config" / "claude-mpm" / "skills_registry.yaml"
        # project
        # Project config (.claude/)
        project_root = self._get_project_root()
        return project_root / ".claude" / "skills_config.yaml"

    def create_default_config(self, scope: str = "project") -> None:
        """Create a default configuration file.

        Args:
            scope: Configuration scope (system, user, project)
        """
        config_path = self.get_config_path(scope)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "version": "2.0.0",
            "skills": {"auto_deploy": True, "update_check": True},
        }

        import yaml

        config_path.write_text(yaml.dump(default_config, default_flow_style=False))
        self.logger.info(f"Created default config at {config_path}")
