"""Migration v6.5.81: Remove MPM-owned agents from ~/.claude/agents/.

WHAT: One-time self-heal migration that removes claude-mpm-owned agent files
from the shared user-level ~/.claude/agents/ directory.

WHY: With Fix A for issue #924, MPM agents now deploy to project-local
.claude/agents/ instead of the shared ~/.claude/agents/. This migration
cleans up stale user-level copies left by prior releases so they no longer
appear in non-MPM Claude Code sessions on the same machine.

Detection: An agent file is considered MPM-owned if its YAML frontmatter
contains any of:
  - author: claude-mpm
  - category: claude-mpm
  - source: external
  - agent_type: claude-mpm
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_MPM_MARKERS = re.compile(
    r"^(author|category|source|agent_type):\s*(claude-mpm|external)\s*$",
    re.MULTILINE,
)
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _is_mpm_owned(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        fm_match = _FRONTMATTER_RE.match(content)
        if not fm_match:
            return False
        return bool(_MPM_MARKERS.search(fm_match.group(1)))
    except OSError:
        return False


def run_migration() -> bool:
    """Remove MPM-owned agent files from ~/.claude/agents/."""
    user_agents_dir = Path.home() / ".claude" / "agents"
    if not user_agents_dir.is_dir():
        logger.info("v6_5_81: ~/.claude/agents/ not found, nothing to clean up")
        return True

    removed = []
    errors = []
    for md_file in user_agents_dir.glob("*.md"):
        if _is_mpm_owned(md_file):
            try:
                md_file.unlink()
                removed.append(md_file.name)
                logger.info(f"v6_5_81: removed user-level agent {md_file.name}")
            except OSError as exc:
                errors.append(str(exc))
                logger.warning(f"v6_5_81: could not remove {md_file}: {exc}")

    logger.info(
        f"v6_5_81: removed {len(removed)} user-level MPM agents"
        f"{', errors: ' + str(len(errors)) if errors else ''}"
    )
    return not errors
