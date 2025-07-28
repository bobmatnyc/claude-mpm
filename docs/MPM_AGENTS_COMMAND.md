# /mpm agents Command Documentation

## Overview

The `/mpm agents` command provides a quick way to check deployed agent versions in claude-mpm. This command is available in multiple contexts:

1. **CLI**: `claude-mpm agents` or `claude-mpm --mpm:agents`
2. **Interactive Mode**: `/mpm:agents` 
3. **Claude Code**: `/mpm agents`

## Purpose

This command displays:
- All deployed agent names and their versions
- The base agent version
- Migration warnings if agents need semantic versioning updates

## Usage Examples

### From Command Line

```bash
# Without prefix
claude-mpm agents

# With prefix
claude-mpm --mpm:agents
```

### From Claude Code

Simply type in your prompt:
```
/mpm agents
```

### From Interactive Wrapper

```
/mpm:agents
```

## Output Format

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

## Implementation Details

The command uses a single source of truth function (`_get_agent_versions_display()`) that:
1. Queries the `AgentDeploymentService` for deployed agents
2. Sorts agents alphabetically by name
3. Formats the output in a consistent table format
4. Includes base agent version information
5. Shows migration warnings if applicable

## Integration Points

1. **CLI (`cli.py`)**: 
   - `manage_agents()` function handles the command when no subcommand is provided
   - Uses `_get_agent_versions_display()` for consistent output

2. **Interactive Wrapper (`simple_runner.py`)**:
   - `_handle_mpm_command()` routes `/mpm:agents` to the display function

3. **Claude Code Hooks (`hook_handler.py`)**:
   - `_handle_mpm_agents()` intercepts `/mpm agents` and displays versions
   - Blocks LLM processing with exit code 2

## Related Commands

- `claude-mpm agents list --deployed`: More detailed listing with file paths
- `claude-mpm agents deploy`: Deploy system agents
- `claude-mpm agents force-deploy`: Force redeploy all agents

## Benefits

1. **Quick Access**: Check agent versions without leaving your workflow
2. **Consistency**: Same output format across all access methods
3. **Visibility**: Easy verification of deployed agent versions
4. **Integration**: Works seamlessly in Claude Code via `/mpm` commands