---
name: trusty-memory
description: "Persistent memory palace system with hierarchical storage (palace/wing/room/closet/drawer), progressive retrieval (L0-L3), and temporal knowledge graph for cross-session context"
user-invocable: false
disable-model-invocation: false
license: Apache-2.0
compatibility: claude-code
---

# trusty-memory

Persistent memory system using the **Memory Palace** metaphor for organizing context across sessions. Replaces `mcp__kuzu-memory__*` tools.

## When to Use

- **Session start**: Recall relevant context for the current task
- **Decision moments**: Store key architectural/design decisions
- **Learning capture**: Remember new patterns, conventions, gotchas discovered
- **Relationship tracking**: Assert facts in the knowledge graph (X depends on Y, A replaces B)
- **Session end**: Persist outcomes and next steps

**Do NOT use for**: ephemeral scratch notes, code snippets (use trusty-search), or content that belongs in source files.

## Architecture

```
Palace (project)     e.g. "claude-mpm"
  └── Wing (area)    e.g. "Backend"
        └── Room     e.g. "Backend", "Frontend", "Testing", "Planning",
                          "Documentation", "Research", "Configuration",
                          "Meetings", "General"
              └── Closet (sub-category)
                    └── Drawer (memory item: uuid, content, tags, importance)
```

### Progressive Retrieval Layers

| Layer | Tokens | When | Trigger |
|-------|--------|------|---------|
| L0 | ~100 | Always | Identity / project context auto-loaded |
| L1 | ~800 | Always | Top-15 drawers by importance auto-loaded |
| L2 | variable | On topic match | `memory_recall` — metadata-filtered vector search |
| L3 | exhaustive | Explicit | `memory_recall_deep` — full HNSW deep search |

**Always try `memory_recall` first.** Escalate to `memory_recall_deep` only if results are insufficient.

## Tool Reference

### Retrieval

**`memory_recall`** — Fast progressive retrieval (L0+L1+L2). Use this first.
```
mcp__trusty-memory__memory_recall(
  query="how does the migration registry work",
  room="Backend",        # optional filter
  limit=10               # optional
)
```

**`memory_recall_deep`** — Full HNSW deep search (L3). Use when `memory_recall` insufficient.
```
mcp__trusty-memory__memory_recall_deep(
  query="rare edge case in hook dispatcher",
  limit=20
)
```

**`memory_list`** — Browse drawers by room/tag (no semantic query).
```
mcp__trusty-memory__memory_list(room="Planning", tag="release-workflow")
```

### Storage

**`memory_remember`** — Store a drawer.
```
mcp__trusty-memory__memory_remember(
  content="The migration runner uses run_pending_migrations() at startup; state in ~/.claude-mpm/migrations.json",
  room="Backend",
  tags=["migrations", "startup"],
  importance=0.8         # 0.0-1.0; higher = more likely to appear in L1
)
```

**`memory_forget`** — Delete by UUID.
```
mcp__trusty-memory__memory_forget(drawer_id="<uuid>")
```

### Palace Management

```
mcp__trusty-memory__palace_list()
mcp__trusty-memory__palace_info(palace="claude-mpm")
mcp__trusty-memory__palace_create(name="new-project")
```

### Knowledge Graph (temporal triples)

**`kg_assert`** — Assert a `(subject, predicate, object)` fact.
```
mcp__trusty-memory__kg_assert(
  subject="trusty-memory",
  predicate="replaces",
  object="kuzu-memory"
)
```

**`kg_query`** — Query triples for a subject.
```
mcp__trusty-memory__kg_query(subject="trusty-memory")
```

## Room Type Selection

| Room | Use For |
|------|---------|
| **Backend** | Server-side logic, APIs, services, data layer |
| **Frontend** | UI, components, styling, client-state |
| **Testing** | Test patterns, fixtures, flaky test notes, coverage decisions |
| **Planning** | Roadmaps, architectural decisions, ticket plans |
| **Documentation** | Doc conventions, README structure, public API docs |
| **Research** | Investigations, spike findings, library evaluations |
| **Configuration** | Build setup, env vars, deploy config, tooling |
| **Meetings** | Decisions from sync calls, action items |
| **General** | Cross-cutting concerns, miscellaneous |

When unsure, prefer the most-specific room. Tags handle the rest.

## KG Triple Patterns

Use consistent predicates for queryable graphs:

| Predicate | Example |
|-----------|---------|
| `replaces` | `(trusty-memory, replaces, kuzu-memory)` |
| `depends_on` | `(release-publish, depends_on, gh-account-bobmatnyc)` |
| `implements` | `(migration_runner, implements, run_pending_migrations)` |
| `documented_in` | `(release_workflow, documented_in, CLAUDE.md)` |
| `owned_by` | `(planner-agent, owned_by, .claude/agents/planner.md)` |
| `version_of` | `(6.2.67, version_of, claude-mpm)` |
| `triggers` | `(SessionStart, triggers, model_tier_hook)` |

## Workflow Protocols

### Session Start Protocol

1. **Auto-loaded**: L0 identity + L1 top-15 drawers appear in context automatically.
2. **Targeted recall**: For task-specific context:
   ```
   memory_recall(query="<current task domain>", limit=10)
   ```
3. **Check KG** for relevant entity relationships:
   ```
   kg_query(subject="<entity being modified>")
   ```

### Session End Protocol

For each significant outcome, persist it:

1. **Decisions** → `memory_remember` with high importance (0.7-0.9)
   ```
   memory_remember(
     content="Decided to consolidate hook scripts under claude-hook-fast.sh; old per-event scripts deprecated",
     room="Backend",
     tags=["hooks", "decision"],
     importance=0.85
   )
   ```

2. **Relationships** → `kg_assert`
   ```
   kg_assert(subject="claude-hook-fast.sh", predicate="replaces", object="per-event-hook-scripts")
   ```

3. **Gotchas / learnings** → `memory_remember` with tags for discoverability
   ```
   memory_remember(
     content="release-publish requires `claude-mpm gh switch` to bobmatnyc first; bob-duetto account causes auth failures",
     room="Configuration",
     tags=["release", "gotcha", "github-auth"],
     importance=0.9
   )
   ```

### Recall vs Recall-Deep Decision

| Situation | Use |
|-----------|-----|
| Standard context lookup | `memory_recall` |
| Top-N relevant results enough | `memory_recall` |
| `memory_recall` returned <3 hits | `memory_recall_deep` |
| Investigating obscure / rare topic | `memory_recall_deep` |
| Need exhaustive coverage of a concept | `memory_recall_deep` |

## Importance Scoring

| Score | Type |
|-------|------|
| 0.9-1.0 | Critical: release gotchas, security constraints, hard rules |
| 0.7-0.9 | Architectural decisions, major patterns |
| 0.5-0.7 | Useful conventions, common patterns |
| 0.3-0.5 | Project trivia, minor preferences |
| 0.0-0.3 | Ephemeral, rarely-useful |

L1 surfaces the top 15 by importance — score accordingly.

## Migration from kuzu-memory

| Old | New |
|-----|-----|
| `mcp__kuzu-memory__kuzu_recall` | `mcp__trusty-memory__memory_recall` |
| `mcp__kuzu-memory__kuzu_learn` | `mcp__trusty-memory__memory_remember` |
| `mcp__kuzu-memory__kuzu_remember` | `mcp__trusty-memory__memory_remember` |
| `mcp__kuzu-memory__kuzu_project_context` | Auto-loaded via L0 |
| `mcp__kuzu-memory__kuzu_stats` | `mcp__trusty-memory__palace_info` |

## Integration with trusty-search

Common pattern: search → understand → remember.

```
# 1. Find code with trusty-search
search_code(query="migration runner", query_type="Definition")

# 2. After investigating, persist the learning
memory_remember(
  content="Migration runner pattern: registry.py registers each migrate_*.py module; run_pending_migrations iterates by version",
  room="Backend",
  tags=["migrations", "pattern"],
  importance=0.75
)
```

## Best Practices

- **Be specific**: "Release workflow requires bobmatnyc gh account" beats "Check gh account before releasing"
- **Include WHY**: Decision rationale beats decision alone
- **Tag generously**: Tags enable cross-room discovery
- **Use KG for relationships**: Don't bury "X replaces Y" in prose — assert it
- **Update over duplicate**: Forget stale drawers when superseded
- **Prefer recall over recall_deep**: Save the expensive call for when you need it
