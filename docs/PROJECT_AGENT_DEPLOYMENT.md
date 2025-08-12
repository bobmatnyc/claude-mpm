# Project Agent Deployment

This document explains how to create project-specific agents that override system agents in Claude MPM using the three-tier precedence system.

## Overview

Claude MPM supports project-specific agents in `.claude-mpm/agents/` that take precedence over system agents. This allows teams to define custom agents that override system defaults for their specific project needs using a flat directory structure.

**Important**: Project agents in `.claude-mpm/agents/` must be in **JSON format only**. The system automatically converts these to Markdown format in `.claude/agents/` for Claude Desktop/IDE compatibility.

## How It Works

### Agent Precedence

The agent system follows a three-tier precedence model:

1. **PROJECT** (Highest) - `.claude-mpm/agents/` in your project
2. **USER** - `~/.claude-mpm/agents/` in your home directory  
3. **SYSTEM** (Lowest) - Built-in framework agents

### Agent Discovery and Loading

When you run `claude-mpm`, the system automatically:

1. Scans for agent files in `.claude-mpm/agents/` (**JSON format only**)
2. Loads project agents with highest precedence in the three-tier system
3. Uses project agents to override system and user agents with the same name
4. Auto-converts JSON agents to Markdown in `.claude/agents/` for Claude Code compatibility
5. Caches loaded agents for performance

### Precedence Resolution

The agent system is intelligent:
- PROJECT agents always override USER and SYSTEM agents with the same name
- **JSON format required** in `.claude-mpm/agents/` directory
- Auto-generates `.claude/agents/*.md` files for Claude Desktop compatibility
- Changes to project agent JSON files are automatically detected and reloaded
- Deployment conversion happens automatically during loading

## Creating Project Agents

### Directory Structure

```
your-project/
├── .claude-mpm/
│   └── agents/                     # JSON only (source files)
│       ├── custom_engineer.json    # Override system engineer
│       ├── project_qa.json         # Project-specific QA agent
│       └── domain_expert.json      # New custom agent
├── .claude/
│   └── agents/                     # Auto-generated Markdown (Claude Code)
│       ├── custom_engineer.md      # Generated from JSON
│       ├── project_qa.md           # Generated from JSON
│       └── domain_expert.md        # Generated from JSON
└── src/
    └── ... (project source files)
```

### Agent Template Format

Create JSON files in `.claude-mpm/agents/` (flat structure, no subdirectories):

```json
{
  "agent_id": "custom_engineer",
  "version": "1.0.0",
  "metadata": {
    "name": "Project Engineer",
    "description": "Custom engineer agent with project-specific rules"
  },
  "capabilities": {
    "model": "claude-opus-4-20250514",
    "tools": ["Read", "Write", "Edit", "Bash", "ProjectTool"]
  },
  "instructions": "You are a project-specific engineer agent. Follow these project rules:\n\n1. Always use our custom coding standards\n2. Include project headers in all files\n3. Follow our specific architecture patterns"
}
```

### Overriding System Agents

To override a system agent (like `engineer`, `qa`, `documentation`), simply:

1. Create a JSON file with the same agent name
2. Place it in `.claude-mpm/agents/`
3. The project version will automatically override the system version

Example: Override the system QA agent:

```json
{
  "agent_id": "qa",
  "version": "2.0.0",
  "metadata": {
    "name": "Project QA",
    "description": "QA agent with project-specific test requirements"
  },
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["Read", "Bash", "Grep", "ProjectTestRunner"]
  },
  "instructions": "You are the QA agent for this project. Always:\n- Run our custom test suite\n- Check for project-specific issues\n- Validate against our quality standards"
}
```

## Agent Loading Process

### Automatic Loading

Project agents are loaded automatically when you run:

```bash
# Interactive mode
claude-mpm

# Non-interactive mode
claude-mpm run -i "Your task here"

# Check agent hierarchy
claude-mpm agents list --by-tier
```

You'll see which agents are active from each tier.

### Programmatic Access

You can also access agents programmatically:

```python
from claude_mpm.services.agents.registry import AgentRegistry

registry = AgentRegistry()
agents = registry.discover_agents()

# Check which tier an agent is loaded from
engineer = registry.get_agent("engineer")
print(f"Engineer agent loaded from: {engineer.tier.value} tier")
```

## Best Practices

### 1. Version Management

Always increment the version when updating agents:
```json
"version": "1.0.0"  // Initial version
"version": "1.1.0"  // Minor update
"version": "2.0.0"  // Major changes
```

### 2. Clear Instructions

Be specific in your agent instructions:
```json
"instructions": "You are a security-focused engineer for the FinTech project.\n\nAlways:\n- Validate all inputs\n- Use encryption for sensitive data\n- Follow OWASP guidelines\n- Add security tests for new features"
```

### 3. Tool Selection

Only include tools the agent needs:
```json
"tools": ["Read", "Write", "Edit", "Grep"]  // Minimal for documentation
"tools": ["Read", "Write", "Edit", "Bash", "WebSearch"]  // Full for engineer
```

### 4. Model Selection

Choose appropriate models:
- `claude-haiku-*` - Fast, simple tasks
- `claude-sonnet-*` - Balanced performance
- `claude-opus-*` - Complex reasoning

## Troubleshooting

### Agents Not Loading

1. Check directory structure:
   ```bash
   ls -la .claude-mpm/agents/
   ```

2. Verify file format (JSON, Markdown, or YAML):
   ```bash
   python -m json.tool .claude-mpm/agents/your_agent.json  # for JSON
   ```

3. Check agent hierarchy:
   ```bash
   claude-mpm agents list --by-tier
   ```

### Agent Not Overriding

1. Ensure the filename matches the agent name:
   - System agent: `engineer`
   - Your override: `.claude-mpm/agents/engineer.json` or `.claude-mpm/agents/engineer.md`

2. Verify the agent is in the PROJECT tier:
   ```bash
   claude-mpm agents view engineer
   # Should show: Tier: PROJECT
   ```

3. Check for configuration issues:
   ```bash
   claude-mpm agents fix --all --dry-run
   ```

### Updates Not Applying

1. Check the agent hierarchy after changes:
   ```bash
   claude-mpm agents list --by-tier
   ```

2. Clear agent cache if needed:
   ```bash
   python -c "from claude_mpm.agents.agent_loader import clear_agent_cache; clear_agent_cache()"
   ```

## Examples

### Custom Domain Expert

```json
{
  "agent_id": "ml_expert",
  "version": "1.0.0",
  "metadata": {
    "name": "Machine Learning Expert",
    "description": "Specialized agent for ML/AI tasks"
  },
  "capabilities": {
    "model": "claude-opus-4-20250514",
    "tools": ["Read", "Write", "Edit", "Bash", "WebSearch"]
  },
  "instructions": "You are an ML/AI expert. Focus on:\n- Model architecture design\n- Training optimization\n- Data preprocessing\n- Performance metrics\n- Deployment strategies"
}
```

### Project-Specific Security Agent

```json
{
  "agent_id": "security",
  "version": "3.0.0",
  "metadata": {
    "name": "Project Security Agent",
    "description": "Enhanced security agent with project rules"
  },
  "capabilities": {
    "model": "claude-opus-4-20250514",
    "tools": ["Read", "Grep", "Bash", "WebSearch"]
  },
  "instructions": "You are the security agent for our healthcare project.\n\nCritical requirements:\n- HIPAA compliance is mandatory\n- All data must be encrypted at rest and in transit\n- Audit all access to patient records\n- Flag any potential PII exposure\n- Validate against our security checklist"
}
```

## Integration with CI/CD

You can commit your project agents to version control:

```bash
# .gitignore (DO NOT ignore these)
# .claude-mpm/agents/  # Keep these in git

# Add and commit
git add .claude-mpm/agents/
git commit -m "feat: Add project-specific QA agent"
```

This ensures all team members get the same agent configurations.