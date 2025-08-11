# Agent Schema Documentation

This document preserves the inline documentation from the agent_schema.json file. The JSON Schema itself must remain comment-free for proper parsing.

## Schema Version 1.2.0

### Required Fields

- **schema_version**: Must match the schema version this agent was built for
- **agent_id**: Unique identifier for the agent type
- **agent_version**: Semantic version of this specific agent template
- **agent_type**: Categorizes the agent's primary function
- **metadata**: Human-readable information about the agent
- **capabilities**: Technical specifications and resource requirements
- **instructions**: System prompt that defines agent behavior

### Field Descriptions

#### schema_version
- **Pattern**: `^\d+\.\d+\.\d+$` (Enforces semantic versioning format X.Y.Z)
- **Description**: Schema version for the agent template format. This ensures compatibility between the agent template and the schema validator. Must be updated when breaking changes are made to the schema.
- **Examples**: "1.0.0", "1.2.0"

#### agent_id
- **Pattern**: `^[a-z][a-z0-9_]*$` (Must start with lowercase letter, followed by lowercase letters, numbers, or underscores)
- **Description**: Unique agent identifier used for agent discovery and loading. This ID must be unique across all agents in the system and follows snake_case naming convention.
- **Examples**: "research_agent", "engineer_agent", "qa_agent", "security_agent"

#### agent_version
- **Pattern**: `^\d+\.\d+\.\d+$` (Enforces semantic versioning for agent templates)
- **Description**: Semantic version of the agent template itself (not the schema). Increment major for breaking changes, minor for new features, patch for bug fixes.
- **Examples**: "1.0.0", "2.1.3"

#### agent_type
- **Description**: Type of agent that determines its primary function and default capabilities. This categorization helps in agent discovery and capability matching.
- **Enum values**:
  - `base`: Generic agent with no specialization
  - `engineer`: Code implementation and development
  - `qa`: Quality assurance and testing
  - `documentation`: Documentation creation and maintenance
  - `research`: Code analysis and research
  - `security`: Security analysis and vulnerability detection
  - `ops`: Operations and infrastructure management
  - `data_engineer`: Data pipeline and ETL development
  - `version_control`: Git and version control operations

### Metadata Object

#### Required metadata fields:
- **name**: Human-readable name for UI display
- **description**: Brief explanation of agent's purpose
- **tags**: Searchable tags for agent discovery

#### Metadata field constraints:
- **name**: 
  - minLength: 3 (Minimum 3 characters for meaningful names)
  - maxLength: 50 (Maximum 50 characters to prevent UI overflow)
- **description**:
  - minLength: 10 (Minimum 10 characters to ensure meaningful descriptions)
  - maxLength: 200 (Maximum 200 characters for conciseness)
- **tags**:
  - Pattern: `^[a-z][a-z0-9-]*$` (Lowercase letters, numbers, and hyphens only)
  - minItems: 1 (At least one tag required for discovery)
  - maxItems: 10 (Maximum 10 tags to prevent over-tagging)
  - uniqueItems: true (No duplicate tags allowed)

### Capabilities Object

#### Required capabilities fields:
- **model**: Claude model version to use
- **tools**: Array of allowed tools for the agent
- **resource_tier**: Resource allocation category

#### Model Options
Available Claude models grouped by performance tier:

**Haiku models** (fastest, most cost-effective):
- claude-3-haiku-20240307
- claude-3-5-haiku-20241022

**Sonnet models** (balanced performance):
- claude-3-sonnet-20240229
- claude-3-5-sonnet-20241022
- claude-3-5-sonnet-20240620
- claude-sonnet-4-20250514
- claude-4-sonnet-20250514

**Opus models** (highest capability):
- claude-3-opus-20240229
- claude-opus-4-20250514
- claude-4-opus-20250514

#### Available Tools
Tools are grouped by functionality:

**File operations**:
- `Read`: Read file contents
- `Write`: Write new files
- `Edit`: Edit existing files
- `MultiEdit`: Multiple edits in one operation

**Search and navigation**:
- `Grep`: Search file contents
- `Glob`: Find files by pattern
- `LS`: List directory contents

**System operations**:
- `Bash`: Execute shell commands

**Web operations**:
- `WebSearch`: Search the web
- `WebFetch`: Fetch web content

**Notebook operations**:
- `NotebookRead`: Read Jupyter notebooks
- `NotebookEdit`: Edit Jupyter notebooks

**Workflow operations**:
- `TodoWrite`: Manage task lists
- `ExitPlanMode`: Exit planning mode

**CLI tools** (future expansion):
- `git`: Git operations
- `docker`: Docker commands
- `kubectl`: Kubernetes operations
- `terraform`: Infrastructure as code
- `aws`: AWS CLI
- `gcloud`: Google Cloud CLI
- `azure`: Azure CLI

#### Resource Tiers
Resource allocation tiers determine memory, CPU, and timeout limits:

- **basic**: Default resources for simple tasks
- **standard**: Medium resources for typical operations
- **intensive**: High resources for complex tasks
- **lightweight**: Minimal resources for quick operations

#### Capability Constraints

**max_tokens**:
- minimum: 1000 (Minimum for meaningful responses)
- maximum: 200000 (Maximum supported by Claude models)
- default: 8192 (Default suitable for most tasks)

**temperature**:
- minimum: 0 (0 = deterministic, focused)
- maximum: 1 (1 = creative, varied)
- default: 0.7 (Balanced default)

**timeout**:
- minimum: 30 (Minimum 30 seconds for basic operations)
- maximum: 3600 (Maximum 1 hour for long-running tasks)
- default: 300 (Default 5 minutes)

### Instructions Field
- **minLength**: 100 (Minimum to ensure meaningful instructions)
- **maxLength**: 8000 (Maximum to fit within context limits)
- **Description**: Agent system instructions that define behavior, approach, and constraints. This becomes the agent's system prompt.

### Additional Properties
- **additionalProperties**: false (Strict validation - no extra properties allowed)

## Resource Tier Definitions

These definitions provide guidance for resource allocation (not enforced by schema but used by runtime):

### Intensive Tier
- memory_limit: 4096-8192 MB
- cpu_limit: 60-100%
- timeout: 600-3600 seconds

### Standard Tier
- memory_limit: 2048-4096 MB
- cpu_limit: 30-60%
- timeout: 300-1200 seconds

### Lightweight Tier
- memory_limit: 512-2048 MB
- cpu_limit: 10-30%
- timeout: 30-600 seconds