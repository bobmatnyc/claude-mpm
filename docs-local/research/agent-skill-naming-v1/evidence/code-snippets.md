# Evidence: Key Code Snippets

## 1. Root Cause: Name Promotion in config_routes.py

### Location: `src/claude_mpm/services/monitor/config_routes.py:365-372`

```python
# Promote metadata fields to root level for frontend compatibility.
# The discovery service nests name/description under metadata,
# but the frontend AvailableAgent interface expects them at root.
for agent in agents:
    metadata = agent.get("metadata", {})
    agent.setdefault(
        "name", metadata.get("name", agent.get("agent_id", ""))
    )
    agent.setdefault("description", metadata.get("description", ""))
```

**Problem**: `metadata.name` = "Svelte Engineer" (human-readable) takes priority over `agent_id` = "svelte-engineer" (machine ID) because the raw dict doesn't have a root `name` key, so `setdefault` sets it to `metadata.name`.

## 2. Root Cause: Broken is_deployed Comparison

### Location: `src/claude_mpm/services/monitor/config_routes.py:386-392`

```python
# Enrich with is_deployed flag by checking project agents
# Use lightweight list_agent_names() to avoid parsing all agent files
agent_mgr = _get_agent_manager()
deployed_names = agent_mgr.list_agent_names(location="project")

for agent in agents:
    agent_name = agent.get("name", agent.get("agent_id", ""))
    agent["is_deployed"] = agent_name in deployed_names
```

**Problem**: After line 370 sets `name` = "Svelte Engineer", this comparison becomes:
`"Svelte Engineer" in {"svelte-engineer", ...}` which is always `False`.

## 3. Deployed Names Source

### Location: `src/claude_mpm/services/agents/management/agent_management_service.py:286-289`

```python
if location in (None, "project"):
    if self.project_dir.exists():
        names.update(f.stem for f in self.project_dir.glob("*.md"))
```

Returns file stems like `{"svelte-engineer", "python-engineer", "engineer"}`.

## 4. Available Agents Discovery

### Location: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py:700-735`

```python
return {
    "agent_id": agent_id,  # "svelte-engineer" (from YAML or filename)
    "metadata": {
        "name": name,      # "Svelte Engineer" (from YAML name field)
        "description": description,
        ...
    },
    ...
}
```

Two separate fields with different formats.

## 5. Frontend Version Comparison Bug

### Location: `src/claude_mpm/dashboard-svelte/src/lib/components/config/AgentsList.svelte:145-156`

```typescript
let outdatedCount = $derived.by(() => {
    let count = 0;
    for (const deployed of deployedAgents) {
        const available = availableAgents.find(a => a.name === deployed.name);
        // "Svelte Engineer" === "svelte-engineer" → never matches
        if (available && deployed.version && available.version) {
            if (compareVersions(deployed.version, available.version) === 'outdated') {
                count++;
            }
        }
    }
    return count;
});
```

## 6. Deployed Agents Response Construction

### Location: `src/claude_mpm/services/monitor/config_routes.py:316-318`

```python
agents_list = [
    {"name": name, **details} for name, details in agents_data.items()
]
```

`name` = dict key from `list_agents()` = file stem.

## 7. Frontend TypeScript Interfaces

### Location: `src/claude_mpm/dashboard-svelte/src/lib/stores/config.svelte.ts:13-42`

```typescript
export interface DeployedAgent {
    name: string;       // "svelte-engineer" (file stem)
    // ...
}

export interface AvailableAgent {
    agent_id: string;   // "svelte-engineer" (YAML agent_id)
    name: string;       // "Svelte Engineer" (YAML name) ← MISMATCH
    // ...
}
```
