"""
Migration: Add Claude Code native agent frontmatter fields (v6.3.0).

Adds permissionMode, maxTurns, and memory fields to .claude/agents/*.md
files that are missing them. Backs up each file before modifying.

Idempotent — safe to run multiple times.
"""

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Fields to add with their defaults when absent
_NATIVE_FIELD_DEFAULTS: dict[str, object] = {
    "permissionMode": "acceptEdits",
    "maxTurns": 50,
    "memory": "project",
}


def _parse_frontmatter(content: str) -> tuple[dict, str] | tuple[None, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full file content

    Returns:
        (frontmatter_dict, body) or (None, original_content) if no frontmatter
    """
    if not content.startswith("---"):
        return None, content

    end = content.find("\n---", 3)
    if end == -1:
        return None, content

    yaml_block = content[3:end].strip()
    body = content[end + 4 :]

    try:
        data = yaml.safe_load(yaml_block) or {}
        return data, body
    except yaml.YAMLError as e:
        logger.warning("Failed to parse frontmatter YAML: %s", e)
        return None, content


def _serialize_frontmatter(data: dict, body: str) -> str:
    """Serialize frontmatter dict back to markdown string.

    Args:
        data: Frontmatter fields
        body: Markdown body after frontmatter

    Returns:
        Full file content with updated frontmatter
    """
    yaml_str = yaml.dump(
        data, default_flow_style=False, allow_unicode=True, sort_keys=False
    )
    return f"---\n{yaml_str}---{body}"


def _backup_file(path: Path) -> Path:
    """Create a timestamped backup of a file.

    Args:
        path: File to back up

    Returns:
        Path to backup file
    """
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".md.bak_{timestamp}")
    shutil.copy2(path, backup)
    return backup


def migrate_agent_file(path: Path, dry_run: bool = False) -> bool:
    """Add missing native Claude Code fields to a single agent file.

    Args:
        path: Path to agent .md file
        dry_run: If True, log what would change without writing

    Returns:
        True if file was (or would be) modified, False if already up to date
    """
    content = path.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(content)

    if frontmatter is None:
        logger.debug("Skipping %s: no YAML frontmatter", path.name)
        return False

    missing = {
        field: default
        for field, default in _NATIVE_FIELD_DEFAULTS.items()
        if field not in frontmatter
    }

    if not missing:
        logger.debug("Skipping %s: all native fields present", path.name)
        return False

    logger.info("Agent %s: adding fields %s", path.name, list(missing.keys()))

    if dry_run:
        return True

    backup = _backup_file(path)
    logger.debug("Backup created: %s", backup)

    frontmatter.update(missing)
    path.write_text(_serialize_frontmatter(frontmatter, body), encoding="utf-8")
    return True


def run_migration(installation_dir: Path | None = None) -> bool:
    """Add native Claude Code frontmatter fields to all project agents.

    Searches for .claude/agents/*.md in installation_dir (defaults to cwd).

    Args:
        installation_dir: Root of the project to migrate (default: cwd)

    Returns:
        True on success (including when no files needed updating)
    """
    project_root = installation_dir or Path.cwd()
    agents_dir = project_root / ".claude" / "agents"

    if not agents_dir.exists():
        logger.info("No .claude/agents/ directory found — nothing to migrate")
        return True

    agent_files = list(agents_dir.glob("*.md"))
    if not agent_files:
        logger.info("No agent .md files found in %s", agents_dir)
        return True

    updated = 0
    errors = 0

    for agent_file in sorted(agent_files):
        try:
            if migrate_agent_file(agent_file):
                updated += 1
        except OSError as e:
            logger.error("Failed to migrate %s: %s", agent_file.name, e)
            errors += 1

    logger.info(
        "Native agent fields migration: %d/%d files updated, %d errors",
        updated,
        len(agent_files),
        errors,
    )

    return errors == 0
