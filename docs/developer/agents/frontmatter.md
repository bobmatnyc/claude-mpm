# Agent Frontmatter Documentation

This document provides comprehensive documentation for agent frontmatter fields used across **Claude MPM** agent formats, and explains compatibility with **Anthropic's Claude Code** format.

## Table of Contents

1. [Overview](#overview)
2. [Format Standards Comparison](#format-standards-comparison)
3. [Claude Code vs Claude MPM Fields](#claude-code-vs-claude-mpm-fields)
4. [Required Fields](#required-fields)
5. [Optional Fields](#optional-fields)
6. [Format-Specific Usage](#format-specific-usage)
7. [Field Descriptions](#field-descriptions)
8. [Validation System](#validation-system)
9. [Schema Enforcement](#schema-enforcement)
10. [Auto-Corrections](#auto-corrections)
11. [Validation Tools](#validation-tools)
12. [Common Issues and Solutions](#common-issues-and-solutions)
13. [Best Practices](#best-practices)
14. [Validation Rules](#validation-rules)
15. [Examples](#examples)
16. [Common Pitfalls](#common-pitfalls)
17. [Migration Considerations](#migration-considerations)

## Overview

Agent frontmatter defines the metadata and configuration for agent templates. Claude MPM supports **two distinct agent standards** with different capabilities and use cases:

1. **Claude Code Format** - Anthropic's official agent standard
2. **Claude MPM Format** - Extended format with additional features

### Supported Formats by Location

- **`.claude-mpm/agents/*.json`**: Claude MPM JSON format (REQUIRED - source files)
- **`.claude/agents/*.md`**: Claude Code Markdown format (auto-generated from JSON)
- **`~/.claude-mpm/agents/*`**: Any format (JSON/Markdown/YAML - flexible)

### JSON → Markdown Conversion

Claude MPM automatically converts JSON agents to Markdown format:
- **Source**: `.claude-mpm/agents/*.json` (Claude MPM native format)
- **Target**: `.claude/agents/*.md` (Claude Code compatibility format)
- **Process**: Automatic during deployment for Claude Desktop/IDE integration

## Format Standards Comparison

### Anthropic's Claude Code vs Claude MPM

| Aspect | Claude Code | Claude MPM |
|--------|-------------|------------|
| **Purpose** | Anthropic tools integration | Extended project capabilities |
| **Complexity** | Simple, minimal | Comprehensive, configurable |
| **Required Fields** | `name`, `description` | Extended metadata object |
| **File Extensions** | `.claude`, `.md` | `.claude-mpm`, `.json` |
| **Tools Format** | String or array | Structured array only |
| **Model Specification** | Tier names (`sonnet`) | Full model IDs |
| **Validation** | Basic YAML validation | Full JSON Schema |
| **Resource Management** | Basic | Advanced with limits |
| **Testing Support** | None | Built-in test framework |
| **Hook System** | None | Pre/post execution hooks |
| **Network Controls** | Basic | Fine-grained permissions |

### When to Use Each Format

**Use Claude Code Format When:**
- Working with Claude Desktop or IDE extensions  
- Need compatibility with Anthropic tooling
- Creating simple, human-readable agents
- Rapid prototyping and personal productivity

**Use Claude MPM Format When:**
- Building enterprise or production agents
- Need advanced resource management
- Require comprehensive testing and validation
- Want integrated hook system and extensibility
- Building project-specific agent teams

## Claude Code vs Claude MPM Fields

### Claude Code Fields (Anthropic Standard)

These are the **only** fields recognized by Anthropic's Claude Code:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Agent identifier (kebab-case) |
| `description` | string | ✅ | Natural language description |
| `tools` | string/array | ❌ | Available tools (optional) |
| `model` | string | ❌ | Model tier (`sonnet`, `opus`, `haiku`) |

**Example Claude Code Frontmatter:**
```yaml
---
name: code-reviewer
description: Reviews code for quality, security, and best practices
tools: Read, Write, Edit, Grep
model: sonnet
---
```

### Claude MPM Extended Fields

Claude MPM recognizes **all Claude Code fields** plus these additional fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | ✅ | Schema version (`1.2.0`) |
| `agent_id` | string | ✅ | Structured agent identifier |
| `agent_version` | string | ✅ | Semantic version |
| `agent_type` | string | ✅ | Agent category |
| `metadata` | object | ✅ | Structured metadata |
| `capabilities` | object | ✅ | Technical capabilities |
| `instructions` | string | ✅ | System instructions |
| `knowledge` | object | ❌ | Domain expertise |
| `interactions` | object | ❌ | Interaction patterns |
| `testing` | object | ❌ | Test configurations |
| `hooks` | object | ❌ | Hook configurations |

### Field Compatibility Matrix

| Field | Claude Code | Claude MPM JSON | Claude MPM Markdown |
|-------|-------------|-----------------|-------------------|
| `name` | ✅ | Via `metadata.name` | ✅ (frontmatter) |
| `description` | ✅ | Via `metadata.description` | ✅ (frontmatter) |
| `tools` | ✅ | Via `capabilities.tools` | ✅ (frontmatter) |
| `model` | ✅ | Via `capabilities.model` | ✅ (frontmatter) |
| `schema_version` | ❌ | ✅ | ✅ (frontmatter) |
| `agent_id` | ❌ | ✅ | ✅ (frontmatter) |
| `metadata` | ❌ | ✅ | ✅ (frontmatter) |
| `capabilities` | ❌ | ✅ | ✅ (frontmatter) |
| `knowledge` | ❌ | ✅ | ✅ (frontmatter) |
| `testing` | ❌ | ✅ | ✅ (frontmatter) |

## Required Fields

These fields must be present in every agent configuration:

### `schema_version`
- **Type**: `string`
- **Pattern**: `^\d+\.\d+\.\d+$`
- **Description**: Schema version for the agent template format
- **Examples**: `"1.0.0"`, `"1.2.0"`
- **Purpose**: Ensures compatibility between agent templates and schema validators

### `agent_id`
- **Type**: `string`
- **Pattern**: `^[a-z][a-z0-9_]*$`
- **Description**: Unique agent identifier used for discovery and loading
- **Examples**: `"research_agent"`, `"engineer_agent"`, `"qa_agent"`
- **Purpose**: System uses this for agent lookup and caching

### `agent_version`
- **Type**: `string`
- **Pattern**: `^\d+\.\d+\.\d+$`
- **Description**: Semantic version of the agent template
- **Examples**: `"1.0.0"`, `"2.1.3"`
- **Purpose**: Version tracking and compatibility management

### `agent_type`
- **Type**: `string`
- **Enum**: `["base", "engineer", "qa", "documentation", "research", "security", "ops", "data_engineer", "version_control"]`
- **Description**: Primary function category for the agent
- **Purpose**: Used for agent discovery and capability matching

### `metadata`
- **Type**: `object`
- **Required Subfields**: `name`, `description`, `tags`
- **Description**: Human-readable information about the agent
- **Purpose**: UI display and agent selection

### `capabilities`
- **Type**: `object`
- **Required Subfields**: `model`, `tools`, `resource_tier`
- **Description**: Technical capabilities and resource requirements
- **Purpose**: Model selection and resource allocation

### `instructions`
- **Type**: `string`
- **Length**: 100-8000 characters
- **Description**: Agent system instructions and behavior definition
- **Purpose**: Becomes the agent's system prompt

## Optional Fields

These fields provide additional configuration and functionality:

### `knowledge`
- **Type**: `object`
- **Description**: Agent-specific knowledge and context
- **Subfields**:
  - `domain_expertise`: Array of expertise areas
  - `best_practices`: Array of practices the agent follows
  - `constraints`: Array of operating constraints
  - `examples`: Array of scenario/approach objects

### `interactions`
- **Type**: `object`
- **Description**: Agent interaction patterns and preferences
- **Subfields**:
  - `input_format`: Expected input structure
  - `output_format`: Preferred output format
  - `handoff_agents`: Agents this agent can delegate to
  - `triggers`: Conditions that trigger specific actions

### `testing`
- **Type**: `object`
- **Description**: Testing configuration for the agent
- **Subfields**:
  - `test_cases`: Array of test scenarios
  - `performance_benchmarks`: Performance criteria

### `hooks`
- **Type**: `object`
- **Description**: Hook configurations for extensibility
- **Subfields**:
  - `pre_execution`: Pre-execution hooks
  - `post_execution`: Post-execution hooks

## Format-Specific Usage

### JSON Format
All fields are top-level properties:

```json
{
  "schema_version": "1.2.0",
  "agent_id": "example_agent",
  "agent_version": "1.0.0",
  "agent_type": "engineer",
  "metadata": {
    "name": "Example Agent",
    "description": "Example agent description",
    "tags": ["example", "test"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Write"],
    "resource_tier": "standard"
  },
  "instructions": "Agent instructions here..."
}
```

### Markdown with YAML Frontmatter (.claude)
Fields are in YAML frontmatter at the top:

```markdown
---
schema_version: "1.2.0"
agent_id: example_agent
agent_version: "1.0.0"
agent_type: engineer
metadata:
  name: Example Agent
  description: Example agent description
  tags:
    - example
    - test
capabilities:
  model: claude-sonnet-4-20250514
  tools:
    - Read
    - Write
  resource_tier: standard
---

# Agent Instructions

Agent instructions in markdown format...
```

### Markdown with Extended Frontmatter (.claude-mpm)
Similar to .claude but with full schema support:

```markdown
---
schema_version: "1.2.0"
agent_id: example_agent
agent_version: "1.0.0"
agent_type: engineer
metadata:
  name: Example Agent
  description: Example agent description
  category: engineering
  tags:
    - example
    - test
  author: Developer Name
  created_at: "2025-01-15T10:30:00Z"
capabilities:
  model: claude-sonnet-4-20250514
  tools:
    - Read
    - Write
    - Edit
  resource_tier: standard
  max_tokens: 8192
  temperature: 0.7
knowledge:
  domain_expertise:
    - software-engineering
    - testing
  best_practices:
    - Use descriptive variable names
    - Write comprehensive tests
interactions:
  output_format:
    structure: markdown
    includes:
      - analysis
      - recommendations
---

# Agent Instructions

Detailed agent instructions in markdown format...
```

## Field Descriptions

### `metadata` Object

#### `name`
- **Type**: `string`
- **Length**: 3-50 characters
- **Description**: Human-readable agent name for UI display
- **Example**: `"Documentation Agent"`

#### `description`
- **Type**: `string`
- **Length**: 10-200 characters
- **Description**: Brief description of agent purpose
- **Example**: `"Creates and maintains technical documentation"`

#### `category`
- **Type**: `string`
- **Enum**: `["engineering", "research", "quality", "operations", "specialized"]`
- **Description**: Agent category for organization
- **Optional**: Yes

#### `tags`
- **Type**: `array`
- **Items**: `string` with pattern `^[a-z][a-z0-9-]*$`
- **Length**: 1-10 items
- **Description**: Tags for discovery and filtering
- **Example**: `["documentation", "api-docs", "guides"]`

#### `author`
- **Type**: `string`
- **Description**: Agent template author
- **Optional**: Yes

#### `created_at`
- **Type**: `string`
- **Format**: `date-time`
- **Description**: Creation timestamp
- **Optional**: Yes

#### `updated_at`
- **Type**: `string`
- **Format**: `date-time`
- **Description**: Last update timestamp
- **Optional**: Yes

### `capabilities` Object

#### `model`
- **Type**: `string`
- **Enum**: `["opus", "sonnet", "haiku"]`
- **Description**: Claude model tier to use for this agent
- **Valid Values**:
  - `"opus"` - Highest capability model for complex tasks
  - `"sonnet"` - Balanced performance for most tasks
  - `"haiku"` - Fastest model for simple tasks
- **Auto-correction**: Full model names (e.g., `"claude-3-5-sonnet-20241022"`) are automatically normalized to tier names

#### `tools`
- **Type**: `array`
- **Items**: Tool name strings
- **Description**: Available tools for the agent
- **Valid Tools**:
  - `"Read"`, `"Write"`, `"Edit"`, `"MultiEdit"`
  - `"Grep"`, `"Glob"`, `"LS"`
  - `"Bash"`
  - `"WebSearch"`, `"WebFetch"`
  - `"NotebookRead"`, `"NotebookEdit"`
  - `"TodoWrite"`, `"ExitPlanMode"`
  - `"git"`, `"docker"`, `"kubectl"`, `"terraform"`
  - `"aws"`, `"gcloud"`, `"azure"`

#### `resource_tier`
- **Type**: `string`
- **Enum**: `["basic", "standard", "intensive", "lightweight"]`
- **Description**: Resource allocation tier
- **Purpose**: Determines memory, CPU, and timeout limits

#### `max_tokens`
- **Type**: `integer`
- **Range**: 1000-200000
- **Default**: 8192
- **Description**: Maximum tokens for response generation

#### `temperature`
- **Type**: `number`
- **Range**: 0-1
- **Default**: 0.7
- **Description**: Model temperature for response randomness

#### `timeout`
- **Type**: `integer`
- **Range**: 30-3600
- **Default**: 300
- **Description**: Operation timeout in seconds

#### `memory_limit`
- **Type**: `integer`
- **Range**: 512-8192
- **Description**: Memory limit in MB
- **Optional**: Yes

#### `cpu_limit`
- **Type**: `integer`
- **Range**: 10-100
- **Description**: CPU limit percentage
- **Optional**: Yes

#### `network_access`
- **Type**: `boolean`
- **Default**: false
- **Description**: Whether agent needs network access

#### `file_access`
- **Type**: `object`
- **Description**: File access permissions
- **Subfields**:
  - `read_paths`: Array of allowed read paths
  - `write_paths`: Array of allowed write paths

#### `allowed_tools`
- **Type**: `array`
- **Description**: Glob patterns for allowed file paths
- **Optional**: Yes

#### `disallowed_tools`
- **Type**: `array`
- **Description**: Tools to explicitly disallow
- **Optional**: Yes

## Validation System

Claude MPM includes an automatic **dual-mode validation system** that handles both Claude Code and Claude MPM formats appropriately. The system automatically detects the format and applies the correct validation rules.

### Dual-Mode Validation

**Format Detection Phase:**
1. **File Extension Analysis**: `.claude` files → Claude Code validation
2. **Content Analysis**: Presence of `schema_version` → Claude MPM validation  
3. **Fallback Logic**: Simple frontmatter → Claude Code validation

**Claude Code Validation:**
- Basic YAML syntax validation
- Required fields: `name`, `description`
- Optional fields: `tools`, `model`
- Lenient tool name checking
- Model tier validation (`sonnet`, `opus`, `haiku`)

**Claude MPM Validation:**
- Full JSON Schema validation against v1.2.0 schema
- All required fields per schema
- Strict type checking and constraints
- Resource limit validation
- Cross-field dependency checks

### Automatic Startup Validation

- **When it runs**: Every time the CLI starts up or agents are loaded
- **What it validates**: All agent files with appropriate format-specific rules
- **Scope**: Format-aware validation with automatic fallback and conversion

### What Gets Validated

1. **Required Fields**: Ensures all mandatory fields (`name`, `description`, `version`, `model`) are present
2. **Field Types**: Validates that fields match expected data types (string, array, object)
3. **Value Formats**: Checks patterns for fields like `name` (snake_case), `version` (semantic versioning)
4. **Enum Values**: Validates that categorical fields use allowed values
5. **Tools Format**: Ensures tools field is a proper array, not string representation
6. **Model Names**: Validates and normalizes model identifiers to standard tiers

### Common Auto-Corrections Applied

The validation system automatically corrects these common issues:

- **Model normalization**: `"claude-3-5-sonnet-20241022"` → `"sonnet"`
- **Tools parsing**: `"Read, Write, Edit"` → `["Read", "Write", "Edit"]`
- **Version format**: `"1.0"` → `"1.0.0"`
- **Tool case**: `"read"` → `"Read"`
- **Field cleanup**: Removes invalid or deprecated fields

The corrections are applied automatically and logged for transparency.

## Schema Enforcement

Frontmatter validation is enforced through a JSON schema located at:

**Schema Location**: `src/claude_mpm/schemas/frontmatter_schema.json`

### Model Field Requirements

The `model` field must use one of these standardized values:

```yaml
model: "opus"    # For Claude Opus models
model: "sonnet"  # For Claude Sonnet models  
model: "haiku"   # For Claude Haiku models
```

**Invalid model values** like `"claude-3-5-sonnet-20241022"` are automatically normalized to the correct tier.

### Tools Field Requirements

The `tools` field **must be a proper YAML array**, not a string representation:

```yaml
# ✅ Correct - proper YAML array
tools:
  - Read
  - Write
  - Edit
  - Bash

# ❌ Wrong - string representation
tools: "Read, Write, Edit, Bash"
tools: 'Read, Write, Edit, Bash'
```

**Auto-correction**: String representations are automatically parsed into proper arrays during validation.

## Auto-Corrections

The validation system applies these automatic corrections:

### Model Normalization Mappings

```yaml
# These model names are automatically corrected:
"claude-3-5-sonnet-20241022" → "sonnet"
"claude-3-5-sonnet-20240620" → "sonnet"
"claude-sonnet-4-20250514"   → "sonnet"
"claude-4-sonnet-20250514"   → "sonnet"
"claude-3-sonnet-20240229"   → "sonnet"
"20241022"                   → "sonnet"  # Common shorthand

"claude-3-opus-20240229"     → "opus"
"claude-opus-4-20250514"     → "opus"
"claude-4-opus-20250514"     → "opus"

"claude-3-haiku-20240307"    → "haiku"
"claude-3-5-haiku-20241022"  → "haiku"
```

### Tools Field Conversion

```yaml
# String to array conversion:
"Read, Write, Edit, Bash" → ["Read", "Write", "Edit", "Bash"]
"Read,Write,Edit" → ["Read", "Write", "Edit"]  # Handles no spaces
"Read | Write | Edit" → ["Read", "Write", "Edit"]  # Handles pipe separators
```

### Version Format Fixes

```yaml
# Version normalization:
"1.0"     → "1.0.0"
"2.1"     → "2.1.0"
"1"       → "1.0.0"
"v1.2.3"  → "1.2.3"  # Removes 'v' prefix
```

### Case Normalization for Tools

```yaml
# Tool name corrections:
"read"           → "Read"
"write"          → "Write"
"edit"           → "Edit"
"multiedit"      → "MultiEdit"
"grep"           → "Grep"
"bash"           → "Bash"
"websearch"      → "WebSearch"
"todowrite"      → "TodoWrite"
```

## Validation Tools

Claude MPM provides command-line tools for validating and fixing frontmatter:

### Validation Script: `scripts/validate_agent_frontmatter.py`

**Purpose**: Check all agent files for frontmatter issues without making changes.

```bash
# Validate all agent files in .claude/agents/
python scripts/validate_agent_frontmatter.py

# The script will show:
# ✅ Valid files (no issues)
# ⚠️  Files with auto-correctable issues  
# ❌ Files with validation errors
# 📊 Summary statistics
```

**Output Example**:
```
📄 engineer.md
⚠️  Auto-correctable issues found:
   📝 Normalized model from 'claude-3-5-sonnet-20241022' to 'sonnet'
   📝 Converted tools from string to array: ['Read', 'Write', 'Edit']

✅ Valid files: 5
⚠️  Auto-correctable: 2  
❌ With errors: 0
```

### Fix Script: `scripts/fix_agent_frontmatter.py`

**Purpose**: Apply automatic corrections to agent files.

```bash
# Dry run - show what would be fixed
python scripts/fix_agent_frontmatter.py --dry-run

# Apply fixes to files
python scripts/fix_agent_frontmatter.py

# Fix files in a specific directory
python scripts/fix_agent_frontmatter.py --directory /path/to/agents
```

**Options**:
- `--dry-run`: Preview changes without modifying files
- `--directory`: Specify custom agent directory (default: `.claude/agents`)

**Usage Workflow**:
1. Run validation script to identify issues
2. Run fix script with `--dry-run` to preview changes
3. Run fix script without `--dry-run` to apply corrections
4. Run validation again to confirm all issues resolved

## Common Issues and Solutions

### Issue 1: String Tools Field

**Problem**: Tools defined as a string instead of YAML array

```yaml
# ❌ Wrong
tools: "Read, Write, Edit, Bash"
```

**Solution**: Use proper YAML array syntax

```yaml
# ✅ Correct  
tools:
  - Read
  - Write
  - Edit
  - Bash
```

**Auto-correction**: The validation system automatically parses string representations into proper arrays.

### Issue 2: Full Model Names

**Problem**: Using full Claude model identifiers instead of tiers

```yaml
# ❌ Wrong
model: "claude-3-5-sonnet-20241022"
```

**Solution**: Use standardized tier names

```yaml
# ✅ Correct
model: "sonnet"
```

**Auto-correction**: Full model names are automatically normalized to tiers.

### Issue 3: Incorrect Version Format

**Problem**: Version not following semantic versioning

```yaml
# ❌ Wrong
version: "1.0"
version: "v2.1.3"
```

**Solution**: Use proper semantic versioning

```yaml
# ✅ Correct
version: "1.0.0"
version: "2.1.3"
```

**Auto-correction**: Versions are automatically normalized to semantic format.

### Issue 4: Case Issues in Tool Names

**Problem**: Tool names with incorrect capitalization

```yaml
# ❌ Wrong
tools:
  - read
  - WRITE
  - multiedit
```

**Solution**: Use proper tool name capitalization

```yaml
# ✅ Correct
tools:
  - Read
  - Write
  - MultiEdit
```

**Auto-correction**: Tool names are automatically corrected to proper case.

### Issue 5: Validation Failures

**Problem**: Validation fails when loading agents

**Symptoms**:
- Agent loading errors on startup
- "Invalid frontmatter" warnings in logs
- Agents not appearing in available agents list

**Solutions**:
1. Run validation script to identify specific issues
2. Use fix script to auto-correct common problems
3. Manually fix structural issues (missing required fields)
4. Verify schema compliance

## Best Practices

### 1. Always Use Allowed Model Values

```yaml
# ✅ Use these standardized values
model: "opus"     # For highest capability tasks
model: "sonnet"   # For balanced performance and cost
model: "haiku"    # For simple, fast tasks

# ❌ Don't use full model identifiers
model: "claude-3-5-sonnet-20241022"  # Will be auto-corrected
```

### 2. Always Format Tools as Proper YAML List

```yaml
# ✅ Correct YAML array format
tools:
  - Read
  - Write
  - Edit
  - Bash

# ❌ Avoid string representations  
tools: "Read, Write, Edit, Bash"
```

### 3. Use Semantic Versioning

```yaml
# ✅ Follow semantic versioning (MAJOR.MINOR.PATCH)
version: "1.0.0"   # Initial release
version: "1.1.0"   # New features added
version: "1.1.1"   # Bug fixes
version: "2.0.0"   # Breaking changes

# ❌ Avoid incomplete versions
version: "1.0"     # Will be auto-corrected to "1.0.0"
version: "v1.2.3"  # 'v' prefix will be removed
```

### 4. Regular Validation

```bash
# Run validation regularly during development
python scripts/validate_agent_frontmatter.py

# Fix issues immediately when found
python scripts/fix_agent_frontmatter.py --dry-run
python scripts/fix_agent_frontmatter.py
```

### 5. Consistent Field Formatting

```yaml
# ✅ Use consistent, descriptive values
name: my_custom_agent          # snake_case identifier
description: "Specialized agent for data processing tasks"  # Clear, descriptive
tags:
  - data-processing            # kebab-case for tags
  - automation
  - specialized
```

### 6. Test After Changes

After modifying frontmatter:
1. Run validation to check for issues
2. Test agent loading: `./claude-mpm agents list`
3. Verify agent appears and loads correctly
4. Check logs for any validation warnings

## Validation Rules

### Field Validation

1. **String Patterns**: Agent IDs and tags must match specified regex patterns
2. **Length Constraints**: All string fields have minimum and maximum length requirements
3. **Enum Validation**: Categorical fields must use valid enum values
4. **Nested Objects**: All required subfields must be present in object fields
5. **Array Constraints**: Arrays have min/max item limits and unique item requirements

### Business Rules

1. **Resource Consistency**: Resource limits should align with the specified tier
2. **Tool Compatibility**: Some tool combinations may generate warnings
3. **Model Selection**: Model should match the complexity requirements
4. **Network Dependencies**: Network tools require `network_access: true`
5. **Security Constraints**: Dangerous tool combinations are flagged

### Cross-Field Validation

1. **Version Compatibility**: `schema_version` must be supported by validator
2. **Agent Type Consistency**: `agent_type` should match the agent's actual purpose
3. **Resource Tier Alignment**: Resource limits should fall within tier ranges
4. **Tool Dependencies**: Some tools require specific configuration

## Examples

### Minimal Required Configuration

```yaml
schema_version: "1.2.0"
agent_id: minimal_agent
agent_version: "1.0.0"
agent_type: base
metadata:
  name: Minimal Agent
  description: Basic agent with minimal configuration
  tags:
    - minimal
    - example
capabilities:
  model: claude-sonnet-4-20250514
  tools:
    - Read
  resource_tier: lightweight
instructions: |
  # Minimal Agent
  
  You are a basic agent with minimal capabilities.
```

### Full Configuration Example

```yaml
schema_version: "1.2.0"
agent_id: comprehensive_agent
agent_version: "2.1.0"
agent_type: engineer
metadata:
  name: Comprehensive Engineering Agent
  description: Full-featured engineering agent with all capabilities
  category: engineering
  tags:
    - engineering
    - comprehensive
    - full-stack
  author: Engineering Team
  created_at: "2025-01-15T10:30:00Z"
  updated_at: "2025-01-20T14:45:00Z"
capabilities:
  model: claude-sonnet-4-20250514
  tools:
    - Read
    - Write
    - Edit
    - MultiEdit
    - Grep
    - Glob
    - Bash
    - git
  resource_tier: standard
  max_tokens: 16384
  temperature: 0.3
  timeout: 600
  memory_limit: 2048
  cpu_limit: 40
  network_access: true
  file_access:
    read_paths:
      - "./"
    write_paths:
      - "./src"
      - "./tests"
knowledge:
  domain_expertise:
    - software-engineering
    - system-architecture
    - testing
  best_practices:
    - Write clean, maintainable code
    - Use comprehensive testing
    - Follow security best practices
  constraints:
    - Must follow company coding standards
    - Requires code review approval
  examples:
    - scenario: Bug fix request
      approach: Identify root cause, write test, fix code, verify
interactions:
  input_format:
    required_fields:
      - task_description
    optional_fields:
      - context
      - constraints
  output_format:
    structure: markdown
    includes:
      - analysis
      - code_changes
      - testing_strategy
  handoff_agents:
    - qa_agent
    - security_agent
  triggers:
    - condition: security_issue_detected
      action: handoff_to_security_agent
testing:
  test_cases:
    - name: Basic engineering task
      input: Fix the login bug in user authentication
      expected_behavior: Identifies issue, provides solution, includes tests
      validation_criteria:
        - identifies_root_cause
        - provides_working_fix
        - includes_test_coverage
  performance_benchmarks:
    response_time: 300
    token_usage: 8192
    success_rate: 0.95
hooks:
  pre_execution:
    - name: security_scan
      enabled: true
  post_execution:
    - name: code_quality_check
      enabled: true
instructions: |
  # Comprehensive Engineering Agent
  
  You are an expert software engineer with deep knowledge of:
  - Modern development practices
  - System architecture and design patterns
  - Testing methodologies
  - Security considerations
  
  ## Approach
  1. Analyze the problem thoroughly
  2. Consider multiple solutions
  3. Implement clean, maintainable code
  4. Provide comprehensive testing
  5. Document your reasoning
  
  ## Standards
  - Follow the project's coding standards
  - Write self-documenting code
  - Include appropriate error handling
  - Consider performance implications
  - Ensure security best practices
```

## Common Pitfalls

### 1. Incorrect Field Names

**Problem**: Using wrong field names from different schema versions
```yaml
# ❌ Wrong
name: Agent Name
desc: Agent description

# ✅ Correct
metadata:
  name: Agent Name
  description: Agent description
```

### 2. Invalid Patterns

**Problem**: Agent IDs that don't match the required pattern
```yaml
# ❌ Wrong - contains uppercase and hyphens
agent_id: My-Agent-Name

# ✅ Correct - lowercase with underscores
agent_id: my_agent_name
```

### 3. Missing Required Fields

**Problem**: Omitting required nested fields
```yaml
# ❌ Wrong - missing required metadata fields
metadata:
  name: Agent Name
  # Missing description and tags

# ✅ Correct - all required fields present
metadata:
  name: Agent Name
  description: Agent description
  tags:
    - example
```

### 4. Invalid Tool Names

**Problem**: Using unsupported tool names
```yaml
# ❌ Wrong - unsupported tools
capabilities:
  tools:
    - file_reader
    - shell_executor

# ✅ Correct - valid tool names
capabilities:
  tools:
    - Read
    - Bash
```

### 5. Resource Tier Misalignment

**Problem**: Resource limits that don't match the tier
```yaml
# ❌ Wrong - lightweight tier with intensive resources
capabilities:
  resource_tier: lightweight
  memory_limit: 8192  # Too high for lightweight
  cpu_limit: 100      # Too high for lightweight

# ✅ Correct - aligned with tier limits
capabilities:
  resource_tier: lightweight
  memory_limit: 1024
  cpu_limit: 20
```

### 6. Schema Version Mismatch

**Problem**: Using unsupported schema versions
```yaml
# ❌ Wrong - unsupported version
schema_version: "2.0.0"

# ✅ Correct - supported version
schema_version: "1.2.0"
```

### 7. Instructions Length Issues

**Problem**: Instructions too short or too long
```yaml
# ❌ Wrong - too short (less than 100 characters)
instructions: "You are an agent."

# ❌ Wrong - too long (more than 8000 characters)
instructions: "Very long instructions that exceed the limit..."

# ✅ Correct - appropriate length
instructions: |
  # Agent Name
  
  You are a specialized agent with specific capabilities...
  [100-8000 characters of detailed instructions]
```

## Migration Considerations

### From Claude Code to Claude MPM

**Automatic Migration (Recommended):**
```bash
# Convert Claude Code agents to Claude MPM format
./claude-mpm agents convert --input-format claude-code --output-format claude-mpm
./claude-mpm agents convert --file path/to/agent.claude --output-format claude-mpm
```

**Manual Migration Steps:**
1. **Keep Original**: Maintain `.claude` files for Anthropic tool compatibility
2. **Create Extended Version**: Add `.claude-mpm` version with enhanced features  
3. **Field Mapping**: Map Claude Code fields to Claude MPM structure
4. **Add Required Fields**: Include `schema_version`, `agent_id`, etc.
5. **Enhance Capabilities**: Add advanced configuration options
6. **Validate**: Ensure both formats work correctly

**Migration Field Mapping:**

| Claude Code Field | Claude MPM Field | Notes |
|-------------------|------------------|--------|
| `name` | `metadata.name` + `agent_id` | Also becomes snake_case agent_id |
| `description` | `metadata.description` | Direct mapping |
| `tools` | `capabilities.tools` | Must be array format |
| `model` | `capabilities.model` | May need full model ID |
| `version` | `agent_version` | Add if missing |
| *(none)* | `schema_version` | Always "1.2.0" |
| *(none)* | `agent_type` | Infer from purpose |

### From Legacy Formats

When migrating from older agent formats:

1. **Field Mapping**: Map old field names to new schema structure
2. **Structure Changes**: Move flat fields into nested objects (`metadata`, `capabilities`)
3. **Validation**: Ensure all new required fields are present
4. **Testing**: Validate migrated agents load correctly

### Version Upgrades

When upgrading schema versions:

1. **Backward Compatibility**: Older versions may still load but miss new features
2. **New Fields**: Add any newly required fields
3. **Deprecated Fields**: Remove or replace deprecated fields
4. **Validation Updates**: Re-validate against new schema

### Format Conversions

**Claude Code to Claude MPM:**
```bash
# Automated conversion
./claude-mpm agents convert --from claude-code --to claude-mpm --input-dir .claude/agents/

# Manual conversion steps:
1. Add schema_version: "1.2.0"
2. Convert name → metadata.name and agent_id  
3. Convert flat fields → nested objects
4. Add required Claude MPM fields
5. Validate with extended schema
```

**Claude MPM to Claude Code (for compatibility):**
```bash  
# Create simplified versions for Anthropic tools
./claude-mpm agents convert --from claude-mpm --to claude-code --simplify

# Manual simplification:
1. Extract name from metadata.name
2. Extract description from metadata.description  
3. Flatten capabilities.tools to tools
4. Convert model ID to tier name
5. Remove Claude MPM-specific fields
6. Validate with Claude Code schema
```

### Dual-Format Maintenance

**Best Practices for Maintaining Both Formats:**

1. **Source of Truth**: Choose Claude MPM as primary, generate Claude Code versions
2. **Naming Convention**: Use consistent prefixes: `agent_name.claude` and `agent_name.claude-mpm`
3. **Automation**: Use conversion tools to keep formats synchronized
4. **Testing**: Validate both formats work in their respective environments
5. **Documentation**: Document format-specific features and limitations

**Directory Structure:**
```
.claude-mpm/agents/
├── primary_agents/           # Primary Claude MPM agents
│   ├── engineer.claude-mpm
│   ├── qa.claude-mpm  
│   └── docs.claude-mpm
├── claude_code_compatibility/ # Auto-generated Claude Code versions
│   ├── engineer.claude
│   ├── qa.claude
│   └── docs.claude
└── README.md                 # Format usage documentation
```

## JSON to Markdown Conversion Details

### Automatic Deployment Process

Claude MPM automatically handles the conversion from JSON (Claude MPM format) to Markdown (Claude Code format):

```
.claude-mpm/agents/engineer.json  →  .claude/agents/engineer.md
      (SOURCE - JSON)                    (DEPLOYED - Markdown)
```

### Field Mapping During Conversion

When converting from JSON to Markdown, Claude MPM maps fields as follows:

| JSON Structure | Markdown Frontmatter | Conversion Notes |
|----------------|---------------------|------------------|
| `metadata.name` | `name` | Direct mapping |
| `metadata.description` | `description` | Direct mapping |
| `agent_version` | `version` | Semantic version string |
| `capabilities.tools` | `tools` | Array format preserved |
| `capabilities.model` | `model` | May convert full model ID to tier |
| `capabilities.resource_tier` | `resource_tier` | Direct mapping |
| `capabilities.temperature` | `temperature` | Numeric value |
| `capabilities.network_access` | `network_access` | Boolean value |
| `instructions` | (content) | Becomes markdown body content |

### Conversion Example

**Source JSON** (`.claude-mpm/agents/engineer.json`):
```json
{
  "agent_id": "engineer",
  "agent_version": "2.0.0",
  "metadata": {
    "name": "Project Engineer",
    "description": "Custom engineering agent with project knowledge",
    "tags": ["engineering", "project-specific"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Write", "Edit", "Bash"],
    "resource_tier": "standard",
    "temperature": 0.3,
    "network_access": true
  },
  "instructions": "# Project Engineer Agent\n\nYou are a specialized engineering agent for this project.\n\n## Guidelines\n- Follow project conventions\n- Use project-specific tools"
}
```

**Generated Markdown** (`.claude/agents/engineer.md`):
```markdown
---
name: Project Engineer
description: Custom engineering agent with project knowledge
version: 2.0.0
tools:
  - Read
  - Write
  - Edit
  - Bash
model: sonnet
resource_tier: standard
temperature: 0.3
network_access: true
---

# Project Engineer Agent

You are a specialized engineering agent for this project.

## Guidelines
- Follow project conventions
- Use project-specific tools
```

### Best Practices for Conversion

1. **Single Source of Truth**: Always edit JSON files in `.claude-mpm/agents/`
2. **Don't Edit Generated Files**: Markdown files in `.claude/agents/` are auto-generated
3. **Version Control**: Track JSON sources, ignore generated Markdown files
4. **Test After Changes**: Verify JSON agents before deployment converts them
5. **Field Validation**: Ensure JSON fields are valid before conversion

### Deployment Commands

```bash
# Deploy agents (converts JSON to Markdown)
claude-mpm agents deploy

# Force redeploy all agents
claude-mpm agents force-deploy

# Clean deployed agents (remove generated Markdown files)
claude-mpm agents clean
```

This documentation provides a comprehensive reference for all agent frontmatter fields and their usage across different formats in Claude MPM, with full consideration for Claude Code compatibility, JSON to Markdown conversion, and migration paths.