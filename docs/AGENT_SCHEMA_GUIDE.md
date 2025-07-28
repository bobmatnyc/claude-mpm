# Claude MPM Agent Schema Documentation

## Overview

The Claude MPM Agent Schema defines the structure and validation rules for all agent configurations in the system. This schema ensures consistency, type safety, and proper validation across all agent templates.

**Schema Version**: 1.2.0  
**Location**: `/src/claude_mpm/schemas/agent_schema.json`

## Schema Structure

### Top-Level Required Fields

Every agent configuration must include these seven required fields:

1. **`schema_version`** - Version of the schema format
2. **`agent_id`** - Unique identifier for the agent
3. **`agent_version`** - Version of the agent template
4. **`agent_type`** - Category of agent functionality
5. **`metadata`** - Human-readable information
6. **`capabilities`** - Technical specifications
7. **`instructions`** - System prompt defining behavior

### Field Specifications

#### 1. `schema_version` (Required)
- **Type**: `string`
- **Pattern**: `^\d+\.\d+\.\d+$` (semantic versioning)
- **Purpose**: Ensures compatibility between agent templates and schema validators
- **Example**: `"1.2.0"`

```json
"schema_version": "1.2.0"
```

#### 2. `agent_id` (Required)
- **Type**: `string`
- **Pattern**: `^[a-z][a-z0-9_]*$`
- **Rules**: 
  - Must start with lowercase letter
  - Can contain lowercase letters, numbers, underscores
  - Must be unique across all agents
- **Example**: `"research_agent"`, `"qa_agent"`

```json
"agent_id": "engineer_agent"
```

#### 3. `agent_version` (Required)
- **Type**: `string`
- **Pattern**: `^\d+\.\d+\.\d+$` (semantic versioning)
- **Purpose**: Track changes to individual agent templates
- **Versioning Rules**:
  - Major: Breaking changes to agent behavior
  - Minor: New features or capabilities
  - Patch: Bug fixes or minor improvements

```json
"agent_version": "2.1.0"
```

#### 4. `agent_type` (Required)
- **Type**: `string`
- **Enum Values**:
  - `"base"` - Generic agent with no specialization
  - `"engineer"` - Code implementation and development
  - `"qa"` - Quality assurance and testing
  - `"documentation"` - Documentation creation
  - `"research"` - Code analysis and research
  - `"security"` - Security analysis
  - `"ops"` - Operations and infrastructure
  - `"data_engineer"` - Data pipeline development
  - `"version_control"` - Git operations

```json
"agent_type": "engineer"
```

#### 5. `metadata` (Required)
- **Type**: `object`
- **Required Sub-fields**:
  - `name` (string, 3-50 chars) - Human-readable name
  - `description` (string, 10-200 chars) - Brief purpose
  - `tags` (array) - Discovery tags
- **Optional Sub-fields**:
  - `category` - Agent categorization
  - `author` - Template creator
  - `created_at` - ISO 8601 timestamp
  - `updated_at` - ISO 8601 timestamp

```json
"metadata": {
  "name": "Engineer Agent",
  "description": "Research-guided code implementation with pattern adherence",
  "category": "engineering",
  "tags": ["engineering", "implementation", "research-guided"],
  "author": "Claude MPM Team",
  "created_at": "2025-07-27T03:45:51.472561Z"
}
```

#### 6. `capabilities` (Required)
- **Type**: `object`
- **Required Sub-fields**:
  - `model` - Claude model to use
  - `tools` - Array of allowed tools
  - `resource_tier` - Resource allocation level
- **Optional Sub-fields**:
  - `max_tokens` - Response token limit (1000-200000)
  - `temperature` - Model temperature (0-1)
  - `timeout` - Operation timeout in seconds
  - `memory_limit` - Memory in MB
  - `cpu_limit` - CPU percentage
  - `network_access` - Boolean for network
  - `file_access` - Read/write path restrictions

```json
"capabilities": {
  "model": "claude-sonnet-4-20250514",
  "tools": ["Read", "Write", "Edit", "Bash", "Grep"],
  "resource_tier": "intensive",
  "max_tokens": 12288,
  "temperature": 0.2,
  "timeout": 1200
}
```

#### 7. `instructions` (Required)
- **Type**: `string`
- **Length**: 100-8000 characters
- **Purpose**: System prompt that defines agent behavior
- **Best Practices**:
  - Use markdown formatting
  - Include clear protocols and phases
  - Define success criteria
  - Provide examples when helpful

### Optional Fields

#### `knowledge` (Optional)
Defines agent-specific expertise and constraints:
- `domain_expertise` - Areas of expertise
- `best_practices` - Guidelines to follow
- `constraints` - Operating limitations
- `examples` - Scenario-based guidance

#### `interactions` (Optional)
Specifies input/output formats and agent handoffs:
- `input_format` - Required/optional input fields
- `output_format` - Response structure
- `handoff_agents` - Agents this can delegate to
- `triggers` - Conditional actions

#### `testing` (Optional)
Testing configuration for validation:
- `test_cases` - Example inputs and expected outputs
- `performance_benchmarks` - Response time, token usage

#### `hooks` (Optional)
Extensibility points for custom logic:
- `pre_execution` - Hooks before agent runs
- `post_execution` - Hooks after completion

## Validation Rules

### Pattern Validation

1. **Version Patterns** (`schema_version`, `agent_version`):
   ```regex
   ^\d+\.\d+\.\d+$
   ```
   Valid: `"1.0.0"`, `"2.3.1"`
   Invalid: `"1.0"`, `"v1.0.0"`

2. **Agent ID Pattern**:
   ```regex
   ^[a-z][a-z0-9_]*$
   ```
   Valid: `"research_agent"`, `"qa2_agent"`
   Invalid: `"Research_Agent"`, `"2qa_agent"`

3. **Tag Pattern**:
   ```regex
   ^[a-z][a-z0-9-]*$
   ```
   Valid: `"code-analysis"`, `"testing"`
   Invalid: `"Code_Analysis"`, `"testing!"`

### Resource Tier Limits

The schema defines guidance for resource allocation:

```json
"resource_tier_limits": {
  "intensive": {
    "memory_limit": {"min": 4096, "max": 8192},
    "cpu_limit": {"min": 60, "max": 100},
    "timeout": {"min": 600, "max": 3600}
  },
  "standard": {
    "memory_limit": {"min": 2048, "max": 4096},
    "cpu_limit": {"min": 30, "max": 60},
    "timeout": {"min": 300, "max": 1200}
  },
  "lightweight": {
    "memory_limit": {"min": 512, "max": 2048},
    "cpu_limit": {"min": 10, "max": 30},
    "timeout": {"min": 30, "max": 600}
  }
}
```

## Examples

### Valid Agent Configuration

```json
{
  "schema_version": "1.2.0",
  "agent_id": "code_reviewer",
  "agent_version": "1.0.0",
  "agent_type": "qa",
  "metadata": {
    "name": "Code Review Agent",
    "description": "Automated code review with security and performance analysis",
    "tags": ["code-review", "quality", "security"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Grep", "Glob"],
    "resource_tier": "standard",
    "max_tokens": 8192,
    "temperature": 0.3
  },
  "instructions": "You are a code review specialist focused on identifying bugs, security vulnerabilities, and performance issues. Follow best practices for the programming language being reviewed."
}
```

### Invalid Configurations

#### Missing Required Field
```json
{
  "schema_version": "1.2.0",
  "agent_id": "test_agent",
  // Missing: agent_version, agent_type, metadata, capabilities, instructions
}
```
**Error**: Missing required fields

#### Invalid Pattern
```json
{
  "agent_id": "Test-Agent",  // Invalid: uppercase and hyphen
  "agent_version": "1.0",     // Invalid: missing patch version
  ...
}
```
**Error**: Pattern validation failure

#### Invalid Enum Value
```json
{
  "agent_type": "custom",     // Invalid: not in enum list
  "capabilities": {
    "model": "gpt-4",         // Invalid: not a Claude model
    ...
  }
}
```
**Error**: Enum validation failure

## Schema-Template Relationship

The schema enforces structure while templates provide implementation:

1. **Schema** (`/src/claude_mpm/schemas/agent_schema.json`):
   - Defines structure and validation rules
   - Enforces type safety and constraints
   - Provides enum values and patterns

2. **Templates** (`/src/claude_mpm/agents/templates/*.json`):
   - Implement specific agent behaviors
   - Must conform to schema validation
   - Contain actual instructions and configurations

3. **Validation Flow**:
   ```
   Template JSON → Schema Validator → Valid Agent Configuration
                          ↓
                   Validation Error
   ```

## Best Practices

### 1. Versioning
- Use semantic versioning for both schema and agents
- Update `agent_version` when changing behavior
- Update `schema_version` only when schema structure changes

### 2. Naming Conventions
- Use snake_case for `agent_id`
- Use descriptive names in metadata
- Keep tags lowercase with hyphens

### 3. Resource Allocation
- Match `resource_tier` to agent complexity
- Set appropriate timeouts for expected tasks
- Configure `max_tokens` based on response needs

### 4. Instructions
- Keep instructions focused and clear
- Use markdown for formatting
- Include examples for complex behaviors
- Define success criteria

### 5. Tool Selection
- Only include necessary tools
- Consider security implications
- Use `allowed_tools` and `disallowed_tools` for restrictions

## Validation Tools

To validate an agent configuration:

```python
from claude_mpm.validation.agent_validator import validate_agent_config

# Validate agent configuration
is_valid, errors = validate_agent_config(agent_dict)
if not is_valid:
    print(f"Validation errors: {errors}")
```

## Common Validation Errors

1. **Pattern Mismatch**: Ensure IDs and versions follow patterns
2. **Missing Required Fields**: Check all seven required fields
3. **Enum Violations**: Use only allowed values for enums
4. **Length Constraints**: Respect min/max lengths
5. **Type Mismatches**: Ensure correct data types

## Future Considerations

The schema is designed for extensibility:
- New agent types can be added to the enum
- Additional tools can be included
- New optional fields can extend functionality
- Backward compatibility through versioning