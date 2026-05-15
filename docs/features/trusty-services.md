# Trusty Services Integration

## Overview

Claude MPM integrates with two Rust-based daemon services that extend Claude's capabilities with local code search and persistent project memory:

- **trusty-search**: Hybrid code search combining semantic embeddings, BM25 full-text search, and knowledge graph traversal. Exposes its index to Claude Code sessions via the MCP protocol.
- **trusty-memory**: A persistent AI memory daemon organized around named "Memory Palaces" — one per project. Allows Claude to store and retrieve project-specific context across sessions.

Both services run as long-lived background daemons and communicate with Claude Code via `stdio` MCP servers. Claude MPM handles detection, wiring, and persistence automatically.

---

## Why These Services Are Useful

Without trusty-search, Claude Code relies solely on text search and its context window to navigate a codebase. trusty-search provides:
- Semantic search that finds conceptually related code, not just textual matches
- BM25 ranking for precise keyword results
- Knowledge-graph edges linking related symbols, files, and modules

Without trusty-memory, every Claude Code session starts cold. trusty-memory provides:
- Persistent storage of decisions, architectural notes, and project-specific patterns
- Per-project isolation via palaces so different codebases don't pollute each other
- A structured memory API exposed directly to Claude's tool use

---

## Installation

Both services are Rust binaries installed via `cargo`:

```bash
cargo install trusty-search
cargo install trusty-memory
```

Ensure `~/.cargo/bin` is on your `PATH`. If you have `cargo-binstall` available, the `claude-mpm setup` commands will use it for faster installation.

Rust itself can be installed from [https://rustup.rs/](https://rustup.rs/).

---

## Auto-Detection (Recommended Path)

Claude MPM detects running trusty daemons automatically on every session start. No manual `setup` command is required if the daemons are already running.

### How It Works

The auto-detection migration (`trusty_autodetect`, registered as `run_always`) executes during startup:

1. For each service (`trusty-search`, `trusty-memory`), claude-mpm checks whether the binary is on `PATH` via `shutil.which`.
2. If the binary is present, it reads the daemon's address discovery file to find the current HTTP address:
   - `~/.trusty-search/http_addr` for trusty-search
   - `~/.trusty-memory/http_addr` for trusty-memory
3. It performs a lightweight HTTP health probe (`GET /health`, 2-second timeout) against that address.
4. If the daemon responds with a 2xx status and the MCP entry is not already in `.mcp.json`, it injects the entry transactionally.

The entire probe is silent: no log output when daemons are absent, no user prompts, no startup delay when probes fail quickly.

### Dynamic Port Selection

Both daemons select their HTTP port dynamically via the OS and write the chosen address to their discovery files. Claude MPM reads these files rather than assuming fixed ports. If the file is absent or unreadable, claude-mpm falls back to the legacy defaults:

| Service | Discovery File | Legacy Default |
|---------|---------------|----------------|
| trusty-search | `~/.trusty-search/http_addr` | `127.0.0.1:7878` |
| trusty-memory | `~/.trusty-memory/http_addr` | `127.0.0.1:3038` |

The addr file format is a single line: `host:port` (for example, `127.0.0.1:54321`).

### MCP Entry Injected

When auto-detection succeeds, the following entries are written to `.mcp.json`:

```json
{
  "mcpServers": {
    "trusty-search": {
      "type": "stdio",
      "command": "trusty-search",
      "args": ["serve"]
    },
    "trusty-memory": {
      "type": "stdio",
      "command": "trusty-memory",
      "args": ["serve", "--mcp"]
    }
  }
}
```

The write uses a transactional helper that rolls back `.mcp.json` to its prior state on any failure, so a crash mid-write will not corrupt your config.

### Idempotency

If the entry already exists in `.mcp.json`, auto-detection skips it. Re-running claude-mpm after a daemon restart will detect the new port automatically and update the entry only if it was missing.

---

## Manual Setup (Fallback)

If you prefer to run setup explicitly, or if the daemons need to be installed and started for the first time, use the setup commands:

```bash
# Set up trusty-search for the current project
claude-mpm setup trusty-search

# Set up trusty-memory for the current project
claude-mpm setup trusty-memory
```

Both commands:
1. Install the binary via `cargo install` (or `cargo-binstall`) if not already present.
2. Start the daemon as a persistent macOS launchd agent (`KeepAlive=true`, `RunAtLoad=true`) if it is not currently running.
3. Wait up to 5 seconds for the daemon to report healthy, re-reading the discovery file each poll.
4. Perform service-specific setup (see below).
5. Write the `.mcp.json` entry with rollback on failure.

### launchd Agent Labels

| Service | Label |
|---------|-------|
| trusty-search | `com.bobmatnyc.trusty-search` |
| trusty-memory | `com.bobmatnyc.trusty-memory` |

Plist files are written to `~/Library/LaunchAgents/`. After setup, the daemon will restart automatically after crashes and survive reboots.

Daemon logs are written to:
- `/tmp/trusty-search.log` and `/tmp/trusty-search-error.log`
- `/tmp/trusty-memory.log` and `/tmp/trusty-memory-error.log`

---

## Per-Project Indexing (trusty-search)

trusty-search maintains a searchable index per project. The setup command indexes the current working directory automatically:

```bash
cd /path/to/your/project
claude-mpm setup trusty-search
# Runs: trusty-search index /path/to/your/project
```

To index a project manually, or to re-index after significant code changes:

```bash
trusty-search index /path/to/your/project
```

Indexing is bounded to 120 seconds during setup. Large repositories may need to be indexed separately after setup completes.

---

## Memory Palaces (trusty-memory)

trusty-memory organizes memories into named "palaces". Claude MPM creates one palace per project, named after the project directory:

```bash
cd ~/Projects/my-api
claude-mpm setup trusty-memory
# Creates palace: my-api
# MCP command: trusty-memory serve --mcp --palace my-api
```

The `palace new` command is idempotent: if the palace already exists, setup verifies it with `palace info` and continues without error.

The palace name is derived from the current working directory name at setup time. Auto-detection does not specify a palace name (the `--palace` flag is omitted from the auto-detected entry), so Claude has access to all palaces.

---

## Troubleshooting

### Daemon Not Auto-Detected

If claude-mpm is not picking up a running daemon:

1. Confirm the binary is on PATH:
   ```bash
   which trusty-search
   which trusty-memory
   ```

2. Check whether the daemon is actually running and healthy:
   ```bash
   # Read the discovery file
   cat ~/.trusty-search/http_addr
   cat ~/.trusty-memory/http_addr

   # Test the health endpoint
   curl http://$(cat ~/.trusty-search/http_addr)/health
   curl http://127.0.0.1:3038/health
   ```

3. Start the daemon manually and wait a moment:
   ```bash
   trusty-search start &
   ```

4. On the next `claude-mpm` invocation, auto-detection will probe again.

### Re-Running Setup

To re-run full setup (reinstall launchd agent, re-index, re-write `.mcp.json`):

```bash
claude-mpm setup trusty-search --force
claude-mpm setup trusty-memory --force
```

Or remove the `.mcp.json` entries and let auto-detection re-add them:

```bash
# Edit .mcp.json and remove the trusty-search / trusty-memory entries,
# then restart claude-mpm. Auto-detection will re-inject them.
```

### Checking the launchd Agent

```bash
# Is the agent loaded?
launchctl list com.bobmatnyc.trusty-search
launchctl list com.bobmatnyc.trusty-memory

# View logs
tail -f /tmp/trusty-search.log
tail -f /tmp/trusty-memory-error.log
```

### MCP Calls Failing After Port Change

If trusty-search restarts and selects a new port, the existing `.mcp.json` entry (which uses `trusty-search serve` via stdio rather than a hardcoded URL) will still work correctly — the stdio MCP server discovers the daemon address at call time. No `.mcp.json` update is needed after a port change.

---

## Related Files

- **Setup handler**: `src/claude_mpm/cli/commands/setup/handlers/trusty.py`
- **Auto-detection migration**: `src/claude_mpm/migrations/migrate_trusty_autodetect.py`
- **Migration registry**: `src/claude_mpm/migrations/registry.py`
- **MCP config helpers**: `src/claude_mpm/cli/commands/setup/mcp_config.py`
- **Discovery files**: `~/.trusty-search/http_addr`, `~/.trusty-memory/http_addr`
- **Daemon logs**: `/tmp/trusty-search.log`, `/tmp/trusty-memory.log`
