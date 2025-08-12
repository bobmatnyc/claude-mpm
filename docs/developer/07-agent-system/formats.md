# Agent File Formats Documentation

This document provides comprehensive documentation for all agent file formats supported by Claude MPM, including **Anthropic's Claude Code format** (.claude) and **Claude MPM's extended format** (.claude-mpm), with format detection logic and precedence system.

## Table of Contents

1. [Overview](#overview)
2. [JSON Format (v1.2.0 Schema)](#json-format-v120-schema)
3. [Markdown with YAML Frontmatter (.claude Format)](#markdown-with-yaml-frontmatter-claude-format)
4. [Markdown with YAML Frontmatter (.claude-mpm Format)](#markdown-with-yaml-frontmatter-claude-mpm-format)
5. [Format Detection Logic](#format-detection-logic)
6. [Precedence System](#precedence-system)
7. [Migration Between Formats](#migration-between-formats)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

Claude MPM supports multiple agent file formats representing **two distinct agent standards**:

### Agent Standards
1. **Anthropic's Claude Code Format** - Official format for Claude Desktop and IDE tools
2. **Claude MPM Format** - Extended format with advanced project capabilities

### File Format Implementations
1. **JSON Format (.json)**: Claude MPM's native structured format with full schema validation
2. **Claude Code Format (.claude)**: Anthropic's official standard for Desktop/IDE integration
3. **Claude MPM Markdown (.claude-mpm)**: Extended markdown with enhanced metadata

All formats coexist seamlessly, with automatic format detection and appropriate validation for each standard.

### Supported File Extensions

| Format | Extensions | Standard | Primary Use Case |
|--------|------------|----------|------------------|
| JSON | `.json` | Claude MPM | Structured configurations, API generation |
| Claude Code | `.claude`, `.md`* | Anthropic | Claude Desktop/IDE integration |  
| Claude MPM Markdown | `.claude-mpm` | Claude MPM | Enhanced project-specific agents |

*`.md` files follow Claude Code standard when they contain simple frontmatter; Claude MPM standard when they contain `schema_version`*

## JSON Format (Claude MPM Standard)

The JSON format represents **Claude MPM's native agent format** with comprehensive structure and full schema validation. This format provides the most extensive capabilities and is the foundation for Claude MPM's advanced features.

### Structure

```json
{
  "schema_version": "1.2.0",
  "agent_id": "agent_identifier",
  "agent_version": "1.0.0",
  "agent_type": "engineer",
  "metadata": {
    "name": "Human Readable Name",
    "description": "Brief agent description",
    "category": "engineering",
    "tags": ["tag1", "tag2"],
    "author": "Author Name",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-20T14:45:00Z"
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Write", "Edit"],
    "resource_tier": "standard",
    "max_tokens": 8192,
    "temperature": 0.7,
    "timeout": 600,
    "memory_limit": 2048,
    "cpu_limit": 40,
    "network_access": true,
    "file_access": {
      "read_paths": ["./src", "./docs"],
      "write_paths": ["./src", "./tests"]
    }
  },
  "knowledge": {
    "domain_expertise": ["software-engineering", "testing"],
    "best_practices": ["Clean code principles", "TDD methodology"],
    "constraints": ["Must follow coding standards"],
    "examples": [
      {
        "scenario": "Bug fix request",
        "approach": "Identify, test, fix, verify"
      }
    ]
  },
  "interactions": {
    "input_format": {
      "required_fields": ["task_description"],
      "optional_fields": ["context", "constraints"]
    },
    "output_format": {
      "structure": "markdown",
      "includes": ["analysis", "code_changes", "tests"]
    },
    "handoff_agents": ["qa_agent", "security_agent"],
    "triggers": [
      {
        "condition": "security_issue_detected",
        "action": "handoff_to_security_agent"
      }
    ]
  },
  "testing": {
    "test_cases": [
      {
        "name": "Basic functionality",
        "input": "Fix authentication bug",
        "expected_behavior": "Identifies and fixes bug with tests",
        "validation_criteria": ["bug_fixed", "tests_added", "documentation_updated"]
      }
    ],
    "performance_benchmarks": {
      "response_time": 300,
      "token_usage": 8192,
      "success_rate": 0.95
    }
  },
  "hooks": {
    "pre_execution": [
      {"name": "security_scan", "enabled": true}
    ],
    "post_execution": [
      {"name": "quality_check", "enabled": true}
    ]
  },
  "instructions": "# Agent Instructions\n\nDetailed system instructions for the agent..."
}
```

### Key Features

- **Full Schema Validation**: Complete v1.2.0 schema compliance
- **Rich Metadata**: Comprehensive agent information
- **Advanced Configuration**: All optional fields supported
- **Structured Testing**: Built-in test case definitions
- **Hook Integration**: Pre/post execution hooks

### Use Cases

- Complex enterprise agents with extensive configuration
- Agents requiring full metadata and testing specifications
- API-generated or programmatically managed agents
- Agents with advanced security and resource constraints

## Claude Code Format (Anthropic Standard)

The `.claude` format follows **Anthropic's Claude Code standard** and is optimized for Claude Desktop integration and human readability. This is the official format used by Anthropic's development tools and IDE extensions.

### Structure

```markdown
---
name: documentation
description: Documentation creation and maintenance
version: 1.3.0
base_version: 0.3.0
author: claude-mpm
tools: Read, Write, Edit, MultiEdit, Grep, Glob, LS, WebSearch, TodoWrite
model: sonnet
resource_tier: lightweight
temperature: 0.2
network_access: true
capabilities:
  - technical_writing
  - api_documentation
  - user_guides
constraints:
  - follow_style_guide
  - maintain_consistency
---

# Documentation Agent

Create comprehensive, clear documentation following established standards. Focus on user-friendly content and technical accuracy.

## Documentation Protocol
1. **Content Structure**: Organize information logically with clear hierarchies
2. **Technical Accuracy**: Ensure documentation reflects actual implementation
3. **User Focus**: Write for target audience with appropriate technical depth
4. **Consistency**: Maintain standards across all documentation assets

## Documentation Focus
- API documentation with examples and usage patterns
- User guides with step-by-step instructions
- Technical specifications and architectural decisions

[... rest of agent instructions ...]
```

### Key Features (Anthropic Standard)

- **Official Anthropic Format**: Direct compatibility with Claude Desktop and IDE tools
- **Human-Readable**: Clean markdown format optimized for developers
- **Simplified Metadata**: Minimal required fields for rapid development
- **Flexible Tools**: String or array format as per Anthropic specification
- **Model Tier Names**: Uses Anthropic's tier naming (`sonnet`, `opus`, `haiku`)

### Frontmatter Fields (Anthropic Standard)

**Core Required Fields (per Anthropic specification):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Agent identifier (kebab-case) |
| `description` | string | ✅ | Brief natural language description |

**Optional Fields (Anthropic standard + community extensions):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tools` | string/array | ❌ | Available tools (comma-separated string or array) |
| `model` | string | ❌ | Model tier (`sonnet`, `opus`, `haiku`) |

**Claude MPM Extensions (when used in Claude MPM context):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | ❌ | Agent version (for Claude MPM compatibility) |
| `resource_tier` | string | ❌ | Resource allocation tier |
| `temperature` | number | ❌ | Model temperature setting |
| `network_access` | boolean | ❌ | Network permissions flag |

### Use Cases (Anthropic Standard)

- **Primary**: Claude Desktop and IDE extension development
- **Compatibility**: Integration with Anthropic developer tools  
- **Development**: Quick prototyping with minimal configuration
- **Personal**: Individual productivity and helper agents
- **Community**: Sharing agents in Anthropic ecosystem

## Claude MPM Markdown Format (.claude-mpm)

The `.claude-mpm` format follows **Claude MPM's extended standard** with enhanced metadata and full schema support. This format bridges human readability with comprehensive agent capabilities.

### Structure

```markdown
---
schema_version: "1.2.0"
agent_id: advanced_engineer
agent_version: "2.1.0"
agent_type: engineer
metadata:
  name: Advanced Engineering Agent
  description: Full-featured engineering agent with comprehensive capabilities
  category: engineering
  tags:
    - engineering
    - full-stack
    - advanced
  author: Engineering Team
  created_at: "2025-01-15T10:30:00Z"
capabilities:
  model: claude-sonnet-4-20250514
  tools:
    - Read
    - Write
    - Edit
    - MultiEdit
    - Grep
    - Bash
    - git
  resource_tier: standard
  max_tokens: 16384
  temperature: 0.3
  network_access: true
  file_access:
    read_paths: ["./"]
    write_paths: ["./src", "./tests"]
knowledge:
  domain_expertise:
    - software-engineering
    - system-architecture
    - devops
  best_practices:
    - Clean architecture principles
    - Test-driven development
    - Security-first approach
interactions:
  output_format:
    structure: markdown
    includes:
      - analysis
      - implementation
      - testing
  handoff_agents:
    - qa_agent
    - security_agent
---

# Advanced Engineering Agent

You are an expert software engineer with comprehensive knowledge of modern development practices, system architecture, and engineering best practices.

## Core Competencies

- **Architecture Design**: Microservices, event-driven architecture, domain modeling
- **Development Practices**: TDD, CI/CD, code review, pair programming
- **Technology Stack**: Full-stack development across multiple languages and frameworks
- **System Operations**: DevOps, monitoring, performance optimization

## Approach

1. **Analysis First**: Thoroughly understand requirements and constraints
2. **Design Thinking**: Consider multiple approaches and trade-offs
3. **Implementation**: Write clean, maintainable, well-tested code
4. **Documentation**: Provide clear explanations and documentation
5. **Quality Assurance**: Ensure robust testing and validation

[... detailed agent instructions ...]
```

### Key Features (Claude MPM Standard)

- **Complete Claude MPM Features**: Full v1.2.0 schema support with all advanced capabilities
- **Rich Metadata**: Comprehensive agent information, categorization, and versioning
- **Human-Readable**: Maintains markdown readability while providing full configuration
- **Project-Optimized**: Designed for team and enterprise deployment scenarios
- **Extensible**: Supports hooks, testing frameworks, and resource management

### Extended Fields

Beyond basic frontmatter, the `.claude-mpm` format supports:

- **Complete Metadata**: All metadata fields from JSON schema
- **Advanced Capabilities**: Full capabilities object
- **Knowledge Structure**: Organized domain expertise and constraints
- **Interaction Patterns**: Input/output format specifications
- **Testing Integration**: Test cases and benchmarks (optional)
- **Hook Configuration**: Pre/post execution hooks (optional)

### Use Cases

- Project-specific agents with comprehensive configuration
- Enterprise deployments requiring full metadata
- Agents with complex capability requirements
- Integration with advanced Claude MPM features

## Format Detection Logic

Claude MPM automatically detects agent file formats and applies the appropriate **standard validation** (Anthropic Claude Code vs Claude MPM) based on file characteristics.

### Standard Detection Strategy

The system determines which **agent standard** to apply:

1. **Claude Code Standard** (Anthropic):
   - `.claude` file extension
   - `.md` files with simple frontmatter (no `schema_version`)
   - Basic required fields: `name`, `description`

2. **Claude MPM Standard** (Extended):
   - `.claude-mpm` file extension  
   - `.json` file extension
   - `.md` files with `schema_version` in frontmatter
   - Full schema validation with extended metadata

### File Extension Based Detection

1. **`.json` files**: Claude MPM format with full JSON schema validation
2. **`.claude` files**: Anthropic Claude Code format with basic validation
3. **`.claude-mpm` files**: Claude MPM enhanced markdown format  
4. **`.md` files**: Content-based standard detection:
   - Contains `schema_version` → Claude MPM standard
   - Simple frontmatter only → Claude Code standard
   - No frontmatter → Plain markdown instructions

### Content-Based Standard Detection

For `.md` files, the system examines frontmatter to determine which standard to apply:

```python
# Simplified standard detection logic
def detect_agent_standard(file_path: Path, content: str) -> str:
    if file_path.suffix == '.json':
        return 'claude-mpm'
    elif file_path.suffix == '.claude':
        return 'claude-code'  # Always Anthropic standard
    elif file_path.suffix == '.claude-mpm':
        return 'claude-mpm'  # Always Claude MPM standard
    elif content.strip().startswith('---'):
        # Analyze frontmatter to determine standard
        if 'schema_version' in content:
            return 'claude-mpm'  # Extended Claude MPM standard
        elif has_simple_frontmatter(content):
            return 'claude-code'  # Anthropic standard
        else:
            return 'claude-mpm'  # Default to Claude MPM for complex frontmatter
    else:
        return 'plain_markdown'

def has_simple_frontmatter(content: str) -> bool:
    """Detect if frontmatter matches Anthropic's simple Claude Code format"""
    frontmatter = extract_frontmatter(content)
    required_fields = {'name', 'description'}
    optional_fields = {'tools', 'model', 'version'}
    
    frontmatter_fields = set(frontmatter.keys())
    extra_fields = frontmatter_fields - required_fields - optional_fields
    
    # Simple if only uses Anthropic standard fields
    return len(extra_fields) == 0
```

### Standard-Specific Validation

Based on detected standard:

**Claude Code Standard (Anthropic)**:
- Basic YAML syntax validation
- Required fields: `name`, `description`  
- Optional fields: `tools`, `model`
- Lenient validation following Anthropic specification

**Claude MPM Standard (Extended)**:
- Full JSON Schema v1.2.0 validation
- Complete metadata requirements
- Structured capability definitions  
- Advanced resource and testing constraints

## Precedence System

When multiple agent files exist for the same agent, the system follows these precedence rules:

### Tier-Based Precedence

1. **PROJECT tier**: `.claude-mpm/agents/`
2. **USER tier**: `~/.claude-mpm/agents/`
3. **SYSTEM tier**: Framework built-in agents

### Format-Based Precedence (within same tier)

Precedence follows capability and specificity order:

1. **Claude MPM JSON** (`.json`) - Most comprehensive format
2. **Claude MPM Markdown** (`.claude-mpm`) - Extended markdown format
3. **Anthropic Claude Code** (`.claude`) - Official Anthropic format
4. **Generic Markdown** (`.md` with frontmatter) - Detected by content analysis

### Naming Convention Precedence

For the same format and tier:

1. `agent_name.ext` (exact match)
2. `agent_name_agent.ext` (with suffix)
3. `agent_name-agent.ext` (with hyphen suffix)

### Resolution Example

Given these files in a PROJECT tier directory:

```
.claude-mpm/agents/
├── engineer.json           # Priority 1
├── engineer.claude-mpm     # Priority 2
├── engineer.md            # Priority 3
├── engineer_agent.json    # Priority 4
└── engineer-agent.yaml    # Priority 5
```

The system loads `engineer.json` as it has the highest precedence.

## Migration Between Formats

### JSON to Markdown

Convert structured JSON to human-readable markdown:

```python
# Example conversion
json_agent = {
    "agent_id": "example",
    "metadata": {"name": "Example Agent"},
    "instructions": "Agent instructions..."
}

# Becomes markdown with frontmatter:
markdown_content = f"""---
name: {json_agent['metadata']['name']}
version: {json_agent.get('agent_version', '1.0.0')}
---

{json_agent['instructions']}
"""
```

### Markdown to JSON

Convert markdown with frontmatter to structured JSON:

```python
# Parse frontmatter and content
frontmatter, content = parse_markdown_frontmatter(markdown_content)

# Convert to JSON structure
json_agent = {
    "schema_version": "1.2.0",
    "agent_id": frontmatter.get('name', 'unnamed'),
    "agent_version": frontmatter.get('version', '1.0.0'),
    "metadata": {
        "name": frontmatter.get('name', ''),
        "description": frontmatter.get('description', ''),
        "tags": frontmatter.get('tags', [])
    },
    "capabilities": {
        "model": map_model_name(frontmatter.get('model', 'sonnet')),
        "tools": parse_tools(frontmatter.get('tools', [])),
        "resource_tier": frontmatter.get('resource_tier', 'standard')
    },
    "instructions": content
}
```

### Field Mapping

Common field mappings between formats:

| Claude Format | JSON Format | Description |
|---------------|-------------|-------------|
| `name` | `metadata.name` | Agent name |
| `description` | `metadata.description` | Description |
| `version` | `agent_version` | Version number |
| `tools` | `capabilities.tools` | Available tools |
| `model` | `capabilities.model` | Model identifier |
| `resource_tier` | `capabilities.resource_tier` | Resource allocation |

## Best Practices

### Format Selection Guidelines

**Standard-Based Selection:**

**Choose Claude Code Standard (Anthropic) when:**
- Primary use is Claude Desktop or IDE extensions
- Need maximum compatibility with Anthropic tooling  
- Creating simple, lightweight agents
- Rapid prototyping with minimal configuration
- Sharing in Anthropic developer community

**Choose Claude MPM Standard (Extended) when:**
- Building production or enterprise agents
- Need advanced resource management and testing
- Require comprehensive metadata and validation
- Using Claude MPM's hook system and extensibility
- Deploying project-specific agent teams

**Format Implementation Selection:**

**Use Claude Code (.claude) when:**
- Following Anthropic standard for maximum compatibility
- Human-authored agents for Claude Desktop
- Simple configuration with essential fields only

**Use Claude MPM JSON (.json) when:**
- Creating complex agents with full feature set
- API-generated or programmatically managed agents
- Need complete schema validation and metadata
- Enterprise deployments with strict validation

**Use Claude MPM Markdown (.claude-mpm) when:**
- Want Claude MPM features but prefer readable format
- Team development with markdown-friendly workflows
- Balancing advanced capabilities with human readability
- Project-specific agents with comprehensive configuration

### File Organization

**Standard-Aware Directory Structure:**

```
project-root/
├── .claude-mpm/agents/            # Claude MPM agents (primary)
│   ├── engineer.json              # Claude MPM JSON format
│   ├── researcher.claude-mpm      # Claude MPM markdown format
│   └── qa.claude-mpm              # Claude MPM markdown format
├── .claude/agents/                # Claude Code agents (compatibility)  
│   ├── simple-helper.claude       # Anthropic Claude Code format
│   ├── code-reviewer.claude       # Anthropic Claude Code format
│   └── docs-generator.md          # Generic markdown (auto-detected)
└── scripts/
    └── sync_agent_formats.sh      # Format synchronization utility
```

**Mixed Standard Strategy:**
- Use Claude MPM for primary development and advanced features
- Maintain Claude Code versions for Anthropic tool compatibility  
- Use automated conversion to keep formats synchronized
- Document which standard each agent follows

### Version Control

**Include in repository:**
- Agent definition files
- Configuration files
- Documentation

**Exclude from repository:**
- Generated cache files
- Runtime logs
- Temporary files

```gitignore
# Include agent definitions
!.claude-mpm/agents/
!.claude-mpm/config/

# Exclude runtime files
.claude-mpm/cache/
.claude-mpm/logs/
.claude-mpm/temp/
```

### Naming Conventions

**File naming:**
- Use lowercase with underscores: `data_engineer.json`
- Be descriptive: `payment_processor.claude-mpm`
- Avoid reserved names: Don't use system agent names

**Agent IDs:**
- Follow pattern: `^[a-z][a-z0-9_]*$`
- Be consistent: `data_engineer_agent` or `data_engineer`
- Use semantic versioning: `1.0.0`, `2.1.3`

## Troubleshooting

### Common Issues

#### 1. Format Detection Failures

**Symptoms**: Agent not loading, format detection errors

**Solutions**:
- Verify file extension matches content format
- Check YAML frontmatter syntax
- Ensure JSON is valid
- Validate schema version if present

#### 2. Precedence Conflicts

**Symptoms**: Wrong agent version loading

**Solutions**:
- Check tier precedence (PROJECT > USER > SYSTEM)
- Verify format precedence within tier
- Use `claude-mpm agents list --by-tier` to debug
- Remove conflicting files if needed

#### 3. Schema Validation Errors

**Symptoms**: Agent loads but validation fails

**Solutions**:
- Validate required fields are present
- Check field types match schema
- Verify enum values are correct
- Use schema validation tools

#### 4. Migration Issues

**Symptoms**: Converted agents don't work properly

**Solutions**:
- Verify field mapping completeness
- Check instruction content preservation
- Validate converted format syntax
- Test loaded agent functionality

### Debugging Tools

#### Format Detection Test

```bash
# Test format detection
python -c "
from claude_mpm.agents.agent_loader import _get_loader
loader = _get_loader()
# Test detection logic on specific file
"
```

#### Agent Loading Verification

```bash
# Verify agent loads correctly
./claude-mpm agents list --by-tier
./claude-mpm agents validate <agent_name>
```

#### Schema Validation

```python
from claude_mpm.validation.agent_validator import AgentValidator

validator = AgentValidator()
result = validator.validate_file(Path('agent.json'))
print(f"Valid: {result.is_valid}")
if not result.is_valid:
    print(f"Errors: {result.errors}")
```

## Deployment Process (JSON → Markdown)

### Automatic Conversion

Claude MPM automatically converts JSON agents to Markdown during deployment:

1. **Source**: `.claude-mpm/agents/*.json` (Claude MPM format)
2. **Target**: `.claude/agents/*.md` (Claude Code format)
3. **Process**: Automatic conversion during agent loading/deployment
4. **Mapping**: JSON structure → YAML frontmatter + Markdown instructions

### Conversion Details

**JSON to Markdown Field Mapping:**

| JSON Field | Markdown Frontmatter | Notes |
|------------|---------------------|--------|
| `metadata.name` | `name` | Direct mapping |
| `metadata.description` | `description` | Direct mapping |
| `capabilities.tools` | `tools` | Array format preserved |
| `capabilities.model` | `model` | Model ID or tier name |
| `agent_version` | `version` | Semantic version |
| `capabilities.resource_tier` | `resource_tier` | Resource allocation |
| `instructions` | (content) | Becomes markdown body |

**Example Conversion:**

```json
// .claude-mpm/agents/engineer.json (SOURCE)
{
  "agent_id": "engineer",
  "version": "2.0.0",
  "metadata": {
    "name": "Project Engineer",
    "description": "Custom engineering agent"
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Write", "Edit"],
    "resource_tier": "standard"
  },
  "instructions": "# Engineer Agent\n\nYou are a specialized engineer..."
}
```

```markdown
<!-- .claude/agents/engineer.md (GENERATED) -->
---
name: Project Engineer
description: Custom engineering agent
version: 2.0.0
tools:
  - Read
  - Write
  - Edit
model: sonnet
resource_tier: standard
---

# Engineer Agent

You are a specialized engineer...
```

### Best Practices for Deployment

1. **Source Control**: Only track `.claude-mpm/agents/*.json` files
2. **Ignore Generated Files**: Add `.claude/agents/` to `.gitignore`
3. **Don't Edit Generated Files**: Changes will be lost on next deployment
4. **Test Sources**: Validate JSON agents before deployment
5. **Verify Deployment**: Check generated Markdown files for correctness

This documentation provides comprehensive guidance for working with location-based agent file formats in Claude MPM, ensuring proper format selection, deployment, and troubleshooting.