# Memory Flow Architecture (v5.4.13)

**Last Updated:** 2025-12-20
**Version:** v5.4.13
**Status:** Active

## Overview

Claude MPM's memory system underwent a significant architectural transformation in v5.4.13, transitioning from **deployment-time memory injection** to **runtime memory loading**. This document describes the new architecture and its benefits.

## Executive Summary

### Key Changes in v5.4.13

1. **Runtime Memory Loading**: Agent memories now loaded dynamically via `MemoryPreDelegationHook` during task delegation
2. **No Restart Required**: Memory changes take effect immediately without restarting Claude Code
3. **PM Memory Only**: PM instructions (`PM_INSTRUCTIONS.md`) now only contain PM-specific memory, not all agent memories
4. **Per-Agent Memory**: Each agent receives only its own memory when delegated to via Task tool
5. **Event Observability**: Memory loading now emits `agent.memory.loaded` events to EventBus
6. **Removed Components**: Obsolete BASE_*.md static templates and unused base_agent_loader infrastructure

### Benefits

✅ **Instant Updates**: Memory changes apply immediately (no restart)
✅ **Cleaner Separation**: PM doesn't carry all agent memories
✅ **Observable**: EventBus integration enables monitoring
✅ **Token Efficient**: Agents only receive relevant memory
✅ **Maintainable**: Simpler architecture with fewer moving parts

---

## Architecture Diagrams

### Old Architecture (Pre-v5.4.13)

```
┌─────────────────────────────────────────────────────────┐
│                 Framework Deployment                     │
│                                                          │
│  MemoryProcessor.load_agent_memories()                  │
│  ├── Load ALL agent memory files                        │
│  │   ├── engineer.md                                    │
│  │   ├── qa.md                                          │
│  │   ├── research.md                                    │
│  │   └── ... (all agents)                               │
│  │                                                       │
│  └── Inject ALL into PM_INSTRUCTIONS.md                 │
│      └── Problem: PM carries 100KB+ of agent memories   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Deployment (Missing)                  │
│                                                          │
│  Agent markdown files deployed WITHOUT memories          │
│  └── Problem: Agents don't have their own memory!       │
└─────────────────────────────────────────────────────────┘
```

**Problems:**
- PM instructions bloated with ALL agent memories
- Agent markdown files missing their own memories
- Memory changes required full restart
- No observability into memory loading

---

### New Architecture (v5.4.13+)

```
┌─────────────────────────────────────────────────────────┐
│                 PM Initialization                        │
│                                                          │
│  FrameworkLoader.load()                                 │
│  ├── Load PM.md memory only                             │
│  └── Generate PM_INSTRUCTIONS.md                        │
│      └── Contains ONLY PM-specific memory               │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Task Delegation                       │
│                                                          │
│  Task tool spawns agent → MemoryPreDelegationHook       │
│  ├── Detect agent_id from delegation context            │
│  ├── Load agent-specific memory (e.g., engineer.md)     │
│  ├── Inject into delegation context dynamically         │
│  ├── Emit EventBus event: "agent.memory.loaded"         │
│  └── Emit SocketIO event: "memory_injected" (legacy)    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Execution                             │
│                                                          │
│  Agent receives:                                         │
│  ├── Agent definition (from .claude/agents/)            │
│  ├── Task context (from delegation)                     │
│  └── Agent memory (injected via hook)                   │
│      └── ONLY this agent's memory, not all agents       │
└─────────────────────────────────────────────────────────┘
```

**Benefits:**
- PM carries only PM memory (smaller context)
- Each agent gets its own memory at runtime
- Memory changes apply immediately
- Full observability via EventBus

---

## Component Details

### 1. MemoryPreDelegationHook

**File:** `src/claude_mpm/hooks/memory_integration_hook.py`

**Purpose:** Load and inject agent-specific memory before task delegation

**Execution Flow:**

```python
def execute(self, context: HookContext) -> HookResult:
    # 1. Extract agent ID from delegation context
    agent_name = context.data.get("agent", "")
    agent_id = normalize_agent_id(agent_name)  # "Engineer Agent" -> "engineer"

    # 2. Load agent memory from storage
    memory_content = self.memory_manager.load_agent_memory(agent_id)

    # 3. Inject into delegation context
    delegation_context["agent_memory"] = format_memory_section(memory_content)

    # 4. Emit observability events
    self.event_bus.publish("agent.memory.loaded", {
        "agent_id": agent_id,
        "memory_source": "runtime",
        "memory_size": len(memory_content),
        "timestamp": datetime.now().isoformat()
    })

    # 5. Return modified context
    return HookResult(success=True, data=updated_data, modified=True)
```

**Key Features:**
- Runs at priority 20 (before delegation)
- Normalizes agent IDs (`"Engineer Agent"` → `"engineer"`)
- Graceful degradation if memory manager unavailable
- Emits both EventBus and SocketIO events

### 2. AgentMemoryManager

**File:** `src/claude_mpm/services/agents/memory/agent_memory_manager.py`

**Purpose:** Manage agent memory storage and retrieval

**Memory File Locations:**

```python
# Priority order (highest to lowest):
memory_locations = [
    Path.cwd() / ".claude-mpm" / "memories",     # Project-specific
    Path.home() / ".claude-mpm" / "memories"      # User-global
]

# File naming patterns (both supported):
memory_filenames = [
    f"{agent_id}.md",               # New format (e.g., engineer.md)
    f"{agent_id}_memories.md"        # Legacy format (e.g., engineer_memories.md)
]
```

**Load Algorithm:**

```python
def load_agent_memory(self, agent_id: str) -> str:
    for memory_dir in memory_locations:
        for filename in memory_filenames:
            memory_file = memory_dir / filename
            if memory_file.exists():
                return memory_file.read_text()
    return ""  # No memory found (OK, not an error)
```

### 3. EventBus Integration

**Event Type:** `agent.memory.loaded`

**Event Data:**
```python
{
    "agent_id": str,          # Agent identifier (e.g., "engineer", "qa")
    "memory_source": str,     # Source: "runtime" (loaded at delegation)
    "memory_size": int,       # Size in bytes
    "timestamp": str          # ISO 8601 timestamp
}
```

**Usage Example:**

```python
from claude_mpm.services.event_bus.event_bus import EventBus

bus = EventBus.get_instance()

def log_memory_loads(data):
    print(f"Agent '{data['agent_id']}' loaded {data['memory_size']} bytes")

bus.on("agent.memory.loaded", log_memory_loads)
```

**See Also:** [docs/observability/agent-memory-events.md](../observability/agent-memory-events.md)

---

## Removed Components (v5.4.13)

### 1. BASE_*.md Template Files

**Status:** ✅ **REMOVED** (obsolete)

**Previously:** Static template files in `src/claude_mpm/agents/`
- `BASE_AGENT_TEMPLATE.md`
- `BASE_DOCUMENTATION.md`
- `BASE_ENGINEER.md`
- `BASE_OPS.md`
- `BASE_PM.md`
- `BASE_PROMPT_ENGINEER.md`
- `BASE_QA.md`
- `BASE_RESEARCH.md`

**Replacement:** Repository-based agent synchronization
- Agents synced from GitHub repositories
- Cached in `~/.claude-mpm/cache/remote-agents/`
- Hierarchical `BASE-AGENT.md` files for shared content

**Migration:** No action required (automatic fallback to remote agents)

### 2. Deployment-Time Memory Injection

**Status:** ✅ **REMOVED**

**Previously:** `ContentFormatter.format_full_framework()` (lines 103-115)
```python
# REMOVED CODE:
if framework_content.get("agent_memories"):
    agent_memories = framework_content["agent_memories"]
    for agent_name in sorted(agent_memories.keys()):
        instructions += f"### {agent_name} Agent Memory\n\n"
        instructions += agent_memories[agent_name]
```

**Problem:** All agent memories embedded in PM instructions

**Solution:** Runtime loading via `MemoryPreDelegationHook`

---

## Memory File Structure

### File Naming Convention

**Standard Format** (preferred):
```
.claude-mpm/memories/
├── PM.md                    # PM-specific memory
├── engineer.md              # Engineer agent memory
├── qa.md                    # QA agent memory
├── research.md              # Research agent memory
└── ...
```

**Legacy Format** (still supported):
```
.claude-mpm/memories/
├── engineer_memories.md
├── qa_memories.md
└── ...
```

**Note:** System tries new format first, falls back to legacy

### Memory File Format

Agent memory files use simple markdown with list-based structure:

```markdown
# Agent Memory: engineer

## Recent Learnings
- Use async/await for I/O operations in Python
- Prefer composition over inheritance for service architecture
- Always validate input parameters with Pydantic models

## Project-Specific Patterns
- Database models use SQLAlchemy 2.0 async syntax
- API routes follow REST conventions with versioning
- Error handling uses custom exception hierarchy

## Known Issues
- Avoid using `os.getcwd()` (use `Path.cwd()` instead)
- Database connections require explicit session cleanup
```

---

## Migration Guide

### From Pre-v5.4.13 to v5.4.13+

**What Changed:**
1. PM instructions no longer contain all agent memories
2. Agent memories loaded dynamically at delegation time
3. Memory changes apply immediately (no restart)

**What You Need to Do:**

✅ **Nothing** - Migration is automatic

**What to Expect:**
- PM startup faster (smaller PM_INSTRUCTIONS.md)
- Memory updates take effect immediately
- EventBus events for memory loading (if monitoring enabled)

**Verification:**

```bash
# Check PM instructions don't contain agent memories
grep "## Agent Memories" .claude-mpm/PM_INSTRUCTIONS.md
# Should return: (nothing)

# Check agent memory files exist
ls -la .claude-mpm/memories/
# Should show: engineer.md, qa.md, etc.

# Run agent and verify memory loaded
claude-mpm run
# Delegate to engineer → Should see memory injection in logs
```

---

## Performance Implications

### Startup Performance

**Before v5.4.13:**
- PM initialization: Load ALL agent memories (~100KB+)
- Generate PM_INSTRUCTIONS.md with all memories
- **Result:** Slower startup, larger PM context

**After v5.4.13:**
- PM initialization: Load ONLY PM.md memory (~5-10KB)
- Generate PM_INSTRUCTIONS.md with PM memory only
- **Result:** ✅ Faster startup, smaller PM context

### Runtime Performance

**Before v5.4.13:**
- Agent spawning: Read agent markdown from `.claude/agents/`
- No memory loaded (missing!)
- **Result:** Agents lacked project knowledge

**After v5.4.13:**
- Agent spawning: Read agent markdown
- MemoryPreDelegationHook: Load agent-specific memory (~5-10KB)
- Inject into delegation context
- **Result:** ✅ Minimal overhead (~10-20ms), agents have memory

### Memory Updates

**Before v5.4.13:**
- Update memory file
- **Restart Claude Code** to reload PM_INSTRUCTIONS.md
- **Result:** Slow iteration cycle

**After v5.4.13:**
- Update memory file
- Next agent delegation loads new memory automatically
- **Result:** ✅ Instant updates, no restart needed

---

## Testing

### Unit Tests

**Memory Hook Tests:**
```bash
pytest tests/hooks/test_memory_integration_hook.py -v
```

**Agent Memory Manager Tests:**
```bash
pytest tests/services/agents/memory/test_agent_memory_manager.py -v
```

### Integration Tests

**End-to-End Memory Flow:**
```bash
pytest tests/integration/test_memory_flow.py -v
```

**Verification:**
1. PM instructions contain ONLY PM memory
2. Agent delegation triggers memory loading
3. EventBus receives `agent.memory.loaded` events
4. Agent receives injected memory in context

### Manual Testing

**1. Update Agent Memory:**
```bash
echo "- New learning: Use pytest fixtures" >> .claude-mpm/memories/engineer.md
```

**2. Delegate to Agent:**
```bash
claude-mpm run
# In PM session: "Engineer agent, write a test for user service"
```

**3. Verify Memory Loaded:**
```bash
# Check logs for memory injection
grep "Injected memory for agent 'engineer'" logs/session.log

# Or use EventBus monitoring
claude-mpm monitor --events "agent.memory.loaded"
```

---

## Observability

### EventBus Monitoring

**Subscribe to Memory Events:**

```python
from claude_mpm.services.event_bus.event_bus import EventBus

bus = EventBus.get_instance()

def track_memory_usage(data):
    print(f"{data['timestamp']}: {data['agent_id']} loaded {data['memory_size']} bytes")

bus.on("agent.memory.loaded", track_memory_usage)
```

**Wildcard Subscription:**

```python
def log_all_agent_events(event_type, data):
    if event_type.startswith("agent."):
        print(f"{event_type}: {data}")

bus.on("agent.*", log_all_agent_events)
```

### Dashboard Integration

**Monitor Dashboard:**
```bash
claude-mpm run --monitor
```

**Navigate to:** `http://localhost:5000/dashboard`

**Memory Events Tab:**
- View real-time memory loading events
- Track memory sizes per agent
- Correlate with task delegation timeline

### SocketIO Events (Legacy)

**Event:** `memory_injected`

**Data:**
```python
{
    "agent_id": str,
    "size": int  # Injected content size in bytes
}
```

**Note:** Legacy compatibility - prefer EventBus for new integrations

---

## Troubleshooting

### Memory Not Loading

**Symptoms:**
- Agent doesn't reference project-specific patterns
- No "Injected memory" log messages

**Diagnosis:**

```bash
# Check memory file exists
ls -la .claude-mpm/memories/engineer.md

# Check file content
cat .claude-mpm/memories/engineer.md

# Verify agent ID normalization
# "Engineer Agent" should map to "engineer"
```

**Solutions:**
1. Ensure memory file exists in correct location
2. Verify file naming: `{agent_id}.md` (e.g., `engineer.md`)
3. Check file permissions (must be readable)
4. Review logs for memory manager errors

### PM Contains Agent Memories

**Symptoms:**
- PM_INSTRUCTIONS.md contains "## Agent Memories" section
- Large PM context size

**Diagnosis:**
```bash
grep "## Agent Memories" .claude-mpm/PM_INSTRUCTIONS.md
```

**Solutions:**
1. Verify running v5.4.13+ (`claude-mpm --version`)
2. Delete `.claude-mpm/PM_INSTRUCTIONS.md` and regenerate
3. Check for old deployment artifacts

### EventBus Events Not Firing

**Symptoms:**
- No `agent.memory.loaded` events observed
- Monitoring dashboard doesn't show memory events

**Diagnosis:**

```python
from claude_mpm.services.event_bus.event_bus import EventBus

bus = EventBus.get_instance()
stats = bus.get_stats()
print(f"Events published: {stats['events_published']}")
print(f"Handlers registered: {stats['handlers']}")
```

**Solutions:**
1. Verify EventBus available (check imports)
2. Ensure hook system initialized
3. Check event bus statistics for publish counts

---

## API Reference

### MemoryPreDelegationHook

**Class:** `claude_mpm.hooks.memory_integration_hook.MemoryPreDelegationHook`

**Methods:**

```python
def __init__(self, config: Config = None)
    """Initialize hook with optional config."""

def execute(self, context: HookContext) -> HookResult
    """
    Load and inject agent memory into delegation context.

    Args:
        context: Hook context containing agent_id and delegation data

    Returns:
        HookResult with modified context containing agent memory
    """
```

**Properties:**
- `name`: "memory_pre_delegation"
- `priority`: 20 (runs before delegation)

### AgentMemoryManager

**Class:** `claude_mpm.services.agents.memory.AgentMemoryManager`

**Methods:**

```python
def load_agent_memory(self, agent_id: str) -> str
    """
    Load memory for specific agent.

    Args:
        agent_id: Agent identifier (e.g., "engineer", "qa")

    Returns:
        Memory content as string, or empty string if not found
    """

def save_agent_memory(self, agent_id: str, content: str) -> bool
    """
    Save memory for specific agent.

    Args:
        agent_id: Agent identifier
        content: Memory content to save

    Returns:
        True if saved successfully
    """
```

### EventBus Events

**Event:** `agent.memory.loaded`

**Data Schema:**
```python
{
    "agent_id": str,        # Agent identifier
    "memory_source": str,   # "runtime"
    "memory_size": int,     # Bytes
    "timestamp": str        # ISO 8601
}
```

**Usage:**
```python
bus = EventBus.get_instance()
bus.on("agent.memory.loaded", handler_function)
```

---

## Related Documentation

- **[Agent Memory Events](../observability/agent-memory-events.md)** - EventBus integration details
- **[Agent System Overview](../agents/README.md)** - Agent architecture and capabilities
- **[Memory Manager Service](../../src/claude_mpm/services/agents/memory/)** - Implementation details
- **[Hook System](../../src/claude_mpm/hooks/)** - Hook architecture and lifecycle

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v5.4.13 | 2025-12-20 | Runtime memory loading architecture |
| Pre-v5.4.13 | - | Deployment-time memory injection (obsolete) |

---

## Future Enhancements

### Planned Features

1. **Memory Versioning**: Track memory changes over time
2. **Memory Compression**: Automatic summarization of old memories
3. **Memory Sharing**: Share memories across agent instances
4. **Memory Analytics**: Dashboard for memory usage patterns
5. **Memory Suggestions**: AI-powered memory recommendations

### Under Consideration

- Memory encryption for sensitive project data
- Memory sync across development environments
- Memory export/import for team collaboration
- Memory conflict resolution for multi-user projects

---

**Document Status:** ✅ Complete
**Last Review:** 2025-12-20
**Next Review:** 2026-01-20 (or at next major version)
