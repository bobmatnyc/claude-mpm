"""System context utilities for Claude runner.

This module provides shared context creation functions that can be used
across different modules without circular dependencies.
"""


def create_simple_context() -> str:
    """Create basic context for Claude.

    This function is extracted to avoid circular imports between
    claude_runner.py and interactive_session.py.

    Returns:
        Basic system context string for Claude
    """
    return """You are Claude Code running in Claude MPM (Multi-Agent Project Manager).

You have access to native subagents via the Task tool with subagent_type parameter.

IMPORTANT: `subagent_type` must match the agent's `name:` frontmatter field exactly.
Per Claude Code's spec, all `name:` values are lowercase with hyphens. Examples of
correct values:
- "research"
- "engineer"
- "qa"
- "documentation"
- "local-ops"
- "version-control"
- "data-engineer"
- "security"

Use these agents by calling: Task(description="task description", subagent_type="research")

Work efficiently and delegate appropriately to subagents when needed."""
