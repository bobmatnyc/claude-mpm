# Agent Removal Path Mismatch Research

**Date**: 2025-12-09
**Issue**: Agent removal fails due to path/filename mismatch
**Status**: Root cause identified, fix recommended

---

## Executive Summary

The agent removal system in Claude MPM fails because:

1. **Selection UI** stores full hierarchical paths (e.g., `engineer/mobile/tauri-engineer`)
2. **Deployment** flattens to leaf names (e.g., `tauri-engineer.md`)
3. **Removal logic** tries to delete using full path (e.g., `engineer/mobile/tauri-engineer.md`)
4. **Result**: File not found, removal fails

**Impact**: Users cannot remove agents through the interactive UI.

**Recommended Fix**: Extract leaf name during removal to match deployed filename.

---

## Data Flow Analysis

### 1. Agent Discovery and Selection

**File**: `src/claude_mpm/cli/commands/agent_state_manager.py`

#### Discovery (_discover_remote_agents, lines 210-263)

```python
agent_config = AgentConfig(
    name=agent_id,  # Full hierarchical path: "engineer/mobile/tauri-engineer"
    description=f"[{category}] {description[:60]}...",
    dependencies=[f"Source: {source}"],
)

# Metadata attached
agent_config.source_type = "remote"
agent_config.is_deployed = is_deployed
agent_config.display_name = name  # Human-readable name
agent_config.full_agent_id = agent_id  # Full hierarchical ID
agent_config.source_dict = agent_dict  # Full dictionary with source_file
```

**Key fields**:
- `agent_config.name` = `"engineer/mobile/tauri-engineer"` (hierarchical path)
- `agent_config.full_agent_id` = `"engineer/mobile/tauri-engineer"` (same)
- `agent_config.source_dict` = Contains `source_file` path to template

#### Selection UI (_deploy_agents_individual, lines 1147-1435)

**File**: `src/claude_mpm/cli/commands/configure.py`

```python
# Build checkbox choices (lines 1196-1219)
for agent in agents:
    # Create choice with full hierarchical path
    choice = questionary.Choice(
        title=f"{agent.name} - {display_name}",
        value=agent.name,  # ← STORES FULL PATH
        checked=is_selected
    )
    agent_choices.append(choice)
    agent_map[agent.name] = agent  # ← Maps full path to agent object

# User selection returns full paths (line 1243)
selected_agent_ids = questionary.checkbox(
    "Agents:", choices=agent_choices, style=self.QUESTIONARY_STYLE
).ask()
# selected_agent_ids = ["engineer/mobile/tauri-engineer", ...]
```

**Selection data**:
- User selects: `"engineer/mobile/tauri-engineer"`
- Stored in `current_selection` set (line 1291)
- Used for computing `to_remove` set (line 1298)

---

### 2. Agent Deployment (Filename Flattening)

**File**: `src/claude_mpm/cli/commands/configure.py`

#### Deployment (_deploy_single_agent, lines 1516-1575)

```python
def _deploy_single_agent(self, agent: AgentConfig, show_feedback: bool = True) -> bool:
    full_agent_id = getattr(agent, "full_agent_id", agent.name)
    # full_agent_id = "engineer/mobile/tauri-engineer"

    # Determine target file name (use leaf name from hierarchical ID)
    if "/" in full_agent_id:
        target_name = full_agent_id.split("/")[-1] + ".md"  # ← FLATTENING
    else:
        target_name = full_agent_id + ".md"
    # target_name = "tauri-engineer.md"

    # Deploy to user-level agents directory
    target_dir = Path.home() / ".claude" / "agents"
    target_file = target_dir / target_name
    # target_file = ~/.claude/agents/tauri-engineer.md

    shutil.copy2(source_file, target_file)
```

**Deployment behavior**:
- Input: `"engineer/mobile/tauri-engineer"`
- Output file: `~/.claude/agents/tauri-engineer.md` (flattened)
- **No directory hierarchy** created in deployment target

---

### 3. Agent Removal (Mismatch)

**File**: `src/claude_mpm/cli/commands/configure.py`

#### Removal Logic (_deploy_agents_individual, lines 1356-1412)

```python
# Remove agents
for agent_id in to_remove:
    # agent_id = "engineer/mobile/tauri-engineer" (full path from selection)

    # Remove from project, legacy, and user locations
    project_path = Path.cwd() / ".claude-mpm" / "agents" / f"{agent_id}.md"
    # project_path = .claude-mpm/agents/engineer/mobile/tauri-engineer.md ❌

    legacy_path = Path.cwd() / ".claude" / "agents" / f"{agent_id}.md"
    # legacy_path = .claude/agents/engineer/mobile/tauri-engineer.md ❌

    user_path = Path.home() / ".claude" / "agents" / f"{agent_id}.md"
    # user_path = ~/.claude/agents/engineer/mobile/tauri-engineer.md ❌

    removed = False
    for path in [project_path, legacy_path, user_path]:
        if path.exists():  # ← NEVER FINDS THE FILE
            path.unlink()
            removed = True
```

**Problem**:
- Looking for: `engineer/mobile/tauri-engineer.md` (with directory structure)
- Actual file: `tauri-engineer.md` (flattened leaf name)
- **Mismatch**: File never found, removal fails

---

## Root Cause

**The mismatch occurs at line 1364**:

```python
project_path = Path.cwd() / ".claude-mpm" / "agents" / f"{agent_id}.md"
```

**Why it fails**:
1. `agent_id` contains full hierarchical path (`engineer/mobile/tauri-engineer`)
2. Directly interpolating creates incorrect path with slashes
3. Deployed files use only leaf name (`tauri-engineer.md`)
4. `path.exists()` returns `False`, no file is deleted

---

## Why Deployment Works But Removal Doesn't

**Deployment has explicit flattening logic** (line 1537):
```python
if "/" in full_agent_id:
    target_name = full_agent_id.split("/")[-1] + ".md"  # Extract leaf name
```

**Removal lacks this logic** - it uses `agent_id` directly:
```python
f"{agent_id}.md"  # No leaf extraction
```

---

## Recommended Fix

### Option 1: Extract Leaf Name During Removal (RECOMMENDED)

Modify removal logic to match deployment's flattening behavior:

```python
# Remove agents (line 1356)
for agent_id in to_remove:
    # Extract leaf name to match deployed filename
    if "/" in agent_id:
        leaf_name = agent_id.split("/")[-1]
    else:
        leaf_name = agent_id

    # Remove from project, legacy, and user locations
    project_path = Path.cwd() / ".claude-mpm" / "agents" / f"{leaf_name}.md"
    legacy_path = Path.cwd() / ".claude" / "agents" / f"{leaf_name}.md"
    user_path = Path.home() / ".claude" / "agents" / f"{leaf_name}.md"

    removed = False
    for path in [project_path, legacy_path, user_path]:
        if path.exists():
            path.unlink()
            removed = True
```

**Pros**:
- Minimal change (3 lines modified)
- Matches deployment behavior exactly
- No data model changes needed
- Fixes all existing paths

**Cons**:
- Temporary fix, doesn't address root issue

---

### Option 2: Store Leaf Name in AgentConfig (COMPREHENSIVE)

Add `deployed_filename` field during discovery:

```python
# In _discover_remote_agents (line 237)
agent_config = AgentConfig(
    name=agent_id,  # Keep full path for display
    description=f"[{category}] {description[:60]}...",
    dependencies=[f"Source: {source}"],
)

# NEW: Store flattened filename for removal
agent_config.deployed_filename = agent_id.split("/")[-1] if "/" in agent_id else agent_id
agent_config.full_agent_id = agent_id
```

Update removal to use `deployed_filename`:

```python
# Remove agents (line 1356)
for agent_id in to_remove:
    agent = agent_map.get(agent_id)
    filename = getattr(agent, "deployed_filename", agent_id.split("/")[-1])

    project_path = Path.cwd() / ".claude-mpm" / "agents" / f"{filename}.md"
    # ... rest of removal logic
```

**Pros**:
- Explicit contract in data model
- Prevents future confusion
- Single source of truth for filename

**Cons**:
- Requires data model changes
- More invasive refactor
- Need to update all discovery paths

---

### Option 3: Use canonical_id Field (FUTURE)

The user mentioned a recent `canonical_id` field addition. If this field stores the flattened name:

```python
# Check if canonical_id exists and use it
for agent_id in to_remove:
    agent = agent_map.get(agent_id)
    filename = getattr(agent, "canonical_id", None)

    if not filename:
        # Fallback to leaf extraction
        filename = agent_id.split("/")[-1] if "/" in agent_id else agent_id

    project_path = Path.cwd() / ".claude-mpm" / "agents" / f"{filename}.md"
```

**Pros**:
- Uses intended field if available
- Graceful fallback
- Future-proof

**Cons**:
- Depends on `canonical_id` being properly populated
- Need to verify field behavior first

---

## collection_id Field Analysis

**File**: `src/claude_mpm/cli/commands/agent_state_manager.py`

The `collection_id` field is **not currently set** in discovery:

```python
# Line 252 - current code
agent_config.source_dict = agent_dict  # No collection_id extraction
```

**Potential use**: Could store repository identifier (`bobmatnyc/claude-mpm-agents`) for grouping, but:
- Not related to filename flattening issue
- Not populated during discovery
- Would need separate implementation

---

## Testing Verification

### Current Behavior (Broken)

1. User selects `engineer/mobile/tauri-engineer` via checkbox
2. System deploys to `~/.claude/agents/tauri-engineer.md` ✅
3. User unchecks `engineer/mobile/tauri-engineer` to remove
4. System looks for `~/.claude/agents/engineer/mobile/tauri-engineer.md` ❌
5. File not found, removal fails ❌

### Expected Behavior (After Fix)

1. User selects `engineer/mobile/tauri-engineer` via checkbox
2. System deploys to `~/.claude/agents/tauri-engineer.md` ✅
3. User unchecks `engineer/mobile/tauri-engineer` to remove
4. System extracts leaf name: `tauri-engineer`
5. System looks for `~/.claude/agents/tauri-engineer.md` ✅
6. File found and deleted ✅

---

## Implementation Priority

**Immediate (Option 1)**: Extract leaf name during removal
- **Effort**: 30 minutes
- **Risk**: Low
- **Impact**: Fixes user-blocking issue immediately

**Short-term (Option 2)**: Add `deployed_filename` field
- **Effort**: 2-3 hours
- **Risk**: Medium (data model change)
- **Impact**: Prevents future issues, cleaner architecture

**Future (Option 3)**: Migrate to `canonical_id` if intended for this purpose
- **Effort**: Depends on current `canonical_id` implementation
- **Risk**: Low if field already exists
- **Impact**: Uses intended architecture if available

---

## Related Code Locations

### Files Modified for Fix

1. **src/claude_mpm/cli/commands/configure.py**
   - Line 1364: `project_path` construction
   - Line 1366: `legacy_path` construction
   - Line 1367: `user_path` construction

### Files to Review (If Choosing Option 2)

1. **src/claude_mpm/cli/commands/agent_state_manager.py**
   - Line 237: Add `deployed_filename` to AgentConfig
   - Line 175: Add same field for local agents

2. **src/claude_mpm/cli/commands/configure_models.py**
   - Line 10: Add `deployed_filename` field to AgentConfig class

### Testing Targets

1. Agent with hierarchical path (`engineer/backend/python-engineer`)
2. Agent with single-level path (`documentation-agent`)
3. Multi-agent batch removal
4. Edge case: Agent name containing slashes but not hierarchical

---

## Conclusion

**Root Cause**: Removal logic uses full hierarchical path instead of leaf name to construct filenames.

**Immediate Fix**: Extract leaf name during removal (3-line change at line 1357).

**Long-term Solution**: Standardize on either:
- Option 2: Add explicit `deployed_filename` field
- Option 3: Use `canonical_id` if it serves this purpose

**Next Steps**:
1. Implement Option 1 immediately to unblock users
2. Verify `canonical_id` field purpose and population
3. Decide on long-term architecture (Option 2 or 3)
4. Add regression tests for removal with hierarchical paths
