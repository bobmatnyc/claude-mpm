# Research: Agent Loading and Dynamic Delegation Matrix Generation

**Date**: 2025-02-06
**Status**: Complete
**Classification**: Actionable

## Executive Summary

This research documents how claude-mpm loads agents, assembles PM instructions, and identifies pathways for dynamic delegation matrix generation. Key finding: The ClaudeProvider exists but is Phase 1 mock only - programmatic Claude API calls require completing Phase 2 implementation.

---

## 1. Agent Loading Process

### Discovery Flow

```
unified_agent_registry.py
    |
    v
discover_agents() -> scans templates/ directory
    |
    v
agent_loader.py -> loads JSON definitions
    |
    v
agents_metadata.py -> extracts metadata for PM
```

### Key Files

| File | Purpose |
|------|---------|
| `src/claude_mpm/core/unified_agent_registry.py` | Central discovery and registration |
| `src/claude_mpm/agents/agent_loader.py` | Loads agent JSON files |
| `src/claude_mpm/agents/agents_metadata.py` | Extracts metadata for PM instructions |

### Storage Locations

- **Templates**: `src/claude_mpm/agents/templates/*.json`
- **Schema**: `src/claude_mpm/schemas/agent_schema.json` (v1.3.0)
- **Base**: `src/claude_mpm/agents/base_agent.json`

### Available Info Per Agent

From schema v1.3.0, each agent provides:

```json
{
  "agent_id": "research",
  "agent_type": "research|engineer|qa|documentation|security|ops|...",
  "metadata": {
    "name": "Research Agent",
    "description": "...",
    "version": "1.0.0",
    "author": "...",
    "tags": ["research", "analysis"]
  },
  "capabilities": {
    "model": "opus|sonnet|haiku",
    "tools": ["Read", "Grep", "Glob", "WebSearch", "mcp__*"],
    "resource_tier": "basic|standard|intensive|lightweight|high"
  },
  "interactions": {
    "triggers": ["keyword patterns for routing"],
    "handoff_agents": ["agent_ids this agent can delegate to"]
  }
}
```

---

## 2. PM Instruction Assembly

### Assembly Flow

```
ClaudeRunner.run()
    |
    v
_create_system_prompt()
    |
    v
section_generators/agents.py -> "Available Agent Capabilities"
    |
    v
PM_INSTRUCTIONS.md template
    |
    v
headless_session._inject_system_prompt() or interactive session
```

### Section Generator (agents.py)

Location: `src/claude_mpm/services/framework_claude_md_generator/section_generators/agents.py`

This generates the "Available Agent Capabilities" section by:
1. Loading all registered agents via unified_agent_registry
2. Extracting metadata (name, description, capabilities)
3. Building routing table from `interactions.triggers`
4. Formatting as markdown for PM instructions

### Routing Table Construction

Built from agent JSON fields:
- `interactions.triggers` - Keywords that route to this agent
- `interactions.handoff_agents` - Agents this one can delegate to
- `capabilities.model` - Model tier requirement
- `knowledge.routing.keywords` - Additional routing hints

---

## 3. Headless Model Usage

### Current State: NOT FUNCTIONAL FOR PROGRAMMATIC API

**headless_session.py** uses `os.execvpe()` to replace the process with Claude CLI:

```python
# Line 355 in headless_session.py
os.execvpe(cmd[0], cmd, env)  # Replaces process entirely
```

This is for CLI piping, NOT programmatic API calls.

**claude_provider.py** is Phase 1 mock only:

```python
# Lines 76-77, 229-266 show TODO Phase 2 comments
# TODO Phase 2: Initialize Anthropic SDK
# self._client = AsyncAnthropic(api_key=self.api_key)
```

### To Enable Programmatic Claude Calls

Option A: Complete ClaudeProvider Phase 2
```python
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key=api_key)
message = await client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
```

Option B: Use headless mode with stream-json output parsing
```bash
echo "prompt" | claude-mpm run --headless --output-format stream-json
```

Option C: Direct Anthropic SDK in new service (recommended for delegation matrix)

---

## 4. Agent Description Schema

### Schema Version 1.3.0 Structure

```json
{
  "schema_version": "1.3.0",
  "agent_id": "string (^[a-z][a-z0-9_-]*$)",
  "agent_version": "string (semver)",
  "agent_type": "enum",
  "metadata": {
    "name": "string",
    "description": "string",
    "version": "string",
    "author": "string",
    "tags": ["array"],
    "deprecated": "boolean",
    "replacement_agent": "string"
  },
  "capabilities": {
    "model": "opus|sonnet|haiku",
    "tools": ["array of tool names"],
    "resource_tier": "basic|standard|intensive|lightweight|high",
    "mcp_servers": ["array"],
    "allowed_commands": ["array"]
  },
  "instructions": {
    "role": "string",
    "guidelines": ["array"],
    "constraints": ["array"],
    "output_format": "string"
  },
  "knowledge": {
    "domain_expertise": ["array"],
    "best_practices": ["array"],
    "anti_patterns": ["array"],
    "routing": {
      "keywords": ["array for routing decisions"]
    }
  },
  "interactions": {
    "triggers": ["array of trigger patterns"],
    "handoff_agents": ["array of agent_ids"],
    "escalation_path": "string"
  },
  "triggers": {
    "file_patterns": ["array"],
    "commands": ["array"],
    "keywords": ["array"]
  }
}
```

### Agent Types (enum)

- base, engineer, qa, documentation, research
- security, ops, data_engineer, version_control
- system, refactoring, memory_manager

---

## 5. Recommendations for Dynamic Delegation Matrix

### Recommended Approach

Create a new service that:

1. **Loads all agents** via unified_agent_registry
2. **Extracts routing-relevant fields**:
   - `interactions.triggers`
   - `interactions.handoff_agents`
   - `knowledge.routing.keywords`
   - `capabilities.model`
3. **Calls Claude API directly** (not via headless mode) to generate matrix
4. **Caches result** to avoid repeated API calls

### Implementation Path

```python
# New file: src/claude_mpm/services/delegation/matrix_generator.py

from anthropic import AsyncAnthropic
from claude_mpm.core.unified_agent_registry import UnifiedAgentRegistry

class DelegationMatrixGenerator:
    def __init__(self):
        self.registry = UnifiedAgentRegistry()
        self.client = AsyncAnthropic()

    async def generate_matrix(self) -> dict:
        # 1. Load all agents
        agents = self.registry.get_all_agents()

        # 2. Extract routing info
        agent_summaries = [
            {
                "id": a.agent_id,
                "triggers": a.interactions.triggers,
                "handoffs": a.interactions.handoff_agents,
                "model": a.capabilities.model
            }
            for a in agents
        ]

        # 3. Call Claude to generate matrix
        prompt = f"Generate delegation matrix from: {agent_summaries}"
        response = await self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return parse_matrix(response.content[0].text)
```

### Required Changes

1. Add `anthropic` to dependencies (if not present)
2. Complete ClaudeProvider Phase 2 OR create dedicated service
3. Add caching layer (InstructionCacheService pattern)
4. Integrate with PM instruction assembly

---

## Appendix: Key Code Paths

| Component | File Path |
|-----------|-----------|
| Agent Registry | `src/claude_mpm/core/unified_agent_registry.py` |
| Agent Loader | `src/claude_mpm/agents/agent_loader.py` |
| Agent Schema | `src/claude_mpm/schemas/agent_schema.json` |
| PM Instructions | `src/claude_mpm/agents/PM_INSTRUCTIONS.md` |
| Section Generator | `src/claude_mpm/services/framework_claude_md_generator/section_generators/agents.py` |
| Headless Session | `src/claude_mpm/core/headless_session.py` |
| Claude Provider | `src/claude_mpm/services/model/claude_provider.py` |
| Base Agent | `src/claude_mpm/agents/base_agent.json` |
