# Agent Migration Script (v5.0)

## Quick Start

```bash
# Preview what will happen (recommended first step)
make migrate-agents-v5-dry-run

# Or directly:
python scripts/migrate_agents_v5.py --dry-run

# Run actual migration
make migrate-agents-v5

# Or with manual confirmation:
python scripts/migrate_agents_v5.py

# Or skip confirmation:
python scripts/migrate_agents_v5.py --force
```

## What This Script Does

Safely migrates from old JSON-template agents to new Git-sourced agents by:

1. **Finding old agents** in `~/.claude/agents/`
2. **Creating backup archive** at `~/.claude/agents-old-archive.zip`
3. **Verifying archive** integrity before proceeding
4. **Removing old agents** safely
5. **Deploying Git agents** from https://github.com/bobmatnyc/claude-mpm-agents

## Safety Features

- ✅ **Archive before delete**: Creates complete backup first
- ✅ **Integrity verification**: Checks archive is valid before deletion
- ✅ **User confirmation**: Asks permission before changes (unless --force)
- ✅ **Dry-run mode**: Preview changes without execution
- ✅ **Selective filtering**: Preserves Git-sourced agents
- ✅ **Detailed logging**: Shows exactly what's happening
- ✅ **Rollback capability**: Archive can be restored if needed

## Command-Line Options

```
python scripts/migrate_agents_v5.py [OPTIONS]

Options:
  --dry-run    Preview migration without making changes
  --force      Skip confirmation prompts
  --help       Show help message
```

## Expected Output (No Old Agents)

```
🔄 Starting v5.0 agent migration...

✅ No old JSON-template agents found!
   Agents directory: ~/.claude/agents

🔍 Checking Git-sourced agents...
```

## Expected Output (With Old Agents)

```
🔄 Starting v5.0 agent migration...

📦 Found 39 old JSON-template agents
   - engineer_agent.md
   - qa_agent.md
   - research_agent.md
   ... and 36 more

⚠️  This will:
   1. Archive 39 old agents to ~/.claude/agents-old-archive.zip
   2. Remove old agent files from ~/.claude/agents
   3. Deploy fresh Git-sourced agents

Continue? [y/N]: y

📦 Creating archive: ~/.claude/agents-old-archive.zip
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

## Archive Contents

The archive includes:

```
agents-old-archive.zip
├── README.txt              # What this archive is and how to restore
└── agents/
    ├── engineer_agent.md   # All your old agents
    ├── qa_agent.md
    ├── research_agent.md
    └── ...
```

## Restoring from Archive (If Needed)

```bash
# Extract entire archive
unzip ~/.claude/agents-old-archive.zip -d ~/agent-restore

# Copy specific agent back
cp ~/agent-restore/agents/engineer_agent.md ~/.claude/agents/

# Or extract single agent
unzip ~/.claude/agents-old-archive.zip agents/engineer_agent.md -d ~/.claude/
```

**Note**: Restored old agents won't receive updates from Git.

## Troubleshooting

### "Archive creation failed"

```bash
# Check disk space
df -h ~

# Check permissions
ls -la ~/.claude/

# Ensure directory exists
mkdir -p ~/.claude/agents
```

### "Git deployment failed"

```bash
# Manually sync agents
claude-mpm agent-source sync

# Check Git source configured
claude-mpm agent-source list

# Test connectivity
curl -I https://github.com/bobmatnyc/claude-mpm-agents
```

### "Permission denied"

```bash
# Check file permissions
ls -la ~/.claude/agents/

# Fix ownership (macOS/Linux)
chown -R $USER ~/.claude/
```

## Development

### Running Tests

```bash
# Run all migration tests
python -m pytest tests/scripts/test_migrate_agents_v5.py -v

# Run specific test
python -m pytest tests/scripts/test_migrate_agents_v5.py::TestAgentMigrator::test_create_archive_success -v

# Run with coverage
python -m pytest tests/scripts/test_migrate_agents_v5.py --cov=scripts.migrate_agents_v5 --cov-report=html
```

### Test Coverage

- 22 comprehensive tests
- 100% pass rate
- Coverage includes:
  - Agent discovery
  - Archive creation/verification
  - Agent removal
  - Git deployment
  - User interaction
  - Error handling
  - Edge cases

## Implementation Details

### Key Components

1. **AgentMigrator Class**
   - Main orchestration logic
   - Dry-run and force modes
   - Comprehensive error handling

2. **Archive System**
   - ZIP compression
   - Integrity verification
   - README generation
   - Restoration support

3. **Git Integration**
   - Uses `claude-mpm agent-source sync`
   - Automatic agent counting
   - Deployment verification

### File Structure

```
scripts/
└── migrate_agents_v5.py          # Main migration script (412 lines)

tests/scripts/
├── __init__.py                    # Module initialization
└── test_migrate_agents_v5.py     # Test suite (381 lines)

docs/migration/
└── v5-agent-migration-guide.md   # User documentation (301 lines)
```

## Version History

- **v1.0.0** (2025-11-30): Initial implementation
  - Complete migration system
  - Comprehensive test suite
  - Full documentation
  - Makefile integration

## Related Documentation

- [User Guide](../../docs/migration/v5-agent-migration-guide.md)
- [Implementation Summary](../../V5_AGENT_MIGRATION_SUMMARY.md)
- [Agent Sources Documentation](../../docs/user/agent-sources.md)
- [Git Source Configuration](../../docs/reference/cli-agent-source.md)

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section above
2. Review [User Guide](../../docs/migration/v5-agent-migration-guide.md)
3. Run diagnostics: `claude-mpm doctor`
4. File an issue: https://github.com/bobmatnyc/claude-mpm/issues

## License

This script is part of Claude MPM and follows the same license.
