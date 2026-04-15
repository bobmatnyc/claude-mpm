"""
Migration: Inject color field into project agent frontmatter (v6.3.2).

Scans .claude/agents/*.md and adds a `color:` field to the YAML frontmatter
based on agent name patterns if the field is not already present.

Color mapping:
  green  — qa, web-qa, api-qa, *-qa* (quality assurance agents)
  purple — research, code-analyzer (analysis and research agents)
  orange — ops, local-ops, vercel-ops, *-ops* (operations agents)
  yellow — documentation (docs agents)
  red    — security (security agents)
  blue   — default (engineer, python-engineer, and all others)

Idempotent: agents that already have a `color:` field are left unchanged.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Pattern → color.  Order matters: more specific patterns first.
_COLOR_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|-)(qa)(-|$)"), "green"),  # qa, web-qa, api-qa, *-qa*
    (re.compile(r"^(research|code-analyzer)$"), "purple"),
    (re.compile(r"(^|-)(ops)(-|$)"), "orange"),  # ops, local-ops, vercel-ops, *-ops*
    (re.compile(r"^documentation$"), "yellow"),
    (re.compile(r"^security$"), "red"),
]
_DEFAULT_COLOR = "blue"


def _color_for_agent(name: str) -> str:
    """Return the color string for a given agent name."""
    for pattern, color in _COLOR_RULES:
        if pattern.search(name):
            return color
    return _DEFAULT_COLOR


def _inject_color(content: str, agent_name: str) -> tuple[str, bool]:
    """Inject color into YAML frontmatter if not already present.

    Args:
        content: Full file content.
        agent_name: Agent name (used for color lookup).

    Returns:
        Tuple of (new_content, was_modified).
    """
    if not content.startswith("---"):
        # No frontmatter — nothing to do.
        return content, False

    # Match ---\n<yaml>\n---\n<body>
    match = re.match(r"^(---\n)(.*?)(\n---\n)(.*)", content, re.DOTALL)
    if not match:
        return content, False

    open_fence, yaml_block, close_fence, body = match.groups()

    # Already has a color field?
    if re.search(r"^color\s*:", yaml_block, re.MULTILINE):
        return content, False

    # Determine the color to inject.
    color = _color_for_agent(agent_name)

    # Append color at the end of the YAML block.
    new_yaml = yaml_block.rstrip("\n") + f"\ncolor: {color}"
    new_content = open_fence + new_yaml + close_fence + body
    return new_content, True


def run_migration(installation_dir: Path | None = None) -> bool:
    """Inject color field into project agent frontmatter.

    Args:
        installation_dir: Root of the project (default: cwd).

    Returns:
        True on success (even if no agents were modified).
    """
    project_root = installation_dir or Path.cwd()
    agents_dir = project_root / ".claude" / "agents"

    if not agents_dir.exists():
        logger.debug("No agents directory found at %s — skipping", agents_dir)
        return True

    modified = 0
    skipped = 0

    for agent_file in sorted(agents_dir.glob("*.md")):
        try:
            content = agent_file.read_text(encoding="utf-8")
            agent_name = agent_file.stem
            new_content, changed = _inject_color(content, agent_name)
            if changed:
                agent_file.write_text(new_content, encoding="utf-8")
                logger.info(
                    "Injected color '%s' into %s",
                    _color_for_agent(agent_name),
                    agent_file.name,
                )
                modified += 1
            else:
                skipped += 1
        except Exception:
            logger.exception("Failed to process agent file %s", agent_file)

    logger.info(
        "Agent color migration complete: %d modified, %d skipped", modified, skipped
    )
    return True
