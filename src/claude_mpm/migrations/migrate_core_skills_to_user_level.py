"""Migration 6.1.0: Move CORE skills to user level, remove project-level duplicates.

WHY: Skills in USER_LEVEL_SKILLS (mpm-* framework skills and the four universal
core skills) should live at ~/.claude/skills/ and be shared across all projects.
Having copies in .claude/skills/ (project level) creates duplicates and confusion.

WHAT THIS MIGRATION DOES:
1. Iterates over every skill in USER_LEVEL_SKILLS.
2. For each skill, verifies it exists at ~/.claude/skills/{skill}/SKILL.md.
3. Only if the user-level copy is confirmed present, removes the project-level
   copy at .claude/skills/{skill}/ (the whole directory).
4. Skips skills that are absent from user level (safe: never deletes blindly).
5. Records the list of removed skills in the return value for reporting.

IDEMPOTENCY: Running this migration multiple times is safe — if the project-level
directory no longer exists the migration simply skips it.
"""

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Import the canonical user-level skills set.  Imported lazily inside the
# run function to avoid circular-import issues at module load time.


def _get_user_level_skills() -> frozenset[str]:
    """Return USER_LEVEL_SKILLS, importing lazily to avoid circular imports."""
    from claude_mpm.services.skills.selective_skill_deployer import USER_LEVEL_SKILLS

    return USER_LEVEL_SKILLS


def _find_project_roots() -> list[Path]:
    """Return candidate project roots that may have .claude/skills/ directories.

    Searches from the current working directory upward to find git-rooted
    projects, then returns the cwd (which is the project being migrated).
    In practice the migration runner calls run() from a specific project
    context so cwd is sufficient.

    Returns:
        List of Path objects to check for .claude/skills/ presence.
    """
    candidates: list[Path] = [Path.cwd()]

    # Also check if we can find a project root from the package itself
    try:
        package_dir = Path(__file__).resolve().parent.parent
        # Traverse up from package looking for .git
        for parent in [package_dir] + list(package_dir.parents):
            if (parent / ".git").exists():
                if parent not in candidates:
                    candidates.append(parent)
                break
    except Exception:
        pass

    return candidates


def migrate_core_skills_to_user_level() -> bool:
    """Remove project-level copies of USER_LEVEL_SKILLS skills.

    For each skill in USER_LEVEL_SKILLS:
    - Verify the user-level copy at ~/.claude/skills/{skill}/SKILL.md exists.
    - Remove the project-level directory .claude/skills/{skill}/ only when the
      user-level copy is confirmed present (idempotent and non-destructive).

    Returns:
        True on success (even if nothing was removed), False if an unrecoverable
        error occurred.
    """
    user_level_skills = _get_user_level_skills()
    user_skills_base = Path.home() / ".claude" / "skills"

    project_roots = _find_project_roots()
    any_error = False
    total_removed = 0
    total_skipped_no_user_copy = 0
    total_already_clean = 0

    for project_root in project_roots:
        project_skills_base = project_root / ".claude" / "skills"

        if not project_skills_base.exists():
            logger.debug(
                "No project-level skills directory at %s, skipping", project_skills_base
            )
            continue

        logger.info(
            "Scanning project-level skills at %s for USER_LEVEL_SKILLS duplicates",
            project_skills_base,
        )

        for skill_name in sorted(user_level_skills):
            project_skill_dir = project_skills_base / skill_name

            # Nothing to do if project-level copy doesn't exist
            if not project_skill_dir.exists():
                total_already_clean += 1
                logger.debug("Already clean (no project copy): %s", skill_name)
                continue

            # Verify user-level copy exists before removing project copy
            user_skill_file = user_skills_base / skill_name / "SKILL.md"
            if not user_skill_file.exists():
                logger.warning(
                    "Skipping removal of project-level '%s': user-level copy not found at %s",
                    skill_name,
                    user_skill_file,
                )
                total_skipped_no_user_copy += 1
                continue

            # Safe to remove the project-level directory
            try:
                shutil.rmtree(project_skill_dir)
                total_removed += 1
                logger.info(
                    "Removed project-level duplicate skill: %s (user copy confirmed at %s)",
                    skill_name,
                    user_skill_file,
                )
            except OSError as exc:
                logger.error(
                    "Failed to remove project-level skill directory %s: %s",
                    project_skill_dir,
                    exc,
                )
                any_error = True

    logger.info(
        "Migration complete: removed=%d, already_clean=%d, skipped_no_user_copy=%d, errors=%s",
        total_removed,
        total_already_clean,
        total_skipped_no_user_copy,
        any_error,
    )

    return not any_error


def run_migration() -> bool:
    """Entry point called by the migration runner.

    Returns:
        True if migration completed without errors, False otherwise.
    """
    try:
        return migrate_core_skills_to_user_level()
    except Exception as exc:
        logger.error("Unexpected error in migrate_core_skills_to_user_level: %s", exc)
        return False
