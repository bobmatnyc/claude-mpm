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
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen

from claude_mpm.core.mixins import LoggerMixin


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

        # Ensure Claude skills directory exists
        self.CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    def deploy_skills(
        self,
        toolchain: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        force: bool = False,
    ) -> Dict:
        """Deploy skills from GitHub repository.

        This is the main entry point for skill deployment. It:
        1. Downloads skills from GitHub
        2. Parses manifest for metadata
        3. Filters by toolchain and categories
        4. Deploys to ~/.claude/skills/
        5. Warns about Claude Code restart

        Args:
            toolchain: Filter by toolchain (e.g., ['python', 'javascript'])
            categories: Filter by categories (e.g., ['testing', 'debugging'])
            force: Overwrite existing skills

        Returns:
            Dict containing:
            - deployed_count: Number of skills deployed
            - skipped_count: Number of skills skipped
            - errors: List of error messages
            - deployed_skills: List of deployed skill names
            - restart_required: True if Claude Code needs restart
            - restart_instructions: Message about restarting

        Example:
            >>> result = deployer.deploy_skills(toolchain=['python'])
            >>> if result['restart_required']:
            >>>     print(result['restart_instructions'])
        """
        self.logger.info(f"Deploying skills from {self.repo_url}")

        # Step 1: Download skills from GitHub
        try:
            skills_data = self._download_from_github()
        except Exception as e:
            self.logger.error(f"Failed to download skills: {e}")
            return {
                "deployed_count": 0,
                "skipped_count": 0,
                "errors": [f"Download failed: {e}"],
                "deployed_skills": [],
                "restart_required": False,
                "restart_instructions": "",
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
            }

        self.logger.info(f"Found {len(skills)} skills in repository")

        # Step 3: Filter skills
        filtered_skills = self._filter_skills(skills, toolchain, categories)

        self.logger.info(
            f"After filtering: {len(filtered_skills)} skills to deploy"
            f" (toolchain={toolchain}, categories={categories})"
        )

        # Step 4: Deploy skills
        deployed = []
        skipped = []
        errors = []

        for skill in filtered_skills:
            try:
                # Validate skill is a dictionary
                if not isinstance(skill, dict):
                    self.logger.error(f"Invalid skill format: {skill}")
                    errors.append(f"Invalid skill format: {skill}")
                    continue

                result = self._deploy_skill(skill, skills_data["temp_dir"], force=force)
                if result["deployed"]:
                    deployed.append(skill["name"])
                elif result["skipped"]:
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

        # Step 5: Cleanup
        self._cleanup(skills_data["temp_dir"])

        # Step 6: Check if Claude Code restart needed
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
            f"{len(skipped)} skipped, {len(errors)} errors"
        )

        return {
            "deployed_count": len(deployed),
            "skipped_count": len(skipped),
            "errors": errors,
            "deployed_skills": deployed,
            "skipped_skills": skipped,
            "restart_required": restart_required,
            "restart_instructions": restart_instructions,
        }

    def list_available_skills(self) -> Dict:
        """List all available skills from GitHub repository.

        Downloads manifest and returns skill metadata grouped by category
        and toolchain.

        Returns:
            Dict containing:
            - total_skills: Total number of available skills
            - by_category: Skills grouped by category
            - by_toolchain: Skills grouped by toolchain
            - skills: Full list of skill metadata

        Example:
            >>> result = deployer.list_available_skills()
            >>> print(f"Available: {result['total_skills']} skills")
            >>> for category, skills in result['by_category'].items():
            >>>     print(f"{category}: {len(skills)} skills")
        """
        try:
            skills_data = self._download_from_github()
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
            }

        except Exception as e:
            self.logger.error(f"Failed to list available skills: {e}")
            return {
                "total_skills": 0,
                "by_category": {},
                "by_toolchain": {},
                "skills": [],
                "error": str(e),
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

            except Exception as e:
                self.logger.error(f"Failed to remove {skill_name}: {e}")
                errors.append(f"{skill_name}: {e}")

        return {
            "removed_count": len(removed),
            "removed_skills": removed,
            "errors": errors,
        }

    def _download_from_github(self) -> Dict:
        """Download skills repository from GitHub.

        Downloads ZIP archive and extracts to temporary directory.

        Returns:
            Dict containing:
            - temp_dir: Path to temporary directory
            - manifest: Parsed manifest.json
            - skills_path: Path to skills directory in temp

        Raises:
            Exception: If download or extraction fails
        """
        # Convert GitHub URL to download URL
        if "github.com" in self.repo_url:
            # Extract owner/repo from URL
            parts = self.repo_url.rstrip("/").split("/")
            owner_repo = "/".join(parts[-2:])
            download_url = (
                f"https://github.com/{owner_repo}/archive/refs/heads/main.zip"
            )
        else:
            download_url = self.repo_url

        self.logger.info(f"Downloading from {download_url}")

        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix="claude_skills_"))

        try:
            # Download ZIP file
            zip_path = temp_dir / "skills.zip"

            with urlopen(download_url) as response:
                with open(zip_path, "wb") as f:
                    f.write(response.read())

            self.logger.debug(f"Downloaded to {zip_path}")

            # Extract ZIP
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find extracted directory (usually repo-name-main/)
            extracted_dirs = [
                d
                for d in temp_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]

            if not extracted_dirs:
                raise Exception("No directory found in downloaded ZIP")

            repo_dir = extracted_dirs[0]

            # Load manifest.json
            manifest_path = repo_dir / "manifest.json"
            if not manifest_path.exists():
                raise Exception("manifest.json not found in repository")

            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)

            return {"temp_dir": temp_dir, "manifest": manifest, "repo_dir": repo_dir}

        except Exception as e:
            # Cleanup on error
            self._cleanup(temp_dir)
            raise e

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

    def _deploy_skill(self, skill: Dict, temp_dir: Path, force: bool = False) -> Dict:
        """Deploy a single skill to ~/.claude/skills/.

        Args:
            skill: Skill metadata dict
            temp_dir: Temporary directory containing downloaded skills
            force: Overwrite if already exists

        Returns:
            Dict with deployed, skipped, error flags
        """
        skill_name = skill["name"]
        target_dir = self.CLAUDE_SKILLS_DIR / skill_name

        # Check if already deployed
        if target_dir.exists() and not force:
            self.logger.debug(f"Skipped {skill_name} (already deployed)")
            return {"deployed": False, "skipped": True, "error": None}

        # Find skill source in temp directory
        # Structure: temp_dir / repo-main / skills / category / skill-name
        repo_dir = next(
            d for d in temp_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        )

        skills_base = repo_dir / "skills"
        category = skill.get("category", "")

        # Try to find skill directory
        source_dir = None
        if category:
            source_dir = skills_base / category / skill_name
        if not source_dir or not source_dir.exists():
            # Fallback: search for skill in all categories
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
                "error": f"Skill source not found: {skill_name}",
            }

        # Security: Validate paths
        if not self._validate_safe_path(temp_dir, source_dir):
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
            shutil.copytree(source_dir, target_dir)

            self.logger.debug(f"Deployed {skill_name} to {target_dir}")
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

        Args:
            temp_dir: Temporary directory to remove
        """
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                self.logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp directory: {e}")
