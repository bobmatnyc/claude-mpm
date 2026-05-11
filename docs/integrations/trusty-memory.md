# Trusty Memory Integration

## Overview

Trusty Memory is a high-performance semantic memory system written in Rust, replacing `kuzu-memory`. It provides graph-based memory storage with powerful search capabilities for managing project context and learnings.

## Features

- **Semantic Memory Storage** - Store and retrieve project knowledge with meaning-based search
- **Graph Database** - Relationships between memories enable deeper context understanding
- **Persistent Daemon** - Runs as launchd service on macOS
- **Automatic Indexing** - Memories automatically indexed for fast retrieval
- **Context Enhancement** - Enrich prompts with relevant project memories
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
claude-mpm setup trusty-memory
```

This will:
1. Check for Rust/cargo installation
2. Install trusty-memory Rust binary via cargo
3. Start daemon process on port 3038
4. Create project "palace" (memory namespace)
5. Configure MCP server in `.mcp.json`
6. Make memory tools available in Claude Code

### What Gets Installed

- **Binary**: Rust binary compiled via `cargo install trusty-memory`
- **Daemon**: Long-running process listening on `localhost:3038`
- **Config**: MCP configuration in `.mcp.json`
- **Palace**: Project-specific memory namespace (database)

## Configuration

### MCP Configuration

Added to `.mcp.json`:

```json
{
  "mcpServers": {
    "trusty-memory": {
      "command": "trusty-memory",
      "args": ["mcp", "--port", "3038"],
      "env": {
        "TRUSTY_MEMORY_PORT": "3038"
      }
    }
  }
}
```

### Project Palace

Trusty Memory organizes memories into "palaces" (namespaces):

- **Project Palace**: Located at `.trusty-memory/palace/`
- **Each project**: Gets its own isolated palace
- **No cross-project contamination**: Memories stay in project
- **Portable**: Palace directory can be backed up or shared

### Environment Variables

Optional environment variables:

- `TRUSTY_MEMORY_PORT` - Daemon port (default: 3038)
- `TRUSTY_MEMORY_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `TRUSTY_MEMORY_PALACE_PATH` - Custom palace location

### Daemon Management (macOS)

The setup process registers trusty-memory as a launchd daemon:

```bash
# Service runs automatically at system startup
# Check status:
launchctl list | grep trusty-memory

# Manually start/stop:
launchctl start trusty-memory
launchctl stop trusty-memory
```

## Usage

### Automatic Memory Storage

Memories are automatically stored during Claude MPM sessions when integrated with hooks.

### Manual Memory Operations

```bash
# Query memories (semantic search)
trusty-memory recall "authentication implementation"

# Store learning
trusty-memory learn "Project uses OAuth2 with PKCE flow"

# View statistics
trusty-memory stats

# List all memories
trusty-memory list
```

### MCP Tools in Claude Code

When using Claude Code, trusty-memory MCP tools are available:

- **trusty_enhance** - Enhance prompts with project memories
- **trusty_learn** - Store new learnings asynchronously
- **trusty_recall** - Query specific memories semantically
- **trusty_stats** - Get memory system statistics
- **trusty_remember** - Store critical facts with confirmation

## Database Location

Memory palace (database) is stored at:

```
<project-root>/.trusty-memory/
├── palace/
│   ├── graph.db
│   ├── embeddings/
│   └── metadata.json
└── config.yaml
```

Each project maintains its own isolated palace.

## Memory Organization

Trusty Memory organizes memories into categories:

- **Identity** - Project identity and context
- **Preference** - User and project preferences
- **Decision** - Architectural and technical decisions
- **Pattern** - Code patterns and conventions

## Usage Examples

### Store a Learning

```bash
# Asynchronous learning (background storage)
trusty-memory learn "Authentication uses JWT tokens with RS256"

# Critical fact (immediate confirmation)
trusty-memory remember "Main database is PostgreSQL 14" --importance 0.9
```

### Query Memories

```bash
# Semantic search
trusty-memory recall "How are users authenticated?"

# Get statistics
trusty-memory stats

# View all memories
trusty-memory list --category pattern
```

### In Claude Code

Use MCP tools directly:

```python
# Enhance prompt with memories
kuzu_enhance(prompt="Implement authentication")

# Store learning asynchronously
kuzu_learn(content="Project uses PKCE flow for OAuth")

# Recall specific memory
kuzu_recall(query="Session management patterns")
```

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| **Daemon startup** | ~1s | Quick startup |
| **Memory storage** | <10ms | Single memory |
| **Semantic search** | <100ms | Fast retrieval |
| **Memory indexing** | ~5ms per memory | Efficient updates |

## Upgrading from Kuzu-Memory

If you're using `kuzu-memory` and want to migrate:

```bash
# Backup old memory
mv kuzu-memories kuzu-memories.backup

# Install trusty-memory
claude-mpm setup trusty-memory

# Migration is automatic - new system starts fresh
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
tail -f ~/.trusty-memory/logs/daemon.log

# Restart daemon
launchctl stop trusty-memory
launchctl start trusty-memory
```

### Port Already in Use

```bash
# Check what's using port 3038
lsof -i :3038

# Kill process or use different port
export TRUSTY_MEMORY_PORT=3039
claude-mpm setup trusty-memory --force
```

### Memory Not Loading

Verify configuration and palace:

```bash
# Check palace exists
ls -la .trusty-memory/

# Verify daemon is running
trusty-memory status

# Check palace contents
trusty-memory list
```

## Palace Backup and Restore

### Backup

```bash
# Backup your palace
cp -r .trusty-memory .trusty-memory.backup

# Or archive for sharing
tar -czf project-palace.tar.gz .trusty-memory/
```

### Restore

```bash
# From backup
cp -r .trusty-memory.backup .trusty-memory

# From archive
tar -xzf project-palace.tar.gz
```

## Reset Memory Palace

To start fresh:

```bash
# Backup current palace (optional)
mv .trusty-memory .trusty-memory.backup

# Re-run setup to create new palace
claude-mpm setup trusty-memory
```

## Integration with Claude MPM

Trusty Memory integrates with:

- **Session Resume** - Memory context in resumed sessions
- **Hook System** - Automatic memory capture during work
- **Prompt Enhancement** - Context injection in prompts
- **Project Context** - Foundation for project understanding

## Project Isolation

Each project has independent memory:

- Separate palace per project
- Project-specific configuration
- No cross-project contamination
- Portable memory units

## Force Upgrade

To force reinstall or upgrade the binary:

```bash
# Force reinstall from scratch
claude-mpm setup trusty-memory --force
```

This will:
1. Rebuild the Rust binary via cargo
2. Restart daemon
3. Create new project palace
4. Update `.mcp.json`

## Memory Optimization

### View Statistics

```bash
# See palace statistics
trusty-memory stats

# Check memory count and size
trusty-memory list --verbose
```

### Cleanup

```bash
# Archive old memories (not yet implemented in v1.0)
# For now: backup and fresh start with reset
```

## Further Reading

- [Trusty Memory GitHub](https://github.com/trusty-memory/trusty-memory)
- [Memory System Design](../design/memory-system.md)
- [Configuration Guide](../configuration/memory.md)

---

[Back to Integrations](README.md) | [Documentation Index](../README.md)
