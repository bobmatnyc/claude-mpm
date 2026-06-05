# Trusty Search Integration

## Overview

Trusty Search is a high-performance semantic code search engine written in Rust, replacing `mcp-vector-search`. It provides AI-powered code discovery with vector embeddings, enabling natural language queries across codebases.

## Features

- **Semantic Code Search** - Find code by meaning, not just keywords
- **Opt-in Indexing** - Explicit index registration via CLI (no auto-indexing)
- **Multiple Search Modes**:
  - **Text-to-code**: Natural language queries ("authentication middleware")
  - **Code-to-code**: Find similar code patterns
  - **Contextual search**: Rich context with focus areas
- **Persistent Daemon** - Runs as launchd service on macOS
- **Fast Retrieval** - Sub-second searches across large codebases
- **Low Memory Footprint** - Efficient Rust implementation

## Prerequisites

- **Rust toolchain** - Required to build the Rust binary
  - Install from: https://rustup.rs/
  - Takes ~5 minutes to install
- **Cargo** - Comes with Rust installation
- Claude MPM installed
- Project directory initialized

## Installation

### Quick Setup

```bash
# From your project directory
claude-mpm setup trusty-search
```

This will:
1. Check for Rust/cargo installation
2. Install trusty-search Rust binary via cargo
3. Start daemon process on port 7878
4. Configure MCP server in `.mcp.json`
5. Make search tools available in Claude Code

**Note**: The daemon no longer auto-indexes projects. See [Index Management](#index-management) below to register your first project.

### What Gets Installed

- **Binary**: Rust binary compiled via `cargo install trusty-search`
- **Daemon**: Long-running process listening on `localhost:7878`
- **Config**: MCP configuration in `.mcp.json`
- **Index**: Project-specific search index

## Configuration

### MCP Configuration

Added to `.mcp.json`:

```json
{
  "mcpServers": {
    "trusty-search": {
      "command": "trusty-search",
      "args": ["mcp", "--port", "7878"],
      "env": {
        "TRUSTY_SEARCH_PORT": "7878"
      }
    }
  }
}
```

### Environment Variables

Optional environment variables:

- `TRUSTY_SEARCH_PORT` - Daemon port (default: 7878)
- `TRUSTY_SEARCH_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

### Daemon Management (macOS)

The setup process registers trusty-search as a launchd daemon:

```bash
# Service runs automatically at system startup
# Check status:
launchctl list | grep trusty-search

# Manually start/stop:
launchctl start trusty-search
launchctl stop trusty-search
```

## Usage

### MCP Tools in Claude Code

When using Claude Code, three search tools are available:

#### 1. search_code (Text-to-Code)

Find code using natural language:

```json
{
  "query": "authentication middleware",
  "file_extensions": [".py", ".js"],
  "language": "python",
  "limit": 10,
  "similarity_threshold": 0.3
}
```

**Example queries**:
- "user authentication logic"
- "database connection pooling"
- "error handling middleware"
- "API rate limiting"

#### 2. search_similar (Code-to-Code)

Find similar code patterns:

```json
{
  "file_path": "src/auth/handler.py",
  "function_name": "authenticate_user",
  "limit": 10,
  "similarity_threshold": 0.3
}
```

**Use cases**:
- Find duplicate implementations
- Discover similar patterns
- Locate related code
- Identify refactoring candidates

#### 3. search_context (Contextual Search)

Search with rich context and focus areas:

```json
{
  "description": "code handling user sessions",
  "focus_areas": ["security", "authentication"],
  "limit": 10
}
```

**Use cases**:
- Broad contextual searches
- Multi-aspect queries
- Exploratory code discovery
- Understanding code relationships

### MPM Search-Index Commands

MPM provides a dedicated command group for managing the trusty-search allowlist:

```bash
# Add a project to the allowlist
claude-mpm search-index add ~/Projects/my-app

# Alias: si (short form)
claude-mpm si add ~/Projects/my-app

# Add with a custom index name
claude-mpm search-index add ~/Projects/my-app --name my-project

# List all registered projects
claude-mpm search-index list

# Alias for list: ls
claude-mpm search-index ls

# Output as JSON
claude-mpm search-index list --json

# Remove a project from the allowlist
claude-mpm search-index remove ~/Projects/my-app

# Alias for remove: rm
claude-mpm search-index rm ~/Projects/my-app
```

### trusty-search Daemon Commands

After registering a project, use trusty-search CLI tools:

```bash
# Check daemon status
trusty-search status

# Index a project (after registration)
trusty-search index /path/to/project

# Search from command line
trusty-search search "authentication logic"

# View indexed projects
trusty-search list-projects
```

## Index Management

### Opt-in Indexing Model

trusty-search uses an **opt-in indexing model**: a directory is indexed only when explicitly registered via MPM. No auto-indexing occurs on daemon startup or project changes.

#### Adding a Project to the Index

```bash
# Register a project root for indexing
claude-mpm search-index add ~/Projects/my-app

# Register with an explicit index name (optional, default: directory basename)
claude-mpm search-index add ~/Projects/my-app --name my-app
```

This command:
1. Validates the path against a denylist of sensitive directories
2. Resolves the path to its canonical absolute form
3. Writes an entry to the trusty-search allowlist (`~/Library/Application Support/trusty-search/indexes.toml` on macOS)
4. Prints next steps (run `trusty-search index` inside the directory to trigger indexing)

After adding a project, trigger the initial index build:

```bash
cd ~/Projects/my-app
trusty-search index
```

#### Listing Registered Projects

```bash
# View all registered project roots
claude-mpm search-index list

# Output as JSON (for scripting)
claude-mpm search-index list --json
```

#### Removing a Project from the Index

```bash
# Unregister a project root
claude-mpm search-index remove ~/Projects/my-app
```

### Denylist: Paths Refused

MPM will refuse to add the following paths (security restriction):

- **System roots**: `$HOME` itself, `/`, `/tmp`, `/etc`, `/var`
- **Credential directories**: `~/.ssh`, `~/.aws`, `~/.gnupg`, `~/.config/gcloud`, `~/.kube`, `~/.docker`
- **Any directory containing a `.env` file** at the top level (prevents secret exposure)

If you try to register a denied path, you'll see an error:

```
Denied: Refusing to index '/Users/you': this path is in the sensitive-path denylist 
(home directory, /tmp, or a system root). Choose a specific project subdirectory instead.
```

### Manual Reindexing

After registering a project, force a full reindex when needed:

```bash
# Reindex current project
trusty-search index .

# Reindex specific directory
trusty-search index src/

# Clear and rebuild index
trusty-search clear
trusty-search index .
```

### Allowlist File Location and Schema

The opt-in allowlist is stored in a TOML file:

**Platform-specific locations:**

- **macOS**: `~/Library/Application Support/trusty-search/indexes.toml`
- **Linux**: `~/.local/share/trusty-search/indexes.toml`
- **Windows**: `%APPDATA%/trusty-search/indexes.toml`

**Override**: Set `TRUSTY_DATA_DIR` environment variable to use a custom location.

**Schema** (TOML array-of-tables format):

```toml
[[index]]
id = "my-project"
root_path = "/absolute/path/to/project"
colocated = true  # store index data inside <root_path>/.trusty-search/

# Additional optional fields:
# include_docs = true        # default: true
# respect_gitignore = true   # default: true
# lexical_only = false       # default: false
# skip_kg = false            # default: false
# include_paths = []         # subtree restrictions
# exclude_globs = []         # glob exclusions
# extensions = []            # extension allow-list
# domain_terms = []          # intent-classifier vocabulary
# path_filter = []           # subdirectory glob filter
```

**Example allowlist**:

```toml
[[index]]
id = "claude-mpm"
root_path = "/Users/you/Projects/claude-mpm"
colocated = true

[[index]]
id = "trusty-tools"
root_path = "/Users/you/Projects/trusty-tools"
colocated = true
```

You normally manage this file via `claude-mpm search-index add/list/remove` — direct TOML editing is supported but not recommended.

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| **Daemon startup** | ~2s | First time: build + start |
| **Initial indexing** | ~2s per 1000 files | One-time operation |
| **Search query** | <100ms | Sub-second response |
| **Incremental update** | <50ms per file | Efficient updates |

### Optimization Tips

1. **Exclude Large Directories**:
   ```bash
   trusty-search index . --exclude node_modules,dist,build
   ```

2. **Limit File Types**:
   ```bash
   trusty-search index . --extensions .py,.js,.ts
   ```

## Upgrading to Trusty Search

If you're using `mcp-vector-search` and want to migrate:

```bash
# Stop old service
claude-mpm setup mcp-vector-search --force  # or manual cleanup

# Install trusty-search
claude-mpm setup trusty-search

# Register your projects (required — no auto-indexing)
claude-mpm search-index add ~/Projects/my-app
claude-mpm search-index add ~/Projects/another-app

# Trigger initial indexing for each project
cd ~/Projects/my-app && trusty-search index
cd ~/Projects/another-app && trusty-search index

# Remove old index (optional)
rm -rf .vector-index/
```

## Troubleshooting

### Rust Not Installed

```bash
# Install Rust from https://rustup.rs/
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Reload shell
source ~/.cargo/env
```

### Daemon Not Starting

```bash
# Check logs
tail -f ~/.trusty-search/logs/daemon.log

# Restart daemon
launchctl stop trusty-search
launchctl start trusty-search
```

### Port Already in Use

```bash
# Check what's using port 7878
lsof -i :7878

# Kill process or use different port
export TRUSTY_SEARCH_PORT=7879
claude-mpm setup trusty-search --force
```

### No Search Results

Check:
1. Index exists: `trusty-search list-projects`
2. Project is registered: `trusty-search status`
3. Query specificity: Try broader terms
4. Threshold: Lower `similarity_threshold`

## Supported Languages

Optimized for:
- Python, JavaScript, TypeScript
- Go, Rust, Java, C++
- Ruby, PHP, C#
- HTML, CSS, SQL
- Markdown, YAML, JSON

## Integration with Claude MPM

Trusty Search integrates with:

- **PM Agent** - Automatic code discovery before file reading
- **Session Resume** - Search available in resumed sessions
- **Semantic Workflows** - Context-aware task routing

## Force Upgrade

To force reinstall or upgrade the binary:

```bash
# Force reinstall from scratch
claude-mpm setup trusty-search --force
```

This will:
1. Rebuild the Rust binary via cargo
2. Restart daemon
3. Update `.mcp.json`

**Note**: The allowlist is preserved. Your registered projects will remain active. If you need to re-register projects, use `claude-mpm search-index add` again.

## Further Reading

- [Trusty Search GitHub](https://github.com/trusty-search/trusty-search)
- [Semantic Search Guide](../guides/semantic-search.md)
- [PM Agent Documentation](../agents/pm.md)

---

[Back to Integrations](README.md) | [Documentation Index](../README.md)
