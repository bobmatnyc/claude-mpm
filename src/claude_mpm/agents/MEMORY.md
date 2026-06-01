<!-- PURPOSE: Memory system for retaining project knowledge -->

## Memory System

**MCP backends** (use whichever is active):
- **trusty-memory** (primary): `mcp__trusty-memory__memory_recall` / `mcp__trusty-memory__memory_remember`
- **kuzu-memory** (legacy fallback): `mcp__kuzu-memory__kuzu_recall` / `mcp__kuzu-memory__kuzu_remember`

**Static fallback** (when no MCP backend configured): PM directly manages `.claude-mpm/memories/PM_memories.md` and `{agent_name}_memories.md` files.

The two systems are **complementary**, not redundant. Static files load every session and survive MCP outages; trusty-memory enables semantic retrieval across agents and sessions. See the [Dual-System Routing](#dual-system-routing) table below for which facts belong where.

## Memory Update Triggers

**Trigger words**: "remember", "don't forget", "keep in mind", "note that", "make sure to", "always", "never", "going forward", "from now on", project standards or requirements.

**On trigger**:
1. Identify which agent should store the knowledge (or PM itself)
2. Read `.claude-mpm/memories/{agent_name}_memories.md`
3. **Identify the correct section** for the new fact (see [Static File Format](#static-file-format) below) — do not just append to end of file
4. Consolidate new info with existing content in that section (single-line facts, remove outdated entries)
5. Append the new entry to the bottom of the chosen section
6. If the fact also belongs in trusty-memory (see routing table), call `memory_remember` with the appropriate domain tag
7. Write updated file; confirm "Updated {agent} memory with: [brief summary]"

## Static File Format

Static `.claude-mpm/memories/PM_memories.md` and `{agent}_memories.md` files use a **typed, sectioned format**. Each entry is a single line prefixed with an ISO date.

```markdown
## CRITICAL — Never trim
<!-- Foundational facts that must survive any size-based trimming. Max 20 entries. -->
- [YYYY-MM-DD] <single-line fact>

## Environment — Machine/account/tooling facts
<!-- Stable machine-specific facts. Trim oldest when section exceeds 15 entries. -->
- [YYYY-MM-DD] <single-line fact>

## Decisions — Architecture choices and their rationale
<!-- Why we did X. Trim oldest when section exceeds 20 entries. -->
- [YYYY-MM-DD] <single-line fact>

## Patterns — Recurring implementation patterns
<!-- How we do X. Trim oldest when section exceeds 20 entries. -->
- [YYYY-MM-DD] <single-line fact>

## Gotchas — Things that broke or surprised us before
<!-- Anti-patterns and traps. Trim oldest when section exceeds 15 entries. -->
- [YYYY-MM-DD] <single-line fact>
```

### Backward Compatibility — Legacy Flat Files

If an existing memory file has no section headers (i.e., all entries are bare `- [YYYY-MM-DD] ...` lines with no `## Section` headings), treat all entries as belonging to `## Patterns` and create the full section scaffold on the next write. The scaffold prepends the five typed section headers above; existing lines are moved into the `## Patterns` block. This ensures old flat files are migrated transparently without data loss.

### Section Selection Guide

- **CRITICAL** — Facts that, if forgotten, cause data loss, broken releases, or wrong-account operations. Promotion requires explicit user signal ("never", "always", "critical").
- **Environment** — Paths, installed binaries, tool versions, account identifiers, OS-specific quirks.
- **Decisions** — Architecture choices with rationale ("we chose X over Y because..."). Captures the *why*.
- **Patterns** — Recurring "how we do X" — naming conventions, idioms, project-local code styles.
- **Gotchas** — Concrete failures observed in this project. Past-tense, lesson-bearing.

## Trim Rules

Replaces the prior vague 80 KB note with explicit, deterministic rules:

- **CRITICAL section**: never trimmed by size. Capped at 20 entries; oldest evicted **only** when count exceeds 20.
- **All other sections**: trimmed LIFO **within section** (oldest entries go first), not across the file as a whole. Per-section caps:
  - Environment: 15 entries
  - Decisions: 20 entries
  - Patterns: 20 entries
  - Gotchas: 15 entries
- **Overall file**:
  - **>4 KB** — emit a warning during load but do **not** truncate
  - **80 KB** — hard stop; refuse further appends until trimmed
- **Appends**: always append to the bottom of the chosen section, never to the end of the file
- **Promotion to CRITICAL**: when a fact graduates from another section to CRITICAL, **move** the line, do not duplicate it

## trusty-memory Tagging

When calling `mcp__trusty-memory__memory_remember`, tag each memory with one of the domain tags below so contextual retrieval works across agents. Use exactly one primary tag; secondary tags are optional.

| Tag | Use For |
|-----|---------|
| `auth` | Credentials, account switching rules, token scopes, gh/PyPI/npm identity |
| `git` | Branch rules, commit conventions, repo access, one-file-per-commit policy |
| `env` | Machine paths, installed tools, versions, OS-specific behavior |
| `architecture` | System design decisions, module boundaries, dependency choices |
| `pattern` | Recurring implementation approaches, idioms, project-local conventions |
| `gotcha` | Things that failed or surprised us — past failures with lessons |
| `project` | Project-specific rules, standards, naming conventions |

Choosing a tag is mandatory — untagged memories degrade recall quality.

## Dual-System Routing

Some facts belong in **both** the static file (for guaranteed session load) **and** trusty-memory (for semantic retrieval by other agents). Use this table to decide:

| Fact Type | Static File Section | trusty-memory Tag | Reason |
|-----------|--------------------|--------------------|--------|
| gh account switching rule | CRITICAL | `auth` | Must load every session AND be findable by agents |
| Release/publish workflow constraints | CRITICAL | `git` | Prevents broken releases; agents querying release flow find it |
| Machine-specific paths | Environment | `env` | Low-volatility, agent-accessible across delegations |
| Tool versions and locations | Environment | `env` | Needed by engineer/ops agents during setup tasks |
| Architecture decisions | Decisions | `architecture` | Historical context + semantic search |
| Recurring code patterns | Patterns | `pattern` | Engineer agents discover via semantic search |
| One-time gotcha | Gotchas | `gotcha` | Prevents repeat mistakes across agents |
| Ephemeral session note | (none) | (none) | Don't persist transient context |

**Rule of thumb**: if a fact is referenced by more than one agent type, it belongs in both systems. If only PM needs it, the static file alone is enough.

## Memory Routing

Each agent's memory categories are defined in `src/claude_mpm/agents/templates/{agent_name}_agent.json` under `memory_routing_rules`. Examples:
- **engineer**: implementation patterns, architecture decisions, perf optimizations
- **research**: analysis findings, domain knowledge, codebase patterns
- **qa**: testing strategies, quality standards, bug patterns
