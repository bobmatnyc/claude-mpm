"""Model-to-context-window resolution for the context circuit breaker.

WHAT: Maps active model identifiers to their real context-window sizes so the
circuit breaker computes context usage as a fraction of the *actual* window
rather than a hardcoded 200 K default.

WHY: Claude Opus 4.x and selected Sonnet 4.x variants ship with a 1 M-token
context window.  Dividing cumulative token counts by a hardcoded 200_000 ceiling
causes those models to report > 100 % usage almost immediately, which fires the
circuit breaker on every tool call — including recovery tools — and makes the
session unrecoverable (GitHub issue #642).

Model-ID resolution order
-------------------------
1. ``ANTHROPIC_MODEL`` environment variable (set by claude-mpm or user).
2. Project ``.claude/settings.local.json`` → ``model`` key.
3. Project ``.claude/settings.json`` → ``model`` key.
4. Global ``~/.claude/settings.json`` → ``model`` key.
5. Conservative default: ``DEFAULT_CONTEXT_WINDOW`` (200_000).

The resolution is intentionally cheap: no heavy imports, no I/O beyond a
small JSON settings read.  It is called from the PreToolUse hot path.

Extending the map
-----------------
Add entries to ``CONTEXT_WINDOW_MAP`` using the *model id prefix* as the key
(everything before the date suffix / patch version).  Exact ids are matched
first; prefix matching handles versioned variants automatically.

    CONTEXT_WINDOW_MAP["claude-new-model-X-Y"] = 2_000_000
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Context-window map
# ---------------------------------------------------------------------------

# Default for unknown / legacy models (conservative so the breaker can still
# fire on genuine 200K models even when the model is not in the map).
DEFAULT_CONTEXT_WINDOW: Final[int] = 200_000

# 1 M-token context window (Opus 4.x and large-context Sonnet variants).
_1M: Final[int] = 1_000_000

# Map of model-id prefix -> context window in tokens.
# Keys are lowercase, no trailing date/version suffix.
# Ordering: more-specific keys must come before generic ones — Python dicts
# are insertion-ordered (Python 3.7+), and the resolver iterates top-to-bottom.
CONTEXT_WINDOW_MAP: dict[str, int] = {
    # -----------------------------------------------------------------------
    # Opus 4.x — 1 M context window
    # -----------------------------------------------------------------------
    "claude-opus-4": _1M,
    # -----------------------------------------------------------------------
    # Sonnet 4.x — 1 M context window for 4.5+ variants
    # -----------------------------------------------------------------------
    "claude-sonnet-4-5": _1M,
    "claude-sonnet-4-6": _1M,
    "claude-sonnet-4-7": _1M,
    # Sonnet 4.0 / 4.1 / 4.4 remain at 200 K
    "claude-sonnet-4": DEFAULT_CONTEXT_WINDOW,
    # -----------------------------------------------------------------------
    # Haiku 4.x — 200 K context window (may be updated as announced)
    # -----------------------------------------------------------------------
    "claude-haiku-4": DEFAULT_CONTEXT_WINDOW,
    # -----------------------------------------------------------------------
    # Claude 3.x — 200 K context window
    # -----------------------------------------------------------------------
    "claude-3-7-sonnet": DEFAULT_CONTEXT_WINDOW,
    "claude-3-5-sonnet": DEFAULT_CONTEXT_WINDOW,
    "claude-3-5-haiku": DEFAULT_CONTEXT_WINDOW,
    "claude-3-opus": DEFAULT_CONTEXT_WINDOW,
    "claude-3-sonnet": DEFAULT_CONTEXT_WINDOW,
    "claude-3-haiku": DEFAULT_CONTEXT_WINDOW,
    # -----------------------------------------------------------------------
    # Short aliases (used in settings.json / ANTHROPIC_MODEL)
    # -----------------------------------------------------------------------
    "opus": _1M,  # bare alias assumed to refer to the latest Opus (1 M)
    "sonnet": DEFAULT_CONTEXT_WINDOW,
    "haiku": DEFAULT_CONTEXT_WINDOW,
}


def resolve_context_window(model_id: str | None = None) -> int:
    """Return the context-window size (in tokens) for *model_id*.

    Falls back to ``DEFAULT_CONTEXT_WINDOW`` when the model is unknown.

    Args:
        model_id: Raw model identifier (e.g. ``"claude-opus-4-6-20260101"``).
            Pass ``None`` to trigger env-var / settings-file resolution.

    Returns:
        Integer token count for the model's context window.
    """
    if model_id is None:
        model_id = _detect_active_model()

    if not model_id:
        return DEFAULT_CONTEXT_WINDOW

    lower = model_id.lower().strip()

    # 1. Exact match (fastest path for known identifiers).
    if lower in CONTEXT_WINDOW_MAP:
        return CONTEXT_WINDOW_MAP[lower]

    # 2. Prefix match — handles dated variants like "claude-opus-4-6-20260101".
    # Require a delimiter boundary ("-") after the prefix so that a future
    # "claude-sonnet-4-50" does not accidentally match "claude-sonnet-4-5"
    # (1 M window).  We match only when lower == prefix (already handled above
    # by the exact-match branch, kept here as a safety net) or when the next
    # character after the prefix is "-".
    for prefix, window in CONTEXT_WINDOW_MAP.items():
        if lower == prefix or lower.startswith(prefix + "-"):
            return window

    # 3. Unknown model — return conservative default.
    return DEFAULT_CONTEXT_WINDOW


def _detect_active_model() -> str | None:
    """Probe env vars and Claude settings files for the active model id.

    Returns the first non-empty model string found, or ``None`` when nothing
    is configured.
    """
    # 1. ANTHROPIC_MODEL env var (highest priority — set by claude-mpm config).
    env_model = os.environ.get("ANTHROPIC_MODEL", "").strip()
    if env_model:
        return env_model

    # 2. CLAUDE_MODEL env var (secondary env-based override).
    env_model2 = os.environ.get("CLAUDE_MODEL", "").strip()
    if env_model2:
        return env_model2

    # 3-5. Claude settings files (project-local first, then global).
    cwd = os.environ.get("CLAUDE_HOOK_CWD", "") or str(Path.cwd())
    settings_paths = [
        Path(cwd) / ".claude" / "settings.local.json",
        Path(cwd) / ".claude" / "settings.json",
        Path.home() / ".claude" / "settings.json",
    ]
    for settings_path in settings_paths:
        try:
            if settings_path.is_file():
                with settings_path.open(encoding="utf-8") as fh:
                    data = json.load(fh)
                model_val = str(data.get("model", "")).strip()
                if model_val:
                    return model_val
        except (OSError, json.JSONDecodeError, ValueError):
            continue

    return None
