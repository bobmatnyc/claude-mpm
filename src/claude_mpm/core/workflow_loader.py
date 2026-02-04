"""Workflow configuration loader with priority-based override system.

This module provides functions for loading, validating, and managing
workflow configurations with support for project-level, user-level,
and system-level defaults.

Priority order (highest to lowest):
1. Project-level: .claude-mpm/WORKFLOW.md
2. User-level: ~/.claude-mpm/WORKFLOW.md
3. System default: Built-in framework WORKFLOW.md
"""

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from claude_mpm.core.logging_utils import get_logger

logger = get_logger("workflow_loader")

# Required sections in workflow files
REQUIRED_SECTIONS = [
    "Phase 1",
    "Phase 2",
    "Phase 3",
    "Phase 4",
    "Phase 5",
]

RECOMMENDED_SECTIONS = [
    "Verification",
    "Override Commands",
]


@dataclass
class WorkflowConfig:
    """Workflow configuration with metadata."""

    content: str
    source_path: Path
    level: str  # 'project', 'user', or 'system'
    phase_count: int
    has_verification_gates: bool
    custom_phases: list[str]


def get_workflow_path(
    current_dir: Optional[Path] = None,
    framework_path: Optional[Path] = None,
) -> tuple[Optional[Path], str]:
    """Get the path to the active workflow file based on priority.

    Args:
        current_dir: Current working directory (defaults to cwd)
        framework_path: Path to framework installation

    Returns:
        Tuple of (path, level) where level is 'project', 'user', 'system', or 'none'
    """
    if current_dir is None:
        current_dir = Path.cwd()

    # Priority 1: Project-level
    project_path = current_dir / ".claude-mpm" / "WORKFLOW.md"
    if project_path.exists():
        logger.info(f"Found project-level workflow: {project_path}")
        return project_path, "project"

    # Priority 2: User-level
    user_path = Path.home() / ".claude-mpm" / "WORKFLOW.md"
    if user_path.exists():
        logger.info(f"Found user-level workflow: {user_path}")
        return user_path, "user"

    # Priority 3: System default (from framework_path if provided)
    if framework_path and framework_path != Path("__PACKAGED__"):
        system_path = framework_path / "src" / "claude_mpm" / "agents" / "WORKFLOW.md"
        if system_path.exists():
            logger.info(f"Found system-level workflow: {system_path}")
            return system_path, "system"

    # Priority 4: Package default (relative to this module)
    # This handles the case when framework_path is None or __PACKAGED__
    package_default = Path(__file__).parent.parent / "agents" / "WORKFLOW.md"
    if package_default.exists():
        logger.info(f"Found default workflow: {package_default}")
        return package_default, "default"

    logger.warning("No workflow file found")
    return None, "none"


def load_workflow(
    current_dir: Optional[Path] = None,
    framework_path: Optional[Path] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Load workflow content from the appropriate location.

    This is the main entry point for loading workflow configurations.
    It handles the priority system and returns the content.

    Args:
        current_dir: Current working directory (defaults to cwd)
        framework_path: Path to framework installation

    Returns:
        Tuple of (content, level) where level is 'project', 'user', 'system', or None
    """
    path, level = get_workflow_path(current_dir, framework_path)

    if path is None:
        return None, None

    try:
        content = path.read_text()
        logger.info(f"Loaded workflow from {level} level: {path}")
        return content, level
    except Exception as e:
        logger.error(f"Failed to load workflow from {path}: {e}")
        return None, None


def get_workflow_config(
    current_dir: Optional[Path] = None,
    framework_path: Optional[Path] = None,
) -> Optional[WorkflowConfig]:
    """Get detailed workflow configuration with metadata.

    Args:
        current_dir: Current working directory (defaults to cwd)
        framework_path: Path to framework installation

    Returns:
        WorkflowConfig with full metadata, or None if not found
    """
    path, level = get_workflow_path(current_dir, framework_path)

    if path is None:
        return None

    try:
        content = path.read_text()

        # Count phases (Phase 1, Phase 2, etc. and custom phases)
        phase_pattern = r"###\s*Phase\s*(\d+)"
        phases = re.findall(phase_pattern, content)
        phase_count = len(set(phases))

        # Check for verification gates section
        has_verification = "Verification" in content and "|" in content

        # Find custom phases (Phase 6+)
        custom_phases = [p for p in phases if int(p) > 5]

        return WorkflowConfig(
            content=content,
            source_path=path,
            level=level,
            phase_count=phase_count,
            has_verification_gates=has_verification,
            custom_phases=[f"Phase {p}" for p in custom_phases],
        )
    except Exception as e:
        logger.error(f"Failed to parse workflow config: {e}")
        return None


def init_local_workflow(
    current_dir: Optional[Path] = None,
    framework_path: Optional[Path] = None,
    minimal: bool = False,
) -> tuple[bool, str]:
    """Initialize a local workflow configuration file.

    Creates a .claude-mpm/WORKFLOW.md file in the current directory
    by copying the system default or creating a minimal template.

    Args:
        current_dir: Current working directory (defaults to cwd)
        framework_path: Path to framework installation
        minimal: If True, create minimal template instead of full copy

    Returns:
        Tuple of (success, message)
    """
    if current_dir is None:
        current_dir = Path.cwd()

    target_dir = current_dir / ".claude-mpm"
    target_path = target_dir / "WORKFLOW.md"

    # Check if already exists
    if target_path.exists():
        return False, f"Workflow file already exists: {target_path}"

    # Ensure directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    if minimal:
        # Create minimal template
        content = _get_minimal_workflow_template()
        target_path.write_text(content)
        return True, f"Created minimal workflow template: {target_path}"

    # Copy from system default
    if framework_path and framework_path != Path("__PACKAGED__"):
        system_path = framework_path / "src" / "claude_mpm" / "agents" / "WORKFLOW.md"
        if system_path.exists():
            shutil.copy(system_path, target_path)
            return True, f"Initialized workflow from system default: {target_path}"

    # Fallback to minimal template
    content = _get_minimal_workflow_template()
    target_path.write_text(content)
    return (
        True,
        f"Created minimal workflow template (system default not found): {target_path}",
    )


def reset_local_workflow(
    current_dir: Optional[Path] = None,
) -> tuple[bool, str]:
    """Reset to default workflow by removing local override.

    Args:
        current_dir: Current working directory (defaults to cwd)

    Returns:
        Tuple of (success, message)
    """
    if current_dir is None:
        current_dir = Path.cwd()

    project_path = current_dir / ".claude-mpm" / "WORKFLOW.md"

    if not project_path.exists():
        return False, "No local workflow file to reset"

    # Create backup before removing
    backup_path = project_path.with_suffix(".md.bak")
    shutil.copy(project_path, backup_path)

    project_path.unlink()
    return True, f"Reset workflow to default. Backup saved: {backup_path}"


def validate_workflow(
    content: Optional[str] = None,
    current_dir: Optional[Path] = None,
    framework_path: Optional[Path] = None,
) -> list[dict]:
    """Validate workflow configuration.

    Args:
        content: Workflow content to validate (loads from file if None)
        current_dir: Current working directory (defaults to cwd)
        framework_path: Path to framework installation

    Returns:
        List of validation results with 'status', 'message', and 'section' keys
    """
    results = []

    if content is None:
        content, _ = load_workflow(current_dir, framework_path)

    if content is None:
        results.append(
            {
                "status": "error",
                "message": "No workflow file found",
                "section": "file",
            }
        )
        return results

    # Check required sections
    for section in REQUIRED_SECTIONS:
        if section in content:
            results.append(
                {
                    "status": "ok",
                    "message": f"{section} defined",
                    "section": section,
                }
            )
        else:
            results.append(
                {
                    "status": "error",
                    "message": f"Missing required section: {section}",
                    "section": section,
                }
            )

    # Check recommended sections
    for section in RECOMMENDED_SECTIONS:
        if section in content:
            results.append(
                {
                    "status": "ok",
                    "message": f"{section} section present",
                    "section": section,
                }
            )
        else:
            results.append(
                {
                    "status": "warn",
                    "message": f"Recommended section missing: {section}",
                    "section": section,
                }
            )

    # Check for custom phases
    phase_pattern = r"###\s*Phase\s*(\d+)"
    phases = re.findall(phase_pattern, content)
    custom_phases = [p for p in phases if int(p) > 5]
    if custom_phases:
        for phase in custom_phases:
            results.append(
                {
                    "status": "warn",
                    "message": f"Custom Phase {phase} defined - ensure corresponding agent exists",
                    "section": f"Phase {phase}",
                }
            )

    # Check for verification gates table
    if "Verification" in content and "|" in content:
        results.append(
            {
                "status": "ok",
                "message": "Verification gates table found",
                "section": "Verification Gates",
            }
        )

    return results


def _get_minimal_workflow_template() -> str:
    """Get minimal workflow template content."""
    return """<!-- PURPOSE: 5-phase workflow execution details -->

# PM Workflow Configuration

## Mandatory 5-Phase Sequence

### Phase 1: Research (ALWAYS FIRST)
**Agent**: Research
**Output**: Requirements, constraints, success criteria, risks

### Phase 2: Code Analyzer Review (MANDATORY)
**Agent**: Code Analyzer
**Output**: APPROVED/NEEDS_IMPROVEMENT/BLOCKED

### Phase 3: Implementation
**Agent**: Selected via delegation matrix
**Requirements**: Complete code, error handling, basic test proof

### Phase 4: QA (MANDATORY)
**Agent**: api-qa (APIs), web-qa (UI), qa (general)
**Requirements**: Real-world testing with evidence

### Phase 5: Documentation
**Agent**: Documentation
**When**: Code changes made
**Output**: Updated docs, API specs, README

## Verification Gates

| Phase | Verification Required | Evidence Format |
|-------|----------------------|-----------------|
| Research | Findings documented | File paths, line numbers |
| Code Analyzer | Approval status | APPROVED/NEEDS_IMPROVEMENT/BLOCKED |
| Implementation | Tests pass | Test command output |
| QA | All criteria verified | Test results with evidence |

## Override Commands

- "Skip workflow" - bypass sequence
- "Go directly to [phase]" - jump to phase
- "No QA needed" - skip QA (not recommended)
- "Emergency fix" - bypass research
"""
