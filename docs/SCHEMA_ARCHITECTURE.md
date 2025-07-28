# Agent Schema Architecture

## Overview

The Claude MPM system uses a dual-schema architecture to manage agent configurations:

1. **Primary Schema** (`/src/claude_mpm/schemas/agent_schema.json`) - Version 1.2.0
2. **Agent Directory Schema** (`/src/claude_mpm/agents/schema/agent_schema.json`) - Version 1.1.0

## Schema Differences and Purpose

### Primary Schema (v1.2.0)
**Location**: `/src/claude_mpm/schemas/agent_schema.json`
**Purpose**: Main validation schema with strict rules and comprehensive validation

Key Features:
- Stricter validation patterns (e.g., `agent_id` must start with lowercase letter)
- More comprehensive enum lists for models and tools
- Detailed resource tier definitions
- Strict `additionalProperties: false` at root level
- More detailed field constraints (min/max lengths)

### Agent Directory Schema (v1.1.0)
**Location**: `/src/claude_mpm/agents/schema/agent_schema.json`
**Purpose**: Template validation with more flexibility for development

Key Differences:
- More permissive `agent_id` pattern (`^[a-z0-9_]+$`)
- `additionalProperties: true` in capabilities section
- Additional fields: `configuration`, `specializations`
- Less strict validation rules
- Focus on template structure

## Schema Evolution

The dual-schema approach allows for:

1. **Backward Compatibility**: v1.1.0 maintains compatibility with older agents
2. **Progressive Enhancement**: v1.2.0 introduces stricter validation
3. **Development Flexibility**: Looser validation during development
4. **Production Safety**: Strict validation for deployed agents

## Validation Flow

```
Agent Template Creation
        ↓
Agent Directory Schema (v1.1.0)
   - Initial validation
   - Development phase
        ↓
Primary Schema (v1.2.0)
   - Production validation
   - Deployment readiness
        ↓
Deployed Agent
```

## Key Differences Table

| Feature | v1.1.0 (Agent Dir) | v1.2.0 (Primary) |
|---------|-------------------|------------------|
| **agent_id pattern** | `^[a-z0-9_]+$` | `^[a-z][a-z0-9_]*$` |
| **Root additionalProperties** | false | false |
| **Capabilities additionalProperties** | true | false |
| **Field length constraints** | None | Enforced |
| **Resource tier definitions** | Basic | Detailed with limits |
| **Model enum list** | Not enforced | Comprehensive list |
| **Tools enum list** | Not enforced | Comprehensive list |
| **Tag pattern** | None | `^[a-z][a-z0-9-]*$` |

## Migration Path

When upgrading agents from v1.1.0 to v1.2.0:

1. **Update agent_id**: Ensure it starts with a lowercase letter
2. **Add field constraints**: Respect min/max lengths
3. **Validate enums**: Use only allowed model and tool values
4. **Fix tags**: Convert to lowercase with hyphens
5. **Remove extra properties**: Clean up any additional fields

## Best Practices

### During Development (v1.1.0)
- Use the agent directory schema for initial validation
- Take advantage of flexible validation for experimentation
- Document any additional properties used

### For Production (v1.2.0)
- Validate against the primary schema before deployment
- Ensure all constraints are met
- Remove any development-only fields
- Test with strict validation enabled

## Schema Location Strategy

```
/src/claude_mpm/
├── schemas/
│   └── agent_schema.json      # Primary validation (v1.2.0)
└── agents/
    ├── schema/
    │   └── agent_schema.json  # Template validation (v1.1.0)
    └── templates/
        ├── engineer.json
        ├── qa.json
        └── ...
```

## Validation Code Example

```python
from claude_mpm.validation.agent_validator import AgentValidator

# For development validation
dev_validator = AgentValidator(schema_version="1.1.0")
is_valid_dev, errors_dev = dev_validator.validate(agent_config)

# For production validation
prod_validator = AgentValidator(schema_version="1.2.0")
is_valid_prod, errors_prod = prod_validator.validate(agent_config)

# Deployment check
if is_valid_dev and not is_valid_prod:
    print("Agent needs updates for production deployment")
    print(f"Production errors: {errors_prod}")
```

## Future Considerations

1. **Schema Consolidation**: Eventually merge to a single schema
2. **Version Detection**: Auto-detect schema version from agent
3. **Migration Tools**: Automated upgrade from v1.1.0 to v1.2.0
4. **Schema Extensions**: Support for custom agent types

## Conclusion

The dual-schema architecture provides flexibility during development while ensuring production safety. Always validate against v1.2.0 before deploying agents to production environments.