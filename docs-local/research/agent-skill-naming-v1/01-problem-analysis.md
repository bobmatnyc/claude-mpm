# Problem Analysis: Agent Naming Inconsistency

## 1. Problem Description

When viewing the Dashboard Config tab's Agents sub-tab, the same agent appears with different names depending on whether it's listed under "Deployed" or "Available":

```
Deployed section:     svelte-engineer    (kebab-case, from filesystem)
Available section:    Svelte Engineer    (Title Case, from YAML frontmatter)
```

This makes it appear as though there are two different agents rather than one agent that is deployed.

## 2. Data Flow Analysis

### 2.1 Deployed Agents Data Flow

```
Filesystem (.claude/agents/)
    │
    ├── svelte-engineer.md
    ├── python-engineer.md
    └── ...
    │
    ▼
AgentManager.list_agents(location="project")
    │  Returns: Dict[str, Dict] where keys = file stems
    │  e.g., {"svelte-engineer": {"location": "project", "version": "2.0", ...}}
    │
    ▼
config_routes.py:handle_agents_deployed() [line 316-318]
    │  Builds: [{"name": "svelte-engineer", "location": "project", ...}]
    │  The "name" key = dict key = file stem
    │
    ▼
Frontend: DeployedAgent.name = "svelte-engineer"
```

### 2.2 Available Agents Data Flow

```
Cache directory (~/.claude-mpm/cache/agents/)
    │
    ├── bobmatnyc/claude-mpm-agents/agents/engineer/svelte-engineer.md
    └── ...    (YAML frontmatter: agent_id: "svelte-engineer", name: "Svelte Engineer")
    │
    ▼
RemoteAgentDiscoveryService._parse_markdown_agent() [line 702-735]
    │  Returns: {
    │    "agent_id": "svelte-engineer",          ← from YAML agent_id or filename
    │    "metadata": {
    │      "name": "Svelte Engineer",            ← from YAML name (human-readable)
    │      "description": "...",
    │      ...
    │    },
    │    ...
    │  }
    │
    ▼
GitSourceManager.list_cached_agents() [line 273-418]
    │  Passes through discovery results, deduplicates by agent_id
    │
    ▼
config_routes.py:handle_agents_available() [line 368-372]
    │  CRITICAL: Promotes metadata.name to root:
    │  agent.setdefault("name", metadata.get("name", agent.get("agent_id", "")))
    │  Result: agent["name"] = "Svelte Engineer"  ← human-readable, NOT agent_id
    │
    ▼
config_routes.py [line 388-392]
    │  is_deployed comparison:
    │  deployed_names = {"svelte-engineer", ...}      ← from file stems
    │  agent_name = agent.get("name", ...)            ← "Svelte Engineer"
    │  agent["is_deployed"] = "Svelte Engineer" in {"svelte-engineer"}  ← FALSE!
    │
    ▼
Frontend: AvailableAgent.name = "Svelte Engineer"
Frontend: AvailableAgent.is_deployed = false  ← WRONG!
```

## 3. The Three Bugs

### Bug 1: Display Name Mismatch
- **Where**: `config_routes.py:370` - `agent.setdefault("name", metadata.get("name", ...))`
- **What**: Promotes human-readable name instead of machine-friendly agent_id
- **Effect**: Deployed list shows "svelte-engineer", Available shows "Svelte Engineer"

### Bug 2: Broken `is_deployed` Flag
- **Where**: `config_routes.py:391` - `agent_name = agent.get("name", agent.get("agent_id", ""))`
- **What**: Compares "Svelte Engineer" against deployed file stems like "svelte-engineer"
- **Effect**: `is_deployed` is always `false` for available agents
- **Cascade**: Deploy button shown for already-deployed agents

### Bug 3: Broken Frontend Version Comparison
- **Where**: `AgentsList.svelte:148` - `availableAgents.find(a => a.name === deployed.name)`
- **What**: Tries to match "svelte-engineer" (deployed) with "Svelte Engineer" (available)
- **Effect**: `outdatedCount` is always 0, `getAvailableVersion()` never returns a match

## 4. Naming Convention Origins

| Source | Field | Format | Example |
|--------|-------|--------|---------|
| Filesystem (deployed) | file stem | kebab-case | `svelte-engineer` |
| YAML frontmatter | `agent_id` | kebab-case | `svelte-engineer` |
| YAML frontmatter | `name` | Title Case (spaces) | `Svelte Engineer` |
| API deployed response | `name` | kebab-case (from stem) | `svelte-engineer` |
| API available response | `name` | Title Case (from metadata.name) | `Svelte Engineer` |
| API available response | `agent_id` | kebab-case | `svelte-engineer` |

The `agent_id` field is already consistent across both sources. The problem is that the available agents endpoint uses `metadata.name` (human-readable) instead of `agent_id` for the root-level `name` field.

## 5. Scope of Impact

### Affected Components
1. **Backend**: `config_routes.py` - name promotion logic and is_deployed comparison
2. **Frontend Store**: `config.svelte.ts` - TypeScript interfaces
3. **Frontend UI**: `AgentsList.svelte` - display rendering and version comparison
4. **Frontend UI**: `AgentDetailPanel.svelte` - detail panel may show wrong data

### NOT Affected
- Agent deployment/undeployment (uses `agent_name` parameter directly)
- Skill naming (different pipeline, different data structures)
- CLI agent listing (uses different code paths)
- Agent template building (uses agent_id correctly)
