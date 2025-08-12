# Agent Exclusion Configuration

This document explains how to configure agent exclusions in Claude MPM to prevent specific agents from being deployed.

## Overview

Claude MPM allows you to exclude specific agents from deployment through configuration. This is useful when:
- You want to reduce the number of deployed agents for performance
- Certain agents are not needed for your workflow
- You're testing or debugging specific agent interactions
- You want to deploy a minimal set of agents

## Configuration Methods

### 1. Configuration File (Recommended)

Create or edit `.claude-mpm/configuration.yaml` in your project directory:

```yaml
agent_deployment:
  # List of agent IDs to exclude from deployment
  excluded_agents:
    - research
    - data_engineer
    - ops
  
  # Whether agent name matching is case-sensitive
  case_sensitive: false
  
  # Whether to exclude agent dependencies (future feature)
  exclude_dependencies: false
```

### 2. Environment Variables

You can also configure exclusions using environment variables:

```bash
# Set excluded agents (comma-separated)
export CLAUDE_PM_AGENT_DEPLOYMENT_EXCLUDED_AGENTS="research,data_engineer,ops"

# Set case sensitivity
export CLAUDE_PM_AGENT_DEPLOYMENT_CASE_SENSITIVE=false
```

### 3. Programmatic Configuration

When using the Python API:

```python
from claude_mpm.core.config import Config
from claude_mpm.services.agents.deployment import AgentDeploymentService

# Create configuration
config = Config()
config.set('agent_deployment.excluded_agents', ['research', 'data_engineer'])
config.set('agent_deployment.case_sensitive', False)

# Deploy with exclusions
service = AgentDeploymentService()
results = service.deploy_agents(config=config)
```

## CLI Usage

### Deploy with Exclusions

When agents are configured for exclusion, the deployment will automatically skip them:

```bash
# Deploy agents (respects exclusion configuration)
claude-mpm agents deploy

# Output will show:
# ⚠️  Excluding agents from deployment: research, data_engineer, ops
# Deploying system agents...
```

### Override Exclusions

To temporarily deploy all agents regardless of exclusion configuration:

```bash
# Deploy all agents, ignoring exclusions
claude-mpm agents deploy --include-all
```

### Check Current Configuration

View which agents are configured for exclusion:

```bash
# Show current configuration
claude-mpm config show | grep agent_deployment
```

## Agent Names

The following agents can be excluded:

- `engineer` - Code implementation and development
- `qa` - Quality assurance and testing
- `security` - Security analysis and vulnerability assessment
- `documentation` - Documentation creation and maintenance
- `research` - Technical research and analysis
- `ops` - Operations and deployment management
- `data_engineer` - Data pipeline and AI integration
- `version_control` - Git operations and version management
- `code_analyzer` - Code analysis and metrics (if available)

## Case Sensitivity

The `case_sensitive` setting determines how agent names are matched:

- **`false` (default)**: Case-insensitive matching
  - `"research"` will match `"Research"`, `"RESEARCH"`, etc.
  - Recommended for most use cases

- **`true`**: Case-sensitive matching
  - `"research"` will only match exactly `"research"`
  - Use when you have agents with similar names differing only in case

## Important Notes

### System Exclusions

The following agents are **always** excluded and cannot be deployed:
- `pm` / `PM` / `project_manager` - The main Project Manager agent
- System files: `__init__`, `MEMORIES`, `TODOWRITE`, `INSTRUCTIONS`, `README`

These are hardcoded exclusions for system stability.

### Common Agent Warning

If you exclude commonly used agents (`engineer`, `qa`, `security`, `documentation`), you'll see a warning:

```
⚠️  Warning: Common agents are being excluded: engineer, qa
   This may affect normal operations. Use 'claude-mpm agents deploy --include-all' to override.
```

### Project vs System Agents

Exclusions apply to both:
- **System agents**: Built-in framework agents
- **Project agents**: Custom agents in `.claude-mpm/agents/`

## Examples

### Example 1: Minimal Deployment

Deploy only essential agents for development:

```yaml
agent_deployment:
  excluded_agents:
    - research
    - data_engineer
    - ops
    - version_control
```

### Example 2: Security-Focused Deployment

Deploy only security and QA agents:

```yaml
agent_deployment:
  excluded_agents:
    - engineer
    - documentation
    - research
    - ops
    - data_engineer
    - version_control
```

### Example 3: Documentation-Only Deployment

Deploy only documentation agent:

```yaml
agent_deployment:
  excluded_agents:
    - engineer
    - qa
    - security
    - research
    - ops
    - data_engineer
    - version_control
```

## Testing Exclusions

Use the test script to verify exclusion functionality:

```bash
# Run exclusion tests
python scripts/test_agent_exclusion.py
```

This will:
1. Test deployment without exclusions
2. Test deployment with exclusions
3. Verify case sensitivity settings
4. Test configuration file loading

## Troubleshooting

### Excluded Agents Still Appearing

1. Check configuration is loaded:
   ```bash
   claude-mpm config show
   ```

2. Verify agent names match exactly (or use case_insensitive):
   ```bash
   claude-mpm agents list --system
   ```

3. Ensure configuration file is in correct location:
   - Project: `.claude-mpm/configuration.yaml`
   - User: `~/.claude-mpm/configuration.yaml`

### Configuration Not Loading

1. Check file syntax (YAML formatting):
   ```bash
   python -c "import yaml; yaml.safe_load(open('.claude-mpm/configuration.yaml'))"
   ```

2. Verify environment variables:
   ```bash
   env | grep CLAUDE_PM_AGENT_DEPLOYMENT
   ```

### Override Not Working

The `--include-all` flag only works with:
- `claude-mpm agents deploy --include-all`
- `claude-mpm agents force-deploy --include-all`

## Best Practices

1. **Start with defaults**: Don't exclude agents unless you have a specific need
2. **Test thoroughly**: Verify your workflow works with excluded agents
3. **Document exclusions**: Add comments explaining why agents are excluded
4. **Use configuration files**: More maintainable than environment variables
5. **Consider dependencies**: Some agents may work better together

## Future Features

- **Dependency exclusion**: Automatically exclude agents that depend on excluded agents
- **Profile support**: Named exclusion profiles for different use cases
- **Dynamic exclusion**: Exclude agents based on runtime conditions
- **Exclusion validation**: Warn about problematic exclusion combinations