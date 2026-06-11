"""PM Skills Deployer Service - Deploy bundled PM skills to user level.

WHY: PM agents require specific framework management skills for proper operation.
This service manages deployment of bundled PM skills from the claude-mpm
package to the Claude Code user-level skills directory with version tracking.

DESIGN DECISIONS:
- Deploys from src/claude_mpm/skills/bundled/pm/ to ~/.claude/skills/
- Skills named mpm-* (framework management skills) and universal-* core skills
- Direct deployment (no intermediate .claude-mpm/skills/pm/ step)
- Uses package-relative paths (works for both installed and dev mode)
- Supports directory structure: mpm-skill-name/SKILL.md
- User-level deployment to ~/.claude/skills/ (shared across all projects)
- Only skills in USER_LEVEL_SKILLS frozenset are deployed to user level
- Version tracking via .claude-mpm/pm_skills_registry.yaml (in project root)
- Checksum validation for integrity verification
- Conflict resolution: mpm-* skills from src WIN (overwrite existing)
- Non-mpm-* skills in ~/.claude/skills/ are untouched (user/git managed)
- Non-blocking verification (returns warnings, doesn't halt execution)
- Force flag to redeploy even if versions match

ARCHITECTURE:
1. Discovery: Find bundled PM skills in package (skills/bundled/pm/)
2. Deployment: Copy SKILL.md files to .claude/skills/{name}/SKILL.md
3. Conflict Check: Overwrite mpm-* skills, preserve non-mpm-* skills
4. Registry: Track deployed versions and checksums
5. Verification: Check deployment status (non-blocking)
6. Updates: Compare bundled vs deployed versions

PATH RESOLUTION:
- Installed package: Uses __file__ to find skills/bundled/pm/
- Dev mode fallback: .claude-mpm/templates/ at project root
- Works correctly in both site-packages and development environments

References:
- Parent Service: src/claude_mpm/services/skills_deployer.py
- Skills Service: src/claude_mpm/skills/skills_service.py
"""

import hashlib
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from claude_mpm.core.mixins import LoggerMixin

# Security constants
MAX_YAML_SIZE = 10 * 1024 * 1024  # 10MB limit to prevent YAML bombs

# Default version assumed for a deployed/bundled skill whose SKILL.md does not
# declare a ``version:`` in its YAML frontmatter. Treated as the lowest version.
DEFAULT_SKILL_VERSION = "0.0.0"

# Matches a ``version:`` line inside YAML frontmatter, with or without quotes.
# Example matches: ``version: "1.2.0"``, ``version: 1.0.0``, ``version: '2.0'``
_FRONTMATTER_VERSION_RE = re.compile(
    r"^version:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", re.MULTILINE
)


def _parse_version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted version string into a comparable integer tuple.

    WHAT: Converts ``"1.2.0"`` -> ``(1, 2, 0)`` so versions sort numerically
    rather than lexically (``"10.0.0" > "9.0.0"``).
    WHY: Bug #735 — checksum-based redeploy silently reverted user-hardened
    skills. Version comparison must be numeric to decide whether the bundled
    skill is strictly newer than the deployed one.

    Non-numeric or malformed segments degrade gracefully to ``0`` so a junk
    version never raises and is simply treated as the lowest possible version.

    Args:
        version: Dotted version string (e.g. ``"1.2.0"``).

    Returns:
        Tuple of integers suitable for direct comparison.
    """
    parts: list[int] = []
    for segment in str(version).strip().split("."):
        # Keep only the leading numeric run of each segment (e.g. "0rc1" -> 0).
        match = re.match(r"\d+", segment)
        parts.append(int(match.group()) if match else 0)
    return tuple(parts) or (0,)


def _read_skill_version(file_path: Path) -> str:
    """Read the ``version:`` from a SKILL.md YAML frontmatter block.

    WHAT: Extracts the declared version string from the frontmatter of a
    SKILL.md file, returning ``DEFAULT_SKILL_VERSION`` when absent/unreadable.
    WHY: Bug #735 — version-aware deployment needs the bundled and deployed
    versions to decide whether an overwrite is an upgrade or a clobber.

    Args:
        file_path: Path to a SKILL.md file.

    Returns:
        The version string declared in frontmatter, or
        ``DEFAULT_SKILL_VERSION`` if none is found or the file cannot be read.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            # Versions live in the frontmatter at the very top; reading the
            # first ~4KB is sufficient and avoids loading large files fully.
            head = f.read(4096)
    except OSError:
        return DEFAULT_SKILL_VERSION

    match = _FRONTMATTER_VERSION_RE.search(head)
    if match:
        return match.group(1).strip()
    return DEFAULT_SKILL_VERSION


# Tier 1: Required PM skills that MUST be deployed for PM agent to function properly
# These are core framework management skills for basic PM operation
REQUIRED_PM_SKILLS = [
    # Core command-based skills (new consolidated CLI)
    "mpm",
    "mpm-init",
    "mpm-status",
    "mpm-help",
    "mpm-doctor",
    # Legacy framework management skills
    "mpm-git-file-tracking",
    "mpm-pr-workflow",
    "mpm-ticketing-integration",
    "mpm-delegation-patterns",
    "mpm-verification-protocols",
    "mpm-bug-reporting",
    "mpm-teaching-mode",
    "mpm-agent-update-workflow",
    "mpm-circuit-breaker-enforcement",
    "mpm-tool-usage-guide",
    "mpm-session-management",
    "mpm-session-pause",
    "mpm-session-resume",
]

# Tier 2: Recommended skills (deployed with standard install)
# These provide enhanced functionality for common workflows
RECOMMENDED_PM_SKILLS = [
    "mpm-config",
    "mpm-ticket-view",
    "mpm-postmortem",
]

# Tier 3: Optional skills (deployed with full install)
# These provide additional features for advanced use cases
OPTIONAL_PM_SKILLS = [
    "mpm-monitor",
    "mpm-version",
    "mpm-organize",
]


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
    deployed: list[str]
    skipped: list[str]
    errors: list[dict[str, str]]
    message: str


@dataclass
class VerificationResult:
    """Result of skill verification operation.

    Attributes:
        verified: Whether all skills are properly deployed
        warnings: List of warning messages
        missing_skills: List of missing skill names
        corrupted_skills: List of corrupted skill names (checksum mismatch)
        outdated_skills: List of outdated skill names
        message: Summary message
        skill_count: Total number of deployed skills
    """

    verified: bool
    warnings: list[str]
    missing_skills: list[str]
    corrupted_skills: list[str]
    outdated_skills: list[str]
    message: str
    skill_count: int = 0


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
    - Discovery of bundled PM skills (mpm-* framework management skills)
    - Deployment to .claude/skills/ (Claude Code location)
    - Conflict resolution (mpm-* skills from src WIN)
    - Version tracking via pm_skills_registry.yaml
    - Checksum validation for integrity
    - Non-blocking verification (warnings only)
    - Update detection and deployment

    Example:
        >>> deployer = PMSkillsDeployerService()
        >>> result = deployer.deploy_pm_skills(Path("/project/root"))
        >>> print(f"Deployed {len(result.deployed)} skills to .claude/skills/")
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
                    "PM skills templates path not found (non-critical, uses defaults)"
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
        """Get deployment directory for PM skills (user level).

        PM skills in USER_LEVEL_SKILLS are deployed to the user-level Claude
        skills directory (~/.claude/skills/) so they are shared across all
        projects. The project_dir argument is accepted for API compatibility
        but is not used to compute the deployment path.

        Args:
            project_dir: Project root directory (unused; kept for API compat)

        Returns:
            Path to ~/.claude/skills/
        """
        return Path.home() / ".claude" / "skills"

    def _load_registry(self, project_dir: Path) -> dict[str, Any]:
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

    def _save_registry(self, project_dir: Path, registry: dict[str, Any]) -> bool:
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

    def _discover_bundled_pm_skills(self) -> list[dict[str, Any]]:
        """Discover all PM skills in bundled templates directory.

        PM skills follow mpm-skill-name/SKILL.md structure.

        Returns:
            List of skill dictionaries containing:
            - name: Skill name (directory name, e.g., mpm-git-file-tracking)
            - path: Full path to skill file (SKILL.md)
            - type: File type (always 'md')
        """
        skills = []

        if not self.bundled_pm_skills_path.exists():
            self.logger.warning(
                f"Bundled PM skills path not found: {self.bundled_pm_skills_path}"
            )
            return skills

        # Scan for skill directories containing SKILL.md
        for skill_dir in self.bundled_pm_skills_path.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue

            # Only process mpm* skills (framework management)
            # Note: Includes both 'mpm' (core skill) and 'mpm-*' (other PM skills)
            if not skill_dir.name.startswith("mpm"):
                self.logger.debug(f"Skipping non-mpm skill: {skill_dir.name}")
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

        self.logger.info(f"Discovered {len(skills)} bundled PM skills")
        return skills

    def _get_skills_for_tier(self, tier: str) -> list[str]:
        """Get list of skills to deploy based on tier.

        Args:
            tier: Deployment tier - "minimal", "standard", or "full"

        Returns:
            List of skill names to deploy

        Raises:
            ValueError: If tier is invalid
        """
        if tier == "minimal":
            return REQUIRED_PM_SKILLS
        if tier == "standard":
            return REQUIRED_PM_SKILLS + RECOMMENDED_PM_SKILLS
        if tier == "full":
            return REQUIRED_PM_SKILLS + RECOMMENDED_PM_SKILLS + OPTIONAL_PM_SKILLS
        raise ValueError(
            f"Invalid tier '{tier}'. Must be 'minimal', 'standard', or 'full'"
        )

    def deploy_pm_skills(
        self,
        project_dir: Path,
        force: bool = False,
        tier: str = "standard",
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> DeploymentResult:
        """Deploy bundled PM skills to project directory with tier-based selection.

        Copies PM skills from bundled templates to .claude/skills/{name}/SKILL.md
        and updates registry with version and checksum information.

        Deployment Tiers:
        - "minimal": Only REQUIRED_PM_SKILLS (Tier 1 - core functionality)
        - "standard": REQUIRED_PM_SKILLS + RECOMMENDED_PM_SKILLS (Tier 1+2 - common workflows)
        - "full": All skills (Tier 1+2+3 - advanced features)

        Conflict Resolution:
        - mpm-* skills from src WIN (overwrite existing)
        - Non-mpm-* skills in .claude/skills/ are untouched

        Args:
            project_dir: Project root directory
            force: If True, redeploy even if skill already exists
            tier: Deployment tier - "minimal", "standard" (default), or "full"
            progress_callback: Optional callback(skill_name, current, total) for progress

        Returns:
            DeploymentResult with deployment status and details

        Example:
            >>> # Standard deployment (Tier 1 + Tier 2)
            >>> result = deployer.deploy_pm_skills(Path("/project"))
            >>> print(f"Deployed: {len(result.deployed)} to .claude/skills/")
            >>>
            >>> # Minimal deployment (Tier 1 only)
            >>> result = deployer.deploy_pm_skills(Path("/project"), tier="minimal")
            >>>
            >>> # Full deployment (all tiers)
            >>> result = deployer.deploy_pm_skills(Path("/project"), tier="full")
        """
        # Get tier-based skill filter
        try:
            tier_skills = self._get_skills_for_tier(tier)
        except ValueError as e:
            return DeploymentResult(
                success=False,
                deployed=[],
                skipped=[],
                errors=[{"skill": "all", "error": str(e)}],
                message=str(e),
            )

        # Discover all bundled skills, then filter by tier
        all_skills = self._discover_bundled_pm_skills()
        skills = [s for s in all_skills if s["name"] in tier_skills]

        self.logger.info(
            f"Deploying {len(skills)}/{len(all_skills)} skills for tier '{tier}'"
        )
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

        # SECURITY: Validate deployment path is within home directory
        # (deployment_dir is ~/.claude/skills/, not under project_dir)
        if not self._validate_safe_path(Path.home(), deployment_dir):
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
        existing_deployments = {skill["name"]: skill for skill in deployed_skills}

        new_deployed_skills = []
        timestamp = datetime.now(tz=UTC).isoformat()
        total_skills = len(skills)

        for idx, skill in enumerate(skills):
            try:
                skill_name = skill["name"]
                source_path = skill["path"]

                # Report progress if callback provided
                if progress_callback:
                    progress_callback(skill_name, idx + 1, total_skills)

                # Create skill directory: .claude/skills/{skill_name}/
                skill_dir = deployment_dir / skill_name
                skill_dir.mkdir(parents=True, exist_ok=True)

                # Target path: .claude/skills/{skill_name}/SKILL.md
                target_path = skill_dir / "SKILL.md"

                # SECURITY: Validate target path is within user-level deployment dir
                if not self._validate_safe_path(deployment_dir, target_path):
                    raise ValueError(f"Path traversal attempt detected: {target_path}")

                # Compute checksum and read declared version of source
                checksum = self._compute_checksum(source_path)
                bundled_version = _read_skill_version(source_path)

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

                    # BUG #735: content differs. Do NOT blindly overwrite —
                    # that silently reverts user-hardened skills. Only overwrite
                    # when the bundled skill is STRICTLY NEWER than the deployed
                    # one. The deployed version is read from the actual file on
                    # disk (authoritative) falling back to the registry entry.
                    if target_path.exists():
                        deployed_version = _read_skill_version(target_path)
                    else:
                        deployed_version = existing.get(
                            "version", DEFAULT_SKILL_VERSION
                        )

                    if _parse_version_tuple(bundled_version) <= _parse_version_tuple(
                        deployed_version
                    ):
                        skipped.append(skill_name)
                        # Preserve the deployed file's real version + a fresh
                        # checksum of what is actually on disk so the registry
                        # reflects reality (not the bundled source).
                        new_deployed_skills.append(
                            {
                                "name": skill_name,
                                "version": deployed_version,
                                "deployed_at": existing.get("deployed_at", timestamp),
                                "checksum": (
                                    self._compute_checksum(target_path)
                                    if target_path.exists()
                                    else existing.get("checksum", checksum)
                                ),
                            }
                        )
                        self.logger.info(
                            f"Skipped {skill_name}: deployed version "
                            f"{deployed_version} >= bundled {bundled_version} "
                            f"(refusing to clobber user-modified skill)"
                        )
                        continue

                    self.logger.info(
                        f"Upgrading {skill_name}: {deployed_version} -> "
                        f"{bundled_version} (bundled is newer)"
                    )

                # Deploy skill. Overwrites only when: forced, brand-new, or the
                # bundled version is strictly newer (checked above).
                shutil.copy2(source_path, target_path)

                # Add to deployed list
                deployed.append(skill_name)

                # Update registry entry with the real bundled version.
                skill_entry = {
                    "name": skill_name,
                    "version": bundled_version,
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
            f"Deployed {len(deployed)} skills (tier: {tier}), skipped {len(skipped)}, "
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

    def verify_pm_skills(
        self, project_dir: Path, auto_repair: bool = True
    ) -> VerificationResult:
        """Verify PM skills are properly deployed with enhanced validation.

        Checks ALL required PM skills for:
        - Existence in deployment directory
        - File integrity (non-empty, valid checksums)
        - Version currency (compared to bundled source)

        Auto-repair logic:
        - If auto_repair=True (default), automatically deploys missing/corrupted skills
        - Reports what was fixed in the result

        Args:
            project_dir: Project root directory
            auto_repair: If True, auto-deploy missing/corrupted skills (default: True)

        Returns:
            VerificationResult with detailed verification status:
            - verified: True if all required skills are deployed and valid
            - missing_skills: List of required skills not deployed
            - corrupted_skills: List of skills with checksum mismatches
            - warnings: List of warning messages
            - skill_count: Total number of deployed skills

        Example:
            >>> result = deployer.verify_pm_skills(Path("/project"))
            >>> if not result.verified:
            ...     print(f"Missing: {result.missing_skills}")
            ...     print(f"Corrupted: {result.corrupted_skills}")
        """
        warnings = []
        missing_skills = []
        corrupted_skills = []
        outdated_skills = []

        # Check if registry exists
        registry = self._load_registry(project_dir)
        deployment_dir = self._get_deployment_dir(project_dir)
        deployed_skills_data = registry.get("skills", []) if registry else []

        # Build lookup for deployed skills
        deployed_lookup = {skill["name"]: skill for skill in deployed_skills_data}

        # Check ALL required PM skills
        for required_skill in REQUIRED_PM_SKILLS:
            # Check if skill is in registry
            if required_skill not in deployed_lookup:
                warnings.append(f"Required PM skill missing: {required_skill}")
                missing_skills.append(required_skill)
                continue

            # Check if skill file exists
            skill_file = deployment_dir / required_skill / "SKILL.md"
            if not skill_file.exists():
                warnings.append(
                    f"Required PM skill file missing: {required_skill}/SKILL.md"
                )
                missing_skills.append(required_skill)
                continue

            # Check if skill file is empty/corrupted
            try:
                file_size = skill_file.stat().st_size
                if file_size == 0:
                    warnings.append(
                        f"Required PM skill file is empty: {required_skill}/SKILL.md"
                    )
                    corrupted_skills.append(required_skill)
                    continue
            except OSError as e:
                warnings.append(
                    f"Cannot read required PM skill file: {required_skill}/SKILL.md - {e}"
                )
                corrupted_skills.append(required_skill)
                continue

            # Verify checksum.
            #
            # BUG #735: a registry-vs-disk checksum mismatch on a non-empty,
            # readable file means the deployed skill was *modified* (e.g. a
            # user hardened it), NOT that it is corrupt. Classifying it as
            # corrupted previously triggered auto-repair force-redeploy, which
            # silently reverted the user's changes. We now treat such files as
            # "user-modified" — a warning only, never auto-repaired. Genuine
            # corruption (empty/unreadable) is still caught above.
            deployed_skill = deployed_lookup[required_skill]
            current_checksum = self._compute_checksum(skill_file)
            expected_checksum = deployed_skill.get("checksum", "")

            if current_checksum != expected_checksum:
                warnings.append(
                    f"Required PM skill modified since deployment: {required_skill} "
                    f"(file differs from registry checksum — leaving user changes intact)"
                )

        # Check for available updates (bundled skills newer than deployed)
        bundled_skills = {s["name"]: s for s in self._discover_bundled_pm_skills()}
        for skill_name, bundled_skill in bundled_skills.items():
            # Skip non-required skills
            if skill_name not in REQUIRED_PM_SKILLS:
                continue

            # Find corresponding deployed skill
            deployed_skill = deployed_lookup.get(skill_name)

            if not deployed_skill:
                # Already tracked as missing
                continue

            # Check if checksums differ
            bundled_checksum = self._compute_checksum(bundled_skill["path"])
            deployed_checksum = deployed_skill.get("checksum", "")

            if bundled_checksum != deployed_checksum:
                # Don't add to outdated_skills if already in corrupted_skills
                if skill_name not in corrupted_skills:
                    warnings.append(f"PM skill update available: {skill_name}")
                    outdated_skills.append(skill_name)

        # Auto-repair if enabled and issues found.
        #
        # BUG #735: auto-repair previously called deploy_pm_skills(force=True),
        # which force-overwrites EVERY skill — clobbering unrelated
        # user-modified skills. We now repair ONLY the specific
        # missing/corrupt skills via a targeted copy, leaving every other
        # deployed skill (including user-modified ones) untouched.
        repaired_skills: list[str] = []
        if auto_repair and (missing_skills or corrupted_skills):
            broken = list(dict.fromkeys(missing_skills + corrupted_skills))
            self.logger.info(
                f"Auto-repairing PM skills: {len(missing_skills)} missing, "
                f"{len(corrupted_skills)} corrupted (targeted)"
            )
            repaired_skills = self._repair_specific_skills(project_dir, broken)

            if repaired_skills:
                self.logger.info(f"Auto-repaired {len(repaired_skills)} PM skills")
                # Remove repaired skills from missing/corrupted lists
                missing_skills = [s for s in missing_skills if s not in repaired_skills]
                corrupted_skills = [
                    s for s in corrupted_skills if s not in repaired_skills
                ]
                warnings.append(
                    f"Auto-repaired {len(repaired_skills)} PM skills: "
                    f"{', '.join(repaired_skills)}"
                )

        # Determine verification status
        verified = len(missing_skills) == 0 and len(corrupted_skills) == 0

        # Build message
        if verified:
            if repaired_skills:
                message = f"All PM skills verified (auto-repaired {len(repaired_skills)} skills)"
            else:
                message = "All PM skills verified and up-to-date"
        else:
            issue_count = len(missing_skills) + len(corrupted_skills)
            message = f"{issue_count} PM skill issues found"

        return VerificationResult(
            verified=verified,
            warnings=warnings,
            missing_skills=missing_skills,
            corrupted_skills=corrupted_skills,
            outdated_skills=outdated_skills,
            message=message,
            skill_count=len(deployed_skills_data),
        )

    def _repair_specific_skills(
        self, project_dir: Path, skill_names: list[str]
    ) -> list[str]:
        """Redeploy ONLY the named skills from their bundled sources.

        WHAT: Copies the bundled SKILL.md for each named skill over the
        deployed location and updates that skill's registry entry, leaving all
        other deployed skills untouched.
        WHY: Bug #735 — auto-repair must fix genuinely missing/empty/corrupt
        files without force-redeploying (and thus clobbering) unrelated
        user-modified skills. This is the surgical alternative to
        ``deploy_pm_skills(force=True)``.

        Args:
            project_dir: Project root directory (for registry location).
            skill_names: Names of skills to repair.

        Returns:
            List of skill names that were successfully repaired.
        """
        if not skill_names:
            return []

        bundled = {s["name"]: s for s in self._discover_bundled_pm_skills()}
        deployment_dir = self._get_deployment_dir(project_dir)
        deployment_dir.mkdir(parents=True, exist_ok=True)

        registry = self._load_registry(project_dir)
        deployed_skills = registry.get("skills", [])
        registry_lookup = {s["name"]: s for s in deployed_skills}

        timestamp = datetime.now(tz=UTC).isoformat()
        repaired: list[str] = []

        for skill_name in skill_names:
            bundled_skill = bundled.get(skill_name)
            if not bundled_skill:
                self.logger.warning(
                    f"Cannot repair {skill_name}: no bundled source found"
                )
                continue

            source_path = bundled_skill["path"]
            skill_dir = deployment_dir / skill_name
            target_path = skill_dir / "SKILL.md"

            # SECURITY: keep targets inside the deployment directory.
            if not self._validate_safe_path(deployment_dir, target_path):
                self.logger.error(
                    f"Refusing to repair {skill_name}: unsafe target path"
                )
                continue

            try:
                skill_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
            except OSError as e:
                self.logger.error(f"Failed to repair {skill_name}: {e}")
                continue

            checksum = self._compute_checksum(target_path)
            version = _read_skill_version(source_path)
            registry_lookup[skill_name] = {
                "name": skill_name,
                "version": version,
                "deployed_at": timestamp,
                "checksum": checksum,
            }
            repaired.append(skill_name)
            self.logger.debug(f"Repaired PM skill: {skill_name}")

        if repaired:
            updated_registry = {
                "version": self.REGISTRY_VERSION,
                "deployed_at": timestamp,
                "skills": list(registry_lookup.values()),
            }
            if not self._save_registry(project_dir, updated_registry):
                self.logger.error("Failed to save registry after targeted repair")

        return repaired

    def get_deployed_skills(self, project_dir: Path) -> list[PMSkillInfo]:
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
            deployed_path = deployment_dir / skill_name / "SKILL.md"

            # Find source path (may not exist if bundled skills changed)
            source_path = self.bundled_pm_skills_path / skill_name / "SKILL.md"

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

    def check_updates_available(self, project_dir: Path) -> list[UpdateInfo]:
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
        deployed_skills = {skill["name"]: skill for skill in registry.get("skills", [])}

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
