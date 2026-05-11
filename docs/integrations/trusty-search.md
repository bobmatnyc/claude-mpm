# Trusty Search Integration

## Overview

Trusty Search is a high-performance semantic code search engine written in Rust, replacing `mcp-vector-search`. It provides AI-powered code discovery with vector embeddings, enabling natural language queries across codebases.

## Features

- **Semantic Code Search** - Find code by meaning, not just keywords
- **Automatic Indexing** - Codebases indexed on demand
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
4. Register project index in trusty-search
5. Configure MCP server in `.mcp.json`
6. Make search tools available in Claude Code

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

### CLI Commands

```bash
# Check daemon status
trusty-search status

# Index a project
trusty-search index /path/to/project

# Search from command line
trusty-search search "authentication logic"

# View indexed projects
trusty-search list-projects
```

## Index Management

### Automatic Indexing

When you run `claude-mpm setup trusty-search`:
1. Project root is registered with daemon
2. Full codebase is indexed
3. Index stored in daemon's local cache
4. Search tools become available

### Manual Reindexing

Force reindex when needed:

```bash
# Reindex current project
trusty-search index .

# Reindex specific directory
trusty-search index src/

# Clear and rebuild index
trusty-search clear
trusty-search index .
```

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
3. Re-register project index
4. Update `.mcp.json`

## Further Reading

- [Trusty Search GitHub](https://github.com/trusty-search/trusty-search)
- [Semantic Search Guide](../guides/semantic-search.md)
- [PM Agent Documentation](../agents/pm.md)

---

[Back to Integrations](README.md) | [Documentation Index](../README.md)
