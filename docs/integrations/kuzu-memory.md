# Kuzu Memory Integration

## Overview

Kuzu Memory provides graph-based semantic memory for Claude MPM, replacing static file-based memory with a powerful knowledge graph that enables semantic search and enhanced context management.

## Features

- **Semantic Memory Storage** - Store project knowledge in a graph database
- **Semantic Search** - Retrieve relevant context using natural language queries
- **Project-Scoped** - Each project maintains its own memory database
- **Automatic Indexing** - Memories are automatically indexed for fast retrieval
- **Context Enhancement** - Automatically enriches prompts with relevant project memories

## Installation

### Prerequisites

- Python 3.11-3.13
- Claude MPM installed
- Project directory initialized

### Quick Setup

```bash
# From your project directory
claude-mpm setup kuzu-memory
```

This will:
1. Install kuzu-memory (v1.6.33+) if not already present
2. Create project-local configuration in `.claude-mpm/configuration.yaml`
3. Set memory backend to 'kuzu' for this project only
4. Create database directory at `kuzu-memories/`
5. Enable subservient mode (MPM controls hooks, project-only)
6. Migrate existing static memory files if present

## Configuration

### Project Configuration

Kuzu-memory is configured in `.claude-mpm/configuration.yaml`:

```yaml
memory:
  backend: kuzu
  kuzu:
    project_root: /path/to/project
    db_path: /path/to/project/kuzu-memories
```

### Subservient Mode

Claude MPM creates a `.kuzu-memory-config` file to indicate kuzu-memory is managed:

```yaml
mode: subservient
managed_by: claude-mpm
version: "1.0"
```

This ensures:
- MPM controls when hooks are active
- Configuration is project-only (not system-wide)
- No conflicts with other projects

## Usage

### Automatic Memory Storage

Memories are automatically stored during Claude MPM sessions:

```bash
# Start session - memories auto-stored
claude-mpm
```

### Manual Memory Operations

```bash
# Query memories
kuzu-memory recall "authentication implementation"

# Store learning
kuzu-memory learn "Project uses OAuth2 with PKCE flow"

# View statistics
kuzu-memory stats
```

### MCP Tools

When using Claude Code, kuzu-memory MCP tools are available:

- `kuzu_enhance` - Enhance prompts with project memories
- `kuzu_learn` - Store new learnings asynchronously
- `kuzu_recall` - Query specific memories
- `kuzu_stats` - Get memory system statistics

## Database Location

Memory database is stored at:

```
<project-root>/kuzu-memories/
```

This directory contains:
- Graph database files (`.kuzu` format)
- Embedding indexes
- Metadata

## Migration from Static Memory

If you have existing static memory files in `.claude-mpm/memories/*.md`, the setup command will:

1. Automatically detect and migrate each memory file
2. Preserve agent associations via metadata
3. Create backup at `.claude-mpm/memories_backup/`
4. Import memories into kuzu-memory graph

## Environment Variables

Optional environment variables:

- `KUZU_DB_PATH` - Override database location
- `KUZU_LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)

## Troubleshooting

### Installation Issues

If installation fails:

```bash
# Check installation method detection
claude-mpm doctor installation

# Try manual installation
uv tool install kuzu-memory>=1.6.33 --python 3.13
# or
pipx install kuzu-memory
```

### Memory Not Loading

Verify configuration:

```bash
# Check configuration
cat .claude-mpm/configuration.yaml

# Verify database exists
ls -la kuzu-memories/
```

### Reset Memory Database

To start fresh:

```bash
# Backup current database
mv kuzu-memories kuzu-memories.backup

# Re-run setup
claude-mpm setup kuzu-memory
```

## Benefits Over Static Memory

| Feature | Static Files | Kuzu Memory |
|---------|-------------|-------------|
| **Search** | Full-text only | Semantic + full-text |
| **Relationships** | None | Graph-based |
| **Scalability** | Limited | Excellent |
| **Context** | Manual | Automatic |
| **Versioning** | Manual | Built-in |

## Performance

- **Storage**: ~1MB per 1000 memories
- **Search**: <100ms for semantic queries
- **Indexing**: ~10ms per memory stored
- **Startup**: <500ms to load database

## Integration with Claude MPM

Kuzu-memory integrates with:

- **Memory Hooks** - Automatic storage during sessions
- **Prompt Enhancement** - Context injection in prompts
- **Agent Memory** - Per-agent memory namespaces
- **Session Resume** - Memory context in resumed sessions

## Project Isolation

Each project has independent memory:

- Separate database per project
- Project-specific configuration
- No cross-project contamination
- Hooks active only in project directory

## Further Reading

- [Kuzu Memory PyPI](https://pypi.org/project/kuzu-memory/)
- [Memory System Design](../design/memory-system.md)
- [Configuration Guide](../configuration/memory.md)

---

[Back to Integrations](README.md) | [Documentation Index](../README.md)
