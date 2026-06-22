"""Shared footer string constants for Claude Code → Claude MPM attribution rewriting.

WHAT: Single source of truth for the old Claude Code footer patterns that need
      replacing and the canonical Claude MPM footer that replaces them.
WHY:  These strings are used in three distinct places — startup_migrations.py
      (agent-file rewrite), gh_footer_hook.py (live PR/issue body rewrite), and
      the PR template service.  Keeping them in one module prevents drift where a
      URL changes in one place but not another.

References
----------
LINK: none  (shared-constants helper, no governing spec yet)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Old Claude Code footer patterns (both URL variants; neither has the emoji)
# ---------------------------------------------------------------------------
# The Claude Code CLI injects one of these two URL forms depending on version:
#   - https://claude.ai/code   (older / canonical)
#   - https://claude.com/claude-code  (newer alias)
# Both must be matched to achieve full coverage.
#
# NOTE: Claude Code also prepends "🤖 " (robot emoji + space) in interactive
# sessions, but the bare form (no emoji) appears in non-interactive / scripted
# usage.  We therefore define both the bare strings (no emoji) — the match
# logic in gh_footer_hook normalises by stripping the emoji prefix.
CLAUDE_CODE_FOOTER_OLD = "Generated with [Claude Code](https://claude.ai/code)"
CLAUDE_CODE_FOOTER_OLD_ALT = (
    "Generated with [Claude Code](https://claude.com/claude-code)"
)

# ---------------------------------------------------------------------------
# Canonical Claude MPM footer (with emoji)
# ---------------------------------------------------------------------------
MPM_FOOTER_CANONICAL = (
    "🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)"
)
