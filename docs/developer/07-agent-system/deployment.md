# Agent Deployment Guide

## Critical Format Requirements

### ⚠️ TOOLS FIELD FORMAT - CRITICAL

**The `tools` field MUST be comma-separated WITHOUT spaces between tools.**

❌ **WRONG** (breaks deployment):
```yaml
tools: "Read, Write, Edit, Bash"  # SPACES WILL BREAK AGENT DEPLOYMENT!
```

✅ **CORRECT**:
```yaml
tools: "Read,Write,Edit,Bash"     # No spaces between commas
```

or as array:
```yaml
tools:
  - Read
  - Write
  - Edit
  - Bash
```

**Why this matters:**
- Claude Desktop/Code expects exact tool names without spaces
- Adding spaces causes tool validation failures
- Agents may fail to deploy or have missing capabilities
- This is a common deployment failure point

## Deployment Process

### 1. Agent Location Hierarchy

Agents are loaded with the following precedence:
1. **PROJECT** - `.claude-mpm/agents/` (JSON format required)
2. **USER** - `~/.claude-mpm/agents/` (any format)
3. **SYSTEM** - Built-in framework agents

### 2. Format Conversion

During deployment, JSON agents are automatically converted to Markdown:

```
.claude-mpm/agents/engineer.json  →  .claude/agents/engineer.md
      (SOURCE - JSON)                  (DEPLOYED - Markdown)
```

### 3. Deployment Commands

```bash
# Deploy agents (converts JSON to Markdown)
claude-mpm agents deploy

# Deploy with exclusions (from configuration.yaml)
claude-mpm agents deploy

# Deploy all agents, ignoring exclusions
claude-mpm agents deploy --include-all

# Force redeploy all agents
claude-mpm agents deploy --force

# Clean deployed agents (remove .claude/agents/)
claude-mpm agents clean
```

### 4. Metadata Enhancement

When creating agents, provide rich metadata for better PM understanding:

```yaml
---
name: engineer
description: Advanced code implementation specialist with AST analysis, refactoring capabilities, and security scanning. Implements production-quality code following discovered patterns.
authority: Full code implementation and refactoring authority within project constraints
primary_function: Transform research findings into production code
handoff_to: qa-agent for testing, security-agent for auditing
tools: "Read,Write,Edit,MultiEdit,Bash,Grep,Glob,LS,WebSearch,TodoWrite"
model: opus
---
```

Key metadata fields:
- **description**: Rich description of capabilities and specialization
- **authority**: What the agent is authorized to do
- **primary_function**: Core responsibility
- **handoff_to**: Which agents to delegate to next
- **tools**: Comma-separated WITHOUT spaces!

## Common Deployment Issues

### Issue 1: Tools Not Working
**Symptom**: Agent can't use expected tools
**Cause**: Spaces in tools field
**Fix**: Remove ALL spaces from comma-separated tools list

### Issue 2: Agent Not Found
**Symptom**: PM can't find agent for delegation
**Cause**: Agent not deployed or wrong ID
**Fix**: Check `.claude/agents/` for deployed files, verify agent ID matches filename

### Issue 3: Metadata Not Appearing
**Symptom**: Agent description missing in PM instructions
**Cause**: Invalid YAML frontmatter format
**Fix**: Ensure frontmatter is between `---` markers and valid YAML

## Validation

Before deploying, validate your agent:

```bash
# List agents to verify they're recognized
claude-mpm agents list --by-tier

# Check deployed agents
ls -la .claude/agents/

# Verify tools format (no spaces!)
grep "tools:" .claude-mpm/agents/*.json | grep ", "
# Should return nothing if correct
```

## Best Practices

1. **Always test locally first**: Deploy to `.claude-mpm/agents/` before system-wide
2. **Keep tools minimal**: Only include tools the agent actually needs
3. **Rich descriptions**: Help the PM understand when to use each agent
4. **Document handoffs**: Specify which agents should receive work next
5. **NO SPACES IN TOOLS**: This cannot be emphasized enough!

## Troubleshooting

### Debug Deployment
```bash
# Enable debug logging
export CLAUDE_MPM_DEBUG=1
claude-mpm agents deploy

# Check deployment logs
tail -f ~/.claude-mpm/logs/deployment.log
```

### Verify Agent Loading
```python
# Test agent loading
from claude_mpm.agents.agent_registry import AgentRegistry
registry = AgentRegistry()
agents = registry.list_agents()
for agent_id, agent in agents.items():
    print(f"{agent_id}: tools={agent.get('capabilities', {}).get('tools', 'none')}")
```

Remember: **The most common deployment failure is spaces in the tools field!**