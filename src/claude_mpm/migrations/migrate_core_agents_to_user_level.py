"""Migration 6.2.0: Move CORE agents to user level, remove project-level duplicates.

WHY: Agents in USER_LEVEL_AGENTS (CORE engineering specialists, PM, QA, ops, etc.)
should live at ~/.claude/agents/ and be shared across all projects.
Having copies in .claude/agents/ (project level) creates duplicates and confusion.

WHAT THIS MIGRATION DOES:
1. Iterates over every agent in USER_LEVEL_AGENTS.
2. For each agent, verifies it exists at ~/.claude/agents/{agent}.md.
3. Only if the user-level copy is confirmed present, removes the project-level
   copy at .claude/agents/{agent}.md.
4. Skips agents that are absent from user level (safe: never deletes blindly).
5. Records the list of removed agents in the return value for reporting.

IDEMPOTENCY: Running this migration multiple times is safe — if the project-level
file no longer exists the migration simply skips it.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Import the canonical user-level agents set.  Imported lazily inside the
# run function to avoid circular-import issues at module load time.


def _get_user_level_agents() -> frozenset[str]:
    """Return USER_LEVEL_AGENTS, importing lazily to avoid circular imports."""
    from claude_mpm.services.agents.deployment.agent_deployment import (
        USER_LEVEL_AGENTS,
    )

    return USER_LEVEL_AGENTS


def _find_project_roots() -> list[Path]:
    """Return candidate project roots that may have .claude/agents/ directories.

    Searches from the current working directory upward to find git-rooted
    projects, then returns the cwd (which is the project being migrated).
    In practice the migration runner calls run() from a specific project
    context so cwd is sufficient.

    Returns:
        List of Path objects to check for .claude/agents/ presence.
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


def migrate_core_agents_to_user_level() -> bool:
    """Remove project-level copies of USER_LEVEL_AGENTS agents.

    For each agent in USER_LEVEL_AGENTS:
    - Verify the user-level copy at ~/.claude/agents/{agent}.md exists.
    - Remove the project-level file .claude/agents/{agent}.md only when the
      user-level copy is confirmed present (idempotent and non-destructive).

    Returns:
        True on success (even if nothing was removed), False if an unrecoverable
        error occurred.
    """
    user_level_agents = _get_user_level_agents()
    user_agents_base = Path.home() / ".claude" / "agents"

    project_roots = _find_project_roots()
    any_error = False
    total_removed = 0
    total_skipped_no_user_copy = 0
    total_already_clean = 0

    for project_root in project_roots:
        project_agents_base = project_root / ".claude" / "agents"

        if not project_agents_base.exists():
            logger.debug(
                "No project-level agents directory at %s, skipping", project_agents_base
            )
            continue

        logger.info(
            "Scanning project-level agents at %s for USER_LEVEL_AGENTS duplicates",
            project_agents_base,
        )

        for agent_name in sorted(user_level_agents):
            project_agent_file = project_agents_base / f"{agent_name}.md"

            # Nothing to do if project-level copy doesn't exist
            if not project_agent_file.exists():
                total_already_clean += 1
                logger.debug("Already clean (no project copy): %s", agent_name)
                continue

            # Verify user-level copy exists before removing project copy
            user_agent_file = user_agents_base / f"{agent_name}.md"
            if not user_agent_file.exists():
                logger.warning(
                    "Skipping removal of project-level '%s': user-level copy not found at %s",
                    agent_name,
                    user_agent_file,
                )
                total_skipped_no_user_copy += 1
                continue

            # Safe to remove the project-level file
            try:
                project_agent_file.unlink()
                total_removed += 1
                logger.info(
                    "Removed project-level duplicate agent: %s (user copy confirmed at %s)",
                    agent_name,
                    user_agent_file,
                )
            except OSError as exc:
                logger.error(
                    "Failed to remove project-level agent file %s: %s",
                    project_agent_file,
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
        return migrate_core_agents_to_user_level()
    except Exception as exc:
        logger.error("Unexpected error in migrate_core_agents_to_user_level: %s", exc)
        return False
