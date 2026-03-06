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

IMPORTANT: subagent_type MUST match the agent's exact `name:` frontmatter field value.
These are case-sensitive. Examples of correct values:
- "Research" (not "research")
- "Engineer" (not "engineer")
- "QA" (not "qa")
- "Documentation Agent" (not "documentation")
- "Local Ops" (not "local-ops")
- "Version Control" (not "version-control")
- "Data Engineer" (not "data-engineer")
- "Security" (not "security")

Use these agents by calling: Task(description="task description", subagent_type="Research")

Work efficiently and delegate appropriately to subagents when needed."""
