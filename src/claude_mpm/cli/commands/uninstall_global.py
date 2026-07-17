"""Global ``~/.claude/`` artifact cleanup for ``claude-mpm uninstall``.

WHY: claude-mpm historically wrote agent templates, output-styles, a statusline
script, and several ``settings.json`` keys into the shared, cross-project
``~/.claude/`` namespace. Those artifacts leak into every Claude Code session on
the machine and break other harnesses (issue #924). This module provides a clean
removal path for every MPM-owned global artifact.

DESIGN DECISIONS:
- Ownership is detected by markers (frontmatter fields, filename prefixes, script
  marker comments, settings key names/values), never by assuming MPM owns a whole
  file — user-authored entries are always left alone.
- Agent frontmatter is matched with a regex rather than a full YAML parse, so a
  malformed or exotic agent file can never crash the cleanup.
- Everything supports ``dry_run`` so ``--dry-run`` can preview without touching
  the filesystem.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Spinner keys mirror src/claude_mpm/cli/startup_migrations.py::_SPINNER_GLOBAL_KEYS.
_SPINNER_KEYS: tuple[str, ...] = (
    "spinnerVerbs",
    "spinnerTipsEnabled",
    "spinnerTipsOverride",
)
_SPINNER_VERSION_KEY = "_mpm_spinner_version"

# Marker comment written into MPM-managed statusline.sh scripts.
_STATUSLINE_MARKER = "# claude-mpm-managed:"
# Substring that identifies an MPM-owned statusLine command / Stop hook.
_STATUSLINE_MATCH = "statusline.sh"

# Frontmatter markers identifying an MPM-owned agent .md file. Matched against the
# YAML frontmatter block only, line-anchored, allowing optional quotes.
_AGENT_MARKER_RE = re.compile(
    r"^(?:author|category):\s*[\"']?claude-mpm[\"']?\s*$"
    r"|^source:\s*[\"']?external[\"']?\s*$",
    re.MULTILINE,
)


@dataclass
class CleanupSummary:
    """Accumulates what a cleanup pass removed (or would remove in dry-run)."""

    removed_files: list[str] = field(default_factory=list)
    settings_keys: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total(self) -> int:
        return len(self.removed_files) + len(self.settings_keys)


def _extract_frontmatter(text: str) -> str:
    """Return the YAML frontmatter block (between leading ``---`` fences) or "".

    Uses a regex rather than a YAML parser so malformed files never raise.
    """
    if not text.startswith("---"):
        return ""
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.DOTALL)
    return match.group(1) if match else ""


def _is_mpm_agent(path: Path) -> bool:
    """True if ``path`` is an MPM-owned agent file (by frontmatter marker)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    frontmatter = _extract_frontmatter(text)
    if not frontmatter:
        return False
    return bool(_AGENT_MARKER_RE.search(frontmatter))


def _remove_agents(claude_dir: Path, summary: CleanupSummary) -> None:
    """Remove ``~/.claude/agents/*.md`` files with MPM ownership markers."""
    agents_dir = claude_dir / "agents"
    if not agents_dir.is_dir():
        return
    for path in sorted(agents_dir.glob("*.md")):
        if _is_mpm_agent(path):
            summary.removed_files.append(str(path))
            if not summary.dry_run:
                path.unlink(missing_ok=True)


def _remove_output_styles(claude_dir: Path, summary: CleanupSummary) -> None:
    """Remove ``~/.claude/output-styles/claude-mpm*.md`` files."""
    styles_dir = claude_dir / "output-styles"
    if not styles_dir.is_dir():
        return
    for path in sorted(styles_dir.glob("claude-mpm*.md")):
        summary.removed_files.append(str(path))
        if not summary.dry_run:
            path.unlink(missing_ok=True)


def _remove_statusline_script(claude_dir: Path, summary: CleanupSummary) -> None:
    """Remove ``~/.claude/hooks/scripts/statusline.sh`` if MPM-managed."""
    script = claude_dir / "hooks" / "scripts" / "statusline.sh"
    if not script.is_file():
        return
    try:
        if _STATUSLINE_MARKER not in script.read_text(encoding="utf-8"):
            return
    except OSError:
        return
    summary.removed_files.append(str(script))
    if not summary.dry_run:
        script.unlink(missing_ok=True)


def _clean_settings(claude_dir: Path, summary: CleanupSummary) -> None:
    """Strip MPM-owned keys from ``~/.claude/settings.json``."""
    settings_path = claude_dir / "settings.json"
    if not settings_path.is_file():
        return
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(data, dict):
        return

    changed = False

    # outputStyle: remove only MPM-owned values.
    value = data.get("outputStyle")
    if isinstance(value, str) and value.startswith("claude_mpm"):
        summary.settings_keys.append("outputStyle")
        changed = True
        if not summary.dry_run:
            del data["outputStyle"]

    # statusLine: remove only when it points at statusline.sh.
    status_line = data.get("statusLine")
    if isinstance(status_line, dict) and _STATUSLINE_MATCH in str(
        status_line.get("command", "")
    ):
        summary.settings_keys.append("statusLine")
        changed = True
        if not summary.dry_run:
            del data["statusLine"]

    # Spinner keys + version stamp.
    for key in (*_SPINNER_KEYS, _SPINNER_VERSION_KEY):
        if key in data:
            summary.settings_keys.append(key)
            changed = True
            if not summary.dry_run:
                del data[key]

    # Stop hooks mentioning statusline.sh (prune emptied groups).
    hooks = data.get("hooks")
    if isinstance(hooks, dict) and isinstance(hooks.get("Stop"), list):
        stop_groups = hooks["Stop"]
        surviving: list = []
        removed_any = False
        for group in stop_groups:
            if isinstance(group, dict) and isinstance(group.get("hooks"), list):
                kept = [
                    hook
                    for hook in group["hooks"]
                    if not (
                        isinstance(hook, dict)
                        and _STATUSLINE_MATCH in str(hook.get("command", ""))
                    )
                ]
                if len(kept) != len(group["hooks"]):
                    removed_any = True
                    if not summary.dry_run:
                        group["hooks"] = kept
                if not kept:
                    continue
            surviving.append(group)
        if removed_any:
            summary.settings_keys.append("hooks.Stop[statusline.sh]")
            changed = True
            if not summary.dry_run:
                if surviving:
                    hooks["Stop"] = surviving
                else:
                    del hooks["Stop"]
                if not hooks:
                    del data["hooks"]

    if changed and not summary.dry_run:
        settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run_global_cleanup(
    claude_dir: Path | None = None, dry_run: bool = False
) -> CleanupSummary:
    """Remove all MPM-owned artifacts from the global ``~/.claude/`` directory.

    Args:
        claude_dir: Root of the global Claude directory. Defaults to
            ``~/.claude``. Injectable for testing.
        dry_run: When True, report what would be removed without changing disk.

    Returns:
        A :class:`CleanupSummary` describing the removed files and settings keys.
    """
    claude_dir = claude_dir or (Path.home() / ".claude")
    summary = CleanupSummary(dry_run=dry_run)
    _remove_agents(claude_dir, summary)
    _remove_output_styles(claude_dir, summary)
    _remove_statusline_script(claude_dir, summary)
    _clean_settings(claude_dir, summary)
    return summary
