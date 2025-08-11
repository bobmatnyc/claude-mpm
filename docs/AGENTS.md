# Claude MPM Agent System

This document provides comprehensive guidance on using and managing agents in Claude MPM, with a focus on the local agent deployment feature that allows projects to define custom agents with precedence over system defaults.

## Table of Contents

1. [Overview](#overview)
2. [Agent Tier System](#agent-tier-system)
3. [Creating Local Agents](#creating-local-agents)
4. [Agent File Formats](#agent-file-formats)
5. [Agent Discovery and Caching](#agent-discovery-and-caching)
6. [Environment Configuration](#environment-configuration)
7. [API Reference](#api-reference)
8. [Best Practices](#best-practices)
9. [Migration Guide](#migration-guide)
10. [Troubleshooting](#troubleshooting)

## Overview

Claude MPM's agent system provides a flexible framework for defining AI assistant behaviors through structured templates. The system supports multiple agent types (Engineer, QA, Research, etc.) with a three-tier precedence system that allows for project-specific customization.

### Key Features

- **Three-tier precedence**: PROJECT > USER > SYSTEM
- **Hot-reload capability**: Changes detected automatically
- **Multiple formats**: Supports `.md`, `.json`, and `.yaml` files
- **Schema validation**: Ensures consistency and correctness
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
- **Location**: `src/claude_mpm/agents/templates/` in framework installation
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

## Agent Discovery and Caching

### Discovery Process

1. **Scan Directories**: System scans all tier directories in precedence order
2. **File Validation**: Each agent file is validated against the schema
3. **Precedence Resolution**: Higher-tier agents override lower-tier ones
4. **Registry Population**: Valid agents are added to the in-memory registry
5. **Cache Initialization**: Agent prompts are cached for performance

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
│   ├── agents/
│   │   ├── engineer.md          # Override with project knowledge
│   │   ├── domain_expert.json   # Project-specific agent
│   │   └── test_runner.yaml     # Testing-focused agent
│   ├── config/
│   │   └── agents.yaml          # Agent configuration
│   └── docs/
│       └── agents.md            # Document project agents
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
# Check if agent file exists
ls -la .claude-mpm/agents/your_agent.*

# Verify file format is supported
file .claude-mpm/agents/your_agent.*

# Check agent discovery
python -c "
from claude_mpm.agents.agent_loader import list_agents_by_tier
import json
print(json.dumps(list_agents_by_tier(), indent=2))"
```

#### 2. Wrong Agent Version Loaded

**Symptoms**: System agent loaded instead of project agent

**Solutions**:
```bash
# Check tier precedence
python -c "
from claude_mpm.agents.agent_loader import get_agent_tier
print(f'Current tier: {get_agent_tier(\"your_agent\")}')"

# Force cache refresh
python -c "
from claude_mpm.agents.agent_loader import reload_agents
reload_agents()"

# Verify file naming
ls -la .claude-mpm/agents/
# Ensure filename matches expected agent ID
```

#### 3. Schema Validation Errors

**Symptoms**: Agent loads but behaves unexpectedly

**Solutions**:
```bash
# Validate agent files
python -c "
from claude_mpm.agents.agent_loader import validate_agent_files
results = validate_agent_files()
for agent, result in results.items():
    if not result['valid']:
        print(f'{agent}:')
        for error in result['errors']:
            print(f'  ❌ {error}')"

# Check schema requirements
python -c "
from claude_mpm.validation.agent_validator import AgentValidator
validator = AgentValidator()
print('Required fields:', validator.get_required_fields())"
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