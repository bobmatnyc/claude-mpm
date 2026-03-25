---
description: "Show MPM system status including version, active agents, and configuration"
---

# /mpm-status

When the user runs `/mpm-status`, perform the following checks and report the results:

## System Check

1. **Installation**: Run `claude-mpm --version` via bash to check if claude-mpm is installed. Report the version or indicate it is not installed.

2. **Configuration**: Check if `~/.claude-mpm/` directory exists and report whether MPM is configured.

3. **Active Agents**: Run `claude-mpm status` via bash to list any active agent sessions. If the command fails, report that no active sessions were found.

4. **MCP Servers**: Check if the mpm-messaging MCP server is available by looking for it in the current MCP tool list. Report which MPM MCP servers are connected.

5. **Hook Status**: Report that hooks are provided by the claude-mpm plugin (this plugin).

## Output Format

Present the results in a clear summary:

```
MPM Status
----------
Version:       [version or "not installed"]
Configuration: [configured / not configured]
Active Agents: [count or "none"]
MCP Servers:   [list of connected MPM servers]
Hooks:         [active via plugin]
```

If claude-mpm is not installed, suggest: `pip install claude-mpm` or `uv tool install claude-mpm`.
