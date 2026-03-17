"""
Centralized environment variable defaults for claude-mpm.

WHY: DISABLE_TELEMETRY and other env vars were scattered across 10+ files,
all hardcoded to "1". This made it impossible to opt-in to telemetry even
if the user explicitly set DISABLE_TELEMETRY=0 in their shell.

This module provides a single source of truth that respects shell env values:
  - If the user has DISABLE_TELEMETRY set in their shell, that value is used.
  - If not set, it defaults to "1" (telemetry disabled).

DESIGN DECISION: Use os.environ.setdefault() pattern for entry points, and
os.environ.get() for subprocess env dicts, so that the user's shell preference
flows all the way down to child processes.

CRITICAL: This module must have ZERO internal claude_mpm imports to avoid
circular imports. It is intentionally importable before any other module.
"""

import os
from typing import Dict

# Registry of env var defaults for claude-mpm.
# Format: {VAR_NAME: default_value}
_ENV_DEFAULTS: Dict[str, str] = {
    "DISABLE_TELEMETRY": "1",
}

# Env vars where the consuming tool checks for existence, not value.
# When the user sets value to "0" (meaning "don't disable"), the var must be
# completely removed from the subprocess env so the tool doesn't see it.
#
# ASSUMPTION: Claude Code (Anthropic CLI) treats DISABLE_TELEMETRY as a
# presence-based flag — if the var exists in the environment (regardless of
# value), telemetry is disabled. Verified as of Claude Code 1.x (2025-2026).
# If this behavior changes in a future Claude Code release, this set should
# be updated accordingly.
_PRESENCE_BASED_VARS: set[str] = {"DISABLE_TELEMETRY"}


def apply_env_defaults() -> None:
    """Apply all env var defaults to os.environ using setdefault.

    This respects any values already set in the shell environment.
    Call once at process startup (entry points only). Idempotent.
    """
    for key, default in _ENV_DEFAULTS.items():
        os.environ.setdefault(key, default)


def get_telemetry_disabled() -> bool:
    """Return True if telemetry is disabled.

    Checks os.environ after defaults have been applied.
    Returns True when DISABLE_TELEMETRY == "1" (the default).
    """
    default = _ENV_DEFAULTS["DISABLE_TELEMETRY"]
    return os.environ.get("DISABLE_TELEMETRY", default) == default


def apply_subprocess_env_defaults(env: Dict[str, str]) -> Dict[str, str]:
    """Apply env var defaults to a subprocess environment dict.

    Uses the current process's resolved value (which respects the shell env
    set before apply_env_defaults() was called), ensuring subprocesses
    inherit the user's preference rather than an unconditional "1".

    For presence-based vars (like DISABLE_TELEMETRY where Claude Code checks
    for existence, not value): when the user sets the value to "0", the var
    is completely removed from the env dict so the subprocess doesn't see it.

    Args:
        env: The subprocess environment dict to update in place.

    Returns:
        The same dict, updated in place (also returned for convenience).
    """
    for key, default in _ENV_DEFAULTS.items():
        # Read from the current process env (already resolved via setdefault
        # at entry point startup), falling back to our default if somehow unset.
        value = os.environ.get(key, default)
        if key in _PRESENCE_BASED_VARS and value == "0":
            # Claude Code checks for EXISTENCE of DISABLE_TELEMETRY, not its value.
            # When user wants telemetry enabled (value="0"), completely remove the var
            # so the subprocess tool doesn't see it at all.
            env.pop(key, None)
        else:
            env[key] = value
    return env
