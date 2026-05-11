# Trusty Analyze Integration

## Overview

Trusty Analyze (binary: `trusty-analyzer`) is a Rust code-analysis sidecar
daemon that sits next to [`trusty-search`](trusty-search.md) and consumes its
indexes. While `trusty-search` answers *"where is this code?"*,
`trusty-analyze` answers *"how healthy is this code?"* — complexity hotspots,
smell detection, A–F quality grading, and concept clustering — all via MCP
tools.

> **Naming note:** the user-facing setup verb (and the GitHub repository) is
> `trusty-analyze`, but the installed binary is `trusty-analyzer` (with the
> trailing "r"). `claude-mpm setup trusty-analyze` always installs the
> `trusty-analyzer` binary.

## Features

- **Complexity Hotspots** — Rank the most cyclomatically complex code chunks
  in any indexed repository (`complexity_hotspots`).
- **Smell Detection** — Long methods, god objects, feature envy, and other
  patterns via `find_smells`.
- **Quality Grade** — Single A–F report card per index with per-axis
  sub-scores via `analyze_quality`.
- **Concept Clustering** — Group code into k semantic clusters
  (`cluster_concepts`) for architectural overviews.
- **Persistent Facts** — `list_facts` returns analyzer findings persisted for
  an index.
- **Persistent Daemon** — Runs as launchd service on macOS with
  `KeepAlive=true` so it survives crashes and reboots.

## Prerequisites

- **Rust toolchain** — Install from <https://rustup.rs/> (~5 minutes).
- **`trusty-search` already running** — `trusty-analyze` is a read-only
  consumer of trusty-search indexes; the repository must already be indexed
  before any analysis tools work. See [`trusty-search.md`](trusty-search.md).
- **claude-mpm installed** and a project directory initialized.

## Installation

### Quick Setup

```bash
# From your project directory
claude-mpm setup trusty-analyze
```

This will:

1. Check for Rust / cargo installation.
2. Install `trusty-analyzer` via `cargo install` (registry first, with a
   `cargo install --git https://github.com/bobmatnyc/trusty-analyze.git`
   fallback while the crate is being published).
3. Write & load a launchd plist (`com.bobmatnyc.trusty-analyzer`) so the
   daemon stays up across reboots and crashes.
4. Probe `http://127.0.0.1:7879/health` until the daemon answers (or warn if
   it doesn't).
5. Register the service in `.mcp.json` so Claude Code can call its MCP
   tools.

### What Gets Installed

| Artifact | Path |
|----------|------|
| Binary | `~/.cargo/bin/trusty-analyzer` |
| Daemon URL | `http://127.0.0.1:7879` |
| launchd plist | `~/Library/LaunchAgents/com.bobmatnyc.trusty-analyzer.plist` |
| Logs (stdout) | `/tmp/trusty-analyzer.log` |
| Logs (stderr) | `/tmp/trusty-analyzer-error.log` |
| MCP entry | `.mcp.json` → `mcpServers.trusty-analyzer` |

## Configuration

### MCP Configuration

Added to `.mcp.json`:

```json
{
  "mcpServers": {
    "trusty-analyzer": {
      "type": "stdio",
      "command": "trusty-analyzer",
      "args": ["mcp"]
    }
  }
}
```

### Daemon Management (macOS)

```bash
# Verify the daemon is loaded persistently
launchctl list | grep trusty-analyzer

# Manually start / stop
launchctl unload ~/Library/LaunchAgents/com.bobmatnyc.trusty-analyzer.plist
launchctl load   ~/Library/LaunchAgents/com.bobmatnyc.trusty-analyzer.plist

# Health probe
curl -s http://127.0.0.1:7879/health
```

`KeepAlive=true` in the plist means the daemon will be auto-restarted by
launchd if it crashes.

## Usage

### MCP Tools in Claude Code

#### 1. analyzer_health

Always call this first to verify both `trusty-search` and `trusty-analyze`
are reachable.

```
mcp__trusty-analyze__analyzer_health()
# { status: "ok", search_reachable: true, version: "..." }
```

#### 2. complexity_hotspots

Top-N most complex chunks in an index.

```
mcp__trusty-analyze__complexity_hotspots(
  index_id="claude-mpm",
  top_k=20
)
```

Use cases:

- Pre-refactor triage.
- "What's the worst function in this codebase?"
- Tracking complexity over time.

#### 3. find_smells

Pattern-based smell detection.

```
mcp__trusty-analyze__find_smells(
  index_id="claude-mpm",
  category="long_method"
)
```

Supported categories include `long_method`, `god_object`, `feature_envy`,
and more — check `analyzer_health` output / daemon docs for the current
list.

#### 4. analyze_quality

Aggregate A–F grade with sub-scores.

```
mcp__trusty-analyze__analyze_quality(
  index_id="claude-mpm"
)
```

#### 5. cluster_concepts

Group an index into k concept clusters.

```
mcp__trusty-analyze__cluster_concepts(
  index_id="claude-mpm",
  k=8,
  method="neural"
)
```

`method` accepts `"neural"`, `"tfidf"`, or `"hybrid"`.

#### 6. list_facts

Recall previously persisted analyzer facts for an index.

```
mcp__trusty-analyze__list_facts(index_id="claude-mpm")
```

## Recommended Workflow

```
# 1. Verify both daemons are reachable
analyzer_health()

# 2. Sanity-check the index exists in trusty-search
mcp__trusty-search__index_status(index="claude-mpm")

# 3. Get an executive summary
analyze_quality(index_id="claude-mpm")

# 4. Drill into the worst offenders
complexity_hotspots(index_id="claude-mpm", top_k=20)
find_smells(index_id="claude-mpm", category="long_method")

# 5. Architectural overview
cluster_concepts(index_id="claude-mpm", k=8, method="neural")

# 6. Persist insights via trusty-memory
mcp__trusty-memory__memory_remember(
  content="Top complexity hotspot is X; refactor by Y",
  room="Backend",
  tags=["complexity", "refactor"]
)
```

## Trusty Trio: search + analyze + memory

| Step | Tool | Purpose |
|------|------|---------|
| Index code | `trusty-search` `create_index` | Make code analyzable |
| Locate code | `trusty-search` `search_code` | Find a starting point |
| Score code | `trusty-analyze` `*_hotspots`, `find_smells`, `analyze_quality` | Triage |
| Remember findings | `trusty-memory` `memory_remember` | Persist learnings |

## Troubleshooting

### Daemon Not Starting

```bash
# Check stderr log
tail -f /tmp/trusty-analyzer-error.log

# Reload launchd agent
launchctl unload ~/Library/LaunchAgents/com.bobmatnyc.trusty-analyzer.plist
launchctl load   ~/Library/LaunchAgents/com.bobmatnyc.trusty-analyzer.plist
```

### `search_reachable: false`

The analyzer requires `trusty-search` on `127.0.0.1:7878`. Make sure
`trusty-search` is installed and running:

```bash
claude-mpm setup trusty-search
curl -s http://127.0.0.1:7878/health
```

### Port 7879 Already in Use

```bash
lsof -i :7879
# Stop the conflicting process or change the port in the plist.
```

### Rust Not Installed

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
claude-mpm setup trusty-analyze
```

## Force Upgrade

```bash
# Force re-install of the binary and reload of the daemon
claude-mpm setup trusty-analyze --force
```

## Integration with Claude MPM

`trusty-analyze` is wired into:

- **code-analyzer agent** — `.claude/agents/code-analyzer.md` prefers
  trusty-analyze tools over manual AST parsing when the daemon is up.
- **trusty-analyze skill** — `.claude/skills/trusty-analyze/SKILL.md`
  documents the tool surface for any agent.
- **.mcp.json** — `claude-mpm setup trusty-analyze` registers the stdio
  command `trusty-analyzer mcp`.

## Further Reading

- [trusty-analyze GitHub](https://github.com/bobmatnyc/trusty-analyze)
- [Trusty Search Integration](trusty-search.md)
- [Trusty Memory Integration](trusty-memory.md)

---

[Back to Integrations](README.md) | [Documentation Index](../README.md)
