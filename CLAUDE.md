# Project Memory Configuration

This project uses KuzuMemory for intelligent context management.

## Project Information
- **Path**: /Users/masa/Projects/claude-mpm
- **Language**: Python
- **Framework**: FastAPI

## Memory Integration

KuzuMemory is configured to enhance all AI interactions with project-specific context.

### Available Commands:
- `kuzu-memory enhance <prompt>` - Enhance prompts with project context
- `kuzu-memory learn <content>` - Store learning from conversations (async)
- `kuzu-memory recall <query>` - Query project memories
- `kuzu-memory stats` - View memory statistics

### MCP Tools Available:
When interacting with Claude Desktop, the following MCP tools are available:
- **kuzu_enhance**: Enhance prompts with project memories
- **kuzu_learn**: Store new learnings asynchronously
- **kuzu_recall**: Query specific memories
- **kuzu_stats**: Get memory system statistics

## Project Context

Claude Multi-Agent Project Manager - Orchestrate Claude with agent delegation and ticket tracking

---

## StGit Patch Management

This fork uses [StGit](https://stacked-git.github.io/) for managing local changes as a stack of patches on top of upstream. This enables clean rebasing when upstream releases new versions.

### Branch Structure
- `main` - Production branch (updated from stgit-migration after rebasing)
- `stgit-migration` - StGit-managed branch with patches on upstream/main
- `upstream` - Remote tracking upstream repository (bobmatnyc/claude-mpm)

### Current Patch Stack
```
01-commander-pro-ui-v2-core      # Pro UI v2 with activity tracker
02-commander-pro-ui-v2-browser-term  # Browser terminal support
03-headless-mode-cli-flags       # --headless CLI flag
04-headless-mode-session         # HeadlessSession class
05-headless-mode-integration     # CLI integration + tests
06-headless-mode-docs            # Headless documentation
07-tob-setup-script              # TOB installation script
08-documentation-updates         # README/CLAUDE.md updates
```

### Syncing with Upstream

Use `stg pull` for a single-command update, or the staged approach for more control:

```bash
# Switch to stgit branch
git checkout stgit-migration

# Option A: Single command (fetch + rebase)
stg pull

# Option B: Staged approach (more control)
git fetch upstream
stg pop -a                    # Pop all patches
stg rebase upstream/main      # Rebase stack base
stg push -a                   # Reapply patches

# If conflicts occur during push:
# 1. Resolve conflicts in files
# 2. git add <resolved-files>
# 3. stg refresh
# 4. stg push -a              # Continue pushing remaining patches

# Update main branch
git checkout main
git merge stgit-migration
git push origin main
```

### When Patches Are Accepted Upstream

Use `--merged` flag to detect merged patches:

```bash
stg pull --merged
# or
stg rebase --merged upstream/main

# Merged patches become empty. To clean up:
stg series --empty            # Shows empty patches with '0' prefix
stg clean                     # Removes empty patches
```

### Modifying an Existing Patch

```bash
git checkout stgit-migration
stg goto <patch-name>         # Navigate to patch
# Make changes to files
stg refresh                   # Update patch with changes
stg refresh -e                # Update patch + edit commit message
stg push -a                   # Reapply remaining patches
```

### Creating a New Patch

```bash
git checkout stgit-migration
stg new <patch-name> -m "Short description"
# Make changes to files
stg refresh
```

### Useful Commands

```bash
stg series -d                 # List patches with descriptions
stg show <patch>              # Show patch diff
stg pop / stg push            # Navigate stack
stg goto <patch>              # Jump to specific patch
stg clean                     # Remove empty patches
stg commit <patch>            # Permanently commit patch to history
```

### Best Practices

1. **Rebase frequently** - Smaller conflict sets are easier to resolve
2. **Logical patch organization** - One feature/fix per patch
3. **Clear commit messages** - Follow conventional commits format
4. **Test after rebase** - Run `uv run pytest` after pushing patches

References: [StGit Tutorial](https://stacked-git.github.io/guides/tutorial/), [Xen StGit Guide](https://wiki.xenproject.org/wiki/Managing_Xen_Patches_with_StGit)

## Key Technologies
- Python
- Flask
- Flask
- FastAPI

## Development Guidelines
- Use kuzu-memory enhance for all AI interactions
- Store important decisions with kuzu-memory learn
- Query context with kuzu-memory recall when needed
- Keep memories project-specific and relevant

## Memory Guidelines

- Store project decisions and conventions
- Record technical specifications and API details
- Capture user preferences and patterns
- Document error solutions and workarounds

---

## Development Changelog (Commander Pro UI)

### 2026-01-17: Initial Commander Pro UI

**Branch:** `feature/commander-pro-ui`

**Commit `55049f7e`:** feat(commander): Add Pro UI with ANSI color support and tree view
- Added ansi_up library for terminal color rendering
- Implemented lazy initialization of AnsiUp to prevent load errors
- Made output container full height (100vh - 180px)
- Created new Pro UI at `/v2` with:
  - Compact tree view layout (Projects → Sessions)
  - Full-height output panel with ANSI color support
  - Live polling (1 second intervals)
  - Debug panel (Ctrl+D to toggle)
  - Session interaction toolbar

**Files changed:**
- `src/claude_mpm/commander/api/app.py` - Added /v2 routes
- `src/claude_mpm/commander/web/static/v2/` - New Pro UI (3 files)
- `src/claude_mpm/commander/web/static/app.js` - ANSI support
- `src/claude_mpm/commander/web/static/index.html` - ansi_up library
- `src/claude_mpm/commander/web/static/styles.css` - Terminal colors

---

### 2026-01-17: Tmux Windows statt Panes + Sync

**Commit:** feat(commander): Use tmux windows instead of panes, add sync endpoint

**Problem:**
- Sessions wurden als Panes erstellt → wurden zu klein bei vielen Sessions
- Keine Synchronisation zwischen tmux und Registry

**Lösung:**
1. **Windows statt Panes**: Jede Session bekommt eigenes tmux Window
   - `create_pane()` → deprecated, ruft `create_window()` auf
   - `list_panes()` → deprecated, ruft `list_windows()` auf
   - `kill_pane()` → deprecated, ruft `kill_window()` auf

2. **Sync Endpoint**: `POST /api/sessions/sync`
   - Prüft welche tmux Windows existieren
   - Aktualisiert Session-Status (running/stopped)
   - Wird bei Refresh-Button aufgerufen

**Files changed:**
- `src/claude_mpm/commander/tmux_orchestrator.py` - New window methods + sync
- `src/claude_mpm/commander/api/routes/sessions.py` - Sync endpoint
- `src/claude_mpm/commander/web/static/v2/app.js` - Refresh calls sync

---

*Generated by KuzuMemory Claude Hooks Installer*
