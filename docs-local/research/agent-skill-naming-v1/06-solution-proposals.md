# Solution Proposals: Agent Naming Consistency Fix

## Solution Overview

Three solution options are presented, from minimal to comprehensive. **Option A is recommended** as it fixes the root cause with minimal blast radius.

---

## Option A: Fix Backend Name Promotion + is_deployed (Recommended)

**Principle**: Use `agent_id` as the canonical identifier everywhere; add `display_name` for human-readable rendering.

### Changes Required

#### 1. `config_routes.py` - Fix name promotion and is_deployed

**File**: `src/claude_mpm/services/monitor/config_routes.py`

**Before** (lines 365-392):
```python
# Promote metadata fields to root level for frontend compatibility.
for agent in agents:
    metadata = agent.get("metadata", {})
    agent.setdefault("name", metadata.get("name", agent.get("agent_id", "")))
    agent.setdefault("description", metadata.get("description", ""))

# ...

for agent in agents:
    agent_name = agent.get("name", agent.get("agent_id", ""))
    agent["is_deployed"] = agent_name in deployed_names
```

**After**:
```python
# Promote metadata fields to root level for frontend compatibility.
# Use agent_id as primary "name" for consistency with deployed agents.
# Add display_name for human-readable rendering in the UI.
for agent in agents:
    metadata = agent.get("metadata", {})
    agent_id = agent.get("agent_id", "")
    human_name = metadata.get("name", agent_id)

    # Set name = agent_id for consistent matching with deployed agents
    agent.setdefault("name", agent_id or human_name)
    # Provide display_name for UI rendering
    agent["display_name"] = human_name
    agent.setdefault("description", metadata.get("description", ""))

# ...

for agent in agents:
    # Use agent_id for deployed comparison (file stems match agent_ids)
    agent_id = agent.get("agent_id", agent.get("name", ""))
    agent["is_deployed"] = agent_id in deployed_names
```

#### 2. `config.svelte.ts` - Update AvailableAgent interface

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`

**Before** (lines 31-42):
```typescript
export interface AvailableAgent {
    agent_id: string;
    name: string;
    // ...
}
```

**After**:
```typescript
export interface AvailableAgent {
    agent_id: string;
    name: string;           // Now agent_id-based (kebab-case), consistent with DeployedAgent
    display_name: string;   // Human-readable name for UI rendering
    // ...
}
```

#### 3. `AgentsList.svelte` - Use display_name for rendering

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/AgentsList.svelte`

Update available agent rendering to use `display_name`:

**Before** (line 554):
```svelte
<HighlightedText text={agent.name} query={searchQuery} />
```

**After**:
```svelte
<HighlightedText text={agent.display_name || agent.name} query={searchQuery} />
```

Update search to include display_name:
```typescript
function matchesSearch(item: { name: string; display_name?: string; ... }, query: string): boolean {
    if (!query) return true;
    const q = query.toLowerCase();
    return item.name.toLowerCase().includes(q) ||
        (item.display_name ?? '').toLowerCase().includes(q) ||
        // ... rest of fields
}
```

Update deploy action to use agent_id:
```typescript
async function handleDeploy(agent: AvailableAgent) {
    const deployName = agent.agent_id || agent.name;
    deployingAgents = new Set([...deployingAgents, deployName]);
    try {
        await deployAgent(deployName);
```

### Pros
- Fixes root cause at the API level
- Minimal blast radius (3-4 files)
- Backward compatible (name field still exists)
- Frontend gets both machine ID and display name
- is_deployed comparison works correctly

### Cons
- Requires frontend update to use display_name
- Existing API consumers may expect name = human-readable

### Estimated Effort
- Backend: 1 hour
- Frontend: 1-2 hours
- Tests: 1 hour
- **Total: 3-4 hours**

---

## Option B: Frontend-Only Normalization

**Principle**: Keep backend as-is; normalize names client-side using `agent_id` field.

### Changes Required

#### 1. `AgentsList.svelte` - Match on agent_id

```typescript
// Version comparison using agent_id
let outdatedCount = $derived.by(() => {
    let count = 0;
    for (const deployed of deployedAgents) {
        const available = availableAgents.find(
            a => a.agent_id === deployed.name ||
                 a.name.toLowerCase().replace(/\s+/g, '-') === deployed.name
        );
        // ...
    }
    return count;
});
```

### Pros
- No backend changes needed
- Quick to implement

### Cons
- Does NOT fix `is_deployed` backend bug (still always false)
- Fragile string normalization
- Multiple places need the same normalization logic
- Doesn't fix deploy action sending wrong name

### Estimated Effort
- Frontend: 2 hours
- Tests: 1 hour
- **Total: 3 hours** (but incomplete fix)

---

## Option C: Comprehensive Backend Normalization

**Principle**: Ensure both endpoints return identical name formats and add agent_id to deployed agents.

### Changes Required

#### 1. Add agent_id to deployed agents response

In `handle_agents_deployed()`, extract `agent_id` from frontmatter:
```python
agents_list = [
    {
        "name": name,
        "agent_id": name,  # File stem IS the agent_id
        "display_name": details.get("frontmatter_name", name),
        **details
    }
    for name, details in agents_data.items()
]
```

#### 2. Standardize available agents (same as Option A)

#### 3. Add display_name to deployed agents

Extract from frontmatter in `_extract_enrichment_fields()`:
```python
enrichment["display_name"] = fmdata.get("name", "")
```

#### 4. Update both frontend interfaces

```typescript
export interface DeployedAgent {
    name: string;           // agent_id (kebab-case)
    agent_id: string;       // explicit agent_id
    display_name: string;   // human-readable
    // ...
}

export interface AvailableAgent {
    agent_id: string;
    name: string;           // agent_id (kebab-case)
    display_name: string;   // human-readable
    // ...
}
```

### Pros
- Most thorough fix
- Both interfaces fully aligned
- agent_id explicitly available on all agents
- Display names available for both deployed and available

### Cons
- Larger blast radius (5+ files)
- More test updates needed
- May break existing frontend logic that assumes DeployedAgent.name is file stem

### Estimated Effort
- Backend: 2 hours
- Frontend: 2 hours
- Tests: 2 hours
- **Total: 6 hours**

---

## Recommendation

**Option A** is recommended because:

1. **Fixes the root cause** (name promotion and is_deployed comparison)
2. **Minimal blast radius** (3-4 files vs 5+ for Option C)
3. **Backward compatible** (name field still present, display_name is additive)
4. **Frontend already has agent_id** on AvailableAgent - just needs to use it more
5. **Most bugs are in the available agents path** - deployed agents work fine as-is

Option C can be pursued later as an enhancement if needed.

---

## Implementation Checklist

### Phase 1: Backend Fix (Option A)
- [ ] Update `config_routes.py:handle_agents_available()` name promotion
- [ ] Update `config_routes.py:handle_agents_available()` is_deployed comparison
- [ ] Add `display_name` field to available agents response
- [ ] Update/add tests in `tests/test_config_routes.py`

### Phase 2: Frontend Fix
- [ ] Update `AvailableAgent` interface in `config.svelte.ts`
- [ ] Update `AgentsList.svelte` to use `display_name` for rendering
- [ ] Update `AgentsList.svelte` version comparison to use `name`/`agent_id`
- [ ] Update deploy/undeploy actions to use `agent_id`
- [ ] Update search to include `display_name`

### Phase 3: Verification
- [ ] Verify deployed and available lists show consistent names
- [ ] Verify `is_deployed` flag works correctly
- [ ] Verify version update detection works
- [ ] Verify deploy/undeploy actions work from both lists
- [ ] Verify search works with both name formats
- [ ] Build Svelte dashboard and verify compiled output

### Phase 4: Cleanup
- [ ] Update any API documentation
- [ ] Check for other consumers of the available agents endpoint
- [ ] Consider adding `agent_id` to deployed agents (Option C enhancement)
