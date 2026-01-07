# Agent Filtering Bug: Canonical ID vs Name Mismatch

**Date**: 2025-12-29
**Status**: Root cause identified
**Severity**: High (profile filtering completely broken)
**Issue**: Agent filtering by profile fails due to key mismatch between excluded_agents list and selected_agents dictionary

## Problem Summary

Profile-based agent filtering is not working despite `Config.set()` being called correctly. The framework-development profile should deploy 19 agents but instead deploys all 43 agents.

**Log Evidence**:
```
Profile 'framework-development': Excluding 24 agents from deployment
Selected 43 agents for deployment (system: 0, project: 0, user: 0)
```

## Root Cause

The bug is in `multi_source_deployment_service.py` lines 532-537:

```python
# Apply exclusion filters
if excluded_agents:
    for agent_name in excluded_agents:
        if agent_name in selected_agents:  # ← BUG: Key mismatch!
            self.logger.info(f"Excluding agent '{agent_name}' from deployment")
            del selected_agents[agent_name]
```

**The Issue**:
- `excluded_agents` contains agent **names**: `["pm", "engineer", "qa", ...]`
- `selected_agents` dictionary is keyed by **canonical_id**: `{"bobmatnyc/claude-mpm-agents:pm": {...}, "bobmatnyc/claude-mpm-agents:engineer": {...}, ...}`

The check `if agent_name in selected_agents` looks for `"pm"` as a key, but the actual key is `"bobmatnyc/claude-mpm-agents:pm"`, so it **never matches** and no agents are excluded!

## How Agents Are Keyed

From `multi_source_deployment_service.py` lines 282-294:

```python
# Build canonical_id for enhanced matching
canonical_id = self._build_canonical_id_for_agent(agent_info)

# Group by canonical_id (PRIMARY) for enhanced matching
matching_key = canonical_id  # ← Uses canonical_id as key!

# Initialize list if this is the first occurrence of this agent
if matching_key not in agents_by_name:
    agents_by_name[matching_key] = []

agents_by_name[matching_key].append(agent_info)
```

**Canonical ID Format** (from `_build_canonical_id_for_agent`, lines 120-175):
- Remote agents: `"{collection_id}:{agent_id}"` (e.g., `"bobmatnyc/claude-mpm-agents:pm"`)
- Legacy agents: `"legacy:{filename}"` (e.g., `"legacy:custom-agent"`)

## Why Config.set() Works But Filtering Doesn't

**Trace of Execution**:

1. ✅ **startup.py:496-497** - `Config.set("agent_deployment.excluded_agents", excluded_agents)` works correctly
2. ✅ **startup.py:505** - `AgentDeploymentService(config=deploy_config)` passes config correctly
3. ✅ **agent_deployment.py:393** - `config, excluded_agents = _load_deployment_config(config)` reads correctly
4. ✅ **deployment_config_loader.py:38-42** - `config.get("agent_deployment.excluded_agents", [])` returns correct list
5. ✅ **agent_deployment.py:895** - `excluded_agents=excluded_agents` parameter passed correctly
6. ❌ **multi_source_deployment_service.py:534-535** - **KEY MISMATCH**: Checks `if "pm" in {"bobmatnyc/claude-mpm-agents:pm": ...}` → False!

## Fix Strategy

**Option 1: Match by agent name within loop** (Recommended)
```python
# Apply exclusion filters
if excluded_agents:
    # Create a set for O(1) lookup
    excluded_set = set(excluded_agents)

    agents_to_remove = []
    for canonical_id, agent_info in selected_agents.items():
        # Extract agent name from agent_info
        agent_name = agent_info.get("name") or agent_info.get("metadata", {}).get("name")

        if agent_name and agent_name in excluded_set:
            self.logger.info(f"Excluding agent '{agent_name}' (canonical_id: {canonical_id}) from deployment")
            agents_to_remove.append(canonical_id)

    # Remove excluded agents
    for canonical_id in agents_to_remove:
        del selected_agents[canonical_id]
```

**Option 2: Build canonical_id from excluded names**
```python
# Apply exclusion filters
if excluded_agents:
    agents_to_remove = []

    for agent_name in excluded_agents:
        # Try to find matching canonical_id
        for canonical_id, agent_info in selected_agents.items():
            info_name = agent_info.get("name") or agent_info.get("metadata", {}).get("name")
            if info_name == agent_name:
                agents_to_remove.append(canonical_id)
                break

    # Remove excluded agents
    for canonical_id in agents_to_remove:
        self.logger.info(f"Excluding agent '{canonical_id}' from deployment")
        del selected_agents[canonical_id]
```

**Option 3: Maintain dual indexing**
```python
# In discover_agents_from_all_sources(), maintain both:
agents_by_canonical_id = {}  # Current behavior
agents_by_name = {}  # Additional index for filtering

# Then in get_agents_for_deployment():
if excluded_agents:
    for agent_name in excluded_agents:
        if agent_name in agents_by_name:
            canonical_id = agents_by_name[agent_name]
            if canonical_id in selected_agents:
                del selected_agents[canonical_id]
```

## Recommended Fix

**Option 1** is recommended because:
- Minimal code change (single location)
- O(n) complexity with early loop termination
- Doesn't require refactoring data structures
- Preserves existing canonical_id behavior
- Easy to test and verify

## Impact

**Current State**:
- Profile filtering: ❌ Broken (0% effectiveness)
- Expected agents: 19
- Actual agents: 43 (all agents deployed)
- User experience: Profile selection has no effect

**After Fix**:
- Profile filtering: ✅ Working (100% effectiveness)
- Expected agents: 19
- Actual agents: 19
- User experience: Profile selection correctly filters agents

## Test Case

```python
# Setup
excluded_agents = ["pm", "engineer", "qa"]
selected_agents = {
    "bobmatnyc/claude-mpm-agents:pm": {"name": "pm", ...},
    "bobmatnyc/claude-mpm-agents:engineer": {"name": "engineer", ...},
    "bobmatnyc/claude-mpm-agents:research": {"name": "research", ...},
}

# Current behavior (BROKEN)
for agent_name in excluded_agents:
    if agent_name in selected_agents:  # Never matches!
        del selected_agents[agent_name]

assert len(selected_agents) == 3  # ❌ FAIL: Nothing excluded

# Fixed behavior
excluded_set = set(excluded_agents)
agents_to_remove = []

for canonical_id, agent_info in selected_agents.items():
    agent_name = agent_info.get("name")
    if agent_name and agent_name in excluded_set:
        agents_to_remove.append(canonical_id)

for canonical_id in agents_to_remove:
    del selected_agents[canonical_id]

assert len(selected_agents) == 1  # ✅ PASS: Only "research" remains
```

## Files Involved

**Primary Bug Location**:
- `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py:532-537`

**Related Code**:
- `src/claude_mpm/cli/startup.py:486-503` (Profile filtering setup)
- `src/claude_mpm/services/agents/deployment/deployment_config_loader.py:38-42` (Config reading)
- `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py:282-294` (Canonical ID keying)

## Next Steps

1. Implement Option 1 fix in `multi_source_deployment_service.py`
2. Add test case to verify filtering works with canonical IDs
3. Test with framework-development profile (should deploy 19 agents, not 43)
4. Add logging to show which canonical_id was excluded for each agent name
5. Consider adding validation to warn if excluded_agents contains names that don't match any discovered agents

## Additional Notes

**Why Source Counts Are All Zero**:
```
Selected 43 agents for deployment (system: 0, project: 0, user: 0)
```

This is because all agents are from the `"remote"` source (cached from GitHub), not from system/project/user sources. The logging doesn't count "remote" source, only the three legacy sources. This is informational only and not related to the filtering bug.

**Profile Manager Behavior**:
The profile manager correctly:
- Loads the framework-development profile
- Identifies 24 agents to exclude
- Calls `Config.set("agent_deployment.excluded_agents", excluded_agents)`
- Logs: "Profile 'framework-development': Excluding 24 agents from deployment"

The bug is purely in the filtering implementation, not in the profile loading or config management.
