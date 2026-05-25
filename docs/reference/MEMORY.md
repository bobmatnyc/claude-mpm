# Memory System Guide

Complete guide to Claude MPM's memory and context management systems.

## Quick Start

```bash
# Initialize agent memory
claude-mpm memory init

# Clean up old conversation history
claude-mpm cleanup-memory

# Keep only recent conversations
claude-mpm cleanup-memory --days 7
```

## Overview

Claude MPM provides two complementary memory systems:

1. **Agent Memory**: Persistent, project-specific learnings
2. **Resume Log System**: Proactive context management for session continuity

## Agent Memory System

### How It Works

Agents learn and retain project-specific patterns using a simple list format:

**Memory Storage:**
- Simple list of learnings
- Project-specific knowledge
- Cross-session persistence
- Agent-specific memory isolation

**Memory Updates:**
Agents update memories via JSON response fields:

```json
{
  "remember": ["Learning 1", "Learning 2"],     // Incremental updates
  "MEMORIES": ["Complete replacement list"]      // Full replacement
}
```

### Initialization

```bash
# Initialize memory for current project
claude-mpm memory init

# Verify memory system
claude-mpm doctor --checks memory
```

### Memory Guidelines

**Store:**
- Project decisions and conventions
- Technical specifications and API details
- User preferences and patterns
- Error solutions and workarounds
- Architectural patterns

**Don't Store:**
- Temporary state or session data
- Large code blocks or files
- Sensitive information (credentials, keys)
- Generic programming knowledge

### Memory Integration

**Automatic Context Enrichment:**
When using [trusty-memory](../integrations/trusty-memory.md) (recommended partner product):

- Persistent memory palace with hierarchical storage (palace/wing/room/closet/drawer)
- Intelligent prompt enrichment via `get_prompt_context()`
- Structured semantic recall of project knowledge
- Temporal knowledge graph for cross-session context
- Seamless zero-configuration integration

Install with:
```bash
uv tool install trusty-memory
claude-mpm setup trusty-memory
```

See [../developer/memory-integration.md](../developer/memory-integration.md) for technical details.

## Resume Log System

### Overview

The Resume Log System (v4.17.2+) provides proactive context management for seamless session continuity.

**Key Features:**
- 🎯 Graduated thresholds at 70%/85%/95% of context window
- 📋 Structured 10k-token logs for session resumption
- 🔄 Automatic context preservation
- ⚙️ Zero-configuration operation

### How It Works

1. **Monitor**: Tracks token usage throughout session
2. **Warn**: Displays proactive warnings at thresholds:
   - 70% (Caution): Plan transition (60k token buffer)
   - 85% (Warning): Wrap up work (30k token buffer)
   - 95% (Critical): Stop new work (10k token buffer)
3. **Generate**: Creates structured 10k-token resume log
4. **Resume**: Automatically loads context in new session

### Resume Log Structure

```markdown
# Session Resume Log: 20251101_115000

## Context Metrics (500 tokens)
- Token usage and percentage
- Session duration
- Key milestones

## Mission Summary (1,000 tokens)
- Overall goal and purpose
- High-level context

## Accomplishments (2,000 tokens)
- What was completed
- Deliverables and outputs

## Key Findings (2,500 tokens)
- Important discoveries
- Technical insights

## Decisions & Rationale (1,500 tokens)
- Why choices were made
- Trade-offs considered

## Next Steps (1,500 tokens)
- What to do next
- Pending tasks

## Critical Context (1,000 tokens)
- Essential state, IDs, paths
- Dependencies and blockers
```

### Configuration

Configure in `.claude-mpm/configuration.yaml`:

```yaml
context_management:
  enabled: true
  budget_total: 200000        # 200k token limit
  thresholds:
    caution: 0.70             # First warning (60k buffer)
    warning: 0.85             # Strong warning (30k buffer)
    critical: 0.95            # Urgent warning (10k buffer)
  resume_logs:
    enabled: true
    auto_generate: true
    max_tokens: 10000         # 10k token budget
    storage_dir: ".claude-mpm/resume-logs"
```

### Usage

**Automatic Operation:**
Resume logs work automatically with no manual intervention:

1. Work normally until threshold warning appears
2. System automatically generates resume log
3. Start new session - previous context loads automatically
4. Continue work seamlessly with full context

**Manual Review:**
```bash
# View resume logs
ls -la .claude-mpm/resume-logs/

# Read specific log
cat .claude-mpm/resume-logs/resume-20251101_115000.md
```

See [../user/resume-logs.md](../user/resume-logs.md) for complete guide.

## Conversation History Management

### Memory Cleanup

Large conversation histories can consume 2GB+ of memory. Clean up periodically:

```bash
# Clean up all old conversations
claude-mpm cleanup-memory

# Keep only last 7 days
claude-mpm cleanup-memory --days 7

# Keep only last 30 days
claude-mpm cleanup-memory --days 30
```

### Storage Locations

**Claude Code Conversations:**
```
~/.local/share/Claude/
  └── conversations/
      ├── conversation-id-1/
      ├── conversation-id-2/
      └── ...
```

**Claude MPM Sessions:**
```
~/.claude-mpm/
  └── sessions/
      ├── session-id-1.json
      ├── session-id-2.json
      └── ...

.claude-mpm/
  └── sessions/
      └── project-session.json
```

### Automatic Cleanup

Configure automatic cleanup:

```yaml
# In configuration.yaml
memory:
  auto_cleanup:
    enabled: true
    retention_days: 30
    schedule: daily  # daily, weekly, monthly
```

## Session Management

### Auto-Save

Sessions automatically save every 5 minutes (configurable):

```yaml
session:
  auto_save:
    enabled: true
    interval: 300  # seconds (60-1800)
```

### Manual Pause/Resume

```bash
# Pause current session
claude-mpm mpm-init pause

# Resume paused session
claude-mpm mpm-init resume
```

### Session State

Session state includes:
- Current agent
- Active tasks
- Context window usage
- File operations
- Configuration

## Context Window Management

### Token Tracking

Monitor token usage in real-time:

```bash
# Start with monitoring
claude-mpm run --monitor

# Dashboard shows token usage and percentage
```

### Threshold Warnings

Graduated warning system:

| Threshold | Usage | Buffer | Action |
|-----------|-------|--------|--------|
| Caution   | 70%   | 60k    | Plan transition |
| Warning   | 85%   | 30k    | Wrap up work |
| Critical  | 95%   | 10k    | Stop new work |

### Context Optimization

**Reduce Context Usage:**
- Use resume logs for long sessions
- Clear unnecessary context
- Focus on specific tasks
- Break work into smaller sessions

**Maximize Context:**
- Load only necessary files
- Use semantic search for discovery
- Leverage agent memory for patterns
- Use resume logs for continuity

## Memory Best Practices

### Agent Memory

**Do:**
- ✅ Store project-specific patterns
- ✅ Record architectural decisions
- ✅ Document error solutions
- ✅ Track user preferences

**Don't:**
- ❌ Store sensitive data
- ❌ Save temporary state
- ❌ Include large code blocks
- ❌ Duplicate documentation

### Resume Logs

**Do:**
- ✅ Let system generate automatically
- ✅ Review logs when resuming
- ✅ Plan work around thresholds
- ✅ Break long tasks into sessions

**Don't:**
- ❌ Ignore threshold warnings
- ❌ Try to fit everything in one session
- ❌ Manual log editing (use new session)
- ❌ Disable without good reason

### Conversation Cleanup

**Do:**
- ✅ Clean up regularly (weekly/monthly)
- ✅ Keep recent conversations (7-30 days)
- ✅ Archive important conversations
- ✅ Monitor disk usage

**Don't:**
- ❌ Delete all conversations (lose context)
- ❌ Keep years of history (memory bloat)
- ❌ Clean during active sessions
- ❌ Ignore memory warnings

## Integration with Partner Products

### trusty-memory (Recommended)

**Advanced memory management** with a hierarchical knowledge palace and temporal graph:

```bash
# Install
uv tool install trusty-memory

# Configure for current project
claude-mpm setup trusty-memory
```

**Benefits:**
- 🧠 Persistent memory palace (palace/wing/room/closet/drawer hierarchy)
- 🎯 Intelligent prompt enrichment via `get_prompt_context()`
- 📊 Progressive retrieval (L0–L3) for token-efficient recall
- 🕓 Temporal knowledge graph for cross-session context
- 🔄 Seamless integration via MCP stdio server

See [trusty-memory integration guide](../integrations/trusty-memory.md) for details.

### trusty-search (Recommended)

**Semantic code search** with hybrid retrieval (BM25 + vector + KG):

```bash
# Install
uv tool install trusty-search

# Configure for current project
claude-mpm setup trusty-search

# Use in Claude MPM
claude-mpm search "authentication logic"
```

**Benefits:**
- 🔍 Find code by intent, not keywords
- 🎯 Context-aware discovery with RRF fusion ranking
- ⚡ Fast indexing via persistent daemon
- 📊 Pattern recognition across the codebase

See [trusty-search integration guide](../integrations/trusty-search.md) for details.

---

## Legacy Backends (Deprecated)

The following backends are retained for backward compatibility with existing installations. New setups should use **trusty-memory** and **trusty-search** instead.

### kuzu-memory (deprecated — superseded by trusty-memory)

```bash
# Legacy installation — prefer trusty-memory for new setups
pipx install kuzu-memory
```

See [kuzu-memory integration guide](../integrations/kuzu-memory.md) for the legacy reference.

### mcp-vector-search (deprecated — superseded by trusty-search)

```bash
# Legacy installation — prefer trusty-search for new setups
pipx install mcp-vector-search
```

See [mcp-vector-search integration guide](../integrations/mcp-vector-search.md) for the legacy reference.

## Troubleshooting

### High Memory Usage

```bash
# Check memory usage
ps aux | grep claude-mpm

# Clean up conversations
claude-mpm cleanup-memory --days 7

# Clear caches
rm -rf ~/.claude-mpm/cache/
```

### Resume Logs Not Generated

```bash
# Check configuration
grep resume_logs ~/.claude-mpm/configuration.yaml

# Verify enabled
claude-mpm doctor --checks configuration

# Check logs directory
ls -la .claude-mpm/resume-logs/
```

### Memory Initialization Failed

```bash
# Verify project structure
ls -la .claude-mpm/

# Reinitialize
claude-mpm memory init

# Check permissions
chmod -R 755 .claude-mpm/
```

See [../user/troubleshooting.md](../user/troubleshooting.md) for more solutions.

## See Also

- **[Resume Logs Guide](../user/resume-logs.md)** - Complete resume log documentation
- **[Memory Integration](../developer/memory-integration.md)** - Technical implementation
- **[User Guide](../user/user-guide.md)** - End-user features
- **[Configuration](../configuration/reference.md)** - Configuration options
- **[Architecture](../developer/resume-log-architecture.md)** - Technical architecture

---

**For technical memory documentation**: See [../developer/memory-integration.md](../developer/memory-integration.md)
