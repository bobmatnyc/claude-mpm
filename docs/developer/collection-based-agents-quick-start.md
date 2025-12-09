# Collection-Based Agents Quick Start Guide

## Overview

Claude MPM now supports **collection-based agent selection** for easier bulk deployment and management of agent sets.

## Key Concepts

### Collection ID
Format: `owner/repo-name` (e.g., `bobmatnyc/claude-mpm-agents`)

Automatically extracted from repository path:
```
~/.claude-mpm/cache/remote-agents/{owner}/{repo}/agents/...
                                    ↓       ↓
                              collection_id: owner/repo
```

### Canonical ID
Format: `collection_id:agent_id` or `legacy:filename`

Examples:
- Remote agent: `bobmatnyc/claude-mpm-agents:pm`
- Legacy agent: `legacy:custom-engineer`

### Source Path
Relative path within repository:
```
agents/research/research-agent.md  (path within repo)
```

## Quick Commands

### List Collections
```bash
# See all available collections
claude-mpm agents list-collections
```

Output:
```
Available Agent Collections:

  • bobmatnyc/claude-mpm-agents (45 agents)
  • user/custom-collection (5 agents)
```

### List Agents in Collection
```bash
# Table format (default)
claude-mpm agents list-by-collection bobmatnyc/claude-mpm-agents

# JSON format
claude-mpm agents list-by-collection bobmatnyc/claude-mpm-agents --format json

# YAML format
claude-mpm agents list-by-collection bobmatnyc/claude-mpm-agents --format yaml
```

### Deploy Collection
```bash
# Dry run (see what would be deployed)
claude-mpm agents deploy-collection bobmatnyc/claude-mpm-agents --dry-run

# Force deployment (override existing)
claude-mpm agents deploy-collection bobmatnyc/claude-mpm-agents --force
```

## Python API

### Get Agents by Collection
```python
from claude_mpm.core.unified_agent_registry import get_agents_by_collection

# Get all agents from a collection
agents = get_agents_by_collection("bobmatnyc/claude-mpm-agents")

for agent in agents:
    print(f"{agent.name} - {agent.description}")
```

### List All Collections
```python
from claude_mpm.core.unified_agent_registry import list_collections

# Get collection metadata
collections = list_collections()

for collection in collections:
    print(f"{collection['collection_id']}: {collection['agent_count']} agents")
    print(f"  Agents: {', '.join(collection['agents'])}")
```

### Get Agent by Canonical ID
```python
from claude_mpm.core.unified_agent_registry import get_agent_by_canonical_id

# Find specific agent by canonical ID
agent = get_agent_by_canonical_id("bobmatnyc/claude-mpm-agents:pm")

if agent:
    print(f"Found: {agent.name}")
    print(f"Version: {agent.version}")
    print(f"Path: {agent.path}")
```

## Frontmatter Format

Agents now support collection metadata in frontmatter:

```yaml
---
name: research_agent
agent_id: research-agent
collection_id: bobmatnyc/claude-mpm-agents  # Auto-populated
source_path: agents/research/research-agent.md  # Auto-populated
canonical_id: bobmatnyc/claude-mpm-agents:research-agent  # Auto-generated
version: 4.9.0
---

# Research Agent

Your agent content here...
```

### Auto-Population

When agents are synced from the cache:
- `collection_id` extracted from repository path
- `source_path` extracted from file path in repo
- `canonical_id` auto-generated from collection_id + agent_id

## Use Cases

### 1. Deploy All QA Agents
```bash
# If QA agents are in a collection
claude-mpm agents list-collections  # Find collection ID
claude-mpm agents deploy-collection qa-agents-collection
```

### 2. Audit Agent Sources
```python
from claude_mpm.core.unified_agent_registry import get_agent_registry

registry = get_agent_registry()
agents = registry.discover_agents()

# Group by collection
for name, metadata in agents.items():
    if metadata.collection_id:
        print(f"{name}: {metadata.collection_id}")
    else:
        print(f"{name}: legacy (no collection)")
```

### 3. Version Comparison Across Collections
```python
from claude_mpm.services.agents.deployment import MultiSourceAgentDeploymentService

service = MultiSourceAgentDeploymentService()

# Discover agents from all sources (including collections)
agents_by_name = service.discover_agents_from_all_sources()

# Select highest version (uses canonical_id matching)
selected = service.select_highest_version_agents(agents_by_name)

for canonical_id, agent_info in selected.items():
    print(f"{canonical_id}: v{agent_info['version']} from {agent_info['source']}")
```

## Backward Compatibility

### Legacy Agents
Agents without collection metadata automatically get:
- `canonical_id: legacy:{filename}`
- Continue to work with existing matching logic
- No migration required

### Mixed Deployments
You can have both:
- Collection-based agents (with canonical_id)
- Legacy agents (without canonical_id)

The system handles both seamlessly.

## Troubleshooting

### "No collections found"
```bash
# Sync agent cache first
claude-mpm agents cache-pull

# Then list collections
claude-mpm agents list-collections
```

### "Agent not found in collection"
```bash
# Check collection contents
claude-mpm agents list-by-collection bobmatnyc/claude-mpm-agents --format json

# Verify agent is in cache
ls ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/
```

### Collection ID format error
- Must be: `owner/repo-name`
- Examples: ✅ `bobmatnyc/claude-mpm-agents` ❌ `bobmatnyc-claude-mpm-agents`

## Advanced Usage

### Custom Collection Filters
```python
from claude_mpm.core.unified_agent_registry import get_agent_registry

registry = get_agent_registry()

# Get all agents, then filter by multiple criteria
all_agents = registry.discover_agents()

# Filter by collection and tags
qa_agents = [
    agent for agent in all_agents.values()
    if agent.collection_id == "bobmatnyc/claude-mpm-agents"
    and "qa" in agent.tags
]
```

### Collection-Based Deployment Script
```python
#!/usr/bin/env python3
from pathlib import Path
from claude_mpm.services.agents.deployment import MultiSourceAgentDeploymentService

def deploy_essential_collections():
    """Deploy core agent collections."""
    service = MultiSourceAgentDeploymentService()

    collections = [
        "bobmatnyc/claude-mpm-agents",
        "user/custom-qa-agents",
    ]

    for collection_id in collections:
        agents = service.get_agents_by_collection(collection_id)
        print(f"Deploying {len(agents)} agents from {collection_id}")

        # Deploy each agent
        for agent in agents:
            print(f"  • {agent['metadata']['name']}")
            # Deployment logic here

if __name__ == "__main__":
    deploy_essential_collections()
```

## Next Steps

1. **Explore Collections**: `claude-mpm agents list-collections`
2. **Filter Agents**: Use `list-by-collection` to see what's available
3. **Deploy Selectively**: Use collection-based deployment for bulk operations
4. **Check Matching**: Verify canonical_id matching with `--format json`

## References

- Full implementation: `/docs/implementation/enhanced-agent-matching.md`
- Agent discovery: `RemoteAgentDiscoveryService`
- Matching logic: `MultiSourceAgentDeploymentService`
- API reference: `UnifiedAgentRegistry`
