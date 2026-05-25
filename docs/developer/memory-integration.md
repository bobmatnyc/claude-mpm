# Memory Integration Developer Guide

This document describes how Claude MPM integrates with **trusty-memory** as the primary persistent memory backend. Trusty-memory replaces the legacy `kuzu-memory` integration; the older backend is retained only for backward compatibility (see [kuzu-memory](../integrations/kuzu-memory.md) for the legacy reference).

## What trusty-memory Provides

Trusty-memory is a Rust-based persistent memory system that gives Claude MPM and its subagents long-lived, structured project knowledge across sessions.

- **Memory palace** — hierarchical storage organized as `palace / wing / room / closet / drawer`, giving every fact a namespaced address
- **Progressive retrieval** — four recall depths (`L0`–`L3`) so agents can ask for "just the highlights" or a "deep dive" without blowing the context budget
- **Semantic recall** — natural-language queries against stored memories, not keyword grep
- **Temporal knowledge graph** — assert/query typed relationships across sessions for project-level reasoning
- **Per-project isolation** — each project owns a palace; no cross-project leakage
- **Low overhead** — Rust binary + persistent daemon, fast startup, small memory footprint

## How It Integrates with claude-mpm

Trusty-memory plugs into claude-mpm at two points:

1. **MCP stdio server** — Claude Code talks to `trusty-memory mcp` over stdio. Tools (`memory_recall`, `memory_remember`, etc.) become directly callable by the PM and subagents.
2. **Hook integration** — the `UserPromptSubmit` hook calls `trusty-memory prompt-context` to inject project context, aliases, and conventions before Claude sees the user's prompt.

```
┌──────────────────┐    UserPromptSubmit hook     ┌──────────────────┐
│   Claude Code    │ ──────────────────────────▶ │  trusty-memory    │
│   CLI session    │ ◀────────── injected ─────── │  prompt-context   │
└────────┬─────────┘     context blocks           └──────────────────┘
         │
         │  MCP stdio (memory_recall, memory_remember, kg_query, …)
         ▼
┌──────────────────┐
│  trusty-memory   │ ◀── persistent palace at .trusty-memory/
│  MCP server      │
└──────────────────┘
```

## Installation

```bash
# Install the binary
uv tool install trusty-memory

# Configure the current project (creates palace, MCP entry, optional hook)
claude-mpm setup trusty-memory
```

The setup command:

1. Verifies `trusty-memory` is installed (offers to install via cargo/uv tool if missing)
2. Creates a project palace at `.trusty-memory/` (or registers a named palace)
3. Adds the MCP server entry to `~/.claude/settings.json` (or project `.mcp.json`)
4. Optionally installs the `UserPromptSubmit` hook for automatic context injection

## MCP Server Configuration

Trusty-memory is registered as an MCP server in `~/.claude/settings.json` (user-level, available across projects):

```json
{
  "mcpServers": {
    "trusty-memory": {
      "command": "trusty-memory",
      "args": ["mcp"],
      "env": {}
    }
  }
}
```

For project-scoped configuration, the same entry can live in `.mcp.json` at the project root.

## Hook Setup

To pull project context into every prompt automatically, wire `trusty-memory prompt-context` into the `UserPromptSubmit` hook in `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "trusty-memory prompt-context" }
        ]
      }
    ]
  }
}
```

The hook is non-blocking: if trusty-memory is unavailable, it returns silently and the prompt proceeds without injected context.

## Palace Concepts

Trusty-memory organizes everything stored into a hierarchy. Each level is optional — pick the depth that fits the knowledge being stored.

| Level | Role | Example |
|-------|------|---------|
| **palace** | Top-level namespace, typically one per project | `claude-mpm` |
| **wing** | Major domain inside the palace | `architecture`, `conventions`, `team` |
| **room** | Topic area inside a wing | `agents`, `hooks`, `release` |
| **closet** | Cluster of related facts inside a room | `pm-instructions` |
| **drawer** | Individual fact / memory | `"PM never uses Edit/Write directly"` |

Most subagent calls only need the palace name; trusty-memory handles routing internally.

## Key MCP Tools

These are the tools claude-mpm agents call most often. All are exposed by the MCP server and discoverable in Claude Code via `mcp__trusty-memory__*`.

| Tool | Purpose |
|------|---------|
| `memory_recall` | Semantic recall against the palace (returns top-N facts, L1 detail by default) |
| `memory_recall_deep` | Same as `memory_recall` but at L2/L3 — fuller context, more tokens |
| `memory_remember` | Store a fact with optional palace / wing / room hint |
| `memory_remember_with_confirmation` | Store a critical fact and require model confirmation |
| `palace_create` | Create a new palace (used during `claude-mpm setup`) |
| `palace_list` | List palaces available to this user |
| `kg_assert` | Add a typed edge to the temporal knowledge graph |
| `kg_query` | Query the knowledge graph (supports temporal filters) |
| `get_prompt_context` | Return aliases / conventions / context for prompt injection |

PM-side guidance for using these tools lives in `src/claude_mpm/agents/PM_INSTRUCTIONS.md` (see "Context-First Protocol").

## Storage Layout

A typical project palace lives at:

```
<project-root>/.trusty-memory/
├── palace/
│   ├── graph.db          # SQLite-backed graph storage
│   ├── embeddings/       # Vector index for semantic recall
│   └── metadata.json
└── config.yaml
```

## Migrating from kuzu-memory

If a project already uses `kuzu-memory`:

1. Back up the legacy database: `mv kuzu-memories kuzu-memories.backup`
2. Run `claude-mpm setup trusty-memory` to create a fresh palace
3. (Optional) Re-import any critical facts manually via `memory_remember`

The two backends can coexist temporarily: PM_INSTRUCTIONS.md treats `trusty-memory` as the primary backend and `kuzu-memory` as a deprecated fallback that is still callable if it happens to be installed.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `trusty-memory: command not found` | `uv tool install trusty-memory`, then reload shell |
| MCP server not connecting | `cat ~/.claude/settings.json` — confirm the `trusty-memory` entry |
| `UserPromptSubmit` hook hangs | Hook command must exit quickly; verify the binary is on `PATH` and that `prompt-context` returns within ~1s |
| Empty recall results | Confirm the palace contains data: `trusty-memory list` or call `memory_recall_deep` |

## Related Documentation

- [Trusty Memory Integration Guide](../integrations/trusty-memory.md) — user-facing setup walkthrough
- [Trusty Search Integration Guide](../integrations/trusty-search.md) — companion semantic code search
- [Memory System Reference](../reference/MEMORY.md) — high-level memory model and partner products
- [PM Instructions](../../src/claude_mpm/agents/PM_INSTRUCTIONS.md) — Context-First Protocol section
