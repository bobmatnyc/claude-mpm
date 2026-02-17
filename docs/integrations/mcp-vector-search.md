# MCP Vector Search Integration

## Overview

MCP Vector Search provides semantic code search capabilities using vector embeddings, enabling AI-powered code discovery and contextual understanding of codebases.

## Features

- **Semantic Code Search** - Find code by meaning, not just keywords
- **Automatic Indexing** - Codebases indexed on startup
- **Multiple Search Modes**:
  - **Text-to-code**: Natural language queries ("authentication middleware")
  - **Code-to-code**: Find similar code patterns
  - **Contextual search**: Rich context with focus areas
- **PM Integration** - Project Manager agent uses vector search before Read/Research
- **Fast Retrieval** - Sub-second searches across large codebases

## Installation

### Prerequisites

- Python 3.11-3.13
- Claude MPM installed
- Project directory initialized

### Quick Setup

```bash
# From your project directory
claude-mpm setup mcp-vector-search
```

This will:
1. Install mcp-vector-search package
2. Configure MCP server in `.mcp.json`
3. Enable automatic indexing
4. Make search tools available in Claude Code

### Manual Installation

```bash
# Install with uv
uv tool install mcp-vector-search --python 3.13

# Or with pipx
pipx install mcp-vector-search

# Or with pip
pip install --user mcp-vector-search
```

## Configuration

### MCP Configuration

Added to `.mcp.json`:

```json
{
  "mcpServers": {
    "mcp-vector-search": {
      "command": "uvx",
      "args": ["mcp-vector-search"],
      "env": {
        "VECTOR_SEARCH_INDEX_PATH": "/path/to/project/.vector-index"
      }
    }
  }
}
```

### Environment Variables

Optional environment variables:

- `VECTOR_SEARCH_INDEX_PATH` - Custom index location (default: `.vector-index/`)
- `VECTOR_SEARCH_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `VECTOR_SEARCH_MODEL` - Embedding model to use (default: sentence-transformers)

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
# Check index status
mcp-vector-search status

# Reindex codebase
mcp-vector-search index

# Search from command line
mcp-vector-search search "authentication logic"

# Clear index
mcp-vector-search clear
```

## PM Agent Integration

The Project Manager (PM) agent automatically uses vector search:

```
User: "Find the authentication code"

PM Agent:
1. Uses search_code("authentication") first
2. Discovers relevant files via semantic search
3. Reads specific files if needed
4. Responds with accurate context
```

This is **significantly faster** than:
- Reading entire codebase
- Using grep/glob patterns
- Manual file exploration

## Index Management

### Automatic Indexing

Vector search automatically indexes:
- On first startup in project
- When new files are detected
- When file modifications occur
- Periodic refresh (configurable)

### Manual Reindexing

Force reindex when needed:

```bash
# Full reindex
mcp-vector-search index --force

# Index specific directory
mcp-vector-search index --path src/

# Index specific file types
mcp-vector-search index --extensions .py,.js
```

### Index Location

Default index location:

```
<project-root>/.vector-index/
├── embeddings/
│   ├── code_embeddings.npy
│   └── metadata.json
├── index/
│   └── faiss_index.bin
└── config.yaml
```

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| **Initial Indexing** | ~1s per 100 files | Depends on file size |
| **Search Query** | <100ms | Sub-second response |
| **Index Load** | <500ms | Fast startup |
| **Incremental Update** | <50ms per file | Efficient updates |

### Optimization Tips

1. **Exclude Large Files**:
   ```yaml
   # .vector-search-config.yaml
   exclude:
     - "*.min.js"
     - "node_modules/**"
     - "dist/**"
   ```

2. **Limit File Types**:
   ```yaml
   include:
     - "*.py"
     - "*.js"
     - "*.ts"
     - "*.go"
   ```

3. **Configure Batch Size**:
   ```yaml
   indexing:
     batch_size: 100
     max_file_size: 1048576  # 1MB
   ```

## Search Quality

### Similarity Threshold

Control search precision:

- `0.1` - Very relaxed (many results)
- `0.3` - Balanced (default)
- `0.5` - Strict (precise results)
- `0.7` - Very strict (only close matches)

### Result Ranking

Results ranked by:
1. Semantic similarity score
2. File relevance
3. Code context
4. Recent modifications (optional)

## Troubleshooting

### No Results

Check:
1. Index exists: `ls .vector-index/`
2. Indexing completed: `mcp-vector-search status`
3. Query specificity: Try broader terms
4. Threshold: Lower `similarity_threshold`

### Slow Indexing

Optimize:
1. Exclude unnecessary directories
2. Limit file types
3. Reduce batch size
4. Check disk space

### Index Corruption

Reset:
```bash
# Remove index
rm -rf .vector-index/

# Reindex
mcp-vector-search index --force
```

## Supported Languages

Optimized for:
- Python, JavaScript, TypeScript
- Go, Rust, Java, C++
- Ruby, PHP, C#
- HTML, CSS, SQL
- Markdown, YAML, JSON

## Integration with Other Tools

### With Kuzu-Memory

Vector search + memory:
```
User query → Vector search (find code)
           ↓
           Memory system (find context)
           ↓
           Enhanced response
```

### With MCP Ticketer

Search code related to tickets:
```python
# Find code related to ticket
search_code("TSK-123 implementation")
```

### With PM Agent

PM automatically combines:
1. Vector search for code discovery
2. File reading for details
3. Memory for project context

## Best Practices

### Query Formulation

**Good queries**:
- "user authentication middleware"
- "database connection handling"
- "error logging utility"

**Poor queries**:
- "code" (too broad)
- "function" (too generic)
- "abc123" (meaningless)

### Index Maintenance

1. **Regular reindex**: Weekly or after major changes
2. **Exclude generated code**: Build artifacts, minified files
3. **Monitor index size**: Keep under 100MB for performance
4. **Version control**: Add `.vector-index/` to `.gitignore`

## Advanced Configuration

### Custom Embedding Model

```yaml
# .vector-search-config.yaml
model:
  name: "sentence-transformers/all-mpnet-base-v2"
  device: "cuda"  # or "cpu"
  batch_size: 32
```

### Search Options

```yaml
search:
  default_limit: 10
  max_limit: 50
  similarity_threshold: 0.3
  enable_reranking: true
```

## Further Reading

- [MCP Vector Search PyPI](https://pypi.org/project/mcp-vector-search/)
- [Semantic Search Guide](../guides/semantic-search.md)
- [PM Agent Documentation](../agents/pm.md)

---

[Back to Integrations](README.md) | [Documentation Index](../README.md)
