# Agent Capabilities Format Documentation

## Overview

The agent capabilities discovery system now provides both the agent name (for TodoWrite) and agent_id (for Task tool) to ensure the PM can properly delegate work.

## Format Structure

Agent capabilities are displayed in the format:
```
- **Agent Name** (`agent_id`): Description
```

Where:
- **Agent Name**: Human-readable name used for TodoWrite task prefixes (e.g., "Engineer", "Research", "QA")
- **`agent_id`**: Technical identifier used with the Task tool for delegation (e.g., `engineer`, `research`, `qa`)
- **Description**: Brief explanation of the agent's capabilities

## Example Usage

### In TodoWrite (uses Agent Name):
```json
{
  "todos": [
    {"id": "1", "content": "[Research] Analyze codebase architecture", "status": "pending"},
    {"id": "2", "content": "[Engineer] Implement authentication system", "status": "pending"},
    {"id": "3", "content": "[QA] Test authentication flows", "status": "pending"}
  ]
}
```

### In Task Tool (uses agent_id):
```json
{
  "subagent_type": "research",
  "prompt": "Analyze the codebase architecture and identify key patterns",
  "description": "Codebase analysis"
}
```

## Implementation Details

### 1. Framework Loader (`framework_loader.py`)
- Reads deployed agents from `.claude/agents/`
- Extracts metadata from YAML frontmatter
- Formats agent capabilities with both name and ID
- Groups agents into Engineering and Research categories

### 2. AgentCapabilitiesGenerator (`agent_capabilities_generator.py`)
- Processes agent metadata from discovery service
- Cleans agent names (removes "Agent" suffix, normalizes formatting)
- Generates structured markdown with clear formatting
- Groups by agent tier (project, user, system)

### 3. DeployedAgentDiscovery (`deployed_agent_discovery.py`)
- Discovers agents following Claude Code's hierarchy
- Respects precedence: PROJECT > USER > SYSTEM
- Provides complete agent metadata including name, ID, and description

## Categories

Agents are grouped into two main categories:

### Engineering Agents
- `engineer` - Code implementation
- `data_engineer` - Data pipelines and ETL
- `documentation` - Technical documentation
- `ops` - Infrastructure and deployment
- `security` - Security analysis
- `ticketing` - Issue management
- `version_control` - Git operations
- `web_ui` - Front-end development

### Research Agents
- `research` - Codebase analysis
- `code_analyzer` - Advanced code analysis
- `qa` - Testing and quality assurance
- `web_qa` - Web application testing

## Benefits

1. **Clear Separation**: Agent names for human-readable tasks, IDs for technical delegation
2. **Consistency**: TodoWrite tasks use consistent naming conventions
3. **Flexibility**: PM can use appropriate format for each context
4. **Discovery**: Dynamic discovery ensures PM always knows available agents
5. **Documentation**: Clear format helps users understand agent usage

## Testing

Run the test script to verify capabilities generation:
```bash
python scripts/test_capabilities_update.py
```

This validates:
- Agent discovery finds deployed agents
- Capabilities generator formats correctly
- Framework loader includes both formats
- All sections are properly generated