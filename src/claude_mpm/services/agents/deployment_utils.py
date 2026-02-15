"""Shared utilities for agent deployment filename normalization.

This module provides consistent filename handling for agent deployment
across different services (SingleTierDeploymentService, GitSourceSyncService).

Design Decision: Dash-based filenames as standard

Rationale: Git repositories use dash-based naming (python-engineer.md),
which is the cache convention. YAML frontmatter may have underscore-based
agent_id fields (python_engineer). This module ensures all deployed files
use dash-based naming to avoid duplicates and maintain consistency.

Priority order for deriving deployment filename:
1. Source filename if it's dash-based (matches cache convention)
2. agent_id from YAML frontmatter, converted underscores to dashes
3. Derive from source filename, converting underscores to dashes

Phase 3 (Issue #299): Unified deployment interface

This module now provides the SINGLE SOURCE OF TRUTH for agent file deployment.
Both SingleTierDeploymentService and GitSourceSyncService call deploy_agent_file()
to ensure consistent behavior across all deployment paths.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

logger = logging.getLogger(__name__)


def normalize_deployment_filename(
    source_filename: str, agent_id: Optional[str] = None
) -> str:
    """Normalize filename for deployment.

    Ensures consistent dash-based filenames for deployed agents.

    Priority:
    1. Use source filename if dash-based (matches cache convention)
    2. Convert underscore to dash in source filename
    3. If agent_id provided and differs from source, use source (already normalized)

    Args:
        source_filename: Original filename (e.g., "python-engineer.md")
        agent_id: Optional agent_id from YAML frontmatter (e.g., "python_engineer")

    Returns:
        Dash-based filename with .md extension (e.g., "python-engineer.md")

    Examples:
        >>> normalize_deployment_filename("python-engineer.md")
        'python-engineer.md'

        >>> normalize_deployment_filename("python_engineer.md")
        'python-engineer.md'

        >>> normalize_deployment_filename("engineer.md", "python_engineer")
        'engineer.md'  # Source filename takes precedence

        >>> normalize_deployment_filename("QA.md")
        'qa.md'
    """
    # Get stem (filename without extension)
    path = Path(source_filename)
    stem = path.stem

    # Normalize: lowercase, replace underscores with dashes
    normalized_stem = stem.lower().replace("_", "-")

    # Strip -agent suffix for consistency (e.g., "qa-agent" -> "qa")
    if normalized_stem.endswith("-agent"):
        normalized_stem = normalized_stem[:-6]  # Remove "-agent"

    # Always use .md extension
    return f"{normalized_stem}.md"


def ensure_agent_id_in_frontmatter(content: str, filename: str) -> str:
    """Ensure YAML frontmatter has agent_id field.

    If the content has YAML frontmatter but no agent_id, derive one from filename.
    If no frontmatter exists, add one with agent_id.

    Args:
        content: Markdown file content (may have YAML frontmatter)
        filename: Source filename to derive agent_id from

    Returns:
        Content with agent_id in frontmatter (may be unchanged if already present)

    Examples:
        >>> content = "---\\nname: Python Engineer\\n---\\n# Content"
        >>> ensure_agent_id_in_frontmatter(content, "python-engineer.md")
        '---\\nagent_id: python-engineer\\nname: Python Engineer\\n---\\n# Content'
    """
    # Derive agent_id from filename (dash-based, no extension)
    derived_agent_id = Path(filename).stem.lower().replace("_", "-")
    if derived_agent_id.endswith("-agent"):
        derived_agent_id = derived_agent_id[:-6]

    # Check if content has YAML frontmatter
    if not content.startswith("---"):
        # No frontmatter, add one with agent_id
        return f"---\nagent_id: {derived_agent_id}\n---\n{content}"

    # Extract frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---(\s*\n)", content, re.DOTALL)
    if not frontmatter_match:
        # Malformed frontmatter, return unchanged
        return content

    yaml_content = frontmatter_match.group(1)
    rest_of_content = content[frontmatter_match.end() :]

    # Parse YAML to check for agent_id
    try:
        parsed = yaml.safe_load(yaml_content)
        if isinstance(parsed, dict) and "agent_id" in parsed:
            # agent_id already exists, return unchanged
            return content
    except yaml.YAMLError:
        # YAML parse error, try to add agent_id anyway
        pass

    # Add agent_id to the beginning of frontmatter
    new_yaml_content = f"agent_id: {derived_agent_id}\n{yaml_content}"
    return f"---\n{new_yaml_content}\n---{frontmatter_match.group(2)}{rest_of_content}"


def get_underscore_variant_filename(normalized_filename: str) -> Optional[str]:
    """Get underscore variant of a dash-based filename.

    Used to detect and clean up duplicate files where the same agent
    might exist with both dash and underscore naming.

    Args:
        normalized_filename: Dash-based filename (e.g., "python-engineer.md")

    Returns:
        Underscore variant filename, or None if no dashes to convert

    Examples:
        >>> get_underscore_variant_filename("python-engineer.md")
        'python_engineer.md'

        >>> get_underscore_variant_filename("engineer.md")
        None
    """
    path = Path(normalized_filename)
    stem = path.stem

    if "-" not in stem:
        return None

    underscore_stem = stem.replace("-", "_")
    return f"{underscore_stem}.md"


# ============================================================================
# Phase 3 (Issue #299): Validation and Deployment Interface
# ============================================================================


@dataclass
class ValidationResult:
    """Result of agent file validation.

    Attributes:
        valid: Whether the file passed validation
        errors: List of validation error messages
        warnings: List of non-fatal warning messages
        agent_id: Extracted or derived agent_id (if valid)
        has_frontmatter: Whether file has YAML frontmatter
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    agent_id: Optional[str] = None
    has_frontmatter: bool = False


@dataclass
class DeploymentResult:
    """Result of agent file deployment.

    Attributes:
        success: Whether deployment succeeded
        deployed_path: Path to deployed file (if successful)
        action: What action was taken ("deployed", "updated", "skipped", "failed")
        error: Error message (if failed)
        cleaned_legacy: List of legacy filenames that were cleaned up
    """

    success: bool
    deployed_path: Optional[Path] = None
    action: str = "failed"
    error: Optional[str] = None
    cleaned_legacy: List[str] = field(default_factory=list)


def validate_agent_file(source_file: Path) -> ValidationResult:
    """Validate agent file before deployment.

    Performs pre-deployment validation:
    1. File exists and is readable
    2. File has .md extension
    3. YAML frontmatter is valid (if present)
    4. Content is not empty

    Args:
        source_file: Path to agent file to validate

    Returns:
        ValidationResult with validation status and any errors

    Examples:
        >>> result = validate_agent_file(Path("engineer.md"))
        >>> if result.valid:
        ...     print(f"Agent ID: {result.agent_id}")
        >>> else:
        ...     print(f"Errors: {result.errors}")
    """
    errors: List[str] = []
    warnings: List[str] = []
    agent_id: Optional[str] = None
    has_frontmatter = False

    # Check file exists
    if not source_file.exists():
        return ValidationResult(
            valid=False, errors=[f"File does not exist: {source_file}"]
        )

    # Check file is readable
    try:
        content = source_file.read_text(encoding="utf-8")
    except PermissionError:
        return ValidationResult(
            valid=False, errors=[f"Permission denied reading: {source_file}"]
        )
    except UnicodeDecodeError:
        return ValidationResult(
            valid=False, errors=[f"File is not valid UTF-8: {source_file}"]
        )

    # Check extension
    if source_file.suffix.lower() != ".md":
        warnings.append(f"Non-standard extension: {source_file.suffix}")

    # Check content is not empty
    if not content.strip():
        errors.append("File is empty")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    # Check YAML frontmatter
    if content.startswith("---"):
        has_frontmatter = True
        frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if frontmatter_match:
            yaml_content = frontmatter_match.group(1)
            try:
                parsed = yaml.safe_load(yaml_content)
                if isinstance(parsed, dict):
                    agent_id = parsed.get("agent_id")
                    if agent_id and not isinstance(agent_id, str):
                        warnings.append(
                            f"agent_id should be string, got {type(agent_id).__name__}"
                        )
                        agent_id = str(agent_id)
                else:
                    warnings.append("Frontmatter is not a valid YAML dictionary")
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML frontmatter: {e}")
        else:
            warnings.append("Malformed frontmatter (missing closing ---)")

    # Derive agent_id from filename if not in frontmatter
    if not agent_id:
        derived_id = source_file.stem.lower().replace("_", "-")
        if derived_id.endswith("-agent"):
            derived_id = derived_id[:-6]
        agent_id = derived_id

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        agent_id=agent_id,
        has_frontmatter=has_frontmatter,
    )


def deploy_agent_file(
    source_file: Path,
    deployment_dir: Path,
    *,
    cleanup_legacy: bool = True,
    ensure_frontmatter: bool = True,
    force: bool = False,
) -> DeploymentResult:
    """Deploy a single agent file with standardized naming.

    This is the SINGLE SOURCE OF TRUTH for agent file deployment.
    Both SingleTierDeploymentService and GitSourceSyncService should
    call this function to ensure consistent deployment behavior.

    Design Decision: Content-based deployment with frontmatter injection

    Rationale: Always read and write content (not copy) to ensure:
    1. Frontmatter can be injected/modified during deployment
    2. Content hash comparison works correctly
    3. Consistent behavior across all deployment paths

    Algorithm:
    1. Validate source file exists
    2. Normalize filename to dash-based convention
    3. Clean up legacy underscore variants (if cleanup_legacy=True)
    4. Check if deployment needed (content comparison unless force=True)
    5. Ensure agent_id in frontmatter (if ensure_frontmatter=True)
    6. Write content to deployment location

    Args:
        source_file: Path to source agent file (in cache)
        deployment_dir: Target deployment directory (.claude/agents/)
        cleanup_legacy: Remove underscore-variant files (default: True)
        ensure_frontmatter: Ensure agent_id in frontmatter (default: True)
        force: Force deployment even if content matches (default: False)

    Returns:
        DeploymentResult with deployment status and deployed path

    Examples:
        >>> result = deploy_agent_file(
        ...     source_file=Path("cache/python-engineer.md"),
        ...     deployment_dir=Path(".claude/agents"),
        ... )
        >>> if result.success:
        ...     print(f"Deployed to: {result.deployed_path}")
        >>> else:
        ...     print(f"Failed: {result.error}")

    Error Handling:
        - FileNotFoundError: Returns failed result with error
        - PermissionError: Returns failed result with error
        - IOError: Returns failed result with error
    """
    cleaned_legacy: List[str] = []

    # Step 1: Validate source file exists
    if not source_file.exists():
        logger.error(f"Source file does not exist: {source_file}")
        return DeploymentResult(
            success=False, error=f"Source file does not exist: {source_file}"
        )

    try:
        # Step 2: Normalize filename to dash-based convention
        normalized_filename = normalize_deployment_filename(source_file.name)
        target_file = deployment_dir / normalized_filename

        # Step 3: Clean up legacy underscore variants
        if cleanup_legacy:
            underscore_variant = get_underscore_variant_filename(normalized_filename)
            if underscore_variant:
                underscore_path = deployment_dir / underscore_variant
                if underscore_path.exists() and underscore_path != target_file:
                    logger.info(
                        f"Removing underscore variant: {underscore_variant} "
                        f"(replaced by {normalized_filename})"
                    )
                    underscore_path.unlink()
                    cleaned_legacy.append(underscore_variant)

        # Step 4: Read source content
        source_content = source_file.read_text(encoding="utf-8")

        # Step 5: Check if deployment needed (content comparison)
        was_existing = target_file.exists()
        should_deploy = force

        if not force and was_existing:
            existing_content = target_file.read_text(encoding="utf-8")
            # Compare after potential frontmatter modification
            modified_content = source_content
            if ensure_frontmatter:
                modified_content = ensure_agent_id_in_frontmatter(
                    source_content, normalized_filename
                )
            should_deploy = modified_content != existing_content
        else:
            should_deploy = True

        if not should_deploy and was_existing:
            logger.debug(f"Skipped (up-to-date): {normalized_filename}")
            return DeploymentResult(
                success=True,
                deployed_path=target_file,
                action="skipped",
                cleaned_legacy=cleaned_legacy,
            )

        # Step 6: Ensure frontmatter if requested
        deploy_content = source_content
        if ensure_frontmatter:
            deploy_content = ensure_agent_id_in_frontmatter(
                source_content, normalized_filename
            )

        # Step 7: Ensure deployment directory exists
        deployment_dir.mkdir(parents=True, exist_ok=True)

        # Step 8: Write content to deployment location
        target_file.write_text(deploy_content, encoding="utf-8")

        # Determine action
        action = "updated" if was_existing else "deployed"
        logger.info(f"{action.capitalize()}: {normalized_filename}")

        return DeploymentResult(
            success=True,
            deployed_path=target_file,
            action=action,
            cleaned_legacy=cleaned_legacy,
        )

    except PermissionError as e:
        logger.error(f"Permission denied deploying {source_file.name}: {e}")
        return DeploymentResult(
            success=False,
            error=f"Permission denied: {e}",
            cleaned_legacy=cleaned_legacy,
        )
    except OSError as e:
        logger.error(f"IO error deploying {source_file.name}: {e}")
        return DeploymentResult(
            success=False, error=f"IO error: {e}", cleaned_legacy=cleaned_legacy
        )
    except Exception as e:
        logger.error(f"Unexpected error deploying {source_file.name}: {e}")
        return DeploymentResult(
            success=False, error=f"Unexpected error: {e}", cleaned_legacy=cleaned_legacy
        )
