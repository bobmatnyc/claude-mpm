"""
Migration: Create .claude/commands/ directory with default templates (v6.3.0).

Creates .claude/commands/ if it does not exist and writes default slash command
templates (release.md, test.md, agent-list.md). Skips files that already exist
so the migration is idempotent.

Template content is loaded from the installed package via importlib.resources
rather than being embedded as string literals.
"""

import logging
from importlib.resources import files
from pathlib import Path

logger = logging.getLogger(__name__)

# Command template filenames to deploy from templates/claude/commands/
_COMMAND_FILENAMES: list[str] = [
    "release.md",
    "test.md",
    "agent-list.md",
]


def run_migration(installation_dir: Path | None = None) -> bool:
    """Create .claude/commands/ and populate with default command templates.

    Args:
        installation_dir: Root of the project (default: cwd)

    Returns:
        True on success
    """
    project_root = installation_dir or Path.cwd()
    commands_dir = project_root / ".claude" / "commands"

    created_dir = False
    if not commands_dir.exists():
        commands_dir.mkdir(parents=True)
        created_dir = True
        logger.info("Created directory: %s", commands_dir)

    written = 0
    skipped = 0

    for filename in _COMMAND_FILENAMES:
        target = commands_dir / filename
        if target.exists():
            logger.debug("Skipping %s: already exists", filename)
            skipped += 1
            continue

        content = (
            files("claude_mpm") / "templates" / "claude" / "commands" / filename
        ).read_text(encoding="utf-8")
        target.write_text(content, encoding="utf-8")
        logger.info("Created command template: %s", filename)
        written += 1

    logger.info(
        "Commands migration: dir=%s, written=%d, skipped=%d",
        "created" if created_dir else "existed",
        written,
        skipped,
    )

    return True
