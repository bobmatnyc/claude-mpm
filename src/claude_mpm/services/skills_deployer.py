"""Skills Deployer Service - Deploy Claude Code skills from GitHub.

WHY: Claude Code loads skills at STARTUP ONLY from ~/.claude/skills/ directory.
This service manages downloading skills from external GitHub repositories and
deploying them to Claude Code's skills directory with automatic restart warnings.

DESIGN DECISIONS:
- Downloads from https://github.com/bobmatnyc/claude-mpm-skills by default
- Deploys to ~/.claude/skills/ (Claude Code's directory), NOT project directory
- Integrates with ToolchainAnalyzer for automatic language detection
- Handles Claude Code restart requirement (skills only load at startup)
- Provides filtering by toolchain and categories
- Graceful error handling with actionable messages

ARCHITECTURE:
1. GitHub Download: Fetch ZIP archive from repository
2. Manifest Parsing: Read skill metadata from manifest.json
3. Filtering: Apply toolchain and category filters
4. Deployment: Copy skills to ~/.claude/skills/
5. Restart Detection: Warn if Claude Code is running
6. Cleanup: Remove temporary files

References:
- Research: docs/research/skills-research.md
- GitHub Repo: https://github.com/bobmatnyc/claude-mpm-skills
"""

import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_mpm.core.mixins import LoggerMixin
from claude_mpm.services.skills_config import SkillsConfig


class SkillsDeployerService(LoggerMixin):
    """Deploy Claude Code skills from external GitHub repositories.

    This service:
    - Downloads skills from GitHub repositories
    - Deploys to ~/.claude/skills/ directory
    - Filters by toolchain (python, javascript, rust, etc.)
    - Filters by categories (testing, debugging, web, etc.)
    - Detects Claude Code process and warns about restart requirement
    - Provides deployment summaries and error handling

    Example:
        >>> deployer = SkillsDeployerService()
        >>> result = deployer.deploy_skills(toolchain=['python'], categories=['testing'])
        >>> print(f"Deployed {result['deployed_count']} skills")
        >>> print(f"Restart Claude Code: {result['restart_required']}")
    """

    DEFAULT_REPO_URL = "https://github.com/bobmatnyc/claude-mpm-skills"
    CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"

    def __init__(
        self,
        repo_url: Optional[str] = None,
        toolchain_analyzer: Optional[any] = None,
    ):
        """Initialize Skills Deployer Service.

        Args:
            repo_url: GitHub repository URL (default: bobmatnyc/claude-mpm-skills)
            toolchain_analyzer: Optional ToolchainAnalyzer for auto-detection
        """
        super().__init__()
        self.repo_url = repo_url or self.DEFAULT_REPO_URL
        self.toolchain_analyzer = toolchain_analyzer
        self.skills_config = SkillsConfig()

        # Ensure Claude skills directory exists
        self.CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    def deploy_skills(
        self,
        collection: Optional[str] = None,
        toolchain: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        force: bool = False,
        selective: bool = True,
        project_root: Optional[Path] = None,
    ) -> Dict:
        """Deploy skills from GitHub repository.

        This is the main entry point for skill deployment. It:
        1. Downloads skills from GitHub collection
        2. Parses manifest for metadata
        3. Filters by toolchain and categories
        4. (If selective=True) Filters to only agent-referenced skills
        5. Deploys to ~/.claude/skills/
        6. Warns about Claude Code restart

        Args:
            collection: Collection name to deploy from (default: uses default collection)
            toolchain: Filter by toolchain (e.g., ['python', 'javascript'])
            categories: Filter by categories (e.g., ['testing', 'debugging'])
            force: Overwrite existing skills
            selective: If True, only deploy skills referenced by agents (default)
            project_root: Project root directory (for finding agents, auto-detected if None)

        Returns:
            Dict containing:
            - deployed_count: Number of skills deployed
            - skipped_count: Number of skills skipped
            - errors: List of error messages
            - deployed_skills: List of deployed skill names
            - restart_required: True if Claude Code needs restart
            - restart_instructions: Message about restarting
            - collection: Collection name used for deployment
            - selective_mode: True if selective deployment was used
            - total_available: Total skills available before filtering

        Example:
            >>> result = deployer.deploy_skills(collection="obra-superpowers")
            >>> result = deployer.deploy_skills(toolchain=['python'])  # Uses default
            >>> # Deploy all skills (not just agent-referenced)
            >>> result = deployer.deploy_skills(selective=False)
            >>> if result['restart_required']:
            >>>     print(result['restart_instructions'])
        """
        # Determine which collection to use
        collection_name = collection or self.skills_config.get_default_collection()

        self.logger.info(f"Deploying skills from collection '{collection_name}'")

        # Step 1: Download skills from GitHub collection
        try:
            skills_data = self._download_from_github(collection_name)
        except Exception as e:
            self.logger.error(f"Failed to download skills: {e}")
            return {
                "deployed_count": 0,
                "skipped_count": 0,
                "errors": [f"Download failed: {e}"],
                "deployed_skills": [],
                "restart_required": False,
                "restart_instructions": "",
                "collection": collection_name,
            }

        # Step 2: Parse manifest and flatten skills
        manifest = skills_data.get("manifest", {})
        try:
            skills = self._flatten_manifest_skills(manifest)
        except ValueError as e:
            self.logger.error(f"Invalid manifest structure: {e}")
            return {
                "deployed_count": 0,
                "skipped_count": 0,
                "errors": [f"Invalid manifest: {e}"],
                "deployed_skills": [],
                "restart_required": False,
                "restart_instructions": "",
                "collection": collection_name,
            }

        self.logger.info(f"Found {len(skills)} skills in repository")

        # Step 3: Filter skills by toolchain and categories
        filtered_skills = self._filter_skills(skills, toolchain, categories)

        self.logger.info(
            f"After filtering: {len(filtered_skills)} skills to deploy"
            f" (toolchain={toolchain}, categories={categories})"
        )

        # Step 3.5: Apply selective filtering (only agent-referenced skills)
        total_available = len(filtered_skills)
        if selective:
            # Auto-detect project root if not provided
            if project_root is None:
                # Try to find project root by looking for .claude-mpm directory
                # Start from current directory and walk up
                current = Path.cwd()
                while current != current.parent:
                    if (current / ".claude-mpm").exists():
                        project_root = current
                        break
                    current = current.parent

            # Read skills from configuration.yaml instead of agent frontmatter
            if project_root:
                config_path = Path(project_root) / ".claude-mpm" / "configuration.yaml"
            else:
                # Fallback to current directory's configuration
                config_path = Path.cwd() / ".claude-mpm" / "configuration.yaml"

            from claude_mpm.services.skills.selective_skill_deployer import (
                get_required_skills_from_agents,
                get_skills_to_deploy,
                save_agent_skills_to_config,
            )

            # Check if agent_referenced is empty and needs to be populated
            required_skill_names, source = get_skills_to_deploy(config_path)

            if not required_skill_names and project_root:
                # agent_referenced is empty, scan deployed agents to populate it
                agents_dir = Path(project_root) / ".claude" / "agents"
                if agents_dir.exists():
                    self.logger.info(
                        "agent_referenced is empty in configuration.yaml, scanning deployed agents..."
                    )
                    agent_skills = get_required_skills_from_agents(agents_dir)
                    if agent_skills:
                        save_agent_skills_to_config(list(agent_skills), config_path)
                        self.logger.info(
                            f"Populated agent_referenced with {len(agent_skills)} skills from deployed agents"
                        )
                        # Re-read configuration after update
                        required_skill_names, source = get_skills_to_deploy(config_path)
                    else:
                        self.logger.warning(
                            "No skills found in deployed agents - configuration.yaml remains empty"
                        )
                else:
                    self.logger.warning(
                        f"Agents directory not found at {agents_dir} - cannot scan for skills"
                    )

            if required_skill_names:
                # Convert required_skill_names to a set for O(1) lookup
                required_set = set(required_skill_names)

                # Filter to only required skills
                # Match on: 'name', 'skill_id', or normalized 'source_path'
                # source_path example: "universal/web/api-design-patterns/SKILL.md"
                # normalized: "universal-web-api-design-patterns"
                def skill_matches_requirement(skill):
                    # Check basic name and skill_id
                    if skill.get("name") in required_set:
                        return True
                    if skill.get("skill_id") in required_set:
                        return True

                    # Check normalized source_path
                    source_path = skill.get("source_path", "")
                    if source_path:
                        # Remove /SKILL.md suffix and replace / with -
                        normalized = (
                            source_path.replace("/SKILL.md", "").replace("/", "-")
                        )
                        if normalized in required_set:
                            return True

                    return False

                filtered_skills = [s for s in filtered_skills if skill_matches_requirement(s)]

                self.logger.info(
                    f"Selective deployment: {len(filtered_skills)}/{total_available} skills "
                    f"(source: {source})"
                )
            else:
                self.logger.warning(
                    f"No skills found in configuration at {config_path}. "
                    f"Deploying all {total_available} skills."
                )
        else:
            self.logger.info(
                f"Selective mode disabled: deploying all {total_available} skills"
            )

        # Step 4: Deploy skills
        deployed = []
        skipped = []
        errors = []

        # Extract normalized skill names for cleanup (needed regardless of deployment outcome)
        # Must match the names used during deployment (normalized from source_path)
        filtered_skills_names = []
        for skill in filtered_skills:
            if isinstance(skill, dict) and "name" in skill:
                source_path = skill.get("source_path", "")
                if source_path:
                    # Normalize: "universal/web/api-design-patterns/SKILL.md" -> "universal-web-api-design-patterns"
                    normalized = source_path.replace("/SKILL.md", "").replace("/", "-")
                    filtered_skills_names.append(normalized)
                else:
                    # Fallback to skill name
                    filtered_skills_names.append(skill["name"])

        for skill in filtered_skills:
            try:
                # Validate skill is a dictionary
                if not isinstance(skill, dict):
                    self.logger.error(f"Invalid skill format: {skill}")
                    errors.append(f"Invalid skill format: {skill}")
                    continue

                result = self._deploy_skill(
                    skill, skills_data["temp_dir"], collection_name, force=force
                )
                if result["deployed"]:
                    # Use normalized name for reporting
                    source_path = skill.get("source_path", "")
                    if source_path:
                        normalized = source_path.replace("/SKILL.md", "").replace("/", "-")
                        deployed.append(normalized)
                    else:
                        deployed.append(skill["name"])
                elif result["skipped"]:
                    # Use normalized name for reporting
                    source_path = skill.get("source_path", "")
                    if source_path:
                        normalized = source_path.replace("/SKILL.md", "").replace("/", "-")
                        skipped.append(normalized)
                    else:
                        skipped.append(skill["name"])
                if result["error"]:
                    errors.append(result["error"])
            except Exception as e:
                skill_name = (
                    skill.get("name", "unknown")
                    if isinstance(skill, dict)
                    else "unknown"
                )
                self.logger.error(f"Failed to deploy {skill_name}: {e}")
                errors.append(f"{skill_name}: {e}")

        # Step 5: Cleanup orphaned skills (always run in selective mode)
        cleanup_result = {"removed_count": 0, "removed_skills": []}
        if selective:
            # Get the set of skills that should remain deployed
            # This is the union of what we just deployed and what was already there
            try:
                from claude_mpm.services.skills.selective_skill_deployer import (
                    cleanup_orphan_skills,
                )

                # Cleanup orphaned skills not referenced by agents
                # This runs even if nothing new was deployed to remove stale skills
                cleanup_result = cleanup_orphan_skills(
                    self.CLAUDE_SKILLS_DIR, set(filtered_skills_names)
                )

                if cleanup_result["removed_count"] > 0:
                    self.logger.info(
                        f"Removed {cleanup_result['removed_count']} orphaned skills: "
                        f"{', '.join(cleanup_result['removed_skills'])}"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to cleanup orphaned skills: {e}")

        # Step 6: Cleanup temp directory
        self._cleanup(skills_data["temp_dir"])

        # Step 7: Check if Claude Code restart needed
        restart_required = len(deployed) > 0
        restart_instructions = ""

        if restart_required:
            claude_running = self._is_claude_code_running()
            if claude_running:
                restart_instructions = (
                    "⚠️  Claude Code is currently running.\n"
                    "Skills are only loaded at STARTUP.\n"
                    "Please restart Claude Code for new skills to be available.\n\n"
                    "How to restart Claude Code:\n"
                    "1. Close all Claude Code windows\n"
                    "2. Quit Claude Code completely (Cmd+Q on Mac, Alt+F4 on Windows)\n"
                    "3. Re-launch Claude Code\n"
                )
            else:
                restart_instructions = (
                    "✓ Claude Code is not currently running.\n"
                    "Skills will be available when you launch Claude Code.\n"
                )

        self.logger.info(
            f"Deployment complete: {len(deployed)} deployed, "
            f"{len(skipped)} skipped, {len(errors)} errors, "
            f"{cleanup_result['removed_count']} orphaned skills removed"
        )

        return {
            "deployed_count": len(deployed),
            "skipped_count": len(skipped),
            "errors": errors,
            "deployed_skills": deployed,
            "skipped_skills": skipped,
            "restart_required": restart_required,
            "restart_instructions": restart_instructions,
            "collection": collection_name,
            "selective_mode": selective,
            "total_available": total_available,
            "cleanup": cleanup_result,
        }

    def list_available_skills(self, collection: Optional[str] = None) -> Dict:
        """List all available skills from GitHub repository.

        Downloads manifest and returns skill metadata grouped by category
        and toolchain.

        Args:
            collection: Collection name to list from (default: uses default collection)

        Returns:
            Dict containing:
            - total_skills: Total number of available skills
            - by_category: Skills grouped by category
            - by_toolchain: Skills grouped by toolchain
            - skills: Full list of skill metadata
            - collection: Collection name used

        Example:
            >>> result = deployer.list_available_skills(collection="obra-superpowers")
            >>> result = deployer.list_available_skills()  # Uses default
            >>> print(f"Available: {result['total_skills']} skills")
            >>> for category, skills in result['by_category'].items():
            >>>     print(f"{category}: {len(skills)} skills")
        """
        collection_name = collection or self.skills_config.get_default_collection()

        try:
            skills_data = self._download_from_github(collection_name)
            manifest = skills_data.get("manifest", {})

            # Flatten skills from manifest (supports both legacy and new structure)
            try:
                skills = self._flatten_manifest_skills(manifest)
            except ValueError as e:
                self.logger.error(f"Failed to parse manifest: {e}")
                return {
                    "total_skills": 0,
                    "by_category": {},
                    "by_toolchain": {},
                    "skills": [],
                    "error": str(e),
                }

            # Group by category
            by_category = {}
            for skill in skills:
                if not isinstance(skill, dict):
                    continue
                category = skill.get("category", "uncategorized")
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(skill)

            # Group by toolchain
            by_toolchain = {}
            for skill in skills:
                if not isinstance(skill, dict):
                    continue
                toolchains = skill.get("toolchain", [])
                if isinstance(toolchains, str):
                    toolchains = [toolchains]
                elif not isinstance(toolchains, list):
                    toolchains = []

                for toolchain in toolchains:
                    if toolchain not in by_toolchain:
                        by_toolchain[toolchain] = []
                    by_toolchain[toolchain].append(skill)

            # Cleanup
            self._cleanup(skills_data["temp_dir"])

            return {
                "total_skills": len(skills),
                "by_category": by_category,
                "by_toolchain": by_toolchain,
                "skills": skills,
                "collection": collection_name,
            }

        except Exception as e:
            self.logger.error(f"Failed to list available skills: {e}")
            return {
                "total_skills": 0,
                "by_category": {},
                "by_toolchain": {},
                "skills": [],
                "error": str(e),
                "collection": collection_name,
            }

    def check_deployed_skills(self) -> Dict:
        """Check which skills are currently deployed.

        Scans ~/.claude/skills/ directory for deployed skills.

        Returns:
            Dict containing:
            - deployed_count: Number of deployed skills
            - skills: List of deployed skill names with paths
            - claude_skills_dir: Path to Claude skills directory

        Example:
            >>> result = deployer.check_deployed_skills()
            >>> print(f"Currently deployed: {result['deployed_count']} skills")
        """
        deployed_skills = []

        if self.CLAUDE_SKILLS_DIR.exists():
            for skill_dir in self.CLAUDE_SKILLS_DIR.iterdir():
                if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                    # Check for SKILL.md
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists():
                        deployed_skills.append(
                            {"name": skill_dir.name, "path": str(skill_dir)}
                        )

        return {
            "deployed_count": len(deployed_skills),
            "skills": deployed_skills,
            "claude_skills_dir": str(self.CLAUDE_SKILLS_DIR),
        }

    def remove_skills(self, skill_names: Optional[List[str]] = None) -> Dict:
        """Remove deployed skills.

        Args:
            skill_names: List of skill names to remove, or None to remove all

        Returns:
            Dict containing:
            - removed_count: Number of skills removed
            - removed_skills: List of removed skill names
            - errors: List of error messages

        Example:
            >>> # Remove specific skills
            >>> result = deployer.remove_skills(['test-skill', 'debug-skill'])
            >>> # Remove all skills
            >>> result = deployer.remove_skills()
        """
        removed = []
        errors = []

        if not self.CLAUDE_SKILLS_DIR.exists():
            return {
                "removed_count": 0,
                "removed_skills": [],
                "errors": ["Claude skills directory does not exist"],
            }

        # Get all skills if no specific names provided
        if skill_names is None:
            skill_names = [
                d.name
                for d in self.CLAUDE_SKILLS_DIR.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]

        for skill_name in skill_names:
            skill_dir = self.CLAUDE_SKILLS_DIR / skill_name

            if not skill_dir.exists():
                errors.append(f"Skill not found: {skill_name}")
                continue

            try:
                # Security: Validate path is within CLAUDE_SKILLS_DIR
                if not self._validate_safe_path(self.CLAUDE_SKILLS_DIR, skill_dir):
                    raise ValueError(f"Path traversal attempt detected: {skill_dir}")

                # Remove skill directory
                if skill_dir.is_symlink():
                    self.logger.warning(f"Removing symlink: {skill_dir}")
                    skill_dir.unlink()
                else:
                    shutil.rmtree(skill_dir)

                removed.append(skill_name)
                self.logger.info(f"Removed skill: {skill_name}")

                # Untrack skill from deployment index
                from claude_mpm.services.skills.selective_skill_deployer import (
                    untrack_skill,
                )

                untrack_skill(self.CLAUDE_SKILLS_DIR, skill_name)

            except Exception as e:
                self.logger.error(f"Failed to remove {skill_name}: {e}")
                errors.append(f"{skill_name}: {e}")

        return {
            "removed_count": len(removed),
            "removed_skills": removed,
            "errors": errors,
        }

    def _download_from_github(self, collection_name: str) -> Dict:
        """Download skills repository from GitHub using git clone/pull.

        Logic:
        1. Get collection config from SkillsConfig
        2. Determine target directory: ~/.claude/skills/{collection_name}/
        3. Check if directory exists:
           - Exists + is git repo → git pull (update)
           - Exists + not git repo → error (manual cleanup needed)
           - Not exists → git clone (first install)
        4. Parse manifest.json from collection
        5. Update last_update timestamp in config
        6. Return skills data

        Args:
            collection_name: Name of collection to download

        Returns:
            Dict containing:
            - temp_dir: Path to collection directory (not temp, but kept for compatibility)
            - manifest: Parsed manifest.json
            - repo_dir: Path to repository directory

        Raises:
            ValueError: If collection not found or disabled
            Exception: If git operations fail
        """
        # Get collection configuration
        collection_config = self.skills_config.get_collection(collection_name)
        if not collection_config:
            raise ValueError(
                f"Collection '{collection_name}' not found. "
                f"Use 'claude-mpm skills collection add' to add it."
            )

        if not collection_config.get("enabled", True):
            raise ValueError(
                f"Collection '{collection_name}' is disabled. "
                f"Use 'claude-mpm skills collection enable {collection_name}' to enable it."
            )

        repo_url = collection_config["url"]
        target_dir = self.CLAUDE_SKILLS_DIR / collection_name

        self.logger.info(f"Processing collection '{collection_name}' from {repo_url}")

        # Check if directory exists and handle accordingly
        if target_dir.exists():
            git_dir = target_dir / ".git"

            if git_dir.exists():
                # Update existing: git pull
                self.logger.info(
                    f"Updating existing collection '{collection_name}' at {target_dir}"
                )
                try:
                    result = subprocess.run(
                        ["git", "pull"],
                        cwd=target_dir,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=60,
                    )
                    self.logger.debug(f"Git pull output: {result.stdout}")

                except subprocess.CalledProcessError as e:
                    raise Exception(
                        f"Failed to update collection '{collection_name}': {e.stderr}"
                    ) from e
                except subprocess.TimeoutExpired as e:
                    raise Exception(
                        f"Git pull timed out for collection '{collection_name}'"
                    ) from e
            else:
                # Directory exists but not a git repo - error
                raise ValueError(
                    f"Directory {target_dir} exists but is not a git repository. "
                    f"Please remove it manually and try again:\n"
                    f"  rm -rf {target_dir}"
                )
        else:
            # First install: git clone
            self.logger.info(
                f"Installing new collection '{collection_name}' to {target_dir}"
            )
            try:
                result = subprocess.run(
                    ["git", "clone", repo_url, str(target_dir)],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=120,
                )
                self.logger.debug(f"Git clone output: {result.stdout}")

            except subprocess.CalledProcessError as e:
                raise Exception(
                    f"Failed to clone collection '{collection_name}': {e.stderr}"
                ) from e
            except subprocess.TimeoutExpired as e:
                raise Exception(
                    f"Git clone timed out for collection '{collection_name}'"
                ) from e

        # Update last_update timestamp
        self.skills_config.update_collection_timestamp(collection_name)

        # Parse manifest.json
        manifest_path = target_dir / "manifest.json"
        if not manifest_path.exists():
            raise Exception(
                f"manifest.json not found in collection '{collection_name}' at {target_dir}"
            )

        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            raise Exception(
                f"Invalid manifest.json in collection '{collection_name}': {e}"
            ) from e

        self.logger.info(
            f"Successfully loaded collection '{collection_name}' from {target_dir}"
        )

        # Return data in same format as before for compatibility
        # Note: temp_dir is now the persistent collection directory
        return {"temp_dir": target_dir, "manifest": manifest, "repo_dir": target_dir}

    def _flatten_manifest_skills(self, manifest: Dict) -> List[Dict]:
        """Flatten skills from manifest, supporting both structures.

        Supports both legacy flat list and new nested dict structures:
        - Legacy: {"skills": [skill1, skill2, ...]}
        - New: {"skills": {"universal": [...], "toolchains": {...}}}

        Args:
            manifest: The manifest dictionary

        Returns:
            List of flattened skill dictionaries

        Raises:
            ValueError: If manifest structure is invalid

        Example:
            >>> # Legacy flat structure
            >>> manifest = {"skills": [{"name": "skill1"}, {"name": "skill2"}]}
            >>> skills = deployer._flatten_manifest_skills(manifest)
            >>> len(skills)  # 2

            >>> # New nested structure
            >>> manifest = {
            ...     "skills": {
            ...         "universal": [{"name": "skill1"}],
            ...         "toolchains": {"python": [{"name": "skill2"}]}
            ...     }
            ... }
            >>> skills = deployer._flatten_manifest_skills(manifest)
            >>> len(skills)  # 2
        """
        skills_data = manifest.get("skills", {})

        # Handle legacy flat list structure
        if isinstance(skills_data, list):
            self.logger.debug(
                f"Using legacy flat manifest structure ({len(skills_data)} skills)"
            )
            return skills_data

        # Handle new nested dict structure
        if isinstance(skills_data, dict):
            flat_skills = []

            # Add universal skills
            universal_skills = skills_data.get("universal", [])
            if isinstance(universal_skills, list):
                flat_skills.extend(universal_skills)
                self.logger.debug(f"Added {len(universal_skills)} universal skills")

            # Add toolchain-specific skills
            toolchains = skills_data.get("toolchains", {})
            if isinstance(toolchains, dict):
                for toolchain_name, toolchain_skills in toolchains.items():
                    if isinstance(toolchain_skills, list):
                        flat_skills.extend(toolchain_skills)
                        self.logger.debug(
                            f"Added {len(toolchain_skills)} {toolchain_name} skills"
                        )

            self.logger.info(
                f"Flattened {len(flat_skills)} total skills from nested structure"
            )
            return flat_skills

        # Invalid structure
        raise ValueError(
            f"Skills manifest must be a list or dict, got {type(skills_data).__name__}"
        )

    def _filter_skills(
        self,
        skills: List[Dict],
        toolchain: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Filter skills by toolchain and categories.

        Args:
            skills: List of skill metadata dicts
            toolchain: List of toolchains to include (None = all)
            categories: List of categories to include (None = all)

        Returns:
            Filtered list of skills
        """
        # Ensure skills is a list and contains dicts
        if not isinstance(skills, list):
            return []

        # Filter out non-dict items
        filtered = [s for s in skills if isinstance(s, dict)]

        # Filter by toolchain
        if toolchain:
            toolchain_lower = [t.lower() for t in toolchain]
            filtered = [
                s
                for s in filtered
                if isinstance(s, dict)
                and any(
                    t.lower() in toolchain_lower
                    for t in (
                        s.get("toolchain", [])
                        if isinstance(s.get("toolchain"), list)
                        else ([s.get("toolchain")] if s.get("toolchain") else [])
                    )
                )
            ]

        # Filter by categories
        if categories:
            categories_lower = [c.lower() for c in categories]
            filtered = [
                s
                for s in filtered
                if isinstance(s, dict)
                and s.get("category", "").lower() in categories_lower
            ]

        return filtered

    def _deploy_skill(
        self,
        skill: Dict,
        collection_dir: Path,
        collection_name: str,
        force: bool = False,
    ) -> Dict:
        """Deploy a single skill to ~/.claude/skills/ and track deployment.

        NOTE: With multi-collection support, skills are now stored in collection
        subdirectories. This method creates symlinks or copies to maintain the
        flat structure that Claude Code expects in ~/.claude/skills/.

        Additionally tracks deployed skills in .mpm-deployed-skills.json index
        for orphan cleanup functionality.

        Args:
            skill: Skill metadata dict
            collection_dir: Collection directory containing skills
            collection_name: Name of collection (for tracking)
            force: Overwrite if already exists

        Returns:
            Dict with deployed, skipped, error flags
        """
        skill_name = skill["name"]

        # Use normalized source_path for both target directory and deployment tracking
        # This ensures consistency with configuration.yaml skill names
        source_path = skill.get("source_path", "")
        if source_path:
            # Normalize: "universal/web/api-design-patterns/SKILL.md" -> "universal-web-api-design-patterns"
            normalized_name = source_path.replace("/SKILL.md", "").replace("/", "-")
            target_dir = self.CLAUDE_SKILLS_DIR / normalized_name
        else:
            # Fallback to skill name if no source_path
            target_dir = self.CLAUDE_SKILLS_DIR / skill_name

        # Check if already deployed
        if target_dir.exists() and not force:
            self.logger.debug(f"Skipped {skill_name} (already deployed)")
            return {"deployed": False, "skipped": True, "error": None}

        # Find skill source using source_path from manifest
        source_dir = None

        if source_path:
            # Direct lookup using source_path (most reliable)
            # Example: "universal/web/api-design-patterns/SKILL.md" -> "universal/web/api-design-patterns"
            skill_dir_path = source_path.replace("/SKILL.md", "")
            potential_source = collection_dir / skill_dir_path
            if potential_source.exists():
                source_dir = potential_source
            else:
                self.logger.debug(
                    f"Source path {skill_dir_path} not found, trying fallback search"
                )

        # Fallback: search using old logic (for backward compatibility)
        if not source_dir:
            skills_base = collection_dir / "skills"
            category = skill.get("category", "")

            # Try multiple possible locations
            search_paths = []

            # Try category-based path
            if category and skills_base.exists():
                search_paths.append(skills_base / category / skill_name)

            # Try universal/toolchains structure
            if (collection_dir / "universal").exists():
                search_paths.append(collection_dir / "universal" / skill_name)

            if (collection_dir / "toolchains").exists():
                toolchain_dir = collection_dir / "toolchains"
                for tc in toolchain_dir.iterdir():
                    if tc.is_dir():
                        search_paths.append(tc / skill_name)

            # Search in all possible locations
            for path in search_paths:
                if path.exists():
                    source_dir = path
                    break

            # Final fallback: search recursively for skill in skills directory
            if not source_dir and skills_base.exists():
                for cat_dir in skills_base.iterdir():
                    if not cat_dir.is_dir():
                        continue
                    potential = cat_dir / skill_name
                    if potential.exists():
                        source_dir = potential
                        break

        if not source_dir or not source_dir.exists():
            return {
                "deployed": False,
                "skipped": False,
                "error": f"Skill source not found: {skill_name} (searched in {collection_dir})",
            }

        # Security: Validate paths
        if not self._validate_safe_path(collection_dir, source_dir):
            return {
                "deployed": False,
                "skipped": False,
                "error": f"Invalid source path: {source_dir}",
            }

        if not self._validate_safe_path(self.CLAUDE_SKILLS_DIR, target_dir):
            return {
                "deployed": False,
                "skipped": False,
                "error": f"Invalid target path: {target_dir}",
            }

        try:
            # Remove existing if force
            if target_dir.exists():
                if target_dir.is_symlink():
                    target_dir.unlink()
                else:
                    shutil.rmtree(target_dir)

            # Copy skill to Claude skills directory
            # NOTE: We use copy instead of symlink to maintain Claude Code compatibility
            shutil.copytree(source_dir, target_dir)

            # Track deployment in index using normalized name
            from claude_mpm.services.skills.selective_skill_deployer import (
                track_deployed_skill,
            )

            # Use normalized name for tracking (matches configuration.yaml format)
            track_name = normalized_name if source_path else skill_name
            track_deployed_skill(self.CLAUDE_SKILLS_DIR, track_name, collection_name)

            self.logger.debug(
                f"Deployed {skill_name} from {source_dir} to {target_dir}"
            )
            return {"deployed": True, "skipped": False, "error": None}

        except Exception as e:
            return {"deployed": False, "skipped": False, "error": str(e)}

    def _validate_safe_path(self, base: Path, target: Path) -> bool:
        """Ensure target path is within base directory (security).

        Args:
            base: Base directory
            target: Target path to validate

        Returns:
            True if path is safe, False otherwise
        """
        try:
            target.resolve().relative_to(base.resolve())
            return True
        except ValueError:
            return False

    def _is_claude_code_running(self) -> bool:
        """Check if Claude Code process is running.

        Returns:
            True if Claude Code is running, False otherwise
        """
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist"], check=False, capture_output=True, text=True, timeout=5
                )
                return "claude" in result.stdout.lower()
            # macOS and Linux
            result = subprocess.run(
                ["ps", "aux"], check=False, capture_output=True, text=True, timeout=5
            )
            # Look for "Claude Code" or "claude-code" process
            return (
                "claude code" in result.stdout.lower()
                or "claude-code" in result.stdout.lower()
            )

        except Exception as e:
            self.logger.debug(f"Failed to check Claude Code process: {e}")
            return False

    def _cleanup(self, temp_dir: Path) -> None:
        """Cleanup temporary directory.

        NOTE: With multi-collection support, temp_dir is now the persistent
        collection directory, so we DON'T delete it. This method is kept for
        backward compatibility but is now a no-op.

        Args:
            temp_dir: Collection directory (not deleted)
        """
        # NO-OP: Collection directories are persistent, not temporary
        # Skills are deployed from collection directories to Claude skills dir
        self.logger.debug(f"Collection directory preserved at {temp_dir} (not deleted)")

    # === Collection Management Methods ===

    def list_collections(self) -> Dict[str, Any]:
        """List all configured skill collections.

        Returns:
            Dict containing:
            - collections: Dict of collection configurations
            - default_collection: Name of default collection
            - enabled_count: Number of enabled collections

        Example:
            >>> result = deployer.list_collections()
            >>> for name, config in result['collections'].items():
            >>>     print(f"{name}: {config['url']} (priority: {config['priority']})")
        """
        collections = self.skills_config.get_collections()
        default = self.skills_config.get_default_collection()
        enabled = self.skills_config.get_enabled_collections()

        return {
            "collections": collections,
            "default_collection": default,
            "enabled_count": len(enabled),
            "total_count": len(collections),
        }

    def add_collection(self, name: str, url: str, priority: int = 99) -> Dict[str, Any]:
        """Add a new skill collection.

        Args:
            name: Collection name (must be unique)
            url: GitHub repository URL
            priority: Collection priority (lower = higher priority, default: 99)

        Returns:
            Dict with operation result

        Example:
            >>> deployer.add_collection("obra-superpowers", "https://github.com/obra/superpowers")
        """
        return self.skills_config.add_collection(name, url, priority)

    def remove_collection(self, name: str) -> Dict[str, Any]:
        """Remove a skill collection.

        Args:
            name: Collection name to remove

        Returns:
            Dict with operation result

        Example:
            >>> deployer.remove_collection("obra-superpowers")
        """
        result = self.skills_config.remove_collection(name)

        # Also remove the collection directory
        collection_dir = self.CLAUDE_SKILLS_DIR / name
        if collection_dir.exists():
            try:
                shutil.rmtree(collection_dir)
                self.logger.info(f"Removed collection directory: {collection_dir}")
                result["directory_removed"] = True
            except Exception as e:
                self.logger.warning(f"Failed to remove directory {collection_dir}: {e}")
                result["directory_removed"] = False
                result["directory_error"] = str(e)

        return result

    def enable_collection(self, name: str) -> Dict[str, Any]:
        """Enable a disabled collection.

        Args:
            name: Collection name

        Returns:
            Dict with operation result

        Example:
            >>> deployer.enable_collection("obra-superpowers")
        """
        return self.skills_config.enable_collection(name)

    def disable_collection(self, name: str) -> Dict[str, Any]:
        """Disable a collection without removing it.

        Args:
            name: Collection name

        Returns:
            Dict with operation result

        Example:
            >>> deployer.disable_collection("obra-superpowers")
        """
        return self.skills_config.disable_collection(name)

    def set_default_collection(self, name: str) -> Dict[str, Any]:
        """Set the default collection for deployments.

        Args:
            name: Collection name to set as default

        Returns:
            Dict with operation result

        Example:
            >>> deployer.set_default_collection("obra-superpowers")
        """
        return self.skills_config.set_default_collection(name)
