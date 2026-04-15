"""
Migration: Add color and initialPrompt fields to project agent files (v6.3.2).

Scans .claude/agents/*.md and injects:
- color: based on agent name mapping (idempotent — skip if already set)
- initialPrompt: copied from the source/bundled agent if available

Color mapping:
- engineer, typescript-engineer, python-engineer, etc. → "blue"
- qa, qa-engineer, etc. → "green"
- research, code-analyzer → "purple"
- ops, devops, etc. → "orange"
- documentation, docs → "yellow"
- security → "red"
- default → "blue"

Idempotent — safe to run multiple times. Files with color already set are skipped.
"""

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Color mapping: partial name matches (checked in order, first match wins)
_COLOR_RULES: list[tuple[list[str], str]] = [
    (["qa", "quality"], "green"),
    (["research", "code-analyzer", "analyzer"], "purple"),
    (["ops", "devops", "infrastructure", "platform"], "orange"),
    (["documentation", "docs", "writer"], "yellow"),
    (["security", "sec"], "red"),
    # Engineer variants and default fall through to blue
]

_DEFAULT_COLOR = "blue"


def _resolve_color(stem: str) -> str:
    """Determine color for an agent based on its filename stem.

    Args:
        stem: Filename stem (e.g. "python-engineer", "qa-engineer")

    Returns:
        Color string
    """
    lower = stem.lower()
    for keywords, color in _COLOR_RULES:
        if any(kw in lower for kw in keywords):
            return color
    return _DEFAULT_COLOR


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


def _find_initial_prompt(stem: str, bundled_agents_dir: Path | None) -> str | None:
    """Look up initialPrompt from the source/bundled agent file if available.

    Args:
        stem: Agent filename stem (e.g. "python-engineer")
        bundled_agents_dir: Directory containing bundled agent templates

    Returns:
        initialPrompt value or None if not found
    """
    if bundled_agents_dir is None or not bundled_agents_dir.exists():
        return None

    source_file = bundled_agents_dir / f"{stem}.md"
    if not source_file.exists():
        return None

    try:
        content = source_file.read_text(encoding="utf-8")
        frontmatter, _ = _parse_frontmatter(content)
        if frontmatter and "initialPrompt" in frontmatter:
            return frontmatter["initialPrompt"]
    except OSError as e:
        logger.debug("Could not read source agent %s: %s", source_file, e)

    return None


def migrate_agent_file(
    path: Path,
    bundled_agents_dir: Path | None = None,
    dry_run: bool = False,
) -> bool:
    """Add color (and optionally initialPrompt) to a single agent file.

    Args:
        path: Path to agent .md file
        bundled_agents_dir: Optional path to bundled agent templates for initialPrompt lookup
        dry_run: If True, log what would change without writing

    Returns:
        True if file was (or would be) modified, False if already up to date
    """
    content = path.read_text(encoding="utf-8")
    frontmatter, body = _parse_frontmatter(content)

    if frontmatter is None:
        logger.debug("Skipping %s: no YAML frontmatter", path.name)
        return False

    # Idempotent: skip if color already set
    if "color" in frontmatter:
        logger.debug(
            "Skipping %s: color already set to %r", path.name, frontmatter["color"]
        )
        return False

    color = _resolve_color(path.stem)
    fields_to_add: dict = {"color": color}

    # Add initialPrompt only if found in bundled source
    if "initialPrompt" not in frontmatter:
        initial_prompt = _find_initial_prompt(path.stem, bundled_agents_dir)
        if initial_prompt:
            fields_to_add["initialPrompt"] = initial_prompt

    logger.info("Agent %s: adding fields %s", path.name, list(fields_to_add.keys()))

    if dry_run:
        return True

    backup = _backup_file(path)
    logger.debug("Backup created: %s", backup)

    frontmatter.update(fields_to_add)
    path.write_text(_serialize_frontmatter(frontmatter, body), encoding="utf-8")
    return True


def run_migration(installation_dir: Path | None = None) -> bool:
    """Add color and initialPrompt fields to all project agent files.

    Searches for .claude/agents/*.md in installation_dir (defaults to cwd).
    Color is determined from agent filename. initialPrompt is sourced from
    bundled agent templates when available.

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

    # Locate bundled agents directory for initialPrompt lookup
    bundled_agents_dir = Path(__file__).parent.parent / "agents" / "bundled"
    if not bundled_agents_dir.exists():
        bundled_agents_dir = None
        logger.debug(
            "Bundled agents directory not found; skipping initialPrompt injection"
        )

    updated = 0
    errors = 0

    for agent_file in sorted(agent_files):
        try:
            if migrate_agent_file(agent_file, bundled_agents_dir=bundled_agents_dir):
                updated += 1
        except OSError as e:
            logger.error("Failed to migrate %s: %s", agent_file.name, e)
            errors += 1

    logger.info(
        "Agent color/initialPrompt migration: %d/%d files updated, %d errors",
        updated,
        len(agent_files),
        errors,
    )

    return errors == 0
