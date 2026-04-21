#!/usr/bin/env python3
"""PreToolUse hook: inject default model into Agent tool calls.

Claude Code ignores agent frontmatter model: field (anthropics/claude-code#44385).
This hook reads the agent .md file's frontmatter and injects the model
parameter into Agent tool calls when the caller didn't specify one.

Returns hookSpecificOutput with updatedInput to modify tool parameters.
"""

import json
import re
import sys
from pathlib import Path

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
_OPUS_MODEL = "claude-opus-4-6"
_HAIKU_MODEL = "haiku"


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


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        # Can't parse — allow through unchanged
        print(json.dumps({"continue": True}))
        return

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Only intercept Agent tool calls that don't already have a model
    if tool_name != "Agent" or "model" in tool_input:
        print(json.dumps({"continue": True}))
        return

    agent_type = tool_input.get("subagent_type", "")
    cwd = event.get("cwd", "")

    # Frontmatter `model:` field always wins when present (e.g. planner.md
    # pins claude-opus-4-7 explicitly). Fall back to tier-based mapping:
    #   haiku  -> low-cost ops/docs/routing agents
    #   opus   -> coding/engineering agents (stronger code quality)
    #   sonnet -> everything else (PM/orchestrator default)
    model = _read_model_from_frontmatter(agent_type, cwd)
    if model is None:
        name_lower = agent_type.lower().replace("_", "-")
        if name_lower in _HAIKU_AGENTS:
            model = _HAIKU_MODEL
        elif name_lower in _OPUS_AGENTS:
            model = _OPUS_MODEL
        else:
            model = _DEFAULT_MODEL

    # Return modified tool_input via hookSpecificOutput.updatedInput
    tool_input["model"] = model
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": tool_input,
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
