# Claude MPM Agent System

This document provides comprehensive guidance on using and managing agents in Claude MPM, with a focus on the local agent deployment feature that allows projects to define custom agents with precedence over system defaults.

## Documentation Structure

This document serves as the main index for agent documentation. For detailed information on specific topics, see the dedicated documentation sections:

### Developer Documentation

- **[Agent Frontmatter](developer/agents/frontmatter.md)** - Complete frontmatter field documentation for all formats
- **[Agent Formats](developer/agents/formats.md)** - Comprehensive format documentation (JSON, .claude, .claude-mpm)
- **[Agent Schema](developer/agents/schema.md)** - Schema documentation covering v1.1.0 and v1.2.0 specifications
- **[Agent Creation Guide](developer/agents/creation-guide.md)** - Step-by-step guide with practical examples and best practices
- **[Research Agent Improvements](developer/07-agent-system/research-agent-improvements.md)** - v4.0.0 critical search failure fixes and quality improvements

### Quick Reference

| Topic | Documentation | Description |
|-------|---------------|-------------|
| **Getting Started** | [Creation Guide](developer/agents/creation-guide.md#getting-started) | Quick start and prerequisites |
| **Format Selection** | [Formats Guide](developer/agents/formats.md#format-selection-guidelines) | Choose the right format for your needs |
| **Field Reference** | [Frontmatter Docs](developer/agents/frontmatter.md) | Complete field documentation |
| **Schema Migration** | [Schema Docs](developer/agents/schema.md#migration-guide) | Migrate between schema versions |
| **Troubleshooting** | [Creation Guide](developer/agents/creation-guide.md#debugging-common-issues) | Common issues and solutions |

## Table of Contents

1. [Overview](#overview)
2. [Agent Tier System](#agent-tier-system)
3. [Creating Local Agents](#creating-local-agents)
4. [Agent File Formats](#agent-file-formats)
5. [Agent Discovery and Caching](#agent-discovery-and-caching)
6. [CLI Agent Management](#cli-agent-management)
7. [Environment Configuration](#environment-configuration)
8. [API Reference](#api-reference)
9. [Best Practices](#best-practices)
10. [Migration Guide](#migration-guide)
11. [Troubleshooting](#troubleshooting)

## Overview

Claude MPM's agent system provides a flexible framework for defining AI assistant behaviors through structured templates. The system includes 15 specialized agents covering development, operations, web development, project management, and code quality, with a three-tier precedence system that allows for project-specific customization.

### Available Agents

Claude MPM includes 15 specialized agents:

#### Core Development
- **Engineer** - Software development and implementation
- **Research** - Code analysis and research  
- **Documentation** - Documentation creation and maintenance
- **QA** - Testing and quality assurance
- **Security** - Security analysis and implementation

#### Operations & Infrastructure
- **Ops** - Operations and deployment
- **Version Control** - Git and version management
- **Data Engineer** - Data pipeline and ETL development

#### Web Development
- **Web UI** - Frontend and UI development
- **Web QA** - Web testing and E2E validation

#### Project Management
- **Ticketing** - Issue tracking and management
- **Project Organizer** - File organization and structure
- **Memory Manager** - Project memory and context management

#### Code Quality
- **Refactoring Engineer** - Code refactoring and optimization
- **Code Analyzer** - Static code analysis with AST and tree-sitter

**Important**: Project agents in `.claude-mpm/agents/` support **multiple formats** (.json, .yaml, .yml, .md) for flexibility. During deployment, agents are automatically converted to Markdown format with YAML frontmatter and placed in `.claude/agents/` for Claude Code compatibility.

### Key Features

- **Three-tier precedence**: PROJECT > USER > SYSTEM
- **Hot-reload capability**: Changes detected automatically
- **Multiple formats**: Supports `.md`, `.json`, and `.yaml` files
- **Schema validation**: Ensures consistency and correctness
- **Project-level customization**: Override system agents with project-specific implementations
- **Intelligent caching**: Performance optimization with cache invalidation
- **Dynamic model selection**: Task complexity-based model assignment

## Agent Tier System

The agent system implements a hierarchical precedence model with three distinct tiers:

### 1. PROJECT Tier (Highest Precedence)
- **Location**: `.claude-mpm/agents/` in current project directory
- **Scope**: Project-specific agents and overrides
- **Use Cases**:
  - Override system agents with project-specific knowledge
  - Add domain-specific agents for specialized workflows
  - Test new agent configurations before promoting to user/system level
  - Maintain project-specific agent versions for consistency

### 2. USER Tier (Medium Precedence)
- **Location**: `~/.claude-mpm/agents/` in user home directory
- **Scope**: User-level customizations across all projects
- **Use Cases**:
  - Personal preferences and workflow customizations
  - User-specific agent modifications
  - Cross-project agent templates

### 3. SYSTEM Tier (Lowest Precedence)
- **Location**: `src/claude_mpm/agents/templates/` in framework installation (system agents)
- **Scope**: Framework built-in agents maintained by developers
- **Use Cases**:
  - Default agent behaviors
  - Fallback when no higher-tier agent exists
  - Reference implementations

### Precedence Resolution

When multiple agents with the same name exist across tiers:

```
PROJECT/engineer.md → Overrides USER/engineer.json → Overrides SYSTEM/engineer.json
```

This allows projects to incrementally customize agents while maintaining fallbacks.

## Creating Local Agents

### Quick Start

Create a project-specific agent in 3 steps:

```bash
# 1. Create the directory
mkdir -p .claude-mpm/agents

# 2. Create an agent file
cat > .claude-mpm/agents/engineer.md << 'EOF'
---
description: Custom engineer for this project
version: 2.0.0
tools: ["project_linter", "custom_debugger"]
---

# Project Engineer Agent

You are an expert software engineer with deep knowledge of this project's:
- Architecture patterns (microservices with event sourcing)
- Technology stack (Python, PostgreSQL, Redis)
- Coding standards and conventions
- Testing requirements (>90% coverage)

## Project-Specific Guidelines

- Always use our custom logging framework: `from project.utils import logger`
- Follow our error handling patterns with structured exceptions
- Ensure all database operations use transactions
- Run `./scripts/validate.py` before suggesting code changes
EOF

# 3. Verify the agent is loaded
./claude-mpm agents list --by-tier
```

### Advanced Example: JSON Agent

For more complex configurations, use JSON format:

```json
{
  "agent_id": "payment_processor",
  "version": "2.0.0",
  "metadata": {
    "name": "Payment Processing Agent",
    "description": "Specialized agent for payment flow handling",
    "category": "domain-specific",
    "tags": ["payments", "fintech", "compliance"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "resource_tier": "standard",
    "tools": ["payment_validator", "compliance_checker", "fraud_detector"],
    "features": ["multi_currency", "pci_compliance", "audit_trail"]
  },
  "knowledge": {
    "domains": ["payments", "financial_regulations", "security"],
    "frameworks": ["stripe", "paypal", "square"],
    "compliance": ["PCI_DSS", "PSD2", "GDPR"]
  },
  "interactions": {
    "tone": "professional",
    "verbosity": "detailed",
    "code_style": "defensive"
  },
  "instructions": "# Payment Processing Agent\n\nYou are a specialized agent for payment processing workflows...\n\n## Compliance Requirements\n\n- All payment data must be tokenized\n- Log all transactions for audit\n- Validate PCI compliance before suggesting code\n\n## Security Guidelines\n\n- Never log sensitive payment data\n- Use secure random for transaction IDs\n- Encrypt all stored payment tokens"
}
```

## Agent File Formats

### 1. Markdown Format (.md)

Best for human-readable agents with optional YAML frontmatter:

```markdown
---
description: Short description
version: 2.0.0
tools: ["tool1", "tool2"]
model: "claude-sonnet-4-20250514"
---

# Agent Name

Agent instructions in markdown format with full formatting support.

## Section 1
Content here...

## Section 2
More content...
```

### 2. JSON Format (.json)

Best for structured configurations and complex metadata:

```json
{
  "agent_id": "agent_name",
  "version": "2.0.0",
  "metadata": {
    "name": "Human Readable Name",
    "description": "Detailed description",
    "category": "category_name"
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["tool1", "tool2"]
  },
  "instructions": "Full agent instructions..."
}
```

### 3. YAML Format (.yaml, .yml)

Best for configuration-heavy agents:

```yaml
agent_id: agent_name
version: "2.0.0"
metadata:
  name: Human Readable Name
  description: Detailed description
  category: category_name
capabilities:
  model: claude-sonnet-4-20250514
  tools:
    - tool1
    - tool2
instructions: |
  # Agent Name
  
  Full agent instructions in YAML multiline format...
```

## Agent Dependencies

Claude MPM supports declaring dependencies for agents, enabling automatic dependency management and optional installation. This feature allows agents to specify their Python and system requirements, which are automatically aggregated during the build process.

### Dependencies Schema

The `dependencies` field in agent configurations supports:

```json
{
  "dependencies": {
    "python": [
      "pandas>=2.0.0",
      "numpy>=1.24.0", 
      "matplotlib>=3.7.0"
    ],
    "system": [
      "git",
      "ripgrep",
      "docker"
    ],
    "optional": false
  }
}
```

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `python` | `array` | Python packages with optional version specifiers | `["pandas>=2.0.0", "requests"]` |
| `system` | `array` | System commands that should be available in PATH | `["git", "docker", "kubectl"]` |
| `optional` | `boolean` | Whether dependencies are optional for agent function | `true` or `false` |

### Python Dependencies Format

Python dependencies follow standard pip requirement syntax:

```json
{
  "python": [
    "package_name",                    // Latest version
    "package_name>=1.0.0",            // Minimum version  
    "package_name==1.2.3",            // Exact version
    "package_name>=1.0.0,<2.0.0",     // Version range
    "package_name[extra1,extra2]>=1.0" // With extras
  ]
}
```

### Dependency Examples by Agent Type

**Data Analysis Agent:**
```json
{
  "agent_id": "data_analyst",
  "dependencies": {
    "python": [
      "pandas>=2.0.0",
      "numpy>=1.24.0",
      "matplotlib>=3.7.0",
      "seaborn>=0.12.0",
      "jupyter>=1.0.0"
    ],
    "system": ["git"],
    "optional": false
  }
}
```

**DevOps Agent:**
```json
{
  "agent_id": "devops_agent", 
  "dependencies": {
    "python": [
      "docker>=6.0.0",
      "kubernetes>=25.0.0",
      "ansible>=7.0.0"
    ],
    "system": ["docker", "kubectl", "terraform", "ansible"],
    "optional": false
  }
}
```

**Research Agent with Tree-sitter:**
```json
{
  "agent_id": "research_agent",
  "dependencies": {
    "python": [
      "tree-sitter>=0.21.0",
      "tree-sitter-language-pack>=0.8.0"
    ],
    "system": ["ripgrep", "git"],
    "optional": false
  }
}
```

### Dependency Aggregation

Dependencies are automatically aggregated from all agent sources during the build process:

1. **Collection**: Dependencies gathered from PROJECT > USER > SYSTEM tiers
2. **Version Conflict Resolution**: Intelligent handling of conflicting versions
3. **Aggregation**: Combined into `pyproject.toml` optional dependencies
4. **Installation**: Available via `pip install "claude-mpm[agents]"`

### Best Practices

**Dependency Declaration:**
- Use minimum version constraints: `>=1.0.0` rather than exact pins
- Declare only essential dependencies for agent functionality
- Mark dependencies as optional if agent can function without them
- Test agents with minimum required versions

**Version Constraints:**
```json
{
  "dependencies": {
    "python": [
      // Good: Reasonable minimum with update flexibility
      "pandas>=2.0.0",
      
      // Avoid: Too restrictive
      "pandas==2.0.1",
      
      // Good: Range allowing compatible updates
      "matplotlib>=3.7.0,<4.0.0"
    ]
  }
}
```

**Documentation:**
```json
{
  "agent_id": "my_agent",
  "metadata": {
    "description": "Agent for data processing (requires pandas, numpy)"
  },
  "dependencies": {
    "python": ["pandas>=2.0.0", "numpy>=1.24.0"],
    "optional": false
  }
}
```

### Installation and Usage

Users can install Claude MPM with agent dependencies:

```bash
# Install with all agent dependencies
pip install "claude-mpm[agents]"

# View what dependencies would be aggregated
python scripts/aggregate_agent_dependencies.py --dry-run

# Update pyproject.toml with current dependencies
python scripts/aggregate_agent_dependencies.py
```

For comprehensive dependency management documentation, see [docs/AGENT_DEPENDENCIES.md](AGENT_DEPENDENCIES.md).

## Agent Discovery and Caching

### Discovery Process

1. **Scan Directories**: System scans all tier directories in precedence order
2. **File Validation**: Each agent file is validated against the schema
3. **Precedence Resolution**: Higher-tier agents override lower-tier ones
4. **Registry Population**: Valid agents are added to the in-memory registry
5. **Cache Initialization**: Agent prompts are cached for performance

### Agent Capabilities Discovery

Claude MPM dynamically discovers agent capabilities by reading from deployed agents in the `.claude/agents/` directory. This ensures that capabilities information always matches what Claude Code actually has access to.

#### How Capabilities Discovery Works

**Source of Truth**: `.claude/agents/` (deployed agents)
- Capabilities are read from agents that have been deployed to Claude Code
- This ensures consistency between what Claude MPM reports and what Claude Code uses
- Project agents in `.claude-mpm/agents/` must be deployed to appear in capabilities

**Discovery Order**: Follows the three-tier precedence system
1. **PROJECT**: `.claude/agents/` agents deployed from `.claude-mpm/agents/`
2. **USER**: `.claude/agents/` agents deployed from `~/.claude-mpm/agents/`
3. **SYSTEM**: `.claude/agents/` built-in framework agents

**Key Benefits**:
- **Consistency**: Capabilities match Claude Code's actual agent access
- **Real-time**: Reflects currently deployed agents, not just definitions
- **Accurate Tooling**: CLI commands show capabilities from deployed agents
- **Version Alignment**: Capabilities correspond to the deployed agent versions

#### Deployment Requirement for Capabilities

For project agents to appear in capabilities discovery:

```bash
# 1. Create project agent
cat > .claude-mpm/agents/custom_agent.json << 'EOF'
{
  "agent_id": "custom_agent",
  "version": "1.0.0",
  "capabilities": {
    "tools": ["custom_tool", "project_validator"]
  },
  "instructions": "Custom agent for project-specific tasks..."
}
EOF

# 2. Deploy to make capabilities visible
./claude-mpm agents deploy

# 3. Verify capabilities are discovered
./claude-mpm agents list --deployed
```

**Important**: Undeployed agents in `.claude-mpm/agents/` will not appear in capabilities discovery until deployed to `.claude/agents/`.

#### Capabilities Information Available

The discovery system extracts these capabilities from deployed agents:

- **Tools**: Available tools and integrations
- **Model**: Preferred Claude model version
- **Resource Tier**: Performance and complexity tier
- **Features**: Special capabilities and extensions
- **Version**: Agent version for compatibility tracking

#### CLI Integration

Agent management commands use capabilities from deployed agents:

```bash
# Show capabilities from deployed agents
./claude-mpm agents list --by-tier

# View specific agent capabilities
./claude-mpm agents view engineer
```

This approach ensures that all capability information reflects the actual deployed state rather than just agent definitions.

### Cache Behavior

- **TTL**: Agent prompts cached for 1 hour (3600 seconds)
- **Invalidation**: Automatic when agent files are modified
- **Hot Reload**: Changes picked up without restart
- **Memory Efficient**: Only frequently accessed agents remain cached

### Manual Cache Management

```bash
# Clear specific agent cache
python -c "from claude_mpm.agents.agent_loader import clear_agent_cache; clear_agent_cache('engineer')"

# Clear all agent caches
python -c "from claude_mpm.agents.agent_loader import clear_agent_cache; clear_agent_cache()"

# Force reload all agents
python -c "from claude_mpm.agents.agent_loader import reload_agents; reload_agents()"
```

## CLI Agent Management

Claude MPM provides comprehensive CLI commands for managing agents across all tiers. These commands help you view, inspect, and troubleshoot agents in your project.

### Command Overview

The agent management commands are accessed via `claude-mpm agents <subcommand>`:

```bash
claude-mpm agents list --by-tier    # Show agents by precedence tier
claude-mpm agents view <agent_name> # View detailed agent information
claude-mpm agents fix [agent_name]  # Fix agent frontmatter issues
```

### `claude-mpm agents list --by-tier`

The most important agent management command shows agents organized by their precedence tier, helping you understand which version of each agent is active.

**Usage:**
```bash
claude-mpm agents list --by-tier
```

**Output:**
```
================================================================================
                         AGENT HIERARCHY BY TIER
================================================================================

Precedence: PROJECT > USER > SYSTEM
(Agents in higher tiers override those in lower tiers)


─────────────────────────────────────── PROJECT TIER ──────────────────────────────────────
  Location: .claude-mpm/agents/ (in current project)

  Found 2 agent(s):

    📄 engineer             [✓ ACTIVE]
       Description: Custom engineer for this project
       File: engineer.md

    📄 payment_processor    [✓ ACTIVE]
       Description: Specialized agent for payment flow handling
       File: payment_processor.json


─────────────────────────────────────── USER TIER ──────────────────────────────────────
  Location: ~/.claude-mpm/agents/

  Found 1 agent(s):

    📄 research_agent       [✓ ACTIVE]
       Description: Research agent with custom tools
       File: research_agent.yaml


─────────────────────────────────────── SYSTEM TIER ──────────────────────────────────────
  Location: Built-in framework agents

  Found 10 agent(s):

    📄 engineer             [⊗ OVERRIDDEN by PROJECT]
       Description: Software engineering specialist
       File: engineer.json

    📄 qa                   [✓ ACTIVE]
       Description: Quality assurance specialist
       File: qa.json

    📄 research_agent       [⊗ OVERRIDDEN by USER]
       Description: Research and analysis specialist
       File: research_agent.json

================================================================================
SUMMARY:
  Total unique agents: 11
  Project agents: 2
  User agents: 1
  System agents: 10
================================================================================
```

**Key Features:**
- **Tier Hierarchy**: Clear visualization of the PROJECT > USER > SYSTEM precedence
- **Override Detection**: Shows which agents are overridden by higher tiers
- **Location Information**: Displays where each agent is loaded from
- **Agent Status**: Active agents vs. overridden ones are clearly marked
- **Summary Statistics**: Quick overview of agent distribution across tiers

**Use Cases:**
- **Debugging**: Understand why a specific agent version is loading
- **Project Setup**: Verify your project agents are taking precedence
- **Team Coordination**: Share agent hierarchy with team members
- **Development**: Test agent precedence during development

### `claude-mpm agents view <agent_name>`

View comprehensive information about a specific agent, including its frontmatter, instructions preview, and file details.

**Usage:**
```bash
claude-mpm agents view engineer
claude-mpm agents view payment_processor
```

**Output:**
```
================================================================================
 AGENT: engineer
================================================================================

📋 BASIC INFORMATION:
  Name: engineer
  Type: development
  Tier: PROJECT
  Path: /path/to/.claude-mpm/agents/engineer.md
  Description: Custom engineer for this project
  Specializations: python, microservices, testing

📝 FRONTMATTER:
  description: Custom engineer for this project
  version: 2.0.0
  tools: [project_linter, custom_debugger]
  model: claude-sonnet-4-20250514
  specializations: [python, microservices, testing]

📖 INSTRUCTIONS PREVIEW (first 500 chars):
  --------------------------------------------------------------------------
  # Project Engineer Agent

  You are an expert software engineer with deep knowledge of this project's:
  - Architecture patterns (microservices with event sourcing)
  - Technology stack (Python, PostgreSQL, Redis)
  - Coding standards and conventions
  - Testing requirements (>90% coverage)

  ## Project-Specific Guidelines

  - Always use our custom logging framework: `from project.utils import logger`
  - Follow our error handling patterns with structured exceptions

  [Truncated - 2.3KB total]
  --------------------------------------------------------------------------

📊 FILE STATS:
  Size: 2,347 bytes
  Last modified: 2025-01-15 14:32:45

================================================================================
```

**Key Features:**
- **Complete Agent Profile**: Name, type, tier, path, and description
- **Frontmatter Analysis**: Parsed and formatted YAML frontmatter
- **Instructions Preview**: First 500 characters with truncation indicator
- **File Statistics**: Size and modification time
- **Error Handling**: Clear messages if agent not found or file issues

**Use Cases:**
- **Agent Inspection**: Understand what an agent does and how it's configured
- **Debugging Configuration**: Verify frontmatter fields are correct
- **Documentation**: Generate agent documentation for team reference
- **Development**: Review agent changes during development

### `claude-mpm agents fix [agent_name] [--dry-run] [--all]`

Automatically fix common frontmatter issues in agent files using the built-in FrontmatterValidator.

**Usage:**
```bash
# Fix specific agent
claude-mpm agents fix engineer

# Preview fixes without applying them
claude-mpm agents fix engineer --dry-run

# Fix all agents
claude-mpm agents fix --all

# Preview fixes for all agents
claude-mpm agents fix --all --dry-run
```

**Output:**
```
🔧 Checking agent 'engineer' for frontmatter issues...

📄 engineer:
  ✓ Fixed:
    - Added missing required field: version (set to "1.0.0")
    - Corrected field format: tools should be array, not string
    - Standardized field name: desc → description
    - Removed invalid field: invalid_field

================================================================================
SUMMARY:
  Agents checked: 1
  Total issues found: 4
  Issues fixed: 4

✓ Frontmatter issues have been fixed!
================================================================================
```

**Dry Run Mode:**
```bash
claude-mpm agents fix engineer --dry-run
```

**Output:**
```
🔍 DRY RUN MODE - No changes will be made

📄 engineer:
  🔧 Would fix:
    - Add missing required field: version
    - Convert tools from string to array format
    - Rename desc to description for consistency
    - Remove invalid field: custom_invalid_field

================================================================================
SUMMARY:
  Agents checked: 1
  Total issues found: 4
  Issues that would be fixed: 4

💡 Run without --dry-run to apply fixes
================================================================================
```

**Key Features:**
- **Automatic Detection**: Finds common frontmatter issues automatically
- **Safe Preview**: `--dry-run` shows changes without applying them
- **Bulk Operations**: `--all` flag fixes all agents at once
- **Detailed Reporting**: Shows exactly what was fixed or would be fixed
- **Non-Destructive**: Preserves original content while fixing structure

**Common Issues Fixed:**
- Missing required fields (version, description)
- Incorrect field formats (strings that should be arrays)
- Invalid field names (standardizes to schema)
- Malformed YAML syntax
- Inconsistent field naming

**Use Cases:**
- **Migration**: Fix agents when upgrading schema versions
- **Development**: Clean up agent files during development
- **Maintenance**: Regularly validate agent configurations
- **Troubleshooting**: Resolve agent loading issues

### Other Agent Commands

#### List System Agents
```bash
claude-mpm agents list --system
```
Shows available agent templates in the framework.

#### List Deployed Agents
```bash
claude-mpm agents list --deployed
```
Shows agents that have been deployed to Claude Code.

#### Deploy Agents
```bash
claude-mpm agents deploy [--target path]
claude-mpm agents force-deploy [--target path]
```
Deploy system agents for Claude Code native agent support.

#### Clean Deployed Agents
```bash
claude-mpm agents clean [--target path]
```
Remove deployed system agents from working directory.

### Integration with Development Workflow

**Daily Workflow:**
```bash
# 1. Check agent hierarchy when starting work
claude-mpm agents list --by-tier

# 2. Inspect specific agents if needed
claude-mpm agents view engineer

# 3. Fix any issues found
claude-mpm agents fix --all --dry-run
claude-mpm agents fix --all  # if fixes look good

# 4. Start work with confidence
claude-mpm run --monitor
```

**Project Setup:**
```bash
# 1. Create project agents directory
mkdir -p .claude-mpm/agents

# 2. Add custom agents (see Creating Local Agents section)
# ...

# 3. Verify agent hierarchy
claude-mpm agents list --by-tier

# 4. Validate agent configurations
claude-mpm agents fix --all --dry-run
```

**Troubleshooting:**
```bash
# 1. Check which agents are active
claude-mpm agents list --by-tier

# 2. Inspect problematic agent
claude-mpm agents view problematic_agent

# 3. Fix configuration issues
claude-mpm agents fix problematic_agent

# 4. Verify fixes
claude-mpm agents view problematic_agent
```

## Environment Configuration

### Global Settings

Control agent system behavior with environment variables:

```bash
# Enable/disable dynamic model selection (default: true)
export ENABLE_DYNAMIC_MODEL_SELECTION=false

# Per-agent model selection override
export CLAUDE_PM_RESEARCH_AGENT_MODEL_SELECTION=true
export CLAUDE_PM_QA_AGENT_MODEL_SELECTION=false

# Cache settings
export CLAUDE_MPM_CACHE_TTL=7200  # 2 hours
export CLAUDE_MPM_ENABLE_CACHE=true
```

### Project-Specific Configuration

Create `.claude-mpm/config/agents.yaml`:

```yaml
# Agent-specific overrides
agent_config:
  engineer:
    model: "claude-opus-4-20250514"  # Use most powerful model
    enable_complexity_analysis: false
  
  qa:
    model: "claude-haiku-3-20240307"  # Use fast model for simple tasks
    cache_ttl: 3600

# Discovery settings
discovery:
  scan_interval: 300  # Check for changes every 5 minutes
  auto_reload: true
  validate_schema: true

# Precedence overrides (advanced)
precedence:
  enforce_project_only: false  # If true, ignore USER and SYSTEM tiers
  allow_system_fallback: true
```

## API Reference

### Core Functions

#### `get_agent_prompt(agent_name, **kwargs)`

Primary interface for retrieving agent prompts with optional model selection.

```python
from claude_mpm.agents.agent_loader import get_agent_prompt

# Basic usage
prompt = get_agent_prompt("engineer")

# With task complexity analysis
prompt = get_agent_prompt(
    "research_agent",
    task_description="Analyze large Python codebase architecture",
    context_size=50000
)

# With model information
prompt, model, config = get_agent_prompt(
    "qa_agent", 
    return_model_info=True,
    task_description="Review simple bug fix"
)
```

#### `list_agents_by_tier()`

Get agents organized by their loading tier.

```python
from claude_mpm.agents.agent_loader import list_agents_by_tier

agents_by_tier = list_agents_by_tier()
# Returns: {
#   "project": ["engineer", "custom_domain"],
#   "user": ["research_agent"],
#   "system": ["engineer", "qa", "research_agent", ...]
# }
```

#### `get_agent_tier(agent_name)`

Determine which tier an agent was loaded from.

```python
from claude_mpm.agents.agent_loader import get_agent_tier

tier = get_agent_tier("engineer")
# Returns: "project", "user", "system", or None
```

#### `list_available_agents()`

Get comprehensive metadata for all available agents.

```python
from claude_mpm.agents.agent_loader import list_available_agents

agents = list_available_agents()
# Returns: {
#   "engineer": {
#     "name": "Engineer Agent",
#     "description": "Software engineering specialist",
#     "category": "development",
#     "model": "claude-sonnet-4-20250514",
#     "tools": ["code_analyzer", "debugger"]
#   },
#   ...
# }
```

### AgentLoader Class

Direct access to the agent loader for advanced usage:

```python
from claude_mpm.agents.agent_loader import AgentLoader

loader = AgentLoader()

# Get agent metadata
metadata = loader.get_agent_metadata("engineer")

# Get performance metrics
metrics = loader.get_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate_percent']:.1f}%")

# List agents with tier information
for agent_info in loader.list_agents():
    agent_data = loader.get_agent(agent_info["id"])
    print(f"{agent_info['id']}: {agent_data.get('_tier', 'unknown')}")
```

## Best Practices

### 1. Project Organization

```
project-root/
├── .claude-mpm/
│   ├── agents/                  # JSON only (Claude MPM format)
│   │   ├── engineer.json        # Override with project knowledge
│   │   ├── domain_expert.json   # Project-specific agent
│   │   └── test_runner.json     # Testing-focused agent
│   ├── config/
│   │   └── agents.yaml          # Agent configuration
│   └── docs/
│       └── agents.md            # Document project agents
├── .claude/
│   └── agents/                  # Auto-generated Markdown (Claude Code format)
│       ├── engineer.md          # Generated from engineer.json
│       ├── domain_expert.md     # Generated from domain_expert.json
│       └── test_runner.md       # Generated from test_runner.json
```

### 2. Version Control

```bash
# Include project agents in version control
echo ".claude-mpm/logs/" >> .gitignore
# But keep agents and config tracked
git add .claude-mpm/agents/
git add .claude-mpm/config/
```

### 3. Agent Naming

- Use descriptive names: `payment_processor` not `pp`
- Follow project conventions: match your team's naming style
- Avoid conflicts: Check existing system agents with `./claude-mpm agents list`

### 4. Documentation

Document your project agents:

```markdown
# Project Agents

## engineer.md
Custom engineer with knowledge of our microservices architecture.
Overrides system engineer to include:
- Service mesh patterns
- Event sourcing conventions
- Database migration standards

## payment_processor.json
Domain-specific agent for payment workflows.
Includes compliance checking and fraud detection tools.
```

### 5. Testing

Test your agents before deployment:

```bash
# Validate agent syntax
python -c "
from claude_mpm.agents.agent_loader import validate_agent_files
results = validate_agent_files()
for agent, result in results.items():
    if not result['valid']:
        print(f'❌ {agent}: {result[\"errors\"]}')"

# Test agent loading
python -c "
from claude_mpm.agents.agent_loader import get_agent_prompt
try:
    prompt = get_agent_prompt('your_agent')
    print('✅ Agent loaded successfully')
except Exception as e:
    print(f'❌ Agent failed to load: {e}')"
```

## Migration Guide

### From System to Project Agents

1. **Identify Customizations**: Find agents you've modified for project needs
2. **Extract Project-Specific Knowledge**: Separate project details from general templates
3. **Create Project Agent**: Copy and customize in `.claude-mpm/agents/`
4. **Test Precedence**: Verify project agent overrides system agent
5. **Document Changes**: Update project documentation

### From User to Project Agents

When moving user-level customizations to project level:

```bash
# 1. Copy user agent to project
cp ~/.claude-mpm/agents/engineer.md .claude-mpm/agents/

# 2. Customize for project
# Edit .claude-mpm/agents/engineer.md with project-specific content

# 3. Test loading
./claude-mpm agents list --by-tier

# 4. Verify precedence
python -c "
from claude_mpm.agents.agent_loader import get_agent_tier
print(f'Engineer tier: {get_agent_tier(\"engineer\")}')"
```

### Legacy Agent Format Migration

For agents using old formats:

```python
from claude_mpm.validation.migration import migrate_agent_format

# Migrate old markdown agent to new JSON format
result = migrate_agent_format("old_agent.md", "new_agent.json")
if result.success:
    print("Migration successful")
else:
    print(f"Migration failed: {result.errors}")
```

## Troubleshooting

### Common Issues

#### 1. Agent Not Found

**Symptoms**: `ValueError: No agent found with name: your_agent`

**Solutions**:
```bash
# First, check the agent hierarchy to see what's available
claude-mpm agents list --by-tier

# Check if agent file exists
ls -la .claude-mpm/agents/your_agent.*

# Verify file format is supported
file .claude-mpm/agents/your_agent.*

# If you have the agent file, try fixing any configuration issues
claude-mpm agents fix your_agent --dry-run
```

#### 2. Wrong Agent Version Loaded

**Symptoms**: System agent loaded instead of project agent

**Solutions**:
```bash
# Check tier precedence and see which version is active
claude-mpm agents list --by-tier

# View details of the specific agent to see which tier it's loaded from
claude-mpm agents view your_agent

# Verify file naming matches agent ID
ls -la .claude-mpm/agents/

# If configuration issues exist, fix them
claude-mpm agents fix your_agent --dry-run
claude-mpm agents fix your_agent  # if fixes look good
```

#### 3. Schema Validation Errors

**Symptoms**: Agent loads but behaves unexpectedly

**Solutions**:
```bash
# Check for and fix frontmatter issues automatically
claude-mpm agents fix --all --dry-run

# Fix specific agent
claude-mpm agents fix your_agent --dry-run
claude-mpm agents fix your_agent  # apply fixes

# View agent details to inspect configuration
claude-mpm agents view your_agent

# Verify all agents are properly configured
claude-mpm agents list --by-tier
```

#### 4. Cache Issues

**Symptoms**: Changes not reflected, old content returned

**Solutions**:
```bash
# Clear specific agent cache
python -c "
from claude_mpm.agents.agent_loader import clear_agent_cache
clear_agent_cache('your_agent')"

# Clear all caches
python -c "
from claude_mpm.agents.agent_loader import clear_agent_cache
clear_agent_cache()"

# Force complete reload
python -c "
from claude_mpm.agents.agent_loader import reload_agents
reload_agents()"
```

#### 5. Performance Issues

**Symptoms**: Slow agent loading, high memory usage

**Solutions**:
```bash
# Check metrics
python -c "
from claude_mpm.agents.agent_loader import _get_loader
loader = _get_loader()
metrics = loader.get_metrics()
print(f'Cache hit rate: {metrics[\"cache_hit_rate_percent\"]:.1f}%')
print(f'Average load time: {metrics[\"average_load_time_ms\"]:.1f}ms')
print(f'Agents loaded: {metrics[\"agents_loaded\"]}')"

# Optimize cache settings
export CLAUDE_MPM_CACHE_TTL=3600  # Reduce TTL
export CLAUDE_MPM_ENABLE_CACHE=true  # Ensure caching enabled
```

### Debugging Tools

#### Agent Inspector

```python
from claude_mpm.agents.agent_loader import _get_loader

def inspect_agent(agent_name):
    loader = _get_loader()
    agent_data = loader.get_agent(agent_name)
    
    if agent_data:
        print(f"Agent: {agent_name}")
        print(f"Tier: {agent_data.get('_tier', 'unknown')}")
        print(f"Version: {agent_data.get('version', 'unknown')}")
        print(f"Model: {agent_data.get('capabilities', {}).get('model', 'default')}")
        print(f"Tools: {agent_data.get('capabilities', {}).get('tools', [])}")
    else:
        print(f"Agent '{agent_name}' not found")

# Usage
inspect_agent("engineer")
```

#### Tier Analysis

```python
from claude_mpm.agents.agent_loader import list_agents_by_tier, get_agent_tier

def analyze_tiers():
    tiers = list_agents_by_tier()
    
    for tier_name, agents in tiers.items():
        print(f"\n{tier_name.upper()} TIER ({len(agents)} agents):")
        for agent in agents:
            actual_tier = get_agent_tier(agent)
            status = "✅" if actual_tier == tier_name else "⚠️"
            print(f"  {status} {agent} (loaded from: {actual_tier})")

# Usage
analyze_tiers()
```

### Getting Help

If you continue to experience issues:

1. **Check Logs**: Look in `.claude-mpm/logs/` for detailed error messages
2. **Enable Debug Logging**: Set `CLAUDE_MPM_LOG_LEVEL=DEBUG`
3. **Validate Environment**: Ensure Python path and dependencies are correct
4. **Create Minimal Example**: Isolate the issue with a simple test case
5. **Report Issues**: Include system info, agent files, and error logs

For additional support, see the [main project documentation](../README.md) or file an issue in the repository.

---

## Detailed Documentation

For comprehensive information on specific agent topics, refer to the detailed documentation sections:

### Developer Reference

- **[Agent Frontmatter Documentation](developer/agents/frontmatter.md)**
  - Complete field reference for all agent formats
  - Required and optional field descriptions
  - Validation rules and common pitfalls
  - Examples for each format type

- **[Agent Formats Guide](developer/agents/formats.md)**  
  - JSON format (v1.2.0 schema) documentation
  - Markdown with YAML frontmatter (.claude format)
  - Enhanced markdown format (.claude-mpm format)
  - Format detection logic and precedence rules
  - Migration between formats

- **[Agent Schema Reference](developer/agents/schema.md)**
  - v1.1.0 legacy schema details
  - v1.2.0 current schema specifications
  - Schema differences and migration guide
  - Validation requirements and security enhancements
  - Troubleshooting schema issues

- **[Agent Creation Guide](developer/agents/creation-guide.md)**
  - Step-by-step creation instructions
  - Practical examples for each format
  - Testing and validation procedures
  - Best practices and security considerations
  - Real-world agent examples
  - Debugging common issues

### Getting Started Resources

- **New to Agents?** Start with the [Creation Guide](developer/agents/creation-guide.md#getting-started)
- **Need Field Reference?** See [Frontmatter Documentation](developer/agents/frontmatter.md)
- **Choosing a Format?** Check [Format Selection Guidelines](developer/agents/formats.md#best-practices)
- **Schema Issues?** Consult [Schema Troubleshooting](developer/agents/schema.md#troubleshooting)
- **Migration Help?** Follow [Migration Guides](developer/agents/schema.md#migration-guide)

This documentation structure ensures you have access to both high-level guidance and detailed technical references for working with Claude MPM agents.