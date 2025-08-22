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
- Claude Code/Code expects exact tool names without spaces
- Adding spaces causes tool validation failures
- Agents may fail to deploy or have missing capabilities
- This is a common deployment failure point

## Overview

As of v4.0.32+, Claude MPM has simplified agent deployment by consolidating all agents to project-level directories. This change improves consistency, isolation, and portability while maintaining full backward compatibility.

### Key Changes in v4.0.32+

- **Unified Deployment Location**: All agents deploy to `<project>/.claude/agents/` regardless of source tier
- **Maintained Discovery**: Agents are still discovered from PROJECT, USER, and SYSTEM tiers  
- **Backward Compatibility**: Existing CLI parameters continue to work
- **Project Isolation**: Each project maintains its own agent environment

## Deployment Process

### 1. Agent Location Hierarchy

**Source Locations** (where agents are discovered):
1. **PROJECT** - `.claude-mpm/agents/` (JSON format required)
2. **USER** - `~/.claude-mpm/agents/` (any format)
3. **SYSTEM** - Built-in framework agents

**Deployment Location** (v4.0.32+):
- **ALL AGENTS**: `<project>/.claude/agents/` (regardless of source tier)

The three-tier precedence system applies during discovery, but all agents deploy to the same project-level location.

### 2. Format Conversion and Deployment

During deployment, all agents are automatically converted to Markdown format and placed in the project directory:

**Project Agents:**
```
.claude-mpm/agents/engineer.json  →  <project>/.claude/agents/engineer.md
      (SOURCE - JSON)                      (DEPLOYED - Markdown)
```

**User Agents:**
```
~/.claude-mpm/agents/research.yaml  →  <project>/.claude/agents/research.md
       (SOURCE - YAML)                       (DEPLOYED - Markdown)
```

**System Agents:**
```
src/claude_mpm/agents/templates/qa.json  →  <project>/.claude/agents/qa.md
         (SOURCE - JSON)                         (DEPLOYED - Markdown)
```

### 3. Deployment Commands

**All deployment commands now deploy to project directory only (v4.0.32+):**

```bash
# Deploy agents from all tiers to project directory
claude-mpm agents deploy

# Deploy with exclusions (from configuration.yaml)
claude-mpm agents deploy

# Deploy all agents, ignoring exclusions
claude-mpm agents deploy --include-all

# Force redeploy all agents
claude-mpm agents deploy --force

# Clean deployed agents (remove .claude/agents/)
claude-mpm agents clean

# Legacy tier parameter (maintained for compatibility)
claude-mpm agents deploy --tier user    # Still deploys to project
claude-mpm agents deploy --tier project # Still deploys to project
```

**Important**: The `--tier` parameter no longer affects deployment location but is maintained for backward compatibility.

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

## Migration from Previous Versions

### For Existing Users (v4.0.31 and earlier)

If you have agents deployed in `~/.claude/agents/`, they will continue to work until overridden by new deployments:

```bash
# Check for old deployments
ls -la ~/.claude/agents/

# Deploy agents to current project (recommended)
cd /path/to/your/project
claude-mpm agents deploy

# Verify project deployment
ls -la .claude/agents/

# Optional: Clean up old user-level deployments
rm -rf ~/.claude/agents/  # Only if you no longer need them globally
```

### Developer Integration Changes

**Code Changes Required**: None. The deployment service automatically handles the new behavior.

**CLI Scripts**: Existing scripts using `--tier` parameters will continue to work but all deployments go to project directory:

```bash
# These all deploy to the same location now
claude-mpm agents deploy --tier user     # → <project>/.claude/agents/
claude-mpm agents deploy --tier project  # → <project>/.claude/agents/
claude-mpm agents deploy                 # → <project>/.claude/agents/
```

### Benefits of the New Approach

1. **Consistency**: Eliminates confusion about where agents are deployed
2. **Project Isolation**: Projects don't interfere with each other's agents
3. **Portability**: Agent deployments travel with the project
4. **Simplified Management**: Single location to manage per project
5. **Team Collaboration**: Project agents are easily shared via version control

## User Agent Cleanup Feature

### Overview

Claude MPM v4.0.32+ includes automatic cleanup of outdated user agents during deployment. This feature ensures users always have the latest agent versions and prevents version conflicts.

### Technical Implementation

The cleanup mechanism is integrated into the `MultiSourceAgentDeploymentService` and operates during the deployment process:

**1. Agent Discovery and Version Analysis:**
```python
# During deployment, the service discovers agents from all tiers
discovered_agents = {
    'project': scan_project_agents(),
    'user': scan_user_agents(), 
    'system': scan_system_agents()
}

# Compare versions across tiers
for agent_name in user_agents:
    user_version = parse_version(user_agents[agent_name]['version'])
    
    # Check if project or system has newer version
    if (project_agents.get(agent_name) and 
        parse_version(project_agents[agent_name]['version']) > user_version):
        mark_for_cleanup(agent_name, 'project supersedes user')
    
    elif (system_agents.get(agent_name) and 
          parse_version(system_agents[agent_name]['version']) > user_version):
        mark_for_cleanup(agent_name, 'system supersedes user')
```

**2. Safe Cleanup Process:**
```python
def cleanup_outdated_user_agents(self):
    """Remove outdated user agents that are superseded by newer versions."""
    cleanup_count = 0
    
    for agent_path in agents_to_cleanup:
        try:
            # Log before removal
            logger.info(f"Removing outdated user agent: {agent_name} v{old_version} "
                       f"(superseded by {source} v{new_version})")
            
            # Safely remove the agent file
            os.remove(agent_path)
            cleanup_count += 1
            
        except OSError as e:
            logger.warning(f"Failed to remove {agent_path}: {e}")
    
    if cleanup_count > 0:
        logger.info(f"Cleanup complete: removed {cleanup_count} outdated user agents")
```

### Configuration Options

**Environment Variable:**
```bash
# Disable cleanup (enabled by default)
export CLAUDE_MPM_CLEANUP_USER_AGENTS=false
```

**Configuration File:**
```yaml
# .claude-mpm/config.yaml
agent_deployment:
  cleanup_outdated_user_agents: false
```

**Runtime Check:**
```python
def should_cleanup_user_agents(self) -> bool:
    """Check if user agent cleanup is enabled."""
    # Check environment variable first
    env_value = os.environ.get('CLAUDE_MPM_CLEANUP_USER_AGENTS', 'true')
    if env_value.lower() == 'false':
        return False
    
    # Check configuration file
    config = self.get_config()
    return config.get('agent_deployment', {}).get('cleanup_outdated_user_agents', True)
```

### Safety Mechanisms

**1. Selective Targeting:**
- Only removes files from `~/.claude-mpm/agents/` directory
- Never touches project (`<project>/.claude-mpm/agents/`) or system agent files
- Validates file paths to prevent directory traversal

**2. Version-Based Logic:**
- Only removes user agents with lower version numbers
- Preserves user agents with same or higher versions than alternatives
- Uses semantic version comparison for accuracy

**3. Error Handling:**
```python
def safe_remove_agent(self, agent_path: Path, agent_info: dict):
    """Safely remove a user agent with comprehensive error handling."""
    try:
        # Validate path is within user agents directory
        user_agents_dir = Path.home() / '.claude-mpm' / 'agents'
        if not agent_path.is_relative_to(user_agents_dir):
            logger.error(f"Path outside user agents directory: {agent_path}")
            return False
        
        # Remove the file
        agent_path.unlink()
        logger.info(f"Removed outdated user agent: {agent_info['name']} v{agent_info['version']}")
        return True
        
    except FileNotFoundError:
        logger.debug(f"Agent file already removed: {agent_path}")
        return True
    except PermissionError:
        logger.warning(f"Permission denied removing {agent_path}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error removing {agent_path}: {e}")
        return False
```

### Logging and Observability

**Cleanup Actions:**
```
INFO: Agent cleanup started for deployment
INFO: Removing outdated user agent: engineer v1.8.0 (superseded by project v2.5.0)
INFO: Removing outdated user agent: qa v1.2.0 (superseded by system v1.3.0)
INFO: Preserving user agent: custom_tool v1.0.0 (no alternative found)
INFO: Cleanup complete: removed 2 outdated user agents, preserved 1
```

**Error Scenarios:**
```
WARNING: Failed to remove outdated user agent engineer.json: Permission denied
ERROR: Path outside user agents directory: /etc/passwd
DEBUG: User agent cleanup disabled via configuration
```

### Testing the Cleanup Feature

**Manual Testing:**
```bash
# 1. Create test user agent with lower version
mkdir -p ~/.claude-mpm/agents
cat > ~/.claude-mpm/agents/test_agent.json << 'EOF'
{
  "agent_id": "test_agent",
  "version": "1.0.0",
  "instructions": "Test agent for cleanup testing"
}
EOF

# 2. Create project agent with higher version
mkdir -p .claude-mpm/agents  
cat > .claude-mpm/agents/test_agent.json << 'EOF'
{
  "agent_id": "test_agent", 
  "version": "2.0.0",
  "instructions": "Updated test agent"
}
EOF

# 3. Deploy and observe cleanup
claude-mpm agents deploy --debug

# 4. Verify user agent was removed
ls ~/.claude-mpm/agents/test_agent.json  # Should not exist
```

**Automated Testing:**
```python
def test_user_agent_cleanup():
    """Test that outdated user agents are cleaned up during deployment."""
    # Setup: Create user agent with v1.0.0
    create_user_agent("test_agent", "1.0.0")
    
    # Setup: Create system agent with v2.0.0  
    create_system_agent("test_agent", "2.0.0")
    
    # Execute: Deploy agents
    deployment_service = MultiSourceAgentDeploymentService()
    deployment_service.deploy_agents()
    
    # Verify: User agent should be removed
    assert not user_agent_exists("test_agent")
    
    # Verify: Deployment contains system agent
    deployed = get_deployed_agents()
    assert deployed["test_agent"]["version"] == "2.0.0"
```

### Performance Considerations

**Efficient Version Comparison:**
```python
from packaging import version

def compare_agent_versions(v1: str, v2: str) -> int:
    """Compare two version strings using semantic versioning."""
    try:
        return version.parse(v1).__cmp__(version.parse(v2))
    except version.InvalidVersion:
        # Fallback to string comparison for non-semantic versions
        return (v1 > v2) - (v1 < v2)
```

**Batch Operations:**
```python
def cleanup_user_agents_batch(self, agents_to_remove: List[Path]):
    """Remove multiple user agents in a single operation."""
    success_count = 0
    error_count = 0
    
    for agent_path in agents_to_remove:
        try:
            agent_path.unlink()
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to remove {agent_path}: {e}")
            error_count += 1
    
    logger.info(f"Cleanup batch complete: {success_count} removed, {error_count} errors")
```

## Architecture Notes

The `MultiSourceAgentDeploymentService` maintains the three-tier discovery system with integrated cleanup:

- **Discovery**: Scans PROJECT → USER → SYSTEM locations for agent definitions
- **Version Analysis**: Compares versions across tiers to identify outdated user agents  
- **Cleanup**: Removes outdated user agents before deployment
- **Precedence**: Higher tiers override lower tiers during discovery
- **Deployment**: All discovered agents deploy to project directory regardless of source

This architecture preserves the flexibility of the tier system while simplifying deployment logistics and maintaining clean agent environments.