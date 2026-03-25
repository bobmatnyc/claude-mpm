# claude-mpm Plugin for Claude Code

A Claude Code plugin that integrates the Multi-Agent Project Manager (MPM) into
Claude Code's native plugin system.  This provides hooks, skills, slash commands,
and MCP server configuration without needing to run `claude-mpm configure` manually.

## What This Plugin Provides

| Component | Description |
|-----------|-------------|
| **Hooks** | Agent delegation tracking, session monitoring, and event handling across all hook events (PreToolUse, PostToolUse, Stop, UserPromptSubmit, SubagentStop) |
| **Skills** | MPM orchestrator skill -- delegation-first agent management, available agent types, verification protocol |
| **Commands** | `/mpm-status` and `/mpm-help` slash commands for quick system status and reference |
| **MCP Servers** | `mpm-messaging` -- cross-project messaging between Claude instances |

## Prerequisites

The plugin acts as a thin integration layer. For full functionality you need the
`claude-mpm` Python package installed:

```bash
# Recommended
uv tool install claude-mpm

# Or via pip
pip install claude-mpm

# Or via pipx
pipx install claude-mpm
```

The plugin degrades gracefully if the package is not installed: hooks will return
`{"continue": true}` with a message suggesting installation, and slash commands
will report that MPM is not available.

## Installation

```bash
# From the Claude Code plugin marketplace (when available)
claude plugin install claude-mpm

# Or install from a local path (development)
claude plugin install /path/to/claude-mpm/plugin
```

## How It Differs from `claude-mpm configure`

| Feature | `claude-mpm configure` | This Plugin |
|---------|----------------------|-------------|
| Hook installation | Copies scripts to `~/.claude/hooks/` | Uses Claude Code's native plugin hook system |
| MCP configuration | Writes to project `.mcp.json` | Plugin provides `.mcp.json` automatically |
| Skills | Writes to `.claude/skills/` | Plugin bundles skills natively |
| Slash commands | Writes to `.claude/commands/` | Plugin bundles commands natively |
| Updates | Must re-run `configure` | Plugin updates via `claude plugin update` |
| Scope | Per-project | All projects (plugin-level) |

The plugin approach is simpler for new users and keeps configuration centralized.
Advanced users who need per-project customization can still use `claude-mpm configure`.

## Architecture

```
Claude Code
    |
    +-- Plugin System
    |       |
    |       +-- hooks/mpm_hook_handler.py   (thin wrapper)
    |       |       |
    |       |       +-- claude-hook binary   (from pip install)
    |       |       |       |
    |       |       |       +-- hook_handler.py  (real logic)
    |       |       |
    |       |       +-- OR: {"continue": true}  (if not installed)
    |       |
    |       +-- skills/mpm-orchestrator/SKILL.md
    |       |
    |       +-- commands/mpm-status.md, mpm-help.md
    |       |
    |       +-- .mcp.json  (registers mpm-messaging server)
    |
    +-- MCP Servers
            |
            +-- mpm-messaging  (cross-project messaging)
```

The hook handler is intentionally thin: it locates the installed `claude-hook`
binary and delegates to it, passing stdin through.  This means the real hook
logic lives in the pip package and gets updated with `pip install --upgrade`.

## Development

To work on the plugin locally:

```bash
# Clone the repo
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Install the Python package in development mode
uv pip install -e .

# Install the plugin from local path
claude plugin install ./plugin
```

## License

MIT -- see [LICENSE](./LICENSE).
