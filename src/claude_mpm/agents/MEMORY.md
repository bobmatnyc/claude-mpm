<!-- PURPOSE: Memory system for retaining project knowledge -->

## Memory System

**MCP backends** (use whichever is active):
- **trusty-memory** (primary): `mcp__trusty-memory__memory_recall` / `mcp__trusty-memory__memory_remember`
- **kuzu-memory** (legacy fallback): `mcp__kuzu-memory__kuzu_recall` / `mcp__kuzu-memory__kuzu_remember`

**Static fallback** (when no MCP backend configured): PM directly manages `.claude-mpm/memories/PM_memories.md` and `{agent_name}_memories.md` files.

## Memory Update Triggers

**Trigger words**: "remember", "don't forget", "keep in mind", "note that", "make sure to", "always", "never", "going forward", "from now on", project standards or requirements.

**On trigger**:
1. Identify which agent should store the knowledge (or PM itself)
2. Read `.claude-mpm/memories/{agent_name}_memories.md`
3. Consolidate new info with existing content (single-line facts, remove outdated entries)
4. Write updated file; confirm "Updated {agent} memory with: [brief summary]"

**Size limit**: 80 KB (~20 k tokens) per file. See Change 5 cap: files >4 KB are trimmed to most-recent entries on load.

## Memory Routing

Each agent's memory categories are defined in `src/claude_mpm/agents/templates/{agent_name}_agent.json` under `memory_routing_rules`. Examples:
- **engineer**: implementation patterns, architecture decisions, perf optimizations
- **research**: analysis findings, domain knowledge, codebase patterns
- **qa**: testing strategies, quality standards, bug patterns
