# Agent Development Guide

> **Navigation**: [Developer Guide](../README.md) → [Agent System](./README.md) → **Agent Development Guide**

## Overview

This comprehensive guide covers all aspects of agent development in Claude MPM, including creation, configuration, deployment, and best practices.

## Table of Contents

1. [Agent Architecture](#agent-architecture)
2. [Agent Schema](#agent-schema)
3. [Creating Agents](#creating-agents)
4. [Agent Formats](#agent-formats)
5. [Frontmatter Configuration](#frontmatter-configuration)
6. [Agent Dependencies](#agent-dependencies)
7. [Deployment and Precedence](#deployment-and-precedence)
8. [Testing Agents](#testing-agents)
9. [Best Practices](#best-practices)

## Agent Architecture

### System Design

Claude MPM uses a three-tier agent system with clear precedence:

1. **PROJECT** - `.claude-mpm/agents/` in your project directory
2. **USER** - `~/.claude-mpm/agents/` in your home directory
3. **SYSTEM** - Built-in framework agents

### Agent Types

- `base` - Generic agent with no specialization
- `engineer` - Code implementation and development
- `qa` - Quality assurance and testing
- `documentation` - Documentation creation
- `research` - Code analysis and research
- `security` - Security analysis
- `ops` - Operations and infrastructure
- `data_engineer` - Data pipeline development
- `version_control` - Git operations

## Agent Schema

### Required Fields

Every agent must include these seven required fields:

1. **`schema_version`** - Version of the schema format (e.g., "1.2.0")
2. **`agent_id`** - Unique identifier (pattern: `^[a-z][a-z0-9_]*$`)
3. **`agent_version`** - Agent template version (semantic versioning)
4. **`agent_type`** - Category from the enum list above
5. **`metadata`** - Human-readable information
6. **`capabilities`** - Technical specifications
7. **`instructions`** - System prompt defining behavior

### JSON Format Example

```json
{
  "schema_version": "1.2.0",
  "agent_id": "custom_engineer",
  "agent_version": "2.0.0",
  "agent_type": "engineer",
  "metadata": {
    "name": "Custom Engineer",
    "description": "Project-specific engineering agent with custom knowledge",
    "tags": ["engineering", "custom", "project-specific"]
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Write", "Edit", "Bash", "Grep"],
    "resource_tier": "intensive",
    "max_tokens": 12288,
    "temperature": 0.2
  },
  "instructions": "You are a specialized engineer for this project..."
}
```

## Creating Agents

### Step 1: Choose Format

Agents can be created in multiple formats:

1. **Markdown with Frontmatter** (Recommended for simplicity)
2. **JSON** (Full control over all fields)
3. **YAML** (Human-friendly structured format)

### Step 2: Define Agent Configuration

#### Markdown Format

```markdown
---
description: Custom QA agent for project-specific testing
version: 2.0.0
tools: ["Read", "Grep", "Bash"]
model: claude-sonnet-4-20250514
max_tokens: 8192
temperature: 0.3
---

# Custom QA Agent

You are a QA specialist for this specific project.

## Your Responsibilities

1. Test all code changes thoroughly
2. Verify integration points
3. Check for regressions

## Project-Specific Rules

- Always run the custom test suite at `./scripts/test_custom.sh`
- Check for memory leaks using our proprietary tool
- Validate against our custom style guide
```

#### JSON Format

```json
{
  "agent_id": "custom_qa",
  "version": "2.0.0",
  "metadata": {
    "name": "Custom QA Agent",
    "description": "Project-specific QA with custom test protocols"
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Grep", "Bash"],
    "max_tokens": 8192,
    "temperature": 0.3
  },
  "instructions": "# Custom QA Agent\n\nYou are a QA specialist..."
}
```

### Step 3: Deploy Agent

```bash
# Create project agents directory
mkdir -p .claude-mpm/agents

# Add your agent (choose appropriate extension)
cp my_agent.md .claude-mpm/agents/
# or
cp my_agent.json .claude-mpm/agents/
# or
cp my_agent.yaml .claude-mpm/agents/

# Verify deployment
./claude-mpm agents list --by-tier
```

## Agent Formats

### Supported Formats

1. **Markdown (.md)** - Instructions with optional frontmatter
2. **JSON (.json)** - Full structured configuration
3. **YAML (.yaml/.yml)** - Human-readable structured format
4. **Plain Text (.txt)** - Simple instructions only

### Format Detection Priority

1. Check file extension
2. Attempt JSON parsing
3. Check for YAML frontmatter
4. Check for YAML structure
5. Default to plain text

### Format Conversion

All formats are internally converted to the standard JSON schema:

```python
# Markdown → JSON
frontmatter, content = parse_markdown(file_content)
agent_config = {
    "agent_id": derive_from_filename(),
    "version": frontmatter.get("version", "1.0.0"),
    "metadata": {
        "description": frontmatter.get("description")
    },
    "capabilities": {
        "tools": frontmatter.get("tools", []),
        "model": frontmatter.get("model")
    },
    "instructions": content
}
```

## Frontmatter Configuration

### Standard Fields

```yaml
---
# Required
description: Brief description of the agent
version: 2.0.0

# Capabilities
tools: ["Read", "Write", "Edit", "Bash", "Grep"]
model: claude-sonnet-4-20250514
max_tokens: 12288
temperature: 0.2
resource_tier: intensive

# Optional
tags: ["custom", "project-specific"]
author: Your Name
created_at: 2025-01-12T10:00:00Z

# File Access Control
file_access:
  read_paths: ["*"]
  write_paths: ["./**"]
  blocked_paths: ["**/secrets/**"]
---
```

### Validation Rules

1. **Version Format**: Must be semantic versioning (X.Y.Z)
2. **Tools**: Must be valid tool names from the allowed list
3. **Model**: Must be a valid Claude model identifier
4. **Temperature**: Must be between 0 and 1
5. **Max Tokens**: Must be between 1000 and 200000

## Agent Dependencies

### Overview

Claude MPM features a sophisticated dependency management system that:
- **Dynamically checks** dependencies only for deployed agents
- **Smart caching** to avoid redundant checks (71x faster on cache hits)
- **Python version compatibility** checking (especially important for Python 3.13+)
- **Interactive prompting** in appropriate contexts
- **Context-aware behavior** (TTY, CI, Docker detection)

### Declaring Dependencies

#### JSON Format

```json
{
  "agent_id": "data_engineer",
  "dependencies": {
    "python": [
      "pandas>=2.1.0",
      "numpy>=1.24.0",
      "dask>=2023.12.0",
      "apache-airflow>=2.8.0"
    ],
    "system": [
      "git",
      "docker",
      "kubectl"
    ],
    "optional": false
  }
}
```

#### Frontmatter Format (Markdown)

```yaml
---
description: Data engineering agent
version: 2.0.0
dependencies:
  python:
    - pandas>=2.1.0
    - numpy>=1.24.0
    - dask>=2023.12.0
  system:
    - git
    - docker
---
```

### Dependency Checking

#### Automatic Checking on Startup

Claude MPM automatically checks dependencies when:
1. **Agents have changed** (new deployment or modification)
2. **First run** after installation
3. **Cache has expired** (24-hour TTL)
4. **Force flag** is used (`--force-check-dependencies`)

```bash
$ ./claude-mpm
# First run after agent deployment
⚠️  26 agent dependencies missing
Install missing dependencies now? [Y/n]: y
🔧 Installing 24 compatible dependencies...
⚠️  Skipping 2 packages incompatible with Python 3.13

# Second run (no changes - uses cache)
$ ./claude-mpm
# Starts immediately, no dependency check
```

#### Manual Dependency Management

```bash
# Check dependencies for all deployed agents
./claude-mpm agents deps-check

# Check specific agent
./claude-mpm agents deps-check --agent engineer

# List all dependencies
./claude-mpm agents deps-list

# Export for pip
./claude-mpm agents deps-list --format pip > requirements.txt

# Install missing dependencies
./claude-mpm agents deps-install

# Dry run to see what would be installed
./claude-mpm agents deps-install --dry-run
```

### Python Version Compatibility

#### Python 3.13 Considerations

Many packages haven't been updated for Python 3.13 yet. The system automatically:
- **Detects incompatible packages** before installation
- **Skips incompatible packages** rather than failing
- **Shows clear warnings** about compatibility issues

```bash
$ ./claude-mpm agents deps-check
Python Version: 3.13.5

⚠️  Python 3.13 Compatibility Warning:
  2 packages are not yet compatible with Python 3.13:
    - ydata-profiling>=4.6.0 (requires Python <3.13)
    - apache-airflow>=2.8.0 (requires Python <3.13)
  
  Consider using Python 3.12 or earlier for full compatibility.
```

#### Known Incompatibilities

| Package | Python 3.13 Status | Alternative |
|---------|-------------------|-------------|
| `ydata-profiling` | ❌ Not compatible | Use `pandas-profiling` or wait for update |
| `apache-airflow` | ❌ Not compatible | Use Python 3.12 or containerized Airflow |
| `tree-sitter-languages` | ❌ Wrong package name | Use `tree-sitter-language-pack` |

### Smart Caching System

#### How It Works

1. **Hash-based tracking**: Calculates SHA256 hash of `.claude/agents/` directory
2. **State persistence**: Stores in `.claude/agents/.mpm_deployment_state`
3. **Cache storage**: Results cached in `~/.claude-mpm/cache/dependency_cache.json`
4. **Automatic invalidation**: When agents change or 24 hours pass

#### Performance Impact

```bash
# First run (full check)
Time: 1.42 seconds

# Cached run (no changes)
Time: 0.02 seconds (71x faster)
```

#### Cache Management

```bash
# Force dependency check (ignores cache)
./claude-mpm --force-check-dependencies

# Skip dependency checking entirely
./claude-mpm --no-check-dependencies

# Clear cache manually
rm ~/.claude-mpm/cache/dependency_cache.json
rm .claude/agents/.mpm_deployment_state
```

### Context-Aware Behavior

The dependency system adapts to different execution contexts:

| Context | Behavior |
|---------|----------|
| **Interactive TTY** | Prompts for installation |
| **CI Environment** | No prompts, warnings only |
| **Docker Container** | No prompts, check-only mode |
| **Non-TTY Script** | No prompts, continues with warnings |
| **Automated Mode** | Respects `CLAUDE_MPM_AUTOMATED` env var |

#### Environment Detection

```python
# Automatic detection
- TTY: sys.stdin.isatty() and sys.stdout.isatty()
- CI: Checks for CI, GITHUB_ACTIONS, GITLAB_CI, etc.
- Docker: Checks for /.dockerenv file
- Interactive: Not CLAUDE_MPM_NON_INTERACTIVE
```

#### Override Behavior

```bash
# Never prompt (CI-like behavior)
./claude-mpm --no-prompt

# Force prompting even in non-TTY
./claude-mpm --force-prompt

# Skip all dependency checks
CLAUDE_MPM_NO_DEPS=1 ./claude-mpm
```

### Dependency Aggregation

#### Build-Time Aggregation

All agent dependencies are aggregated into `pyproject.toml`:

```bash
# Aggregate dependencies from all agents
python scripts/aggregate_agent_dependencies.py

# Install all agent dependencies at once
pip install "claude-mpm[agents]"
```

#### Aggregation Sources (in precedence order)

1. **PROJECT**: `.claude-mpm/agents/*.json`
2. **USER**: `~/.claude-mpm/agents/*`
3. **SYSTEM**: `src/claude_mpm/agents/templates/*.json`

### Best Practices for Dependencies

#### 1. Minimal Dependencies
Only declare dependencies that are truly necessary:

```json
{
  "dependencies": {
    "python": [
      "pandas>=2.0.0",  // Good: minimum version
      "pandas==2.0.1"   // Bad: too restrictive
    ]
  }
}
```

#### 2. Version Ranges
Use appropriate version constraints:

```json
{
  "dependencies": {
    "python": [
      "numpy>=1.24.0",           // Minimum version
      "django>=4.0,<5.0",        // Range for major version
      "requests>=2.28.0,<3.0.0"  // Strict upper bound
    ]
  }
}
```

#### 3. Optional Dependencies
Mark dependencies as optional when agent can function without them:

```json
{
  "dependencies": {
    "python": ["optional-package>=1.0.0"],
    "optional": true  // Agent works without these
  }
}
```

#### 4. System Dependencies
Document system-level requirements clearly:

```json
{
  "dependencies": {
    "system": [
      "git",      // Version control
      "docker",   // Container operations
      "aws"       // AWS CLI for cloud operations
    ]
  }
}
```

### Troubleshooting

#### Missing Dependencies After Installation

```bash
# Clear pip cache and retry
pip cache purge
pip install --force-reinstall "claude-mpm[agents]"

# Check what's installed
pip list | grep package-name
```

#### Python Version Issues

```bash
# Check your Python version
python --version

# Use pyenv or conda for different Python versions
pyenv install 3.12.0
pyenv local 3.12.0

# Or with conda
conda create -n claude-mpm python=3.12
conda activate claude-mpm
```

#### Dependency Conflicts

```bash
# Check for conflicts
pip check

# Install specific versions
pip install "pandas==2.1.0" "numpy==1.24.0"

# Use virtual environment
python -m venv venv
source venv/bin/activate
pip install claude-mpm
```

## Deployment and Precedence

### Three-Tier System

```
PROJECT (.claude-mpm/agents/)
    ↓ Overrides
USER (~/.claude-mpm/agents/)
    ↓ Overrides
SYSTEM (built-in agents)
```

### Deployment Commands

```bash
# List all agents by tier
./claude-mpm agents list --by-tier

# List only project agents
./claude-mpm agents list --tier project

# Show specific agent (shows which tier is active)
./claude-mpm agents show engineer

# Deploy agent to user directory
cp my_agent.md ~/.claude-mpm/agents/

# Deploy agent to project directory
cp my_agent.md .claude-mpm/agents/
```

### Resolution Process

1. Check project directory (`.claude-mpm/agents/`)
2. If not found, check user directory (`~/.claude-mpm/agents/`)
3. If not found, use system agent
4. If not found anywhere, return error

## Testing Agents

### Validation

```bash
# Validate agent configuration
python scripts/validate_agent_frontmatter.py .claude-mpm/agents/my_agent.md

# Validate all agents
python scripts/validate_agent_frontmatter.py .claude-mpm/agents/*.md
```

### Testing Workflow

1. **Create Test Agent**
   ```bash
   cat > .claude-mpm/agents/test_agent.md << 'EOF'
   ---
   description: Test agent for validation
   version: 1.0.0
   tools: ["Read"]
   ---
   # Test Agent
   This is a test agent.
   EOF
   ```

2. **Validate Configuration**
   ```bash
   ./claude-mpm agents show test_agent
   ```

3. **Test Execution**
   ```bash
   ./claude-mpm run -i "Test prompt" --agent test_agent
   ```

## Best Practices

### 1. Naming Conventions

- Use snake_case for agent IDs
- Be descriptive but concise
- Include role in name (e.g., `project_qa`, `custom_engineer`)

### 2. Version Management

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Major: Breaking changes to agent behavior
- Minor: New features or capabilities
- Patch: Bug fixes or minor improvements

### 3. Instructions

- Start with a clear role definition
- Use markdown formatting for structure
- Include specific project knowledge
- Define success criteria
- Provide examples when helpful

### 4. Tool Selection

- Only include necessary tools
- Consider security implications
- Use read-only tools for analysis agents
- Restrict write access appropriately

### 5. Resource Allocation

```yaml
# Intensive tasks (complex analysis, large codebases)
resource_tier: intensive
max_tokens: 12288
timeout: 1200

# Standard tasks (normal development)
resource_tier: standard
max_tokens: 8192
timeout: 600

# Lightweight tasks (simple queries)
resource_tier: lightweight
max_tokens: 4096
timeout: 300
```

### 6. Project-Specific Agents

- Override system agents with project knowledge
- Include project-specific commands and tools
- Reference project documentation
- Define project-specific workflows

### 7. Security Considerations

```yaml
file_access:
  read_paths:
    - "*"  # Can read from anywhere
  write_paths:
    - "."  # Only current directory
    - "./src/**"  # Source code
    - "./tests/**"  # Test files
  blocked_paths:
    - "**/.env"  # Environment files
    - "**/secrets/**"  # Sensitive data
    - "**/.git/**"  # Git internals
```

## Common Patterns

### Research-Guided Engineer

```markdown
---
description: Engineer that follows research agent findings
version: 2.0.0
tools: ["Read", "Write", "Edit", "MultiEdit", "Bash"]
---

# Research-Guided Engineer

You implement solutions based on research agent findings.

## Protocol

1. Review research agent's analysis
2. Validate patterns against current codebase
3. Implement following discovered conventions
4. Test implementation thoroughly
5. Document decisions and trade-offs
```

### Domain-Specific QA

```markdown
---
description: QA agent with domain-specific testing knowledge
version: 2.0.0
tools: ["Read", "Grep", "Bash"]
---

# Domain QA Specialist

You are a QA engineer specializing in [specific domain].

## Testing Requirements

1. Unit tests for all public methods
2. Integration tests for API endpoints
3. Performance benchmarks for critical paths
4. Security validation for user inputs

## Domain-Specific Checks

- [Specific validation rules]
- [Performance requirements]
- [Security considerations]
```

### Documentation Specialist

```markdown
---
description: Creates comprehensive technical documentation
version: 2.0.0
tools: ["Read", "Write", "Grep"]
max_tokens: 16384
---

# Documentation Specialist

You create clear, comprehensive technical documentation.

## Documentation Standards

1. API documentation with examples
2. Architecture diagrams and explanations
3. Setup and deployment guides
4. Troubleshooting sections
5. Code examples and best practices
```

## Troubleshooting

### Agent Not Found

```bash
# Check if agent exists in any tier
./claude-mpm agents list --by-tier | grep agent_name

# Check file permissions
ls -la .claude-mpm/agents/
```

### Validation Errors

```bash
# Validate frontmatter
python scripts/validate_agent_frontmatter.py agent.md

# Check JSON schema compliance
python scripts/validate_agent_configuration.py agent.json
```

### Precedence Issues

```bash
# Show which version is active
./claude-mpm agents show agent_name

# Force specific tier
./claude-mpm agents show agent_name --tier project
```

## Migration Guide

### From JSON to Markdown

```python
# Convert existing JSON agent to Markdown
import json
import yaml

with open('agent.json') as f:
    config = json.load(f)

frontmatter = {
    'description': config['metadata']['description'],
    'version': config.get('agent_version', '1.0.0'),
    'tools': config['capabilities']['tools'],
    'model': config['capabilities']['model']
}

with open('agent.md', 'w') as f:
    f.write('---\n')
    f.write(yaml.dump(frontmatter))
    f.write('---\n\n')
    f.write(config['instructions'])
```

### From v1 to v2 Schema

Key changes:
- `agent_version` → `version` in frontmatter
- `resource_limits` → `resource_tier`
- New `file_access` configuration
- Enhanced validation rules

## Related Documentation

- [Agent Schema Guide](./AGENT_SCHEMA_GUIDE.md)
- [Project Agents Guide](../../PROJECT_AGENTS.md)
- [Agent Compatibility Guide](./compatibility.md)
- [Frontmatter Validation](./frontmatter.md)
