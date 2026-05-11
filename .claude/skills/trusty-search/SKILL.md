---
name: trusty-search
description: "Hybrid code search (BM25 + vector + KG) with RRF fusion. Single daemon serves multiple named indexes. Replaces mcp-vector-search."
user-invocable: false
disable-model-invocation: false
license: Apache-2.0
compatibility: claude-code
---

# trusty-search

Hybrid semantic + lexical + relational code search. Replaces `mcp__mcp-vector-search__*` tools.

## When to Use

- **Locate code**: "Where is X defined?" / "How is X used?"
- **Explore concepts**: "How does the migration system work?"
- **Find tech debt**: "Where are the TODOs / FIXMEs?"
- **Q&A over codebase**: Use `chat` for synthesized answers with citations.

**Do NOT use for**: persistent memory (use trusty-memory), edits (use Edit), or shell-level file listing.

## Architecture

- **Single daemon** at `http://127.0.0.1:7878` serves all projects.
- **Named indexes** — one per project: `claude-mpm`, `cto`, `duetto`, `open-mpm`, `rust-dre`, etc.
- **Hybrid retrieval**:
  - **BM25** — lexical/keyword precision
  - **HNSW** — vector semantic similarity
  - **KG** — knowledge graph relational signals
  - Fused with **Reciprocal Rank Fusion (RRF)**

## Query Type Routing

`search_code` accepts a `query_type` hint that biases the fusion weights. Always specify it.

| `query_type` | Use For | Bias |
|--------------|---------|------|
| `Definition` | "Where is `run_pending_migrations` defined?" | BM25 precision |
| `Usage` | "How is the planner agent invoked?" | Vector similarity |
| `Conceptual` | "How does the migration system work?" | Balanced BM25+vector+KG |
| `BugDebt` | "Show me the TODOs / hacks" | Keyword match |

If unspecified, the daemon auto-routes — but explicit is better.

## Tool Reference

### Search

**`search_code`** — primary tool.
```
mcp__trusty-search__search_code(
  query="migration registry",
  index="claude-mpm",
  query_type="Definition",
  limit=10
)
```

**`chat`** — LLM-powered Q&A over the index with citations.
```
mcp__trusty-search__chat(
  index="claude-mpm",
  question="How does the hook dispatcher route PreToolUse events?"
)
```

### Index Management

```
mcp__trusty-search__list_indexes()
mcp__trusty-search__create_index(name="new-project", root="/abs/path")
mcp__trusty-search__delete_index(name="old-project")
mcp__trusty-search__index_status(index="claude-mpm")
mcp__trusty-search__reindex(index="claude-mpm")
mcp__trusty-search__index_file(index="claude-mpm", path="src/foo.py")
mcp__trusty-search__remove_file(index="claude-mpm", path="src/old.py")
```

### Health

```
mcp__trusty-search__search_health()
# Returns daemon liveness + uptime.
```

## When to Use `search_code` vs `chat`

| Need | Tool |
|------|------|
| List of matching files/symbols | `search_code` |
| Quick lookup, then read source | `search_code` |
| Synthesized explanation across many files | `chat` |
| Citations and a narrative answer | `chat` |
| Bulk grep replacement | `search_code` with `query_type="Definition"` |

`search_code` is cheap; `chat` is more expensive. Prefer `search_code` + targeted `Read` when feasible.

## Index Health Workflow

```
# 1. Confirm daemon up
search_health()

# 2. Confirm index registered and healthy
index_status(index="claude-mpm")

# 3. If stale or recently changed many files:
reindex(index="claude-mpm")

# 4. For single-file invalidation after edit:
index_file(index="claude-mpm", path="src/claude_mpm/foo.py")
```

If `search_health` fails: the daemon is not running. Start it externally (`trusty-search serve`). The MCP transport assumes the daemon is already serving.

## Example Calls

### Definition lookup
```
search_code(
  query="run_pending_migrations",
  index="claude-mpm",
  query_type="Definition",
  limit=5
)
```

### Conceptual exploration
```
search_code(
  query="how hooks get dispatched after tool use",
  index="claude-mpm",
  query_type="Conceptual",
  limit=15
)
```

### Tech debt audit
```
search_code(
  query="TODO FIXME XXX HACK",
  index="claude-mpm",
  query_type="BugDebt",
  limit=50
)
```

### Q&A
```
chat(
  index="claude-mpm",
  question="What invariants does the migration registry enforce on migration IDs?"
)
```

## Integration with trusty-memory

Search → understand → remember. After investigation, persist learnings.

```
# 1. Find code
search_code(query="model_tier_hook", index="claude-mpm", query_type="Definition")

# 2. Read and understand the code (use Read tool)

# 3. Persist the learning
mcp__trusty-memory__memory_remember(
  content="model_tier_hook enforces planner→claude-opus-4-7 routing; config at ~/.claude-mpm/config/configuration.yaml models.planning",
  room="Backend",
  tags=["hooks", "model-tier", "planner"],
  importance=0.8
)

# 4. Optionally assert relationship in KG
mcp__trusty-memory__kg_assert(
  subject="model_tier_hook",
  predicate="enforces",
  object="planner-model-routing"
)
```

## Migration from mcp-vector-search

| Old | New |
|-----|-----|
| `mcp__mcp-vector-search__search_code` | `mcp__trusty-search__search_code` |
| `mcp__mcp-vector-search__index_project` | `mcp__trusty-search__create_index` + `reindex` |
| `mcp__mcp-vector-search__get_project_status` | `mcp__trusty-search__index_status` |
| `mcp__mcp-vector-search__search_similar` | `search_code` with `query_type="Usage"` |
| `mcp__mcp-vector-search__search_context` | `search_code` with `query_type="Conceptual"` or `chat` |
| `mcp__mcp-vector-search__search_hybrid` | `search_code` (hybrid is default) |

## Best Practices

- **Always pass `index`**: the daemon hosts many projects; omitting `index` is ambiguous.
- **Specify `query_type`**: it materially improves ranking.
- **Start narrow**: `limit=10` for `search_code`, then expand if needed.
- **Reindex sparingly**: full reindex is expensive — prefer `index_file` for single-file updates.
- **Verify before claiming**: check `search_health` if results seem stale or empty.
- **Pair with memory**: search to find, memory to remember.
