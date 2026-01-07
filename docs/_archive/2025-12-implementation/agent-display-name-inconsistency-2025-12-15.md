# Agent Display Name Inconsistency Research

**Date**: 2025-12-15
**Researcher**: Claude Code Research Agent
**Status**: Root cause identified
**Classification**: Informational (data quality issue in agent metadata)

## Summary

The agent selection view in `claude-mpm config` displays inconsistent naming conventions:
- **Title Case**: "API QA", "Code Analysis", "Agentic Coder Optimizer"
- **snake_case**: "documentation_agent", "product_owner"

This inconsistency originates from the agent markdown frontmatter `name:` field, not from the display code.

## Investigation Results

### 1. Display Name Rendering Location

**File**: `src/claude_mpm/cli/commands/configure_agent_display.py`

```python
# Line 121: Table display uses agent.name directly
table.add_row(str(idx), agent.name, status, desc_display, tools_display)
```

**Verdict**: Display code is correct - it passes through the `agent.name` field as-is.

---

### 2. Source of Display Names

**File**: `src/claude_mpm/cli/commands/agent_state_manager.py`

#### Local Template Agents (lines 128-209)

```python
# Line 155: Gets display name from template metadata
display_name = metadata.get("name", agent_id)

# Line 188: Stores display_name on agent config
agent_config.display_name = display_name
```

**Issue**: For local JSON templates, the code extracts `metadata.name` from JSON files, which should be properly formatted.

#### Remote Agents (lines 211-264)

```python
# Line 228: Gets name from markdown frontmatter metadata
name = metadata.get("name", agent_id)

# Line 239: Uses agent_id as the name field for uniqueness
agent_config = AgentConfig(
    name=agent_id,  # ← This becomes the displayed name
    ...
)

# Line 251: Stores display_name separately
agent_config.display_name = name
```

**Root Cause Identified**: The code creates `AgentConfig` with `name=agent_id` (line 239), but the table display shows `agent.name` (line 121 of `configure_agent_display.py`), NOT `agent.display_name`.

This means remote agents display their `agent_id` instead of their formatted `display_name`.

---

### 3. Agent Metadata Analysis

Examined agent markdown files in `~/.claude-mpm/cache/remote-agents/`:

| Agent File | `name:` Field | `agent_id:` Field | What's Displayed |
|------------|--------------|-------------------|------------------|
| `qa/api-qa.md` | `"API QA"` | `"api-qa-agent"` | **Should show**: "API QA" |
| `universal/code-analyzer.md` | `"Code Analysis"` | `"code-analyzer"` | **Should show**: "Code Analysis" |
| `documentation/documentation.md` | `"documentation_agent"` | `"documentation-agent"` | **Currently shows**: "documentation_agent" |
| `universal/product-owner.md` | `"product_owner"` | `"product_owner"` | **Currently shows**: "product_owner" |

**Findings**:
1. **Title Case agents** have properly formatted `name:` fields ("API QA", "Code Analysis")
2. **snake_case agents** have literal snake_case in their `name:` fields ("documentation_agent", "product_owner")
3. **Display bug**: Remote agents show `agent_id` instead of `display_name`

---

### 4. Root Cause Summary

**Two Issues Identified**:

#### Issue 1: Display Code Uses Wrong Field (CODE BUG)

**Location**: `src/claude_mpm/cli/commands/agent_state_manager.py:239`

```python
# Current (incorrect):
agent_config = AgentConfig(
    name=agent_id,  # ← Shows "documentation-agent" instead of "Documentation Agent"
    ...
)
agent_config.display_name = name  # ← Stored but not used for display

# Should be:
agent_config = AgentConfig(
    name=name,  # ← Use display_name from frontmatter
    ...
)
agent_config.agent_id = agent_id  # ← Store agent_id separately for deployment
```

**Impact**: All remote agents display their `agent_id` (like "documentation-agent") instead of their formatted name (like "Documentation Agent").

#### Issue 2: Agent Metadata Quality (DATA ISSUE)

**Location**: Agent markdown frontmatter in `~/.claude-mpm/cache/remote-agents/`

Agents with incorrect `name:` field formatting:
- `documentation/documentation.md`: `name: documentation_agent` → Should be `name: Documentation Agent`
- `universal/product-owner.md`: `name: product_owner` → Should be `name: Product Owner`

**Impact**: Even after fixing Issue 1, these agents will still show snake_case names until their markdown frontmatter is updated.

---

## Agents Requiring Metadata Fixes

After fixing the display code bug (Issue 1), the following agents need their markdown frontmatter updated:

### Confirmed Snake_Case Names

```bash
# Search for snake_case names in agent frontmatter
grep -r "^name: [a-z_]*$" ~/.claude-mpm/cache/remote-agents/ | grep -v "agent_id"
```

**Expected Results**:
- `documentation/documentation.md`: `name: documentation_agent`
- `universal/product-owner.md`: `name: product_owner`
- *(Run command above to find complete list)*

### Recommended Fix Format

```yaml
# Before (incorrect):
name: documentation_agent

# After (correct):
name: Documentation Agent
```

---

## Fix Implementation Plan

### Step 1: Fix Display Code (High Priority)

**File**: `src/claude_mpm/cli/commands/agent_state_manager.py`

**Change**:
```python
# Line 239: Use display_name for the name field
agent_config = AgentConfig(
    name=name,  # ← Change from agent_id to name (display_name)
    description=(
        f"[{category}] {description[:60]}..."
        if len(description) > 60
        else f"[{category}] {description}"
    ),
    dependencies=[f"Source: {source}"],
)

# Store agent_id separately for deployment operations
agent_config.agent_id = agent_id  # ← Add this line
agent_config.source_type = "remote"
agent_config.is_deployed = is_deployed
agent_config.display_name = name  # ← Keep for backward compatibility
```

**Testing**:
```bash
# Verify agents display with Title Case names
claude-mpm config

# Expected output:
# - "Documentation Agent" (not "documentation-agent")
# - "Product Owner" (not "product_owner")
# - "API QA" (unchanged)
# - "Code Analysis" (unchanged)
```

### Step 2: Update Agent Metadata (Medium Priority)

**Location**: Agent repository (`~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/`)

**Process**:
1. Find all agents with snake_case names:
   ```bash
   cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/
   grep -r "^name: [a-z_]*$" agents/ | grep -v "agent_id"
   ```

2. Update each agent's frontmatter:
   ```yaml
   # Example: agents/documentation/documentation.md
   name: Documentation Agent  # ← Change from documentation_agent
   ```

3. Commit and push to agent repository:
   ```bash
   git add agents/
   git commit -m "fix: normalize agent display names to Title Case"
   git push
   ```

4. Sync to local cache:
   ```bash
   claude-mpm agents sync
   ```

### Step 3: Add Validation (Low Priority)

**File**: `src/claude_mpm/services/agents/git_source_manager.py` (or similar)

**Add validation** during agent parsing:
```python
def _validate_agent_metadata(metadata: dict) -> list[str]:
    """Validate agent metadata for common issues."""
    warnings = []

    name = metadata.get("name", "")
    # Warn if name contains underscores (likely snake_case)
    if "_" in name:
        warnings.append(
            f"Agent name '{name}' contains underscores. "
            f"Consider using Title Case: '{name.replace('_', ' ').title()}'"
        )

    # Warn if name is all lowercase
    if name.islower():
        warnings.append(
            f"Agent name '{name}' is all lowercase. "
            f"Consider using Title Case: '{name.title()}'"
        )

    return warnings
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/cli/commands/test_agent_state_manager.py`

```python
def test_remote_agent_uses_display_name():
    """Verify remote agents use display_name for UI, not agent_id."""
    manager = SimpleAgentManager(config_dir=Path("/tmp/.claude-mpm"))

    # Mock remote agent with Title Case display name
    with patch('claude_mpm.services.agents.git_source_manager.GitSourceManager') as mock:
        mock.return_value.list_cached_agents.return_value = [{
            "agent_id": "documentation-agent",
            "metadata": {
                "name": "Documentation Agent",  # ← Title Case
                "description": "Test description"
            },
            "category": "documentation",
            "source": "remote"
        }]

        agents = manager.discover_agents(include_remote=True)

        # Should use display_name, not agent_id
        assert agents[0].name == "Documentation Agent"
        assert agents[0].agent_id == "documentation-agent"
```

### Integration Tests

```bash
# Test display in configure view
claude-mpm config

# Expected:
# All agents show Title Case names
# No snake_case names visible in Name column
```

---

## Related Files

### Source Code
- `src/claude_mpm/cli/commands/agent_state_manager.py` - Agent discovery logic (NEEDS FIX)
- `src/claude_mpm/cli/commands/configure_agent_display.py` - Display rendering (CORRECT)
- `src/claude_mpm/cli/commands/configure_models.py` - AgentConfig model (OK)

### Agent Metadata
- `~/.claude-mpm/cache/remote-agents/documentation/documentation.md` - NEEDS UPDATE
- `~/.claude-mpm/cache/remote-agents/universal/product-owner.md` - NEEDS UPDATE
- `~/.claude-mpm/cache/remote-agents/qa/api-qa.md` - CORRECT (reference)
- `~/.claude-mpm/cache/remote-agents/universal/code-analyzer.md` - CORRECT (reference)

### Tests
- `tests/cli/commands/test_agent_state_manager.py` - Unit tests for agent discovery
- `tests/integration/test_configure_display.py` - Integration tests for UI display

---

## Recommendations

### Immediate Action (High Priority)
1. **Fix display code** in `agent_state_manager.py:239` to use `name` instead of `agent_id`
2. **Add `agent_id` field** to `AgentConfig` to preserve agent ID for deployment operations
3. **Test** with `claude-mpm config` to verify Title Case display

### Short-term Action (Medium Priority)
4. **Update agent metadata** in markdown frontmatter files:
   - `documentation_agent` → `Documentation Agent`
   - `product_owner` → `Product Owner`
   - *(Find complete list with grep command)*
5. **Commit to agent repository** and sync to local cache

### Long-term Action (Low Priority)
6. **Add metadata validation** to warn about snake_case names during agent parsing
7. **Document naming standards** in agent contribution guide
8. **Add CI checks** to enforce Title Case naming in agent frontmatter

---

## Architecture Notes

**Agent Config Flow**:
```
Agent Markdown File (frontmatter)
  ↓
GitSourceManager.list_cached_agents()
  ↓ (parses metadata.name)
SimpleAgentManager._discover_remote_agents()
  ↓ (creates AgentConfig with agent_id as name) ← BUG HERE
AgentConfig(name=agent_id, display_name=name)
  ↓
configure_agent_display.py (uses agent.name) ← CORRECT
Table Display (shows agent_id instead of display_name)
```

**After Fix**:
```
Agent Markdown File (frontmatter)
  ↓
GitSourceManager.list_cached_agents()
  ↓ (parses metadata.name)
SimpleAgentManager._discover_remote_agents()
  ↓ (creates AgentConfig with display name) ← FIXED
AgentConfig(name=display_name, agent_id=agent_id)
  ↓
configure_agent_display.py (uses agent.name) ← CORRECT
Table Display (shows display_name correctly)
```

---

## Conclusion

**Root Cause**: Display code uses `agent_id` instead of `display_name` for remote agents.

**Impact**: All remote agents show technical IDs (like "documentation-agent") instead of user-friendly names (like "Documentation Agent").

**Solution**:
1. Change `agent_state_manager.py:239` to use `name` field for display
2. Update agent markdown frontmatter to use Title Case naming conventions
3. Add validation to prevent future snake_case names

**Classification**: Code bug + data quality issue (both need fixing)

---

## Appendix: Quick Reference

### Display Name Sources

| Agent Type | Source File | Name Field Source | Current Display |
|-----------|-------------|-------------------|-----------------|
| Local Template | `*.json` | `metadata.name` | Correct (uses display_name) |
| Remote Agent | `*.md` frontmatter | `name:` field | **BUG** (uses agent_id) |

### Code Change Summary

**File**: `src/claude_mpm/cli/commands/agent_state_manager.py`

**Line 239**: Change from:
```python
agent_config = AgentConfig(name=agent_id, ...)
```

To:
```python
agent_config = AgentConfig(name=name, ...)
agent_config.agent_id = agent_id  # Store for deployment
```

**Impact**: Fixes display for all remote agents immediately.

---

**Research Complete**
