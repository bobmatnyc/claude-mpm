# Agent Color and Prompt Migration

## Overview

Claude MPM v6.3.2 includes a startup migration that automatically injects a `color:` field into agent definitions based on agent category. This ensures agents are consistently color-coded in the Claude Code UI while preserving custom `initialPrompt` values from source agent definitions.

## What Gets Migrated

### Color Injection

The migration automatically assigns colors to agents based on their category:

| Agent Category | Color | Use Case |
|---|---|---|
| `qa` | green | Quality assurance and testing agents |
| `research` | purple | Research and investigation agents |
| `ops` | orange | Operations and infrastructure agents |
| `documentation` | yellow | Documentation and writing agents |
| `security` | red | Security and compliance agents |
| *default* | blue | All other agent types |

### Agent Definition Format

Agents are defined in `.claude/agents/*.md` files with YAML frontmatter:

```markdown
---
name: My QA Agent
agent_id: qa-agent-123
agent_type: qa
model: claude-opus-4
---

Agent description and instructions here.
```

### Color Field Addition

After migration, the agent definition includes:

```markdown
---
name: My QA Agent
agent_id: qa-agent-123
agent_type: qa
model: claude-opus-4
color: green
---

Agent description and instructions here.
```

## Preservation of Initial Prompt

### Initial Prompt in Source Definitions

If an agent definition includes an `initialPrompt:` field in the YAML frontmatter, the migration preserves it:

```markdown
---
name: Research Agent
agent_id: researcher-001
agent_type: research
initialPrompt: "Start by analyzing the problem systematically..."
---
```

### After Migration

Both `color` and `initialPrompt` are preserved:

```markdown
---
name: Research Agent
agent_id: researcher-001
agent_type: research
initialPrompt: "Start by analyzing the problem systematically..."
color: purple
---
```

## Idempotency

The migration is **idempotent** — it is safe to run multiple times:

- **On first run**: Adds `color:` field to all agents without color
- **On subsequent runs**: Checks if `color:` field exists; skips agents that already have it
- **No overwrites**: Existing `color:` values are never overwritten

This means:
- If you manually set a color, the migration will not override it
- You can re-run the migration safely without affecting existing configurations
- The migration completes quickly if already applied (checks existing state first)

## Migration Details

### Migration ID

- **ID**: `v6.3.2-agent-color-inject`
- **Version**: 6.3.2
- **Description**: Inject color field into agent definitions based on category

### When It Runs

The migration runs automatically:
1. **During startup** - Before agent sync or other operations
2. **Once per installation** - Tracked in `~/.claude-mpm/migrations.yaml`
3. **Non-blocking** - Failures do not prevent startup

## User Experience

### During Startup

You may see a message like:

```
Starting startup services...
Running startup migration: Inject color field into agent definitions
Syncing agents from 1 remote sources...
```

### After Migration

- **UI Changes**: Agents display with assigned colors in Claude Code UI
- **Functionality**: No changes to agent behavior or capabilities
- **Config**: Agent definitions in `.claude/agents/` contain new `color:` field

## Troubleshooting

### Color Not Appearing in UI

1. **Restart Claude Code** - UI updates require restart to reload agent definitions
2. **Verify Migration**: Check that `color:` field was added to agent files:
   ```bash
   grep "color:" .claude/agents/*.md
   ```
3. **Check Agent Type**: Verify `agent_type:` is correctly set (qa, research, ops, documentation, security)

### Custom Color Not Applied

If you want to override the default color:

1. Edit the agent definition file (`.claude/agents/your-agent.md`)
2. Add or update the `color:` field with your preferred value
3. Use valid Claude Code color values (see [Claude Code documentation](https://claude.ai/docs))

### Re-run Migration

To force re-run the migration (not typically needed):

1. Edit `~/.claude-mpm/migrations.yaml`
2. Remove the entry for `v6.3.2-agent-color-inject`
3. Restart claude-mpm

```bash
sed -i '' '/v6.3.2-agent-color-inject/d' ~/.claude-mpm/migrations.yaml
```

## Related Documentation

- [Startup Migrations](./startup-migrations.md)
- [Agent System](../architecture/agents.md)
- [Agent Configuration](../guides/agent-configuration.md)
