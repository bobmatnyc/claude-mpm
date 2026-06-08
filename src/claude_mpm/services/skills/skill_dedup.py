"""Framework-skill deduplication sweep across multiple projects.

WHAT: Scans a root directory for project .claude/skills/ directories and removes
any skill whose name is in USER_LEVEL_SKILLS AND whose user-level copy exists at
~/.claude/skills/<name>/.  Supports dry-run (default) and apply modes.

WHY: Migration 6.1.0_core_skills_to_user_level was previously recorded globally
so it only ran once; projects opened later kept stale project-level copies.  This
module provides both a per-invocation sweep (the CLI subcommand) and a reusable
helper used by tests to exercise the logic in isolation.

References
----------
LINK: none
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_user_level_skills() -> frozenset[str]:
    """Return USER_LEVEL_SKILLS, importing lazily to avoid circular imports."""
    from claude_mpm.services.skills.selective_skill_deployer import USER_LEVEL_SKILLS

    return USER_LEVEL_SKILLS


@dataclass
class ProjectDedupResult:
    """Dedup result for a single project directory.

    Attributes:
        project_dir: Absolute path to the project root.
        removed: Skill names removed (or would be removed in dry-run).
        kept: Skill names in USER_LEVEL_SKILLS that were kept (no user-level copy).
        project_unique: Skill names NOT in USER_LEVEL_SKILLS — untouched.
        errors: Error messages for skills that failed to remove.
    """

    project_dir: Path
    removed: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    project_unique: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def removed_count(self) -> int:
        return len(self.removed)

    @property
    def project_unique_count(self) -> int:
        return len(self.project_unique)


@dataclass
class SweepSummary:
    """Aggregated results from sweeping multiple projects.

    Attributes:
        root: The directory that was scanned.
        dry_run: Whether this was a dry-run (True) or apply (False).
        results: Per-project results, one entry per project that had .claude/skills/.
        projects_scanned: Total projects examined (with or without skills dir).
    """

    root: Path
    dry_run: bool
    results: list[ProjectDedupResult] = field(default_factory=list)
    projects_scanned: int = 0

    @property
    def total_removed(self) -> int:
        return sum(r.removed_count for r in self.results)

    @property
    def total_project_unique(self) -> int:
        return sum(r.project_unique_count for r in self.results)

    @property
    def projects_with_dupes(self) -> int:
        return sum(1 for r in self.results if r.removed_count > 0)


def dedup_project_skills(
    project_dir: Path,
    user_skills_base: Path,
    dry_run: bool = True,
) -> ProjectDedupResult:
    """Remove USER_LEVEL_SKILLS duplicates from a single project's .claude/skills/.

    Only removes a skill directory when BOTH:
    - (a) its name is in USER_LEVEL_SKILLS, AND
    - (b) the corresponding user-level copy ~/.claude/skills/<name>/ exists.

    Never touches skills whose names are not in USER_LEVEL_SKILLS.

    Args:
        project_dir: Root of the project (parent of .claude/).
        user_skills_base: Path to the user-level skills directory (~/.claude/skills/).
        dry_run: If True (default), report what would be removed but do nothing.

    Returns:
        A :class:`ProjectDedupResult` with full per-skill accounting.
    """
    result = ProjectDedupResult(project_dir=project_dir)

    project_skills_base = project_dir / ".claude" / "skills"
    if not project_skills_base.exists():
        return result

    user_level_skills = _get_user_level_skills()

    # Enumerate all subdirectories in the project skills dir.
    try:
        entries = sorted(e for e in project_skills_base.iterdir() if e.is_dir())
    except OSError as exc:
        result.errors.append(f"Cannot list {project_skills_base}: {exc}")
        return result

    for skill_dir in entries:
        skill_name = skill_dir.name

        if skill_name not in user_level_skills:
            # Not a framework skill — never touch it.
            result.project_unique.append(skill_name)
            continue

        # Verify user-level copy exists before removing.
        user_skill_marker = user_skills_base / skill_name / "SKILL.md"
        if not user_skill_marker.exists():
            result.kept.append(skill_name)
            logger.debug(
                "Skipping '%s' in %s: no user-level copy at %s",
                skill_name,
                project_dir,
                user_skill_marker,
            )
            continue

        # Safe to remove (or report in dry-run).
        if dry_run:
            result.removed.append(skill_name)
            logger.debug(
                "[DRY-RUN] Would remove %s from %s", skill_name, project_skills_base
            )
            continue

        try:
            shutil.rmtree(skill_dir)
            result.removed.append(skill_name)
            logger.info(
                "Removed duplicate skill '%s' from %s (user copy confirmed)",
                skill_name,
                project_dir,
            )
        except OSError as exc:
            result.errors.append(f"Failed to remove '{skill_name}': {exc}")
            logger.error("Failed to remove skill dir %s: %s", skill_dir, exc)

    return result


def sweep_projects(
    root: Path,
    user_skills_base: Path | None = None,
    dry_run: bool = True,
) -> SweepSummary:
    """Scan top-level subdirectories of *root* and dedup framework skills.

    Only looks one level deep: ``<root>/<project>/.claude/skills/``.
    Sub-directories of *root* that contain no ``.claude/skills/`` directory are
    counted in ``projects_scanned`` but produce no :class:`ProjectDedupResult`.

    Args:
        root: Directory whose immediate children are treated as project roots.
        user_skills_base: Override for ~/.claude/skills/ (useful in tests).
        dry_run: If True (default), report only — delete nothing.

    Returns:
        A :class:`SweepSummary` containing per-project results.
    """
    if user_skills_base is None:
        user_skills_base = Path.home() / ".claude" / "skills"

    summary = SweepSummary(root=root, dry_run=dry_run)

    if not root.exists():
        logger.warning("Sweep root does not exist: %s", root)
        return summary

    try:
        top_level = sorted(d for d in root.iterdir() if d.is_dir())
    except OSError as exc:
        logger.error("Cannot list sweep root %s: %s", root, exc)
        return summary

    summary.projects_scanned = len(top_level)

    for project_dir in top_level:
        skills_dir = project_dir / ".claude" / "skills"
        if not skills_dir.exists():
            continue

        project_result = dedup_project_skills(
            project_dir=project_dir,
            user_skills_base=user_skills_base,
            dry_run=dry_run,
        )

        if (
            project_result.removed
            or project_result.kept
            or project_result.project_unique
            or project_result.errors
        ):
            summary.results.append(project_result)

    return summary
