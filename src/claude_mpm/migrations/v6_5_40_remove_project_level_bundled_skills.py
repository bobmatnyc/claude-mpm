"""Migration 6.5.40: Remove project-level copies of all bundled skills.

WHY: All bundled skills now deploy at user level (~/.claude/skills/).
Project-level copies (.claude/skills/) are duplicates that create confusion.
This migration safely removes them only when the user-level copy exists.

SAFETY:
- Only removes skills in the bundled set (never user-authored custom skills).
- Only removes when user-level copy confirmed present (no data loss).
- Non-fatal: logs errors and continues.
- Idempotent: safe to run multiple times.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_bundled_skill_names() -> frozenset[str]:
    """Return the set of bundled skill names from SkillsService.

    Why: Derives the canonical bundled set dynamically so there is no
    hardcoded list that can drift out of sync with actual bundled skills.
    What: Instantiates SkillsService without calling __init__ to avoid side
    effects, sets bundled_skills_path manually, then calls discover_bundled_skills().
    Test: Mock bundled_skills_path to a tmp dir with sample SKILL.md files and
    assert the returned frozenset contains exactly those names.
    """
    try:
        from claude_mpm.skills.skills_service import SkillsService

        service = SkillsService.__new__(SkillsService)
        service.bundled_skills_path = (
            Path(__file__).parent.parent / "skills" / "bundled"
        )
        skills = service.discover_bundled_skills()
        return frozenset(s["name"] for s in skills)
    except Exception as exc:
        logger.error("Failed to discover bundled skills: %s", exc)
        return frozenset()


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
        bundled_skill_names = _get_bundled_skill_names()
        if not bundled_skill_names:
            logger.warning("No bundled skills found, skipping migration")
            return True

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

            # Remove project-level directory
            project_skill_dir = project_skills_base / skill_name
            if project_skill_dir.exists():
                try:
                    shutil.rmtree(project_skill_dir)
                    total_removed += 1
                    logger.info(
                        "Removed project-level bundled skill: %s (user copy at %s)",
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
                    total_removed += 1
                    logger.info(
                        "Removed legacy flat skill file: %s", project_skill_file
                    )
                except OSError as exc:
                    logger.error("Failed to remove %s: %s", project_skill_file, exc)
                    any_error = True

        logger.info(
            "Migration complete: removed=%d, errors=%s", total_removed, any_error
        )
        return not any_error

    except Exception as exc:
        logger.error("Unexpected error in remove_project_level_bundled_skills: %s", exc)
        return False
