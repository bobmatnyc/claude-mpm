# v5.0 Agent Migration Guide

## Overview

Claude MPM v5.0 introduces Git-based agent sources, replacing the old JSON-template system. This guide covers the migration process from old JSON-template agents to new Git-sourced agents.

## Quick Migration

For most users, migration is automatic. The system now uses:
- **Git Source**: `https://github.com/bobmatnyc/claude-mpm-agents`
- **Auto-sync**: Agents sync automatically on startup
- **50+ Agents**: Expanded from original template set

## Manual Migration (If Needed)

If you have old JSON-template agents in `~/.claude/agents/`, use the migration script:

### Dry Run (Preview)

```bash
python scripts/migrate_agents_v5.py --dry-run
```

### Full Migration

```bash
python scripts/migrate_agents_v5.py
```

### Force (Skip Confirmation)

```bash
python scripts/migrate_agents_v5.py --force
```

## What the Script Does

1. **Identifies Old Agents**
   - Scans `~/.claude/agents/` for old JSON-template agents
   - Filters out Git-sourced agents (if any exist)

2. **Creates Archive**
   - Archives to: `~/.claude/agents-old-archive.zip`
   - Includes README.txt explaining the archive
   - Verifies archive integrity before proceeding

3. **Removes Old Agents**
   - Only deletes agents successfully archived
   - Preserves user-custom agents (if identifiable)

4. **Deploys Git Agents**
   - Syncs from Git repository
   - Deploys all available agents
   - Verifies deployment success

5. **Reports Results**
   - Shows counts: archived, removed, deployed
   - Provides archive location
   - Confirms migration success

## Expected Output

```
🔄 Starting v5.0 agent migration...

📦 Found 39 old JSON-template agents
   Creating archive: ~/.claude/agents-old-archive.zip

✅ Archive created successfully (2.5 MB)
   Verified: All 39 agents backed up

🗑️  Removing old agents...
   ✅ Removed 39 old agents

🚀 Deploying fresh Git-sourced agents...
   Syncing from: https://github.com/bobmatnyc/claude-mpm-agents
   ✅ Deployed successfully
   ✅ 47 agents available

📊 Migration Summary:
   - Archived: 39 old agents
   - Removed: 39 old agents
   - Deployed: 47 new Git agents
   - Archive: ~/.claude/agents-old-archive.zip

✅ Migration complete! v5.0 agents ready.
```

## Archive Structure

```
agents-old-archive.zip
├── README.txt              # Migration information
└── agents/
    ├── engineer_agent.md
    ├── qa_agent.md
    ├── research_agent.md
    └── ... (all old agents)
```

## Restoring Old Agents (If Needed)

To restore a specific old agent:

1. Extract the archive:
   ```bash
   unzip ~/.claude/agents-old-archive.zip -d ~/agent-restore
   ```

2. Copy desired agent:
   ```bash
   cp ~/agent-restore/agents/engineer_agent.md ~/.claude/agents/
   ```

**Note**: Old agents won't receive updates from Git source.

## Git-Sourced Agents

### Default Repository

- **URL**: https://github.com/bobmatnyc/claude-mpm-agents
- **Subdirectory**: `agents/`
- **Priority**: 100 (system)

### Managing Git Sources

```bash
# List configured sources
claude-mpm agent-source list

# Sync agents from Git
claude-mpm agent-source sync

# Add custom source
claude-mpm agent-source add \
  --url https://github.com/yourorg/custom-agents \
  --name custom-agents
```

## Differences: Old vs. New

### Old System (JSON Templates)

- **Location**: `src/claude_mpm/agents/templates/*.json`
- **Deployment**: `claude-mpm agents deploy <name>`
- **Updates**: Manual code updates, redeploy required
- **Count**: ~15 agents
- **Source**: Built into package

### New System (Git Sources)

- **Location**: Git repository (external)
- **Deployment**: `claude-mpm agent-source sync`
- **Updates**: Automatic sync from Git
- **Count**: 50+ agents (growing)
- **Source**: https://github.com/bobmatnyc/claude-mpm-agents

## Benefits of Git-Sourced Agents

1. **Automatic Updates**
   - Agents sync from Git on startup
   - Always get latest improvements
   - No manual deployment needed

2. **Expanded Library**
   - 50+ agents vs. original 15
   - Community contributions
   - Specialized agents for specific tasks

3. **Customization**
   - Add your own Git sources
   - Mix official + custom agents
   - Priority-based resolution

4. **Maintainability**
   - Agents maintained separately from core
   - Faster iteration on agent improvements
   - Clear separation of concerns

## Troubleshooting

### Migration Script Issues

**Problem**: Script can't find old agents
```bash
# Check agents directory
ls -la ~/.claude/agents/
```

**Problem**: Archive creation fails
```bash
# Check disk space
df -h ~

# Check permissions
ls -la ~/.claude/
```

**Problem**: Git deployment fails
```bash
# Manually sync agents
claude-mpm agent-source sync

# Check connectivity
curl -I https://github.com/bobmatnyc/claude-mpm-agents
```

### Post-Migration Issues

**Problem**: Agents not appearing
```bash
# Verify Git source configured
claude-mpm agent-source list

# Re-sync agents
claude-mpm agent-source sync

# Check deployment
claude-mpm agents list
```

**Problem**: Need old agent back
```bash
# Extract specific agent from archive
unzip ~/.claude/agents-old-archive.zip agents/agent_name.md -d ~/.claude/
```

## Safety Features

The migration script includes multiple safety measures:

1. **Dry-Run Mode**
   - Preview changes without execution
   - Verify what will happen

2. **Archive Before Delete**
   - Always creates backup first
   - Verifies archive integrity
   - Aborts if archive fails

3. **Confirmation Prompt**
   - User must confirm migration
   - Use `--force` to skip

4. **Selective Filtering**
   - Only migrates old JSON-template agents
   - Preserves Git-sourced agents
   - Skips user-custom agents

5. **Detailed Logging**
   - Shows exactly what's happening
   - Reports success/failure for each step
   - Provides clear error messages

## Version Compatibility

- **Required**: Claude MPM v5.0.0+
- **Python**: 3.8+
- **Dependencies**: Standard library only

## Migration Checklist

- [ ] Backup important custom agents (if any)
- [ ] Run dry-run to preview migration
- [ ] Execute migration script
- [ ] Verify archive created successfully
- [ ] Confirm new agents deployed
- [ ] Test agents work as expected
- [ ] Store archive in safe location

## Support

If you encounter issues during migration:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the archive contents for your old agents
3. Run `claude-mpm doctor` for diagnostics
4. File an issue: https://github.com/bobmatnyc/claude-mpm/issues

## Related Documentation

- [Agent Sources Documentation](../user/agent-sources.md)
- [Agent Migration Details](./agent-sources-git-default-v4.5.0.md)
- [Git Source Configuration](../reference/cli-agent-source.md)

## Rollback Procedure

If you need to rollback to old agents:

1. Stop Claude MPM
2. Extract old agents from archive:
   ```bash
   unzip ~/.claude/agents-old-archive.zip -d ~/.claude/
   ```
3. Remove Git source:
   ```bash
   claude-mpm agent-source remove bobmatnyc/claude-mpm-agents/agents
   ```
4. Restart Claude MPM

**Note**: This is not recommended as old agents won't receive updates.
