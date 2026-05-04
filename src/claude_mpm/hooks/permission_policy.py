"""Permission decision engine for the PermissionRequest hook.

Claude Code emits ``PermissionRequest`` events when a tool invocation needs an
explicit policy decision. The hook dispatcher routes these events to
``model_tier_hook.py`` (configured in ``.claude/settings.json``), which delegates
the actual policy logic to this module.

Design goals
------------
* **Fail open by default** — unknown tools return ``allow`` so the current
  behavior (issue #421: unconditional approve) is preserved as the safety net
  when no specific policy applies.
* **Explicit deny lists** — clearly destructive Bash invocations (``rm -rf /``,
  ``sudo rm``, fork-bomb patterns, etc.) are denied with a reason.
* **Cheap allowlist** — read-only / navigation tools (``Read``, ``Glob``,
  ``Grep``, ``WebSearch``, ``WebFetch``, ``TodoRead``, ``TodoWrite``,
  ``NotebookRead``, ``LS``) are explicitly approved without further inspection.
* **Tier-aware deny** — when the event payload carries an ``agent_id`` /
  ``subagent_type`` the engine consults a per-tier blocklist (e.g. read-only
  agents cannot invoke ``Edit`` / ``Write`` / ``MultiEdit``).

The policy intentionally returns simple ``PermissionDecision`` dataclasses
rather than the wire format. ``model_tier_hook.py`` is responsible for
rendering the JSON envelope expected by Claude Code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final

# ---------------------------------------------------------------------------
# Decision dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermissionDecision:
    """Result of evaluating a PermissionRequest payload.

    Attributes:
        decision: One of ``"allow"``, ``"deny"``, ``"ask"``. Mirrors the
            ``permissionDecision`` field expected by Claude Code's
            ``hookSpecificOutput`` envelope.
        reason: Human-readable explanation. Surfaced to the user when the
            harness denies / asks; logged for observability when allowed.
    """

    decision: str
    reason: str = ""


# ---------------------------------------------------------------------------
# Tool classification
# ---------------------------------------------------------------------------

# Read-only / navigation tools — always safe to approve.
SAFE_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "Read",
        "Glob",
        "Grep",
        "WebSearch",
        "WebFetch",
        "TodoRead",
        "TodoWrite",
        "NotebookRead",
        "LS",
    }
)

# Mutating tools — denied for read-only agent tiers (see ``READ_ONLY_TIERS``).
MUTATING_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "Edit",
        "Write",
        "MultiEdit",
        "NotebookEdit",
    }
)

# Agent tiers that must not perform mutations regardless of tool allowlists.
READ_ONLY_TIERS: Final[frozenset[str]] = frozenset(
    {
        "research",
        "qa",
        "documentation-reviewer",
        "code-reviewer",
        "ticketing",
    }
)

# Patterns that mark a Bash command as clearly destructive. The matcher is
# deliberately conservative — false positives are preferable to silently
# allowing a `rm -rf /` from a misbehaving agent.
DESTRUCTIVE_BASH_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\brm\s+-[a-zA-Z]*[rRfF][a-zA-Z]*\s+/(?:\s|$)"),  # rm -rf /
    re.compile(r"\brm\s+-[a-zA-Z]*[rRfF][a-zA-Z]*\s+/\*"),  # rm -rf /*
    re.compile(r"\bsudo\s+rm\b"),  # sudo rm <anything>
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:"),  # classic fork bomb
    re.compile(r"\bmkfs(\.\w+)?\b"),  # mkfs / mkfs.ext4 / ...
    re.compile(r"\bdd\s+if=.*\s+of=/dev/(sd|nvme|hd|xvd)"),  # dd to raw disk
    re.compile(r">\s*/dev/sd[a-z]"),  # redirect into raw disk
    re.compile(r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b"),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate(event: dict[str, Any]) -> PermissionDecision:
    """Evaluate a PermissionRequest payload and return a decision.

    The function is pure and side-effect free, which keeps it cheap to unit
    test. ``model_tier_hook.py`` is responsible for stdin parsing, JSON
    serialization, and emitting the result on stdout.

    Decision order (first match wins):
        1. Tool is in the explicit safe allowlist → ``allow``.
        2. Tool is a mutator and the requesting agent tier is read-only → ``deny``.
        3. Tool is ``Bash`` and the command matches a destructive pattern → ``deny``.
        4. Default → ``allow`` (fail open, preserves prior behavior).

    Args:
        event: The raw hook payload from Claude Code. The function reads
            ``tool_name``, ``tool_input`` (a dict), and any agent identifier
            fields (``agent_id``, ``subagent_type``, ``agent_type``) without
            assuming a specific schema version.

    Returns:
        :class:`PermissionDecision` describing the policy outcome.
    """
    tool_name = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    # 1. Safe-tool allowlist — short-circuit before any further inspection.
    if tool_name in SAFE_TOOLS:
        return PermissionDecision(
            decision="allow",
            reason=f"{tool_name} is in the safe-tool allowlist",
        )

    # 2. Read-only agent tier cannot perform mutations.
    agent_tier = _extract_agent_tier(event)
    if (
        tool_name in MUTATING_TOOLS
        and agent_tier is not None
        and agent_tier in READ_ONLY_TIERS
    ):
        return PermissionDecision(
            decision="deny",
            reason=(
                f"Agent tier {agent_tier!r} is read-only; "
                f"{tool_name} is a mutating tool"
            ),
        )

    # 3. Destructive Bash invocations.
    if tool_name == "Bash":
        command = str(tool_input.get("command") or "")
        matched = _match_destructive_pattern(command)
        if matched is not None:
            return PermissionDecision(
                decision="deny",
                reason=f"Bash command matches destructive pattern: {matched}",
            )

    # 4. Default — fail open to preserve existing behavior (#421).
    return PermissionDecision(
        decision="allow",
        reason="No explicit policy matched; defaulting to allow",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_agent_tier(event: dict[str, Any]) -> str | None:
    """Pull the agent identifier from the hook payload.

    Claude Code has shifted the field name across releases, so we accept any
    of ``agent_id`` / ``subagent_type`` / ``agent_type`` and normalise the
    value (lowercase, ``_`` → ``-``). Returns ``None`` when none are present
    so callers can distinguish "no tier info" from "empty tier".
    """
    for key in ("agent_id", "subagent_type", "agent_type"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower().replace("_", "-")
    return None


def _match_destructive_pattern(command: str) -> str | None:
    """Return the offending pattern source if ``command`` is destructive."""
    if not command:
        return None
    for pattern in DESTRUCTIVE_BASH_PATTERNS:
        if pattern.search(command):
            return pattern.pattern
    return None
