"""PM Skills Deployer Service - Deploy bundled PM skills to projects.

WHY: PM agents require specific templates and skills for proper operation.
This service manages deployment of bundled PM skills from the claude-mpm
package to individual project .claude-mpm directories with version tracking.

DESIGN DECISIONS:
- Deploys from src/claude_mpm/skills/bundled/pm/ to .claude-mpm/skills/pm/
- Uses package-relative paths (works for both installed and dev mode)
- Supports two skill formats:
  1. Directory structure: pm-skill-name/SKILL.md (new format)
  2. Flat files: skill-name.md (legacy format in .claude-mpm/templates/)
- Per-project deployment (NOT global like Claude Code skills)
- Version tracking via .claude-mpm/pm_skills_registry.yaml
- Checksum validation for integrity verification
- Non-blocking verification (returns warnings, doesn't halt execution)
- Force flag to redeploy even if versions match

ARCHITECTURE:
1. Discovery: Find bundled PM skills in package (skills/bundled/pm/)
2. Deployment: Copy SKILL.md files to .claude-mpm/skills/pm/{name}.md
3. Registry: Track deployed versions and checksums
4. Verification: Check deployment status (non-blocking)
5. Updates: Compare bundled vs deployed versions

PATH RESOLUTION:
- Installed package: Uses __file__ to find skills/bundled/pm/
- Dev mode fallback: .claude-mpm/templates/ at project root
- Works correctly in both site-packages and development environments

References:
- Parent Service: src/claude_mpm/services/skills_deployer.py
- Skills Service: src/claude_mpm/skills/skills_service.py
"""

import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from claude_mpm.core.mixins import LoggerMixin

# Security constants
MAX_YAML_SIZE = 10 * 1024 * 1024  # 10MB limit to prevent YAML bombs


@dataclass
class PMSkillInfo:
    """Information about a deployed PM skill.

    Attributes:
        name: Skill name (directory/file name)
        version: Skill version from metadata
        deployed_at: ISO timestamp of deployment
        checksum: SHA256 checksum of skill content
        source_path: Original bundled skill path
        deployed_path: Deployed skill path
    """

    name: str
    version: str
    deployed_at: str
    checksum: str
    source_path: Path
    deployed_path: Path


@dataclass
class DeploymentResult:
    """Result of skill deployment operation.

    Attributes:
        success: Whether deployment succeeded
        deployed: List of successfully deployed skill names
        skipped: List of skipped skill names (already deployed)
        errors: List of dicts with 'skill' and 'error' keys
        message: Summary message
    """

    success: bool
    deployed: List[str]
    skipped: List[str]
    errors: List[Dict[str, str]]
    message: str


@dataclass
class VerificationResult:
    """Result of skill verification operation.

    Attributes:
        verified: Whether all skills are properly deployed
        warnings: List of warning messages
        missing_skills: List of missing skill names
        outdated_skills: List of outdated skill names
        message: Summary message
    """

    verified: bool
    warnings: List[str]
    missing_skills: List[str]
    outdated_skills: List[str]
    message: str


@dataclass
class UpdateInfo:
    """Information about available skill update.

    Attributes:
        skill_name: Name of skill with update available
        current_version: Currently deployed version
        new_version: Available bundled version
        checksum_changed: Whether content changed (even if version same)
    """

    skill_name: str
    current_version: str
    new_version: str
    checksum_changed: bool


class PMSkillsDeployerService(LoggerMixin):
    """Deploy and manage PM skills from bundled sources to projects.

    This service provides:
    - Discovery of bundled PM skills (templates)
    - Deployment to .claude-mpm/skills/pm/
    - Version tracking via pm_skills_registry.yaml
    - Checksum validation for integrity
    - Non-blocking verification (warnings only)
    - Update detection and deployment

    Example:
        >>> deployer = PMSkillsDeployerService()
        >>> result = deployer.deploy_pm_skills(Path("/project/root"))
        >>> print(f"Deployed {len(result.deployed)} skills")
        >>>
        >>> verify_result = deployer.verify_pm_skills(Path("/project/root"))
        >>> if not verify_result.verified:
        ...     print(f"Warnings: {verify_result.warnings}")
    """

    REGISTRY_VERSION = "1.0.0"
    REGISTRY_FILENAME = "pm_skills_registry.yaml"

    def __init__(self) -> None:
        """Initialize PM Skills Deployer Service.

        Sets up paths for:
        - bundled_pm_skills_path: Source bundled PM skills (skills/bundled/pm/)
        - Deployment paths are project-specific (passed to methods)
        """
        super().__init__()

        # Bundled PM skills are in the package's skills/bundled/pm/ directory
        # This works for both installed packages and development mode
        package_dir = Path(__file__).resolve().parent.parent  # Go up to claude_mpm
        self.bundled_pm_skills_path = package_dir / "skills" / "bundled" / "pm"

        if not self.bundled_pm_skills_path.exists():
            # Fallback: try .claude-mpm/templates/ at project root for dev mode
            self.project_root = self._find_project_root()
            alt_path = self.project_root / ".claude-mpm" / "templates"
            if alt_path.exists():
                self.bundled_pm_skills_path = alt_path
                self.logger.debug(f"Using dev templates path: {alt_path}")
            else:
                self.logger.warning(
                    f"PM skills templates path not found (non-critical, uses defaults)"
                )

    def _find_project_root(self) -> Path:
        """Find project root by traversing up from current file.

        Returns:
            Path to project root (directory containing .git or pyproject.toml)
        """
        current = Path(__file__).resolve()

        # Traverse up to find project root markers
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                return parent

        # Fallback to current working directory
        return Path.cwd()

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

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of file content.

        Args:
            file_path: Path to file to checksum

        Returns:
            Hex string of SHA256 checksum
        """
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read in 64KB chunks to handle large files
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except OSError as e:
            self.logger.error(f"Failed to compute checksum for {file_path}: {e}")
            return ""

    def _get_registry_path(self, project_dir: Path) -> Path:
        """Get path to PM skills registry file.

        Args:
            project_dir: Project root directory

        Returns:
            Path to pm_skills_registry.yaml
        """
        return project_dir / ".claude-mpm" / self.REGISTRY_FILENAME

    def _get_deployment_dir(self, project_dir: Path) -> Path:
        """Get deployment directory for PM skills.

        Args:
            project_dir: Project root directory

        Returns:
            Path to .claude-mpm/skills/pm/
        """
        return project_dir / ".claude-mpm" / "skills" / "pm"

    def _load_registry(self, project_dir: Path) -> Dict[str, Any]:
        """Load PM skills registry with security checks.

        Args:
            project_dir: Project root directory

        Returns:
            Dict containing registry data, or empty dict if not found/invalid
        """
        registry_path = self._get_registry_path(project_dir)

        if not registry_path.exists():
            self.logger.debug(f"PM skills registry not found: {registry_path}")
            return {}

        # Check file size to prevent YAML bomb
        try:
            file_size = registry_path.stat().st_size
            if file_size > MAX_YAML_SIZE:
                self.logger.error(
                    f"Registry file too large: {file_size} bytes (max {MAX_YAML_SIZE})"
                )
                return {}
        except OSError as e:
            self.logger.error(f"Failed to stat registry file: {e}")
            return {}

        try:
            with open(registry_path, encoding="utf-8") as f:
                registry = yaml.safe_load(f)
                if not registry:
                    self.logger.warning(f"Empty registry file: {registry_path}")
                    return {}
                self.logger.debug(f"Loaded PM skills registry from {registry_path}")
                return registry
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in registry: {e}")
            return {}
        except OSError as e:
            self.logger.error(f"Failed to read registry file: {e}")
            return {}

    def _save_registry(self, project_dir: Path, registry: Dict[str, Any]) -> bool:
        """Save PM skills registry to file.

        Args:
            project_dir: Project root directory
            registry: Registry data to save

        Returns:
            True if save succeeded, False otherwise
        """
        registry_path = self._get_registry_path(project_dir)

        try:
            # Ensure parent directory exists
            registry_path.parent.mkdir(parents=True, exist_ok=True)

            with open(registry_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    registry, f, default_flow_style=False, allow_unicode=True
                )

            self.logger.debug(f"Saved PM skills registry to {registry_path}")
            return True
        except (OSError, yaml.YAMLError) as e:
            self.logger.error(f"Failed to save registry: {e}")
            return False

    def _discover_bundled_pm_skills(self) -> List[Dict[str, Any]]:
        """Discover all PM skills in bundled templates directory.

        PM skills can be in two formats:
        1. Directory structure: pm-skill-name/SKILL.md (new format)
        2. Flat files: skill-name.md (legacy format for .claude-mpm/templates/)

        Returns:
            List of skill dictionaries containing:
            - name: Skill name (directory/filename without extension)
            - path: Full path to skill file (SKILL.md or .md file)
            - type: File type (always 'md')
        """
        skills = []

        if not self.bundled_pm_skills_path.exists():
            self.logger.warning(
                f"Bundled PM skills path not found: {self.bundled_pm_skills_path}"
            )
            return skills

        # Scan for skill directories containing SKILL.md (new format)
        for skill_dir in self.bundled_pm_skills_path.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue

            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skills.append(
                    {
                        "name": skill_dir.name,
                        "path": skill_file,
                        "type": "md",
                    }
                )

        # Fallback: Scan for .md files directly (legacy format)
        for skill_file in self.bundled_pm_skills_path.glob("*.md"):
            if skill_file.name.startswith("."):
                continue

            skills.append(
                {
                    "name": skill_file.stem,
                    "path": skill_file,
                    "type": "md",
                }
            )

        self.logger.info(f"Discovered {len(skills)} bundled PM skills")
        return skills

    def deploy_pm_skills(
        self,
        project_dir: Path,
        force: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> DeploymentResult:
        """Deploy bundled PM skills to project directory.

        Copies PM skills from bundled templates to .claude-mpm/skills/pm/
        and updates registry with version and checksum information.

        Args:
            project_dir: Project root directory
            force: If True, redeploy even if skill already exists
            progress_callback: Optional callback(skill_name, current, total) for progress

        Returns:
            DeploymentResult with deployment status and details

        Example:
            >>> result = deployer.deploy_pm_skills(Path("/project"), force=True)
            >>> print(f"Deployed: {len(result.deployed)}")
        """
        skills = self._discover_bundled_pm_skills()
        deployed = []
        skipped = []
        errors = []

        if not skills:
            return DeploymentResult(
                success=True,
                deployed=[],
                skipped=[],
                errors=[],
                message="No PM skills found to deploy",
            )

        # Ensure deployment directory exists
        deployment_dir = self._get_deployment_dir(project_dir)
        deployment_dir.mkdir(parents=True, exist_ok=True)

        # SECURITY: Validate deployment path
        if not self._validate_safe_path(project_dir, deployment_dir):
            return DeploymentResult(
                success=False,
                deployed=[],
                skipped=[],
                errors=[
                    {
                        "skill": "all",
                        "error": "Path traversal attempt detected in deployment directory",
                    }
                ],
                message="Security check failed",
            )

        # Load existing registry
        registry = self._load_registry(project_dir)
        deployed_skills = registry.get("skills", [])

        # Create lookup for existing deployments
        existing_deployments = {
            skill["name"]: skill for skill in deployed_skills
        }

        new_deployed_skills = []
        timestamp = datetime.utcnow().isoformat() + "Z"
        total_skills = len(skills)

        for idx, skill in enumerate(skills):
            try:
                skill_name = skill["name"]
                source_path = skill["path"]

                # Report progress if callback provided
                if progress_callback:
                    progress_callback(skill_name, idx + 1, total_skills)

                # Use skill name for target file (e.g., pm-delegation-patterns.md)
                target_path = deployment_dir / f"{skill_name}.md"

                # SECURITY: Validate target path
                if not self._validate_safe_path(deployment_dir, target_path):
                    raise ValueError(f"Path traversal attempt detected: {target_path}")

                # Compute checksum of source
                checksum = self._compute_checksum(source_path)

                # Check if already deployed
                if skill_name in existing_deployments and not force:
                    existing = existing_deployments[skill_name]
                    if existing.get("checksum") == checksum:
                        skipped.append(skill_name)
                        new_deployed_skills.append(existing)  # Keep existing entry
                        self.logger.debug(
                            f"Skipped {skill_name} (already deployed with same checksum)"
                        )
                        continue

                # Deploy skill
                shutil.copy2(source_path, target_path)

                # Add to deployed list
                deployed.append(skill_name)

                # Update registry entry
                skill_entry = {
                    "name": skill_name,
                    "version": "1.0.0",  # PM templates don't have versions yet
                    "deployed_at": timestamp,
                    "checksum": checksum,
                }
                new_deployed_skills.append(skill_entry)

                self.logger.debug(f"Deployed PM skill: {skill_name}")

            except (ValueError, OSError) as e:
                self.logger.error(f"Failed to deploy {skill['name']}: {e}")
                errors.append({"skill": skill["name"], "error": str(e)})

        # Update registry
        updated_registry = {
            "version": self.REGISTRY_VERSION,
            "deployed_at": timestamp,
            "skills": new_deployed_skills,
        }

        if not self._save_registry(project_dir, updated_registry):
            errors.append(
                {
                    "skill": "registry",
                    "error": "Failed to save registry after deployment",
                }
            )

        success = len(errors) == 0
        message = (
            f"Deployed {len(deployed)} skills, skipped {len(skipped)}, "
            f"{len(errors)} errors"
        )

        self.logger.info(message)

        return DeploymentResult(
            success=success,
            deployed=deployed,
            skipped=skipped,
            errors=errors,
            message=message,
        )

    def verify_pm_skills(self, project_dir: Path) -> VerificationResult:
        """Verify PM skills are properly deployed (non-blocking).

        Checks deployment status and returns warnings without halting execution.
        This allows graceful degradation if PM skills are missing.

        Args:
            project_dir: Project root directory

        Returns:
            VerificationResult with verification status and warnings

        Example:
            >>> result = deployer.verify_pm_skills(Path("/project"))
            >>> if not result.verified:
            ...     for warning in result.warnings:
            ...         print(f"WARNING: {warning}")
        """
        warnings = []
        missing_skills = []
        outdated_skills = []

        # Check if registry exists
        registry = self._load_registry(project_dir)
        if not registry:
            warnings.append("PM skills registry not found or invalid")
            missing_skills.append("all")
            return VerificationResult(
                verified=False,
                warnings=warnings,
                missing_skills=missing_skills,
                outdated_skills=outdated_skills,
                message="PM skills not deployed. Run 'claude-mpm init' to deploy.",
            )

        # Check each registered skill exists
        deployment_dir = self._get_deployment_dir(project_dir)
        deployed_skills = registry.get("skills", [])

        for skill in deployed_skills:
            skill_name = skill["name"]
            skill_file = deployment_dir / f"{skill_name}.md"

            if not skill_file.exists():
                warnings.append(f"Deployed skill file missing: {skill_name}")
                missing_skills.append(skill_name)
                continue

            # Verify checksum
            current_checksum = self._compute_checksum(skill_file)
            expected_checksum = skill.get("checksum", "")

            if current_checksum != expected_checksum:
                warnings.append(
                    f"Skill checksum mismatch: {skill_name} (file may be corrupted)"
                )
                outdated_skills.append(skill_name)

        # Check for available updates
        bundled_skills = {s["name"]: s for s in self._discover_bundled_pm_skills()}
        for skill_name, bundled_skill in bundled_skills.items():
            # Find corresponding deployed skill
            deployed_skill = next(
                (s for s in deployed_skills if s["name"] == skill_name), None
            )

            if not deployed_skill:
                warnings.append(f"New PM skill available: {skill_name}")
                missing_skills.append(skill_name)
                continue

            # Check if checksums differ
            bundled_checksum = self._compute_checksum(bundled_skill["path"])
            deployed_checksum = deployed_skill.get("checksum", "")

            if bundled_checksum != deployed_checksum:
                warnings.append(f"PM skill update available: {skill_name}")
                outdated_skills.append(skill_name)

        verified = len(warnings) == 0

        if verified:
            message = "All PM skills verified and up-to-date"
        else:
            message = f"{len(warnings)} verification warnings found"

        return VerificationResult(
            verified=verified,
            warnings=warnings,
            missing_skills=missing_skills,
            outdated_skills=outdated_skills,
            message=message,
        )

    def get_deployed_skills(self, project_dir: Path) -> List[PMSkillInfo]:
        """Get list of deployed PM skills with metadata.

        Args:
            project_dir: Project root directory

        Returns:
            List of PMSkillInfo objects for deployed skills

        Example:
            >>> skills = deployer.get_deployed_skills(Path("/project"))
            >>> for skill in skills:
            ...     print(f"{skill.name} v{skill.version} ({skill.deployed_at})")
        """
        registry = self._load_registry(project_dir)
        deployment_dir = self._get_deployment_dir(project_dir)

        skills = []
        for skill_data in registry.get("skills", []):
            skill_name = skill_data["name"]
            deployed_path = deployment_dir / f"{skill_name}.md"

            # Find source path (may not exist if bundled skills changed)
            source_path = self.bundled_pm_skills_path / f"{skill_name}.md"

            skills.append(
                PMSkillInfo(
                    name=skill_name,
                    version=skill_data.get("version", "1.0.0"),
                    deployed_at=skill_data.get("deployed_at", "unknown"),
                    checksum=skill_data.get("checksum", ""),
                    source_path=source_path,
                    deployed_path=deployed_path,
                )
            )

        return skills

    def check_updates_available(self, project_dir: Path) -> List[UpdateInfo]:
        """Check for available PM skill updates.

        Compares bundled skills against deployed skills to identify updates.

        Args:
            project_dir: Project root directory

        Returns:
            List of UpdateInfo objects for skills with updates available

        Example:
            >>> updates = deployer.check_updates_available(Path("/project"))
            >>> for update in updates:
            ...     print(f"{update.skill_name}: {update.current_version} -> {update.new_version}")
        """
        registry = self._load_registry(project_dir)
        deployed_skills = {
            skill["name"]: skill for skill in registry.get("skills", [])
        }

        bundled_skills = self._discover_bundled_pm_skills()

        updates = []
        for bundled_skill in bundled_skills:
            skill_name = bundled_skill["name"]

            # Compute bundled checksum
            bundled_checksum = self._compute_checksum(bundled_skill["path"])

            if skill_name not in deployed_skills:
                # New skill available
                updates.append(
                    UpdateInfo(
                        skill_name=skill_name,
                        current_version="not deployed",
                        new_version="1.0.0",
                        checksum_changed=True,
                    )
                )
                continue

            # Check if checksum differs
            deployed_skill = deployed_skills[skill_name]
            deployed_checksum = deployed_skill.get("checksum", "")

            if bundled_checksum != deployed_checksum:
                updates.append(
                    UpdateInfo(
                        skill_name=skill_name,
                        current_version=deployed_skill.get("version", "1.0.0"),
                        new_version="1.0.0",
                        checksum_changed=True,
                    )
                )

        return updates
