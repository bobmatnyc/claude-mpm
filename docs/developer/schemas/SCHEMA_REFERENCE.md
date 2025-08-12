# Schema Reference Documentation

> **Navigation**: [Developer Guide](../README.md) → [Schemas](./README.md) → **Schema Reference**

## Overview

Claude MPM uses JSON schemas to define and validate agent configurations, ensuring consistency and type safety across the system.

## Table of Contents

1. [Agent Schema](#agent-schema)
2. [Frontmatter Schema](#frontmatter-schema)
3. [Schema Validation](#schema-validation)
4. [Schema Evolution](#schema-evolution)
5. [Best Practices](#best-practices)

## Agent Schema

### Current Version: 1.2.0

Location: `/src/claude_mpm/schemas/agent_schema.json`

### Schema Structure

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Claude MPM Agent Configuration Schema",
  "type": "object",
  "required": [
    "schema_version",
    "agent_id",
    "agent_version",
    "agent_type",
    "metadata",
    "capabilities",
    "instructions"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Version of the schema format"
    },
    "agent_id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*$",
      "description": "Unique identifier for the agent"
    },
    "agent_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Version of the agent template"
    },
    "agent_type": {
      "type": "string",
      "enum": [
        "base", "engineer", "qa", "documentation",
        "research", "security", "ops", "data_engineer",
        "version_control"
      ]
    },
    "metadata": {
      "type": "object",
      "required": ["name", "description", "tags"],
      "properties": {
        "name": {
          "type": "string",
          "minLength": 3,
          "maxLength": 50
        },
        "description": {
          "type": "string",
          "minLength": 10,
          "maxLength": 200
        },
        "tags": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[a-z][a-z0-9-]*$"
          }
        }
      }
    },
    "capabilities": {
      "type": "object",
      "required": ["model", "tools", "resource_tier"],
      "properties": {
        "model": {
          "type": "string",
          "enum": [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-haiku-4-20250514"
          ]
        },
        "tools": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "resource_tier": {
          "type": "string",
          "enum": ["intensive", "standard", "lightweight"]
        },
        "max_tokens": {
          "type": "integer",
          "minimum": 1000,
          "maximum": 200000
        },
        "temperature": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "file_access": {
          "type": "object",
          "properties": {
            "read_paths": {
              "type": "array",
              "items": {"type": "string"}
            },
            "write_paths": {
              "type": "array",
              "items": {"type": "string"}
            },
            "blocked_paths": {
              "type": "array",
              "items": {"type": "string"}
            }
          }
        }
      }
    },
    "instructions": {
      "type": "string",
      "minLength": 100,
      "maxLength": 8000
    }
  }
}
```

## Frontmatter Schema

### For Markdown Agent Files

Location: `/src/claude_mpm/schemas/frontmatter_schema.json`

```yaml
---
# Required fields
description: string (10-200 chars)
version: string (semantic version X.Y.Z)

# Capability fields
tools: array of strings
model: string (Claude model identifier)
resource_tier: enum [intensive, standard, lightweight]
max_tokens: integer (1000-200000)
temperature: number (0-1)

# Optional metadata
tags: array of strings
author: string
created_at: ISO 8601 timestamp
updated_at: ISO 8601 timestamp

# File access control
file_access:
  read_paths: array of path patterns
  write_paths: array of path patterns
  blocked_paths: array of path patterns
---
```

### Frontmatter Validation Rules

1. **Version Format**: Must match `^\d+\.\d+\.\d+$`
2. **Description Length**: 10-200 characters
3. **Tools**: Must be valid tool names
4. **Model**: Must be a valid Claude model
5. **Tags**: Lowercase with hyphens only

## Schema Validation

### Python Validation

```python
from jsonschema import validate, ValidationError
import json

def validate_agent_config(config: dict) -> tuple[bool, list[str]]:
    """
    Validate agent configuration against schema.
    """
    # Load schema
    with open('src/claude_mpm/schemas/agent_schema.json') as f:
        schema = json.load(f)
    
    errors = []
    try:
        validate(instance=config, schema=schema)
        return True, []
    except ValidationError as e:
        errors.append(str(e.message))
        
        # Collect all validation errors
        for error in e.context:
            errors.append(f"{error.path}: {error.message}")
        
        return False, errors
```

### CLI Validation

```bash
# Validate single agent
python scripts/validate_agent_configuration.py agent.json

# Validate all agents
python scripts/validate_agent_configuration.py --all

# Validate frontmatter
python scripts/validate_agent_frontmatter.py agent.md
```

### Validation Process Flow

```
┌─────────────────┐
│  Agent File     │
│ (.md/.json/.yml)│
└───────┬────────┘
        │
        ▼
┌─────────────────┐
│  Format Parser  │
└───────┬────────┘
        │
        ▼
┌─────────────────┐
│ Schema Validator│
└───────┬────────┘
        │
    ┌───┼───┐
    ▼       ▼
┌───────┐ ┌───────┐
│ Valid │ │Invalid│
└───────┘ └───────┘
```

## Schema Evolution

### Version History

- **1.0.0** - Initial schema release
- **1.1.0** - Added file_access configuration
- **1.2.0** - Enhanced validation patterns, added resource tiers

### Migration Guide

#### From 1.0.0 to 1.1.0

```python
def migrate_1_0_to_1_1(config: dict) -> dict:
    """
    Migrate from schema 1.0.0 to 1.1.0.
    """
    # Add default file_access if not present
    if 'capabilities' in config:
        if 'file_access' not in config['capabilities']:
            config['capabilities']['file_access'] = {
                'read_paths': ['*'],
                'write_paths': ['.'],
                'blocked_paths': []
            }
    
    # Update schema version
    config['schema_version'] = '1.1.0'
    
    return config
```

#### From 1.1.0 to 1.2.0

```python
def migrate_1_1_to_1_2(config: dict) -> dict:
    """
    Migrate from schema 1.1.0 to 1.2.0.
    """
    # Convert resource_limits to resource_tier
    if 'capabilities' in config:
        if 'resource_limits' in config['capabilities']:
            limits = config['capabilities']['resource_limits']
            
            # Determine tier based on limits
            memory = limits.get('memory_limit', 2048)
            if memory >= 4096:
                tier = 'intensive'
            elif memory >= 2048:
                tier = 'standard'
            else:
                tier = 'lightweight'
            
            config['capabilities']['resource_tier'] = tier
            del config['capabilities']['resource_limits']
    
    # Update schema version
    config['schema_version'] = '1.2.0'
    
    return config
```

### Backward Compatibility

```python
class SchemaCompatibilityManager:
    """
    Handle schema version compatibility.
    """
    
    COMPATIBLE_VERSIONS = {
        '1.2.0': ['1.1.0', '1.0.0'],
        '1.1.0': ['1.0.0'],
        '1.0.0': []
    }
    
    @classmethod
    def is_compatible(cls, schema_version: str, config_version: str) -> bool:
        """
        Check if config version is compatible with schema version.
        """
        if schema_version == config_version:
            return True
        
        compatible = cls.COMPATIBLE_VERSIONS.get(schema_version, [])
        return config_version in compatible
    
    @classmethod
    def auto_migrate(cls, config: dict, target_version: str) -> dict:
        """
        Automatically migrate config to target version.
        """
        current_version = config.get('schema_version', '1.0.0')
        
        if current_version == target_version:
            return config
        
        # Apply migrations in sequence
        migrations = [
            ('1.0.0', '1.1.0', migrate_1_0_to_1_1),
            ('1.1.0', '1.2.0', migrate_1_1_to_1_2),
        ]
        
        for from_v, to_v, migrate_func in migrations:
            if current_version == from_v:
                config = migrate_func(config)
                current_version = to_v
                
                if current_version == target_version:
                    break
        
        return config
```

## Best Practices

### 1. Schema Design

- Use semantic versioning for schema versions
- Make backward-compatible changes when possible
- Document breaking changes clearly
- Provide migration tools for major version changes

### 2. Validation

- Validate early and often
- Provide clear error messages
- Include examples of valid configurations
- Test edge cases thoroughly

### 3. Field Definitions

```json
{
  "field_name": {
    "type": "string",
    "description": "Clear description of the field's purpose",
    "examples": ["example1", "example2"],
    "default": "default_value",
    "pattern": "^[a-z]+$",
    "minLength": 1,
    "maxLength": 100
  }
}
```

### 4. Required vs Optional

- Keep required fields minimal
- Provide sensible defaults for optional fields
- Document when fields become required
- Consider feature flags for new required fields

### 5. Enum Values

```json
{
  "agent_type": {
    "type": "string",
    "enum": [
      "base",
      "engineer",
      "qa"
    ],
    "enumDescriptions": {
      "base": "Generic agent with no specialization",
      "engineer": "Code implementation and development",
      "qa": "Quality assurance and testing"
    }
  }
}
```

## Common Validation Errors

### Pattern Mismatches

```
Error: 'Test_Agent' does not match pattern '^[a-z][a-z0-9_]*$'
Fix: Use lowercase and underscores: 'test_agent'
```

### Missing Required Fields

```
Error: 'metadata' is a required property
Fix: Add metadata object with name, description, and tags
```

### Invalid Enum Values

```
Error: 'custom' is not one of ['base', 'engineer', 'qa', ...]
Fix: Use one of the defined agent types
```

### Length Constraints

```
Error: 'description' is too short (5 chars), minimum 10
Fix: Provide a more detailed description
```

## Testing Schemas

### Unit Tests

```python
import pytest
from jsonschema import validate, ValidationError

class TestAgentSchema:
    
    def test_valid_minimal_config(self, schema):
        """Test minimal valid configuration."""
        config = {
            "schema_version": "1.2.0",
            "agent_id": "test_agent",
            "agent_version": "1.0.0",
            "agent_type": "base",
            "metadata": {
                "name": "Test Agent",
                "description": "A test agent for validation",
                "tags": ["test"]
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "tools": ["Read"],
                "resource_tier": "standard"
            },
            "instructions": "You are a test agent. " * 20
        }
        
        # Should not raise
        validate(instance=config, schema=schema)
    
    def test_invalid_agent_id_pattern(self, schema):
        """Test invalid agent_id pattern."""
        config = self.get_base_config()
        config["agent_id"] = "Test-Agent"  # Invalid: uppercase and hyphen
        
        with pytest.raises(ValidationError) as exc:
            validate(instance=config, schema=schema)
        
        assert "does not match pattern" in str(exc.value)
```

### Integration Tests

```python
def test_schema_validation_pipeline():
    """Test complete validation pipeline."""
    # Load agent file
    agent_file = "test_agent.json"
    with open(agent_file) as f:
        config = json.load(f)
    
    # Validate against schema
    is_valid, errors = validate_agent_config(config)
    
    assert is_valid, f"Validation failed: {errors}"
    
    # Deploy agent
    deployed = deploy_agent(config)
    assert deployed.agent_id == config["agent_id"]
```

## Schema Documentation Tools

### Generate HTML Documentation

```python
def generate_schema_docs(schema_path: str, output_path: str):
    """
    Generate HTML documentation from JSON schema.
    """
    with open(schema_path) as f:
        schema = json.load(f)
    
    html = render_schema_to_html(schema)
    
    with open(output_path, 'w') as f:
        f.write(html)
```

### Generate Markdown Documentation

```python
def schema_to_markdown(schema: dict) -> str:
    """
    Convert JSON schema to Markdown documentation.
    """
    md = []
    md.append(f"# {schema.get('title', 'Schema')}")
    md.append(f"\n{schema.get('description', '')}\n")
    
    # Document required fields
    if 'required' in schema:
        md.append("## Required Fields\n")
        for field in schema['required']:
            md.append(f"- `{field}`")
    
    # Document properties
    if 'properties' in schema:
        md.append("\n## Properties\n")
        for name, prop in schema['properties'].items():
            md.append(f"### {name}")
            md.append(f"- Type: `{prop.get('type')}`")
            if 'description' in prop:
                md.append(f"- Description: {prop['description']}")
            if 'pattern' in prop:
                md.append(f"- Pattern: `{prop['pattern']}`")
    
    return '\n'.join(md)
```

## Related Documentation

- [Agent Schema Guide](../AGENT_SCHEMA_GUIDE.md)
- [Agent Development Guide](../agents/AGENT_DEVELOPMENT.md)
- [Frontmatter Validation](../agents/frontmatter.md)
- [Schema Security Notes](../security/agent_schema_security_notes.md)
