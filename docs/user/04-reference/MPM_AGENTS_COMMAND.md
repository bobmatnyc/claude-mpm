# Agent Management Commands Documentation

## Overview

Claude MPM provides comprehensive agent management through the `claude-mpm agents` command family. These commands help you understand, inspect, and maintain agents across the three-tier system (PROJECT > USER > SYSTEM).

### Command Access

1. **CLI**: `claude-mpm agents <subcommand>`
2. **Interactive Mode**: `/mpm:agents` (version display only)
3. **Claude Code**: `/mpm agents` (version display only)

## Command Family

### Quick Version Display (`claude-mpm agents`)

When called without a subcommand, displays deployed agent versions:
- All deployed agent names and their versions
- The base agent version
- Migration warnings if agents need semantic versioning updates

### Comprehensive Agent Management

| Command | Purpose | Key Features |
|---------|---------|--------------|
| `agents list --by-tier` | View agent hierarchy | Shows PROJECT > USER > SYSTEM precedence |
| `agents view <name>` | Inspect agent details | Frontmatter, instructions, file stats |
| `agents fix [name]` | Fix configuration issues | Auto-repair frontmatter, dry-run mode |
| `agents list --system` | List system templates | Available framework agents |
| `agents list --deployed` | List deployed agents | Claude Code native agents |

## Usage Examples

### Quick Version Display

**From Command Line:**
```bash
# Show deployed agent versions
claude-mpm agents

# Alternative syntax
claude-mpm --mpm:agents
```

**From Claude Code:**
```
/mpm agents
```

**From Interactive Wrapper:**
```
/mpm:agents
```

### Advanced Agent Management

**View Agent Hierarchy (Most Important):**
```bash
# See which agents are active and their precedence
claude-mpm agents list --by-tier
```

**Inspect Specific Agent:**
```bash
# View comprehensive agent information
claude-mpm agents view engineer
claude-mpm agents view payment_processor
```

**Fix Configuration Issues:**
```bash
# Preview fixes without applying them
claude-mpm agents fix engineer --dry-run
claude-mpm agents fix --all --dry-run

# Apply fixes
claude-mpm agents fix engineer
claude-mpm agents fix --all
```

**List Agent Categories:**
```bash
# Show system agent templates
claude-mpm agents list --system

# Show deployed agents for Claude Code
claude-mpm agents list --deployed
```

## Output Formats

### Version Display Output

```
Deployed Agent Versions:
----------------------------------------
  data_engineer        1.0.0
  documentation        1.0.0
  engineer             1.0.0
  ops                  1.0.0
  qa                   1.0.0
  research             2.1.0
  security             1.0.0
  version_control      1.0.0

  Base Agent Version:  0.2.0
----------------------------------------
```

### `--by-tier` Output Sample

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
       Description: Specialized payment flow agent
       File: payment_processor.json


─────────────────────────────────────── SYSTEM TIER ──────────────────────────────────────
  Location: Built-in framework agents

  Found 10 agent(s):

    📄 engineer             [⊗ OVERRIDDEN by PROJECT]
       Description: Software engineering specialist
       File: engineer.json

    📄 qa                   [✓ ACTIVE]
       Description: Quality assurance specialist
       File: qa.json

================================================================================
SUMMARY:
  Total unique agents: 11
  Project agents: 2
  User agents: 0
  System agents: 10
================================================================================
```

### `view` Command Output Sample

```
================================================================================
 AGENT: engineer
================================================================================

📋 BASIC INFORMATION:
  Name: engineer
  Type: development
  Tier: PROJECT
  Path: /project/.claude-mpm/agents/engineer.md
  Description: Custom engineer for this project

📝 FRONTMATTER:
  description: Custom engineer for this project
  version: 2.1.0
  tools: [project_linter, custom_debugger]
  model: claude-sonnet-4-20250514

📖 INSTRUCTIONS PREVIEW (first 500 chars):
  --------------------------------------------------------------------------
  # Project Engineer Agent

  You are an expert software engineer with deep knowledge of this project's
  architecture and conventions...

  [Truncated - 2.3KB total]
  --------------------------------------------------------------------------

📊 FILE STATS:
  Size: 2,347 bytes
  Last modified: 2025-01-15 14:32:45

================================================================================
```

### `fix --dry-run` Output Sample

```
🔍 DRY RUN MODE - No changes will be made

📄 engineer:
  🔧 Would fix:
    - Add missing required field: version
    - Convert tools from string to array format
    - Standardize field name: desc → description

================================================================================
SUMMARY:
  Agents checked: 1
  Total issues found: 3
  Issues that would be fixed: 3

💡 Run without --dry-run to apply fixes
================================================================================
```

## Implementation Details

The command uses a single source of truth function (`_get_agent_versions_display()`) that:
1. Queries the `AgentDeploymentService` for deployed agents
2. Sorts agents alphabetically by name
3. Formats the output in a consistent table format
4. Includes base agent version information
5. Shows migration warnings if applicable

## Integration Points

1. **CLI (`cli/commands/agents.py`)**: 
   - `manage_agents()` function handles the command when no subcommand is provided
   - Uses `get_agent_versions_display()` from `cli/utils.py` for consistent output

2. **Interactive Wrapper (`simple_runner.py`)**:
   - `_handle_mpm_command()` routes `/mpm:agents` to the display function

3. **Claude Code Hooks (`hook_handler.py`)**:
   - `_handle_mpm_agents()` intercepts `/mpm agents` and displays versions
   - Blocks LLM processing with exit code 2

## Common Workflows

### Daily Development Workflow

```bash
# 1. Check agent hierarchy when starting work
claude-mpm agents list --by-tier

# 2. If issues found, inspect specific agents
claude-mpm agents view problematic_agent

# 3. Fix configuration issues
claude-mpm agents fix --all --dry-run
claude-mpm agents fix --all  # if fixes look good

# 4. Start working with confidence
claude-mpm run --monitor
```

### Troubleshooting Workflow

```bash
# 1. Identify which agents are active
claude-mpm agents list --by-tier

# 2. Inspect problematic agent
claude-mpm agents view problematic_agent

# 3. Check for configuration issues
claude-mpm agents fix problematic_agent --dry-run

# 4. Apply fixes if needed
claude-mpm agents fix problematic_agent

# 5. Verify the fix worked
claude-mpm agents view problematic_agent
```

### Project Setup Workflow

```bash
# 1. Create project-specific agents
mkdir -p .claude-mpm/agents
# ... create agent files ...

# 2. Verify hierarchy and precedence
claude-mpm agents list --by-tier

# 3. Fix any configuration issues
claude-mpm agents fix --all --dry-run
claude-mpm agents fix --all

# 4. Test agents work correctly
claude-mpm run -i "test setup" --non-interactive
```

## Related Commands

### Agent Management
- `claude-mpm agents list --by-tier`: **Most important** - View agent hierarchy
- `claude-mpm agents view <name>`: Inspect specific agent details
- `claude-mpm agents fix [name] [--dry-run] [--all]`: Fix configuration issues
- `claude-mpm agents list --system`: List system agent templates
- `claude-mpm agents list --deployed`: List deployed agents for Claude Code

### Agent Deployment
- `claude-mpm agents deploy`: Deploy system agents
- `claude-mpm agents force-deploy`: Force redeploy all agents
- `claude-mpm agents clean`: Remove deployed agents

## Benefits

### Version Display
1. **Quick Access**: Check agent versions without leaving your workflow
2. **Consistency**: Same output format across all access methods
3. **Visibility**: Easy verification of deployed agent versions
4. **Integration**: Works seamlessly in Claude Code via `/mpm` commands

### Advanced Agent Management
1. **Hierarchy Understanding**: Clear visualization of PROJECT > USER > SYSTEM precedence
2. **Configuration Validation**: Automatic detection and fixing of frontmatter issues
3. **Safe Maintenance**: Dry-run mode for previewing changes before applying
4. **Comprehensive Inspection**: Detailed agent information including instructions and metadata
5. **Development Support**: Essential tools for agent development and troubleshooting
6. **Workflow Integration**: Seamlessly fits into daily development and maintenance workflows

## Next Steps

- See [Agent System Guide](../../AGENTS.md) for comprehensive agent documentation
- Check [Creating Local Agents](../../AGENTS.md#creating-local-agents) for agent development
- Review [CLI Commands Reference](cli-commands.md) for other available commands
- Explore [Agent Troubleshooting](../../AGENTS.md#troubleshooting) for problem resolution