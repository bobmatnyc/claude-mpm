# Claude MPM v6.0.0b1 Beta

## Status

v6.0.0b1 is a **pre-release beta**. It is opt-in only — `pip install claude-mpm` and `uv tool install claude-mpm` will continue to install the stable v5.11.4 release. You must explicitly request the beta version to get it.

All core scenarios have been tested and passed. That said, this is a major version with breaking binary changes, so some rough edges are expected.

---

## What's New

### 1. Plugin System

Claude MPM can now be installed as a **Claude Code plugin** — no pip install required for core functionality. The plugin gives you:

- 6 hook events (pre/post tool calls, stop hook, notifications, etc.)
- 56 bundled skills
- 2 slash commands: `/mpm-status`, `/mpm-help`
- MCP server configuration

For the full CLI, multi-agent orchestration, monitoring dashboard, and all integrations, a pip install is still required.

### 2. Binary Consolidation

10 standalone binaries have been reduced to **2**:

| Binary | Purpose |
|--------|---------|
| `claude-mpm` | All CLI commands, plus `mcp serve <name>` for MCP servers |
| `claude-hook` | Hook handler — kept separate for performance |

The following standalone binaries have been removed:

- `claude-mpm-doctor` (now `claude-mpm doctor`)
- `claude-mpm-monitor` (now `claude-mpm monitor`)
- `claude-mpm-socketio` (now `claude-mpm mcp serve session`)
- `claude-mpm-ui` (now `claude-mpm ui`)
- `confluence-mcp` (now `claude-mpm mcp serve confluence`)
- `notion-mpm` (now `claude-mpm mcp serve messaging`)
- `mpm-session-server` (now `claude-mpm mcp serve session`)
- `mpm-session-server-http` (now `claude-mpm mcp serve session-http`)

MCP server names for `claude-mpm mcp serve <name>`:

| Name | Description |
|------|-------------|
| `messaging` | MPM messaging MCP server |
| `slack-proxy` | Slack user proxy MCP server |
| `session` | Session management (WebSocket) |
| `session-http` | Session management (HTTP) |
| `confluence` | Confluence MCP server |

### 3. Auto-Migration

When you upgrade to v6, existing `.mcp.json` files referencing old binary names are automatically detected and rewritten on startup. You can also run the migration manually:

```bash
# Preview what will change
claude-mpm migrate --dry-run

# Apply migration
claude-mpm migrate
```

Migration handles entries like `python -m claude_mpm.mcp.*` and standalone binary calls, rewriting them to `claude-mpm mcp serve <name>`.

### 4. 56 Bundled Skills

The skills library has grown from 44 to 56 bundled skills, adding coverage for more development patterns and workflows.

### 5. Stop Hook Fix

The "Only 1 message already read" stale count bug has been fixed. The stop hook now queries fresh message counts on every invocation and resets the throttle correctly when a block occurs.

---

## Install the Beta

### Option A: Plugin (No pip required)

The easiest path. Works directly inside Claude Code without any pip install.

```bash
# Add the MPM marketplace
claude plugin marketplace add bobmatnyc/claude-mpm-marketplace

# Install the plugin (always installs the latest plugin version)
claude plugin install claude-mpm@claude-mpm-marketplace
```

This gives you hooks, skills, slash commands, and MCP config. If you later want CLI commands and multi-agent orchestration, also do Option B.

### Option B: Pip (explicit pin required)

PEP 440 pre-release versions are never auto-selected. You must pin the version explicitly:

```bash
pip install claude-mpm==6.0.0b1
```

Or with uv:

```bash
uv tool install claude-mpm==6.0.0b1
```

### Option C: Run from source

```bash
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm
git checkout v6.0.0b1
uv sync
uv run claude-mpm --help
```

---

## Stay on Stable (v5.11.4)

No action required. The default install commands always pick the latest stable release:

```bash
pip install claude-mpm
uv tool install claude-mpm
```

If you previously pinned to `6.0.0b1` and want to downgrade:

```bash
pip install claude-mpm==5.11.4
```

---

## Migration from v5.x

If you are upgrading from v5.x to v6.0.0b1:

1. **Install the beta**:
   ```bash
   pip install claude-mpm==6.0.0b1
   ```

2. **Run migration** (or let it run automatically on next startup):
   ```bash
   claude-mpm migrate --dry-run   # preview changes first
   claude-mpm migrate             # apply
   ```

3. **Update any scripts** that call removed binaries directly (the migration handles `.mcp.json`, but shell scripts referencing `mpm-session-server` etc. need manual updates).

4. **Install the plugin** (optional but recommended):
   ```bash
   claude plugin marketplace add bobmatnyc/claude-mpm-marketplace
   claude plugin install claude-mpm@claude-mpm-marketplace
   ```

**Backward compatibility note**: `claude-mpm-doctor` still works but prints a deprecation warning. Use `claude-mpm doctor` going forward.

---

## What We Tested

All of the following test scenarios passed before the beta was published:

- ✅ Binary consolidation — all `claude-mpm` subcommands work correctly
- ✅ Auto-migration — old `.mcp.json` configs are detected and rewritten
- ✅ Plugin install and uninstall — clean lifecycle via `claude plugin` commands
- ✅ Stop hook stale count fix — no false "already read" messages
- ✅ Agent workflow end-to-end — multi-agent orchestration unaffected

---

## Known Issues / Limitations

- This is a pre-release. Expect some rough edges, especially around edge cases in the plugin system.
- The plugin system is new infrastructure. If you hit unexpected behavior, please file an issue.
- `claude-mpm-doctor` still works but shows a deprecation warning. It will be removed in a future release.
- Shell scripts or CI configs that call removed binaries directly (not via `.mcp.json`) require manual updates — auto-migration only covers `.mcp.json`.

---

## Feedback

Found a bug or have feedback on the beta? File an issue on GitHub:

https://github.com/bobmatnyc/claude-mpm/issues

Please tag your issue with the `v6-beta` label so it gets routed to the right place.
