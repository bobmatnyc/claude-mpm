# Schema Standardization Migration Guide

## Overview

Claude MPM v2.0.0 introduces a standardized agent schema format that significantly improves agent behavior predictability, validation, and resource management. This guide helps you migrate from the previous format to the new standardized schema.

## Breaking Changes

### 1. Agent ID Format Changes

**Old Format:**
```yaml
agent_type: research_agent
```

**New Format:**
```json
{
  "id": "research",  // No "_agent" suffix
  "agent_type": "research"
}
```

### 2. Complete Schema Structure

All agents must now follow the standardized JSON schema with required fields:

```json
{
  "id": "research",
  "version": "1.0.0",
  "metadata": {
    "name": "Research Agent",
    "description": "Conducts comprehensive technical investigation",
    "category": "research",
    "tags": ["research", "analysis", "codebase"]
  },
  "capabilities": {
    "model": "claude-4-sonnet-20250514",
    "tools": ["Read", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"],
    "resource_tier": "intensive"
  },
  "instructions": "Detailed agent instructions..."
}
```

### 3. Resource Tier System

Agents are now categorized into three resource tiers:

| Tier | Timeout | Memory | CPU | Use Cases |
|------|---------|---------|-----|-----------|
| **Lightweight** | 300s | 1024MB | 30% | version_control, documentation |
| **Standard** | 600s | 2048MB | 50% | qa, ops, security, data_engineer |
| **Intensive** | 900s | 3072MB | 70% | research, engineer |

### 4. Model Naming Standardization

Model names must use the standardized format:
- `claude-4-sonnet-20250514` (not `claude-sonnet-4-20250514`)
- `claude-4-opus-20250514`
- `claude-3-5-sonnet-20241022`

## Migration Steps

### Step 1: Update Agent References

Update all code that references agents to use the new ID format:

```python
# Old
agent = loader.get_agent("research_agent")

# New  
agent = loader.get_agent("research")
```

### Step 2: Convert Agent Definitions

If you have custom agents, convert them to the new format:

```python
# Example migration
old_agent = {
    "agent_type": "custom_agent",
    "configuration_fields": {
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.7,
        "tools": ["Read", "Write"]
    }
}

new_agent = {
    "id": "custom",
    "version": "1.0.0",
    "metadata": {
        "name": "Custom Agent",
        "description": "Your custom agent description",
        "category": "specialized",
        "tags": ["custom"]
    },
    "capabilities": {
        "model": "claude-4-sonnet-20250514",  # Standardized name
        "tools": ["Read", "Write"],
        "resource_tier": "standard"
    },
    "instructions": "Your agent instructions..."
}
```

### Step 3: Validate Agent Definitions

Use the validation framework to ensure your agents are compliant:

```python
from claude_mpm.validation import AgentValidator

validator = AgentValidator()
result = validator.validate_agent(your_agent_definition)

if not result.valid:
    print("Validation errors:", result.errors)
```

### Step 4: Update Integration Code

If you're using the agent system programmatically:

```python
# Old way
from claude_mpm.core import AgentLoader

loader = AgentLoader()
agent = loader.get_agent("research_agent")

# New way - backward compatibility maintained
agent = loader.get_agent("research")  # Clean ID
# or
agent = loader.get_agent("research_agent")  # Still works
```

## Backward Compatibility

The system maintains backward compatibility for:
- Agent ID references (both `research` and `research_agent` work)
- Programmatic access patterns
- Existing integration code

However, we strongly recommend updating to the new format for:
- Better validation
- Improved performance
- Access to new features
- Future compatibility

## Common Issues and Solutions

### Issue 1: Agent Not Found

**Symptom:** `AgentNotFoundError: Agent 'custom_agent' not found`

**Solution:** Remove the `_agent` suffix:
```python
# Change from
agent = loader.get_agent("custom_agent")
# To
agent = loader.get_agent("custom")
```

### Issue 2: Validation Errors

**Symptom:** Schema validation failures

**Solution:** Ensure all required fields are present:
```json
{
  "id": "your_agent",
  "version": "1.0.0",
  "metadata": { /* required fields */ },
  "capabilities": { /* required fields */ },
  "instructions": "Must be 100-8000 characters"
}
```

### Issue 3: Resource Constraints

**Symptom:** Agent timeout or memory errors

**Solution:** Choose appropriate resource tier:
- Use `intensive` for complex analysis tasks
- Use `standard` for normal operations  
- Use `lightweight` for simple tasks

## Benefits of Migration

1. **Predictable Behavior**: Standardized resource allocation ensures consistent performance
2. **Better Validation**: Comprehensive schema validation catches errors early
3. **Improved Performance**: Resource tiers optimize allocation
4. **Enhanced Maintainability**: Clear structure makes agents easier to understand and modify
5. **Future Features**: New features will require the standardized format

## Support

For migration assistance:
- Check the [API Documentation](../04-reference/api-reference.md)
- Review [example agents](https://github.com/bobmatnyc/claude-mpm/tree/main/src/claude_mpm/agents)
- Submit issues on [GitHub](https://github.com/bobmatnyc/claude-mpm/issues)

## Next Steps

After migration:
1. Run validation tests on all agents
2. Update any custom integration code
3. Review agent performance with new resource tiers
4. Explore new schema features like knowledge bases and testing configurations