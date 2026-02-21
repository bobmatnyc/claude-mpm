# Frontend Investigation: UI Display Logic Analysis

## 1. TypeScript Interfaces

**File**: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts`

### DeployedAgent Interface (lines 13-29)
```typescript
export interface DeployedAgent {
    name: string;           // ← "svelte-engineer" (file stem from backend)
    location: string;
    path: string;
    version: string;
    type: string;
    is_core: boolean;
    description?: string;
    category?: string;
    color?: string;
    tags?: string[];
    resource_tier?: string;
    network_access?: boolean;
    skills_count?: number;
}
```

### AvailableAgent Interface (lines 31-42)
```typescript
export interface AvailableAgent {
    agent_id: string;       // ← "svelte-engineer" (from backend agent_id)
    name: string;           // ← "Svelte Engineer" (from backend metadata.name)
    description: string;
    version: string;
    source: string;
    source_url: string;
    priority: number;
    category: string;
    tags: string[];
    is_deployed: boolean;   // ← always false due to backend bug
}
```

**Key observation**: `DeployedAgent.name` = "svelte-engineer" while `AvailableAgent.name` = "Svelte Engineer". These are supposed to represent the same field but contain different formats.

## 2. AgentsList.svelte Component

**File**: `src/claude_mpm/dashboard-svelte/src/lib/components/config/AgentsList.svelte`

### Version Update Detection (lines 145-156)

```typescript
let outdatedCount = $derived.by(() => {
    let count = 0;
    for (const deployed of deployedAgents) {
        const available = availableAgents.find(a => a.name === deployed.name);
        //  Tries: "Svelte Engineer" === "svelte-engineer"  → NEVER matches
        if (available && deployed.version && available.version) {
            if (compareVersions(deployed.version, available.version) === 'outdated') {
                count++;
            }
        }
    }
    return count;
});
```

**Bug**: `outdatedCount` is always 0 because `a.name` ("Svelte Engineer") never equals `deployed.name` ("svelte-engineer").

### getAvailableVersion() (lines 159-161)

```typescript
function getAvailableVersion(agentName: string): string | undefined {
    return availableAgents.find(a => a.name === agentName)?.version;
    //  agentName = "svelte-engineer", a.name = "Svelte Engineer" → never matches
}
```

**Bug**: Always returns `undefined` due to same name mismatch.

### Selected Agent Comparison (line 209-212)

```typescript
function getSelectedName(agent: DeployedAgent | AvailableAgent | null): string {
    if (!agent) return '';
    return agent.name;
}
```

This is used for selection highlighting. When a deployed agent "svelte-engineer" is selected, clicking on the available "Svelte Engineer" won't show it as the same agent.

### Deploy Action (lines 223-237)

```typescript
async function handleDeploy(agent: AvailableAgent) {
    deployingAgents = new Set([...deployingAgents, agent.name]);
    // agent.name = "Svelte Engineer" → sent to backend as deploy name
    // BUT: The deploy endpoint expects agent_name matching filesystem
    try {
        await deployAgent(agent.name);
        // This calls POST /api/config/agents/deploy with body:
        // { "agent_name": "Svelte Engineer" }  ← MAY FAIL or create wrong file
```

**Potential Bug**: If user clicks "Deploy" on an available agent, the `agent.name` sent is "Svelte Engineer" which may not match the expected kebab-case filename. However, the deploy endpoint uses `agent_name` to look up in cache via `GitSourceManager.get_agent_path()` which does normalize names.

### Keyed Iteration (line 540)

```svelte
{#each group.agents as agent (agent.agent_id || agent.name)}
```

Uses `agent_id` as the Svelte key, which is correct for uniqueness. But display uses `agent.name`.

## 3. Display Rendering

### Deployed Agents Display (line 408)
```svelte
<HighlightedText text={agent.name} query={searchQuery} />
```
Shows: `svelte-engineer` (file stem)

### Available Agents Display (line 554)
```svelte
<HighlightedText text={agent.name} query={searchQuery} />
```
Shows: `Svelte Engineer` (human-readable)

## 4. Store Fetch Functions

### fetchDeployedAgents() (lines 189-199)
```typescript
export async function fetchDeployedAgents() {
    const data = await fetchJSON(`${API_BASE}/agents/deployed`);
    deployedAgents.set(data.agents);
    // data.agents[].name = file stems
}
```

### fetchAvailableAgents() (lines 201-214)
```typescript
export async function fetchAvailableAgents(search?: string) {
    const data = await fetchJSON(url);
    availableAgents.set(data.agents);
    // data.agents[].name = human-readable names
    // data.agents[].agent_id = kebab-case IDs
}
```

No client-side normalization is applied between fetch and store update.

## 5. Impact Summary

| Feature | Status | Reason |
|---------|--------|--------|
| Deployed agents display | Shows file stems | Correct but inconsistent |
| Available agents display | Shows human-readable | Correct but inconsistent |
| `is_deployed` badge | Always false | Backend comparison uses wrong field |
| Version update count | Always 0 | Frontend name matching fails |
| Available version display | Never shows | Frontend name matching fails |
| Deploy button visibility | Shows for deployed | is_deployed is always false |
| Selection highlighting | Cross-section fails | Name mismatch |
| Deploy action | May fail | Sends human-readable name |

## 6. Frontend Fix Requirements

1. **Add `display_name` field** to `AvailableAgent` interface for human-readable name
2. **Use `agent_id` as `name`** for matching/comparison
3. **Update `AgentsList.svelte`** to render `display_name` but compare on `name`/`agent_id`
4. **Fix version comparison** to use `agent_id` for matching
5. **Fix deploy action** to send `agent_id` instead of `name`
