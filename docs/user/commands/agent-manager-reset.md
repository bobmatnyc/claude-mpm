# Agent Manager Reset Command

## Overview

The `agent-manager reset` command removes claude-mpm authored agents from your project and user directories, providing a clean slate for agent management. This is useful when you want to:

- Get fresh versions of system agents after an update
- Clean up after testing or experimentation
- Prepare for a clean reinstall
- Remove all framework-provided agents while keeping your custom agents

## How It Works

The reset command identifies agents by checking for `author: claude-mpm` in the agent's frontmatter. Only agents with this metadata are removed, ensuring your custom agents are preserved.

## Usage

```bash
# Preview what would be removed (dry-run mode)
claude-mpm agent-manager reset --dry-run

# Remove all claude-mpm agents with confirmation prompt
claude-mpm agent-manager reset

# Remove all claude-mpm agents immediately without confirmation
claude-mpm agent-manager reset --force

# Remove only project-level agents
claude-mpm agent-manager reset --project-only

# Remove only user-level agents
claude-mpm agent-manager reset --user-only

# Get output in JSON format
claude-mpm agent-manager reset --format json
```

## Options

- `--dry-run`: Preview what would be removed without making changes
- `--force`: Execute cleanup immediately without confirmation prompt
- `--project-only`: Only clean project-level agents (.claude/agents)
- `--user-only`: Only clean user-level agents (~/.claude/agents)
- `--format {text,json}`: Output format (default: text)

## Agent Preservation

The reset command preserves:
- Any agent without `author: claude-mpm` in its frontmatter
- User-created custom agents
- Agents modified from system templates (if author metadata was changed)

## Examples

### Preview cleanup
```bash
$ claude-mpm agent-manager reset --dry-run

🔍 DRY RUN - No changes will be made
==================================================

📁 Project Level (.claude/agents):
   Would remove 5 claude-mpm agent(s):
      • engineer.md
      • researcher.md
      • ops.md
      • reviewer.md
      • architect.md
   Preserved 2 user-created agent(s)

📁 User Level (~/.claude/agents):
   No claude-mpm agents found

📊 Summary:
   • Would remove: 5 agent(s)
   • Preserved: 2 user agent(s)

💡 Run with --force to execute this cleanup immediately
```

### Force cleanup without confirmation
```bash
$ claude-mpm agent-manager reset --force

🧹 Agent Reset Complete
==================================================

📁 Project Level (.claude/agents):
   Removed 5 claude-mpm agent(s):
      • engineer.md
      • researcher.md
      • ops.md
      • reviewer.md
      • architect.md
   Preserved 2 user-created agent(s)

📊 Summary:
   • Removed: 5 agent(s)
   • Preserved: 2 user agent(s)
```

### Clean only project agents
```bash
$ claude-mpm agent-manager reset --project-only --force

🧹 Agent Reset Complete
==================================================

📁 Project Level (.claude/agents):
   Removed 3 claude-mpm agent(s)
   Preserved 1 user-created agent(s)

📊 Summary:
   • Removed: 3 agent(s)
   • Preserved: 1 user agent(s)
```

## Safety Features

1. **Dry-run by default**: Use `--dry-run` to preview changes before execution
2. **Confirmation prompt**: Without `--force`, the command asks for confirmation
3. **Selective preservation**: Only removes agents explicitly authored by claude-mpm
4. **Directory-specific options**: Target specific directories with `--project-only` or `--user-only`
5. **Clear feedback**: Shows exactly which agents will be or were removed

## When to Use

- **After framework updates**: Get the latest versions of system agents
- **Project cleanup**: Remove test or experimental agents while keeping production ones
- **Troubleshooting**: Start fresh if agents are behaving unexpectedly
- **Before uninstall**: Clean up framework agents before removing claude-mpm

## Related Commands

- `agent-manager list`: View all agents across tiers
- `agent-manager deploy`: Deploy specific agents to project or user tier
- `agent-manager create`: Create new custom agents
- `agent-manager variant`: Create variants of existing agents