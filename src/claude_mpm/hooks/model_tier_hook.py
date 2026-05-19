#!/usr/bin/env python3
"""PreToolUse + PermissionRequest hook dispatcher.

This module is referenced from ``.claude/settings.json`` for two distinct
events:

* ``PreToolUse`` (matcher ``Agent``) — injects a default model into Agent
  tool calls because Claude Code ignores agent frontmatter ``model:`` fields
  (upstream issue anthropics/claude-code#44385).
* ``PermissionRequest`` (matcher ``*``) — runs the policy engine in
  :mod:`claude_mpm.hooks.permission_policy` and emits a real allow/deny
  decision instead of the previous unconditional approve (issue #421).

Routing is decided from the ``hook_event_name`` field in the JSON payload so
that one entrypoint can serve both hook types without changing settings.
"""

import json
import re
import sys
from pathlib import Path

from claude_mpm.hooks import permission_policy
from claude_mpm.utils.agent_filters import normalize_agent_id

# Agent type -> model mapping (fallback when frontmatter unavailable)
_HAIKU_AGENTS: frozenset[str] = frozenset(
    {
        "ops",
        "local-ops",
        "vercel-ops",
        "gcp-ops",
        "clerk-ops",
        "documentation",
        "ticketing",
        "version-control",
        "project-organizer",
        "memory-manager",
        "memory-manager-agent",
        "tmux-agent",
        "tmux",
        "content-agent",
        "content",
        "imagemagick",
        "agentic-coder-optimizer",
        "mpm-agent-manager",
        "mpm-skills-manager",
        "base",
    }
)

# Coding / engineering agents default to claude-opus-4-6 for stronger code quality.
_OPUS_AGENTS: frozenset[str] = frozenset(
    {
        "engineer",
        "python-engineer",
        "typescript-engineer",
        "react-engineer",
        "nextjs-engineer",
        "svelte-engineer",
        "rust-engineer",
        "golang-engineer",
        "java-engineer",
        "php-engineer",
        "ruby-engineer",
        "dart-engineer",
        "nestjs-engineer",
        "tauri-engineer",
        "javascript-engineer",
        "phoenix-engineer",
        "visual-basic-engineer",
        "data-engineer",
        "refactoring-engineer",
    }
)

# Explicit model IDs so Claude Code routes to the intended tier rather than
# resolving bare "sonnet"/"opus" aliases that can drift over time.
_DEFAULT_MODEL = "claude-sonnet-4-6"
# claude-opus-4-7 is the default opus model as of Claude Code v2.1.142, which
# changed fast mode to default to opus-4-7 instead of opus-4-6.  Both versions
# belong to the same tier and are used interchangeably for coding tasks.
_OPUS_MODEL = "claude-opus-4-7"
_HAIKU_MODEL = "haiku"

# Tier alias -> concrete model ID. Users may also pass full model names
# (e.g. "claude-opus-4-7"), which are passed through unchanged.
_TIER_ALIASES: dict[str, str] = {
    "haiku": _HAIKU_MODEL,
    "sonnet": _DEFAULT_MODEL,
    "opus": _OPUS_MODEL,
    # Explicit versioned opus names — both map to the opus tier model so that
    # callers referencing either generation get consistent routing.
    "claude-opus-4-6": _OPUS_MODEL,
    "claude-opus-4-7": _OPUS_MODEL,
}

# Module-level cache for per-agent model preferences. ``None`` means not yet
# loaded; the empty dict means loaded with no overrides. Caching avoids
# re-reading YAML on every Agent tool call.
_AGENT_MODEL_CONFIG: dict[str, str] | None = None


def _resolve_tier_alias(value: str) -> str:
    """Map a tier alias to its concrete model ID, or pass through unchanged."""
    return _TIER_ALIASES.get(value.strip().lower(), value)


def _load_yaml_agents_section(path: Path) -> dict[str, str]:
    """Read ``models.agents`` from a YAML config file.

    Returns an empty dict if the file is missing, unreadable, or has no
    ``models.agents`` mapping. Uses PyYAML if available; otherwise silently
    returns empty (the hook must never crash Claude Code).
    """
    if not path.is_file():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    models_section = data.get("models")
    if not isinstance(models_section, dict):
        return {}
    agents = models_section.get("agents")
    if not isinstance(agents, dict):
        return {}
    # Normalize: lowercase agent IDs, stringify values, drop non-string entries.
    result: dict[str, str] = {}
    for agent_name, model_value in agents.items():
        if not isinstance(agent_name, str) or not isinstance(model_value, str):
            continue
        result[normalize_agent_id(agent_name)] = model_value.strip()
    return result


def _load_agent_model_config(cwd: str) -> dict[str, str]:
    """Load per-agent model overrides from user + project config.

    Reads ``~/.claude-mpm/config/configuration.yaml`` first, then merges in
    ``<cwd>/.claude-mpm/configuration.yaml`` so the project file wins for
    duplicate agent keys. Result is cached at module level for the lifetime
    of the hook process.
    """
    global _AGENT_MODEL_CONFIG
    if _AGENT_MODEL_CONFIG is not None:
        return _AGENT_MODEL_CONFIG

    merged: dict[str, str] = {}
    user_config = Path.home() / ".claude-mpm" / "config" / "configuration.yaml"
    merged.update(_load_yaml_agents_section(user_config))
    if cwd:
        project_config = Path(cwd) / ".claude-mpm" / "configuration.yaml"
        merged.update(_load_yaml_agents_section(project_config))

    _AGENT_MODEL_CONFIG = merged
    return merged


def _read_model_from_config(agent_name: str, cwd: str) -> str | None:
    """Look up an agent's configured model, resolving tier aliases."""
    config = _load_agent_model_config(cwd)
    value = config.get(normalize_agent_id(agent_name))
    if not value:
        return None
    return _resolve_tier_alias(value)


def _read_model_from_frontmatter(agent_name: str, cwd: str) -> str | None:
    """Try to read model: from agent .md frontmatter."""
    agents_dir = Path(cwd) / ".claude" / "agents"
    agent_file = agents_dir / f"{agent_name}.md"
    if not agent_file.exists():
        return None
    try:
        text = agent_file.read_text(encoding="utf-8")
        # Parse YAML frontmatter between --- markers
        match = re.search(r"^model:\s*(\S+)", text, re.MULTILINE)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def build_permission_request_response(event: dict) -> dict:
    """Run the permission policy engine and build the wire-format response.

    Claude Code expects the ``permissionDecision`` field inside
    ``hookSpecificOutput``. We always include ``permissionDecisionReason`` so
    the harness can surface why a request was approved/denied.

    Returns the full ``hookSpecificOutput``-wrapped payload dict. Exposed as an
    importable function so ``pretooluse_dispatcher`` can call it directly.
    """
    decision = permission_policy.evaluate(event)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "permissionDecision": decision.decision,
            "permissionDecisionReason": decision.reason,
        }
    }


def _handle_permission_request(event: dict) -> None:
    """Emit the wire-format permission decision for a PermissionRequest event."""
    print(json.dumps(build_permission_request_response(event)))


def build_model_tier_response(event: dict) -> dict:
    """Resolve and inject the model tier for an Agent tool call.

    Returns the full ``hookSpecificOutput``-wrapped payload dict, or
    ``{"continue": True}`` when the event is not an Agent call or already has a
    model set. Exposed as an importable function so ``pretooluse_dispatcher``
    can call it directly without spawning a subprocess.
    """
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Only intercept Agent tool calls that don't already have a model
    if tool_name != "Agent" or "model" in tool_input:
        return {"continue": True}

    agent_type = tool_input.get("subagent_type", "")
    cwd = event.get("cwd", "")

    # Resolution priority (highest -> lowest):
    #   1. Explicit ``model`` in the Agent tool call (handled above).
    #   2. ``models.agents.<name>`` from ~/.claude-mpm/config/configuration.yaml
    #      (with project-level .claude-mpm/configuration.yaml as override).
    #   3. Frontmatter ``model:`` field in .claude/agents/<name>.md.
    #   4. Built-in tier-based mapping (_HAIKU_AGENTS / _OPUS_AGENTS).
    #   5. Default sonnet.
    model = _read_model_from_config(agent_type, cwd)
    if model is None:
        model = _read_model_from_frontmatter(agent_type, cwd)
    if model is None:
        name_lower = normalize_agent_id(agent_type)
        if name_lower in _HAIKU_AGENTS:
            model = _HAIKU_MODEL
        elif name_lower in _OPUS_AGENTS:
            model = _OPUS_MODEL
        else:
            model = _DEFAULT_MODEL

    # Return modified tool_input via hookSpecificOutput.updatedInput.
    # Use additionalContext instead of permissionDecision/reason so the model
    # tier info is injected into the context window rather than surfaced as a
    # chat message (Claude Code v2.1.133+ additionalContext support).
    tool_input["model"] = model
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": f"Model tier resolved for agent '{agent_type}': {model}",
            "updatedInput": tool_input,
        }
    }


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        # Can't parse — allow through unchanged
        print(json.dumps({"continue": True}))
        return

    # Route by hook_event_name so one entrypoint handles both
    # PreToolUse (Agent model injection) and PermissionRequest (policy).
    hook_event = (
        event.get("hook_event_name")
        or event.get("event")
        or event.get("hook_event_type")
        or ""
    )
    if hook_event == "PermissionRequest":
        _handle_permission_request(event)
        return

    print(json.dumps(build_model_tier_response(event)))


if __name__ == "__main__":
    main()
