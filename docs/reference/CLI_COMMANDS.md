# Claude MPM CLI Commands Reference

Complete reference for all Claude MPM command-line interface commands, including the agent-manager local agent commands.

## Table of Contents

- [Core Commands](#core-commands)
- [Agent Manager Commands](#agent-manager-commands)
- [Local Agent Commands](#local-agent-commands)
- [Memory Commands](#memory-commands)
- [Project Commands](#project-commands)
- [Global Options](#global-options)

## Core Commands

### `claude-mpm run`

Execute a task using Claude MPM agents.

```bash
claude-mpm run [OPTIONS] [TASK]
```

**Options:**
- `--agent AGENT_ID`: Specify which agent to use
- `--model MODEL`: Override model (opus/sonnet/haiku)
- `--interactive`: Enable interactive mode
- `--debug`: Enable debug output
- `--format FORMAT`: Output format (text/json)

**Examples:**
```bash
# Run with default PM agent
claude-mpm run "Analyze the codebase structure"

# Run with specific agent
claude-mpm run --agent research "Research best practices for React testing"

# Run with local agent
claude-mpm run --agent custom-researcher "Analyze financial data trends"

# Interactive mode
claude-mpm run --interactive --agent documentation
```

### `claude-mpm init`

Initialize Claude MPM in a project directory.

```bash
claude-mpm init [OPTIONS]
```

**Options:**
- `--force`: Overwrite existing configuration
- `--template TEMPLATE`: Use configuration template

**Examples:**
```bash
# Basic initialization
claude-mpm init

# Force reinitialize
claude-mpm init --force
```

## Agent Manager Commands

The `agent-manager` command provides comprehensive agent lifecycle management.

### `claude-mpm agent-manager list`

List all agents across tiers with hierarchy.

```bash
claude-mpm agent-manager list [OPTIONS]
```

**Options:**
- `--format FORMAT`: Output format (text/json)
- `--tier TIER`: Filter by tier (project/user/system)

**Output shows:**
- **[P] PROJECT LEVEL**: Highest priority agents (local project agents)
- **[U] USER LEVEL**: User-specific agents
- **[S] SYSTEM LEVEL**: Framework default agents

**Examples:**
```bash
# List all agents
claude-mpm agent-manager list

# JSON output for scripting
claude-mpm agent-manager list --format json

# Filter by tier
claude-mpm agent-manager list --tier project
```

### `claude-mpm agent-manager create`

Create a new agent interactively or with parameters.

```bash
claude-mpm agent-manager create [OPTIONS]
```

**Options:**
- `--agent-id ID`: Agent identifier (required for non-interactive)
- `--name NAME`: Display name
- `--description DESC`: Agent description
- `--model MODEL`: AI model (opus/sonnet/haiku)
- `--tool-choice CHOICE`: Tool choice (auto/required/any/none)
- `--template TEMPLATE`: Base template to use

**Examples:**
```bash
# Interactive creation
claude-mpm agent-manager create

# Command-line creation
claude-mpm agent-manager create \
  --agent-id custom-analyzer \
  --name "Custom Code Analyzer" \
  --description "Analyzes code quality and patterns" \
  --model sonnet \
  --tool-choice auto
```

### `claude-mpm agent-manager variant`

Create an agent variant based on an existing agent.

```bash
claude-mpm agent-manager variant [OPTIONS]
```

**Required Options:**
- `--base-agent ID`: Base agent to inherit from
- `--variant-id ID`: New variant identifier

**Optional:**
- `--name NAME`: Variant display name
- `--model MODEL`: Override model
- `--tool-choice CHOICE`: Override tool choice
- `--instructions TEXT`: Additional instructions

**Examples:**
```bash
# Create research variant with different model
claude-mpm agent-manager variant \
  --base-agent research \
  --variant-id research-fast \
  --model haiku \
  --name "Fast Research Assistant"

# Add custom instructions
claude-mpm agent-manager variant \
  --base-agent documentation \
  --variant-id doc-api \
  --instructions "Focus specifically on API documentation"
```

### `claude-mpm agent-manager deploy`

Deploy an agent to specified tier.

```bash
claude-mpm agent-manager deploy [OPTIONS]
```

**Required Options:**
- `--agent-id ID`: Agent to deploy

**Optional:**
- `--tier TIER`: Deployment tier (project/user) - defaults to project

**Examples:**
```bash
# Deploy to project level (default)
claude-mpm agent-manager deploy --agent-id custom-analyzer

# Deploy to user level
claude-mpm agent-manager deploy --agent-id personal-helper --tier user
```

### `claude-mpm agent-manager show`

Display detailed agent information.

```bash
claude-mpm agent-manager show AGENT_ID [OPTIONS]
```

**Options:**
- `--format FORMAT`: Output format (text/json)

**Examples:**
```bash
# Show agent details
claude-mpm agent-manager show research

# JSON format
claude-mpm agent-manager show custom-analyzer --format json
```

### `claude-mpm agent-manager test`

Test and validate agent configuration.

```bash
claude-mpm agent-manager test AGENT_ID
```

**Examples:**
```bash
# Test agent configuration
claude-mpm agent-manager test custom-analyzer
```

### `claude-mpm agent-manager templates`

List available agent templates.

```bash
claude-mpm agent-manager templates [OPTIONS]
```

**Options:**
- `--format FORMAT`: Output format (text/json)

**Examples:**
```bash
# List templates
claude-mpm agent-manager templates

# JSON output
claude-mpm agent-manager templates --format json
```

### `claude-mpm agent-manager reset`

Remove claude-mpm authored agents for clean installation.

```bash
claude-mpm agent-manager reset [OPTIONS]
```

**Options:**
- `--dry-run`: Show what would be removed without actually removing
- `--force`: Skip confirmation prompt
- `--project-only`: Only clean project directory
- `--user-only`: Only clean user directory
- `--format FORMAT`: Output format (text/json)

**Examples:**
```bash
# Dry run to see what would be removed
claude-mpm agent-manager reset --dry-run

# Force removal without confirmation
claude-mpm agent-manager reset --force

# Clean only project agents
claude-mpm agent-manager reset --project-only

# Clean only user agents  
claude-mpm agent-manager reset --user-only
```

### `claude-mpm agent-manager customize-pm`

Customize PM instructions via `.claude-mpm/INSTRUCTIONS.md`.

```bash
claude-mpm agent-manager customize-pm [OPTIONS]
```

**Options:**
- `--level LEVEL`: Customization level (user/project)
- `--template TEMPLATE`: Use predefined template
- `--patterns PATTERNS`: Delegation patterns
- `--workflows WORKFLOWS`: Workflow overrides
- `--rules RULES`: Custom rules

**Examples:**
```bash
# Customize at project level
claude-mpm agent-manager customize-pm --level project

# Use template
claude-mpm agent-manager customize-pm --template basic
```

## Local Agent Commands

Local agent commands manage project-specific agent templates stored as JSON files.

### `claude-mpm agent-manager create-local`

Create a new local agent template.

```bash
claude-mpm agent-manager create-local [OPTIONS]
```

**Required Options:**
- `--agent-id ID`: Unique agent identifier

**Optional:**
- `--name NAME`: Human-readable name
- `--description DESC`: Agent description  
- `--instructions TEXT`: Agent behavior instructions
- `--model MODEL`: AI model (opus/sonnet/haiku, default: sonnet)
- `--tools TOOLS`: Tool access ("*" for all, or comma-separated list)
- `--parent PARENT_ID`: Inherit from system agent
- `--tier TIER`: Storage tier (project/user, default: project)

**Examples:**
```bash
# Basic local agent
claude-mpm agent-manager create-local \
  --agent-id financial-analyst \
  --name "Financial Analyst" \
  --description "Expert in financial modeling and analysis"

# Agent with custom instructions
claude-mpm agent-manager create-local \
  --agent-id code-reviewer \
  --name "Senior Code Reviewer" \
  --instructions "You are a senior engineer focused on code quality, security, and maintainability. Always check for performance issues and suggest optimizations." \
  --model sonnet

# Inherit from system agent
claude-mpm agent-manager create-local \
  --agent-id custom-researcher \
  --parent research \
  --name "Domain Research Assistant" \
  --instructions "Like the research agent, but with expertise in financial services"

# User-tier agent
claude-mpm agent-manager create-local \
  --agent-id personal-assistant \
  --name "Personal AI Assistant" \
  --tier user
```

### `claude-mpm agent-manager deploy-local`

Deploy local JSON templates to Claude Code.

```bash
claude-mpm agent-manager deploy-local [OPTIONS]
```

**Options:**
- `--agent-id ID`: Deploy specific agent (if omitted, deploys all)
- `--force`: Force deployment, overwrite existing
- `--tier TIER`: Filter by tier (project/user)

**Examples:**
```bash
# Deploy all local agents
claude-mpm agent-manager deploy-local

# Deploy specific agent
claude-mpm agent-manager deploy-local --agent-id financial-analyst

# Force redeploy (overwrite existing)
claude-mpm agent-manager deploy-local --agent-id code-reviewer --force

# Deploy only project agents
claude-mpm agent-manager deploy-local --tier project
```

**Output includes:**
- Number of agents deployed
- Number of agents updated
- Number of agents skipped
- Any errors encountered

### `claude-mpm agent-manager list-local`

List all local agent templates.

```bash
claude-mpm agent-manager list-local [OPTIONS]
```

**Options:**
- `--tier TIER`: Filter by tier (project/user)
- `--format FORMAT`: Output format (text/json)

**Examples:**
```bash
# List all local agents
claude-mpm agent-manager list-local

# List only project agents
claude-mpm agent-manager list-local --tier project

# JSON output for scripting
claude-mpm agent-manager list-local --format json
```

**Text Output Format:**
```
Local Agent Templates:

PROJECT AGENTS:
  • financial-analyst (v1.0.0) - Financial Analyst
    Expert in financial modeling and analysis
  • code-reviewer (v1.2.0) - Senior Code Reviewer
    Thorough code review with security focus

USER AGENTS:
  • personal-assistant (v1.0.0) - Personal AI Assistant
    General purpose personal assistant
```

### `claude-mpm agent-manager sync-local`

Synchronize local templates with deployed agents.

```bash
claude-mpm agent-manager sync-local
```

**This command:**
- Adds templates for deployed local agents that don't have templates
- Updates templates that have changed since deployment
- Removes templates for agents no longer deployed
- Reports summary of changes

**Example output:**
```
Local Agent Synchronization:
  Added: 2
  Updated: 1
  Removed: 0

Added agents: new-analyzer, domain-expert
Updated agents: financial-analyst
```

### `claude-mpm agent-manager export-local`

Export local agent templates to a directory.

```bash
claude-mpm agent-manager export-local [OPTIONS]
```

**Options:**
- `--output DIR`: Output directory (default: ./exported-agents)

**Examples:**
```bash
# Export to default directory
claude-mpm agent-manager export-local

# Export to specific directory
claude-mpm agent-manager export-local --output ./team-agents

# Export for sharing
claude-mpm agent-manager export-local --output ./shared-agents
```

**Creates individual JSON files:**
```
exported-agents/
├── financial-analyst.json
├── code-reviewer.json
└── domain-expert.json
```

### `claude-mpm agent-manager import-local`

Import agent templates from a directory.

```bash
claude-mpm agent-manager import-local [OPTIONS]
```

**Required Options:**
- `--input DIR`: Directory containing template JSON files

**Optional:**
- `--tier TIER`: Import tier (project/user, default: project)

**Examples:**
```bash
# Import from directory as project agents
claude-mpm agent-manager import-local --input ./shared-agents

# Import as user agents
claude-mpm agent-manager import-local --input ./personal-agents --tier user

# Import team templates
claude-mpm agent-manager import-local --input ./team-shared-agents
```

## Memory Commands

Manage agent memory and learning system.

### `claude-mpm memory init`

Initialize memory system for the project.

```bash
claude-mpm memory init [OPTIONS]
```

### `claude-mpm memory show`

Display agent memories and learnings.

```bash
claude-mpm memory show [OPTIONS]
```

### `claude-mpm memory status`

Show memory system status and statistics.

```bash
claude-mpm memory status
```

## Project Commands

### `claude-mpm analyze`

Analyze project structure and generate insights.

```bash
claude-mpm analyze [OPTIONS] [PATH]
```

**Options:**
- `--depth DEPTH`: Analysis depth
- `--format FORMAT`: Output format
- `--agent AGENT`: Agent to use for analysis

### `claude-mpm monitor`

Start the monitoring dashboard.

```bash
claude-mpm monitor [OPTIONS]
```

**Options:**
- `--port PORT`: Dashboard port (default: 8080)
- `--host HOST`: Host to bind to

## Global Options

These options are available for most commands:

- `--verbose, -v`: Increase output verbosity
- `--quiet, -q`: Suppress non-essential output
- `--config FILE`: Use alternate configuration file
- `--working-dir DIR`: Change working directory
- `--no-cache`: Disable caching
- `--help, -h`: Show command help

## Environment Variables

- `CLAUDE_MPM_CONFIG`: Path to configuration file
- `CLAUDE_MPM_CACHE_DIR`: Cache directory
- `CLAUDE_MPM_LOG_LEVEL`: Log level (DEBUG/INFO/WARNING/ERROR)
- `CLAUDE_MPM_NO_COLOR`: Disable colored output

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Configuration error
- `4`: Agent not found
- `5`: Deployment error
- `130`: Interrupted by user (Ctrl+C)

## Command Chaining Examples

### Complete Local Agent Workflow

```bash
# Create, deploy, and test a local agent
claude-mpm agent-manager create-local \
  --agent-id api-documenter \
  --name "API Documentation Specialist" \
  --instructions "Expert in creating comprehensive API documentation" &&
claude-mpm agent-manager deploy-local --agent-id api-documenter &&
claude-mpm run --agent api-documenter "Document the REST API endpoints"
```

### Team Sharing Workflow

```bash
# Export agents for sharing
claude-mpm agent-manager export-local --output ./team-agents

# Team member imports and deploys
claude-mpm agent-manager import-local --input ./team-agents &&
claude-mpm agent-manager deploy-local
```

### Agent Development Cycle

```bash
# Create agent
claude-mpm agent-manager create-local --agent-id test-analyzer

# Test and iterate
claude-mpm run --agent test-analyzer "Analyze this test file"

# Update template (edit JSON file)
nano .claude-mpm/agents/test-analyzer.json

# Redeploy with changes
claude-mpm agent-manager deploy-local --agent-id test-analyzer --force
```

## Troubleshooting Commands

### Check Agent Status
```bash
# List all agents to see hierarchy
claude-mpm agent-manager list

# Show specific agent details
claude-mpm agent-manager show my-agent

# Test agent configuration
claude-mpm agent-manager test my-agent
```

### Debug Deployment Issues
```bash
# Check local templates
claude-mpm agent-manager list-local

# Try deployment with force
claude-mpm agent-manager deploy-local --agent-id problem-agent --force

# Sync to fix inconsistencies
claude-mpm agent-manager sync-local
```

### Clean Up Problems
```bash
# See what would be reset
claude-mpm agent-manager reset --dry-run

# Remove problematic agents
claude-mpm agent-manager reset --force

# Redeploy clean agents
claude-mpm agent-manager deploy-local
```

This CLI reference provides comprehensive documentation for all Claude MPM commands with emphasis on the new local agent management capabilities.