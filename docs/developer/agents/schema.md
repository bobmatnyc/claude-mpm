# Agent Schema Documentation

This document provides comprehensive documentation for agent schemas in Claude MPM, covering both the legacy v1.1.0 schema and the current v1.2.0 schema, including migration guidance and validation requirements.

## Table of Contents

1. [Overview](#overview)
2. [Schema Versions](#schema-versions)
3. [v1.1.0 Legacy Schema](#v110-legacy-schema)
4. [v1.2.0 Current Schema](#v120-current-schema)
5. [Schema Differences](#schema-differences)
6. [Migration Guide](#migration-guide)
7. [Validation Requirements](#validation-requirements)
8. [Schema Evolution](#schema-evolution)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Overview

Claude MPM uses JSON Schema to validate agent configurations and ensure consistency across the system. The schema has evolved through multiple versions to support new features and improve validation coverage.

### Current Status

- **Current Schema**: v1.2.0 (primary)
- **Legacy Schema**: v1.1.0 (backward compatible)
- **Validation**: Draft-07 JSON Schema specification
- **Location**: `src/claude_mpm/schemas/agent_schema.json` (v1.2.0), `src/claude_mpm/agents/schema/agent_schema.json` (v1.1.0)

### Key Features

- **Strict Validation**: Prevents malformed agent configurations
- **Security Controls**: Resource limits and capability restrictions
- **Backward Compatibility**: Legacy format support with migration path
- **Extensibility**: Optional fields for advanced features

## Schema Versions

### Version History

| Version | Release Date | Status | Key Features |
|---------|-------------|--------|--------------|
| v1.1.0 | Early 2024 | Legacy | Basic agent structure, flexible validation |
| v1.2.0 | Current | Active | Enhanced security, stricter validation, extended metadata |

### Version Detection

The schema version is determined by:

1. **Explicit Declaration**: `schema_version` field in agent configuration
2. **Content Analysis**: Field structure and validation patterns
3. **Fallback Behavior**: Defaults to v1.1.0 for backward compatibility

```json
{
  "schema_version": "1.2.0",
  "agent_id": "example_agent",
  // ... rest of configuration
}
```

## v1.1.0 Legacy Schema

The legacy schema provides foundational agent structure with flexible validation.

### Required Fields

```json
{
  "schema_version": "1.1.0",
  "agent_id": "string (pattern: ^[a-z0-9_]+$)",
  "agent_version": "string (pattern: ^\\d+\\.\\d+\\.\\d+$)",
  "agent_type": "enum: base|engineer|qa|documentation|research|security|ops|data_engineer|version_control",
  "metadata": {
    "name": "string",
    "description": "string", 
    "tags": ["string", ...],
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  },
  "capabilities": {
    // Flexible structure with additionalProperties: true
  },
  "instructions": "string"
}
```

### Capabilities Structure (v1.1.0)

```json
{
  "capabilities": {
    "model": "string",
    "tools": ["string", ...],
    "resource_tier": "enum: basic|standard|intensive|lightweight",
    "max_tokens": "integer (minimum: 1)",
    "temperature": "number (0-1)",
    "timeout": "integer (minimum: 1)",
    "memory_limit": "integer (minimum: 1)",
    "cpu_limit": "integer (1-100)",
    "network_access": "boolean",
    "file_access": {
      "read_paths": ["string", ...],
      "write_paths": ["string", ...]
    },
    "when_to_use": ["string", ...],
    "specialized_knowledge": ["string", ...],
    "unique_capabilities": ["string", ...]
  }
}
```

### Optional Fields (v1.1.0)

- **`configuration`**: Alternative configuration structure
- **`knowledge`**: Domain expertise and constraints
- **`interactions`**: Input/output formats and triggers
- **`testing`**: Test cases and performance benchmarks

### Key Characteristics

- **Flexible Validation**: `additionalProperties: true` allows custom fields
- **Basic Security**: Limited resource constraint validation
- **Minimal Requirements**: Focus on core functionality
- **Legacy Support**: Maintained for backward compatibility

## v1.2.0 Current Schema

The current schema provides enhanced validation, security controls, and extended functionality.

### Required Fields

```json
{
  "schema_version": "1.2.0",
  "agent_id": "string (pattern: ^[a-z][a-z0-9_]*$)",
  "agent_version": "string (pattern: ^\\d+\\.\\d+\\.\\d+$)",
  "agent_type": "enum: base|engineer|qa|documentation|research|security|ops|data_engineer|version_control",
  "metadata": {
    "name": "string (3-50 chars)",
    "description": "string (10-200 chars)",
    "tags": ["string (pattern: ^[a-z][a-z0-9-]*$)", ...] // 1-10 items, unique
  },
  "capabilities": {
    "model": "enum: claude-3-haiku-20240307|claude-3-5-haiku-20241022|...",
    "tools": ["enum: Read|Write|Edit|...", ...] // unique items,
    "resource_tier": "enum: basic|standard|intensive|lightweight"
  },
  "instructions": "string (100-8000 chars)"
}
```

### Enhanced Capabilities (v1.2.0)

```json
{
  "capabilities": {
    "model": "enum: [specific Claude model identifiers]",
    "tools": ["enum: [specific tool names]"],
    "resource_tier": "enum: basic|standard|intensive|lightweight",
    "max_tokens": "integer (1000-200000, default: 8192)",
    "temperature": "number (0-1, default: 0.7)",
    "timeout": "integer (30-3600, default: 300)",
    "memory_limit": "integer (512-8192)",
    "cpu_limit": "integer (10-100)",
    "network_access": "boolean (default: false)",
    "file_access": {
      "read_paths": ["string", ...],
      "write_paths": ["string", ...]
    },
    "allowed_tools": ["string", ...],
    "disallowed_tools": ["string", ...]
  }
}
```

### Extended Metadata (v1.2.0)

```json
{
  "metadata": {
    "name": "string (required, 3-50 chars)",
    "description": "string (required, 10-200 chars)",
    "category": "enum: engineering|research|quality|operations|specialized",
    "tags": ["string", ...], // Required, 1-10 items, unique, pattern validated
    "author": "string",
    "created_at": "string (date-time format)",
    "updated_at": "string (date-time format)"
  }
}
```

### Security Enhancements

- **Strict Model Validation**: Only approved Claude models allowed
- **Tool Whitelist**: Explicit tool enumeration with validation
- **Resource Limits**: Enforced minimum/maximum values
- **Character Limits**: Prevent resource exhaustion attacks
- **Pattern Validation**: Strict naming conventions
- **No Additional Properties**: `additionalProperties: false` prevents injection

## Schema Differences

### Field Changes

| Field | v1.1.0 | v1.2.0 | Change Type |
|-------|--------|--------|-------------|
| `agent_id` | `^[a-z0-9_]+$` | `^[a-z][a-z0-9_]*$` | Pattern stricter |
| `metadata.tags` | Optional | Required | Now required |
| `metadata.category` | Not present | Optional enum | New field |
| `capabilities.model` | Free string | Strict enum | Security enhancement |
| `capabilities.tools` | Free array | Enum array | Security enhancement |
| `instructions` | Any length | 100-8000 chars | Length limits |
| `additionalProperties` | `true` | `false` | Stricter validation |

### Resource Validation

| Resource | v1.1.0 | v1.2.0 | Enhancement |
|----------|--------|--------|-------------|
| `max_tokens` | Min: 1 | Range: 1000-200000 | Realistic bounds |
| `timeout` | Min: 1 | Range: 30-3600 | Practical limits |
| `memory_limit` | Min: 1 | Range: 512-8192 | Resource tiers |
| `cpu_limit` | Range: 1-100 | Range: 10-100 | Minimum enforcement |

### Security Improvements

1. **Model Restrictions**: Only approved Claude models
2. **Tool Validation**: Whitelist-based tool approval
3. **Resource Bounds**: Prevent DoS through resource exhaustion
4. **Input Validation**: Character limits on all text fields
5. **Pattern Enforcement**: Strict naming conventions
6. **Injection Prevention**: No arbitrary properties allowed

## Migration Guide

### Automatic Migration

The system automatically handles v1.1.0 to v1.2.0 migration:

```python
from claude_mpm.validation.migration import migrate_agent_format

# Migrate legacy agent to current schema
old_agent = load_v11_agent("legacy_agent.json")
new_agent = migrate_agent_format(old_agent, target_version="1.2.0")
```

### Manual Migration Steps

#### 1. Update Schema Version

```json
// Before (v1.1.0)
{
  "schema_version": "1.1.0",
  // ...
}

// After (v1.2.0)
{
  "schema_version": "1.2.0",
  // ...
}
```

#### 2. Fix Agent ID Pattern

```json
// Before - may start with number
{
  "agent_id": "2nd_engineer"
}

// After - must start with letter
{
  "agent_id": "second_engineer"
}
```

#### 3. Add Required Tags

```json
// Before - tags optional
{
  "metadata": {
    "name": "Engineer Agent",
    "description": "Software engineering assistant"
    // tags missing
  }
}

// After - tags required
{
  "metadata": {
    "name": "Engineer Agent",
    "description": "Software engineering assistant",
    "tags": ["engineering", "software", "development"]
  }
}
```

#### 4. Update Model Specification

```json
// Before - free string
{
  "capabilities": {
    "model": "claude-3-sonnet"
  }
}

// After - specific identifier
{
  "capabilities": {
    "model": "claude-3-5-sonnet-20241022"
  }
}
```

#### 5. Validate Tool Names

```json
// Before - custom tools allowed
{
  "capabilities": {
    "tools": ["file_reader", "shell", "custom_tool"]
  }
}

// After - only approved tools
{
  "capabilities": {
    "tools": ["Read", "Bash"]
    // custom_tool removed - not in whitelist
  }
}
```

#### 6. Add Instruction Length Limits

```json
// Before - any length
{
  "instructions": "Brief instruction"
}

// After - minimum 100 characters
{
  "instructions": "Comprehensive instruction set with detailed guidelines for agent behavior, including specific examples and use cases to meet the minimum character requirement..."
}
```

### Migration Validation

After migration, validate the result:

```python
from claude_mpm.validation.agent_validator import AgentValidator

validator = AgentValidator()
result = validator.validate_agent(migrated_agent)

if result.is_valid:
    print("Migration successful")
else:
    print(f"Migration errors: {result.errors}")
    print(f"Migration warnings: {result.warnings}")
```

## Validation Requirements

### JSON Schema Validation

All agents must pass JSON Schema validation:

```python
import jsonschema
from claude_mpm.validation.agent_validator import AgentValidator

validator = AgentValidator()
result = validator.validate_agent(agent_config)

# Check validation result
if not result.is_valid:
    for error in result.errors:
        print(f"Validation error: {error}")
```

### Business Rule Validation

Beyond schema validation, agents undergo business rule validation:

#### Resource Tier Consistency

```python
# Resource limits must align with declared tier
{
  "capabilities": {
    "resource_tier": "lightweight",
    "memory_limit": 1024,  # Must be 512-2048 for lightweight
    "cpu_limit": 20,       # Must be 10-30 for lightweight
    "timeout": 300         # Must be 30-600 for lightweight
  }
}
```

#### Tool Compatibility

```python
# Network tools require network access
{
  "capabilities": {
    "tools": ["WebSearch"],
    "network_access": true  # Required for network tools
  }
}
```

#### Security Constraints

```python
# Dangerous tool combinations flagged
{
  "capabilities": {
    "tools": ["Bash", "Write"]  # Can write and execute scripts
  }
  // Generates security warning
}
```

### Custom Validation Rules

Projects can implement custom validation:

```python
class CustomAgentValidator(AgentValidator):
    def _validate_business_rules(self, agent_data, result):
        super()._validate_business_rules(agent_data, result)
        
        # Custom project rules
        if agent_data.get("agent_type") == "engineer":
            tools = agent_data.get("capabilities", {}).get("tools", [])
            if "git" not in tools:
                result.warnings.append("Engineer agents should include git tool")
```

## Schema Evolution

### Version Lifecycle

1. **Development**: New features and validations added
2. **Testing**: Comprehensive validation with existing agents
3. **Release**: New schema version published
4. **Migration**: Tools provided for upgrading
5. **Deprecation**: Old versions marked as legacy
6. **Removal**: Legacy support eventually removed

### Future Enhancements

Planned improvements for future schema versions:

#### v1.3.0 (Planned)

- **Enhanced Security**: Additional security constraints and validation
- **Performance Metrics**: Built-in performance monitoring fields
- **Dependency Management**: Agent dependency specifications
- **Environment Constraints**: Platform-specific requirements

#### Breaking Changes Policy

- **Major Version**: Breaking changes (e.g., v2.0.0)
- **Minor Version**: New optional fields (e.g., v1.3.0)
- **Patch Version**: Bug fixes and clarifications (e.g., v1.2.1)

### Backward Compatibility

- **Migration Tools**: Automated upgrade utilities
- **Validation Support**: Legacy format validation maintained
- **Documentation**: Clear migration guides provided
- **Deprecation Warnings**: Advanced notice of changes

## Best Practices

### Schema Compliance

1. **Use Latest Schema**: Always target the current schema version
2. **Validate Early**: Run validation during development
3. **Test Migration**: Verify agent behavior after schema updates
4. **Monitor Warnings**: Address validation warnings promptly

### Security Considerations

1. **Principle of Least Privilege**: Only grant necessary capabilities
2. **Resource Limits**: Set appropriate resource constraints
3. **Tool Restrictions**: Use minimal required tool set
4. **Network Access**: Enable only when necessary

### Performance Optimization

1. **Resource Tiers**: Choose appropriate tier for workload
2. **Token Limits**: Set realistic token limits
3. **Timeout Values**: Balance responsiveness with completion
4. **Model Selection**: Match model to task complexity

### Maintenance

1. **Version Tracking**: Keep agent versions up to date
2. **Schema Updates**: Regularly update to latest schema
3. **Validation Integration**: Include validation in CI/CD
4. **Documentation**: Document custom validation rules

## Troubleshooting

### Common Validation Errors

#### Schema Version Mismatch

**Error**: `"Unsupported schema version: 2.0.0"`

**Solution**: Use supported schema version (1.1.0 or 1.2.0)

```json
{
  "schema_version": "1.2.0"  // Use current version
}
```

#### Invalid Agent ID Pattern

**Error**: `"Agent ID must start with letter: 2nd_engineer"`

**Solution**: Ensure agent ID starts with lowercase letter

```json
{
  "agent_id": "second_engineer"  // Fixed pattern
}
```

#### Missing Required Fields

**Error**: `"Missing required field: metadata.tags"`

**Solution**: Add all required fields

```json
{
  "metadata": {
    "name": "Agent Name",
    "description": "Agent description",
    "tags": ["required", "tag"]  // Add missing tags
  }
}
```

#### Resource Limit Violations

**Error**: `"Memory limit 512MB outside recommended range 2048-4096MB for tier 'standard'"`

**Solution**: Align resource limits with tier or change tier

```json
{
  "capabilities": {
    "resource_tier": "lightweight",  // Change tier
    "memory_limit": 512              // Or adjust limit
  }
}
```

### Debugging Tools

#### Schema Validation

```bash
# Validate specific agent file
python -c "
from claude_mpm.validation.agent_validator import validate_agent_file
from pathlib import Path
result = validate_agent_file(Path('agent.json'))
print(f'Valid: {result.is_valid}')
if not result.is_valid:
    for error in result.errors:
        print(f'Error: {error}')
"
```

#### Migration Testing

```bash
# Test migration from v1.1.0 to v1.2.0
python -c "
from claude_mpm.validation.migration import migrate_agent_format
result = migrate_agent_format('old_agent.json', 'new_agent.json')
print(f'Migration successful: {result.success}')
"
```

#### Bulk Validation

```bash
# Validate all agents in directory
python -c "
from claude_mpm.validation.agent_validator import validate_all_agents
from pathlib import Path
valid, invalid, errors = validate_all_agents(Path('.claude-mpm/agents'))
print(f'Valid: {valid}, Invalid: {invalid}')
for error in errors:
    print(f'Error: {error}')
"
```

This comprehensive schema documentation provides the foundation for understanding, migrating, and troubleshooting agent configurations in Claude MPM.