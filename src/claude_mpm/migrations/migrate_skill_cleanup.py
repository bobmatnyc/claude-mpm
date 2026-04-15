"""Migration: Skill naming cleanup — remove mpm-* duplicates and rename conflicting skills.

WHY:
1. mpm-* skills belong ONLY at ~/.claude/skills/ (user level). Having them in
   .claude/skills/ (project level) creates duplicates and confusion.
2. Skills whose names start with "mcp" conflict visually (and functionally via
   prefix matching) with Claude Code's built-in /mcp command.
   - ~/.claude/skills/mcp-vector-search-pr-mr-skill → vector-search-pr-mr-skill
     (renamed copy already exists at user level; old name can be removed)
3. toolchains-ai-protocols-model-context in project skills should match the
   plugin directory name toolchains-ai-protocols.

WHAT THIS MIGRATION DOES:
1. Removes mpm-* skill directories from .claude/skills/ (project level) when
   confirmed present at ~/.claude/skills/.
2. In .claude/skills/: renames toolchains-ai-protocols-model-context →
   toolchains-ai-protocols if the target doesn't already exist.
3. In ~/.claude/skills/: removes mcp-vector-search-pr-mr-skill when
   vector-search-pr-mr-skill already exists at the same level.

CLI usage (standalone):
    python migrate_skill_cleanup.py [--dry-run]

IDEMPOTENCY: Safe to run multiple times. Each step checks preconditions before
acting and skips operations that are already complete.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Old mcp-prefixed name at user level → replaced by this new name
MCP_SKILL_RENAME: dict[str, str] = {
    "mcp-vector-search-pr-mr-skill": "vector-search-pr-mr-skill",
}

# Project-level rename: old name → new name (must match plugin directory)
PROJECT_SKILL_RENAME: dict[str, str] = {
    "toolchains-ai-protocols-model-context": "toolchains-ai-protocols",
}


def _get_user_level_skills() -> frozenset[str]:
    """Return USER_LEVEL_SKILLS, importing lazily to avoid circular imports."""
    try:
        from claude_mpm.services.skills.selective_skill_deployer import (
            USER_LEVEL_SKILLS,
        )

        return USER_LEVEL_SKILLS
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not import USER_LEVEL_SKILLS: %s", exc)
        return frozenset()


def _find_project_roots() -> list[Path]:
    """Return candidate project roots that may have .claude/skills/ directories."""
    candidates: list[Path] = [Path.cwd()]
    try:
        package_dir = Path(__file__).resolve().parent.parent
        for parent in [package_dir] + list(package_dir.parents):
            if (parent / ".git").exists():
                if parent not in candidates:
                    candidates.append(parent)
                break
    except Exception:
        pass
    return candidates


# ---------------------------------------------------------------------------
# Step 1 — Remove mpm-* project-level duplicates
# ---------------------------------------------------------------------------


def _remove_project_level_mpm_skills(
    project_roots: list[Path],
    user_skills_base: Path,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Remove mpm-* directories from project-level .claude/skills/.

    Returns:
        (removed, already_clean, skipped_no_user_copy)
    """
    user_level_skills = _get_user_level_skills()
    mpm_skills = frozenset(s for s in user_level_skills if s.startswith("mpm-"))

    removed = already_clean = skipped_no_user_copy = 0

    for project_root in project_roots:
        project_skills_base = project_root / ".claude" / "skills"
        if not project_skills_base.exists():
            continue

        logger.info("Scanning %s for mpm-* duplicates", project_skills_base)

        for skill_name in sorted(mpm_skills):
            project_skill_dir = project_skills_base / skill_name

            if not project_skill_dir.exists():
                already_clean += 1
                logger.debug("Already clean (no project copy): %s", skill_name)
                continue

            user_skill_file = user_skills_base / skill_name / "SKILL.md"
            if not user_skill_file.exists():
                logger.warning(
                    "Skipping removal of project-level '%s': user-level copy not found at %s",
                    skill_name,
                    user_skill_file,
                )
                skipped_no_user_copy += 1
                continue

            if dry_run:
                print(f"[DRY-RUN] Would remove project-level mpm-* skill: {skill_name}")
                removed += 1
                continue

            try:
                shutil.rmtree(project_skill_dir)
                removed += 1
                logger.info(
                    "Removed project-level mpm-* skill: %s (user copy confirmed)",
                    skill_name,
                )
                print(f"Removed project-level mpm-* skill: {skill_name}")
            except OSError as exc:
                logger.error("Failed to remove %s: %s", project_skill_dir, exc)

    return removed, already_clean, skipped_no_user_copy


# ---------------------------------------------------------------------------
# Step 2 — Rename project-level skills to match plugin directory names
# ---------------------------------------------------------------------------


def _rename_project_level_skills(
    project_roots: list[Path],
    dry_run: bool,
) -> int:
    """Rename project-level skill directories per PROJECT_SKILL_RENAME mapping.

    Returns:
        Number of renames performed (or that would be performed in dry-run).
    """
    renamed = 0

    for project_root in project_roots:
        project_skills_base = project_root / ".claude" / "skills"
        if not project_skills_base.exists():
            continue

        for old_name, new_name in sorted(PROJECT_SKILL_RENAME.items()):
            old_dir = project_skills_base / old_name
            new_dir = project_skills_base / new_name

            if not old_dir.exists():
                logger.debug("Project-level rename source does not exist: %s", old_name)
                continue

            if new_dir.exists():
                logger.info(
                    "Target already exists, skipping rename %s → %s", old_name, new_name
                )
                print(f"Skipped (target exists): {old_name} → {new_name}")
                continue

            if dry_run:
                print(
                    f"[DRY-RUN] Would rename project-level skill: {old_name} → {new_name}"
                )
                renamed += 1
                continue

            try:
                old_dir.rename(new_dir)
                renamed += 1
                logger.info("Renamed project-level skill: %s → %s", old_name, new_name)
                print(f"Renamed project-level skill: {old_name} → {new_name}")
            except OSError as exc:
                logger.error("Failed to rename %s → %s: %s", old_name, new_name, exc)

    return renamed


# ---------------------------------------------------------------------------
# Step 3 — Remove superseded mcp-prefixed skills from user level
# ---------------------------------------------------------------------------


def _remove_user_level_mcp_skills(
    user_skills_base: Path,
    dry_run: bool,
) -> int:
    """Remove old mcp-prefixed skill directories from user-level ~/.claude/skills/
    when the renamed replacement already exists at the same level.

    Returns:
        Number of removals performed (or that would be performed in dry-run).
    """
    removed = 0

    for old_name, new_name in sorted(MCP_SKILL_RENAME.items()):
        old_dir = user_skills_base / old_name
        new_dir = user_skills_base / new_name

        if not old_dir.exists():
            logger.debug("User-level mcp skill already absent: %s", old_name)
            continue

        if not new_dir.exists():
            logger.warning(
                "Skipping removal of user-level '%s': replacement '%s' not found at %s",
                old_name,
                new_name,
                new_dir,
            )
            print(
                f"Skipped (replacement not found): {old_name} → {new_name} at {user_skills_base}"
            )
            continue

        if dry_run:
            print(
                f"[DRY-RUN] Would remove superseded user-level mcp skill: {old_name} "
                f"(replaced by {new_name})"
            )
            removed += 1
            continue

        try:
            shutil.rmtree(old_dir)
            removed += 1
            logger.info(
                "Removed superseded user-level mcp skill: %s (replaced by %s)",
                old_name,
                new_name,
            )
            print(
                f"Removed superseded user-level mcp skill: {old_name} (replaced by {new_name})"
            )
        except OSError as exc:
            logger.error("Failed to remove user-level skill %s: %s", old_dir, exc)

    return removed


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


def migrate_skill_cleanup(dry_run: bool = False) -> bool:
    """Run all skill cleanup steps.

    Args:
        dry_run: If True, print actions without performing them.

    Returns:
        True on success (even if nothing changed), False if an unrecoverable
        error occurred.
    """
    user_skills_base = Path.home() / ".claude" / "skills"
    project_roots = _find_project_roots()

    if dry_run:
        print("=== DRY-RUN MODE: no changes will be made ===")

    print("\n--- Step 1: Remove mpm-* project-level skill duplicates ---")
    removed, already_clean, skipped = _remove_project_level_mpm_skills(
        project_roots, user_skills_base, dry_run
    )
    print(
        f"  removed={removed}, already_clean={already_clean}, "
        f"skipped_no_user_copy={skipped}"
    )

    print("\n--- Step 2: Rename project-level skills to match plugin names ---")
    renamed = _rename_project_level_skills(project_roots, dry_run)
    print(f"  renamed={renamed}")

    print("\n--- Step 3: Remove superseded mcp-prefixed user-level skills ---")
    user_removed = _remove_user_level_mcp_skills(user_skills_base, dry_run)
    print(f"  removed={user_removed}")

    print("\nMigration complete.")
    return True


def run_migration() -> bool:
    """Entry point called by the migration runner (no --dry-run flag)."""
    try:
        return migrate_skill_cleanup(dry_run=False)
    except Exception as exc:
        logger.error("Unexpected error in migrate_skill_cleanup: %s", exc)
        return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Skill naming cleanup migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without making changes",
    )
    args = parser.parse_args()

    success = migrate_skill_cleanup(dry_run=args.dry_run)
    sys.exit(0 if success else 1)
