"""Migration 6.5.40: Remove project-level copies of all bundled skills.

WHAT: For each skill in the dynamically-discovered bundled set, removes the
project-level directory (.claude/skills/<name>/) and any legacy flat file
(.claude/skills/<name>.md) only when the corresponding user-level copy
(~/.claude/skills/<name>/SKILL.md) is confirmed present.  Logs totals and
errors, returns True when all deletions succeeded, False on any OSError.

WHY: All bundled skills now deploy at user level (~/.claude/skills/).
Project-level copies (.claude/skills/) are duplicates that create confusion.
This migration safely removes them only when the user-level copy exists.

SAFETY:
- Only removes skills in the bundled set (never user-authored custom skills).
- Only removes when user-level copy confirmed present (no data loss).
- Non-fatal: logs errors and continues.
- Idempotent: safe to run multiple times.

NOTE: This migration operates on the CURRENT project only (Path.cwd()).
Each project is cleaned the next time claude-mpm starts up in that project.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_bundled_skill_names() -> frozenset[str]:
    """Return the set of bundled skill names from SkillsService.

    Why: Derives the canonical bundled set dynamically so there is no
    hardcoded list that can drift out of sync with actual bundled skills.
    What: Constructs SkillsService(scope=ConfigScope.USER) normally — __init__
    is side-effect-free (only resolves paths and loads registry YAML) — then
    calls discover_bundled_skills().  If discovery fails the error is logged
    at WARNING level and the caller receives a sentinel None so it can abort
    cleanup safely instead of silently no-oping.
    Test: Mock bundled_skills_path to a tmp dir with sample SKILL.md files and
    assert the returned frozenset contains exactly those names.
    """
    from claude_mpm.core.config_scope import ConfigScope
    from claude_mpm.skills.skills_service import SkillsService

    service = SkillsService(scope=ConfigScope.USER)
    skills = service.discover_bundled_skills()
    return frozenset(s["name"] for s in skills)


def run_migration() -> bool:
    """Remove project-level copies of bundled skills when user-level copies exist.

    Why: Bundled skills now deploy at user level; project-level copies are
    duplicates that can confuse Claude Code's skill resolution.
    What: For each bundled skill, removes .claude/skills/<name>/ dir and legacy
    .claude/skills/<name>.md if the user-level ~/.claude/skills/<name>/SKILL.md
    exists. Never removes non-bundled custom skills.
    Test: Create a tmp project dir with a bundled skill dir and a user-level copy;
    run migration; assert project-level dir is gone but user-level copy remains.
    """
    try:
        try:
            bundled_skill_names = _get_bundled_skill_names()
        except Exception as exc:
            logger.warning(
                "Cannot discover bundled skills — aborting cleanup to avoid data loss: %s",
                exc,
            )
            return False

        if not bundled_skill_names:
            logger.warning(
                "Bundled skill discovery returned empty set — aborting cleanup "
                "to avoid deleting everything. Check bundled skills directory."
            )
            return False

        user_skills_base = Path.home() / ".claude" / "skills"
        project_root = Path.cwd()
        project_skills_base = project_root / ".claude" / "skills"

        if not project_skills_base.exists():
            logger.debug("No project-level skills directory, nothing to do")
            return True

        any_error = False
        total_removed = 0

        for skill_name in sorted(bundled_skill_names):
            # Check user-level copy exists
            user_skill_file = user_skills_base / skill_name / "SKILL.md"
            if not user_skill_file.exists():
                logger.debug(
                    "Skipping '%s': user-level copy not found at %s",
                    skill_name,
                    user_skill_file,
                )
                continue

            # Count one logical removal per skill regardless of whether we remove
            # a directory, a flat file, or both (avoids double-counting).
            skill_removed = False

            # Remove project-level directory
            project_skill_dir = project_skills_base / skill_name
            if project_skill_dir.exists():
                try:
                    shutil.rmtree(project_skill_dir)
                    skill_removed = True
                    logger.info(
                        "Removed project-level bundled skill directory: %s "
                        "(user copy at %s)",
                        skill_name,
                        user_skill_file,
                    )
                except OSError as exc:
                    logger.error("Failed to remove %s: %s", project_skill_dir, exc)
                    any_error = True

            # Remove legacy flat .md file
            project_skill_file = project_skills_base / f"{skill_name}.md"
            if project_skill_file.exists():
                try:
                    project_skill_file.unlink()
                    skill_removed = True
                    logger.info(
                        "Removed legacy flat skill file: %s", project_skill_file
                    )
                except OSError as exc:
                    logger.error("Failed to remove %s: %s", project_skill_file, exc)
                    any_error = True

            if skill_removed:
                total_removed += 1

        logger.info(
            "Migration complete: removed=%d skills (logical), errors=%s",
            total_removed,
            any_error,
        )
        return not any_error

    except Exception as exc:
        logger.error("Unexpected error in remove_project_level_bundled_skills: %s", exc)
        return False
