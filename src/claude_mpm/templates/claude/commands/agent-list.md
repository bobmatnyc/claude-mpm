---
description: "List all available agents with their capabilities (MPM-provided — may be shadowed by a user /agent-list command)"
---

> **Note (MPM-provided command)**: This `/agent-list` command is shipped by claude-mpm.
> If you have a project or user-level command also named `/agent-list`, it will shadow
> this one.  User commands take precedence by design.

List all available agents in the claude-mpm project.

1. Find agent files in `.claude/agents/` (project-level) and `~/.claude/agents/` (user-level).

2. For each `.md` file found, read the YAML frontmatter and extract:
   - `name` — agent identifier
   - `description` — when/how to use it
   - `model` — which model it uses (if specified)
   - `tools` — allowed tools (if specified)
   - `skills` — preloaded skills (if specified)

3. Display a formatted table or list with columns: **Name**, **Model**, **Description** (truncated to ~80 chars), **Skills**.

4. Group results by location: project-level agents first, then user-level agents.

5. Report total counts: X project agents, Y user-level agents.
