"""Migration: remove deployed BASE composition templates from agent directories.

WHY: ``BASE-*.md`` and ``BASE_*.md`` files are composition templates that are
composed INTO agent prompts by the assembly pipeline.  They are NOT stand-alone
Claude Code agents.  A previous deployment bug caused them to be written into
``~/.claude/agents/`` and ``.claude/agents/``, where Claude Code tries to parse
them as agents and fails with "Missing required 'description' field" errors.

WHAT: Scans the user-level (``~/.claude/agents/``) and project-level
(``.claude/agents/`` relative to ``cwd()``) agent directories and removes any
file whose name matches the BASE template pattern via :func:`is_base_template`.

HOW TO TEST: Create a temporary ``.claude/agents/`` directory, drop in
``BASE-ENGINEER.md``, ``BASE_QA.md``, and ``engineer.md``.  Run this migration
and assert that only ``engineer.md`` remains.

References
----------
Issue: BASE-*.md templates deployed as agents causing parse errors
"""

import logging
from pathlib import Path

from claude_mpm.utils.agent_filters import is_base_template

logger = logging.getLogger(__name__)


def _remove_base_templates_from_dir(agents_dir: Path) -> list[str]:
    """Remove BASE composition templates from a single agent directory.

    WHY: Scans for and deletes any stray BASE-*/BASE_* files that were
    incorrectly deployed as agents.

    WHAT: Iterates over ``*.md`` files in *agents_dir* and unlinks those
    that match :func:`is_base_template`.

    TEST: Pass a ``tmp_path / ".claude" / "agents"`` directory containing
    ``BASE-ENGINEER.md`` and ``engineer.md``; assert only ``engineer.md``
    remains and the function returns ``["BASE-ENGINEER.md"]``.

    Args:
        agents_dir: Path to the agents deployment directory to scan.

    Returns:
        List of filenames that were removed.
    """
    removed: list[str] = []

    if not agents_dir.exists():
        logger.debug("Skipping non-existent directory: %s", agents_dir)
        return removed

    for md_file in agents_dir.glob("*.md"):
        if is_base_template(md_file.name):
            try:
                md_file.unlink()
                removed.append(md_file.name)
                logger.info("Removed stray BASE template: %s", md_file)
            except OSError as exc:
                logger.warning("Could not remove %s: %s", md_file, exc)

    return removed


def run_migration() -> bool:
    """Remove any BASE-*.md / BASE_*.md files from deployed agent directories.

    WHY: Ensures the one-shot cleanup runs on startup for every installation
    that was affected by the deployment bug.

    WHAT: Checks both ``~/.claude/agents/`` (user-level) and
    ``.claude/agents/`` relative to the current working directory
    (project-level) for stray BASE template files and removes them.

    Returns:
        Always ``True`` — the migration is idempotent: if no BASE files are
        present the function is a no-op and still succeeds.

    TEST: Run on a clean environment (no BASE files anywhere); assert it
    returns ``True`` without raising.
    """
    scan_dirs: list[Path] = [
        Path.home() / ".claude" / "agents",
        Path.cwd() / ".claude" / "agents",
    ]

    total_removed: list[str] = []

    for agents_dir in scan_dirs:
        removed = _remove_base_templates_from_dir(agents_dir)
        if removed:
            total_removed.extend(removed)
            logger.info(
                "Removed %d BASE template(s) from %s: %s",
                len(removed),
                agents_dir,
                ", ".join(removed),
            )

    if total_removed:
        logger.info(
            "Migration complete: removed %d stray BASE template file(s) total.",
            len(total_removed),
        )
    else:
        logger.debug(
            "Migration complete: no stray BASE template files found — nothing to do."
        )

    # Always return True: idempotent success whether files were present or not.
    return True
