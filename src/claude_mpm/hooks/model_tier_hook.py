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

_DEFAULT_MODEL = "sonnet"


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

    # Try frontmatter first, fall back to static mapping
    model = _read_model_from_frontmatter(agent_type, cwd)
    if model is None:
        name_lower = agent_type.lower().replace("_", "-")
        model = "haiku" if name_lower in _HAIKU_AGENTS else _DEFAULT_MODEL

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
