# PM Context Optimization

## Overview

The PM system prompt has been optimized to reduce token consumption from ~18,500 tokens (~25% of context at session start) down to ~11,560 tokens (~15% of context). This optimization provides more working room for actual user prompts and agent responses without sacrificing PM functionality.

## Problem Statement

The system prompt token overhead was consuming too much of the available context window at session start:

- **Before**: ~18,500 tokens (~25% of typical 128K context window)
- **After**: ~11,560 tokens (~15% of typical 128K context window)
- **Savings**: ~6,940 tokens reclaimed for user prompts and agent work

This was a critical bottleneck for long sessions with many agents and complex delegations.

## Five Optimizations

### 1. Strip `<example>` Blocks from Capability Descriptions

**File**: `src/claude_mpm/core/framework/formatters/capability_generator.py`  
**Tokens Saved**: ~3,681

Agent frontmatter YAML can include `<example>` blocks in capability descriptions. These blocks were being serialized into the assembled system prompt, adding unnecessary detail.

The `CapabilityGenerator` now strips these blocks at assembly time:

- Example blocks remain in source files (`agents/*.md`) for developer reference
- Rendered capabilities exclude the examples
- Assembled system prompt is significantly smaller

### 2. Lazy-Load WORKFLOW.md

**File**: `src/claude_mpm/core/framework/loaders/instruction_loader.py`  
**Tokens Saved**: ~1,150

The system-level WORKFLOW.md (complete workflow procedures) was being embedded verbatim in every system prompt. However, most projects override WORKFLOW.md anyway.

New behavior:

- Base system prompt includes only a one-line reference to `docs/workflow/PM_WORKFLOW.md` (external)
- **Full** WORKFLOW.md is still available at `docs/workflow/PM_WORKFLOW.md` for offline reference
- **Project-level** WORKFLOW.md overrides (`project_dir/WORKFLOW.md`) are still embedded **verbatim** in the system prompt
- **User-level** WORKFLOW.md (`~/.claude-mpm/WORKFLOW.md`) are still embedded **verbatim** in the system prompt

This way, the prompt is lean by default, but projects with custom workflows still get their full procedures embedded.

### 3. Conditional PM_memories.md Injection (MCP Backend Detection)

**File**: `src/claude_mpm/services/core/memory_manager.py`  
**Tokens Saved**: ~1,540

When an MCP memory backend (trusty-memory, kuzu-memory, etc.) is detected, the memory manager now skips embedding PM_memories.md into the system prompt. Instead, memories are injected dynamically via the UserPromptSubmit hook.

Configuration:

```yaml
# ~/.claude-mpm/config/configuration.yaml
memory:
  use_mcp_backend: true   # Skip PM_memories.md injection (use MCP hook)
  # use_mcp_backend: false  # Force PM_memories.md injection even with MCP available (fallback behavior)
```

Behavior:

- **With MCP backend + `use_mcp_backend: true`**: PM_memories.md excluded from system prompt; memories injected per-query via hook
- **Without MCP backend**: PM_memories.md embedded in system prompt (fallback)
- **Explicitly disabled**: PM_memories.md embedded even if MCP is available (testing/debugging)

### 4. Compressed MEMORY.md

**File**: `src/claude_mpm/agents/MEMORY.md`  
**Tokens Saved**: ~568

Removed verbose administrative procedures from MEMORY.md, focusing on behavioral rules only. The file is now ~60% smaller while preserving all essential memory directives.

Changes:

- Removed step-by-step memory management walkthroughs
- Kept all behavioral rules and memory categories
- Simplified formatting for faster parsing

### 5. PM_memories.md 4KB Cap

**File**: `src/claude_mpm/services/core/memory_manager.py`  
**Tokens Saved**: Varies (unbounded growth prevented)

To prevent unbounded growth in fallback installations without MCP memory, PM_memories.md is capped at 4KB. When the cap is approached, oldest entries are pruned.

This is a safety measure for long-running sessions without external memory backends.

## Results

| Optimization | Tokens Saved | Percent |
|---|---|---|
| Strip `<example>` blocks | ~3,681 | 53% |
| Lazy-load WORKFLOW.md | ~1,150 | 17% |
| Skip PM_memories.md (MCP backend) | ~1,540 | 22% |
| Compress MEMORY.md | ~568 | 8% |
| **Total Saved** | **~6,939** | **100%** |
| **System prompt before** | ~18,500 tokens | — |
| **System prompt after** | ~11,560 tokens | — |
| **Reduction** | ~37.5% | — |
| **Session start context usage** | 25% → ~15% | — |

## Regression Guards

The following tests ensure optimizations work correctly and don't regress:

### Structural Invariants
**File**: `tests/test_assembled_prompt_snapshot.py`

Validates:
- `<example>` blocks are stripped from assembled prompt
- PM_memories.md injection is conditional on MCP backend detection
- WORKFLOW.md lazy-loading works correctly
- Required sections are present (AGENTS, PM_WORKFLOW_REFERENCE, etc.)
- System prompt size stays below ceiling (~12,000 tokens)

### Lazy-Load Effectiveness
**File**: `tests/test_lazy_load_workflow.py`

Validates:
- WORKFLOW.md is not embedded in base system prompt
- Project-level WORKFLOW.md overrides are still embedded verbatim
- User-level WORKFLOW.md overrides are still embedded verbatim
- External reference to `docs/workflow/PM_WORKFLOW.md` is present

### Golden Snapshot
**File**: `tests/fixtures/assembled_prompt_golden.txt`

A frozen example of the assembled system prompt (with all optimizations applied). This allows spotting unexpected changes during development:

```bash
# Update golden snapshot after intentional changes
PM_UPDATE_GOLDEN=1 uv run pytest tests/test_assembled_prompt_snapshot.py
```

## Configuration

### Via Environment

```bash
# Enable MCP backend memory (skip PM_memories.md injection)
export MPM_USE_MCP_BACKEND=true

# Disable MCP backend memory (force PM_memories.md injection)
export MPM_USE_MCP_BACKEND=false
```

### Via Config File

```yaml
# ~/.claude-mpm/config/configuration.yaml
memory:
  use_mcp_backend: true
```

## Testing

```bash
# Run structural invariant tests (fast, no API calls)
uv run pytest tests/test_assembled_prompt_snapshot.py -v

# Run lazy-load effectiveness tests
uv run pytest tests/test_lazy_load_workflow.py -v

# Run all context optimization tests
uv run pytest tests/test_assembled_prompt_snapshot.py tests/test_lazy_load_workflow.py -v

# Update golden snapshot after intentional changes
PM_UPDATE_GOLDEN=1 uv run pytest tests/test_assembled_prompt_snapshot.py
```

## Verifying in Practice

To see the effect in a real session:

```bash
# Start a PM session
claude --agent pm

# In the session, use the memory command to view memory status
@memory status

# Check prompt tokens in logs (if verbose logging enabled)
# The system prompt should be significantly smaller than before
```

## Implementation Details

### CapabilityGenerator (`src/claude_mpm/core/framework/formatters/capability_generator.py`)

The `CapabilityGenerator` class now includes an `_strip_examples()` method that:
- Parses agent descriptions for XML-like `<example>` tags
- Removes the entire tag block and its contents
- Leaves all other content intact

### InstructionLoader (`src/claude_mpm/core/framework/loaders/instruction_loader.py`)

The `InstructionLoader` now:
- Checks for base WORKFLOW.md at the system level
- Replaces it with a one-line reference
- Still embeds project and user-level overrides in full

### MemoryManager (`src/claude_mpm/services/core/memory_manager.py`)

The `MemoryManager` now:
- Detects MCP memory backends via the hook system
- Conditionally includes or excludes PM_memories.md based on `use_mcp_backend` config
- Enforces 4KB cap on PM_memories.md growth

## Related Documentation

- [Memory Management](../features/memory.md) — for memory system overview
- [WORKFLOW.md Reference](../workflow/PM_WORKFLOW.md) — full workflow procedures
- [Configuration Guide](../guides/configuration.md) — for `memory.use_mcp_backend` and other settings
