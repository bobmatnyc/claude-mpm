# Agent Schema API Reference

## Overview

The Claude MPM Agent Schema provides a standardized format for defining agent capabilities, behaviors, and resource requirements. This document details the schema structure and validation API.

## Schema Location

The canonical schema definition is located at:
```
src/claude_mpm/schemas/agent_schema.json
```

## Schema Structure

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique agent identifier (lowercase, alphanumeric with underscores) |
| `version` | string | Yes | Agent version in semantic format (e.g., "1.0.0") |
| `metadata` | object | Yes | Agent metadata including name, description, and tags |
| `capabilities` | object | Yes | Agent capabilities configuration |
| `instructions` | string | Yes | Detailed agent instructions (100-8000 characters) |
| `knowledge` | object | No | Agent-specific knowledge and context |
| `interactions` | object | No | Agent interaction patterns |
| `testing` | object | No | Testing configuration |
| `hooks` | object | No | Hook configurations |

### Metadata Object

```json
{
  "metadata": {
    "name": "Research Agent",
    "description": "Conducts comprehensive technical investigation",
    "category": "research",
    "tags": ["research", "analysis"],
    "author": "Claude MPM Team",
    "created_at": "2025-07-26T00:00:00Z",
    "updated_at": "2025-07-26T00:00:00Z"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Human-readable agent name (3-50 characters) |
| `description` | string | Yes | Brief description (10-200 characters) |
| `category` | enum | Yes | One of: engineering, research, quality, operations, specialized |
| `tags` | array | Yes | Array of lowercase tags (1-10 items) |
| `author` | string | No | Agent template author |
| `created_at` | datetime | No | ISO 8601 creation timestamp |
| `updated_at` | datetime | No | ISO 8601 last update timestamp |

### Capabilities Object

```json
{
  "capabilities": {
    "model": "claude-4-sonnet-20250514",
    "tools": ["Read", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"],
    "resource_tier": "intensive",
    "max_tokens": 8192,
    "temperature": 0.7,
    "timeout": 300,
    "memory_limit": 2048,
    "cpu_limit": 50,
    "network_access": true,
    "file_access": {
      "read_paths": ["/project"],
      "write_paths": ["/project/output"]
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | enum | Yes | Claude model identifier |
| `tools` | array | Yes | Available tools for the agent |
| `resource_tier` | enum | Yes | One of: intensive, standard, lightweight |
| `max_tokens` | integer | No | Maximum response tokens (default: 8192) |
| `temperature` | number | No | Model temperature 0-1 (default: 0.7) |
| `timeout` | integer | No | Operation timeout in seconds (default: 300) |
| `memory_limit` | integer | No | Memory limit in MB |
| `cpu_limit` | integer | No | CPU limit percentage (10-100) |
| `network_access` | boolean | No | Network access permission (default: false) |
| `file_access` | object | No | File access configuration |

### Available Tools

| Tool | Description |
|------|-------------|
| `Read` | Read file contents |
| `Write` | Write file contents |
| `Edit` | Edit specific file sections |
| `MultiEdit` | Multiple edits in one operation |
| `Grep` | Search file contents |
| `Glob` | Find files by pattern |
| `LS` | List directory contents |
| `Bash` | Execute shell commands |
| `WebSearch` | Search the web |
| `WebFetch` | Fetch web content |
| `NotebookRead` | Read Jupyter notebooks |
| `NotebookEdit` | Edit Jupyter notebooks |
| `TodoWrite` | Manage task lists |
| `ExitPlanMode` | Exit planning mode |

### Resource Tiers

| Tier | Timeout | Memory | CPU | Description |
|------|---------|--------|-----|-------------|
| `intensive` | 900s | 3072MB | 70% | Complex analysis and implementation |
| `standard` | 600s | 2048MB | 50% | Normal operations |
| `lightweight` | 300s | 1024MB | 30% | Simple, fast operations |

## Validation API

### AgentValidator Class

```python
from claude_mpm.validation import AgentValidator

# Initialize validator
validator = AgentValidator()

# Validate an agent definition
result = validator.validate_agent(agent_dict)

# Check results
if result.valid:
    print("Agent is valid!")
else:
    print("Errors:", result.errors)
    print("Warnings:", result.warnings)
```

### ValidationResult Object

```python
class ValidationResult:
    valid: bool           # True if agent passes all validations
    errors: List[str]     # List of validation errors
    warnings: List[str]   # List of validation warnings
    agent_id: str         # ID of validated agent
```

### Validation Types

1. **Schema Validation**: Ensures JSON structure matches schema
2. **Business Rule Validation**: Checks logical consistency
3. **Resource Tier Validation**: Ensures resource allocations match tier
4. **Tool Assignment Validation**: Verifies appropriate tools for agent type

### Example Validation

```python
# Example agent definition
agent = {
    "id": "custom",
    "version": "1.0.0",
    "metadata": {
        "name": "Custom Agent",
        "description": "A custom agent for specific tasks",
        "category": "specialized",
        "tags": ["custom", "specialized"]
    },
    "capabilities": {
        "model": "claude-4-sonnet-20250514",
        "tools": ["Read", "Write", "Edit"],
        "resource_tier": "standard"
    },
    "instructions": "Detailed instructions for the custom agent..."
}

# Validate
validator = AgentValidator()
result = validator.validate_agent(agent)

if not result.valid:
    for error in result.errors:
        print(f"ERROR: {error}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
```

## Agent Loader API

### Loading Agents

```python
from claude_mpm.core import AgentLoader

# Initialize loader
loader = AgentLoader()

# List all agents
agents = loader.list_agents()
for agent in agents:
    print(f"{agent['id']}: {agent['metadata']['name']}")

# Get specific agent
research_agent = loader.get_agent("research")
print(research_agent['metadata']['description'])

# Get agent prompt
prompt = loader.get_prompt("research")
print(prompt)
```

### Backward Compatibility

The loader maintains backward compatibility with old agent IDs:

```python
# Both work
agent1 = loader.get_agent("research")
agent2 = loader.get_agent("research_agent")  # Legacy support
assert agent1 == agent2
```

## Creating Custom Agents

### Step 1: Define Agent Structure

```python
custom_agent = {
    "id": "my_custom_agent",
    "version": "1.0.0",
    "metadata": {
        "name": "My Custom Agent",
        "description": "Handles specialized custom tasks",
        "category": "specialized",
        "tags": ["custom", "specialized"]
    },
    "capabilities": {
        "model": "claude-4-sonnet-20250514",
        "tools": ["Read", "Write", "Edit", "Grep"],
        "resource_tier": "standard",
        "temperature": 0.3,
        "max_tokens": 8192
    },
    "instructions": """
# My Custom Agent

You are a specialized agent for handling custom tasks.

## Core Responsibilities
- Task 1: Description
- Task 2: Description
- Task 3: Description

## Guidelines
Follow these guidelines when performing tasks...
"""
}
```

### Step 2: Validate Agent

```python
validator = AgentValidator()
result = validator.validate_agent(custom_agent)

if not result.valid:
    raise ValueError(f"Invalid agent: {result.errors}")
```

### Step 3: Save Agent

```python
import json

# Save to agents directory
agent_path = "src/claude_mpm/agents/my_custom_agent.json"
with open(agent_path, 'w') as f:
    json.dump(custom_agent, f, indent=2)
```

## Best Practices

1. **Choose Appropriate Resource Tiers**
   - Use `intensive` only for complex analysis/implementation
   - Default to `standard` for most use cases
   - Use `lightweight` for simple, fast operations

2. **Tool Selection**
   - Only include tools the agent actually needs
   - Consider security implications of tool access
   - Follow the principle of least privilege

3. **Clear Instructions**
   - Keep instructions focused and specific
   - Include examples when helpful
   - Stay within the 8000 character limit

4. **Semantic Versioning**
   - Use proper semantic versioning (MAJOR.MINOR.PATCH)
   - Increment MAJOR for breaking changes
   - Increment MINOR for new features
   - Increment PATCH for bug fixes

5. **Metadata Quality**
   - Use descriptive names and descriptions
   - Choose accurate categories
   - Add relevant tags for discoverability

## Error Handling

```python
from claude_mpm.core import AgentLoader
from claude_mpm.exceptions import AgentNotFoundError, ValidationError

loader = AgentLoader()

try:
    agent = loader.get_agent("nonexistent")
except AgentNotFoundError as e:
    print(f"Agent not found: {e}")

try:
    # Invalid agent definition
    invalid_agent = {"id": "bad"}  # Missing required fields
    validator.validate_agent(invalid_agent)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Migration Support

For migrating from old format to new:

```python
from claude_mpm.migration import migrate_agent

# Old format agent
old_agent = {
    "agent_type": "custom_agent",
    "configuration_fields": {...}
}

# Migrate to new format
new_agent = migrate_agent(old_agent)

# Validate migrated agent
result = validator.validate_agent(new_agent)
```