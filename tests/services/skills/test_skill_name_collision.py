"""Regression tests for skill-name / Claude Code reserved-command collisions.

Claude Code resolves slash commands via prefix matching, so a skill whose
``name:`` equals (or starts with) a reserved command such as ``mcp`` will
shadow the built-in ``/mcp`` handler. These tests guard against:

1. Any bundled SKILL.md shipping with a reserved ``name:``.
2. Regressions in ``sanitize_skill_name_for_deployment`` for exact-match,
   prefix-match, and non-colliding names.

References
----------
Issue #931 — MCP skill-collision rename follow-ups.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from claude_mpm.services.skills.selective_skill_deployer import (
    sanitize_skill_name_for_deployment,
)

# Reserved Claude Code slash commands that a skill name must never equal.
RESERVED_COMMANDS = {"mcp", "help", "exit", "clear", "quit"}

# Repository root: tests/services/skills/ -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUNDLED_SKILLS_DIR = _REPO_ROOT / "src" / "claude_mpm" / "skills" / "bundled"

_NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)


def _skill_md_name(skill_md: Path) -> str | None:
    """Return the frontmatter ``name:`` value from a SKILL.md, or None."""
    match = _NAME_RE.search(skill_md.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else None


def test_no_bundled_skill_has_reserved_name() -> None:
    """No bundled SKILL.md may declare a name that collides with a reserved command."""
    skill_files = list(_BUNDLED_SKILLS_DIR.glob("**/SKILL.md"))
    assert skill_files, f"No bundled SKILL.md files found under {_BUNDLED_SKILLS_DIR}"

    offenders = {
        str(skill_md.relative_to(_REPO_ROOT)): name
        for skill_md in skill_files
        if (name := _skill_md_name(skill_md)) in RESERVED_COMMANDS
    }

    assert not offenders, (
        f"Bundled skills collide with reserved Claude Code commands: {offenders}"
    )


def test_sanitize_skill_name_exact_reserved() -> None:
    """A skill named exactly 'mcp' must be renamed to something else."""
    result = sanitize_skill_name_for_deployment("mcp")
    assert result != "mcp"


def test_sanitize_skill_name_prefix_reserved() -> None:
    """A skill named 'mcp-builder' must not keep the reserved 'mcp' prefix."""
    result = sanitize_skill_name_for_deployment("mcp-builder")
    assert not result.startswith("mcp")


def test_sanitize_skill_name_non_colliding_unchanged() -> None:
    """A non-colliding skill name passes through unchanged."""
    assert sanitize_skill_name_for_deployment("my-skill") == "my-skill"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
