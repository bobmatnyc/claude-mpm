# Backend Investigation: API and Service Layer Analysis

## 1. API Endpoint Comparison

### GET /api/config/agents/deployed

**Handler**: `config_routes.py:handle_agents_deployed()` (lines 305-348)

**Data source**: `AgentManager.list_agents(location="project")` which:
- Globs `*.md` files from `.claude/agents/` directory
- Uses the **file stem** as the dict key (and thus the agent name)
- Returns `Dict[str, Dict[str, Any]]` where keys are file stems

**Response shape**:
```json
{
  "success": true,
  "agents": [
    {
      "name": "svelte-engineer",       // ← file stem
      "location": "project",
      "path": "/path/to/.claude/agents/svelte-engineer.md",
      "version": "2.0.0",
      "type": "specialist",
      "is_core": false,
      "description": "Specialized agent for Svelte...",
      "category": "engineer",
      "color": "orange",
      "tags": ["svelte", "frontend"]
    }
  ],
  "total": 1
}
```

**Key code** (`config_routes.py:316-318`):
```python
agents_list = [
    {"name": name, **details} for name, details in agents_data.items()
]
```
The `name` is the dict key from `list_agents()`, which is `agent_file.stem`.

### GET /api/config/agents/available

**Handler**: `config_routes.py:handle_agents_available()` (lines 351-420)

**Data source**: `GitSourceManager.list_cached_agents()` which:
- Discovers agents via `RemoteAgentDiscoveryService`
- Returns list of dicts with nested `metadata.name` and root-level `agent_id`

**Critical name promotion** (`config_routes.py:368-372`):
```python
for agent in agents:
    metadata = agent.get("metadata", {})
    agent.setdefault("name", metadata.get("name", agent.get("agent_id", "")))
    agent.setdefault("description", metadata.get("description", ""))
```

This `setdefault` call sets `name` to `metadata.name` ("Svelte Engineer") because
the raw agent dict from discovery does NOT have a root-level `name` key yet.

**Response shape**:
```json
{
  "success": true,
  "agents": [
    {
      "agent_id": "svelte-engineer",       // ← kebab-case from frontmatter
      "name": "Svelte Engineer",            // ← human-readable from metadata.name
      "description": "Specialized agent...",
      "version": "2.0.0",
      "source": "bobmatnyc/claude-mpm-agents",
      "category": "engineer",
      "is_deployed": false                   // ← ALWAYS FALSE due to comparison bug
    }
  ],
  "total": 1
}
```

## 2. The is_deployed Comparison Bug

**Location**: `config_routes.py:386-392`

```python
# Enrich with is_deployed flag by checking project agents
# Use lightweight list_agent_names() to avoid parsing all agent files
agent_mgr = _get_agent_manager()
deployed_names = agent_mgr.list_agent_names(location="project")
#  → Returns: {"svelte-engineer", "python-engineer", "engineer", ...}
#    (file stems from .claude/agents/*.md)

for agent in agents:
    agent_name = agent.get("name", agent.get("agent_id", ""))
    #  → Gets "Svelte Engineer" (human-readable, set by line 370)
    agent["is_deployed"] = agent_name in deployed_names
    #  → "Svelte Engineer" in {"svelte-engineer"} = False!
```

**Fix**: Use `agent_id` for the comparison:
```python
for agent in agents:
    agent_id = agent.get("agent_id", agent.get("name", ""))
    agent["is_deployed"] = agent_id in deployed_names
```

## 3. Service Layer: AgentManager

**File**: `src/claude_mpm/services/agents/management/agent_management_service.py`

### list_agents() (line 291-340)

Returns `Dict[str, Dict[str, Any]]` where:
- **Key** = `agent_file.stem` (e.g., `"svelte-engineer"`)
- **Value** = enriched metadata dict

```python
for agent_file in self.project_dir.glob("*.md"):
    agent_name = agent_file.stem        # ← "svelte-engineer"
    entry = _build_agent_entry(agent_file, agent_name, "project")
    if entry:
        agents[agent_name] = entry      # ← dict key is file stem
```

### list_agent_names() (line 265-289)

Returns `Set[str]` of file stems:
```python
names.update(f.stem for f in self.project_dir.glob("*.md"))
# → {"svelte-engineer", "python-engineer", ...}
```

## 4. Service Layer: RemoteAgentDiscoveryService

**File**: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

### _parse_markdown_agent() (line 551-735)

Returns a dict with **two different name representations**:

```python
return {
    "agent_id": agent_id,           # "svelte-engineer" (from YAML agent_id or filename)
    "metadata": {
        "name": name,               # "Svelte Engineer" (from YAML name field)
        "description": description,
        ...
    },
    ...
}
```

The `agent_id` comes from:
1. YAML frontmatter `agent_id` field (e.g., `agent_id: svelte-engineer`)
2. Fallback: filename stem (e.g., `svelte-engineer.md` -> `"svelte-engineer"`)

The `metadata.name` comes from:
1. YAML frontmatter `name` field (e.g., `name: Svelte Engineer`)
2. Fallback: first markdown heading
3. Last resort: filename stem with spaces/title case

## 5. Agent Detail Endpoint

**Handler**: `config_routes.py:handle_agent_detail()` (lines 677-791)

This endpoint returns BOTH `name` and `agent_id` from frontmatter:
```python
return {
    "name": fmdata.get("name", agent_name),      # Human-readable
    "agent_id": fmdata.get("agent_id", agent_name), # Machine ID
    ...
}
```

The detail endpoint correctly distinguishes between the two. The bug is only in the list endpoints.

## 6. Key Observation: agent_id is Already Consistent

Both deployed and available agents have a consistent `agent_id`:
- **Deployed**: file stem IS the agent_id (filenames match YAML agent_id)
- **Available**: `agent_id` field from YAML frontmatter

The fix is to use `agent_id` as the primary comparison key, not `name`.
