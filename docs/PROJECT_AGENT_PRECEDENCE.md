# PROJECT Agent Precedence Implementation

## Overview

This document describes the implementation of PROJECT-level agent precedence in claude-mpm, allowing projects to override framework agents with custom implementations.

## Architecture Changes

### 1. Agent Tier System

Implemented a three-tier precedence system in `/src/claude_mpm/agents/agent_loader.py`:

```python
class AgentTier(Enum):
    PROJECT = "project"  # Highest precedence - project-specific agents
    USER = "user"       # Medium precedence - user-level agents  
    SYSTEM = "system"   # Lowest precedence - framework built-in agents
```

### 2. Directory Structure

Agent templates are discovered from these locations:

- **PROJECT**: `{cwd}/.claude-mpm/agents/templates/` - Project-specific agents
- **USER**: `~/.claude-mpm/agents/templates/` - User-level customizations
- **SYSTEM**: Built-in framework agents

### 3. Loading Precedence

When an agent is requested, the system checks in this order:
1. PROJECT agents (if present in current working directory)
2. USER agents (if present in user home)
3. SYSTEM agents (always available)

The first match wins and overrides lower-precedence versions.

## Key Implementation Files

### Modified Files

1. **`/src/claude_mpm/agents/agent_loader.py`**
   - Added `AgentTier` enum for tier management
   - Updated `_get_agent_templates_dirs()` to discover all tiers
   - Modified `AgentLoader` to track tier source for each agent
   - Enhanced `_load_agents()` to process tiers in correct precedence order
   - Added `get_agent_tier()` function to check agent source
   - Added `list_agents_by_tier()` for debugging

2. **`/src/claude_mpm/services/framework_agent_loader.py`**
   - Updated to integrate with new tier system
   - Modified precedence logic to match PROJECT > USER > SYSTEM
   - Enhanced `load_agent_profile()` to respect new precedence

3. **`/src/claude_mpm/services/agent_profile_loader.py`**
   - Updated `ProfileTier` enum with precedence documentation
   - Ensured PROJECT tier has highest precedence

### New Files

1. **`/src/claude_mpm/config/agent_config.py`**
   - Configuration management for agent loading
   - Environment variable support for directory overrides
   - Precedence mode configuration (strict/override/merge)
   - Auto-discovery of agent directories

2. **`/scripts/test_project_agent_precedence.py`**
   - Comprehensive test suite for PROJECT precedence
   - Tests agent override functionality
   - Validates environment configuration
   - Ensures hot reload works correctly

## Configuration Options

### Environment Variables

- `CLAUDE_MPM_PROJECT_AGENTS_DIR`: Override project agents directory
- `CLAUDE_MPM_USER_AGENTS_DIR`: Override user agents directory  
- `CLAUDE_MPM_SYSTEM_AGENTS_DIR`: Override system agents directory
- `CLAUDE_MPM_AGENT_SEARCH_PATH`: Additional search paths (colon-separated)
- `CLAUDE_MPM_AGENT_PRECEDENCE`: Precedence mode (strict/override/merge)
- `CLAUDE_MPM_DISABLE_PROJECT_AGENTS`: Disable project agents
- `CLAUDE_MPM_DISABLE_USER_AGENTS`: Disable user agents
- `CLAUDE_MPM_DISABLE_SYSTEM_AGENTS`: Disable system agents
- `CLAUDE_MPM_AGENT_HOT_RELOAD`: Enable/disable hot reload
- `CLAUDE_MPM_AGENT_CACHE_TTL`: Cache TTL in seconds

### Configuration File

Projects can include `.claude-mpm/agent_config.yaml`:

```yaml
project_agents_dir: ./custom_agents
precedence_mode: override
enable_hot_reload: true
cache_ttl_seconds: 3600
```

## Usage Examples

### Creating a Project Agent

1. Create directory structure:
```bash
mkdir -p .claude-mpm/agents/templates
```

2. Add custom agent (e.g., `engineer.json`):
```json
{
  "agent_id": "engineer",
  "version": "1.0.0",
  "metadata": {
    "name": "Project Engineer Agent",
    "description": "Custom engineer for this project"
  },
  "instructions": "Project-specific engineering instructions...",
  "capabilities": {
    "model": "claude-sonnet-4-20250514",
    "tools": ["custom_tools"]
  }
}
```

3. The custom agent will automatically override the system engineer agent.

### Checking Agent Source

```python
from claude_mpm.agents.agent_loader import get_agent_tier, list_agents_by_tier

# Check which tier an agent is loaded from
tier = get_agent_tier("engineer")  # Returns: "project", "user", or "system"

# List all agents by tier
agents = list_agents_by_tier()
# Returns: {"project": [...], "user": [...], "system": [...]}
```

## Benefits

1. **Project Customization**: Projects can tailor agents to their specific needs
2. **Backward Compatibility**: Existing code continues to work without changes
3. **User Preferences**: Users can customize agents globally via ~/.claude-mpm
4. **Development Flexibility**: Easy testing of agent modifications
5. **Clean Separation**: Clear precedence rules prevent confusion

## Future Enhancements

1. **Merge Mode**: Option to merge agent capabilities across tiers
2. **Partial Overrides**: Override only specific agent sections
3. **Version Constraints**: Specify minimum/maximum agent versions
4. **Agent Inheritance**: Extend base agents instead of full replacement
5. **CLI Management**: Commands to manage project agents

## Testing

Run the test suite to verify PROJECT precedence:

```bash
python scripts/test_project_agent_precedence.py
```

This tests:
- System agent loading without project override
- Project agent creation and override
- Tier precedence validation
- Configuration system
- Hot reload functionality
- Environment variable configuration

## Migration Guide

For projects wanting to customize agents:

1. Create `.claude-mpm/agents/templates/` in your project root
2. Copy system agent templates you want to customize
3. Modify the agent instructions and capabilities
4. Test with `get_agent_tier()` to verify precedence
5. Commit `.claude-mpm/` to version control

## Troubleshooting

### Agent Not Loading from Project

1. Check directory structure: `.claude-mpm/agents/templates/`
2. Verify agent file naming (e.g., `engineer.json`)
3. Check JSON syntax and schema compliance
4. Use `list_agents_by_tier()` to see discovered agents
5. Enable debug logging to see discovery process

### Precedence Issues

1. Use `get_agent_tier("agent_name")` to check source
2. Verify no USER-level override interfering
3. Check environment variables aren't overriding paths
4. Ensure `reload_agents()` called after changes

## Conclusion

The PROJECT agent precedence system provides a powerful way for projects to customize claude-mpm's behavior while maintaining clean separation and backward compatibility. Projects can now have agents specifically tailored to their domain, coding standards, and workflows.