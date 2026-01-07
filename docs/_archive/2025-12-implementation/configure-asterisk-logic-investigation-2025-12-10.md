# Investigation: Configure Agent List Asterisk Logic

**Date**: 2025-12-10
**Issue**: Asterisks (*) don't show correctly in `claude-mpm configure` agent list
**User Expectation**: Asterisks should mark agents that are DEPLOYED (exist in `.claude/agents/`)
**Current Behavior**: Asterisks only mark agents from `recommended_agent_ids` (from AgentRecommendationService)

---

## Executive Summary

The asterisk logic in `claude-mpm configure` is currently tied to **recommended agents** from the `AgentRecommendationService`, NOT to **deployed agents** in `.claude/agents/`. The user wants asterisks to indicate which agents are already deployed/installed.

**Key Finding**: The code already has:
1. ✅ Logic to detect deployed agents (`deployed_ids` from `get_deployed_agent_ids()`)
2. ✅ Checkbox state reflecting deployment status (`is_selected = agent.name in current_selection`)
3. ❌ Asterisk logic tied to WRONG variable (`recommended_agent_ids` instead of `deployed_ids`)

**Solution**: Change asterisk condition from `is_recommended` to `is_deployed`.

---

## Code Locations

### Primary File
**File**: `src/claude_mpm/cli/commands/configure.py`

### Key Lines for Asterisk Logic

**Line 1260-1268**: Where `deployed_ids` is fetched (CORRECT)
```python
# Get deployed agent IDs and recommended agents
deployed_ids = get_deployed_agent_ids()

try:
    recommended_agent_ids = self.recommendation_service.get_recommended_agents(
        str(self.project_dir)
    )
except Exception as e:
    self.logger.warning(f"Failed to get recommended agents: {e}")
    recommended_agent_ids = set()
```

**Line 1270-1275**: Where deployed agents are mapped to full paths (CORRECT)
```python
# Build mapping: leaf name -> full path for deployed agents
deployed_full_paths = set()
for agent in agents:
    agent_leaf_name = agent.name.split("/")[-1]
    if agent_leaf_name in deployed_ids:
        deployed_full_paths.add(agent.name)
```

**Line 1278**: Current selection starts with deployed agents (CORRECT)
```python
# Track current selection state (starts with deployed, updated in loop)
current_selection = deployed_full_paths.copy()
```

**Line 1412-1420**: **WHERE ASTERISK IS DETERMINED (INCORRECT)**
```python
# Check if recommended
is_recommended = any(
    agent.name == rec_id or agent_leaf_name == rec_id.split("/")[-1]
    for rec_id in recommended_agent_ids
)

# Format choice text with asterisk for recommended
choice_text = f"    {display_name}"
if is_recommended:
    choice_text += " *"
```

**Line 1435**: Help text claiming asterisk means "recommended" (INCORRECT for user's needs)
```python
self.console.print("[dim]* = Recommended for this project[/dim]")
```

---

## Current Logic (INCORRECT for User's Needs)

```python
# Lines 1412-1420
is_recommended = any(
    agent.name == rec_id or agent_leaf_name == rec_id.split("/")[-1]
    for rec_id in recommended_agent_ids  # ❌ WRONG: Using recommendation service
)

choice_text = f"    {display_name}"
if is_recommended:  # ❌ WRONG: Should check deployment status
    choice_text += " *"
```

**Problem**: Asterisk indicates "recommended" agents (from AgentRecommendationService), NOT deployed agents.

---

## Expected Logic (CORRECT for User's Needs)

```python
# Lines 1412-1420 (CORRECTED)
is_deployed = agent.name in deployed_full_paths  # ✅ CORRECT: Check deployment status

choice_text = f"    {display_name}"
if is_deployed:  # ✅ CORRECT: Asterisk for deployed agents
    choice_text += " *"
```

**Solution**: Change asterisk logic to check `deployed_full_paths` instead of `recommended_agent_ids`.

---

## Supporting Infrastructure (Already Correct)

### Deployment Detection Logic

**File**: `src/claude_mpm/utils/agent_filters.py`
**Function**: `get_deployed_agent_ids(project_dir=None)`
**Lines**: 87-177

**Detection Methods**:
1. **Virtual Deployment State** (primary): `.claude/agents/.mpm_deployment_state` JSON file
2. **Physical Files** (fallback): `.claude/agents/*.md` files

**Returns**: `Set[str]` of deployed agent IDs (leaf names like "python-engineer", "qa")

**Example**:
```python
# Checks:
# 1. .claude/agents/.mpm_deployment_state (virtual deployment)
# 2. .claude/agents/*.md (physical files)
deployed_ids = get_deployed_agent_ids()
# Returns: {"python-engineer", "qa", "PM", "ticketing"}
```

---

## Required Changes

### Change 1: Update Asterisk Logic

**File**: `src/claude_mpm/cli/commands/configure.py`
**Lines**: 1412-1420

**Current Code**:
```python
# Check if recommended
is_recommended = any(
    agent.name == rec_id or agent_leaf_name == rec_id.split("/")[-1]
    for rec_id in recommended_agent_ids
)

# Format choice text with asterisk for recommended
choice_text = f"    {display_name}"
if is_recommended:
    choice_text += " *"
```

**Corrected Code**:
```python
# Check if deployed (exists in .claude/agents/)
is_deployed = agent.name in deployed_full_paths

# Format choice text with asterisk for deployed agents
choice_text = f"    {display_name}"
if is_deployed:
    choice_text += " *"
```

### Change 2: Update Help Text

**File**: `src/claude_mpm/cli/commands/configure.py`
**Line**: 1435

**Current Code**:
```python
self.console.print("[dim]* = Recommended for this project[/dim]")
```

**Corrected Code**:
```python
self.console.print("[dim]* = Already deployed to .claude/agents/[/dim]")
```

---

## Why This Matters

### User Confusion Scenarios

**Current Behavior**:
- User has `python-engineer`, `qa`, `PM` deployed to `.claude/agents/`
- Asterisks appear on DIFFERENT agents (those recommended by detection service)
- User sees deployed agents WITHOUT asterisks
- User sees undeployed agents WITH asterisks (if recommended)
- User asks: "Why aren't my deployed agents marked with asterisks?"

**Expected Behavior**:
- User has `python-engineer`, `qa`, `PM` deployed to `.claude/agents/`
- Asterisks appear on `python-engineer`, `qa`, `PM` (deployed agents)
- User sees clear visual indication of what's already installed
- Checkbox state ([✓] vs [ ]) aligns with asterisk presence
- User understands: asterisk = deployed/installed

---

## Verification Steps

After implementing the fix:

1. **Check deployed agents exist**:
   ```bash
   ls -la .claude/agents/*.md
   # Should show: python-engineer.md, qa.md, PM.md, etc.
   ```

2. **Run configure**:
   ```bash
   claude-mpm configure
   # Select: "Manage Agents"
   ```

3. **Verify asterisks**:
   - [ ] Asterisks appear ONLY on agents with `.md` files in `.claude/agents/`
   - [ ] No asterisks on agents NOT in `.claude/agents/`
   - [ ] Help text says "* = Already deployed to .claude/agents/"
   - [ ] Checkbox state ([✓]) matches asterisk presence

4. **Edge cases**:
   - [ ] Virtual deployment (`.mpm_deployment_state`) shows asterisks correctly
   - [ ] Physical deployment (`.md` files) shows asterisks correctly
   - [ ] Mixed deployment (some virtual, some physical) shows all asterisks

---

## Related Code

### Checkbox State Logic (Already Correct)

**File**: `src/claude_mpm/cli/commands/configure.py`
**Line**: 1422

```python
is_selected = agent.name in current_selection
```

**Note**: Checkbox state ([✓] checked vs [ ] unchecked) ALREADY reflects deployment status correctly. Only asterisk logic needs fixing.

---

## Files Analyzed

1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py`
   - Lines 1260-1268: Deployed IDs fetching
   - Lines 1270-1275: Deployed full paths mapping
   - Lines 1278: Current selection initialization
   - Lines 1412-1420: Asterisk logic (NEEDS FIX)
   - Line 1435: Help text (NEEDS UPDATE)

2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/utils/agent_filters.py`
   - Lines 87-177: `get_deployed_agent_ids()` implementation
   - Detection methods: Virtual state + physical files

3. `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure_agent_display.py`
   - Reviewed for display logic (separate concern, not related to issue)

---

## Conclusion

**Root Cause**: Asterisk logic checks `recommended_agent_ids` (from AgentRecommendationService) instead of `deployed_full_paths` (from filesystem).

**Fix Complexity**: LOW (2-line change + 1-line help text update)

**Fix Confidence**: HIGH (deployed_ids logic already exists and is correct)

**User Impact**: HIGH (removes confusion about what asterisks mean)

**Recommendation**: Implement the 3-line fix immediately. No architectural changes needed.
